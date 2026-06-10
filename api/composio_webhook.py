"""POST /webhooks/composio — Composio inbound events.

Source-of-truth surface for connection lifecycle and live ingest. Verifies
HMAC-SHA256 signature against COMPOSIO_WEBHOOK_SECRET, then dispatches by
`event` field. Handles connection lifecycle (complete/revoke/expired) and
live ingest for gmail.new_message and calendar.event.{created,updated,deleted}.

Calendar event payloads ride on the top-level `data` field rather than `event`
to avoid colliding with the event-type discriminator.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from backend.integrations import state
from backend.integrations.calendar_ingest import (
    delete_calendar_event,
    ingest_calendar_event,
)
from backend.integrations.composio_client import (
    TRIGGER_CALENDAR_EVENT_CREATED,
    TRIGGER_CALENDAR_EVENT_DELETED,
    TRIGGER_CALENDAR_EVENT_UPDATED,
    TRIGGER_GMAIL_NEW_MESSAGE,
    ComposioClient,
    normalize_v3_gmail,
    svix_debug,
    verify_svix_signature,
    verify_webhook_signature,
)
from backend.integrations.gmail_ingest import ingest_gmail_message
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


_APP_TO_PRODUCT = {
    "GMAIL": "gmail",
    "GOOGLECALENDAR": "calendar",
}

_CALENDAR_UPSERT_EVENTS = {"calendar.event.created", "calendar.event.updated"}

_PRODUCT_TRIGGERS = {
    "gmail": (TRIGGER_GMAIL_NEW_MESSAGE,),
    "calendar": (
        TRIGGER_CALENDAR_EVENT_CREATED,
        TRIGGER_CALENDAR_EVENT_UPDATED,
        TRIGGER_CALENDAR_EVENT_DELETED,
    ),
}


async def _ensure_user(user_id: str) -> None:
    """Create the Donna user row if it doesn't exist yet.

    Composio events arrive keyed by the Composio entity id; email_messages has
    an FK to users.id, so the first event for a new id must create the user.
    Idempotent; concurrent-insert races are swallowed (the row exists either way).
    """
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    try:
        async with async_session() as session:
            existing = (
                await session.execute(select(User.id).where(User.id == user_id))
            ).scalar_one_or_none()
            if existing:
                return
            session.add(User(id=user_id, phone=f"composio:{user_id}"))
            await session.commit()
            logger.info("composio_webhook: created user %r for incoming events", user_id)
    except Exception:
        # unique-violation race or transient DB error — ingest will surface
        # anything real; don't fail the webhook here.
        logger.exception("composio_webhook: _ensure_user(%r) failed", user_id)


@router.post("/webhooks/composio")
async def composio_webhook(
    request: Request,
    # Legacy Composio
    x_composio_signature: str | None = Header(default=None),
    # Composio V3 (Svix / Standard Webhooks)
    webhook_id: str | None = Header(default=None),
    webhook_timestamp: str | None = Header(default=None),
    webhook_signature: str | None = Header(default=None),
) -> dict:
    body = await request.body()
    secret = settings.composio_webhook_secret or ""

    # Verify: Composio V3 (Svix) first, then legacy x-composio-signature.
    if webhook_signature:
        scheme = "svix-v3"
        ok = verify_svix_signature(secret, webhook_id or "", webhook_timestamp or "", body, webhook_signature)
    elif x_composio_signature:
        scheme = "legacy"
        ok = verify_webhook_signature(body, x_composio_signature, secret)
    else:
        scheme = "none"
        ok = False

    if not ok:
        logger.warning(
            "composio_webhook: signature invalid (scheme=%s, secret_set=%s, headers=%s)",
            scheme, bool(secret), sorted(request.headers.keys()),
        )
        if scheme == "svix-v3":
            # TEMP: log received vs computed signatures (HMACs, not the secret).
            logger.warning(
                "composio_webhook SVIX DEBUG: %s",
                svix_debug(secret, webhook_id or "", webhook_timestamp or "", body, webhook_signature or ""),
            )
        raise HTTPException(status_code=401, detail="bad signature")
    logger.info("composio_webhook: signature OK (scheme=%s)", scheme)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="bad json")

    # V3 payloads use `type`; legacy used `event`.
    event = payload.get("event") or payload.get("type")
    user_id = payload.get("user_id")
    logger.info("composio_webhook: event type received = %r (keys=%s)", event, sorted(payload.keys()))

    # ── Composio V3 trigger envelope ──────────────────────────────────────────
    # type="composio.trigger.message"; the real trigger + user live in metadata,
    # and the full record is inlined in `data` (no follow-up fetch needed).
    if event == "composio.trigger.message":
        meta = payload.get("metadata") or {}
        slug = meta.get("trigger_slug") or ""
        v3_user = meta.get("user_id")
        data = payload.get("data") or {}
        logger.info("composio_webhook: V3 trigger_slug=%r user=%r", slug, v3_user)
        if not v3_user:
            return {"ok": True, "unhandled": "v3 missing user_id"}
        # The Composio user id may not exist as a Donna user yet (FK on
        # email_messages.user_id) — create it on first event.
        await _ensure_user(v3_user)
        try:
            if slug == TRIGGER_GMAIL_NEW_MESSAGE:
                msg = normalize_v3_gmail(data)
                await ingest_gmail_message(v3_user, msg)
                await state.touch_synced(v3_user, "google", "gmail")
                logger.info(
                    "composio_webhook: ingested gmail id=%s from=%r subj=%r user=%s",
                    msg.gmail_message_id, msg.from_address, msg.subject, v3_user,
                )
                return {"ok": True}
            if slug in (TRIGGER_CALENDAR_EVENT_CREATED, TRIGGER_CALENDAR_EVENT_UPDATED):
                await ingest_calendar_event(v3_user, data)
                await state.touch_synced(v3_user, "google", "calendar")
                return {"ok": True}
            if slug == TRIGGER_CALENDAR_EVENT_DELETED:
                ev_id = data.get("id") or data.get("event_id")
                if ev_id:
                    await delete_calendar_event(v3_user, ev_id)
                return {"ok": True}
        except Exception:
            logger.exception("composio_webhook: V3 ingest failed slug=%s user=%s", slug, v3_user)
            return {"ok": True, "error": "ingest_failed"}
        logger.info("composio_webhook: unhandled V3 trigger_slug=%r", slug)
        return {"ok": True, "unhandled": slug}
    # ──────────────────────────────────────────────────────────────────────────

    # Legacy Composio shapes below. Signed but unmapped → ACK 200 (no retry).
    if not event:
        return {"ok": True, "unhandled": True}
    if not user_id:
        logger.info("composio_webhook: no top-level user_id for event=%r — acking", event)
        return {"ok": True, "unhandled": "no user_id"}

    if event == "connection.complete":
        app = (payload.get("app") or "").upper()
        product = _APP_TO_PRODUCT.get(app)
        if product is None:
            logger.warning("composio_webhook: unknown app=%r", app)
            return {"ok": True, "ignored": True}
        connection_id = payload.get("connection_id") or ""
        await state.mark_connected(
            user_id,
            "google",
            product,
            connection_id=connection_id,
        )
        triggers = _PRODUCT_TRIGGERS.get(product, ())
        if triggers and connection_id:
            client = ComposioClient(api_key=settings.composio_api_key or "")
            await client.subscribe_triggers(
                user_id=user_id,
                connection_id=connection_id,
                trigger_names=triggers,
            )
        # Bootstrap enqueue happens in P3.
        return {"ok": True}

    if event in {"connection.revoked", "connection.expired"}:
        app = (payload.get("app") or "").upper()
        product = _APP_TO_PRODUCT.get(app)
        if product:
            await state.mark_revoked(user_id, "google", product)
        return {"ok": True}

    if event == "gmail.new_message":
        message_id = payload.get("message_id")
        if not message_id:
            raise HTTPException(status_code=400, detail="missing message_id")
        client = ComposioClient(api_key=settings.composio_api_key or "")
        msg = await client.fetch_gmail_message(
            user_id=user_id, message_id=message_id, include_body=True
        )
        await ingest_gmail_message(user_id, msg)
        await state.touch_synced(user_id, "google", "gmail")
        return {"ok": True}

    if event in _CALENDAR_UPSERT_EVENTS:
        ev = payload.get("data") or {}
        if not ev.get("id"):
            raise HTTPException(status_code=400, detail="missing event id")
        await ingest_calendar_event(user_id, ev)
        await state.touch_synced(user_id, "google", "calendar")
        return {"ok": True}

    if event == "calendar.event.deleted":
        ev = payload.get("data") or {}
        ev_id = ev.get("id") or payload.get("event_id")
        if not ev_id:
            raise HTTPException(status_code=400, detail="missing event id")
        await delete_calendar_event(user_id, ev_id)
        await state.touch_synced(user_id, "google", "calendar")
        return {"ok": True}

    logger.info("composio_webhook: unhandled event=%r", event)
    return {"ok": True, "unhandled": event}

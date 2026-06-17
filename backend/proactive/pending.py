"""Pending proactive queue (A1 — Meta 24h session-window compliance).

When Donna wants to send a proactive message and the user is outside the 24h
window, we:
  1. Send the `donna_reopen` template (fixed text, no variables) to reopen the
     session window — the user gets a gentle "hey, been a while" nudge.
  2. Store the actual proactive content here.

When the user replies (any inbound message), _run_pipeline calls flush_pending
BEFORE the brain loop — the user gets what Donna wanted to say, then the
conversation continues naturally.

Rows older than _EXPIRE_DAYS are dropped silently at flush time — a 10-day-old
proactive is out of context and better discarded than delivered.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_EXPIRE_DAYS = 7


async def queue_proactive(user_id: str, content: str) -> None:
    """Store proactive content for later delivery and send the reopen template."""
    from sqlalchemy import delete

    from db.models import PendingProactive, utcnow
    from db.session import async_session

    # Drop stale rows first so we don't accumulate garbage.
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=_EXPIRE_DAYS)
    async with async_session() as s:
        await s.execute(
            delete(PendingProactive)
            .where(PendingProactive.user_id == user_id)
            .where(PendingProactive.created_at < cutoff)
        )
        s.add(PendingProactive(user_id=user_id, content=content, created_at=utcnow()))
        await s.commit()

    logger.info("pending_proactive: queued for user=%s", user_id[:8])

    # Send the reopen template to nudge the user back into the window.
    await _send_reopen_template(user_id)


async def flush_pending(user_id: str, phone: str) -> bool:
    """Send all queued proactive messages as freeform and clear the queue.

    Returns True if anything was flushed. Called by _run_pipeline on every
    inbound so the user gets what Donna wanted to say before the brain runs.
    Rows older than _EXPIRE_DAYS are silently dropped.
    """
    from sqlalchemy import delete, select

    from db.models import PendingProactive
    from db.session import async_session

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=_EXPIRE_DAYS)

    async with async_session() as s:
        rows = (
            await s.execute(
                select(PendingProactive)
                .where(PendingProactive.user_id == user_id)
                .order_by(PendingProactive.created_at)
            )
        ).scalars().all()

        if not rows:
            return False

        fresh = [r for r in rows if r.created_at >= cutoff]
        stale_count = len(rows) - len(fresh)

        await s.execute(
            delete(PendingProactive).where(PendingProactive.user_id == user_id)
        )
        await s.commit()

    if stale_count:
        logger.info("pending_proactive: dropped %d stale rows for user=%s", stale_count, user_id[:8])

    if not fresh:
        return False

    from delivery.messages import TextMessage
    from delivery.whatsapp import WhatsAppChannel

    wa = WhatsAppChannel()
    for row in fresh:
        try:
            await wa.send(phone, TextMessage(body=row.content))
        except Exception:
            logger.exception("pending_proactive: send failed for user=%s", user_id[:8])

    logger.info("pending_proactive: flushed %d messages to user=%s", len(fresh), user_id[:8])
    return True


async def _send_reopen_template(user_id: str) -> None:
    """Send the donna_reopen template to the user to nudge them back."""
    from sqlalchemy import select

    from config import settings
    from db.models import User
    from db.session import async_session
    from delivery.whatsapp import WhatsAppChannel

    if not settings.whatsapp_token:
        return

    async with async_session() as s:
        phone = (
            await s.execute(select(User.phone).where(User.id == user_id))
        ).scalar_one_or_none()

    if not phone or phone.startswith("composio:"):
        return

    try:
        await WhatsAppChannel().send_template(phone, settings.whatsapp_reopen_template)
        logger.info("pending_proactive: sent reopen template to user=%s", user_id[:8])
    except Exception:
        logger.exception("pending_proactive: reopen template failed for user=%s", user_id[:8])

"""Push notifications via Firebase Cloud Messaging (HTTP v1).

This is the app's proactive channel: when Donna decides to reach out (a notable
email, a scheduled nudge), the same outbound bubbles she'd send on WhatsApp also
land as a phone notification that deep-links into chat.

Config-gated. With no credentials it is a silent no-op, so the backend runs and
the APK builds before Firebase is set up. To enable, set:

    FCM_SERVICE_ACCOUNT_JSON  — the service-account JSON (raw string OR a path)
    FCM_PROJECT_ID            — optional; defaults to the JSON's project_id

The device side is `@capacitor/push-notifications` + `webapp/src/push.js`, which
uploads the FCM registration token to POST /push/register.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select

from db.models import DeviceToken
from db.session import async_session

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_FCM_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

_creds = None  # cached google service-account credentials


def _fcm_raw() -> str:
    # pydantic settings read both .env (local) and real env (Railway); fall back
    # to os.getenv for any context where settings isn't the source of truth.
    try:
        from config import settings
        if settings.fcm_service_account_json:
            return settings.fcm_service_account_json.strip()
    except Exception:
        pass
    return os.getenv("FCM_SERVICE_ACCOUNT_JSON", "").strip()


def _load_service_account() -> dict | None:
    raw = _fcm_raw()
    if not raw:
        return None
    # Accept either inline JSON or a path to a .json file.
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error("push: FCM_SERVICE_ACCOUNT_JSON is not valid JSON")
            return None
    p = Path(raw)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            logger.error("push: could not read FCM service account file %s", p)
            return None
    logger.error("push: FCM_SERVICE_ACCOUNT_JSON neither JSON nor an existing path")
    return None


def is_configured() -> bool:
    return _load_service_account() is not None


def _project_id(info: dict) -> str | None:
    try:
        from config import settings
        if settings.fcm_project_id:
            return settings.fcm_project_id.strip()
    except Exception:
        pass
    return os.getenv("FCM_PROJECT_ID", "").strip() or info.get("project_id")


def _access_token_sync(info: dict) -> str | None:
    """Mint a short-lived OAuth token from the service account. Blocking —
    callers run it via asyncio.to_thread."""
    global _creds
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests as greq

        if _creds is None:
            _creds = service_account.Credentials.from_service_account_info(
                info, scopes=[_SCOPE]
            )
        if not _creds.valid:
            _creds.refresh(greq.Request())
        return _creds.token
    except Exception:
        logger.exception("push: failed to mint FCM access token")
        return None


async def _tokens_for(user_id: str) -> list[DeviceToken]:
    async with async_session() as s:
        rows = await s.execute(
            select(DeviceToken).where(DeviceToken.user_id == user_id)
        )
        return list(rows.scalars().all())


async def _drop_token(token: str) -> None:
    try:
        async with async_session() as s:
            await s.execute(delete(DeviceToken).where(DeviceToken.token == token))
            await s.commit()
    except Exception:
        logger.exception("push: failed to drop dead token")


async def send_push(
    user_id: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Send one notification to every device registered for `user_id`.
    Returns the number of devices reached. No-op (0) if FCM is unconfigured
    or the user has no devices."""
    info = _load_service_account()
    if info is None:
        logger.debug("push: skipped (FCM not configured)")
        return 0

    project_id = _project_id(info)
    if not project_id:
        logger.error("push: no project_id available")
        return 0

    tokens = await _tokens_for(user_id)
    if not tokens:
        return 0

    access_token = await asyncio.to_thread(_access_token_sync, info)
    if not access_token:
        return 0

    url = _FCM_URL.format(project_id=project_id)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    # FCM data values must be strings.
    str_data = {k: str(v) for k, v in (data or {}).items()}
    str_data.setdefault("route", "chat")

    sent = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for dt in tokens:
            message: dict[str, Any] = {
                "message": {
                    "token": dt.token,
                    "notification": {"title": title, "body": body},
                    "data": str_data,
                    "android": {"priority": "high"},
                    "apns": {"headers": {"apns-priority": "10"}},
                }
            }
            try:
                resp = await client.post(url, headers=headers, json=message)
            except Exception:
                logger.exception("push: send failed for one device")
                continue
            if resp.status_code == 200:
                sent += 1
            elif resp.status_code in (404, 400) and "UNREGISTERED" in resp.text.upper():
                # Token is dead — prune it so we stop trying.
                await _drop_token(dt.token)
            else:
                logger.warning("push: FCM %s -> %s", resp.status_code, resp.text[:200])
    logger.info("push: delivered to %d/%d devices for user=%s", sent, len(tokens), user_id[:8])
    return sent


def render_bubbles_to_text(outbound: list) -> str:
    """Collapse a burst of outbound bubbles into one notification body."""
    from donna_runtime.tool_logic import render_outbound_text

    parts: list[str] = []
    for m in outbound or []:
        t = render_outbound_text(m)
        if t:
            parts.append(t)
    text = "  ".join(parts).strip()
    return (text[:240] + "…") if len(text) > 240 else text


async def notify_outbound(user_id: str, outbound: list, title: str = "donna") -> int:
    """Push a proactive turn's bubbles to the user's devices. Best-effort."""
    body = render_bubbles_to_text(outbound)
    if not body:
        return 0
    try:
        return await send_push(user_id, title, body)
    except Exception:
        logger.exception("push: notify_outbound failed for user=%s", user_id[:8])
        return 0

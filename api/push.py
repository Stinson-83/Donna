"""Push registration + test endpoints.

The app uploads its FCM token here on launch; we resolve the stable app id to
the same User the chat/brain path uses, then upsert the device. POST /push/test
lets you verify the whole chain (Firebase creds -> device -> phone) end to end.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from db.models import DeviceToken, User, utcnow
from db.session import async_session

logger = logging.getLogger(__name__)
router = APIRouter()


def _now():
    return utcnow()


async def resolve_user_id(app_id: str) -> str:
    """Map the stable app id (phone key) to the User.id UUID, creating the user
    if needed — mirrors api.graph.user_lookup but without the full ingress state."""
    # Resolve the session factory at call time (not the module-level binding) so a
    # swapped db.session.async_session — the test fixture — is always honored.
    from db.session import async_session

    app_id = (app_id or "web-demo").strip() or "web-demo"
    async with async_session() as s:
        row = await s.execute(select(User).where(User.phone == app_id))
        user = row.scalar_one_or_none()
        if user is None:
            user = User(id=str(uuid.uuid4()), phone=app_id)
            s.add(user)
            await s.commit()
            await s.refresh(user)
        return user.id


class RegisterBody(BaseModel):
    user: str
    token: str
    platform: str | None = "android"


@router.post("/push/register")
async def register(body: RegisterBody) -> dict:
    if not body.token.strip():
        return {"ok": False, "error": "empty token"}
    user_id = await resolve_user_id(body.user)
    async with async_session() as s:
        row = await s.execute(select(DeviceToken).where(DeviceToken.token == body.token))
        dt = row.scalar_one_or_none()
        if dt is None:
            s.add(DeviceToken(
                user_id=user_id,
                token=body.token,
                platform=(body.platform or "android"),
            ))
        else:
            # Token may have moved to a different identity (re-login) — re-key it.
            dt.user_id = user_id
            dt.platform = body.platform or dt.platform
            dt.last_seen_at = _now()
        await s.commit()
    logger.info("push: registered %s device for user=%s", body.platform, user_id[:8])
    return {"ok": True, "user_id": user_id}


class TestBody(BaseModel):
    user: str
    title: str | None = None
    body: str | None = None


@router.post("/push/test")
async def test_push(body: TestBody) -> dict:
    """Fire a test notification to the user's devices. Reports whether FCM is
    configured and how many devices were reached."""
    from backend.integrations.push import is_configured, send_push

    user_id = await resolve_user_id(body.user)
    if not is_configured():
        return {"ok": False, "configured": False, "reason": "FCM_SERVICE_ACCOUNT_JSON not set"}
    sent = await send_push(
        user_id,
        body.title or "donna",
        body.body or "this is a test ping. tap to open chat.",
    )
    return {"ok": sent > 0, "configured": True, "delivered": sent}

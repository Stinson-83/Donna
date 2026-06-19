"""Web-dashboard auth — the magic-link layer (build plan B1).

Flow: Donna mints a per-user magic link (`mint_magic_link`) and sends it in WhatsApp.
The dashboard opens it, posts the magic token to `POST /auth/exchange`, and gets back a
longer-lived *session* token it stores and sends as `Authorization: Bearer <session>`.
`current_user_id` is the dependency the dashboard endpoints use to resolve the caller:
a valid Bearer session wins; otherwise it falls back to the legacy unauthenticated
`?user=` param — UNLESS `settings.require_auth` is set, in which case the fallback is
refused (so a public deploy serves only token-verified, per-user data).

No DB lookup is needed to validate a token (it's self-contained + signed); the only DB
touch is loading the display name. Same gate/executors as WhatsApp downstream.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.auth.tokens import (
    MAGIC,
    SESSION,
    TokenError,
    mint_magic_token,
    mint_session_token,
    verify_token,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def mint_magic_link(user_id: str) -> str:
    """The per-user dashboard URL Donna sends in WhatsApp. The token rides the URL
    *fragment* (`#t=`) so it is never sent to a server in a request line or Referer —
    only the dashboard's own JS reads it, then exchanges it for a session."""
    from config import settings

    base = (settings.dashboard_base_url or "").rstrip("/")
    return f"{base}/#t={mint_magic_token(user_id)}"


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return None


async def _user_name(user_id: str) -> str | None:
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        return (await s.execute(select(User.name).where(User.id == user_id))).scalar_one_or_none()


async def resolve_request_user(authorization: str | None, user: str | None) -> str:
    """Pure resolution (directly unit-testable, no FastAPI binding): a valid Bearer
    session token wins; else the legacy `?user=` fallback unless auth is required."""
    token = _bearer(authorization)
    if token:
        try:
            return verify_token(token, purpose=SESSION)
        except TokenError as exc:
            raise HTTPException(status_code=401, detail=f"invalid_session:{exc.reason}")

    from config import settings

    if getattr(settings, "require_auth", False):
        raise HTTPException(status_code=401, detail="auth_required")

    from api.push import resolve_user_id

    return await resolve_user_id(user or "web-demo")


async def current_user_id(
    authorization: str | None = Header(default=None),
    user: str | None = None,
) -> str:
    """FastAPI dependency: the resolved caller for a dashboard request. Drop-in for the
    old `user: str` + `resolve_user_id(user)` pair — back-compatible (the `?user=` path
    still works) until `require_auth` is turned on."""
    return await resolve_request_user(authorization, user)


class ExchangeBody(BaseModel):
    magic: str


@router.post("/auth/exchange")
async def exchange(body: ExchangeBody) -> dict:
    """Magic token (from the link) → a session token the dashboard stores."""
    try:
        user_id = verify_token(body.magic, purpose=MAGIC)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=f"invalid_magic_link:{exc.reason}")
    return {
        "session_token": mint_session_token(user_id),
        "user_id": user_id,
        "name": await _user_name(user_id),
    }


@router.get("/auth/me")
async def me(user_id: str = Depends(current_user_id)) -> dict:
    """Validate the session and return who it is — the dashboard's bootstrap call."""
    return {"user_id": user_id, "name": await _user_name(user_id)}


class DevLinkBody(BaseModel):
    user: str


@router.post("/auth/dev_token")
async def dev_token(body: DevLinkBody) -> dict:
    """DEV-ONLY: mint a magic token for a user so the dashboard auth flow can be
    exercised without the WhatsApp link. Fails closed (404) once require_auth is
    enabled, so it is inert in any real/public deploy."""
    from config import settings

    if getattr(settings, "require_auth", False):
        raise HTTPException(status_code=404, detail="not_found")
    from api.push import resolve_user_id

    user_id = await resolve_user_id(body.user)
    return {"magic": mint_magic_token(user_id), "user_id": user_id}

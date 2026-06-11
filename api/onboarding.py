"""App-facing onboarding endpoints.

POST /onboarding/run     — kick off the backfill (calendar + relationships)
GET  /onboarding/status  — progress (complete?, #relationships, #calendar events)

Also runs automatically in the background when an account connection completes
(api/composio_webhook.py). Reuses the app's user resolution.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RunBody(BaseModel):
    user: str


class ConnectBody(BaseModel):
    user: str
    provider: str | None = "googlecalendar"


@router.post("/onboarding/connect")
async def connect(body: ConnectBody) -> dict:
    """Start an OAuth connection for the user (real Composio). The app opens the
    returned url; on completion the connection.complete webhook auto-runs the
    backfill (and the app can also call /onboarding/run to kick it immediately)."""
    from config import settings

    from api.push import resolve_user_id
    from backend.integrations.composio_client import ComposioClient

    user_id = await resolve_user_id(body.user)
    provider = (body.provider or "googlecalendar").strip()
    try:
        _conn, url = await ComposioClient(
            api_key=settings.composio_api_key or ""
        ).get_or_create_connection(user_id, provider)
    except Exception:
        return {"ok": False, "user_id": user_id, "provider": provider, "error": "connect_failed"}
    return {"ok": True, "user_id": user_id, "provider": provider, "url": url}


@router.post("/onboarding/run")
async def run(body: RunBody) -> dict:
    from api.push import resolve_user_id
    from backend.onboarding.service import run_onboarding

    user_id = await resolve_user_id(body.user)
    result = await run_onboarding(user_id)
    return {"user_id": user_id, **result}


@router.get("/onboarding/status")
async def status(user: str) -> dict:
    from api.push import resolve_user_id
    from backend.onboarding.service import onboarding_status

    user_id = await resolve_user_id(user)
    return {"user_id": user_id, **await onboarding_status(user_id)}

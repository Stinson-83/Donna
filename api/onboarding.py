"""App-facing onboarding endpoints.

POST /onboarding/run     — kick off the backfill (calendar + relationships)
GET  /onboarding/status  — progress (complete?, #relationships, #calendar events)

Also runs automatically in the background when an account connection completes
(api/composio_webhook.py). Reuses the app's user resolution.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


class RunBody(BaseModel):
    pass


class ConnectBody(BaseModel):
    provider: str | None = "googlecalendar"


@router.post("/onboarding/connect")
async def connect(body: ConnectBody, user_id: str = Depends(current_user_id)) -> dict:
    """Start an OAuth connection for the user (real Composio). The app opens the
    returned url; on completion the connection.complete webhook auto-runs the
    backfill (and the app can also call /onboarding/run to kick it immediately)."""
    from config import settings

    from backend.integrations.composio_client import ComposioClient

    provider = (body.provider or "googlecalendar").strip()
    try:
        _conn, url = await ComposioClient(
            api_key=settings.composio_api_key or ""
        ).get_or_create_connection(user_id, provider)
    except Exception as exc:
        logger.exception("onboarding/connect failed user=%s provider=%s", user_id[:8], provider)
        return {
            "ok": False, "user_id": user_id, "provider": provider,
            "error": "connect_failed", "detail": f"{type(exc).__name__}: {exc}",
        }
    return {"ok": True, "user_id": user_id, "provider": provider, "url": url}


@router.post("/onboarding/run")
async def run(body: RunBody, user_id: str = Depends(current_user_id)) -> dict:
    from backend.onboarding.service import run_onboarding

    result = await run_onboarding(user_id)
    return {"user_id": user_id, **result}


@router.get("/onboarding/status")
async def status(user_id: str = Depends(current_user_id)) -> dict:
    from backend.onboarding.service import onboarding_status

    return {"user_id": user_id, **await onboarding_status(user_id)}

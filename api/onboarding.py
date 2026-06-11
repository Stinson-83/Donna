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

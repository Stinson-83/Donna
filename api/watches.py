"""App-facing watch endpoint — the dashboard's 'watching' list."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/watches")
async def list_watches(user: str) -> dict:
    from api.push import resolve_user_id
    from backend.proactive.watches import active_watches

    user_id = await resolve_user_id(user)
    return {"user_id": user_id, "watching": await active_watches(user_id)}

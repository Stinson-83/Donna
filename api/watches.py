"""App-facing watch endpoint — the dashboard's 'watching' list."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import current_user_id

router = APIRouter()


@router.get("/watches")
async def list_watches(user_id: str = Depends(current_user_id)) -> dict:
    from backend.proactive.watches import active_watches

    return {"user_id": user_id, "watching": await active_watches(user_id)}

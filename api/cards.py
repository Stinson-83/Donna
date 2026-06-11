"""App-facing card endpoints.

GET  /cards         — the user's active (pending) cards as DonnaCard payloads
POST /cards/action  — resolve a tap; SAME resolver + §10.3 gate as the WhatsApp
                      path (backend.cards.resolution). 'reopen' re-enters the
                      BRAIN loop and returns the freshly rendered card(s).

The app renders DonnaCard payloads natively (block components); the action_map
never ships to the client — only opaque action_ids.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from backend.cards.projection import card_to_app
from db.models import Card
from db.session import async_session

logger = logging.getLogger(__name__)
router = APIRouter()


async def _active_cards(user_id: str) -> list[dict]:
    async with async_session() as s:
        rows = (
            await s.execute(
                select(Card)
                .where(Card.user_id == user_id, Card.state == "pending")
                .order_by(Card.created_at.desc())
            )
        ).scalars().all()
    return [card_to_app(r.payload, r.state) for r in rows]


@router.get("/cards")
async def list_cards(user: str) -> dict:
    from api.push import resolve_user_id

    user_id = await resolve_user_id(user)
    return {"user_id": user_id, "cards": await _active_cards(user_id)}


class CardActionBody(BaseModel):
    user: str
    card_id: str
    action_id: str


@router.post("/cards/action")
async def card_action(body: CardActionBody) -> dict:
    from api.push import resolve_user_id
    from backend.cards.resolution import resolve_card_action

    user_id = await resolve_user_id(body.user)
    res = await resolve_card_action(
        user_id, f"{body.card_id}:{body.action_id}", surface="app"
    )

    if res.status == "reopen":
        from donna_runtime.brain import donna_turn

        state = {
            "user_id": user_id,
            "raw_input": res.reopen_prompt,
            "user_message": res.reopen_prompt,
        }
        try:
            await donna_turn(state)
        except Exception:
            logger.exception("cards: reopen loop failed user=%s", user_id[:8])
        return {"status": "ok", "cards": await _active_cards(user_id)}

    from donna_runtime.tool_logic import render_outbound_text

    messages = [t for m in (res.outbound or []) if (t := render_outbound_text(m))]
    return {
        "status": res.status,
        "messages": messages,
        "cards": await _active_cards(user_id),
    }

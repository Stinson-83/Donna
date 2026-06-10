"""HTTP chat endpoint — drive the Donna brain from any web/app frontend.

This is the demo seam: it runs the exact same pipeline as the WhatsApp webhook
(state_from_payload -> user_lookup -> enrich -> brain.donna_turn) but returns
the outbound bubbles as JSON instead of sending them through Meta. No WhatsApp
token, webhook, or phone number required.

POST /chat
    { "message": "how much did I spend this week", "user": "demo-aarav" }
->
    { "user_id": "<uuid>", "reply": [ {"type":"text","text":"..."}, ... ] }

`user` is any stable string (becomes the user's phone key); reuse the same
value across calls to keep one user's memory/history. Omit it and everyone
shares a single demo user.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from db.models import ChatMessage
from db.session import async_session
from delivery.messages import (
    AudioMessage,
    CTAMessage,
    CTAUrlMessage,
    Delay,
    DocumentMessage,
    ImageMessage,
    ListMessage,
    TextMessage,
    VoiceResponseMarker,
)
from ingress.node import enrich as enrich_state
from ingress.payload import IngressPayload
from api.graph import state_from_payload, user_lookup
from donna_runtime.brain import donna_turn
from donna_runtime.tool_logic import render_outbound_text

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    user: str | None = None


def _serialize(msg) -> dict | None:
    """Turn one OutboundMessage into a JSON bubble the frontend can render."""
    if isinstance(msg, Delay):
        return {"type": "delay", "seconds": msg.seconds}
    if isinstance(msg, VoiceResponseMarker):
        return None
    if isinstance(msg, TextMessage):
        return {"type": "text", "text": msg.body}
    if isinstance(msg, CTAMessage):
        return {
            "type": "cta",
            "text": msg.body,
            "buttons": [{"id": b.id, "title": b.title} for b in msg.buttons],
        }
    if isinstance(msg, CTAUrlMessage):
        return {
            "type": "cta_url",
            "text": msg.body,
            "display_text": msg.display_text,
            "url": msg.url,
        }
    if isinstance(msg, ListMessage):
        return {
            "type": "list",
            "text": msg.body,
            "button_label": msg.button_label,
            "sections": [
                {
                    "title": s.title,
                    "rows": [{"id": r.id, "title": r.title} for r in s.rows],
                }
                for s in msg.sections
            ],
        }
    if isinstance(msg, ImageMessage):
        return {"type": "image", "url": msg.url, "caption": msg.caption}
    if isinstance(msg, AudioMessage):
        return {"type": "audio", "url": msg.url}
    if isinstance(msg, DocumentMessage):
        return {
            "type": "document",
            "url": msg.url,
            "filename": msg.filename,
            "caption": msg.caption,
        }
    return None


async def _save_message(user_id: str, role: str, content: str) -> None:
    if not content:
        return
    try:
        async with async_session() as session:
            session.add(ChatMessage(user_id=user_id, role=role, content=content))
            await session.commit()
    except Exception:
        logger.exception("chat: save %s message failed", role)


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    phone = (req.user or "web-demo").strip() or "web-demo"
    payload = IngressPayload(
        user_id="",
        phone=phone,
        message=req.message,
        message_type="text",
        source="web",
        platform_message_id=f"web-{uuid.uuid4().hex[:16]}",
    )

    state = state_from_payload(payload)
    state = await user_lookup(state)
    state = await enrich_state(state)

    await _save_message(state["user_id"], "user", state.get("raw_input") or "")

    try:
        state = await donna_turn(state)
    except Exception:
        logger.exception("chat: brain failed")
        return {
            "user_id": state.get("user_id", ""),
            "reply": [{"type": "text", "text": "hm, one sec"}],
        }

    outbound = state.get("_outbound") or []
    bubbles = [b for b in (_serialize(m) for m in outbound) if b]

    for m in outbound:
        body = render_outbound_text(m)
        if body:
            await _save_message(state["user_id"], "assistant", body)

    return {"user_id": state["user_id"], "reply": bubbles}

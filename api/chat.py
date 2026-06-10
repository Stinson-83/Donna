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

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
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
from donna_runtime.observability import subscribe_live, unsubscribe_live
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


async def _prepare_state(req: ChatRequest) -> tuple[dict, str]:
    """Shared inbound prep for both /chat and /chat/stream: build the ingress
    state, persist the user message, and feed the cognition layer. Returns the
    enriched state and the stable app id (phone key)."""
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

    # Chat is an ingestion surface — every message can update Donna's model.
    try:
        from backend.cognition.pipeline import ingest as _cog_ingest
        from backend.cognition.store import async_session as _cog_session
        async with _cog_session() as cs:
            # Key cognition on the stable app id (req.user), NOT the resolved
            # UUID — so chat updates the same belief/memory model the Plan /
            # Beliefs / Memory screens read with ?user=<that id>. One identity.
            await _cog_ingest(cs, user_id=phone, content=state.get("raw_input") or "", source_type="donna_app")
            await cs.commit()
    except Exception:
        logger.exception("chat: cognition ingest failed (non-fatal)")

    return state, phone


async def _persist_outbound(user_id: str, outbound: list) -> None:
    for m in outbound:
        body = render_outbound_text(m)
        if body:
            await _save_message(user_id, "assistant", body)


# Map a tool's short name to a one-word status Donna shows while she works. Kept
# in her register: lowercase, blunt, no filler. None = don't surface (terminals,
# silent dashboard writes).
def _status_for_tool(short: str) -> str | None:
    s = short or ""
    if s.startswith(("recall_", "read_", "list_", "search")):
        return "looking that up"
    if s.startswith(("update_living", "add_insight", "flag_")):
        return "noticing something"
    if s.startswith(("update_", "schedule_", "log_")) or s in ("track",):
        return "noting that"
    if s in ("dig_deeper", "compile_brief", "draft_high_stakes_message") or s.startswith("subagent"):
        return "thinking it through"
    return None


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    state, _phone = await _prepare_state(req)

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
    await _persist_outbound(state["user_id"], outbound)

    return {"user_id": state["user_id"], "reply": bubbles}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Streaming twin of /chat over Server-Sent Events.

    Events:
        status — ephemeral "what she's doing" line (thinking / looking that up …)
        bubble — one outbound message, emitted with her real burst pacing
        done   — terminal; carries {user_id}

    The brain runs as a task while we forward its live tool activity, then we
    replay the burst honoring the inter-message delays server-side. Same loop,
    same bubbles as /chat — just delivered progressively.
    """
    state, _phone = await _prepare_state(req)
    user_uuid = state["user_id"]

    async def gen():
        yield _sse("status", {"text": "thinking"})
        queue = subscribe_live()
        brain_task = asyncio.create_task(donna_turn(state))
        seen: set[str] = set()
        try:
            # Forward live tool activity until the loop finishes.
            while not brain_task.done():
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=0.3)
                except asyncio.TimeoutError:
                    continue
                if ev.get("user_id") != user_uuid or ev.get("event") != "tool.call":
                    continue
                text = _status_for_tool(ev.get("tool_short") or "")
                if text and text not in seen:
                    seen.add(text)
                    yield _sse("status", {"text": text})
            await brain_task
        except Exception:
            logger.exception("chat stream: brain failed")
            yield _sse("bubble", {"type": "text", "text": "hm, one sec"})
            yield _sse("done", {"user_id": user_uuid})
            return
        finally:
            unsubscribe_live(queue)

        outbound = state.get("_outbound") or []
        await _persist_outbound(user_uuid, outbound)

        for m in outbound:
            b = _serialize(m)
            if b is None:
                continue
            if b.get("type") == "delay":
                await asyncio.sleep(max(0.4, min(float(b.get("seconds") or 1.0), 3.0)))
                continue
            yield _sse("bubble", b)
        yield _sse("done", {"user_id": user_uuid})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering so events flush
        },
    )

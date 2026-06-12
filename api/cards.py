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


@router.get("/today")
async def today(user: str) -> dict:
    """The Today/Dashboard meta: next-24h calendar (the day rail) + the 'holding'
    count (active watches + pending cards + open loops)."""
    from datetime import timedelta

    from sqlalchemy import func, select

    from api.push import resolve_user_id
    from db.models import CalendarEntry, Card, OpenLoop, Watch, utcnow
    from db.session import async_session

    user_id = await resolve_user_id(user)
    now = utcnow()

    def _t(dt):
        return dt.strftime("%I:%M").lstrip("0")

    async with async_session() as s:
        cal = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.user_id == user_id,
                CalendarEntry.start_time >= now,
                CalendarEntry.start_time <= now + timedelta(hours=24),
            ).order_by(CalendarEntry.start_time).limit(12)
        )).scalars().all()
        n_watch = (await s.execute(select(func.count(Watch.id)).where(Watch.user_id == user_id, Watch.status == "active"))).scalar_one()
        n_card = (await s.execute(select(func.count(Card.id)).where(Card.user_id == user_id, Card.state == "pending"))).scalar_one()
        n_loop = (await s.execute(select(func.count(OpenLoop.id)).where(OpenLoop.user_id == user_id, OpenLoop.status == "active"))).scalar_one()

    return {
        "user_id": user_id,
        "date": now.strftime("%a %d %b"),
        "calendar": [{"time": _t(c.start_time), "title": c.title, "note": c.location or ""} for c in cal],
        "holding": int(n_watch or 0) + int(n_card or 0) + int(n_loop or 0),
    }


@router.get("/history")
async def history(user: str, limit: int = 80) -> dict:
    """The cross-surface message stream (app + WhatsApp), chronological."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import ChatMessage
    from db.session import async_session

    user_id = await resolve_user_id(user)
    async with async_session() as s:
        rows = (await s.execute(
            select(ChatMessage).where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc()).limit(limit)
        )).scalars().all()
    rows = list(reversed(rows))  # chronological (oldest -> newest)

    def _fmt(dt):
        return dt.strftime("%I:%M %p").lstrip("0")

    return {
        "user_id": user_id,
        "messages": [{
            "from": "user" if r.role == "user" else "donna",
            "text": r.content,
            "surface": "whatsapp" if r.wa_message_id else "app",
            "time": _fmt(r.created_at),
            "date": r.created_at.strftime("%a %d %b"),
            "proactive": bool(r.is_proactive),
        } for r in rows],
    }


_CHANNELS = {"auto", "app", "whatsapp"}


class SettingsBody(BaseModel):
    user: str
    notify_channel: str


@router.get("/settings")
async def get_settings(user: str) -> dict:
    """The user's preferences. notify_channel: which surface Donna reaches you on."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import User
    from db.session import async_session

    user_id = await resolve_user_id(user)
    async with async_session() as s:
        u = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    return {"user_id": user_id, "notify_channel": (u.notify_channel if u else "auto") or "auto"}


@router.post("/settings")
async def set_settings(body: SettingsBody) -> dict:
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import User
    from db.session import async_session

    channel = body.notify_channel if body.notify_channel in _CHANNELS else "auto"
    user_id = await resolve_user_id(body.user)
    async with async_session() as s:
        u = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if u is not None:
            u.notify_channel = channel
            await s.commit()
    return {"user_id": user_id, "notify_channel": channel}


@router.get("/library")
async def library(user: str) -> dict:
    """Counts behind the Library drawer: people, documents, trackers (active
    watches), to-dos (open loops), connected accounts."""
    from sqlalchemy import func, select

    from api.push import resolve_user_id
    from db.models import Document, Integration, OpenLoop, User, Watch
    from db.session import async_session

    user_id = await resolve_user_id(user)
    async with async_session() as s:
        u = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        people = 0
        if u is not None and isinstance(u.living_profile, dict):
            people = len((u.living_profile.get("biography") or {}).get("relationships") or [])
        docs = (await s.execute(select(func.count(Document.id)).where(Document.user_id == user_id))).scalar_one()
        trackers = (await s.execute(select(func.count(Watch.id)).where(Watch.user_id == user_id, Watch.status == "active"))).scalar_one()
        todos = (await s.execute(select(func.count(OpenLoop.id)).where(OpenLoop.user_id == user_id, OpenLoop.status == "active"))).scalar_one()
        connected = (await s.execute(select(func.count(Integration.id)).where(Integration.user_id == user_id))).scalar_one()

    return {
        "user_id": user_id,
        "people": int(people or 0),
        "documents": int(docs or 0),
        "trackers": int(trackers or 0),
        "todos": int(todos or 0),
        "connected": int(connected or 0),
    }


@router.get("/library/todos")
async def library_todos(user: str) -> dict:
    """The To-dos detail list: active open loops, deadlined ones first (soonest
    due at the top), then undated by recency."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import OpenLoop, utcnow
    from db.session import async_session

    user_id = await resolve_user_id(user)
    now = utcnow()
    async with async_session() as s:
        rows = (await s.execute(
            select(OpenLoop).where(OpenLoop.user_id == user_id, OpenLoop.status == "active")
            .order_by(OpenLoop.created_at.desc()).limit(100)
        )).scalars().all()

    dated = sorted([r for r in rows if r.due_date], key=lambda r: r.due_date)
    undated = [r for r in rows if not r.due_date]

    def _due(r):
        if not r.due_date:
            return None
        days = (r.due_date.date() - now.date()).days
        if days < 0:
            return f"{-days}d overdue"
        if days == 0:
            return "due today"
        if days == 1:
            return "due tomorrow"
        return f"due in {days}d"

    return {
        "user_id": user_id,
        "todos": [{
            "id": r.id,
            "content": r.content,
            "category": r.category,
            "due": _due(r),
            "overdue": bool(r.due_date and r.due_date.date() < now.date()),
        } for r in dated + undated],
    }


class TodoDoneBody(BaseModel):
    user: str
    id: str


@router.post("/library/todos/done")
async def library_todo_done(body: TodoDoneBody) -> dict:
    """Mark a to-do done. Same settle shape as the close_open_loop tool."""
    from api.push import resolve_user_id
    from db.models import OpenLoop, utcnow
    from db.session import async_session

    user_id = await resolve_user_id(body.user)
    async with async_session() as s:
        loop = await s.get(OpenLoop, body.id)
        if loop is None or loop.user_id != user_id:
            return {"ok": False}
        loop.status = "closed"
        loop.resolved_at = utcnow()
        await s.commit()
    return {"ok": True}


@router.get("/library/trackers")
async def library_trackers(user: str) -> dict:
    """The Trackers detail list: active watches with their cadence + state, most
    important first. A flight watch carries its last-known status."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import Watch
    from db.session import async_session

    user_id = await resolve_user_id(user)
    async with async_session() as s:
        rows = (await s.execute(
            select(Watch).where(Watch.user_id == user_id, Watch.status == "active")
            .order_by(Watch.importance.desc(), Watch.created_at.desc()).limit(100)
        )).scalars().all()

    def _state_note(w):
        st = w.last_known_state or {}
        if w.watch_type == "flight" and st.get("status"):
            return st["status"]
        if w.watch_type == "web" and st.get("seen_urls") is not None:
            return f"{len(st['seen_urls'])} results seen"
        return None

    return {
        "user_id": user_id,
        "trackers": [{
            "id": w.id,
            "type": w.watch_type,
            "title": w.title,
            "subject": w.subject_key,
            "importance": w.importance,
            "deadline": w.deadline.isoformat() if w.deadline else None,
            "last_checked": w.last_checked_at.isoformat() if w.last_checked_at else None,
            "next_check": w.next_check.isoformat() if w.next_check else None,
            "note": _state_note(w),
        } for w in rows],
    }


class TrackerRetireBody(BaseModel):
    user: str
    id: str


@router.post("/library/trackers/retire")
async def library_tracker_retire(body: TrackerRetireBody) -> dict:
    """Stop watching. Uses the watch system's own retire (status flip, no delete)."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from backend.proactive.watches import retire_watch
    from db.models import Watch
    from db.session import async_session

    user_id = await resolve_user_id(body.user)
    async with async_session() as s:
        w = (await s.execute(select(Watch).where(Watch.id == body.id))).scalar_one_or_none()
        if w is None or w.user_id != user_id:
            return {"ok": False}
    await retire_watch(body.id)
    return {"ok": True}


def _added(dt, now) -> str | None:
    if not dt:
        return None
    days = (now.date() - dt.date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days}d ago"
    return dt.strftime("%b %d")


@router.get("/library/people")
async def library_people(user: str) -> dict:
    """The People detail: relationships from the living profile, most important
    first, with whatever Donna knows (relation, email, birthday, a note)."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import User
    from db.session import async_session

    user_id = await resolve_user_id(user)
    async with async_session() as s:
        u = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    rels = []
    if u is not None and isinstance(u.living_profile, dict):
        rels = (u.living_profile.get("biography") or {}).get("relationships") or []

    def _f(r, *keys):
        for k in keys:
            v = r.get(k)
            if v:
                return v
        return None

    people = []
    for r in rels:
        if not isinstance(r, dict):
            continue
        people.append({
            "name": r.get("name") or "someone",
            "relation": _f(r, "relation", "role", "relationship"),
            "email": _f(r, "email", "_email"),
            "birthday": _f(r, "birthday", "birthday_date"),
            "importance": int(r.get("importance") or 0),
            "note": _f(r, "note", "notes", "prefs", "preferences"),
        })
    people.sort(key=lambda p: -p["importance"])
    return {"user_id": user_id, "people": people}


@router.get("/library/documents")
async def library_documents(user: str) -> dict:
    """The Documents detail: files Donna holds, most recent first."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import Document, utcnow
    from db.session import async_session

    user_id = await resolve_user_id(user)
    now = utcnow()
    async with async_session() as s:
        rows = (await s.execute(
            select(Document).where(Document.user_id == user_id)
            .order_by(Document.created_at.desc()).limit(100)
        )).scalars().all()

    def _size(n):
        if not n:
            return None
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n // 1024} KB"
        return f"{n / (1024 * 1024):.1f} MB"

    return {
        "user_id": user_id,
        "documents": [{
            "id": d.id,
            "filename": d.filename,
            "mime": d.mime_type,
            "size": _size(d.file_size_bytes),
            "status": d.processing_status,
            "source": d.source,
            "added": _added(d.created_at, now),
        } for d in rows],
    }


@router.get("/library/connected")
async def library_connected(user: str) -> dict:
    """The Connected detail: integrations and their health (the source of truth is
    the integrations table, per the model)."""
    from sqlalchemy import select

    from api.push import resolve_user_id
    from db.models import Integration, utcnow
    from db.session import async_session

    user_id = await resolve_user_id(user)
    now = utcnow()
    async with async_session() as s:
        rows = (await s.execute(
            select(Integration).where(Integration.user_id == user_id)
            .order_by(Integration.created_at.asc())
        )).scalars().all()

    return {
        "user_id": user_id,
        "connected": [{
            "provider": i.provider,
            "product": i.product,
            "status": i.status,
            "healthy": bool(i.status == "connected" and not i.last_error),
            "synced": _added(i.last_synced_at, now),
            "error": i.last_error,
        } for i in rows],
    }

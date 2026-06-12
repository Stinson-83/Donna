"""Ambient model — the attention ranker behind the Dynamic Watch Bar.

One unified, continuously-reordered "what matters most right now" across the
things Donna is holding: pending decision cards, active watches, and admin tasks
coming due. Each is scored by a single deterministic function — base signal by
kind, a deadline-proximity bump, and a goal-relevance lift (Cap 7) — then sorted
and tiered. No llm; the bar is a live read of Donna's priorities.

This is the general "what matters now" ranking; the Morning Brief composes a
similar set into prose, the Watch Bar renders it as a live strip.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _tier(p: float) -> str:
    if p >= 85:
        return "critical"
    if p >= 65:
        return "high"
    if p >= 45:
        return "medium"
    return "low"


def _proximity_bump(deadline: datetime | None, now: datetime) -> float:
    """Closer deadline -> more attention. Past-due gets the biggest bump."""
    if deadline is None:
        return 0.0
    hours = (deadline - now).total_seconds() / 3600
    if hours < 0:
        return 18.0   # overdue
    if hours <= 24:
        return 15.0
    if hours <= 72:
        return 8.0
    return 0.0


def _parse_iso(s) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except (ValueError, TypeError):
        return None


def _card_title(payload) -> str | None:
    if not isinstance(payload, dict):
        return None
    for b in payload.get("blocks", []):
        if isinstance(b, dict) and b.get("type") == "header":
            return b.get("ref") or b.get("label")
    return None


async def rank_attention(user_id: str, *, now: datetime | None = None, limit: int = 8) -> list[dict]:
    """The ranked attention list for the watch bar. Each item:
    {kind, ref_id, title, note, priority, tier, deadline}."""
    from sqlalchemy import select

    from db.models import Card, utcnow
    from db.session import async_session

    from backend.knowledge.goals import goal_terms, list_active_goals
    from backend.knowledge.tasks import list_due_tasks
    from backend.proactive.watches import active_watches

    now = now or utcnow()

    # goal index once (local matching beats N relevant_goals() queries)
    goals = await list_active_goals(user_id)
    goal_index = [(int(g.priority or 3), goal_terms(g)) for g in goals]

    def _goal_bump(title: str) -> float:
        low = (title or "").lower()
        best = None
        for pri, terms in goal_index:
            if terms and any(t in low for t in terms):
                best = pri if best is None else min(best, pri)
        return 0.0 if best is None else max(5.0, 24.0 - (best - 1) * 5.0)

    raw: list[dict] = []

    async with async_session() as s:
        cards = (await s.execute(
            select(Card).where(Card.user_id == user_id, Card.state == "pending")
            .order_by(Card.created_at.desc()).limit(20)
        )).scalars().all()
    for c in cards:
        base = 88.0 if c.intent == "approval" else 80.0 if c.intent == "heads_up" else 74.0
        raw.append({
            "kind": "card", "ref_id": c.id,
            "title": _card_title(c.payload) or c.intent,
            "note": "needs you", "deadline": c.expires_at,
            "priority": base + _proximity_bump(c.expires_at, now),
        })

    for w in await active_watches(user_id):
        dl = _parse_iso(w.get("deadline"))
        raw.append({
            "kind": "watch", "ref_id": w["id"], "title": w["title"],
            "note": w.get("type"), "deadline": dl,
            "priority": float(w.get("importance") or 50) + _proximity_bump(dl, now),
        })

    for t in await list_due_tasks(user_id, now=now, within_days=7):
        days = (t["due_date"].date() - now.date()).days
        base = 90.0 if days < 0 else 85.0 if days == 0 else 75.0 if days == 1 else 60.0 if days <= 3 else 45.0
        note = "overdue" if days < 0 else "due today" if days == 0 else "due tomorrow" if days == 1 else f"due in {days}d"
        raw.append({
            "kind": "task", "ref_id": t["id"], "title": t["content"],
            "note": note, "deadline": t["due_date"], "priority": base,
        })

    for it in raw:
        it["priority"] = round(min(100.0, it["priority"] + _goal_bump(it["title"])), 1)
        it["tier"] = _tier(it["priority"])
        dl = it["deadline"]
        it["deadline"] = dl.isoformat() if isinstance(dl, datetime) else dl

    raw.sort(key=lambda it: -it["priority"])
    return raw[:limit]

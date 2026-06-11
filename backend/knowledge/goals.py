"""Goals — what the user is trying to achieve (user_model.md Layer 1).

Goals give meaning: the loop prioritizes against active goals. Stored first-class
so they can be listed, ranked, and connected to events. create_or_update matches
on normalized title so repeated mentions strengthen one goal, not spawn dupes.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_CATEGORIES = {"career", "health", "relationships", "financial", "personal", "other"}


def _norm(title: str) -> str:
    return " ".join((title or "").strip().lower().split())


async def create_or_update_goal(
    user_id: str,
    title: str,
    *,
    description: str | None = None,
    category: str = "personal",
    priority: int = 3,
    status: str = "active",
    confidence: float = 0.7,
    source: str = "chat",
) -> str:
    from sqlalchemy import select

    from db.models import Goal
    from db.session import async_session

    title = (title or "").strip()
    if not title:
        return ""
    category = category if category in _CATEGORIES else "personal"
    key = _norm(title)

    async with async_session() as s:
        rows = (await s.execute(
            select(Goal).where(Goal.user_id == user_id, Goal.status != "dropped")
        )).scalars().all()
        existing = next((g for g in rows if _norm(g.title) == key), None)
        if existing is not None:
            existing.title = title
            if description:
                existing.description = description
            existing.category = category
            existing.priority = priority
            existing.status = status
            existing.confidence = max(existing.confidence, confidence)
            await s.commit()
            return existing.id
        g = Goal(
            user_id=user_id, title=title, description=description, category=category,
            priority=priority, status=status, confidence=confidence, source=source,
        )
        s.add(g)
        await s.commit()
        return g.id


async def list_active_goals(user_id: str) -> list:
    from sqlalchemy import select

    from db.models import Goal
    from db.session import async_session

    async with async_session() as s:
        return list((await s.execute(
            select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
            .order_by(Goal.priority.asc(), Goal.created_at.asc())
        )).scalars().all())


async def render_goals_block(user_id: str) -> str:
    """The goals section for the loop's user-model context. Empty if no goals."""
    goals = await list_active_goals(user_id)
    if not goals:
        return ""
    lines = [f"- [{g.category}] {g.title}" + (f" — {g.description}" if g.description else "") for g in goals]
    return "## GOALS (what you're working toward — weigh everything against these)\n" + "\n".join(lines)

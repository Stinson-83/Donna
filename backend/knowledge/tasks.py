"""Capability 11 — Personal Operations (admin tasks / errands).

An admin task — renew a passport, RSVP to a wedding, book a dentist, submit an
application — is an open loop WITH a due_date and a category. Reusing the open-loop
store keeps one to-do list (the same rows the Library drawer counts as "To-dos");
the due_date is what lets Donna surface it ahead of the deadline (the proactive
maybe_surface_due_task check) and prepare it. No new store, no redundancy.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_CATEGORIES = {"renewal", "booking", "rsvp", "form", "application", "admin", "errand"}


async def create_task(
    user_id: str,
    title: str,
    *,
    due: datetime | None = None,
    category: str = "admin",
    source: str | None = None,
) -> str:
    """Track an admin task. Idempotent on exact active content — re-stating a task
    updates its due_date/category instead of duplicating. Returns the loop id."""
    from sqlalchemy import select

    from db.models import OpenLoop
    from db.session import async_session

    title = (title or "").strip()
    if not title:
        raise ValueError("title is required")
    category = (category or "admin").strip().lower()
    if category not in _CATEGORIES:
        category = "admin"

    async with async_session() as s:
        existing = (await s.execute(
            select(OpenLoop).where(
                OpenLoop.user_id == user_id,
                OpenLoop.status == "active",
                OpenLoop.content == title,
            )
        )).scalar_one_or_none()
        if existing is not None:
            if due is not None:
                existing.due_date = due
            existing.category = category
            await s.commit()
            return existing.id

        loop = OpenLoop(
            user_id=user_id, content=title, status="active",
            due_date=due, category=category, source_message=source,
        )
        s.add(loop)
        await s.commit()
        await s.refresh(loop)
        return loop.id


async def list_due_tasks(user_id: str, *, now: datetime | None = None, within_days: int = 14) -> list[dict]:
    """Active tasks with a due_date at or before now+within_days (overdue included),
    soonest first."""
    from sqlalchemy import select

    from db.models import OpenLoop, utcnow
    from db.session import async_session

    now = now or utcnow()
    horizon = now + timedelta(days=within_days)
    async with async_session() as s:
        rows = (await s.execute(
            select(OpenLoop).where(
                OpenLoop.user_id == user_id,
                OpenLoop.status == "active",
                OpenLoop.due_date.is_not(None),
                OpenLoop.due_date <= horizon,
            ).order_by(OpenLoop.due_date.asc())
        )).scalars().all()
    return [
        {"id": r.id, "content": r.content, "due_date": r.due_date, "category": r.category}
        for r in rows
    ]

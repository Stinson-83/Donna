"""Cross-connection — recall_about(entity).

The Cross-Connection "engine" is folded into the BRAIN loop (ADR §6): the loop
connects the dots. This gives it the substrate — one call that gathers, across
every store, what Donna knows about one person or topic: their relationship,
current facts, active open loops, upcoming calendar, and related goals. So when
a birthday, meeting, or reply comes up, the loop can see the whole picture
(birthday + the dinner conflict + 'likes lilies' + 'you call at noon') at once.

Deterministic retrieval, no LLM (the loop does the connecting).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def recall_about(user_id: str, entity: str, *, limit: int = 8) -> str:
    from sqlalchemy import or_, select

    from db.models import CalendarEntry, Fact, Goal, OpenLoop, User, utcnow
    from db.session import async_session

    e = (entity or "").strip()
    if not e:
        return "recall_about: no entity given."
    like = f"%{e}%"
    el = e.lower()
    now = utcnow()

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        rel = None
        if user and isinstance(user.living_profile, dict):
            rels = (user.living_profile.get("biography") or {}).get("relationships") or []
            for r in rels:
                if isinstance(r, dict) and (r.get("name") or "").lower() and (
                    el in (r.get("name") or "").lower() or (r.get("name") or "").lower() in el
                ):
                    rel = r
                    break

        facts = (await s.execute(
            select(Fact).where(
                Fact.user_id == user_id, Fact.subject.ilike(like),
                Fact.t_valid_to.is_(None), Fact.t_recorded_to.is_(None),
            ).limit(limit)
        )).scalars().all()

        loops = (await s.execute(
            select(OpenLoop).where(
                OpenLoop.user_id == user_id, OpenLoop.status == "active",
                OpenLoop.content.ilike(like),
            ).limit(limit)
        )).scalars().all()

        cal = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.user_id == user_id, CalendarEntry.title.ilike(like),
                CalendarEntry.start_time >= now,
            ).order_by(CalendarEntry.start_time).limit(limit)
        )).scalars().all()

        goals = (await s.execute(
            select(Goal).where(
                Goal.user_id == user_id, Goal.status == "active",
                or_(Goal.title.ilike(like), Goal.description.ilike(like)),
            ).limit(limit)
        )).scalars().all()

    sections: list[str] = []
    if rel:
        bits = [f"{k}: {v}" for k, v in rel.items() if k != "source" and v not in (None, "", [])]
        if bits:
            sections.append("relationship — " + ", ".join(bits))
    if facts:
        sections.append("facts:\n" + "\n".join(f"- {f.subject} {f.predicate} {f.object}" for f in facts))
    if loops:
        sections.append("open loops:\n" + "\n".join(f"- {l.content}" for l in loops))
    if cal:
        sections.append("upcoming:\n" + "\n".join(f"- {c.start_time:%a %d %b} · {c.title}" for c in cal))
    if goals:
        sections.append("related goals:\n" + "\n".join(f"- [{g.category}] {g.title}" for g in goals))

    if not sections:
        return f"i don't have anything connected to '{entity}' yet."
    return f"what i know about {entity}:\n" + "\n".join(sections)

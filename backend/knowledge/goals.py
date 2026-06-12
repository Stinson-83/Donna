"""Goals — what the user is trying to achieve (user_model.md Layer 1).

Goals give meaning: the loop prioritizes against active goals. Stored first-class
so they can be listed, ranked, and connected to events. create_or_update matches
on normalized title so repeated mentions strengthen one goal, not spawn dupes.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_CATEGORIES = {"career", "health", "relationships", "financial", "personal", "other"}

# Stopwords stripped from goal text so matching keys on meaningful terms only.
_STOP = {
    "want", "need", "make", "more", "less", "this", "that", "with", "from", "into",
    "have", "your", "their", "about", "before", "after", "than", "then", "some",
    "goal", "goals", "trying", "work", "working", "toward", "towards", "every",
}

# Domain terms a goal's category implies, so a financial goal still matches an
# email about a "series" round even if the title only says "raise funding".
_CATEGORY_SYNONYMS = {
    "financial": {"funding", "investor", "investors", "fundraise", "fundraising",
                  "seed", "series", "venture", "valuation", "runway", "round"},
    "career": {"job", "jobs", "interview", "interviews", "offer", "internship",
               "recruiter", "recruiters", "promotion", "hiring", "role", "application"},
    "health": {"gym", "calorie", "calories", "sleep", "workout", "workouts", "diet",
               "weight", "running", "fitness", "medication"},
}


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 4 and w not in _STOP}


def goal_terms(goal) -> set[str]:
    """The match terms for one goal — significant words from its title/description
    plus the terms its category implies. Accepts a Goal row or a dict."""
    def _get(attr):
        return goal.get(attr) if isinstance(goal, dict) else getattr(goal, attr, None)

    terms = _terms(f"{_get('title') or ''} {_get('description') or ''}")
    terms |= _CATEGORY_SYNONYMS.get((_get("category") or "").lower(), set())
    return terms


async def goal_keywords(user_id: str) -> list[str]:
    """Flattened match terms across all active goals — for the email scorer's
    context. Deterministic, no llm."""
    terms: set[str] = set()
    for g in await list_active_goals(user_id):
        terms |= goal_terms(g)
    return sorted(terms)


async def relevant_goals(user_id: str, text: str) -> list[dict]:
    """Which active goals a piece of text relates to (highest-priority first), so a
    surface can explain 'this matters because of your goal'. Deterministic."""
    low = (text or "").lower()
    out: list[dict] = []
    for g in await list_active_goals(user_id):
        matched = sorted(t for t in goal_terms(g) if t in low)
        if matched:
            out.append({"title": g.title, "priority": g.priority, "category": g.category, "terms": matched})
    out.sort(key=lambda d: d["priority"])  # priority 1 = highest
    return out


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

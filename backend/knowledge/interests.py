"""Interests — durable topics the user wants kept an eye on (a team, a company,
a stock, a hobby). Stored in the living profile; the proactive runner turns each
into a web watch so Donna surfaces genuinely-new developments on her own.
"""
from __future__ import annotations

import copy
import logging

logger = logging.getLogger(__name__)


def _norm(t: str) -> str:
    return " ".join((t or "").strip().lower().split())


async def add_interest(user_id: str, topic: str, *, source: str = "chat") -> bool:
    """Append an interest to living_profile.biography.interests (deduped).
    Returns True if newly added. Deep-copies before mutating so the JSON column
    change is detected (see onboarding.service)."""
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    topic = (topic or "").strip()
    if not topic:
        return False
    key = _norm(topic)

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return False
        profile = copy.deepcopy(user.living_profile) if isinstance(user.living_profile, dict) else {}
        bio = profile.get("biography")
        if not isinstance(bio, dict):
            bio = {}
        interests = bio.get("interests")
        if not isinstance(interests, list):
            interests = []
        for i in interests:
            existing = i.get("topic") if isinstance(i, dict) else str(i)
            if _norm(existing) == key:
                return False
        interests.append({"topic": topic, "source": source})
        bio["interests"] = interests
        profile["biography"] = bio
        user.living_profile = profile
        await s.commit()
        return True


async def list_interests(user_id: str) -> list[str]:
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None or not isinstance(user.living_profile, dict):
            return []
        items = (user.living_profile.get("biography") or {}).get("interests") or []
    out: list[str] = []
    for i in items:
        topic = i.get("topic") if isinstance(i, dict) else str(i)
        if topic:
            out.append(topic)
    return out

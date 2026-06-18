"""Daily situation-brief refresh as a proactive check (throttled ~once/20h).

Wraps refresh_situation_brief_best_effort so the temporal mental model stored in
`users.living_profile.situation_brief` regenerates roughly daily off the proactive
tick — no separate nightly scheduler needed. Self-throttles on the brief's own
`generated_at` (an ISO string). Pure state synthesis; never surfaces to the user.
Merge-safe by construction: synthesize_and_store_temporal_brief only rewrites the
`situation_brief` key, so biography/interests/etc. in living_profile are preserved.

Draws from Supermemory + the knowledge graph + observations, so it produces a brief
even when one source is degraded; a populated FalkorDB makes it richer.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL = timedelta(hours=20)


def _is_fresh(brief: object) -> bool:
    if not isinstance(brief, dict):
        return False
    gen = brief.get("generated_at")
    if not gen:
        return False
    try:
        ts = datetime.fromisoformat(str(gen))
    except ValueError:
        # Unparseable timestamp — treat as fresh so we don't refresh every tick.
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts < _REFRESH_INTERVAL


async def maybe_refresh_situation_brief(user_id: str) -> None:
    """Regenerate the situation brief if the stored one is missing or >20h old."""
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        profile = (
            await s.execute(select(User.living_profile).where(User.id == user_id))
        ).scalar_one_or_none()

    brief = profile.get("situation_brief") if isinstance(profile, dict) else None
    if _is_fresh(brief):
        return

    try:
        from backend.memory.tools.refresh_situation_brief import (
            refresh_situation_brief_best_effort,
        )

        ok = await refresh_situation_brief_best_effort(user_id)
        if ok:
            logger.info("situation_brief: refreshed for user=%s", user_id[:8])
    except Exception:
        logger.exception("situation_brief: refresh failed for user=%s", user_id[:8])

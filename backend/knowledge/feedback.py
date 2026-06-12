"""Capability 20 — learning from feedback.

Every card tap is feedback: acting on a card (execute / reopen / consent) says the
surface was wanted; dismissing or snoozing says it wasn't. The cards table is
already the log — `intent` (what kind) + `state` (acted | dismissed) — so we
aggregate over it instead of keeping a separate store. The signal feeds back into
prioritization two ways: a learned-preferences block the BRAIN loop weighs each
turn, and a concrete dampener that raises the proactive-email bar when the user
keeps dismissing heads-ups. Deterministic; the loop still decides.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_MIN_SAMPLES = 4    # don't "learn" from a handful of taps
_LEAN = 0.5         # |bias| at/above this is a clear preference


def _bias(acted: int, dismissed: int) -> float:
    total = acted + dismissed
    if total < _MIN_SAMPLES:
        return 0.0
    return (acted - dismissed) / total  # [-1, 1]


async def feedback_stats(user_id: str) -> dict[str, dict]:
    """Per-intent counts of acted vs dismissed over the user's resolved cards."""
    from sqlalchemy import func, select

    from db.models import Card
    from db.session import async_session

    async with async_session() as s:
        rows = (await s.execute(
            select(Card.intent, Card.state, func.count(Card.id))
            .where(Card.user_id == user_id, Card.state.in_(("acted", "dismissed")))
            .group_by(Card.intent, Card.state)
        )).all()

    stats: dict[str, dict] = {}
    for intent, state, n in rows:
        d = stats.setdefault(intent or "info", {"acted": 0, "dismissed": 0})
        d[state] = d.get(state, 0) + int(n)
    for d in stats.values():
        d["total"] = d["acted"] + d["dismissed"]
        d["bias"] = _bias(d["acted"], d["dismissed"])
    return stats


async def render_feedback_block(user_id: str) -> str:
    """Learned-preferences section for the loop context. Only emits an intent with
    enough samples AND a clear lean — silent until there's real signal."""
    stats = await feedback_stats(user_id)
    lines: list[str] = []
    for intent, d in sorted(stats.items()):
        if d["total"] < _MIN_SAMPLES:
            continue
        if d["bias"] <= -_LEAN:
            lines.append(
                f"- you usually dismiss {intent} cards ({d['dismissed']}/{d['total']}) — "
                f"only surface {intent} when it's clearly worth interrupting"
            )
        elif d["bias"] >= _LEAN:
            lines.append(
                f"- you usually act on {intent} cards ({d['acted']}/{d['total']}) — keep bringing those"
            )
    if not lines:
        return ""
    return "## LEARNED (from how you've responded so far — weigh these)\n" + "\n".join(lines)


async def email_threshold_bump(user_id: str) -> float:
    """Raise the proactive-email bar when the user keeps dismissing heads-ups (a
    proactive email surfaces as a heads_up card). Only raises, never lowers below
    the default — learning suppresses the unwanted, it never forces more. Max +0.25."""
    stats = await feedback_stats(user_id)
    d = stats.get("heads_up")
    if not d or d["total"] < _MIN_SAMPLES or d["bias"] >= 0:
        return 0.0
    return min(0.25, -d["bias"] * 0.25)  # bias -1 -> +0.25

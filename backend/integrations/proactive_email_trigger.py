"""Single-source proactive trigger: 'important email arrived'.

When a Gmail webhook ingests a row, fan out here. Score → rate-limit →
invoke Donna's brain in mode='proactive' with the email as trigger context.

NOTE: this is one hardcoded producer. The general noticing layer (multi-
source, learning-aware) is a separate spec.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from backend.integrations.composio_client import NormalizedGmailMessage
from backend.integrations.email_importance import (
    ScoringContext,
    score_email,
)
from backend.integrations.proactive_rate_limit import (
    can_fire_proactive,
    record_ping,
)
from db.models import ChatMessage, OpenLoop, User

logger = logging.getLogger(__name__)

THRESHOLD = 0.5


def _session_factory():
    from backend.db.session import async_session

    return async_session


async def _build_scoring_context(user_id: str) -> ScoringContext:
    async with _session_factory()() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        loops = (
            await session.execute(
                select(OpenLoop)
                .where(OpenLoop.user_id == user_id)
                .where(OpenLoop.status == "active")
            )
        ).scalars().all()
        # Fetched but unused for now — sent-folder mirror not in P2.
        _recent_sent = (
            await session.execute(
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(50)
            )
        ).scalars().all()

    biography = (
        (user.living_profile or {}).get("biography", {})
        if user else {}
    )
    relationships = list(biography.get("relationships") or [])

    from backend.knowledge.goals import goal_keywords

    return ScoringContext(
        biography_relationships=relationships,
        open_loop_keywords=[
            (loop.content or "").strip()
            for loop in loops if (loop.content or "").strip()
        ],
        recent_sent_thread_ids=set(),
        goal_keywords=await goal_keywords(user_id),
    )


def _format_trigger_prompt(
    msg: NormalizedGmailMessage, signals: list[str], goal_hint: str | None = None
) -> str:
    body_excerpt = (msg.body_text or msg.snippet or "")[:600]
    goal_line = (
        f"This relates to the user's goal: {goal_hint}. Weigh it in that light and, "
        "if you surface it, say why it matters for that goal.\n"
        if goal_hint else ""
    )
    return (
        "[SYSTEM TRIGGER: proactive_email]\n"
        "A new email arrived that may be worth surfacing to the user. "
        "Decide whether to ping them. If it is not actually surface-worthy on a "
        "second look, stay silent (end with send_burst carrying a single minimal "
        "text).\n\n"
        "If it IS worth interrupting, end the turn with render_card — a heads_up "
        "card:\n"
        "- a one-line body stating the key facts (who, what, any deadline) with "
        "**bold** on the facts (lowercase, no em dashes)\n"
        "- two actions, max: 'Draft a reply' and 'Not now'\n"
        "- action_map: {'<draft action_id>': {'kind': 'reopen', 'prompt': "
        "'draft a reply to this email: <one line on the stance and why>'}, "
        "'<dismiss action_id>': {'kind': 'dismiss'}}\n"
        "- a unique card_id, and expires_at set to any hard deadline in the email\n\n"
        f"From: {msg.from_name or ''} <{msg.from_address}>\n"
        f"Subject: {msg.subject or ''}\n"
        f"Importance signals: {', '.join(signals) or 'none'}\n"
        f"{goal_line}\n"
        f"{body_excerpt}"
    )


async def _invoke_brain(state: dict, config=None) -> dict:
    """Pluggable for tests. In prod, calls donna_runtime.brain.donna_turn."""
    from donna_runtime.brain import donna_turn

    return await donna_turn(state, config)


async def maybe_surface_email(
    user_id: str, msg: NormalizedGmailMessage
) -> None:
    ctx = await _build_scoring_context(user_id)
    score = score_email(msg, ctx)

    # Cap 20: if the user keeps dismissing email heads-ups, raise the bar for them.
    from backend.knowledge.feedback import email_threshold_bump

    threshold = THRESHOLD + await email_threshold_bump(user_id)
    if score.score < threshold:
        return

    decision = await can_fire_proactive(user_id, source="email")
    if not decision.allowed:
        await record_ping(
            user_id,
            "email",
            msg.gmail_message_id,
            suppressed_reason=decision.reason,
        )
        logger.info(
            "proactive_email: suppressed user=%s reason=%s",
            user_id, decision.reason,
        )
        return

    from donna_runtime.config import DonnaAgentConfig

    from backend.knowledge.goals import relevant_goals

    rel = await relevant_goals(user_id, f"{msg.subject or ''} {msg.body_text or msg.snippet or ''}")
    goal_hint = rel[0]["title"] if rel else None

    cfg = DonnaAgentConfig(mode="proactive", user_id=user_id)
    prompt = _format_trigger_prompt(msg, score.signals, goal_hint=goal_hint)
    state = {
        "user_id": user_id,
        # raw_input is what brain.donna_turn reads; user_message is the
        # human-friendly mirror used for tracing + tests.
        "raw_input": prompt,
        "user_message": prompt,
        "trigger": {
            "source": "email",
            "message_ref": msg.gmail_message_id,
            "score": score.score,
            "signals": score.signals,
        },
    }
    try:
        result = await _invoke_brain(state, cfg)
        await record_ping(user_id, "email", msg.gmail_message_id)
        # If Donna chose to surface this (didn't stay_silent), push the bubbles
        # to the app so the user is notified even with the app closed.
        outbound = (result or state).get("_outbound") or []
        if outbound:
            try:
                from backend.integrations.notify import deliver_proactive
                await deliver_proactive(user_id, outbound)
            except Exception:
                logger.exception("proactive_email: deliver failed user=%s", user_id)
    except Exception:
        logger.exception(
            "proactive_email: brain invocation failed user=%s msg=%s",
            user_id, msg.gmail_message_id,
        )

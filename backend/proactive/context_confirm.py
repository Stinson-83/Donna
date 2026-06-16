"""Context Layer slice 3 — the confirmation trigger (§8).

When an INFERRED, SIGNIFICANT context (travel, fundraising, exams, ...) crosses
the confidence threshold, reorganizing the whole system around it is worth ONE
question first. This deterministic check finds that context, dedups (so it asks
at most once per season), and hands a [SYSTEM TRIGGER: context_confirm] stimulus
to the BRAIN loop in mode=proactive. The loop renders a confirmation card; a tap
is resolved deterministically by the confirm_context / decline_context executors,
NO second LLM call. The engine detects; the loop asks; the executor commits.

This is contextual alignment, not mode switching: silence leaves the inferred
weighting in place (ADR §6 / CONTEXT_INTELLIGENCE_ARCHITECTURE §8).
"""
from __future__ import annotations

import logging
from datetime import timedelta, timezone

logger = logging.getLogger(__name__)

_ASK_EVERY = timedelta(days=21)   # don't re-ask the same season inside this window
_WAKE_HOURS = range(8, 22)        # confirmations are low-urgency — daytime only


def _because(kind: str, evidence: dict) -> str:
    """A short, grounded 'why she thinks so' from the evidence — never invented."""
    ev = evidence or {}
    bits = []
    if ev.get("flight_watch"):
        bits.append("a flight you're tracking")
    if ev.get("event"):
        bits.append(f'"{ev["event"]}" on your calendar')
    if ev.get("watch"):
        bits.append(f'a watch you have running ("{ev["watch"]}")')
    if ev.get("email_threads"):
        bits.append(f'{ev["email_threads"]} recent threads in your inbox')
    if ev.get("goal"):
        bits.append(f'your goal "{ev["goal"]}"')
    return ", ".join(bits) if bits else "recent signals"


async def maybe_confirm_context(user_id: str, *, now_utc=None) -> None:
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from db.models import User, utcnow
    from db.session import async_session

    from backend.knowledge.context import confirmable_context, context_phrase

    now = now_utc or utcnow()
    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return
        tz = ZoneInfo(user.timezone or "Asia/Singapore")
        if now.replace(tzinfo=timezone.utc).astimezone(tz).hour not in _WAKE_HOURS:
            return  # no off-hours season questions

    ctx = await confirmable_context(user_id, now=now)
    if ctx is None:
        return

    from backend.proactive.checks import _pinged_since, _run_proactive

    source = f"context_confirm:{ctx.kind}"
    async with async_session() as s:
        if await _pinged_since(s, user_id, source, now - _ASK_EVERY):
            return  # already asked about this season recently — silence holds

    phrase = context_phrase(ctx.kind)
    await _run_proactive(user_id, (
        "[SYSTEM TRIGGER: context_confirm]\n"
        f'it looks like {phrase} right now (inferred from {_because(ctx.kind, ctx.evidence)}). '
        "you've started weighting related things up on your own, but reorganizing the "
        "season around this is worth one check first.\n"
        "render ONE confirmation card (intent=\"confirmation\"): say what you think is "
        "going on in a single line, then ask if she should prioritize it and hold "
        "non-urgent pings. exactly two actions — a yes and a no. wire them in the "
        "action_map as execute actions:\n"
        f'  yes -> {{"kind":"execute","tool":"confirm_context","args":{{"kind":"{ctx.kind}"}}}}\n'
        f'  no  -> {{"kind":"execute","tool":"decline_context","args":{{"kind":"{ctx.kind}"}}}}\n'
        "do not invent specifics you can't see in the evidence above. if it's obviously "
        "not worth asking, stay silent."
    ))

    from backend.integrations.proactive_rate_limit import record_ping

    await record_ping(user_id, source, phrase, at=now)

"""Capability 17 — Cross-Connection, the proactive trigger.

When a calendar event's time shifts materially (calendar sync detects the change),
this walks the connection set (backend.knowledge.connections) and, if the event
actually touches something else, hands an [event_shift] stimulus to the BRAIN loop
in mode=proactive. The loop works out the downstream consequence and proposes ONE
coordinated fix — the "how did she catch that?" moment, made first-class instead of
hoped-for. The engine finds the links; the loop does the reasoning.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_MIN_SHIFT = timedelta(minutes=20)  # ignore trivial nudges
_CAP = 4                            # at most N items per section in the stimulus


def _local(dt: datetime, tz) -> str:
    return dt.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%a %I:%M %p").replace(" 0", " ").lower()


def _render(conns: dict, old_start: datetime, new_start: datetime, tz) -> str:
    anchor = conns["anchor"]
    loc = f" at {anchor['location']}" if anchor.get("location") else ""
    lines = [
        "[SYSTEM TRIGGER: event_shift]",
        f'"{anchor["title"]}" moved from {_local(old_start, tz)} to {_local(new_start, tz)}{loc}.',
        "This may have downstream effects:",
    ]
    for c in conns["conflicts"][:_CAP]:
        lines.append(f'- now clashes with "{c["title"]}" ({_local(c["start"], tz)})')
    for nb in conns["neighbors"][:_CAP]:
        lines.append(f'- close in time: "{nb["title"]}" ({_local(nb["start"], tz)})')
    for re_ev in conns["referential_events"][:_CAP]:
        lines.append(f'- related: "{re_ev["title"]}" ({_local(re_ev["start"], tz)})')
    for loop in conns["open_loops"][:_CAP]:
        lines.append(f'- open commitment: "{loop}"')
    if conns["people"]:
        lines.append(f"- people involved: {', '.join(conns['people'])}")
    lines.append(
        "Work out the real consequence like a chief of staff: who is now affected, "
        "what clashes or no longer makes sense, and propose ONE coordinated fix "
        "(move the pickup and tell them, push the dinner, reschedule the call). "
        "render_card if there's an action to approve, otherwise a tight send_burst. "
        "If nothing here is genuinely affected, stay silent. Never invent details "
        "you did not retrieve."
    )
    return "\n".join(lines)


async def maybe_surface_event_shift(
    user_id: str,
    event_id: str,
    old_start: datetime | None,
    new_start: datetime | None,
    *,
    now_utc: datetime | None = None,
) -> None:
    if old_start is None or new_start is None:
        return
    if abs((new_start - old_start).total_seconds()) < _MIN_SHIFT.total_seconds():
        return  # trivial nudge — not worth a cross-connection pass

    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from db.models import User, utcnow
    from db.session import async_session

    from backend.knowledge.connections import find_connections, has_links

    now = now_utc or utcnow()
    if new_start <= now:
        return  # the event is in the past — nothing to coordinate

    conns = await find_connections(user_id, event_id, also_around=old_start)
    if not has_links(conns):
        return  # a lone shift with nothing connected is not a cross-connection

    new_iso = new_start.replace(microsecond=0).isoformat()
    source = f"shift:{event_id}:{new_iso}"  # re-firing on a NEW time is intended; same time is not

    from backend.proactive.checks import _pinged_since, _run_proactive

    async with async_session() as s:
        if await _pinged_since(s, user_id, source, now - timedelta(days=7)):
            return
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    tz = ZoneInfo((user.timezone if user else None) or "Asia/Singapore")

    await _run_proactive(user_id, _render(conns, old_start, new_start, tz))

    from backend.integrations.proactive_rate_limit import record_ping

    await record_ping(user_id, source, conns["anchor"]["title"], at=now)

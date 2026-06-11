"""Capability 14 — the Preparation Engine ("the closest capability to Donna from
Suits").

Before an event happens, Donna prepares for it. This is a deterministic check on
the proactive tick: it finds the soonest upcoming calendar event the user has not
been prepped for, attaches cheap pointers (when, where, who-you-know), and invokes
the BRAIN loop in mode=proactive to assemble the brief and offer ONE concrete next
action. The reasoning + drafting happen in the loop (the one reasoning site) — this
module only triggers and dedups.

Cadence: an event is prepped once (deduped by a per-event ping), during the user's
waking hours, when it falls inside the lead window — so next-day events get an
evening-before / morning-of brief and same-day events get prepped earlier in the
day. One event per tick to avoid a burst.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_WAKING = range(7, 23)  # local hour 7am..10pm — never prep at 3am


def _when_phrase(start_local: datetime, now_local: datetime) -> str:
    delta_days = (start_local.date() - now_local.date()).days
    t = start_local.strftime("%I:%M %p").lstrip("0").lower()
    if delta_days <= 0:
        return f"today at {t}"
    if delta_days == 1:
        return f"tomorrow at {t}"
    return f"{start_local.strftime('%A')} at {t}"


def _known_people(title: str, location: str | None, relationships: list) -> list[str]:
    """Relationship names that literally appear in the event text — a cheap,
    deterministic match so the loop knows who to recall about. No LLM."""
    hay = f"{title or ''} {location or ''}".lower()
    out = []
    for r in relationships:
        if not isinstance(r, dict):
            continue
        name = (r.get("name") or "").strip()
        if name and name.lower() in hay and name not in out:
            out.append(name)
    return out


async def maybe_prepare_upcoming(
    user_id: str, *, now_utc: datetime | None = None, lead_hours: int = 20
) -> None:
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from db.models import CalendarEntry, User, utcnow
    from db.session import async_session

    from backend.proactive.checks import _pinged_since, _run_proactive

    now = now_utc or utcnow()

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return
        tz = ZoneInfo(user.timezone or "Asia/Singapore")
        now_local = now.replace(tzinfo=timezone.utc).astimezone(tz)
        if now_local.hour not in _WAKING:
            return  # respect sleep — the night-before brief comes in the evening, not at 3am

        profile = user.living_profile if isinstance(user.living_profile, dict) else {}
        relationships = (profile.get("biography") or {}).get("relationships") or []

        rows = (await s.execute(
            select(CalendarEntry)
            .where(
                CalendarEntry.user_id == user_id,
                CalendarEntry.start_time > now,
                CalendarEntry.start_time <= now + timedelta(hours=lead_hours),
            )
            .order_by(CalendarEntry.start_time.asc())
            .limit(10)
        )).scalars().all()

        target = None
        for ev in rows:
            key = ev.google_event_id or ev.id
            # one-shot per event: an event is unique, so any prior prep ping means done
            if await _pinged_since(s, user_id, f"prep:{key}", now - timedelta(days=30)):
                continue
            target = ev
            break

    if target is None:
        return

    key = target.google_event_id or target.id
    start_local = target.start_time.replace(tzinfo=timezone.utc).astimezone(tz)
    when = _when_phrase(start_local, now_local)
    people = _known_people(target.title, target.location, relationships)

    loc_clause = f" at {target.location}" if target.location else ""
    if people:
        who = people[0] if len(people) == 1 else " and ".join(people)
        person_clause = f"It involves {who} — someone you know."
    else:
        who = "the people involved"
        person_clause = ""

    await _run_proactive(user_id, (
        "[SYSTEM TRIGGER: prepare_event]\n"
        f"The user has \"{target.title}\" {when}{loc_clause}. {person_clause}\n"
        "Prepare them for it the way a chief of staff would the evening before or "
        "the morning of. Use your tools to pull only what is relevant: the last "
        f"email thread with {who}, any open loops or commitments tied to this, "
        "documents they will need, and logistics (travel time, conflicts with "
        "other events). Surface a SHORT brief and offer ONE concrete next action — "
        "draft an unanswered reply, attach the document, confirm a detail. Use "
        "render_card when there is a clear action, otherwise a tight send_burst.\n"
        "If there is genuinely nothing worth preparing (a routine block with no "
        "prep value), stay silent. Do not pad. Never invent details you did not "
        "actually retrieve."
    ))

    from backend.integrations.proactive_rate_limit import record_ping

    await record_ping(user_id, f"prep:{key}", target.title)

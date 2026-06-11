"""Capability 17 — Cross-Connection Intelligence (the deterministic engine).

`find_connections` walks an anchor calendar event and returns the things connected
to it across stores — temporal conflicts, near-in-time neighbors, other events or
open loops that share a named entity (the person/place link), and the known people
named in it. Retrieval only — NO llm. This is what turns "a flight moved" into
"the flight moved, so the pickup and the dinner are affected": the engine surfaces
the links, the BRAIN loop reasons the consequence.

Used by the proactive event-shift trigger (backend.proactive.cross_connect) and is
the natural backing for a reactive read_connections tool.
"""
from __future__ import annotations

import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

_DEFAULT_EVENT_MINUTES = 60   # assume a 1h event when end_time is missing
_NEAR_HOURS = 2               # "right around" the anchor counts as a temporal neighbor
_REF_WINDOW_HOURS = 48        # bound the referential (entity-shared) search


def _interval(ev):
    start = ev.start_time
    end = ev.end_time or (start + timedelta(minutes=_DEFAULT_EVENT_MINUTES))
    return start, end


def _entities(title: str | None, location: str | None, relationships: list) -> tuple[list[str], list[str]]:
    """Deterministic entities in the anchor text: known people named in it, plus
    significant location tokens. These are the join keys for referential links."""
    hay = f"{title or ''} {location or ''}".lower()
    people: list[str] = []
    for r in relationships:
        if isinstance(r, dict):
            name = (r.get("name") or "").strip()
            if name and name.lower() in hay and name not in people:
                people.append(name)
    tokens: list[str] = []
    for tok in (location or "").replace(",", " ").split():
        t = tok.strip().lower()
        if len(t) >= 4 and t.isalpha() and t not in tokens:
            tokens.append(t)
    return people, tokens


async def find_connections(
    user_id: str,
    anchor_event_id: str,
    *,
    near_hours: int = _NEAR_HOURS,
    also_around=None,
) -> dict | None:
    """Return the connection set around an anchor event, or None if it's gone.

    {anchor, people, conflicts, neighbors, referential_events, open_loops}
    conflicts overlap the anchor's interval; neighbors sit within near_hours of the
    anchor OR of `also_around` (pass the pre-shift time so things aligned to the old
    slot — the pickup booked for the old landing — still count); referential_* share
    a named entity (person/place) with the anchor.
    """
    from sqlalchemy import select

    from db.models import CalendarEntry, OpenLoop, User
    from db.session import async_session

    async with async_session() as s:
        anchor = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.id == anchor_event_id,
                CalendarEntry.user_id == user_id,
            )
        )).scalar_one_or_none()
        if anchor is None:
            return None

        a_start, a_end = _interval(anchor)
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        prof = user.living_profile if (user and isinstance(user.living_profile, dict)) else {}
        rels = (prof.get("biography") or {}).get("relationships") or []
        people, loc_tokens = _entities(anchor.title, anchor.location, rels)
        terms = [p.lower() for p in people] + loc_tokens

        lo = a_start - timedelta(hours=_REF_WINDOW_HOURS)
        hi = a_end + timedelta(hours=_REF_WINDOW_HOURS)
        evs = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.user_id == user_id,
                CalendarEntry.id != anchor.id,
                CalendarEntry.start_time >= lo,
                CalendarEntry.start_time <= hi,
            ).order_by(CalendarEntry.start_time.asc()).limit(50)
        )).scalars().all()

        conflicts, neighbors, referential = [], [], []
        near = timedelta(hours=near_hours)

        def _is_near(e_start, e_end) -> bool:
            if e_start <= a_end + near and e_end >= a_start - near:
                return True
            if also_around is not None:
                return e_start <= also_around + near and e_end >= also_around - near
            return False

        for ev in evs:
            e_start, e_end = _interval(ev)
            rec = {"id": ev.id, "title": ev.title, "start": ev.start_time, "end": ev.end_time}
            overlap = e_start < a_end and e_end > a_start
            is_near = _is_near(e_start, e_end)
            text = f"{ev.title or ''} {ev.location or ''}".lower()
            shares = bool(terms) and any(t in text for t in terms)
            if overlap:
                conflicts.append(rec)
            elif is_near:
                neighbors.append(rec)
            if shares and not overlap and not is_near:
                referential.append(rec)

        open_loops: list[str] = []
        if terms:
            loops = (await s.execute(
                select(OpenLoop).where(
                    OpenLoop.user_id == user_id,
                    OpenLoop.status == "active",
                ).limit(100)
            )).scalars().all()
            for loop in loops:
                c = (loop.content or "").lower()
                if any(t in c for t in terms):
                    open_loops.append(loop.content)

    return {
        "anchor": {"id": anchor.id, "title": anchor.title, "start": a_start, "end": a_end, "location": anchor.location},
        "people": people,
        "conflicts": conflicts,
        "neighbors": neighbors,
        "referential_events": referential,
        "open_loops": open_loops,
    }


def has_links(conns: dict | None) -> bool:
    """A real cross-connection exists when the anchor touches something else —
    a clash, a near event, an entity-shared event, or an open commitment."""
    if not conns:
        return False
    return bool(
        conns["conflicts"] or conns["neighbors"] or conns["referential_events"] or conns["open_loops"]
    )


async def _resolve_anchor(session, user_id: str, event_query: str, now):
    """Map a natural reference ('flight', 'Raghav demo', '') to an upcoming event:
    the soonest one whose title/location contains a query word, or — with no query
    — the soonest upcoming event. Returns the CalendarEntry or None."""
    import re

    from sqlalchemy import select

    from db.models import CalendarEntry

    tokens = [t for t in re.findall(r"[a-z0-9]+", (event_query or "").lower()) if len(t) >= 3]
    rows = (await session.execute(
        select(CalendarEntry).where(
            CalendarEntry.user_id == user_id,
            CalendarEntry.start_time >= now - timedelta(hours=3),
            CalendarEntry.start_time <= now + timedelta(days=30),
        ).order_by(CalendarEntry.start_time.asc()).limit(60)
    )).scalars().all()
    if not rows:
        return None
    if tokens:
        for ev in rows:
            hay = f"{ev.title or ''} {ev.location or ''}".lower()
            if any(t in hay for t in tokens):
                return ev
        return None  # a reference was given but nothing matched it
    return rows[0]  # no reference -> the next thing on the calendar


async def summarize_connections(user_id: str, event_query: str = "", *, now=None) -> str:
    """Reactive read of what an event touches, rendered for the BRAIN loop. Backs
    the read_connections tool. Retrieval only."""
    from datetime import timezone
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from db.models import User, utcnow
    from db.session import async_session

    now = now or utcnow()
    async with async_session() as s:
        anchor = await _resolve_anchor(s, user_id, event_query, now)
        anchor_id = anchor.id if anchor is not None else None
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        tzname = user.timezone if user else None

    if anchor_id is None:
        if (event_query or "").strip():
            return f"no upcoming event matches '{event_query.strip()}'. check the calendar first."
        return "nothing on the calendar to connect right now."

    tz = ZoneInfo(tzname or "Asia/Singapore")

    def f(dt):
        return dt.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%a %I:%M %p").replace(" 0", " ").lower()

    conns = await find_connections(user_id, anchor_id)
    a = conns["anchor"]
    loc = f", {a['location']}" if a.get("location") else ""
    if not has_links(conns):
        return f'"{a["title"]}" ({f(a["start"])}{loc}) — nothing else on the calendar or your open loops connects to it.'

    lines = [f'connections for "{a["title"]}" ({f(a["start"])}{loc}):']
    for c in conns["conflicts"][:5]:
        lines.append(f"- clashes with: {c['title']} ({f(c['start'])})")
    for n in conns["neighbors"][:5]:
        lines.append(f"- close in time: {n['title']} ({f(n['start'])})")
    for r in conns["referential_events"][:5]:
        lines.append(f"- related (shared person/place): {r['title']} ({f(r['start'])})")
    for loop in conns["open_loops"][:5]:
        lines.append(f"- open commitment: {loop}")
    if conns["people"]:
        lines.append(f"- people involved: {', '.join(conns['people'])}")
    return "\n".join(lines)

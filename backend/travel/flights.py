"""Capability 5 — Travel (flight tracking).

A flight is a `flight` watch: Donna polls the flight's status on the active-watch
cadence (which tightens near departure via the watch deadline), and on a material
change — a delay, a gate change, a cancellation — she surfaces it. Crucially she
surfaces the DOWNSTREAM consequence too: if the flight is on the calendar, the
evaluator updates that event to the new time and reuses the cross-connection engine
(find_connections, old-time-aware) so the airport pickup and the dinner that the
old landing time implied get caught in the same message.

The flight-status DATA SOURCE is a pluggable provider. There's no live aviation API
wired by default (it needs an AeroDataBox / FlightAware key), so get_flight_status
returns None unless a provider is set — the engine is real and general; only the
feed is a swap-in (the same honesty as the action executors). set_flight_provider()
injects a real adapter (or a fixture in tests/demos).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_MATERIAL_MINUTES = 15            # a time move under this isn't worth a buzz
_TERMINAL = {"landed", "cancelled", "diverted"}


# ── status + provider boundary ───────────────────────────────────────────────

@dataclass
class FlightStatus:
    flight_no: str
    date: str
    status: str = "scheduled"     # scheduled | delayed | cancelled | diverted | landed
    sched_dep: datetime | None = None
    est_dep: datetime | None = None
    sched_arr: datetime | None = None
    est_arr: datetime | None = None
    dep_gate: str | None = None
    arr_gate: str | None = None


_PROVIDER = None  # async (flight_no, date_iso) -> FlightStatus | None


def set_flight_provider(fn) -> None:
    """Install the live flight-status adapter (or a fixture). Swap point for
    AeroDataBox/FlightAware — the rest of the engine is provider-agnostic."""
    global _PROVIDER
    _PROVIDER = fn


def reset_flight_provider() -> None:
    global _PROVIDER
    _PROVIDER = None


async def get_flight_status(flight_no: str, date_iso: str) -> FlightStatus | None:
    if _PROVIDER is None:
        return None  # no live feed wired — honest no-op, not a fake "on time"
    try:
        return await _PROVIDER(flight_no, date_iso)
    except Exception:
        logger.exception("get_flight_status: provider failed %s %s", flight_no, date_iso)
        return None


# ── state (de)serialization (last_known_state is JSON) ───────────────────────

def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _dt(s) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _merge_state(prev: dict, cur: FlightStatus) -> dict:
    """Carry identity (flight_no/date/calendar_event_id) forward, refresh status."""
    return {
        "flight_no": prev.get("flight_no") or cur.flight_no,
        "date": prev.get("date") or cur.date,
        "calendar_event_id": prev.get("calendar_event_id"),
        "status": cur.status,
        "sched_dep": _iso(cur.sched_dep),
        "est_dep": _iso(cur.est_dep),
        "sched_arr": _iso(cur.sched_arr),
        "est_arr": _iso(cur.est_arr),
        "dep_gate": cur.dep_gate,
        "arr_gate": cur.arr_gate,
    }


def _eff_dep(cur: FlightStatus) -> datetime | None:
    return cur.est_dep or cur.sched_dep


def _eff_arr(cur: FlightStatus) -> datetime | None:
    return cur.est_arr or cur.sched_arr


def _shift_min(a: datetime | None, b: datetime | None) -> float | None:
    if a is None or b is None:
        return None
    return abs((b - a).total_seconds()) / 60.0


def _changes(prev: dict, cur: FlightStatus, tz) -> list[str]:
    """Human-readable material changes between the stored status and the new one."""
    out: list[str] = []

    prev_dep = _dt(prev.get("est_dep")) or _dt(prev.get("sched_dep"))
    cur_dep = _eff_dep(cur)
    if (m := _shift_min(prev_dep, cur_dep)) is not None and m >= _MATERIAL_MINUTES:
        out.append(f"departure {_fmt(prev_dep, tz)} -> {_fmt(cur_dep, tz)}")

    prev_arr = _dt(prev.get("est_arr")) or _dt(prev.get("sched_arr"))
    cur_arr = _eff_arr(cur)
    if (m := _shift_min(prev_arr, cur_arr)) is not None and m >= _MATERIAL_MINUTES:
        out.append(f"arrival {_fmt(prev_arr, tz)} -> {_fmt(cur_arr, tz)}")

    if cur.dep_gate and cur.dep_gate != prev.get("dep_gate"):
        out.append(f"departure gate {cur.dep_gate}")
    if cur.arr_gate and cur.arr_gate != prev.get("arr_gate"):
        out.append(f"arrival gate {cur.arr_gate}")
    if cur.status in _TERMINAL and prev.get("status") not in _TERMINAL:
        out.append(cur.status)
    return out


# ── timezone formatting ──────────────────────────────────────────────────────

def _fmt(dt: datetime | None, tz) -> str:
    if dt is None:
        return "?"
    return dt.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%a %I:%M %p").replace(" 0", " ").lower()


async def _user_tz(user_id: str):
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    return ZoneInfo((user.timezone if user else None) or "Asia/Singapore")


# ── calendar link + update ───────────────────────────────────────────────────

async def _link_calendar(user_id: str, flight_no: str) -> str | None:
    """Best-effort: a calendar event whose title carries the flight number."""
    from sqlalchemy import select

    from db.models import CalendarEntry, utcnow
    from db.session import async_session

    async with async_session() as s:
        row = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.user_id == user_id,
                CalendarEntry.title.ilike(f"%{flight_no}%"),
                CalendarEntry.start_time >= utcnow() - timedelta(days=1),
            ).order_by(CalendarEntry.start_time.asc()).limit(1)
        )).scalar_one_or_none()
    return row.id if row is not None else None


async def _update_calendar_time(event_id: str, new_start: datetime) -> datetime | None:
    """Move the linked event to new_start (preserving duration). Returns the old
    start, or None if the event is gone / already there."""
    from sqlalchemy import select

    from db.models import CalendarEntry
    from db.session import async_session

    async with async_session() as s:
        ev = (await s.execute(select(CalendarEntry).where(CalendarEntry.id == event_id))).scalar_one_or_none()
        if ev is None or ev.start_time == new_start:
            return None
        old_start = ev.start_time
        duration = (ev.end_time - ev.start_time) if ev.end_time else None
        ev.start_time = new_start
        if duration is not None:
            ev.end_time = new_start + duration
        await s.commit()
    return old_start


def _consequence_lines(conns: dict, tz) -> list[str]:
    lines: list[str] = []
    for c in conns["conflicts"][:4]:
        lines.append(f"- now clashes with \"{c['title']}\" ({_fmt(c['start'], tz)})")
    for n in conns["neighbors"][:4]:
        lines.append(f"- close in time: \"{n['title']}\" ({_fmt(n['start'], tz)})")
    for r in conns["referential_events"][:4]:
        lines.append(f"- related: \"{r['title']}\" ({_fmt(r['start'], tz)})")
    for loop in conns["open_loops"][:4]:
        lines.append(f"- open commitment: \"{loop}\"")
    return lines


# ── tracking + evaluation ────────────────────────────────────────────────────

async def _set_watch_state(watch_id: str, state: dict) -> None:
    from db.models import Watch
    from db.session import async_session

    async with async_session() as s:
        w = await s.get(Watch, watch_id)
        if w is not None:
            w.last_known_state = state
            await s.commit()


async def track_flight(user_id: str, flight_no: str, date_iso: str, *, importance: int = 80) -> str:
    """Start watching a flight. Idempotent on (flight_no, date). Seeds the baseline
    status, links a calendar event by flight number, and sets the watch deadline to
    scheduled departure so the cadence tightens as it approaches."""
    from backend.proactive.watches import create_watch

    flight_no = (flight_no or "").strip().upper()
    date_iso = (date_iso or "").strip()
    if not flight_no or not date_iso:
        raise ValueError("flight_no and date_iso are required")

    cur = await get_flight_status(flight_no, date_iso)
    deadline = cur.sched_dep if cur else None
    watch_id = await create_watch(
        user_id, "flight", f"{flight_no}:{date_iso}",
        title=f"flight {flight_no}", importance=importance, deadline=deadline,
    )

    event_id = await _link_calendar(user_id, flight_no)
    base = {"flight_no": flight_no, "date": date_iso, "calendar_event_id": event_id}
    if cur is not None:
        base = _merge_state(base, cur)
    await _set_watch_state(watch_id, base)
    return watch_id


async def evaluate_flight_watch(watch):
    """Watch evaluator: poll the flight, diff vs last-known, and on a material
    change update the linked calendar event + surface the change with its downstream
    consequences. No data source -> honest no-op. Terminal status -> retire."""
    from backend.knowledge.connections import find_connections

    from backend.proactive.watches import WatchOutcome

    prev = dict(watch.last_known_state or {})
    flight_no = prev.get("flight_no") or (watch.subject_key or "").split(":")[0]
    date_iso = prev.get("date") or (watch.subject_key or ":").split(":", 1)[-1]
    event_id = prev.get("calendar_event_id")

    cur = await get_flight_status(flight_no, date_iso)
    if cur is None:
        return WatchOutcome(surface=False, new_state=prev)  # no live data — keep state

    new_state = _merge_state(prev, cur)

    if "status" not in prev:  # first real reading establishes the baseline (no buzz)
        await _set_watch_state(watch.id, new_state)
        return WatchOutcome(surface=False, new_state=new_state)

    tz = await _user_tz(watch.user_id)
    changes = _changes(prev, cur, tz)
    terminal = cur.status in _TERMINAL
    if not changes:
        return WatchOutcome(surface=False, new_state=new_state, retire=terminal)

    # downstream: move the linked event to the new effective time + walk connections
    cal_note = ""
    consequence_lines: list[str] = []
    new_event_time = _eff_arr(cur) or _eff_dep(cur)
    if event_id and new_event_time is not None:
        old_start = await _update_calendar_time(event_id, new_event_time)
        if old_start is not None:
            conns = await find_connections(watch.user_id, event_id, also_around=old_start)
            a = conns["anchor"]
            cal_note = f'i moved "{a["title"]}" to {_fmt(new_event_time, tz)} on the calendar.'
            consequence_lines = _consequence_lines(conns, tz)

    lines = [
        "[SYSTEM TRIGGER: flight_update]",
        f"Flight {flight_no} ({date_iso}) changed: {'; '.join(changes)}.",
    ]
    if cal_note:
        lines.append(cal_note)
    if consequence_lines:
        lines.append("This affects:")
        lines.extend(consequence_lines)
    lines.append(
        "Tell the user in one short line what changed. If anything downstream is "
        "affected, propose ONE coordinated fix (move the pickup and tell them, push "
        "the dinner). render_card if there's an action to approve, otherwise a tight "
        "send_burst. If it's a small change that doesn't really matter, stay silent. "
        "Never invent details you did not retrieve."
    )

    from backend.integrations.delivery_policy import tier_for_flight

    return WatchOutcome(
        surface=True, new_state=new_state, surface_prompt="\n".join(lines),
        retire=terminal, tier=tier_for_flight(cur.status),
    )

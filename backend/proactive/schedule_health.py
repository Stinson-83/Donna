"""Capability 2 depth — schedule health: conflicts + overload.

Pure deterministic analysis over calendar rows. Two pathologies:

- conflict: two timed events overlap (however that happened — newly booked,
  synced in, or moved; the cross-connection trigger only sees moves).
- overload: a back-to-back run of meetings with no real break (>=4 such events
  chained with gaps under 15 minutes).

maybe_surface_schedule_issue is the tick check: scan the next 48h, surface the
single most pressing issue (conflicts first, soonest first) to the BRAIN loop,
which judges whether it's a REAL problem (an all-day label over sessions inside
it is intentional) and proposes ONE coordinated fix. Each issue surfaces once
(ping key carries the pair + times). Detection has no llm.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_DEFAULT_MINUTES = 60          # an event with no end_time reads as 1h
_ALL_DAY_HOURS = 20            # >=20h long is a day banner, not a meeting — skip
_CHAIN_GAP_MIN = 15            # gaps under this don't count as a break
_CHAIN_LEN = 4                 # this many chained events = overload
_WAKING = range(7, 23)


def _interval(ev) -> tuple[datetime, datetime]:
    start = ev.start_time
    end = ev.end_time or (start + timedelta(minutes=_DEFAULT_MINUTES))
    return start, end


def _is_banner(ev) -> bool:
    start, end = _interval(ev)
    return (end - start) >= timedelta(hours=_ALL_DAY_HOURS)


@dataclass
class Conflict:
    a_id: str
    a_title: str
    b_id: str
    b_title: str
    start: datetime          # when the overlap begins
    overlap_minutes: int


@dataclass
class Overload:
    date: str                # YYYY-MM-DD of the run's start
    titles: list[str]
    start: datetime
    end: datetime
    count: int


def detect_conflicts(events: list) -> list[Conflict]:
    """Overlapping pairs among timed (non-banner) events, soonest first."""
    timed = sorted((e for e in events if not _is_banner(e)), key=lambda e: e.start_time)
    out: list[Conflict] = []
    for i, a in enumerate(timed):
        a_start, a_end = _interval(a)
        for b in timed[i + 1:]:
            b_start, b_end = _interval(b)
            if b_start >= a_end:
                break  # sorted — nothing later can overlap a
            overlap = (min(a_end, b_end) - b_start).total_seconds() / 60
            out.append(Conflict(
                a_id=a.id, a_title=a.title, b_id=b.id, b_title=b.title,
                start=b_start, overlap_minutes=int(overlap),
            ))
    out.sort(key=lambda c: c.start)
    return out


def detect_overload(events: list) -> list[Overload]:
    """Back-to-back runs: >=CHAIN_LEN timed events chained with gaps under
    CHAIN_GAP_MIN minutes — no room to think between them."""
    timed = sorted((e for e in events if not _is_banner(e)), key=lambda e: e.start_time)
    out: list[Overload] = []
    run: list = []
    run_end: datetime | None = None
    for ev in timed + [None]:  # sentinel flushes the last run
        if ev is not None and run_end is not None:
            gap = (ev.start_time - run_end).total_seconds() / 60
        else:
            gap = None
        if ev is not None and (not run or (gap is not None and gap < _CHAIN_GAP_MIN)):
            run.append(ev)
            run_end = max(run_end or _interval(ev)[1], _interval(ev)[1])
            continue
        if len(run) >= _CHAIN_LEN:
            out.append(Overload(
                date=run[0].start_time.strftime("%Y-%m-%d"),
                titles=[e.title for e in run],
                start=run[0].start_time,
                end=run_end,
                count=len(run),
            ))
        run = [ev] if ev is not None else []
        run_end = _interval(ev)[1] if ev is not None else None
    return out


# ── the tick check ───────────────────────────────────────────────────────────

def _fmt(dt: datetime, tz) -> str:
    return dt.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%a %I:%M %p").replace(" 0", " ").lower()


async def maybe_surface_schedule_issue(
    user_id: str, *, now_utc: datetime | None = None, window_hours: int = 48
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
        if now.replace(tzinfo=timezone.utc).astimezone(tz).hour not in _WAKING:
            return

        events = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.user_id == user_id,
                CalendarEntry.start_time >= now,
                CalendarEntry.start_time <= now + timedelta(hours=window_hours),
            ).order_by(CalendarEntry.start_time.asc()).limit(60)
        )).scalars().all()
    if len(events) < 2:
        return

    conflicts = detect_conflicts(list(events))
    overloads = detect_overload(list(events))

    # pick the most pressing un-pinged issue: clashes first, soonest first
    target_prompt = None
    target_key = None
    async with async_session() as s:
        for c in conflicts:
            key = f"schedclash:{min(c.a_id, c.b_id)}:{max(c.a_id, c.b_id)}:{c.start.isoformat()}"
            if await _pinged_since(s, user_id, key, now - timedelta(days=7)):
                continue
            target_key = key
            target_prompt = (
                "[SYSTEM TRIGGER: schedule_conflict]\n"
                f'"{c.a_title}" and "{c.b_title}" overlap by {c.overlap_minutes} '
                f"minutes (clash starts {_fmt(c.start, tz)}).\n"
                "Judge whether this is a REAL clash (sessions inside a conference "
                "block, a hold, or a deliberate double-book are not). If real, one "
                "short line and ONE coordinated fix — which one to move and where, "
                "via render_card with the proposal or a tight send_burst. If it "
                "looks intentional, stay silent."
            )
            break
        if target_prompt is None:
            for o in overloads:
                key = f"schedload:{o.date}:{o.count}"
                if await _pinged_since(s, user_id, key, now - timedelta(days=2)):
                    continue
                target_key = key
                target_prompt = (
                    "[SYSTEM TRIGGER: schedule_overload]\n"
                    f"{o.count} meetings back-to-back with no real break, "
                    f"{_fmt(o.start, tz)} to {_fmt(o.end, tz)}: "
                    + "; ".join(o.titles[:6]) + ".\n"
                    "If this looks like a rough stretch rather than a deliberate "
                    "sprint, say so in one short line and offer ONE fix — a break "
                    "after a specific meeting, or moving the most movable one. "
                    "Stay silent if it's clearly fine for them."
                )
                break
    if target_prompt is None:
        return

    await _run_proactive(user_id, target_prompt)

    from backend.integrations.proactive_rate_limit import record_ping

    await record_ping(user_id, target_key, "schedule", at=now)

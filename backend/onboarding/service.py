"""Onboarding backfill (onboarding.md, baseline).

run_onboarding(user_id) pulls the user's Google Calendar (real, via Composio)
into calendar entries, derives their key relationships from calendar attendees +
already-stored email senders (frequency-ranked), merges those into the living
profile WITHOUT clobbering anything already there, and marks onboarding complete.

Idempotent — safe to re-run (calendar upserts by event id; relationships merge by
name). No LLM here; the goal/identity distillation passes are the refinement.
"""
from __future__ import annotations

import copy
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_BACKFILL_PAST_DAYS = 30
_BACKFILL_FUTURE_DAYS = 90
_MAX_RELATIONSHIPS = 15


async def run_onboarding(user_id: str) -> dict:
    events = await _list_calendar(user_id)
    n_events = 0
    for ev in events:
        try:
            if await _upsert_calendar_entry(user_id, ev):
                n_events += 1
        except Exception:
            logger.exception("onboarding: calendar upsert failed user=%s", user_id[:8])
    n_rel = await _seed_relationships(user_id, events)
    await _mark_complete(user_id)
    logger.info(
        "onboarding: user=%s calendar=%d relationships=%d", user_id[:8], n_events, n_rel
    )
    return {"events": n_events, "relationships": n_rel, "status": "complete"}


# ── calendar ─────────────────────────────────────────────────────────────

async def _list_calendar(user_id: str) -> list[dict]:
    from config import settings

    from db.models import utcnow
    from backend.integrations.composio_client import ComposioClient

    now = utcnow()
    try:
        return await ComposioClient(api_key=settings.composio_api_key or "").list_calendar_events(
            user_id,
            time_min=now - timedelta(days=_BACKFILL_PAST_DAYS),
            time_max=now + timedelta(days=_BACKFILL_FUTURE_DAYS),
        )
    except Exception:
        logger.exception("onboarding: calendar list failed user=%s", user_id[:8])
        return []


def _parse_dt(node) -> datetime | None:
    if not isinstance(node, dict):
        return None
    raw = node.get("dateTime") or node.get("date")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def _upsert_calendar_entry(user_id: str, ev: dict) -> bool:
    from sqlalchemy import select

    from db.models import CalendarEntry
    from db.session import async_session

    start = _parse_dt(ev.get("start"))
    if start is None:
        return False
    gid = ev.get("id")
    title = ev.get("summary") or "(no title)"
    end = _parse_dt(ev.get("end"))
    location = ev.get("location")

    async with async_session() as s:
        existing = None
        if gid:
            existing = (await s.execute(
                select(CalendarEntry).where(
                    CalendarEntry.user_id == user_id,
                    CalendarEntry.google_event_id == gid,
                )
            )).scalar_one_or_none()
        if existing:
            existing.title, existing.start_time = title, start
            existing.end_time, existing.location = end, location
        else:
            s.add(CalendarEntry(
                user_id=user_id, title=title, start_time=start, end_time=end,
                location=location, google_event_id=gid,
            ))
        await s.commit()
    return True


# ── relationships ────────────────────────────────────────────────────────

def _is_real_person(email: str) -> bool:
    return bool(email) and "noreply" not in email and "no-reply" not in email and "@" in email


async def _seed_relationships(user_id: str, events: list[dict]) -> int:
    from sqlalchemy import select

    from db.models import EmailMessage, User
    from db.session import async_session

    counts: Counter[str] = Counter()
    names: dict[str, str] = {}

    for ev in events:
        for att in ev.get("attendees") or []:
            if not isinstance(att, dict) or att.get("self"):
                continue
            email = (att.get("email") or "").strip().lower()
            if not _is_real_person(email):
                continue
            counts[email] += 1
            if att.get("displayName"):
                names[email] = att["displayName"]

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return 0
        rows = (await s.execute(
            select(EmailMessage.from_address, EmailMessage.from_name)
            .where(EmailMessage.user_id == user_id).limit(500)
        )).all()
        for addr, nm in rows:
            email = (addr or "").strip().lower()
            if not _is_real_person(email):
                continue
            counts[email] += 1
            if nm and email not in names:
                names[email] = nm

        if not counts:
            return 0

        # Deep-copy so we don't mutate the loaded (committed) state in place —
        # otherwise SQLAlchemy can't tell the JSON column changed and skips the
        # UPDATE. We reassign user.living_profile to this fresh object at the end.
        profile = copy.deepcopy(user.living_profile) if isinstance(user.living_profile, dict) else {}
        bio = profile.get("biography")
        if not isinstance(bio, dict):
            bio = {}
        existing = bio.get("relationships")
        if not isinstance(existing, list):
            existing = []
        by_name = {
            (r.get("name") or "").strip().lower(): r
            for r in existing if isinstance(r, dict)
        }

        top = counts.most_common(_MAX_RELATIONSHIPS)
        for email, c in top:
            display = names.get(email) or email.split("@")[0]
            importance = min(100, 30 + c * 8)
            r = by_name.get(display.strip().lower())
            if r is not None:
                r["interaction_count"] = c
                r["importance"] = max(int(r.get("importance") or 0), importance)
                r.setdefault("email", email)
            else:
                new = {
                    "name": display, "email": email, "importance": importance,
                    "interaction_count": c, "source": "onboarding_backfill",
                }
                existing.append(new)
                by_name[display.strip().lower()] = new

        bio["relationships"] = existing
        profile["biography"] = bio
        user.living_profile = profile
        await s.commit()
        return len(top)


# ── state ────────────────────────────────────────────────────────────────

async def _mark_complete(user_id: str) -> None:
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return
        user.onboarding_complete = True
        goals = dict(user.onboarding_goals or {})
        goals["backfill_done"] = True
        user.onboarding_goals = goals
        await s.commit()


async def onboarding_status(user_id: str) -> dict:
    from sqlalchemy import func, select

    from db.models import CalendarEntry, User
    from db.session import async_session

    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return {"complete": False, "relationships": 0, "calendar_events": 0}
        profile = user.living_profile if isinstance(user.living_profile, dict) else {}
        rels = (profile.get("biography") or {}).get("relationships") or []
        n_cal = (await s.execute(
            select(func.count(CalendarEntry.id)).where(CalendarEntry.user_id == user_id)
        )).scalar_one()
        return {
            "complete": bool(user.onboarding_complete),
            "relationships": len(rels),
            "calendar_events": int(n_cal or 0),
        }

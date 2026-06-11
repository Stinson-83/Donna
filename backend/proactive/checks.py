"""Baseline proactive checks for the runner: meal check-in (M4) + birthday
cross-connection (M7).

Each is deterministic until it decides to surface, then invokes the loop in
mode=proactive (gated by the per-(user,source) rate-limit / ping dedup). Kept
deliberately simple — refine cadence + data sources as real usage shows.
Email/finance live in their own trigger modules.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_MEAL_WINDOWS = {"lunch": range(12, 15), "dinner": range(19, 22)}


async def _invoke_brain(state: dict, config=None) -> dict:
    """Pluggable for tests. In prod, calls donna_runtime.brain.donna_turn."""
    from donna_runtime.brain import donna_turn

    return await donna_turn(state, config)


async def _run_proactive(user_id: str, prompt: str) -> None:
    from donna_runtime.config import DonnaAgentConfig

    cfg = DonnaAgentConfig(mode="proactive", user_id=user_id)
    state = {"user_id": user_id, "raw_input": prompt, "user_message": prompt}
    result = await _invoke_brain(state, cfg)
    outbound = (result or state).get("_outbound") or []
    if outbound:
        try:
            from backend.integrations.push import notify_outbound

            await notify_outbound(user_id, outbound)
        except Exception:
            logger.exception("proactive: push failed user=%s", user_id[:8])


# ── M4: meal check-in ────────────────────────────────────────────────────

def _meal_for_hour(hour: int) -> str | None:
    return next((m for m, hrs in _MEAL_WINDOWS.items() if hour in hrs), None)


async def maybe_checkin_meal(user_id: str, *, now_utc: datetime | None = None) -> None:
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from db.models import Observation, ProactivePing, User, utcnow
    from db.session import async_session

    now = now_utc or utcnow()
    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return
        tz = ZoneInfo(user.timezone or "Asia/Singapore")
        now_local = now.replace(tzinfo=timezone.utc).astimezone(tz)
        meal = _meal_for_hour(now_local.hour)
        if meal is None:
            return

        # asked in the last 4h? don't nag.
        if await _pinged_since(s, user_id, "meal_checkin", now - timedelta(hours=4)):
            return
        # already logged a meal in the last 3h? they don't need the nudge.
        meal_cutoff = now - timedelta(hours=3)
        logged = (await s.execute(
            select(Observation.id).where(
                Observation.user_id == user_id,
                Observation.type == "meal",
                Observation.created_at >= meal_cutoff,
            ).limit(1)
        )).scalar_one_or_none()
        if logged:
            return

    await _run_proactive(user_id, (
        "[SYSTEM TRIGGER: meal_checkin]\n"
        f"It's around {meal} time for the user. Ask, in one short line, what they "
        f"had for {meal} so you can log it. When they reply, log the meal (with a "
        "calorie estimate) and tell them the day's running total against their "
        "goal, offering a lighter option if they are over. Stay silent "
        "(send_burst minimal) if it is clearly a bad moment."
    ))
    from backend.integrations.proactive_rate_limit import record_ping

    await record_ping(user_id, "meal_checkin", meal)


# ── M7: birthday cross-connection ────────────────────────────────────────

def _parse_bday(raw) -> tuple[int, int] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    nums = [int(p) for p in raw.strip().replace("/", "-").split("-") if p.isdigit()]
    if len(nums) == 3:   # YYYY-MM-DD
        return (nums[1], nums[2])
    if len(nums) == 2:   # MM-DD
        return (nums[0], nums[1])
    return None


def _days_until(md: tuple[int, int], now: datetime) -> int | None:
    month, day = md
    today = now.date()
    try:
        this_year = date(today.year, month, day)
    except ValueError:
        return None
    target = this_year if this_year >= today else date(today.year + 1, month, day)
    return (target - today).days


async def maybe_surface_birthday(user_id: str, *, now_utc: datetime | None = None, lead_days: int = 3) -> None:
    from sqlalchemy import select

    from db.models import ProactivePing, User, utcnow
    from db.session import async_session

    now = now_utc or utcnow()
    target = None
    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return
        profile = user.living_profile if isinstance(user.living_profile, dict) else {}
        rels = (profile.get("biography") or {}).get("relationships") or []
        for r in rels:
            if not isinstance(r, dict):
                continue
            md = _parse_bday(r.get("birthday") or r.get("birthday_date"))
            if md is None:
                continue
            days = _days_until(md, now)
            if days is None or days < 0 or days > lead_days:
                continue
            name = (r.get("name") or "someone").strip()
            if await _pinged_since(s, user_id, f"birthday_{name.lower()}", now - timedelta(days=7)):
                continue
            target = (name, days)
            break
    if target is None:
        return

    name, days = target
    await _run_proactive(user_id, (
        "[SYSTEM TRIGGER: birthday_approaching]\n"
        f"{name}'s birthday is in {days} day(s). Surface it as a cross-connection: "
        "recall what they like (gifts, flowers, preferences) and any plans or "
        "calendar conflicts that week, then offer ONE concrete action — order a "
        "gift/flowers, or schedule a call/reminder. An approval card or a short "
        "burst. Stay silent if it is not worth interrupting."
    ))
    from backend.integrations.proactive_rate_limit import record_ping

    await record_ping(user_id, f"birthday_{name.lower()}", name)


# ── shared ────────────────────────────────────────────────────────────────

async def _pinged_since(session, user_id: str, source: str, cutoff: datetime) -> bool:
    from sqlalchemy import select

    from db.models import ProactivePing

    row = (await session.execute(
        select(ProactivePing.id).where(
            ProactivePing.user_id == user_id,
            ProactivePing.source == source,
            ProactivePing.fired_at >= cutoff,
        ).limit(1)
    )).scalar_one_or_none()
    return row is not None

"""Ambient model — the Morning Brief ("every day begins with Donna").

Once a day, in the user's morning, Donna composes the top things that matter into
ONE delivery: "good morning. three things matter today...". This is not a new
detector — it COMPOSES the ones already built (finance shortfall + waste, schedule
conflicts, due tasks, active watches), ranks them deterministically (goal-weighted),
and hands the top few to the BRAIN loop to write in her voice. No llm in collection
or ranking; the loop only phrases + delivers.

Gated to a morning window in the user's timezone and deduped to once per local day.
The brief is a digest that points at what matters and asks what to handle first; the
actionable L0/L1 cards still arrive through their own gated paths when JIT-appropriate.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_MORNING = range(7, 11)   # local hour 7-10am
_MAX_ITEMS = 6            # hand at most this many to the loop; it leads with the top ~3
_WATCH_FLOOR = 70         # only surface genuinely-important active watches in the brief


@dataclass
class BriefItem:
    kind: str
    importance: float
    summary: str


async def collect_brief_items(user_id: str, *, now: datetime, tz) -> list[BriefItem]:
    """Gather + rank what matters this morning across the existing detectors.
    Deterministic — DB reads only, no llm."""
    from sqlalchemy import select

    from db.models import Bill, CalendarEntry, FinanceAccount, FinanceTransaction
    from db.session import async_session

    from backend.finance.detector import detect_low_balance_vs_bill
    from backend.finance.waste import detect_waste
    from backend.knowledge.tasks import list_due_tasks
    from backend.proactive.schedule_health import detect_conflicts
    from backend.proactive.watches import active_watches

    local_today = now.replace(tzinfo=timezone.utc).astimezone(tz).date()

    async with async_session() as s:
        accounts = (await s.execute(
            select(FinanceAccount).where(FinanceAccount.user_id == user_id)
        )).scalars().all()
        bills = (await s.execute(
            select(Bill).where(Bill.user_id == user_id, Bill.status == "upcoming")
        )).scalars().all()
        txns = (await s.execute(
            select(FinanceTransaction).where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.occurred_at >= now - timedelta(days=120),
            )
        )).scalars().all()
        events = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.user_id == user_id,
                CalendarEntry.start_time >= now,
                CalendarEntry.start_time <= now + timedelta(hours=36),
            ).order_by(CalendarEntry.start_time.asc())
        )).scalars().all()

    items: list[BriefItem] = []

    # a bill about to bounce — highest signal (risk + money)
    for sf in detect_low_balance_vs_bill(list(accounts), list(bills), now=now):
        items.append(BriefItem(
            "finance_shortfall", 90 + max(0, 7 - sf.days_until_due),
            f"{sf.biller} {sf.currency} {sf.bill_amount:,.0f} auto-debits in "
            f"{sf.days_until_due}d, you're {sf.currency} {sf.shortfall:,.0f} short",
        ))

    # a clash on today's calendar
    todays = [
        e for e in events
        if e.start_time.replace(tzinfo=timezone.utc).astimezone(tz).date() == local_today
    ]
    for c in detect_conflicts(todays)[:2]:
        items.append(BriefItem("schedule_conflict", 76, f'"{c.a_title}" and "{c.b_title}" clash today'))

    # admin tasks coming due
    for t in (await list_due_tasks(user_id, now=now, within_days=3))[:3]:
        days = (t["due_date"].date() - now.date()).days
        when = "overdue" if days < 0 else "today" if days == 0 else "tomorrow" if days == 1 else f"in {days}d"
        items.append(BriefItem("due_task", 72 if days <= 1 else 56, f"{t['content']} — due {when}"))

    # the most important things she's watching
    for w in (await active_watches(user_id))[:4]:
        if w["importance"] >= _WATCH_FLOOR:
            items.append(BriefItem("watch", min(85.0, float(w["importance"])), f"watching: {w['title']}"))

    # money quietly leaking — lower priority, included if there's room
    waste = detect_waste(list(txns), now=now)
    if waste:
        items.append(BriefItem("finance_waste", 46, waste[0].summary))

    # goals lift what relates to them (Cap 7, same signal as everywhere else)
    from backend.knowledge.goals import relevant_goals

    for it in items:
        rel = await relevant_goals(user_id, it.summary)
        if rel:
            it.importance += max(6, 30 - (int(rel[0]["priority"] or 3) - 1) * 6)

    items.sort(key=lambda it: -it.importance)
    return items


async def _invoke_brain(state: dict, config=None) -> dict:
    """Pluggable for tests. In prod, calls donna_runtime.brain.donna_turn."""
    from donna_runtime.brain import donna_turn

    return await donna_turn(state, config)


async def maybe_send_morning_brief(user_id: str, *, now_utc: datetime | None = None) -> None:
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from db.models import User, utcnow
    from db.session import async_session

    from backend.proactive.checks import _pinged_since

    now = now_utc or utcnow()
    async with async_session() as s:
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            return
        tz = ZoneInfo(user.timezone or "Asia/Singapore")
        local = now.replace(tzinfo=timezone.utc).astimezone(tz)
        if local.hour not in _MORNING:
            return
        source = f"morning_brief:{local.date().isoformat()}"
        if await _pinged_since(s, user_id, source, now - timedelta(hours=20)):
            return  # already briefed today

    items = await collect_brief_items(user_id, now=now, tz=tz)
    if not items:
        return  # nothing worth a brief — silence beats an empty "all clear" every day

    top = items[:_MAX_ITEMS]
    listing = "\n".join(f"{i + 1}. {it.summary}" for i, it in enumerate(top))
    prompt = (
        "[SYSTEM TRIGGER: morning_brief]\n"
        f"It's the start of the user's day ({local.strftime('%A')} morning). What "
        f"matters, most important first:\n{listing}\n\n"
        "Deliver a short morning brief in your voice: open with 'good morning', "
        "then the top few that genuinely matter (aim for three, fewer if only one "
        "or two are real), each as one short line, and end by asking which to "
        "handle first. Lowercase, no filler, no em dashes. Lead with what matters "
        "most — do not just list everything. If something is clearly stale or not "
        "worth raising, drop it."
    )

    from backend.proactive.checks import _run_proactive

    await _run_proactive(user_id, prompt)

    from backend.integrations.proactive_rate_limit import record_ping

    await record_ping(user_id, source, "brief", at=now)

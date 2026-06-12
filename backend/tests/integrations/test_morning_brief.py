"""Ambient model — the Morning Brief.

Composes the existing detectors into one ranked daily delivery. Covers the
deterministic collector (gather + rank, money-risk over admin), and the once-a-day
check: fires in the morning window, dedups per local day, silent off-window and on
an empty day.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from db.models import Bill, FinanceAccount, OpenLoop, User

DAY = datetime(2026, 8, 25)  # a Tuesday, future relative to the test clock
UTC = ZoneInfo("UTC")


def _at(h, m=0):
    return DAY.replace(hour=h, minute=m)


async def _seed(db):
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.timezone = "UTC"
        acct = FinanceAccount(user_id="u1", account_type="current", institution="hdfc", balance=43000)
        s.add(acct)
        await s.flush()
        s.add_all([
            Bill(user_id="u1", account_id=acct.id, biller="AWS", amount=47200,
                 due_date=_at(8) + timedelta(days=1), auto_pay=True, status="upcoming"),
            OpenLoop(user_id="u1", content="renew passport", status="active",
                     due_date=_at(8) + timedelta(days=2), category="renewal"),
        ])
        await s.commit()


# ── collector ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_collect_ranks_money_risk_first(db):
    from backend.proactive.morning_brief import collect_brief_items

    await _seed(db)
    items = await collect_brief_items("u1", now=_at(8), tz=UTC)

    kinds = [it.kind for it in items]
    assert "finance_shortfall" in kinds and "due_task" in kinds
    assert items[0].kind == "finance_shortfall"           # bill-about-to-bounce leads
    assert "AWS" in items[0].summary


@pytest.mark.asyncio
async def test_collect_empty_when_nothing_matters(db):
    from backend.proactive.morning_brief import collect_brief_items

    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u2"))).scalar_one()
        u.timezone = "UTC"
        await s.commit()

    assert await collect_brief_items("u2", now=_at(8), tz=UTC) == []


# ── the daily check ──────────────────────────────────────────────────────────

def _stub_brain(monkeypatch):
    import backend.proactive.checks as checks
    prompts: list[str] = []

    async def fake_brain(state, config=None):
        prompts.append(state["raw_input"])
        state["_outbound"] = []
        return state

    monkeypatch.setattr(checks, "_invoke_brain", fake_brain)
    return prompts


@pytest.mark.asyncio
async def test_brief_fires_once_in_the_morning(db, monkeypatch):
    from backend.proactive.morning_brief import maybe_send_morning_brief

    await _seed(db)
    prompts = _stub_brain(monkeypatch)

    # 4am local -> outside the morning window, silent
    await maybe_send_morning_brief("u1", now_utc=_at(4))
    assert prompts == []

    # 8am -> the brief, composing the shortfall + the task
    await maybe_send_morning_brief("u1", now_utc=_at(8))
    assert len(prompts) == 1
    assert "morning_brief" in prompts[0]
    assert "AWS" in prompts[0] and "renew passport" in prompts[0]

    # later the same morning -> already briefed, no repeat
    await maybe_send_morning_brief("u1", now_utc=_at(9, 30))
    assert len(prompts) == 1


@pytest.mark.asyncio
async def test_no_brief_on_an_empty_day(db, monkeypatch):
    from backend.proactive.morning_brief import maybe_send_morning_brief

    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u2"))).scalar_one()
        u.timezone = "UTC"
        await s.commit()
    prompts = _stub_brain(monkeypatch)

    await maybe_send_morning_brief("u2", now_utc=_at(8))
    assert prompts == []  # nothing matters -> no empty "all clear" ping

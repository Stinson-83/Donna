"""demo_seed.py — verify the seed populates the runtime state so every
DEMO_VIDEO_PLAN.md moment can occur, and that the key engines are READY over it.

Runs against the in-memory db fixture; the cognition store (separate) is stubbed.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

import demo_seed
from db.models import (Bill, CalendarEntry, Context, DeviceToken, EmailMessage,
                       FinanceAccount, Goal, Observation, OpenLoop, ProactivePing, User, Watch)

NOW = datetime(2026, 4, 18, 7, 30, 0)
UID = "demo-mira"


@pytest.fixture
def seeded(db, monkeypatch):
    async def _no_cognition(user_id, now):
        return {"beliefs": 0, "memories": 0}
    monkeypatch.setattr(demo_seed, "_cognition", _no_cognition)
    return None


async def _count(db, model, **where):
    async with db() as s:
        q = select(func.count(model.id)).where(model.user_id == UID)
        for k, v in where.items():
            q = q.where(getattr(model, k) == v)
        return (await s.execute(q)).scalar_one()


@pytest.mark.asyncio
async def test_seed_populates_everything(db, seeded):
    summary = await demo_seed.seed(user_id=UID, now=NOW)

    # user model + relationships + device token + cleared pings
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == UID))).scalar_one()
    rels = u.living_profile["biography"]["relationships"]
    assert u.name == "Mira Sharma" and len(rels) == 9
    assert any(r["name"] == "Anjali Sharma" and r["relation"] == "mother" for r in rels)
    assert await _count(db, DeviceToken) == 1
    assert await _count(db, ProactivePing) == 0          # nothing held -> proactive moments fire immediately

    # goals + context + commitments + watches
    assert summary["goals"] == 3 and await _count(db, Goal, status="active") == 3
    assert await _count(db, Context, kind="fundraising", state="active") == 1
    assert summary["commitments"] == 19                  # 6 demo + 13 backlog
    assert summary["watches"] == 4 and await _count(db, Watch, status="active") == 4
    assert summary["holding"] == 23                       # 4 watches + 0 cards + 19 loops -> the dashboard pulse

    # calendar (incl the friday flight + the saturday birthday), emails, finance, meals
    async with db() as s:
        titles = [c.title for c in (await s.execute(select(CalendarEntry).where(CalendarEntry.user_id == UID))).scalars().all()]
    assert any("SQ112" in t for t in titles) and any("birthday" in t.lower() for t in titles)
    assert await _count(db, EmailMessage) == 7
    assert await _count(db, EmailMessage, is_important=True) == 1   # the sequoia flag (rest is noise)
    assert await _count(db, FinanceAccount) == 2
    assert await _count(db, Observation, type="meal") == 5


@pytest.mark.asyncio
async def test_moments_are_ready(db, seeded):
    """The seed makes the real engines fire — proof the moments can occur immediately."""
    await demo_seed.seed(user_id=UID, now=NOW)

    # M3 — bill-about-to-bounce: the shortfall detector finds the AWS gap
    from backend.finance.detector import detect_low_balance_vs_bill
    async with db() as s:
        accts = list((await s.execute(select(FinanceAccount).where(FinanceAccount.user_id == UID))).scalars().all())
        bills = list((await s.execute(select(Bill).where(Bill.user_id == UID, Bill.status == "upcoming"))).scalars().all())
    shortfalls = detect_low_balance_vs_bill(accts, bills, now=NOW)
    assert any(sf.biller == "AWS" and sf.shortfall > 0 for sf in shortfalls)

    # M8 — waste: spotify + apple music = a duplicate music service
    from backend.finance.waste import detect_waste
    from db.models import FinanceTransaction
    async with db() as s:
        txns = list((await s.execute(select(FinanceTransaction).where(FinanceTransaction.user_id == UID))).scalars().all())
    kinds = {f.kind for f in detect_waste(txns, now=NOW)}
    assert "duplicate_service" in kinds

    # M1/M2 — context + goal weighting is live and matches the sequoia thread
    from backend.knowledge.context import active_contexts, context_keywords
    from backend.knowledge.goals import relevant_goals
    assert any(c.kind == "fundraising" for c in await active_contexts(UID, now=NOW))
    assert "series" in await context_keywords(UID, now=NOW)
    assert await relevant_goals(UID, "Series A term sheet")   # the goal matches the email -> goal_match in M2

    # M1 — the watch bar ranks the seeded state
    from backend.knowledge.attention import rank_attention
    items = await rank_attention(UID, now=NOW)
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_seed_is_idempotent(db, seeded):
    await demo_seed.seed(user_id=UID, now=NOW)
    await demo_seed.seed(user_id=UID, now=NOW)   # re-run: wipes + reseeds, no duplicates
    assert await _count(db, Goal) == 3
    assert await _count(db, Watch) == 4
    assert await _count(db, OpenLoop) == 19

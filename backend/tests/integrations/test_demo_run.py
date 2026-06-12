"""demo_run.py — the scenario runner plays all 23 shots over the seeded DB and
verifies every shot (scripted mode, no LLM / no OAuth). Proves the executable
storyboard end to end: cards stage, taps resolve (running the real sandboxed
executors), and the expected notifications/cards/states hold.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import select

import demo_run
import demo_seed
from db.models import Card, FinanceTransaction

SCENARIOS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "demo_scenarios.yaml")
UID = "demo-mira"


@pytest.fixture(autouse=True)
def _stub_cognition(db, monkeypatch):
    async def _no_cognition(user_id, now):
        return {"beliefs": 0, "memories": 0}
    monkeypatch.setattr(demo_seed, "_cognition", _no_cognition)


@pytest.mark.asyncio
async def test_runner_plays_all_shots(db):
    result = await demo_run.run(SCENARIOS, mode="scripted", seed=True)
    assert result["failed"] == 0           # every shot verified
    assert result["passed"] == 23          # all 23 shots ran + passed

    async with db() as s:
        # the decision cards resolved through the tap path
        aws = (await s.execute(select(Card).where(Card.id == "c_m3_aws"))).scalar_one()
        seq = (await s.execute(select(Card).where(Card.id == "c_m2_sequoia"))).scalar_one()
        flowers = (await s.execute(select(Card).where(Card.id == "c_m7_flowers"))).scalar_one()
        assert aws.state == "acted" and seq.state == "acted" and flowers.state == "acted"
        # the M3 transfer ran the real (sandboxed) executor -> a ledger row exists
        moved = (await s.execute(
            select(FinanceTransaction).where(FinanceTransaction.user_id == UID, FinanceTransaction.amount == 5000)
        )).scalars().all()
        assert moved, "transfer executor should have written the ₹5,000 ledger move"


@pytest.mark.asyncio
async def test_single_shot(db):
    await demo_seed.seed(user_id=UID)
    result = await demo_run.run(SCENARIOS, mode="scripted", only="shot_6")
    assert result["passed"] == 1 and result["failed"] == 0
    async with db() as s:
        assert (await s.execute(select(Card).where(Card.id == "c_m3_aws"))).scalar_one().intent == "approval"

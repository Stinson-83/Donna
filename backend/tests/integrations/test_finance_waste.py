"""Capability 4 depth — subscription + waste detection.

Pure detector tests (recurring, double-charge, duplicate-family, price creep,
spending spike — and the silences) plus the proactive check end to end with a
stubbed brain: surfaces the top finding once, then the ping dedup holds.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

NOW = datetime(2026, 8, 25, 12, 0)


def _txn(merchant, amount, days_ago, direction="debit", currency="INR"):
    return SimpleNamespace(
        merchant=merchant, amount=amount, direction=direction, currency=currency,
        occurred_at=NOW - timedelta(days=days_ago),
    )


# ── recurring ────────────────────────────────────────────────────────────────

def test_detect_recurring_monthly_only():
    from backend.finance.waste import detect_recurring

    txns = [
        _txn("Spotify", 119, 65), _txn("Spotify", 119, 35), _txn("Spotify", 119, 5),
        _txn("Amazon", 2300, 40),                       # one-off
        _txn("Gym", 1500, 110), _txn("Gym", 1500, 80),  # lapsed (nothing in 80 days)
        _txn("Salary", 90000, 10, direction="credit"),  # credits ignored
    ]
    rec = detect_recurring(txns, now=NOW)
    assert [r.merchant for r in rec] == ["spotify"]
    assert rec[0].count == 3
    assert 25 <= rec[0].interval_days <= 35


# ── waste findings ───────────────────────────────────────────────────────────

def test_double_charge_same_cycle():
    from backend.finance.waste import detect_waste

    txns = [
        _txn("Spotify", 119, 70), _txn("Spotify", 119, 40),
        _txn("Spotify", 119, 10), _txn("Spotify", 179, 5),  # two plans this cycle
    ]
    kinds = {f.kind for f in detect_waste(txns, now=NOW)}
    assert "double_charge" in kinds


def test_duplicate_service_family():
    from backend.finance.waste import detect_waste

    txns = [
        _txn("Spotify", 119, 65), _txn("Spotify", 119, 35), _txn("Spotify", 119, 5),
        _txn("Apple Music", 99, 60), _txn("Apple Music", 99, 30),
    ]
    dups = [f for f in detect_waste(txns, now=NOW) if f.kind == "duplicate_service"]
    assert len(dups) == 1
    assert "music" in dups[0].summary
    assert dups[0].monthly_cost == pytest.approx(99, rel=0.15)  # the cheaper one


def test_price_increase():
    from backend.finance.waste import detect_waste

    txns = [_txn("Netflix", 499, 65), _txn("Netflix", 499, 35), _txn("Netflix", 649, 5)]
    bumps = [f for f in detect_waste(txns, now=NOW) if f.kind == "price_increase"]
    assert len(bumps) == 1
    assert "499" in bumps[0].summary and "649" in bumps[0].summary


def test_spending_spike_and_quiet_baseline():
    from backend.finance.waste import detect_waste

    steady = [_txn("Groceries", 1000, d) for d in range(40, 100, 6)]  # prior baseline
    assert detect_waste(steady, now=NOW) == []  # steady spending -> silence

    spike = steady + [_txn("Electronics", 4000, d) for d in (20, 12, 4)]
    kinds = {f.kind for f in detect_waste(spike, now=NOW)}
    assert "spending_spike" in kinds


# ── the proactive check ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_waste_check_surfaces_once(db, monkeypatch):
    import backend.finance.waste as waste
    from db.models import FinanceAccount, FinanceTransaction

    async with db() as s:
        acct = FinanceAccount(user_id="u1", account_type="current", institution="hdfc", balance=50000)
        s.add(acct)
        await s.flush()
        for m, amt, days in [
            ("Spotify", 119, 65), ("Spotify", 119, 35), ("Spotify", 119, 5),
            ("Apple Music", 99, 60), ("Apple Music", 99, 30),
        ]:
            s.add(FinanceTransaction(
                user_id="u1", account_id=acct.id, amount=amt, direction="debit",
                merchant=m, occurred_at=NOW - timedelta(days=days),
            ))
        await s.commit()

    prompts: list[str] = []

    async def fake_brain(state, config=None):
        prompts.append(state["raw_input"])
        state["_outbound"] = []
        return state

    monkeypatch.setattr(waste, "_invoke_brain", fake_brain)

    await waste.maybe_surface_waste("u1", now_utc=NOW)
    assert len(prompts) == 1
    assert "finance_waste" in prompts[0]
    assert "music" in prompts[0]  # the duplicate-family finding

    # same finding, same cycle -> deduped
    await waste.maybe_surface_waste("u1", now_utc=NOW + timedelta(hours=6))
    assert len(prompts) == 1

    # a user with no transactions stays silent
    await waste.maybe_surface_waste("u2", now_utc=NOW)
    assert len(prompts) == 1

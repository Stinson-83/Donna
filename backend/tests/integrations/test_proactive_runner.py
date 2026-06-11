"""The proactive runner tick — sweeps users x checks, isolates failures, and
drives the real finance check (M3) so a shortfall surfaces on its own.
Uses the in-memory aiosqlite `db` fixture (seeds u1, u2)."""
from __future__ import annotations

from datetime import timedelta

import pytest

from backend.proactive.runner import run_once


@pytest.mark.asyncio
async def test_run_once_sweeps_users_and_checks(db):
    seen: list[tuple[str, str]] = []

    async def check_a(uid):
        seen.append(("a", uid))

    async def check_b(uid):
        seen.append(("b", uid))

    n = await run_once(checks=[check_a, check_b])
    assert n == 4  # 2 seeded users x 2 checks
    assert {("a", "u1"), ("a", "u2"), ("b", "u1"), ("b", "u2")} == set(seen)


@pytest.mark.asyncio
async def test_run_once_isolates_check_failures(db):
    ok_calls: list[str] = []

    async def boom(uid):
        raise RuntimeError("nope")

    async def fine(uid):
        ok_calls.append(uid)

    n = await run_once(checks=[boom, fine])
    assert n == 4  # every evaluation attempted
    assert set(ok_calls) == {"u1", "u2"}  # 'fine' ran for both despite 'boom'


@pytest.mark.asyncio
async def test_run_once_drives_finance_check(db, monkeypatch):
    from db.models import Bill, FinanceAccount, utcnow

    # u1 has a shortfall; u2 has no finance data at all.
    async with db() as s:
        s.add(FinanceAccount(id="c1", user_id="u1", account_type="current",
                             institution="HDFC", balance=43000, currency="INR"))
        s.add(FinanceAccount(id="s1", user_id="u1", account_type="savings",
                             institution="HDFC", balance=57000, currency="INR"))
        s.add(Bill(id="b1", user_id="u1", account_id="c1", biller="AWS", amount=47200,
                   currency="INR", due_date=utcnow() + timedelta(days=4),
                   auto_pay=True, status="upcoming"))
        await s.commit()

    import backend.finance.trigger as trig

    surfaced: list[str] = []

    async def fake_brain(state, config=None):
        surfaced.append(state["user_id"])
        state["_outbound"] = []
        return state

    monkeypatch.setattr(trig, "_invoke_brain", fake_brain)

    from backend.finance.trigger import maybe_surface_finance

    await run_once(checks=[maybe_surface_finance])
    assert surfaced == ["u1"]  # only the user in shortfall got surfaced

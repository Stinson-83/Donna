"""M3 — the saved auto-payment, at the finance + card layer.

Covers: the deterministic low_balance_vs_bill detector, the sandbox transfer
executor, and the full L0 path (tap -> gate=L0 -> transfer -> balances move ->
card settles, idempotent). Uses the in-memory aiosqlite `db` fixture (conftest).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from backend.cards.gate import classify
from backend.cards.models import DonnaCard
from backend.cards.resolution import resolve_card_action
from backend.cards.service import persist_card
from backend.finance.detector import detect_low_balance_vs_bill
from db.models import Card, FinanceAccount

NOW = datetime(2026, 4, 18, 10, 0, 0)


def _acct(id_, type_, bal, inst="HDFC"):
    return SimpleNamespace(id=id_, account_type=type_, balance=bal, institution=inst, currency="INR")


def _bill(id_, amount, days, *, auto_pay=True, status="upcoming", account_id="current", biller="AWS"):
    return SimpleNamespace(
        id=id_, amount=amount, due_date=NOW + timedelta(days=days), auto_pay=auto_pay,
        status=status, account_id=account_id, biller=biller, currency="INR",
    )


# ── detector (pure) ──────────────────────────────────────────────────────

def test_detector_fires_on_shortfall():
    accts = [_acct("current", "current", 43000), _acct("savings", "savings", 57000)]
    sfs = detect_low_balance_vs_bill(accts, [_bill("aws", 47200, 4)], now=NOW)
    assert len(sfs) == 1
    sf = sfs[0]
    assert sf.biller == "AWS"
    assert sf.shortfall == 4200
    assert sf.suggested_transfer == 5000          # 4,200 short -> round up to 5,000
    assert sf.debit_account_id == "current"
    assert sf.fund_account_id == "savings"
    assert sf.debit_account_label == "hdfc current"


def test_detector_quiet_when_covered_or_irrelevant():
    covered = [_acct("current", "current", 60000)]
    assert detect_low_balance_vs_bill(covered, [_bill("aws", 47200, 4)], now=NOW) == []

    short = [_acct("current", "current", 1000)]
    assert detect_low_balance_vs_bill(short, [_bill("a", 5000, 4, auto_pay=False)], now=NOW) == []
    assert detect_low_balance_vs_bill(short, [_bill("a", 5000, 40)], now=NOW) == []  # beyond lead
    assert detect_low_balance_vs_bill(short, [_bill("a", 5000, 4, status="paid")], now=NOW) == []


# ── transfer executor (sandbox) ──────────────────────────────────────────

async def _seed_accounts(db, *, current=43000.0, savings=57000.0):
    async with db() as s:
        s.add(FinanceAccount(id="acct_current", user_id="u1", account_type="current",
                             institution="HDFC", balance=current, currency="INR"))
        s.add(FinanceAccount(id="acct_savings", user_id="u1", account_type="savings",
                             institution="HDFC", balance=savings, currency="INR"))
        await s.commit()
    return "acct_savings", "acct_current"


@pytest.mark.asyncio
async def test_transfer_moves_money(db):
    from backend.cards.executors import transfer

    from_id, to_id = await _seed_accounts(db)
    out, ok = await transfer("u1", {"from_account_id": from_id, "to_account_id": to_id, "amount": 5000})
    assert ok is True
    assert "done" in out[0].body and "48,000" in out[0].body  # 43,000 + 5,000

    async with db() as s:
        cur = (await s.execute(select(FinanceAccount).where(FinanceAccount.id == to_id))).scalar_one()
        sav = (await s.execute(select(FinanceAccount).where(FinanceAccount.id == from_id))).scalar_one()
    assert cur.balance == 48000
    assert sav.balance == 52000  # 57,000 - 5,000


@pytest.mark.asyncio
async def test_transfer_insufficient_funds_fails(db):
    from backend.cards.executors import transfer

    from_id, to_id = await _seed_accounts(db, savings=1000.0)
    out, ok = await transfer("u1", {"from_account_id": from_id, "to_account_id": to_id, "amount": 5000})
    assert ok is False
    assert "not enough" in out[0].body


# ── full L0 path: tap -> gate -> transfer -> settle ──────────────────────

@pytest.mark.asyncio
async def test_tap_transfer_is_l0_executes_and_settles(db):
    from_id, to_id = await _seed_accounts(db)
    assert classify("transfer", {"amount": 5000}).tier == "L0"  # money is hard-gated

    card = DonnaCard.model_validate({
        "version": 1, "card_id": "c_aws", "intent": "approval", "theme": "dark",
        "blocks": [
            {"type": "body", "text": "aws **47,200** auto-debits in 4 days, your current is **4,200** short. move **5,000**?"},
            {"type": "actions", "actions": [
                {"label": "Transfer 5,000", "action_id": "a_transfer", "style": "primary"},
                {"label": "Not now", "action_id": "a_dismiss", "style": "secondary"},
            ]},
        ],
    })
    amap = {
        "a_transfer": {"kind": "execute", "tool": "transfer",
                       "args": {"from_account_id": from_id, "to_account_id": to_id, "amount": 5000}},
        "a_dismiss": {"kind": "dismiss"},
    }
    await persist_card("u1", card, amap)

    res = await resolve_card_action("u1", "c_aws:a_transfer")
    assert res.status == "handled"
    assert "done" in res.outbound[0].body

    async with db() as s:
        row = (await s.execute(select(Card).where(Card.id == "c_aws"))).scalar_one()
        cur = (await s.execute(select(FinanceAccount).where(FinanceAccount.id == to_id))).scalar_one()
    assert row.state == "acted"
    assert row.acted_action_id == "a_transfer"
    assert cur.balance == 48000  # money actually moved

    # second tap is rejected — no double transfer
    res2 = await resolve_card_action("u1", "c_aws:a_transfer")
    assert res2.status == "rejected"

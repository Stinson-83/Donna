"""low_balance_vs_bill — the deterministic Layer-1 diff for M3 (proactive_runner §5).

For auto-pay bills due within a lead window, is the debiting account's balance
below the bill amount? If so, surface a shortfall with a suggested transfer from
savings. No LLM — pure arithmetic over the cached finance tables.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

LEAD_DAYS = 7
TRANSFER_ROUND_TO = 1000.0  # round the suggested transfer up to a clean figure


@dataclass
class Shortfall:
    bill_id: str
    biller: str
    bill_amount: float
    due_date: datetime
    days_until_due: int
    currency: str
    debit_account_id: str | None
    debit_account_label: str   # "hdfc current"
    debit_balance: float
    shortfall: float           # bill_amount - debit_balance
    fund_account_id: str | None
    fund_account_label: str    # "hdfc savings"
    suggested_transfer: float  # rounded up to cover the shortfall


def _label(acct) -> str:
    inst = (getattr(acct, "institution", None) or "").strip().lower()
    kind = (getattr(acct, "account_type", None) or "account").strip().lower()
    return f"{inst} {kind}".strip()


def _suggest(shortfall: float, round_to: float = TRANSFER_ROUND_TO) -> float:
    # round the shortfall UP to the next clean figure (demo: 4,200 short -> 5,000)
    if shortfall <= 0:
        return 0.0
    return math.ceil(shortfall / round_to) * round_to


def detect_low_balance_vs_bill(
    accounts: list,
    bills: list,
    *,
    now: datetime,
    lead_days: int = LEAD_DAYS,
) -> list[Shortfall]:
    """accounts: FinanceAccount-like (.id, .account_type, .balance, .institution).
    bills: Bill-like (.id, .auto_pay, .status, .due_date, .amount, .account_id, .biller).
    Returns one Shortfall per at-risk auto-pay bill, with a suggested transfer
    from the highest-balance savings account."""
    by_id = {a.id: a for a in accounts}
    current = next((a for a in accounts if a.account_type == "current"), None)
    savings = sorted(
        (a for a in accounts if a.account_type == "savings"),
        key=lambda a: a.balance,
        reverse=True,
    )
    fund = savings[0] if savings else None
    horizon = now + timedelta(days=lead_days)

    out: list[Shortfall] = []
    for b in bills:
        if not b.auto_pay or b.status != "upcoming":
            continue
        if b.due_date < now or b.due_date > horizon:
            continue
        debit = by_id.get(b.account_id) or current
        if debit is None or debit.balance >= b.amount:
            continue  # no debit account, or already covered
        shortfall = b.amount - debit.balance
        out.append(
            Shortfall(
                bill_id=b.id,
                biller=b.biller,
                bill_amount=b.amount,
                due_date=b.due_date,
                days_until_due=max(0, (b.due_date - now).days),
                currency=getattr(b, "currency", "INR"),
                debit_account_id=debit.id,
                debit_account_label=_label(debit),
                debit_balance=debit.balance,
                shortfall=shortfall,
                fund_account_id=fund.id if fund else None,
                fund_account_label=_label(fund) if fund else "savings",
                suggested_transfer=_suggest(shortfall),
            )
        )
    return out

"""Proactive finance trigger — 'a bill is about to bounce'.

Analogous to proactive_email_trigger: run the deterministic detector, rate-limit,
then invoke the BRAIN loop in mode='proactive' to render an L0 approval card.

Directly invokable now (and by tests via _invoke_brain); the proactive runner
(proactive_runner.md) will schedule it once built. Detection is deterministic;
moving money is L0 — never auto-executed, the card tap is the approval.
"""
from __future__ import annotations

import json
import logging

from backend.finance.detector import Shortfall, detect_low_balance_vs_bill

logger = logging.getLogger(__name__)


def _session_factory():
    from db.session import async_session

    return async_session


async def _load_finance(user_id: str):
    from sqlalchemy import select

    from db.models import Bill, FinanceAccount

    async with _session_factory()() as s:
        accounts = (
            await s.execute(select(FinanceAccount).where(FinanceAccount.user_id == user_id))
        ).scalars().all()
        bills = (
            await s.execute(
                select(Bill).where(Bill.user_id == user_id, Bill.status == "upcoming")
            )
        ).scalars().all()
    return list(accounts), list(bills)


def _format_finance_prompt(s: Shortfall) -> str:
    cur = s.currency
    action_map_example = {
        "a_transfer": {
            "kind": "execute",
            "tool": "transfer",
            "args": {
                "from_account_id": s.fund_account_id,
                "to_account_id": s.debit_account_id,
                "amount": round(s.suggested_transfer),
            },
        },
        "a_dismiss": {"kind": "dismiss"},
    }
    return (
        "[SYSTEM TRIGGER: proactive_finance]\n"
        "A bill is about to auto-debit and the paying account is short. Decide "
        "whether to surface this; stay silent (send_burst with a single minimal "
        "text) if it is not worth interrupting.\n\n"
        f"Bill: {s.biller} {cur} {s.bill_amount:,.0f}, auto-debits in "
        f"{s.days_until_due} days\n"
        f"Paying account: {s.debit_account_label} — short by {cur} "
        f"{s.shortfall:,.0f} (balance {cur} {s.debit_balance:,.0f})\n"
        f"Cover it from: {s.fund_account_label}\n"
        f"Suggested transfer: {cur} {s.suggested_transfer:,.0f}\n\n"
        "If worth surfacing, end the turn with render_card — an approval card "
        "(intent approval, theme dark):\n"
        "- body states the bill, the shortfall, and the proposed transfer, with "
        "**bold** on the numbers (lowercase, no em dashes)\n"
        "- two actions, max: 'Transfer <amount>' and 'Not now'\n"
        f"- action_map (use these exact account ids): {json.dumps(action_map_example)}\n"
        "- a unique card_id, and expires_at near the due date\n"
        "Moving money is high-risk: never auto-execute. The card IS the approval."
    )


async def _invoke_brain(state: dict, config=None) -> dict:
    """Pluggable for tests. In prod, calls donna_runtime.brain.donna_turn."""
    from donna_runtime.brain import donna_turn

    return await donna_turn(state, config)


async def maybe_surface_finance(user_id: str) -> None:
    from db.models import utcnow

    accounts, bills = await _load_finance(user_id)
    shortfalls = detect_low_balance_vs_bill(accounts, bills, now=utcnow())
    if not shortfalls:
        return
    shortfalls.sort(key=lambda s: s.days_until_due)  # most urgent first
    s = shortfalls[0]

    from backend.integrations.proactive_rate_limit import can_fire_proactive, record_ping

    decision = await can_fire_proactive(user_id, source="finance")
    if not decision.allowed:
        await record_ping(user_id, "finance", s.bill_id, suppressed_reason=decision.reason)
        logger.info("proactive_finance: suppressed user=%s reason=%s", user_id, decision.reason)
        return

    from donna_runtime.config import DonnaAgentConfig

    cfg = DonnaAgentConfig(mode="proactive", user_id=user_id)
    prompt = _format_finance_prompt(s)
    state = {
        "user_id": user_id,
        "raw_input": prompt,
        "user_message": prompt,
        "trigger": {
            "source": "finance",
            "message_ref": s.bill_id,
            "shortfall": s.shortfall,
            "suggested_transfer": s.suggested_transfer,
        },
    }
    try:
        result = await _invoke_brain(state, cfg)
        await record_ping(user_id, "finance", s.bill_id)
        outbound = (result or state).get("_outbound") or []
        if outbound:
            try:
                from backend.integrations.push import notify_outbound

                await notify_outbound(user_id, outbound)
            except Exception:
                logger.exception("proactive_finance: push notify failed user=%s", user_id)
    except Exception:
        logger.exception("proactive_finance: brain invocation failed user=%s", user_id)

"""Card-action executors — the deterministic side effects a card tap triggers,
AFTER the §10.3 gate (cards_and_delivery §7). Distinct from BRAIN-loop tools:
these run when a user taps an L0/L1 action, not during a reasoning turn.

Each executor: async (user_id, args) -> (outbound: list, ok: bool).
ok=True settles the card; ok=False leaves it pending so it can retry.
Idempotency is at the card level — a card resolves at most once (resolution.py),
so an executor never runs twice for the same tap.
"""
from __future__ import annotations

import logging

from delivery.messages import TextMessage

logger = logging.getLogger(__name__)


async def send_email(user_id: str, args: dict) -> tuple[list, bool]:
    """Send (or reply to) an email via Composio Gmail.

    args: {body, thread_id?, to?, subject?}. thread_id -> reply to the thread.
    """
    from config import settings
    from backend.integrations.composio_client import ComposioClient

    args = args or {}
    body = str(args.get("body") or "").strip()
    if not body:
        return (
            [TextMessage(body="i didn't have a drafted reply to send. tell me what to say?")],
            False,
        )

    client = ComposioClient(api_key=settings.composio_api_key or "")
    try:
        await client.send_gmail(
            user_id,
            body=body,
            thread_id=args.get("thread_id"),
            to=args.get("to"),
            subject=args.get("subject"),
        )
    except Exception:
        logger.exception("send_email executor failed user=%s", user_id[:8])
        return ([TextMessage(body="couldn't send that just now. try again in a sec?")], False)

    return ([TextMessage(body="sent.")], True)


_CCY = {"INR": "₹", "SGD": "S$", "USD": "$"}


def _money(amount: float, currency: str = "INR") -> str:
    return f"{_CCY.get(currency, '')}{amount:,.0f}"


def _acct_label(acct) -> str:
    inst = (getattr(acct, "institution", None) or "").strip().lower()
    kind = (getattr(acct, "account_type", None) or "account").strip().lower()
    return f"{inst} {kind}".strip()


async def transfer(user_id: str, args: dict) -> tuple[list, bool]:
    """SANDBOX transfer between the user's CACHED accounts.

    This is NOT a real bank rail — Donna has no money-movement integration. It
    moves balance from->to in finance_accounts and records transactions, so the
    demo's "balance now ₹52,000" reflects her updated model. A real rail would
    replace the body of this function (the L0 gate + approval card stay the same).

    args: {from_account_id, to_account_id, amount, currency?}.
    """
    from sqlalchemy import select

    from db.models import FinanceAccount, FinanceTransaction, utcnow
    from db.session import async_session

    args = args or {}
    from_id = args.get("from_account_id")
    to_id = args.get("to_account_id")
    try:
        amount = float(args.get("amount"))
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0 or not from_id or not to_id:
        return ([TextMessage(body="i didn't have a clear amount or accounts to move. tell me again?")], False)

    async with async_session() as s:
        frm = (
            await s.execute(select(FinanceAccount).where(FinanceAccount.id == from_id))
        ).scalar_one_or_none()
        to = (
            await s.execute(select(FinanceAccount).where(FinanceAccount.id == to_id))
        ).scalar_one_or_none()
        if frm is None or to is None or frm.user_id != user_id or to.user_id != user_id:
            return ([TextMessage(body="couldn't find those accounts.")], False)
        if frm.balance < amount:
            return (
                [TextMessage(body=(
                    f"your {_acct_label(frm)} only has {_money(frm.balance, frm.currency)} — "
                    f"not enough to move {_money(amount, frm.currency)}."
                ))],
                False,
            )

        now = utcnow()
        frm.balance -= amount
        to.balance += amount
        frm.balance_synced_at = now
        to.balance_synced_at = now
        s.add(FinanceTransaction(
            user_id=user_id, account_id=frm.id, amount=amount, currency=frm.currency,
            direction="debit", merchant=f"transfer to {_acct_label(to)}", occurred_at=now,
        ))
        s.add(FinanceTransaction(
            user_id=user_id, account_id=to.id, amount=amount, currency=to.currency,
            direction="credit", merchant=f"transfer from {_acct_label(frm)}", occurred_at=now,
        ))
        new_to_balance, cur = to.balance, to.currency
        await s.commit()

    logger.info("transfer executor: moved %s %s->%s user=%s", amount, from_id, to_id, user_id[:8])
    return ([TextMessage(body=f"done. {_money(amount, cur)} moved. balance now {_money(new_to_balance, cur)}.")], True)


async def _calendar_event(user_id: str, *, title: str, start_iso: str | None,
                          duration_minutes: int = 60, location: str | None = None,
                          description: str | None = None) -> bool:
    """Create a real Google Calendar event via Composio. Returns True on success.
    The booking executors use this so a reservation/ride lands on the user's
    actual calendar even when the third-party rail isn't connected."""
    if not start_iso:
        return False
    from config import settings
    from backend.integrations.composio_client import ComposioClient

    try:
        await ComposioClient(api_key=settings.composio_api_key or "").create_calendar_event(
            user_id, title=title, start_iso=start_iso,
            duration_minutes=duration_minutes, location=location, description=description,
        )
        return True
    except Exception:
        logger.exception("calendar event create failed user=%s", user_id[:8])
        return False


def _int(v, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


async def book_restaurant(user_id: str, args: dict) -> tuple[list, bool]:
    """Record a restaurant reservation as a REAL calendar event. The reservation
    rail (OpenTable) isn't connected, so the calendar entry is the real artifact.
    args: {name, datetime_iso, party_size?, location?}."""
    args = args or {}
    name = args.get("name") or "the restaurant"
    party = _int(args.get("party_size"), 2)
    ok = await _calendar_event(
        user_id, title=f"Dinner at {name} (table for {party})",
        start_iso=args.get("datetime_iso"), duration_minutes=120,
        location=args.get("location"), description="reservation via donna",
    )
    if ok:
        return ([TextMessage(body=f"added to your calendar: {name}, table for {party}.")], True)
    return ([TextMessage(body=f"i couldn't add {name} to your calendar — is google calendar connected?")], False)


async def book_ride(user_id: str, args: dict) -> tuple[list, bool]:
    """Set a REAL calendar reminder for a ride. The ride-hailing rail (Grab/Uber)
    isn't connected, so this is a calendar reminder, not a booked car.
    args: {destination, pickup_time_iso, service?}."""
    args = args or {}
    dest = args.get("destination") or "your destination"
    service = (args.get("service") or "cab").lower()
    ok = await _calendar_event(
        user_id, title=f"{service} to {dest}", start_iso=args.get("pickup_time_iso"),
        duration_minutes=45, description="ride reminder via donna",
    )
    if ok:
        return ([TextMessage(body=(
            f"set a calendar reminder for your {service} to {dest}. "
            f"(booking the actual ride needs grab or uber connected.)"
        ))], True)
    return ([TextMessage(body=(
        f"i can't book the {service} yet — grab/uber isn't connected and i "
        f"couldn't reach your calendar to set a reminder."
    ))], False)


async def order_flowers(user_id: str, args: dict) -> tuple[list, bool]:
    """Honest stub: no flower-delivery rail (FNP) is connected, so Donna can't
    actually place the order. Don't fake a 'done'. args: {recipient, item, amount}."""
    args = args or {}
    recipient = args.get("recipient") or "them"
    item = args.get("item") or "flowers"
    logger.info("order_flowers (no rail): %s for %s amount=%s", item, recipient, args.get("amount"))
    return ([TextMessage(body=(
        f"i don't have a flower-delivery service connected yet, so i can't place "
        f"the {item} order for {recipient} myself. want me to remind you to do it?"
    ))], False)


# tool name (as the loop puts it in action_map) -> executor
EXECUTORS = {
    "send_email": send_email,
    "transfer": transfer,
    "book_restaurant": book_restaurant,
    "book_ride": book_ride,
    "order_flowers": order_flowers,
}

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


# tool name (as the loop puts it in action_map) -> executor
EXECUTORS = {
    "send_email": send_email,
}

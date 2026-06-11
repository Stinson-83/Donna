"""Card action resolution — a tap on any surface resolves the same card_id +
action_id through the card's action_map, with the §10.3 gate on execute kinds
(cards_and_delivery §7, INTEGRATION.md §2).

Deterministic except 'reopen', which hands control back to the BRAIN loop with a
new prompt. Idempotent + fresh: a card resolves at most once; a stale/expired/
already-acted card is rejected with an explanation (never silently re-run).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class CardActionResult:
    status: str                       # "reopen" | "handled" | "rejected"
    reopen_prompt: str | None = None  # status=reopen: the new BRAIN-loop input
    outbound: list = field(default_factory=list)  # handled/rejected: direct messages


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_card_action(card_action: str | None) -> tuple[str, str] | None:
    """'card_id:action_id' -> (card_id, action_id). card_id is a uuid (no colon),
    so split on the FIRST colon only."""
    if not card_action or ":" not in card_action:
        return None
    card_id, action_id = card_action.split(":", 1)
    if not card_id or not action_id:
        return None
    return card_id, action_id


async def resolve_card_action(
    user_id: str, card_action: str, surface: str = "whatsapp"
) -> CardActionResult:
    from sqlalchemy import select

    from delivery.messages import TextMessage
    from db.models import Card
    from db.session import async_session

    parsed = parse_card_action(card_action)
    if not parsed:
        return CardActionResult(
            "rejected",
            outbound=[TextMessage(body="hm, that tap didn't carry through. say it in words?")],
        )
    card_id, action_id = parsed

    async with async_session() as s:
        card = (
            await s.execute(select(Card).where(Card.id == card_id))
        ).scalar_one_or_none()
        if card is None or card.user_id != user_id:
            return CardActionResult(
                "rejected", outbound=[TextMessage(body="i can't find that card anymore.")]
            )
        # Freshness + idempotency: a card resolves once.
        if card.state != "pending":
            return CardActionResult(
                "rejected", outbound=[TextMessage(body="already handled that one.")]
            )
        spec = (card.action_map or {}).get(action_id)
        if not isinstance(spec, dict):
            return CardActionResult(
                "rejected",
                outbound=[TextMessage(body="that option isn't available anymore.")],
            )
        kind = (spec.get("kind") or "").strip().lower()

        if kind == "dismiss":
            _settle(card, action_id, surface, "dismissed")
            await s.commit()
            return CardActionResult("handled", outbound=[])  # silent sink

        if kind == "reopen":
            _settle(card, action_id, surface, "acted")
            await s.commit()
            prompt = spec.get("prompt") or ""
            return CardActionResult(
                "reopen", reopen_prompt=f"[CARD ACTION: {action_id}]\n{prompt}"
            )

        if kind == "execute":
            from backend.cards.gate import classify

            tool = spec.get("tool")
            targs = spec.get("args") or {}
            decision = classify(tool, targs)
            logger.info(
                "card execute: card=%s action=%s tool=%s tier=%s",
                card_id, action_id, tool, decision.tier,
            )
            outbound, ok = await _run_execute(user_id, tool, targs, decision)
            if ok:
                _settle(card, action_id, surface, "acted")
            await s.commit()
            return CardActionResult("handled", outbound=outbound)

        # consent / snooze: not yet wired for M2.
        return CardActionResult(
            "rejected", outbound=[TextMessage(body="i can't do that one yet.")]
        )


def _settle(card, action_id: str, surface: str, state: str) -> None:
    card.state = state
    card.acted_action_id = action_id
    card.acted_surface = surface
    card.acted_at = _utcnow()


async def _run_execute(user_id, tool, targs, decision):
    """Execute the tapped action's tool through the gate.

    No execute-capable action tools (send_email, transfer, ...) are wired into
    card resolution yet — that is integration work. Be honest rather than claim
    success: leave the card pending so it can run once the tool exists. The gate
    has already assigned the correct tier (decision.tier) for when it is.
    """
    from delivery.messages import TextMessage

    logger.info(
        "card execute (not wired): tool=%s tier=%s reason=%s",
        tool, decision.tier, decision.reason,
    )
    return (
        [TextMessage(body="got it. heads up: actually doing this isn't connected to your accounts yet.")],
        False,
    )

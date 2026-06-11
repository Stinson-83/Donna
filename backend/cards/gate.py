"""The §10.3 execution gate — deterministic agency-tier classifier.

Classifies a (tool, args) into L2 (auto) / L1 (confirm) / L0 (approve) from the
tool + its arguments ALONE. The BRAIN loop cannot talk past it. At card-tap time
the tap IS the authorization for L0/L1 (the card's existence is the approval);
the gate assigns + records the tier and refuses to AUTO-run anything above L2.

No LLM — pure rules (ADR §6/§10.3). When new action tools are added
(send_email, transfer, ...), add them to the right tier here.
"""
from __future__ import annotations

from dataclasses import dataclass

# money / legal / irreversible -> explicit approval, every time
_L0_TOOLS = {
    "transfer", "transfer_funds", "make_payment", "pay", "charge",
    "book_flight", "book_ride", "book_paid", "order_flowers", "place_order",
    "cancel_critical_service", "send_legal_document", "delete_data",
}
# acts toward a third party AS the user, or not trivially reversible -> confirm
_L1_TOOLS = {
    "send_email", "send_reply", "send_message", "send_whatsapp",
    "book_reservation", "make_reservation", "book_restaurant", "cancel_subscription",
}
_MONEY_NAME_HINTS = ("transfer", "pay", "send_money", "charge", "payment")
_MONEY_ARG_KEYS = ("amount", "amount_inr", "amount_cents", "amount_sgd")


@dataclass(frozen=True)
class GateDecision:
    tier: str        # "L0" | "L1" | "L2"
    reason: str

    @property
    def auto_ok(self) -> bool:
        """Only L2 may execute without an explicit user tap/approval."""
        return self.tier == "L2"


def classify(tool: str | None, args: dict | None = None) -> GateDecision:
    name = (tool or "").strip().lower()
    args = args or {}
    if name in _L0_TOOLS:
        return GateDecision("L0", f"{name}: money/legal/irreversible")
    # Anything that moves money is L0 regardless of the exact tool name.
    if any(k in args for k in _MONEY_ARG_KEYS) and any(h in name for h in _MONEY_NAME_HINTS):
        return GateDecision("L0", f"{name}: moves money")
    if name in _L1_TOOLS:
        return GateDecision("L1", f"{name}: acts as the user / not trivially reversible")
    return GateDecision("L2", f"{name or 'unknown'}: low-risk reversible")

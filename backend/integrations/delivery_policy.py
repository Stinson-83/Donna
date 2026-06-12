"""Tiered contextual delivery (ambient model).

Priority decides whether a proactive surface INTERRUPTS the user or lands quietly:

  critical -> push (+ voice, once ambient voice exists)
  high     -> push notification
  medium   -> dashboard + watch bar only (no buzz)
  low      -> dashboard only

The decision-card persists either way (render_card writes it, the dashboard +
/watchbar read it), so a "held" surface is still visible — it just doesn't buzz.
This is how "notifications stay rare, only meaningful changes interrupt" becomes
real. (Trade-off: a WhatsApp-only user, with no quiet dashboard, doesn't receive
held surfaces — which is the point: protect attention.)
"""
from __future__ import annotations

INTERRUPT_TIERS = frozenset({"critical", "high"})
VOICE_TIERS = frozenset({"critical"})

# Reference map: the tier each proactive source surfaces at. Time-critical, money,
# and explicit deadlines interrupt; ambient nudges and low-value finds stay quiet.
# (Sources pass their tier at the call site; this documents the policy in one place.)
SOURCE_TIERS = {
    "finance_shortfall": "critical",   # a bill about to bounce
    "morning_brief": "high",
    "schedule_conflict": "high",
    "prepare_event": "high",
    "task_due": "high",
    "birthday": "high",
    "proactive_email": "high",
    "event_shift": "high",
    "finance_waste": "medium",         # a duplicate sub is never urgent
    "meal_checkin": "high",            # interactive (expects a reply) -> still pushes
}


def should_interrupt(tier: str | None) -> bool:
    return (tier or "high").lower() in INTERRUPT_TIERS


def is_voice_tier(tier: str | None) -> bool:
    return (tier or "").lower() in VOICE_TIERS


def tier_for_watch(importance: int | None) -> str:
    """An active watch firing: important ones interrupt, quiet ones land on the bar."""
    return "high" if (importance or 0) >= 75 else "medium"


def tier_for_flight(status: str | None) -> str:
    return "critical" if (status or "") in ("cancelled", "diverted") else "high"

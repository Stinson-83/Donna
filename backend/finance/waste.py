"""Capability 4 depth — subscription + waste detection (the Spotify moment).

Pure deterministic analysis over the cached transactions ledger. From debit
history we derive recurring charges (subscriptions), then flag waste:

- double_charge: the same merchant billed twice inside one monthly cycle —
  two overlapping plans (Spotify Family + Individual).
- duplicate_service: two recurring charges in the same service family (two
  music-streaming subscriptions).
- price_increase: a subscription's latest charge is materially above its
  previous one (price creep).
- spending_spike: the last 30 days of debits run well above the prior
  trailing average.

"Unused subscription" needs usage data no bank feed carries — honestly out of
scope until an activity source exists. Detection is pure; maybe_surface_waste is
the proactive check (registered in the tick) that hands ONE finding to the BRAIN
loop. Cancelling a subscription is L1 — a card tap, never auto.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

logger = logging.getLogger(__name__)

_MONTHLY = (20.0, 40.0)        # day-gap band that reads as a monthly cycle
_AMOUNT_BAND = 0.35            # charges within 35% of each other look like one plan
_PRICE_BUMP = 0.10             # >=10% above the previous charge = price creep
_SPIKE_RATIO = 1.5             # last 30d >= 1.5x the trailing average = a spike
_SPIKE_FLOOR = 1000.0          # ...and at least this much absolute increase

# Same-family services: two active subscriptions here usually means one is waste.
_FAMILIES = {
    "music": {"spotify", "apple music", "youtube music", "tidal", "deezer"},
    "video": {"netflix", "prime video", "disney", "hotstar", "hbo", "hulu", "apple tv"},
    "storage": {"dropbox", "google one", "icloud", "onedrive"},
    "fitness": {"cultfit", "classpass", "peloton", "fitbit premium"},
}


def _norm(merchant: str | None) -> str:
    m = re.sub(r"[^a-z ]", " ", (merchant or "").lower())
    return " ".join(m.split())


def _family(merchant_norm: str) -> str | None:
    for fam, names in _FAMILIES.items():
        if any(n in merchant_norm for n in names):
            return fam
    return None


@dataclass
class Recurring:
    merchant: str          # normalized
    display: str           # last raw merchant string
    count: int
    interval_days: float   # median gap
    last_amount: float
    prev_amount: float
    monthly_cost: float
    currency: str
    last_charged: datetime
    family: str | None


@dataclass
class WasteFinding:
    kind: str              # double_charge | duplicate_service | price_increase | spending_spike
    key: str               # stable id for ping dedup
    summary: str           # one factual line for the stimulus
    monthly_cost: float    # what acting on it saves/affects, per month
    merchants: list[str]


def detect_recurring(txns: list, *, now: datetime) -> list[Recurring]:
    """Debit transactions -> recurring charges. A merchant recurs when it has >=2
    debits of similar size on a roughly monthly gap, the latest within ~1.5 cycles."""
    by_merchant: dict[str, list] = {}
    for t in txns:
        if getattr(t, "direction", "debit") != "debit":
            continue
        key = _norm(getattr(t, "merchant", None))
        if key:
            by_merchant.setdefault(key, []).append(t)

    out: list[Recurring] = []
    for key, rows in by_merchant.items():
        rows.sort(key=lambda t: t.occurred_at)
        if len(rows) < 2:
            continue
        amounts = [float(t.amount) for t in rows]
        if (max(amounts) - min(amounts)) / max(amounts) > _AMOUNT_BAND:
            continue  # too irregular to be one plan
        gaps = [
            (b.occurred_at - a.occurred_at).total_seconds() / 86400.0
            for a, b in zip(rows, rows[1:])
        ]
        gap = median(gaps)
        if not (_MONTHLY[0] <= gap <= _MONTHLY[1]):
            continue
        last = rows[-1]
        if (now - last.occurred_at).days > gap * 1.5:
            continue  # lapsed — not active anymore
        out.append(Recurring(
            merchant=key,
            display=last.merchant or key,
            count=len(rows),
            interval_days=gap,
            last_amount=float(last.amount),
            prev_amount=float(rows[-2].amount),
            monthly_cost=float(last.amount) * (30.0 / gap),
            currency=getattr(last, "currency", "INR"),
            last_charged=last.occurred_at,
            family=_family(key),
        ))
    return out


def detect_waste(txns: list, *, now: datetime) -> list[WasteFinding]:
    """All waste findings over the transaction history, most actionable first."""
    findings: list[WasteFinding] = []
    recurring = detect_recurring(txns, now=now)

    # double_charge: same merchant, >=2 debits inside one cycle window this month
    by_merchant: dict[str, list] = {}
    for t in txns:
        if getattr(t, "direction", "debit") != "debit":
            continue
        key = _norm(getattr(t, "merchant", None))
        if key:
            by_merchant.setdefault(key, []).append(t)
    cycle_start = now - timedelta(days=32)
    for key, rows in by_merchant.items():
        recent = sorted((t for t in rows if t.occurred_at >= cycle_start), key=lambda t: t.occurred_at)
        if len(recent) >= 2 and len(rows) >= 3:  # an established merchant billing twice this cycle
            cur = getattr(recent[-1], "currency", "INR")
            amounts = " + ".join(f"{cur} {float(t.amount):,.0f}" for t in recent[-2:])
            findings.append(WasteFinding(
                kind="double_charge",
                key=f"double:{key}:{now.strftime('%Y-%m')}",
                summary=f"{recent[-1].merchant or key} charged twice this cycle ({amounts}) — looks like two overlapping plans",
                monthly_cost=min(float(t.amount) for t in recent[-2:]),
                merchants=[recent[-1].merchant or key],
            ))

    # duplicate_service: two active recurring charges in the same family
    by_family: dict[str, list[Recurring]] = {}
    for r in recurring:
        if r.family:
            by_family.setdefault(r.family, []).append(r)
    for fam, subs in by_family.items():
        if len(subs) >= 2:
            subs.sort(key=lambda r: r.monthly_cost)
            cheaper = subs[0]
            names = " and ".join(r.display for r in subs)
            findings.append(WasteFinding(
                kind="duplicate_service",
                key=f"dupfam:{fam}:" + ":".join(sorted(r.merchant for r in subs)),
                summary=(
                    f"two {fam} subscriptions running ({names}) — dropping the cheaper one "
                    f"saves {cheaper.currency} {cheaper.monthly_cost:,.0f}/mo"
                ),
                monthly_cost=cheaper.monthly_cost,
                merchants=[r.display for r in subs],
            ))

    # price_increase: latest charge materially above the previous
    for r in recurring:
        if r.prev_amount > 0 and (r.last_amount - r.prev_amount) / r.prev_amount >= _PRICE_BUMP:
            findings.append(WasteFinding(
                kind="price_increase",
                key=f"bump:{r.merchant}:{r.last_amount:.0f}",
                summary=(
                    f"{r.display} went up: {r.currency} {r.prev_amount:,.0f} -> "
                    f"{r.currency} {r.last_amount:,.0f} per cycle"
                ),
                monthly_cost=(r.last_amount - r.prev_amount) * (30.0 / r.interval_days),
                merchants=[r.display],
            ))

    # spending_spike: last 30d debits vs the prior trailing average (needs >=60d history)
    debits = [t for t in txns if getattr(t, "direction", "debit") == "debit"]
    if debits:
        oldest = min(t.occurred_at for t in debits)
        history_days = (now - oldest).days
        if history_days >= 60:
            last30 = sum(float(t.amount) for t in debits if t.occurred_at >= now - timedelta(days=30))
            prior = [t for t in debits if t.occurred_at < now - timedelta(days=30)]
            prior_days = max(30.0, float(history_days - 30))
            prior_avg30 = sum(float(t.amount) for t in prior) / prior_days * 30.0
            if prior_avg30 > 0 and last30 >= prior_avg30 * _SPIKE_RATIO and last30 - prior_avg30 >= _SPIKE_FLOOR:
                cur = getattr(debits[0], "currency", "INR")
                findings.append(WasteFinding(
                    kind="spending_spike",
                    key=f"spike:{now.strftime('%Y-%m')}",
                    summary=(
                        f"spending is up: {cur} {last30:,.0f} in the last 30 days vs a "
                        f"{cur} {prior_avg30:,.0f} usual month"
                    ),
                    monthly_cost=last30 - prior_avg30,
                    merchants=[],
                ))

    findings.sort(key=lambda f: -f.monthly_cost)
    return findings


# ── proactive check ──────────────────────────────────────────────────────────

async def _invoke_brain(state: dict, config=None) -> dict:
    """Pluggable for tests. In prod, calls donna_runtime.brain.donna_turn."""
    from donna_runtime.brain import donna_turn

    return await donna_turn(state, config)


def _format_waste_prompt(f: WasteFinding) -> str:
    return (
        "[SYSTEM TRIGGER: finance_waste]\n"
        f"Found likely money waste: {f.summary}.\n"
        "Decide whether this is worth telling the user; stay silent if it's noise "
        "or they clearly chose this on purpose.\n"
        "If worth surfacing, one short line with the numbers in **bold**, via a "
        "heads_up card or a tight send_burst, and offer ONE concrete next step "
        "(cancel the cheaper plan, check the new price, look at what drove the "
        "spike). Cancelling anything is an action the USER takes via the card — "
        "never claim you cancelled something. Never invent numbers beyond the "
        "finding above."
    )


async def maybe_surface_waste(user_id: str, *, now_utc: datetime | None = None) -> None:
    """The tick check: detect waste over the last ~120 days of transactions and
    surface the single most valuable un-pinged finding. One finding per tick;
    each finding surfaces once a month (ping key carries the cycle)."""
    from sqlalchemy import select

    from db.models import FinanceTransaction, utcnow
    from db.session import async_session

    now = now_utc or utcnow()
    async with async_session() as s:
        txns = (await s.execute(
            select(FinanceTransaction).where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.occurred_at >= now - timedelta(days=120),
            ).order_by(FinanceTransaction.occurred_at.asc()).limit(2000)
        )).scalars().all()
    if not txns:
        return

    findings = detect_waste(list(txns), now=now)
    if not findings:
        return

    from backend.proactive.checks import _pinged_since

    target = None
    async with async_session() as s:
        for f in findings:
            if not await _pinged_since(s, user_id, f"waste:{f.key}", now - timedelta(days=30)):
                target = f
                break
    if target is None:
        return

    from backend.integrations.proactive_rate_limit import can_fire_proactive, record_ping

    decision = await can_fire_proactive(user_id, source="finance_waste")
    if not decision.allowed:
        await record_ping(user_id, f"waste:{target.key}", target.kind,
                          suppressed_reason=decision.reason, at=now)
        return

    from donna_runtime.config import DonnaAgentConfig

    cfg = DonnaAgentConfig(mode="proactive", user_id=user_id)
    prompt = _format_waste_prompt(target)
    state = {"user_id": user_id, "raw_input": prompt, "user_message": prompt,
             "trigger": {"source": "finance_waste", "message_ref": target.key}}
    try:
        result = await _invoke_brain(state, cfg)
        await record_ping(user_id, f"waste:{target.key}", target.kind, at=now)
        outbound = (result or state).get("_outbound") or []
        if outbound:
            try:
                from backend.integrations.notify import deliver_proactive

                await deliver_proactive(user_id, outbound)
            except Exception:
                logger.exception("finance_waste: deliver failed user=%s", user_id[:8])
    except Exception:
        logger.exception("finance_waste: brain invocation failed user=%s", user_id[:8])

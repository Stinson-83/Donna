"""The Context Layer — the adaptive "season of life" engine.

(Spec: docs_v2/CONTEXT_INTELLIGENCE_ARCHITECTURE.md.) Deterministic state + weights,
NOT a second reasoning site and ZERO synchronous LLM calls. The engine infers
probabilistic, time-bounded, simultaneously-active contexts (travel, fundraising,
exams, ...) from signals the system already produces, decays them as evidence
lapses, and exposes a single weighting function that the priority scorers, the
email importance scorer, the loop's prompt, and (next) delivery all consume —
exactly the way goals already weight things (Cap 7).

Inference is arithmetic over signals:
- focus_window  : an explicit user declaration ("fundraising is my priority for 2 weeks")
- travel        : an upcoming travel-ish calendar event OR an active flight watch
- domain match  : an active goal whose text matches a context's domain keywords

The loop still does all the reasoning; this only sets priors and filters.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_FLOOR = 0.2     # below this confidence a context closes
_DECAY = 0.6     # per-tick multiplier when a signal has lapsed
_MIN_SURFACE = 0.45  # contexts below this don't feed the prompt / email keywords

# kind -> the attention domains it amplifies (and, later, damps). These keywords
# are what a piece of text is matched against to decide if a context applies.
CONTEXT_DOMAINS: dict[str, dict[str, set[str]]] = {
    "travel": {"amplify": {"flight", "airport", "hotel", "gate", "boarding", "itinerary",
                            "pickup", "trip", "visa", "baggage", "layover", "terminal", "customs", "check-in"}},
    "fundraising": {"amplify": {"investor", "investors", "fundraise", "fundraising", "raise", "round",
                                "seed", "series", "term sheet", "valuation", "diligence", "cap table",
                                "pitch", "data room", "wire", "sequoia"}},
    "job_search": {"amplify": {"recruiter", "interview", "interviews", "offer", "application",
                               "applications", "resume", "onsite", "referral", "hiring", "internship"}},
    "exam": {"amplify": {"exam", "exams", "final", "finals", "midterm", "study", "assignment",
                         "quiz", "syllabus", "revision", "grading"}},
    "health": {"amplify": {"gym", "workout", "sleep", "meal", "calorie", "run", "diet",
                          "physio", "medication", "recovery", "weight", "fitness"}},
    "launch": {"amplify": {"launch", "ship", "release", "beta", "waitlist", "go-live", "demo day"}},
    "wedding": {"amplify": {"wedding", "venue", "rsvp", "registry", "caterer", "guest list"}},
    "family": {"amplify": {"family", "mom", "dad", "parents", "sibling", "brother", "sister"}},
}

_PHRASE = {
    "travel": "you're traveling",
    "fundraising": "you're fundraising",
    "job_search": "you're job-hunting",
    "exam": "you're in exam season",
    "health": "you're focused on health",
    "launch": "you're shipping a launch",
    "wedding": "you're planning a wedding",
    "family": "family is front of mind",
}

_FOCUS_ALIASES = {
    "fundrais": "fundraising", "raise": "fundraising", "investor": "fundraising", "round": "fundraising",
    "travel": "travel", "trip": "travel",
    "exam": "exam", "study": "exam", "academic": "exam", "semester": "exam",
    "job": "job_search", "internship": "job_search", "interview": "job_search", "recruit": "job_search",
    "health": "health", "fitness": "health", "gym": "health",
    "launch": "launch", "ship": "launch",
    "wedding": "wedding", "family": "family",
}

_STOP = {"with", "from", "this", "that", "have", "your", "about", "next", "the", "for", "and", "priority"}


def _dom_lists(dom: dict) -> dict:
    """JSON-safe domains (sets -> sorted lists) for storage."""
    return {"amplify": sorted(dom.get("amplify", set())), "damp": sorted(dom.get("damp", set()))}


def _matches(text: str, keywords) -> bool:
    low = (text or "").lower()
    return any(k and k in low for k in keywords)


# ── inference (deterministic signal aggregation) ─────────────────────────────

async def _infer(session, user_id: str, now: datetime) -> dict[str, dict]:
    """Current signal-derived contexts: {kind: {confidence, evidence, domains}}."""
    from sqlalchemy import select

    from db.models import CalendarEntry, Goal, Watch

    out: dict[str, dict] = {}

    # travel — an upcoming travel-ish event, or an active flight watch
    evs = (await session.execute(
        select(CalendarEntry).where(
            CalendarEntry.user_id == user_id,
            CalendarEntry.start_time >= now,
            CalendarEntry.start_time <= now + timedelta(days=30),
        ).limit(40)
    )).scalars().all()
    travel_ev = next((e for e in evs if _matches(f"{e.title} {e.location or ''}", CONTEXT_DOMAINS["travel"]["amplify"])), None)
    flight_watch = (await session.execute(
        select(Watch.id).where(Watch.user_id == user_id, Watch.watch_type == "flight", Watch.status == "active").limit(1)
    )).scalar_one_or_none()
    if travel_ev or flight_watch:
        out["travel"] = {
            "confidence": 0.8 if flight_watch else 0.6,
            "evidence": {"flight_watch": bool(flight_watch), "event": travel_ev.title if travel_ev else None},
            "domains": _dom_lists(CONTEXT_DOMAINS["travel"]),
        }

    # a goal whose text matches a context's domain seeds that context (medium prior)
    goals = (await session.execute(
        select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
    )).scalars().all()
    for g in goals:
        text = f"{g.title} {g.description or ''}".lower()
        for kind, dom in CONTEXT_DOMAINS.items():
            if _matches(text, dom["amplify"]):
                cur = out.get(kind)
                if cur is None or 0.55 > cur["confidence"]:
                    out[kind] = {"confidence": max(0.55, cur["confidence"] if cur else 0.0),
                                 "evidence": {"goal": g.title}, "domains": _dom_lists(dom)}
    return out


async def refresh_contexts(user_id: str, *, now: datetime | None = None) -> None:
    """The tick pass: infer current contexts, refresh/upsert them, decay the ones
    whose signal lapsed, and expire focus windows. Idempotent."""
    from sqlalchemy import select

    from db.models import Context, utcnow
    from db.session import async_session

    now = now or utcnow()
    async with async_session() as s:
        rows = (await s.execute(
            select(Context).where(Context.user_id == user_id, Context.state == "active")
        )).scalars().all()
        by_kind = {c.kind: c for c in rows}

        # expire focus windows past their horizon
        for c in rows:
            if c.source == "focus_window" and c.expires_at and c.expires_at <= now:
                c.state = "closed"

        inferred = await _infer(s, user_id, now)
        for kind, spec in inferred.items():
            existing = by_kind.get(kind)
            if existing is not None and existing.source == "focus_window" and existing.state == "active":
                continue  # an explicit focus window outranks inference for the same kind
            if existing is not None:
                existing.confidence = spec["confidence"]
                existing.last_signal_at = now
                existing.evidence = spec["evidence"]
                existing.domains = spec["domains"]
                existing.state = "active"
            else:
                s.add(Context(
                    user_id=user_id, kind=kind, confidence=spec["confidence"], state="active",
                    source="inferred", evidence=spec["evidence"], domains=spec["domains"],
                    onset_at=now, last_signal_at=now,
                ))

        # decay inferred contexts whose signal is gone this run
        for c in rows:
            if c.state == "active" and c.source == "inferred" and c.kind not in inferred:
                c.confidence = round(c.confidence * _DECAY, 4)
                if c.confidence < _FLOOR:
                    c.state = "closed"

        await s.commit()


async def maybe_refresh_contexts(user_id: str, *, now_utc: datetime | None = None) -> None:
    """Proactive-tick entry point. Pure state update — never surfaces."""
    try:
        await refresh_contexts(user_id, now=now_utc)
    except Exception:
        logger.exception("context refresh failed user=%s", user_id[:8])


# ── explicit focus windows ───────────────────────────────────────────────────

async def set_focus(user_id: str, focus: str, *, days: int = 14, now: datetime | None = None) -> str:
    """Declare an intentional priority ("fundraising for 2 weeks"). High-confidence,
    time-bounded, expires on its own. Returns the resolved context kind."""
    from sqlalchemy import select

    from db.models import Context, utcnow
    from db.session import async_session

    now = now or utcnow()
    low = (focus or "").strip().lower()
    kind = next((v for k, v in _FOCUS_ALIASES.items() if k in low), None)
    if kind:
        domains = _dom_lists(CONTEXT_DOMAINS[kind])
    else:
        words = [w for w in re.findall(r"[a-z0-9]+", low) if len(w) >= 4 and w not in _STOP]
        kind = "custom:" + ("-".join(words[:3]) or "focus")
        domains = {"amplify": words or [low], "damp": []}

    expires = now + timedelta(days=max(1, int(days)))
    async with async_session() as s:
        existing = (await s.execute(
            select(Context).where(Context.user_id == user_id, Context.kind == kind)
        )).scalar_one_or_none()
        if existing is not None:
            existing.source = "focus_window"
            existing.confidence = 0.9
            existing.state = "active"
            existing.domains = domains
            existing.expires_at = expires
            existing.last_signal_at = now
            existing.evidence = {"declared": focus}
        else:
            s.add(Context(
                user_id=user_id, kind=kind, confidence=0.9, state="active", source="focus_window",
                evidence={"declared": focus}, domains=domains, onset_at=now, last_signal_at=now, expires_at=expires,
            ))
        await s.commit()
    return kind


# ── read + weighting API (what the rest of the system consumes) ──────────────

async def active_contexts(user_id: str, *, now: datetime | None = None) -> list:
    from sqlalchemy import select

    from db.models import Context, utcnow
    from db.session import async_session

    now = now or utcnow()
    async with async_session() as s:
        rows = (await s.execute(
            select(Context).where(Context.user_id == user_id, Context.state == "active")
            .order_by(Context.confidence.desc())
        )).scalars().all()
    return [c for c in rows if not (c.expires_at and c.expires_at <= now)]


def context_weight(text: str, contexts: list) -> float:
    """0..1 — the confidence of the most-confident active context whose domain this
    text touches. Callers scale it into their own point system."""
    low = (text or "").lower()
    best = 0.0
    for c in contexts:
        amp = (c.domains or {}).get("amplify") or []
        if any(k and k in low for k in amp):
            best = max(best, float(c.confidence or 0.0))
    return best


async def delivery_tier_shift(user_id: str, text: str, *, now: datetime | None = None) -> int:
    """How the active context should nudge a proactive surface's delivery tier:
    +1 raise (the surface matches a confident active context — interrupt more readily),
    -1 lower (off-focus while an explicit focus window is active — stay quieter),
    0 none. Critical is never lowered (that's enforced by delivery_policy.shift_tier)."""
    ctxs = await active_contexts(user_id, now=now)
    if not ctxs:
        return 0
    w = context_weight(text, ctxs)
    if w >= 0.7:
        return 1
    has_focus = any(c.source == "focus_window" and float(c.confidence or 0) >= 0.7 for c in ctxs)
    if has_focus and w < 0.3:
        return -1
    return 0


async def context_keywords(user_id: str, *, now: datetime | None = None) -> list[str]:
    """Flat amplify-keyword set across reasonably-confident contexts — for the
    email importance scorer (parallel to goal_keywords)."""
    kws: set[str] = set()
    for c in await active_contexts(user_id, now=now):
        if float(c.confidence or 0) >= _MIN_SURFACE:
            kws |= set((c.domains or {}).get("amplify") or [])
    return sorted(kws)


async def render_context_block(user_id: str, *, now: datetime | None = None) -> str:
    """The cached ## CONTEXT Standing section so the loop's recommendations align
    with the season of life. Silent until a context is confident enough to matter."""
    ctxs = [c for c in await active_contexts(user_id, now=now) if float(c.confidence or 0) >= _MIN_SURFACE]
    if not ctxs:
        return ""
    lines = []
    for c in ctxs:
        phrase = _PHRASE.get(c.kind) or f"focus: {c.kind.replace('custom:', '').replace('-', ' ')}"
        level = "high" if c.confidence >= 0.7 else "medium" if c.confidence >= 0.5 else "low"
        lines.append(f"- {phrase} ({level} confidence) — weigh related things up, routine things down")
    return "## CONTEXT (the season of life you're in right now — weigh accordingly)\n" + "\n".join(lines)

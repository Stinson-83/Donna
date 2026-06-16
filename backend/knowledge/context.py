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

# Confirmation (§8): contexts whose downstream weighting changes enough that, at
# high confidence, reorganizing around them is worth ONE question first. Softer
# seasons (health, family) adapt silently — they never trigger a confirmation.
_SIGNIFICANT_KINDS = {"travel", "fundraising", "exam", "job_search", "launch", "wedding"}
_CONFIRM_THRESHOLD = 0.75   # confidence at/above which a significant context is worth asking
_DECLINED_CONF = round(_FLOOR + 0.05, 4)  # a declined context lingers here: active but negligible

# noun for the post-tap acknowledgement copy ("i'll keep the trip front of mind")
_SEASON_NOUN = {
    "travel": "the trip", "fundraising": "the raise", "exam": "exam season",
    "job_search": "the search", "launch": "the launch", "wedding": "the wedding",
}

# Trigger-tier retrieval pointers (§6.3): cheap, capped, pointers-not-a-brief.
_MAX_POINTER_CONTEXTS = 2       # surface only the top seasons by confidence
_MAX_POINTERS_PER_CONTEXT = 4   # a handful of refs, never an inventory
_POINTER_HORIZON_DAYS = 30      # how far ahead an upcoming event still counts as "now"


def _dom_lists(dom: dict) -> dict:
    """JSON-safe domains (sets -> sorted lists) for storage."""
    return {"amplify": sorted(dom.get("amplify", set())), "damp": sorted(dom.get("damp", set()))}


def _matches(text: str, keywords) -> bool:
    low = (text or "").lower()
    return any(k and k in low for k in keywords)


def _short(text: str, limit: int = 72) -> str:
    """Collapse whitespace + clip to a pointer-length label (never a paragraph)."""
    t = " ".join((text or "").split())
    return t if len(t) <= limit else t[: limit - 3].rstrip() + "..."


# ── inference (deterministic signal aggregation) ─────────────────────────────

# per-signal priors; a season's confidence is the noisy-or over its signals, capped
_SIG_FLIGHT = 0.8     # a booked flight is a strong, concrete travel signal
_SIG_EVENT = 0.6      # an upcoming calendar event matching a season
_SIG_WATCH = 0.55     # she is already monitoring something in that domain
_SIG_GOAL = 0.55      # a standing goal prior on the matching season
_INFER_CAP = 0.9      # inference never asserts certainty (a user-confirmed season = 0.95)
_EMAIL_WINDOW_DAYS = 21   # rolling window for the email/thread-density signal
_EMAIL_MIN_THREADS = 2    # fewer matching threads than this is not a pattern


def _noisy_or(confs) -> float:
    """Combine independent evidence: corroborating signals raise confidence, each
    bounded by 1. A lone 0.6 stays 0.6; 0.6 + 0.55 -> 0.82 (crosses the ask bar)."""
    prod = 1.0
    for c in confs:
        prod *= 1.0 - max(0.0, min(1.0, float(c)))
    return 1.0 - prod


def _email_conf(n: int) -> float:
    """Confidence from N matching email threads in the window (2 nudges, 3+ asks)."""
    return 0.6 if n < 3 else min(0.82, 0.6 + 0.09 * (n - 1))


async def _infer(session, user_id: str, now: datetime) -> dict[str, dict]:
    """Signal-derived contexts: {kind: {confidence, evidence, domains}}. Pure
    deterministic aggregation over the signals the system already produces —
    upcoming calendar, active watches, goals, and recent email/thread density —
    each emitting a per-season prior, combined per kind via noisy-or. No LLM
    (a 'classify my life phase' model pass is the banned pipeline, ADR §8)."""
    from collections import defaultdict

    from sqlalchemy import select

    from db.models import CalendarEntry, EmailMessage, Goal, Watch

    signals: dict[str, list[tuple[float, tuple[str, object]]]] = defaultdict(list)

    def _emit(kind: str, conf: float, ev_key: str, ev_val) -> None:
        signals[kind].append((conf, (ev_key, ev_val)))

    # 1. upcoming calendar — any season by domain match (a scheduled, concrete thing)
    evs = (await session.execute(
        select(CalendarEntry).where(
            CalendarEntry.user_id == user_id,
            CalendarEntry.start_time >= now,
            CalendarEntry.start_time <= now + timedelta(days=30),
        ).order_by(CalendarEntry.start_time.asc()).limit(40)
    )).scalars().all()
    for e in evs:
        text = f"{e.title} {e.location or ''}"
        for kind, dom in CONTEXT_DOMAINS.items():
            if _matches(text, dom["amplify"]):
                _emit(kind, _SIG_EVENT, "event", e.title)

    # 2. active watches — a flight watch is a strong travel booking; any other watch
    #    whose subject matches a domain says she is already watching that season
    watches = (await session.execute(
        select(Watch).where(Watch.user_id == user_id, Watch.status == "active").limit(60)
    )).scalars().all()
    for w in watches:
        if w.watch_type == "flight":
            _emit("travel", _SIG_FLIGHT, "flight_watch", True)
            continue
        text = f"{w.title} {w.subject_key}"
        for kind, dom in CONTEXT_DOMAINS.items():
            if _matches(text, dom["amplify"]):
                _emit(kind, _SIG_WATCH, "watch", w.title)

    # 3. active goals — a standing prior on the matching season
    goals = (await session.execute(
        select(Goal).where(Goal.user_id == user_id, Goal.status == "active").limit(40)
    )).scalars().all()
    for g in goals:
        text = f"{g.title} {g.description or ''}"
        for kind, dom in CONTEXT_DOMAINS.items():
            if _matches(text, dom["amplify"]):
                _emit(kind, _SIG_GOAL, "goal", g.title)

    # 4. recent inbound email/thread density — the "≥N recruiter threads ⇒ job_search"
    #    rule, generalized: distinct matching threads per season in a rolling window
    try:
        emails = (await session.execute(
            select(EmailMessage).where(
                EmailMessage.user_id == user_id,
                EmailMessage.is_sent.is_(False),
                EmailMessage.internal_date >= now - timedelta(days=_EMAIL_WINDOW_DAYS),
            ).order_by(EmailMessage.internal_date.desc()).limit(200)
        )).scalars().all()
        threads: dict[str, set] = defaultdict(set)
        for e in emails:
            text = f"{e.subject or ''} {e.snippet or ''} {e.from_address} {e.from_name or ''}"
            for kind, dom in CONTEXT_DOMAINS.items():
                if _matches(text, dom["amplify"]):
                    threads[kind].add(e.thread_id)
        for kind, ts in threads.items():
            if len(ts) >= _EMAIL_MIN_THREADS:
                _emit(kind, _email_conf(len(ts)), "email_threads", len(ts))
    except Exception:
        logger.exception("context infer: email-density signal failed user=%s", user_id[:8])

    # combine per kind: noisy-or over the signal priors, capped; merge the evidence
    out: dict[str, dict] = {}
    for kind, sigs in signals.items():
        conf = min(_INFER_CAP, round(_noisy_or([c for c, _ in sigs]), 4))
        evidence = {k: v for _, (k, v) in sigs}
        out[kind] = {"confidence": conf, "evidence": evidence,
                     "domains": _dom_lists(CONTEXT_DOMAINS[kind])}
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
            if existing is not None and existing.source == "confirmed":
                # the user confirmed this season — pin it. inference refreshes the
                # signal trail but must never lower a user-confirmed context.
                existing.confidence = max(float(existing.confidence or 0), spec["confidence"])
                existing.last_signal_at = now
                existing.evidence = {**(existing.evidence or {}), **spec["evidence"]}
                existing.domains = spec["domains"]
                existing.state = "active"
                continue
            if existing is not None and (existing.evidence or {}).get("declined"):
                # the user declined the confirmation — the signal is still here, but
                # don't bounce the weighting back up or forget the decline.
                existing.last_signal_at = now
                existing.state = "active"
                continue
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

        # decay contexts whose signal is gone this run. confirmed seasons decay too
        # (a finished trip should release its weights), just from a higher floor;
        # focus windows are exempt — they expire on their horizon instead.
        for c in rows:
            if c.state == "active" and c.source in ("inferred", "confirmed") and c.kind not in inferred:
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


# ── confirmation (high-confidence + significant → ask once, §8) ───────────────

def context_phrase(kind: str) -> str:
    """The natural-language 'season' phrase for a kind ('you're traveling')."""
    return _PHRASE.get(kind) or f"focus: {kind.replace('custom:', '').replace('-', ' ')}"


def season_noun(kind: str) -> str:
    """The noun for post-tap acknowledgement copy ('the trip', 'the raise')."""
    return _SEASON_NOUN.get(kind) or kind.replace("custom:", "").replace("-", " ")


async def confirmable_context(user_id: str, *, now: datetime | None = None):
    """The single context worth a confirmation right now, or None. Deterministic:
    an INFERRED (not focus/confirmed/declined), SIGNIFICANT context whose confidence
    has crossed the threshold. The trigger asks; the loop renders the card; a yes
    pins it (confirm_context_kind), a no damps it (decline_context_kind)."""
    best = None
    for c in await active_contexts(user_id, now=now):
        if c.source != "inferred":
            continue                                  # focus = explicit, confirmed = done
        if (c.evidence or {}).get("declined"):
            continue                                  # the user already said no
        if c.kind not in _SIGNIFICANT_KINDS:
            continue                                  # soft seasons adapt silently
        if float(c.confidence or 0) < _CONFIRM_THRESHOLD:
            continue
        if best is None or float(c.confidence or 0) > float(best.confidence or 0):
            best = c
    return best


async def confirm_context_kind(user_id: str, kind: str, *, now: datetime | None = None) -> bool:
    """The user said yes — pin the context (source=confirmed, high confidence) so it
    weights strongly and stops re-asking. Returns False if it's no longer active."""
    from sqlalchemy import select

    from db.models import Context, utcnow
    from db.session import async_session

    now = now or utcnow()
    async with async_session() as s:
        c = (await s.execute(
            select(Context).where(
                Context.user_id == user_id, Context.kind == kind, Context.state == "active")
        )).scalar_one_or_none()
        if c is None:
            return False
        c.source = "confirmed"
        c.confidence = max(float(c.confidence or 0), 0.95)
        c.last_signal_at = now
        ev = dict(c.evidence or {})
        ev.pop("declined", None)
        ev["confirmed"] = True
        c.evidence = ev
        await s.commit()
    return True


async def decline_context_kind(user_id: str, kind: str, *, now: datetime | None = None) -> bool:
    """The user said no — damp the context below the surface line and mark it declined
    so refresh won't bounce it back up or re-ask. It still exists (the signal is real),
    it just stops asserting and decays away. Returns False if it's no longer active."""
    from sqlalchemy import select

    from db.models import Context, utcnow
    from db.session import async_session

    now = now or utcnow()
    async with async_session() as s:
        c = (await s.execute(
            select(Context).where(
                Context.user_id == user_id, Context.kind == kind, Context.state == "active")
        )).scalar_one_or_none()
        if c is None:
            return False
        c.source = "inferred"
        c.confidence = min(float(c.confidence or 0), _DECLINED_CONF)
        c.last_signal_at = now
        c.evidence = {**(c.evidence or {}), "declined": True}
        await s.commit()
    return True


# ── retrieval pointers — Context Assembly, Trigger tier (§6.3) ────────────────

async def context_pointers(user_id: str, *, now: datetime | None = None) -> list[dict]:
    """Deterministic Trigger-tier retrieval: for the top active seasons, the cheap
    pointers (title + ref) to the watches she's running, the open commitments, and
    the upcoming events that belong to that season — matched by each context's own
    amplify keywords. This tells the loop WHAT EXISTS and which way to lean its
    recall_*; it is pointers, NEVER a brief (ADR §5), and makes ZERO LLM calls.

    Returns [{kind, phrase, pointers:[{type,label,ref}]}], at most a handful each."""
    from sqlalchemy import select

    from db.models import CalendarEntry, OpenLoop, Watch, utcnow
    from db.session import async_session

    now = now or utcnow()
    ctxs = [c for c in await active_contexts(user_id, now=now)
            if float(c.confidence or 0) >= _MIN_SURFACE][:_MAX_POINTER_CONTEXTS]
    if not ctxs:
        return []

    async with async_session() as s:
        watches = (await s.execute(
            select(Watch).where(Watch.user_id == user_id, Watch.status == "active")
            .order_by(Watch.importance.desc()).limit(40)
        )).scalars().all()
        loops = (await s.execute(
            select(OpenLoop).where(OpenLoop.user_id == user_id, OpenLoop.status == "active")
            .order_by(OpenLoop.created_at.desc()).limit(40)
        )).scalars().all()
        events = (await s.execute(
            select(CalendarEntry).where(
                CalendarEntry.user_id == user_id,
                CalendarEntry.start_time >= now,
                CalendarEntry.start_time <= now + timedelta(days=_POINTER_HORIZON_DAYS),
            ).order_by(CalendarEntry.start_time.asc()).limit(40)
        )).scalars().all()

    groups: list[dict] = []
    for c in ctxs:
        amp = (c.domains or {}).get("amplify") or []
        if not amp:
            continue
        ptrs: list[dict] = []
        for w in watches:
            if _matches(f"{w.title} {w.subject_key}", amp):
                ptrs.append({"type": "watch", "label": _short(w.title), "ref": w.id})
        for ol in loops:
            if _matches(ol.content, amp):
                ptrs.append({"type": "commitment", "label": _short(ol.content), "ref": ol.id})
        for ev in events:
            if _matches(f"{ev.title} {ev.location or ''}", amp):
                ptrs.append({"type": "event", "label": _short(ev.title), "ref": ev.id})
        if ptrs:
            groups.append({"kind": c.kind, "phrase": context_phrase(c.kind),
                           "pointers": ptrs[:_MAX_POINTERS_PER_CONTEXT]})
    return groups


async def render_context_pointers(user_id: str, *, now: datetime | None = None) -> str:
    """The ## RELEVANT NOW block for the per-turn (Trigger-tier) context. Silent
    when no season has pointers worth attaching."""
    groups = await context_pointers(user_id, now=now)
    if not groups:
        return ""
    lines = [
        "## RELEVANT NOW (pointers tied to your current season — recall_* into these "
        "for detail; do not assume their contents)"
    ]
    for g in groups:
        lines.append(f"- {g['phrase']}:")
        for p in g["pointers"]:
            lines.append(f"    - {p['type']}: {p['label']}")
    return "\n".join(lines)

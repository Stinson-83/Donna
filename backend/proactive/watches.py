"""The active-watch system (proactive_runner.md §4-6).

A watch is a standing situation Donna monitors for the user ("tell me when
Sequoia replies", "keep an eye on the AWS bill"). Watches are evaluated only
when DUE (next_check <= now) on an adaptive cadence, and each watch_type has an
evaluator that does a cheap deterministic diff and only surfaces (wakes the BRAIN
loop) on a material change.

The runner calls sweep_due_watches() each tick. The evaluators here are
deterministic; the loop does the reasoning when something fires.

Evaluators included:
- reply : REAL — fires when a new inbound email arrives from the awaited sender
          (reads the EmailMessage mirror that Gmail ingest populates).
- generic: no-op — the watch is recorded and shown in the 'watching' list, but
           there's no data source to monitor an arbitrary topic yet (honest).

Single-process claim (no SKIP LOCKED) — fine for one proactive worker; the
material-change diff + retire-on-fire are the anti-spam. Multi-instance locking
is the documented follow-up.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ── dynamic check (adaptive cadence) ─────────────────────────────────────

def compute_next_check(
    *,
    now: datetime,
    deadline: datetime | None = None,
    importance: int = 50,
    stable_checks: int = 0,
    recent_change: bool = False,
    default_interval: timedelta = timedelta(hours=6),
) -> datetime:
    """Closer deadline + higher importance + recent change -> check sooner;
    stable + low importance -> back off. Clamped to [5min, 24h]."""
    if deadline is not None:
        hours = (deadline - now).total_seconds() / 3600
        if hours > 720:
            base = timedelta(hours=24)
        elif hours > 168:
            base = timedelta(hours=12)
        elif hours > 24:
            base = timedelta(hours=3)
        elif hours > 2:
            base = timedelta(minutes=15)
        else:
            base = timedelta(minutes=5)
    else:
        base = default_interval

    factor = 1.0
    if importance >= 75:
        factor *= 0.5
    elif importance <= 25:
        factor *= 2.0
    factor *= 0.5 if recent_change else min(1.5 ** stable_checks, 4.0)

    interval = base * factor
    interval = max(timedelta(minutes=5), min(interval, timedelta(hours=24)))
    return now + interval


# ── service ──────────────────────────────────────────────────────────────

async def _apply_goal_boost(user_id: str, text: str, importance: int) -> int:
    """Cap 7 — goals drive prioritization. A watch whose subject relates to an
    active goal gets more important, so it's checked sooner (compute_next_check
    favors high importance) and ranks higher in the watching list. Boost scales
    with goal priority. No goals / no match -> unchanged."""
    try:
        from backend.knowledge.goals import relevant_goals

        rel = await relevant_goals(user_id, text)
        if not rel:
            return importance
        top = int(rel[0]["priority"] or 3)
        boost = max(0, 35 - (top - 1) * 7)  # p1->35, p2->28, p3->21, p4->14, p5->7
        return min(100, int(importance) + boost)
    except Exception:
        logger.exception("_apply_goal_boost failed user=%s", user_id[:8])
        return importance


async def create_watch(
    user_id: str,
    watch_type: str,
    subject_key: str,
    *,
    title: str,
    importance: int = 50,
    deadline: datetime | None = None,
) -> str:
    """Idempotent on (user_id, watch_type, subject_key). Returns the watch id."""
    from sqlalchemy import select

    from db.models import Watch, utcnow
    from db.session import async_session

    watch_type = (watch_type or "generic").strip().lower()
    subject_key = (subject_key or title or "").strip()
    importance = await _apply_goal_boost(user_id, f"{title} {subject_key}", importance)
    async with async_session() as s:
        existing = (await s.execute(
            select(Watch).where(
                Watch.user_id == user_id,
                Watch.watch_type == watch_type,
                Watch.subject_key == subject_key,
            )
        )).scalar_one_or_none()
        if existing is not None:
            existing.title = title or existing.title
            existing.status = "active"
            existing.importance = importance
            if deadline is not None:
                existing.deadline = deadline
            existing.next_check = compute_next_check(
                now=utcnow(), deadline=existing.deadline, importance=importance
            )
            await s.commit()
            return existing.id
        w = Watch(
            user_id=user_id, watch_type=watch_type, subject_key=subject_key,
            title=title or subject_key, importance=importance, deadline=deadline,
            next_check=compute_next_check(now=utcnow(), deadline=deadline, importance=importance),
        )
        s.add(w)
        await s.commit()
        return w.id


async def claim_due_watches(now: datetime, limit: int = 200) -> list:
    from sqlalchemy import select

    from db.models import Watch
    from db.session import async_session

    async with async_session() as s:
        rows = (await s.execute(
            select(Watch).where(Watch.status == "active", Watch.next_check <= now)
            .order_by(Watch.next_check).limit(limit)
        )).scalars().all()
    return list(rows)


async def rearm_watch(watch, *, changed: bool, new_state: dict) -> None:
    from db.models import Watch, utcnow
    from db.session import async_session

    async with async_session() as s:
        w = await s.get(Watch, watch.id)
        if w is None:
            return
        w.last_checked_at = utcnow()
        if changed:
            w.stable_checks = 0
            w.last_known_state = new_state or {}
        else:
            w.stable_checks = int(w.stable_checks or 0) + 1
        w.next_check = compute_next_check(
            now=utcnow(), deadline=w.deadline, importance=w.importance,
            stable_checks=w.stable_checks, recent_change=changed,
        )
        await s.commit()


async def retire_watch(watch_id: str) -> None:
    from db.models import Watch
    from db.session import async_session

    async with async_session() as s:
        w = await s.get(Watch, watch_id)
        if w is not None:
            w.status = "retired"
            await s.commit()


async def active_watches(user_id: str) -> list[dict]:
    """The 'watching' list for the dashboard."""
    from sqlalchemy import select

    from db.models import Watch
    from db.session import async_session

    async with async_session() as s:
        rows = (await s.execute(
            select(Watch).where(Watch.user_id == user_id, Watch.status == "active")
            .order_by(Watch.importance.desc(), Watch.created_at.desc())
        )).scalars().all()
    return [{
        "id": w.id, "type": w.watch_type, "title": w.title, "subject": w.subject_key,
        "importance": w.importance,
        "deadline": w.deadline.isoformat() if w.deadline else None,
    } for w in rows]


# ── evaluators ───────────────────────────────────────────────────────────

@dataclass
class WatchOutcome:
    surface: bool
    new_state: dict = field(default_factory=dict)
    surface_prompt: str | None = None
    retire: bool = False
    tier: str | None = None  # delivery tier override; None -> derived from importance


async def evaluate_generic(watch) -> WatchOutcome:
    # Recorded + shown in the watching list, but no data source to monitor an
    # arbitrary topic — honest no-op (just re-arm).
    return WatchOutcome(surface=False, new_state=dict(watch.last_known_state or {}))


async def evaluate_reply_watch(watch) -> WatchOutcome:
    """Fires when a new inbound email arrives from the awaited sender after the
    watch was created. Real — reads the EmailMessage mirror."""
    from sqlalchemy import select

    from db.models import EmailMessage
    from db.session import async_session

    async with async_session() as s:
        row = (await s.execute(
            select(EmailMessage).where(
                EmailMessage.user_id == watch.user_id,
                EmailMessage.from_address.ilike(f"%{watch.subject_key}%"),
                EmailMessage.is_sent.is_(False),                 # inbound, not our sent reply
                EmailMessage.internal_date > watch.created_at,
            ).order_by(EmailMessage.internal_date.desc()).limit(1)
        )).scalar_one_or_none()

    if row is None:
        return WatchOutcome(surface=False, new_state=dict(watch.last_known_state or {}))

    prompt = (
        "[SYSTEM TRIGGER: watch_fired]\n"
        f"The thing the user asked you to watch happened: {watch.title}.\n"
        f"{watch.subject_key} sent a new email: subject \"{row.subject or ''}\", "
        f"\"{(row.snippet or '')[:200]}\". Tell the user in one short line and "
        "offer the obvious next step (e.g. draft a reply). Stay silent if it is noise."
    )
    return WatchOutcome(
        surface=True, new_state={"fired_email_id": row.id}, surface_prompt=prompt, retire=True,
    )


_SEEN_URL_CAP = 200


async def evaluate_web_watch(watch) -> WatchOutcome:
    """Monitor the web for new developments on the watch's subject. Real — runs
    the existing Exa search (recency-filtered), diffs result URLs against
    last_known_state, and fires ONLY on genuinely new findings. The first check
    just establishes a baseline (no day-one dump); the loop is the relevance
    judge when it fires. Web watches keep running (don't retire)."""
    from backend.web.search import search_web

    result = await search_web(watch.subject_key, max_results=6, recency="week")
    prev_state = dict(watch.last_known_state or {})
    if result.get("status") != "ok":
        return WatchOutcome(surface=False, new_state=prev_state)  # degraded/no_hits -> keep state

    hits = [h for h in (result.get("payload") or []) if h.get("url")]
    seen = list(prev_state.get("seen_urls") or [])
    seen_set = set(seen)
    new_hits = [h for h in hits if h["url"] not in seen_set]
    merged = (seen + [h["url"] for h in new_hits])[-_SEEN_URL_CAP:]
    new_state = {"seen_urls": merged}

    first_check = "seen_urls" not in prev_state
    if first_check or not new_hits:
        return WatchOutcome(surface=False, new_state=new_state)  # baseline, or nothing new

    lines = "\n".join(f"- {h.get('title') or h['url']} ({h['url']})" for h in new_hits[:3])
    prompt = (
        "[SYSTEM TRIGGER: watch_fired]\n"
        f"New on something the user asked you to watch: {watch.title}.\n"
        f"New results:\n{lines}\n"
        "Decide if any of this is genuinely worth telling them. If yes, one short "
        "line with the most important update and a link. If it's noise or they'd "
        "already know, stay silent."
    )
    return WatchOutcome(surface=True, new_state=new_state, surface_prompt=prompt, retire=False)


WATCH_EVALUATORS = {
    "reply": evaluate_reply_watch,
    "web": evaluate_web_watch,
    "generic": evaluate_generic,
}


def _evaluator_for(watch_type: str):
    """Dispatch to the evaluator for a watch_type. Flight lives in backend.travel
    and is imported lazily so this module has no import cycle with it (travel
    imports create_watch/WatchOutcome from here)."""
    if watch_type == "flight":
        from backend.travel.flights import evaluate_flight_watch

        return evaluate_flight_watch
    return WATCH_EVALUATORS.get(watch_type, evaluate_generic)


# ── sweep (called by the runner each tick) ───────────────────────────────

async def _invoke_brain(state: dict, config=None) -> dict:
    """Pluggable for tests. In prod, calls donna_runtime.brain.donna_turn."""
    from donna_runtime.brain import donna_turn

    return await donna_turn(state, config)


async def _surface_watch(watch, prompt: str, *, tier: str = "high") -> None:
    from donna_runtime.config import DonnaAgentConfig

    cfg = DonnaAgentConfig(mode="proactive", user_id=watch.user_id)
    state = {"user_id": watch.user_id, "raw_input": prompt, "user_message": prompt}
    result = await _invoke_brain(state, cfg)
    outbound = (result or state).get("_outbound") or []
    if outbound:
        try:
            from backend.integrations.notify import deliver_proactive

            await deliver_proactive(watch.user_id, outbound, tier=tier)
        except Exception:
            logger.exception("watch surface: push failed user=%s", watch.user_id[:8])


async def sweep_due_watches(now: datetime | None = None) -> int:
    """Evaluate every due watch; surface on material change; re-arm or retire.
    Returns the number of watches that fired."""
    from db.models import utcnow

    now = now or utcnow()
    due = await claim_due_watches(now)
    fired = 0
    for w in due:
        evaluator = _evaluator_for(w.watch_type)
        try:
            outcome = await evaluator(w)
        except Exception:
            logger.exception("watch eval failed id=%s type=%s", w.id, w.watch_type)
            outcome = WatchOutcome(surface=False, new_state=dict(w.last_known_state or {}))

        if outcome.surface and outcome.surface_prompt:
            try:
                from backend.integrations.delivery_policy import tier_for_watch

                tier = outcome.tier or tier_for_watch(w.importance)
                await _surface_watch(w, outcome.surface_prompt, tier=tier)
                fired += 1
            except Exception:
                logger.exception("watch surface failed id=%s", w.id)

        if outcome.retire:
            await retire_watch(w.id)
        else:
            await rearm_watch(w, changed=outcome.surface, new_state=outcome.new_state)

    if due:
        logger.info("watch sweep: %d due, %d fired", len(due), fired)
    return fired

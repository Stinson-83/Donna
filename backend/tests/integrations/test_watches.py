"""The active-watch system: adaptive cadence, idempotent creation, the real
email-reply evaluator, and the runner sweep (fire on material change, retire,
re-arm). Uses the in-memory aiosqlite `db` fixture (seeds u1, u2)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from backend.proactive.watches import (
    WATCH_EVALUATORS,
    active_watches,
    compute_next_check,
    create_watch,
    evaluate_reply_watch,
    sweep_due_watches,
)
from db.models import EmailMessage, Watch

NOW = datetime(2026, 4, 18, 10, 0, 0)


# ── dynamic cadence (pure) ───────────────────────────────────────────────

def test_dynamic_cadence():
    far = compute_next_check(now=NOW, deadline=NOW + timedelta(days=180), importance=50)
    assert timedelta(hours=20) <= (far - NOW) <= timedelta(hours=24)      # ~daily when far

    soon = compute_next_check(now=NOW, deadline=NOW + timedelta(hours=20), importance=50)
    assert (soon - NOW) <= timedelta(minutes=20)                          # tight when ~a day out

    hi = compute_next_check(now=NOW, deadline=NOW + timedelta(days=10), importance=90)
    base = compute_next_check(now=NOW, deadline=NOW + timedelta(days=10), importance=50)
    assert (hi - NOW) < (base - NOW)                                      # importance shortens

    clamp = compute_next_check(now=NOW, deadline=NOW + timedelta(minutes=30), importance=90)
    assert (clamp - NOW) >= timedelta(minutes=5)                          # never under 5min


# ── creation ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_watch_idempotent(db):
    a = await create_watch("u1", "reply", "sequoia", title="waiting on sequoia")
    b = await create_watch("u1", "reply", "sequoia", title="waiting on sequoia (again)")
    assert a == b  # same (user, type, subject) -> one watch

    async with db() as s:
        rows = (await s.execute(select(Watch).where(Watch.user_id == "u1"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].title == "waiting on sequoia (again)"


@pytest.mark.asyncio
async def test_active_watches_list(db):
    await create_watch("u1", "reply", "sequoia", title="sequoia reply", importance=90)
    await create_watch("u1", "generic", "poke launch", title="poke launch", importance=40)
    watching = await active_watches("u1")
    assert [w["title"] for w in watching] == ["sequoia reply", "poke launch"]  # by importance


# ── the real reply evaluator ─────────────────────────────────────────────

async def _seed_reply_watch(db, *, created=datetime(2026, 1, 1)):
    async with db() as s:
        s.add(Watch(id="w_reply", user_id="u1", watch_type="reply", subject_key="sequoia",
                    title="tell me when sequoia replies", importance=90,
                    next_check=datetime(2026, 1, 1), created_at=created))
        await s.commit()


def _email(**kw):
    base = dict(user_id="u1", gmail_message_id="g1", thread_id="t1",
                from_address="partner@sequoia.com", from_name="Partner",
                subject="re: term sheet", snippet="we're in, let's talk",
                internal_date=datetime(2026, 1, 2), ingest_depth="full", is_sent=False)
    base.update(kw)
    return EmailMessage(**base)


@pytest.mark.asyncio
async def test_reply_evaluator_fires_on_new_email(db):
    await _seed_reply_watch(db)
    async with db() as s:
        s.add(_email())  # inbound from sequoia, after the watch was created
        await s.commit()
        w = (await s.execute(select(Watch).where(Watch.id == "w_reply"))).scalar_one()

    outcome = await evaluate_reply_watch(w)
    assert outcome.surface is True
    assert outcome.retire is True
    assert "sequoia" in outcome.surface_prompt.lower()


@pytest.mark.asyncio
async def test_reply_evaluator_quiet_without_email(db):
    await _seed_reply_watch(db)
    async with db() as s:
        w = (await s.execute(select(Watch).where(Watch.id == "w_reply"))).scalar_one()
    outcome = await evaluate_reply_watch(w)
    assert outcome.surface is False


# ── the sweep ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sweep_fires_and_retires(db, monkeypatch):
    await _seed_reply_watch(db)
    async with db() as s:
        s.add(_email())
        await s.commit()

    import backend.proactive.watches as watches
    surfaced: list[str] = []

    async def fake_brain(state, config=None):
        surfaced.append(state["user_id"]); state["_outbound"] = []; return state

    monkeypatch.setattr(watches, "_invoke_brain", fake_brain)

    fired = await sweep_due_watches(now=datetime(2026, 4, 18))
    assert fired == 1
    assert surfaced == ["u1"]

    async with db() as s:
        w = (await s.execute(select(Watch).where(Watch.id == "w_reply"))).scalar_one()
    assert w.status == "retired"  # the wait is over


@pytest.mark.asyncio
async def test_sweep_rearms_generic_without_firing(db, monkeypatch):
    async with db() as s:
        s.add(Watch(id="w_gen", user_id="u1", watch_type="generic", subject_key="poke",
                    title="poke launch", importance=40,
                    next_check=datetime(2026, 1, 1), created_at=datetime(2026, 1, 1)))
        await s.commit()

    import backend.proactive.watches as watches
    monkeypatch.setattr(watches, "_invoke_brain", lambda *a, **k: None)

    fired = await sweep_due_watches(now=datetime(2026, 4, 18))
    assert fired == 0

    async with db() as s:
        w = (await s.execute(select(Watch).where(Watch.id == "w_gen"))).scalar_one()
    assert w.status == "active"               # still watching
    assert w.next_check > datetime(2026, 4, 18)  # re-armed into the future
    assert w.stable_checks == 1


# ── the real web-monitoring evaluator ────────────────────────────────────

def _ns(**kw):
    from types import SimpleNamespace
    return SimpleNamespace(**kw)


@pytest.mark.asyncio
async def test_web_watch_baseline_then_fires(monkeypatch):
    from backend.proactive.watches import evaluate_web_watch

    hits = {"status": "ok", "payload": [{"title": "Poke raises $5M", "url": "u1", "snippet": "..."}]}

    async def fake_search(query, *, max_results=5, recency=None):
        return hits

    monkeypatch.setattr("backend.web.search.search_web", fake_search)

    # first check = baseline (no day-one dump)
    o1 = await evaluate_web_watch(_ns(subject_key="poke launch", title="poke launch", last_known_state={}))
    assert o1.surface is False
    assert "u1" in o1.new_state["seen_urls"]

    # a genuinely new url appears -> fire
    hits["payload"] = [
        {"title": "Poke ships v2", "url": "u2", "snippet": "..."},
        {"title": "Poke raises $5M", "url": "u1", "snippet": "..."},
    ]
    o2 = await evaluate_web_watch(_ns(subject_key="poke launch", title="poke launch", last_known_state=o1.new_state))
    assert o2.surface is True
    assert o2.retire is False                      # web watches keep running
    assert "Poke ships v2" in o2.surface_prompt
    assert "Poke raises $5M" not in o2.surface_prompt  # already seen, not re-surfaced

    # nothing new -> quiet (dedup works)
    o3 = await evaluate_web_watch(_ns(subject_key="poke launch", title="poke launch", last_known_state=o2.new_state))
    assert o3.surface is False


@pytest.mark.asyncio
async def test_web_watch_degraded_is_quiet(monkeypatch):
    from backend.proactive.watches import evaluate_web_watch

    async def fake_search(query, *, max_results=5, recency=None):
        return {"status": "degraded", "payload": {"reason": "no key"}}

    monkeypatch.setattr("backend.web.search.search_web", fake_search)
    o = await evaluate_web_watch(_ns(subject_key="x", title="x", last_known_state={"seen_urls": ["a"]}))
    assert o.surface is False
    assert o.new_state == {"seen_urls": ["a"]}     # state preserved


@pytest.mark.asyncio
async def test_sweep_fires_web_watch(db, monkeypatch):
    async with db() as s:
        s.add(Watch(id="w_web", user_id="u1", watch_type="web", subject_key="poke launch",
                    title="poke launch", importance=50, last_known_state={"seen_urls": ["old"]},
                    next_check=datetime(2026, 1, 1), created_at=datetime(2026, 1, 1)))
        await s.commit()

    async def fake_search(query, *, max_results=5, recency=None):
        return {"status": "ok", "payload": [{"title": "Poke ships v2", "url": "new", "snippet": "x"}]}

    monkeypatch.setattr("backend.web.search.search_web", fake_search)

    import backend.proactive.watches as watches
    surfaced: list[str] = []

    async def fake_brain(state, config=None):
        surfaced.append(state["user_id"]); state["_outbound"] = []; return state

    monkeypatch.setattr(watches, "_invoke_brain", fake_brain)

    fired = await sweep_due_watches(now=datetime(2026, 4, 18))
    assert fired == 1
    assert surfaced == ["u1"]

    async with db() as s:
        w = (await s.execute(select(Watch).where(Watch.id == "w_web"))).scalar_one()
    assert w.status == "active"                       # keeps running, not retired
    assert "new" in w.last_known_state["seen_urls"]   # state advanced

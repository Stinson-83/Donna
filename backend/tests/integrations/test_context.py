"""The Context Layer (CONTEXT_INTELLIGENCE_ARCHITECTURE.md).

Deterministic "season of life" engine: infers contexts from signals (goals,
flight watches), honors explicit focus windows, decays lapsed ones, and weights
the attention ranker + email importance. Zero LLM.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from db.models import CalendarEntry, Card, Context, EmailMessage, Goal, OpenLoop, Watch

NOW = datetime(2026, 8, 25, 12, 0)


def _card(uid, ref, intent="heads_up"):
    return Card(user_id=uid, intent=intent,
                payload={"blocks": [{"type": "header", "ref": ref}]}, state="pending")


# ── inference + decay ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_infer_from_goal_and_flight_watch(db):
    from backend.knowledge.context import active_contexts, refresh_contexts

    async with db() as s:
        s.add(Goal(user_id="u1", title="raise a seed round", category="financial", status="active"))
        s.add(Watch(user_id="u1", watch_type="flight", subject_key="SQ516:2026-08-28",
                    title="flight SQ516", status="active"))
        await s.commit()

    await refresh_contexts("u1", now=NOW)
    kinds = {c.kind: c for c in await active_contexts("u1", now=NOW)}
    assert "fundraising" in kinds            # the goal text matched the fundraising domain
    assert "travel" in kinds                 # the flight watch
    assert kinds["travel"].confidence >= kinds["fundraising"].confidence  # a booked flight is stronger


@pytest.mark.asyncio
async def test_context_decays_and_closes_when_signal_lapses(db):
    from backend.knowledge.context import active_contexts, refresh_contexts

    async with db() as s:
        g = Goal(user_id="u1", title="raise a seed round", category="financial", status="active")
        s.add(g)
        await s.commit()
        gid = g.id

    await refresh_contexts("u1", now=NOW)
    assert any(c.kind == "fundraising" for c in await active_contexts("u1", now=NOW))

    # signal goes away
    async with db() as s:
        g = await s.get(Goal, gid)
        g.status = "dropped"
        await s.commit()

    await refresh_contexts("u1", now=NOW + timedelta(hours=6))   # 0.55 -> 0.33 (still active)
    assert any(c.kind == "fundraising" for c in await active_contexts("u1", now=NOW))
    await refresh_contexts("u1", now=NOW + timedelta(hours=12))  # 0.33 -> ~0.2 -> closed
    assert not any(c.kind == "fundraising" for c in await active_contexts("u1", now=NOW))


def _email(uid, i, subject, snippet, frm="x@example.com", thread=None, days_ago=2):
    return EmailMessage(
        user_id=uid, gmail_message_id=f"m{uid}{i}", thread_id=thread or f"t{uid}{i}",
        from_address=frm, from_name="Sender", subject=subject, snippet=snippet,
        ingest_depth="metadata", is_sent=False, internal_date=NOW - timedelta(days=days_ago),
    )


@pytest.mark.asyncio
async def test_infer_email_thread_density_seeds_job_search(db):
    """The headline richer signal: ≥N inbound threads matching a season's domain
    raises that season — one thread is noise, three is a pattern she'll ask about."""
    from backend.knowledge.context import active_contexts, confirmable_context, refresh_contexts

    async with db() as s:  # a single recruiter thread is not yet a pattern
        s.add(_email("u1", 0, "interview availability", "onsite next week",
                     frm="recruiter@lever.co", thread="t0"))
        await s.commit()
    await refresh_contexts("u1", now=NOW)
    assert not any(c.kind == "job_search" for c in await active_contexts("u1", now=NOW))

    async with db() as s:  # two more distinct recruiter threads -> a real pattern
        s.add(_email("u1", 1, "onsite loop scheduling", "your interview panel", thread="t1"))
        s.add(_email("u1", 2, "referral for the role", "recruiter follow-up", thread="t2"))
        await s.commit()
    await refresh_contexts("u1", now=NOW)

    js = next((c for c in await active_contexts("u1", now=NOW) if c.kind == "job_search"), None)
    assert js is not None and js.confidence >= 0.75
    assert (await confirmable_context("u1", now=NOW)).kind == "job_search"


@pytest.mark.asyncio
async def test_corroborating_signals_cross_the_confirm_threshold(db):
    """noisy-or: one signal nudges a season but stays below the ask bar; a second,
    independent signal tips it over — and it now generalizes past travel (job_search
    from a calendar event + a watch)."""
    from backend.knowledge.context import active_contexts, confirmable_context, refresh_contexts

    async with db() as s:  # one calendar signal — a nudge, not an assertion
        s.add(CalendarEntry(user_id="u1", title="onsite interview at acme",
                            start_time=NOW + timedelta(days=3)))
        await s.commit()
    await refresh_contexts("u1", now=NOW)
    js = next(c for c in await active_contexts("u1", now=NOW) if c.kind == "job_search")
    assert 0.5 <= js.confidence < 0.75
    assert await confirmable_context("u1", now=NOW) is None

    async with db() as s:  # a second, independent signal in the same domain
        s.add(Watch(user_id="u1", watch_type="reply", subject_key="acme recruiter",
                    title="recruiter follow-up", status="active"))
        await s.commit()
    await refresh_contexts("u1", now=NOW + timedelta(minutes=5))
    js = next(c for c in await active_contexts("u1", now=NOW) if c.kind == "job_search")
    assert js.confidence >= 0.75
    assert (await confirmable_context("u1", now=NOW)).kind == "job_search"


# ── focus windows ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_focus_creates_high_confidence_window_that_expires(db):
    from backend.knowledge.context import active_contexts, render_context_block, set_focus

    kind = await set_focus("u1", "fundraising", days=14, now=NOW)
    assert kind == "fundraising"

    ctxs = await active_contexts("u1", now=NOW)
    fr = next(c for c in ctxs if c.kind == "fundraising")
    assert fr.source == "focus_window" and fr.confidence >= 0.9
    assert "you're fundraising" in await render_context_block("u1", now=NOW)

    # past its horizon it's no longer active
    assert not any(c.kind == "fundraising" for c in await active_contexts("u1", now=NOW + timedelta(days=15)))


@pytest.mark.asyncio
async def test_focus_window_outranks_inference(db):
    from backend.knowledge.context import active_contexts, refresh_contexts, set_focus

    await set_focus("u1", "fundraising", days=14, now=NOW)
    async with db() as s:  # a competing weak goal signal for the same kind
        s.add(Goal(user_id="u1", title="raise a seed round", category="financial", status="active"))
        await s.commit()
    await refresh_contexts("u1", now=NOW)

    fr = next(c for c in await active_contexts("u1", now=NOW) if c.kind == "fundraising")
    assert fr.source == "focus_window" and fr.confidence >= 0.9  # inference didn't clobber it


# ── it weights the attention ranker ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_context_reorders_the_watch_bar(db):
    from backend.knowledge.attention import rank_attention
    from backend.knowledge.context import set_focus

    await set_focus("u1", "fundraising", days=14, now=NOW)
    async with db() as s:
        s.add_all([_card("u1", "Sequoia · term sheet"), _card("u1", "lunch order")])
        await s.commit()

    items = {it["title"]: it["priority"] for it in await rank_attention("u1", now=NOW)}
    assert items["Sequoia · term sheet"] > items["lunch order"]  # fundraising context lifts the investor card


# ── it weights email importance ─────────────────────────────────────────────

def test_email_context_match_boost():
    from backend.integrations.email_importance import ScoringContext, score_email
    from backend.integrations.composio_client import NormalizedGmailMessage

    msg = NormalizedGmailMessage(
        gmail_message_id="m1", thread_id="t1", from_address="partner@sequoia.com", from_name="P",
        to_addresses=[], cc_addresses=[], subject="Series A term sheet", snippet="", body_text="attached",
        labels=[], is_important=False, is_starred=False, is_sent=False, internal_date=NOW,
    )
    plain = score_email(msg, ScoringContext())
    with_ctx = score_email(msg, ScoringContext(context_keywords=["series", "term sheet", "investor"]))
    assert "context_match" in with_ctx.signals
    assert with_ctx.score > plain.score


# ── it tightens watch cadence ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_context_tightens_relevant_watch_cadence(db):
    from backend.knowledge.context import set_focus
    from backend.proactive.watches import create_watch

    await set_focus("u1", "fundraising", days=14, now=NOW)
    rel_id = await create_watch("u1", "reply", "sequoia partner", title="sequoia investor reply", importance=50)
    off_id = await create_watch("u1", "web", "ramen spots", title="best ramen in town", importance=50)

    async with db() as s:
        rel = await s.get(Watch, rel_id)
        off = await s.get(Watch, off_id)
    assert rel.next_check < off.next_check        # the fundraising watch checks sooner
    assert rel.importance == off.importance == 50  # stored importance is unchanged (context is transient)


# ── it nudges the delivery tier ──────────────────────────────────────────────

def test_shift_tier_pure():
    from backend.integrations.delivery_policy import shift_tier
    assert shift_tier("critical", -1) == "critical"   # a bill-bounce never goes quiet
    assert shift_tier("critical", 1) == "critical"
    assert shift_tier("medium", 1) == "high"
    assert shift_tier("high", 1) == "high"             # up-bump caps at high
    assert shift_tier("high", -1) == "medium"
    assert shift_tier("low", -1) == "low"              # down-bump floors at low


@pytest.mark.asyncio
async def test_delivery_tier_shift_by_context(db):
    from backend.knowledge.context import delivery_tier_shift, set_focus

    await set_focus("u1", "fundraising", days=14, now=NOW)
    assert await delivery_tier_shift("u1", "sequoia term sheet is ready", now=NOW) == 1
    assert await delivery_tier_shift("u1", "your spotify renews tomorrow", now=NOW) == -1


@pytest.mark.asyncio
async def test_context_shifts_real_delivery(db, monkeypatch):
    from delivery.messages import TextMessage

    from backend.integrations.notify import deliver_proactive
    from backend.knowledge.context import set_focus

    calls = {"wa": 0}

    async def fake_wa(self, phone, messages):
        calls["wa"] += 1
        return ["w"]

    monkeypatch.setattr("delivery.whatsapp.WhatsAppChannel.send_many", fake_wa)
    await set_focus("u1", "fundraising", days=14, now=NOW)  # u1 has phone "+1", no app

    # a medium surface ABOUT the focus -> bumped to high -> interrupts
    assert await deliver_proactive("u1", [TextMessage(body="sequoia replied on the term sheet")], tier="medium") == "whatsapp"
    assert calls["wa"] == 1
    # an off-focus medium surface during the focus window -> bumped to low -> held
    assert await deliver_proactive("u1", [TextMessage(body="your spotify subscription renews tomorrow")], tier="medium") == "held"
    assert calls["wa"] == 1  # no extra send


# ── slice 3: confirmation (high-confidence + significant -> ask once, §8) ─────

def _ctx(uid, kind, conf, source="inferred", evidence=None, amp=None):
    return Context(user_id=uid, kind=kind, confidence=conf, state="active", source=source,
                   evidence=evidence or {}, domains={"amplify": amp or [kind], "damp": []})


@pytest.mark.asyncio
async def test_confirmable_only_significant_high_and_inferred(db):
    """The detector fires for an inferred SIGNIFICANT season over threshold, and for
    nothing else — soft seasons, low confidence, focus windows and confirmed/declined
    contexts are all silent."""
    from backend.knowledge.context import confirmable_context

    async with db() as s:
        s.add_all([
            _ctx("u1", "travel", 0.9),                        # significant + high  -> the one
            _ctx("u1", "health", 0.95),                       # high but not significant
            _ctx("u1", "fundraising", 0.6),                   # significant but below 0.75
            _ctx("u1", "wedding", 0.9, source="focus_window"),  # explicit already
            _ctx("u1", "launch", 0.9, source="confirmed"),    # already confirmed
            _ctx("u1", "exam", 0.9, evidence={"declined": True}),  # already declined
        ])
        await s.commit()

    ctx = await confirmable_context("u1", now=NOW)
    assert ctx is not None and ctx.kind == "travel"


@pytest.mark.asyncio
async def test_confirm_pins_and_survives_refresh(db):
    """A yes flips the season to source=confirmed at high confidence, drops it out of
    the ask queue, and refresh can't lower it back while the signal persists."""
    from backend.knowledge.context import (
        active_contexts, confirm_context_kind, confirmable_context, refresh_contexts,
    )

    async with db() as s:  # flight watch -> inferred travel at 0.8
        s.add(Watch(user_id="u1", watch_type="flight", subject_key="SQ1:2026-08-28",
                    title="flight SQ1", status="active"))
        await s.commit()
    await refresh_contexts("u1", now=NOW)
    assert (await confirmable_context("u1", now=NOW)).kind == "travel"

    assert await confirm_context_kind("u1", "travel", now=NOW) is True
    travel = next(c for c in await active_contexts("u1", now=NOW) if c.kind == "travel")
    assert travel.source == "confirmed" and travel.confidence >= 0.95
    assert await confirmable_context("u1", now=NOW) is None       # no longer asks

    await refresh_contexts("u1", now=NOW + timedelta(hours=2))    # signal still present
    travel = next(c for c in await active_contexts("u1", now=NOW) if c.kind == "travel")
    assert travel.source == "confirmed" and travel.confidence >= 0.95  # inference didn't clobber it


@pytest.mark.asyncio
async def test_decline_damps_and_stays_declined_across_refresh(db):
    """A no damps the season below the surface line and marks it declined, so it stops
    asserting and refresh won't bounce it back up or re-ask."""
    from backend.knowledge.context import (
        active_contexts, confirmable_context, context_keywords,
        decline_context_kind, refresh_contexts,
    )

    async with db() as s:
        s.add(Watch(user_id="u1", watch_type="flight", subject_key="SQ1:2026-08-28",
                    title="flight SQ1", status="active"))
        await s.commit()
    await refresh_contexts("u1", now=NOW)

    assert await decline_context_kind("u1", "travel", now=NOW) is True
    travel = next(c for c in await active_contexts("u1", now=NOW) if c.kind == "travel")
    assert travel.confidence < 0.45 and (travel.evidence or {}).get("declined") is True
    assert await confirmable_context("u1", now=NOW) is None
    assert not any(k in ("flight", "trip") for k in await context_keywords("u1", now=NOW))  # out of the prompt

    await refresh_contexts("u1", now=NOW + timedelta(hours=2))    # signal still present
    travel = next(c for c in await active_contexts("u1", now=NOW) if c.kind == "travel")
    assert travel.confidence < 0.45 and (travel.evidence or {}).get("declined") is True  # still damped
    assert await confirmable_context("u1", now=NOW) is None       # still doesn't re-ask


@pytest.mark.asyncio
async def test_confirmed_season_decays_and_closes_when_signal_lapses(db):
    """A confirmed season isn't permanent — when its signal is gone (trip over) it
    decays and closes like any other, releasing its weights."""
    from backend.knowledge.context import (
        active_contexts, confirm_context_kind, refresh_contexts,
    )

    async with db() as s:
        s.add(Watch(user_id="u1", watch_type="flight", subject_key="SQ1:2026-08-28",
                    title="flight SQ1", status="active"))
        await s.commit()
    await refresh_contexts("u1", now=NOW)
    await confirm_context_kind("u1", "travel", now=NOW)

    async with db() as s:  # the trip is over — the flight watch closes
        w = (await s.execute(select(Watch).where(Watch.user_id == "u1"))).scalar_one()
        w.status = "closed"
        await s.commit()

    # 0.95 -> 0.57 -> 0.34 -> 0.21 -> below floor, closed
    for h in (6, 12, 18, 24):
        await refresh_contexts("u1", now=NOW + timedelta(hours=h))
    assert not any(c.kind == "travel" for c in await active_contexts("u1", now=NOW))


@pytest.mark.asyncio
async def test_executors_flip_state(db):
    """The card-tap executors are deterministic — no second LLM call — and settle the
    card (ok=True) only when they actually moved a live context."""
    from backend.cards.executors import confirm_context, decline_context
    from backend.knowledge.context import active_contexts

    async with db() as s:
        s.add_all([_ctx("u1", "travel", 0.9, amp=["flight"]), _ctx("u2", "fundraising", 0.9)])
        await s.commit()

    out, ok = await confirm_context("u1", {"kind": "travel"})
    assert ok and out and "front of mind" in out[0].body
    assert next(c for c in await active_contexts("u1", now=NOW) if c.kind == "travel").source == "confirmed"

    out, ok = await decline_context("u2", {"kind": "fundraising"})
    assert ok and out  # quiet ack
    assert (next(c for c in await active_contexts("u2", now=NOW) if c.kind == "fundraising").evidence or {}).get("declined")

    out, ok = await confirm_context("u1", {"kind": "exam"})  # no such active season -> nothing to pin
    assert ok is False


@pytest.mark.asyncio
async def test_confirmation_trigger_asks_once(db, monkeypatch):
    """End to end: the deterministic check hands ONE grounded stimulus to the loop
    (wired to the confirm/decline executors) and dedups so a season is asked at most
    once per window."""
    import backend.proactive.checks as checks
    from backend.knowledge.context import refresh_contexts
    from backend.proactive.context_confirm import maybe_confirm_context

    async with db() as s:
        s.add(Watch(user_id="u1", watch_type="flight", subject_key="SQ1:2026-08-28",
                    title="flight SQ1", status="active"))
        await s.commit()
    await refresh_contexts("u1", now=NOW)

    seen = []

    async def fake_brain(state, config=None):
        seen.append(state["raw_input"])
        return {}

    monkeypatch.setattr(checks, "_invoke_brain", fake_brain)

    await maybe_confirm_context("u1", now_utc=NOW)
    assert len(seen) == 1
    stim = seen[0]
    assert "context_confirm" in stim
    assert '"tool":"confirm_context"' in stim and '"tool":"decline_context"' in stim
    assert '"kind":"travel"' in stim

    await maybe_confirm_context("u1", now_utc=NOW + timedelta(hours=1))   # deduped
    assert len(seen) == 1


# ── slice 3b: Context Assembly — retrieval pointers (Trigger tier, §6.3) ──────

@pytest.mark.asyncio
async def test_pointers_attach_only_season_matched_rows(db):
    """For an active season, the pointers are exactly the watches / commitments /
    upcoming events whose text matches that season's domain — and nothing else."""
    from backend.knowledge.context import CONTEXT_DOMAINS, context_pointers

    async with db() as s:
        s.add(_ctx("u1", "travel", 0.8, amp=sorted(CONTEXT_DOMAINS["travel"]["amplify"])))
        # matches the travel domain
        s.add(Watch(user_id="u1", watch_type="flight", subject_key="SQ516",
                    title="flight SQ516 status", status="active", importance=60))
        s.add(OpenLoop(user_id="u1", content="renew swiss visa before the trip", status="active"))
        s.add(CalendarEntry(user_id="u1", title="aspen ski trip", start_time=NOW + timedelta(days=5)))
        # off-season noise that must NOT ride along
        s.add(Watch(user_id="u1", watch_type="bill", subject_key="spotify",
                    title="spotify renewal", status="active", importance=40))
        s.add(OpenLoop(user_id="u1", content="buy groceries", status="active"))
        s.add(CalendarEntry(user_id="u1", title="dentist", start_time=NOW + timedelta(days=3)))
        await s.commit()

    groups = await context_pointers("u1", now=NOW)
    assert len(groups) == 1 and groups[0]["kind"] == "travel"
    labels = {p["label"] for p in groups[0]["pointers"]}
    assert {p["type"] for p in groups[0]["pointers"]} == {"watch", "commitment", "event"}
    assert "flight SQ516 status" in labels and "aspen ski trip" in labels
    assert any("swiss visa" in l for l in labels)
    assert not any(("spotify" in l or "groceries" in l or "dentist" in l) for l in labels)


@pytest.mark.asyncio
async def test_pointers_surface_top_two_seasons(db):
    """Only the two highest-confidence seasons attach pointers — the rest stay quiet."""
    from backend.knowledge.context import CONTEXT_DOMAINS, context_pointers

    async with db() as s:
        s.add(_ctx("u1", "fundraising", 0.9, amp=sorted(CONTEXT_DOMAINS["fundraising"]["amplify"])))
        s.add(_ctx("u1", "travel", 0.8, amp=sorted(CONTEXT_DOMAINS["travel"]["amplify"])))
        s.add(_ctx("u1", "exam", 0.7, amp=sorted(CONTEXT_DOMAINS["exam"]["amplify"])))
        s.add(OpenLoop(user_id="u1", content="email the investor back", status="active"))
        s.add(OpenLoop(user_id="u1", content="book the flight", status="active"))
        s.add(OpenLoop(user_id="u1", content="study for the exam", status="active"))
        await s.commit()

    kinds = [g["kind"] for g in await context_pointers("u1", now=NOW)]
    assert kinds == ["fundraising", "travel"]   # exam (0.7) dropped by the cap


@pytest.mark.asyncio
async def test_pointers_capped_per_season(db):
    """A season with many matches yields a handful of pointers, never an inventory."""
    from backend.knowledge.context import (
        CONTEXT_DOMAINS, _MAX_POINTERS_PER_CONTEXT, context_pointers,
    )

    async with db() as s:
        s.add(_ctx("u1", "fundraising", 0.9, amp=sorted(CONTEXT_DOMAINS["fundraising"]["amplify"])))
        for i in range(6):
            s.add(OpenLoop(user_id="u1", content=f"send investor update {i}", status="active"))
        await s.commit()

    groups = await context_pointers("u1", now=NOW)
    assert len(groups) == 1 and len(groups[0]["pointers"]) == _MAX_POINTERS_PER_CONTEXT


@pytest.mark.asyncio
async def test_pointers_empty_without_confident_or_matched_context(db):
    """Below the surface bar, no pointers; and a confident season with nothing
    matching attaches nothing (no empty group)."""
    from backend.knowledge.context import context_pointers

    async with db() as s:
        s.add(_ctx("u1", "travel", 0.3, amp=["flight"]))           # below _MIN_SURFACE
        s.add(Watch(user_id="u1", watch_type="flight", subject_key="x",
                    title="flight x", status="active"))
        s.add(_ctx("u2", "travel", 0.9, amp=["flight"]))           # confident but nothing matches
        await s.commit()

    assert await context_pointers("u1", now=NOW) == []
    assert await context_pointers("u2", now=NOW) == []


@pytest.mark.asyncio
async def test_relevant_now_block_renders_into_turn_context(db):
    """The ## RELEVANT NOW block is assembled deterministically into the per-turn
    Trigger context (the wiring, end to end)."""
    from backend.knowledge.context import CONTEXT_DOMAINS
    from donna_runtime.context_builder import render_turn_context

    async with db() as s:
        s.add(_ctx("u1", "fundraising", 0.9, amp=sorted(CONTEXT_DOMAINS["fundraising"]["amplify"])))
        s.add(Watch(user_id="u1", watch_type="reply", subject_key="sequoia partner",
                    title="sequoia investor reply", status="active", importance=70))
        await s.commit()

    out = await render_turn_context({"user_id": "u1"})
    assert "## RELEVANT NOW" in out
    assert "you're fundraising" in out
    assert "watch: sequoia investor reply" in out

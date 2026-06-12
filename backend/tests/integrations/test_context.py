"""The Context Layer (CONTEXT_INTELLIGENCE_ARCHITECTURE.md).

Deterministic "season of life" engine: infers contexts from signals (goals,
flight watches), honors explicit focus windows, decays lapsed ones, and weights
the attention ranker + email importance. Zero LLM.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from db.models import Card, Context, Goal, Watch

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

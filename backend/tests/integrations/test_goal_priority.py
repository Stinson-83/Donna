"""Capability 7 — goals drive prioritization.

A deterministic goal-relevance signal (knowledge.goals) raises the importance of
things that touch an active goal: an investor email when fundraising is a goal
(the spec's example) scores higher and crosses the proactive threshold, and a
goal-relevant watch gets a higher importance. The loop still reasons; this just
weights what reaches it.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from backend.integrations.composio_client import NormalizedGmailMessage


async def _goal(db, title, *, category="financial", priority=1):
    from backend.knowledge.goals import create_or_update_goal
    return await create_or_update_goal("u1", title, category=category, priority=priority)


def _msg(**kw):
    base = dict(
        gmail_message_id="m1", thread_id="t1", from_address="partner@sequoia.com",
        from_name="A Partner", to_addresses=[], cc_addresses=[],
        subject="Series A term sheet", snippet="", body_text="our offer attached, EOD",
        labels=[], is_important=False, is_starred=False, is_sent=False,
        internal_date=datetime(2026, 8, 25, 9, 0),
    )
    base.update(kw)
    return NormalizedGmailMessage(**base)


# ── relevance service ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_relevant_goals_matches_via_category_synonyms(db):
    from backend.knowledge.goals import goal_keywords, relevant_goals

    await _goal(db, "raise a seed round", category="financial", priority=1)

    rel = await relevant_goals("u1", "Sequoia — Series A term sheet, respond by EOD")
    assert rel and rel[0]["title"] == "raise a seed round"
    assert "series" in rel[0]["terms"]  # category synonym caught it

    # unrelated text -> no match
    assert await relevant_goals("u1", "lunch with mom on saturday") == []

    kws = await goal_keywords("u1")
    assert "seed" in kws and "investor" in kws  # title term + category synonym


# ── email importance boost (the spec's investor example) ─────────────────────

@pytest.mark.asyncio
async def test_goal_email_boosts_score_over_threshold():
    from backend.integrations.email_importance import ScoringContext, score_email

    msg = _msg()

    # no goals -> ordinary email, below the 0.5 proactive threshold
    assert score_email(msg, ScoringContext()).score < 0.5

    # fundraising is a goal -> goal_match lifts it to the threshold
    res = score_email(msg, ScoringContext(goal_keywords=["series", "investor", "seed"]))
    assert "goal_match" in res.signals
    assert res.score >= 0.5


@pytest.mark.asyncio
async def test_proactive_email_surfaces_goal_relevant_and_names_the_goal(db, monkeypatch):
    import backend.integrations.proactive_email_trigger as trig

    await _goal(db, "raise a seed round", category="financial", priority=1)

    prompts: list[str] = []

    async def fake_brain(state, config=None):
        prompts.append(state["raw_input"])
        state["_outbound"] = []
        return state

    monkeypatch.setattr(trig, "_invoke_brain", fake_brain)

    await trig.maybe_surface_email("u1", _msg(gmail_message_id="m2", thread_id="t2"))

    assert len(prompts) == 1  # surfaced thanks to the goal boost
    assert "goal_match" in prompts[0]
    assert "raise a seed round" in prompts[0]  # the stimulus names the goal


# ── watch importance boost ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_goal_relevant_watch_gets_higher_importance(db):
    from backend.proactive.watches import create_watch

    await _goal(db, "raise a seed round", category="financial", priority=1)

    wid_goal = await create_watch("u1", "web", "series a market news", title="series a news", importance=45)
    wid_plain = await create_watch("u1", "web", "best ramen in town", title="ramen", importance=45)

    from db.models import Watch
    async with db() as s:
        g = await s.get(Watch, wid_goal)
        p = await s.get(Watch, wid_plain)
    assert g.importance > p.importance     # the goal-relevant watch is prioritized
    assert p.importance == 45              # the unrelated one is untouched

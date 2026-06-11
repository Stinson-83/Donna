"""The moat layer: first-class goals (+ dedupe + render) and recall_about, the
cross-connection retrieval that pulls what Donna knows about a person/topic
across every store. Uses the in-memory aiosqlite `db` fixture (seeds u1, u2)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from db.models import CalendarEntry, Fact, Goal, OpenLoop, User, Watch, utcnow


# ── goals ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_goal_create_and_dedupe(db):
    from backend.knowledge.goals import create_or_update_goal, list_active_goals, render_goals_block

    a = await create_or_update_goal("u1", "Raise a seed round", category="career", priority=1)
    b = await create_or_update_goal("u1", "raise a seed round", category="financial", priority=2)
    assert a == b  # same normalized title -> one goal, updated

    goals = await list_active_goals("u1")
    assert len(goals) == 1
    assert goals[0].priority == 2 and goals[0].category == "financial"

    block = await render_goals_block("u1")
    assert "GOALS" in block and "seed round" in block.lower()


@pytest.mark.asyncio
async def test_goals_into_user_model_context(db):
    from backend.knowledge.goals import create_or_update_goal
    from donna_runtime.context_builder import load_user_model_block

    await create_or_update_goal("u1", "lose 5kg", category="health")
    block = await load_user_model_block("u1")
    assert "lose 5kg" in block  # goals reach the loop's prompt -> drive prioritization


# ── cross-connection ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recall_about_connects_across_stores(db):
    now = utcnow()
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.living_profile = {"biography": {"relationships": [
            {"name": "Mom", "importance": 100, "birthday": "04-20"}
        ]}}
        s.add(Fact(user_id="u1", subject="mom", predicate="likes", object="lilies"))
        s.add(OpenLoop(user_id="u1", content="call mom this week", status="active"))
        s.add(CalendarEntry(user_id="u1", title="dinner with mom", start_time=now + timedelta(days=2)))
        s.add(Goal(user_id="u1", title="spend more time with mom", category="relationships", status="active"))
        await s.commit()

    from backend.knowledge.connect import recall_about

    out = await recall_about("u1", "mom")
    # the whole cross-domain picture in one shot — what makes "how did she catch that" possible
    assert "relationship" in out and "lilies" in out
    assert "call mom" in out
    assert "dinner with mom" in out
    assert "spend more time with mom" in out


@pytest.mark.asyncio
async def test_recall_about_empty(db):
    from backend.knowledge.connect import recall_about

    out = await recall_about("u1", "nonexistent topic")
    assert "don't have anything" in out


def test_tools_registered():
    from donna_runtime.tools import DONNA_TOOLS

    names = [getattr(t, "name", "") for t in DONNA_TOOLS]
    assert "track_goal" in names and "recall_about" in names and "track_interest" in names


# ── interests -> automatic web monitoring (the football scenario) ─────────

@pytest.mark.asyncio
async def test_interest_becomes_a_web_watch(db):
    from backend.knowledge.interests import add_interest, list_interests
    from backend.proactive.checks import maybe_watch_interests

    assert await add_interest("u1", "Arsenal") is True
    assert await add_interest("u1", "arsenal") is False  # deduped
    assert "Arsenal" in await list_interests("u1")

    # the runner pass turns a passive interest into active web monitoring
    await maybe_watch_interests("u1")
    async with db() as s:
        rows = (await s.execute(select(Watch).where(Watch.user_id == "u1", Watch.watch_type == "web"))).scalars().all()
    assert any(w.subject_key == "Arsenal" and w.status == "active" for w in rows)

    # idempotent — no duplicate watch on the next tick
    await maybe_watch_interests("u1")
    async with db() as s:
        rows2 = (await s.execute(select(Watch).where(Watch.user_id == "u1", Watch.subject_key == "Arsenal"))).scalars().all()
    assert len(rows2) == 1

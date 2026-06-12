"""Ambient model — the attention ranker behind the Dynamic Watch Bar.

One unified ranking across pending cards, active watches, and due tasks: covers
cross-type ordering + tiers, the deadline-proximity bump, the goal lift, the
endpoint, and user scoping.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from db.models import Card, OpenLoop, User, Watch

NOW = datetime(2026, 8, 25, 12, 0)


def _card(uid, intent, ref, **kw):
    return Card(user_id=uid, intent=intent,
                payload={"blocks": [{"type": "header", "label": intent, "ref": ref}]},
                state=kw.get("state", "pending"), expires_at=kw.get("expires_at"))


# ── ranking ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ranks_across_types_with_tiers(db):
    from backend.knowledge.attention import rank_attention

    async with db() as s:
        s.add(_card("u1", "approval", "HDFC auto-pay"))                      # decision needing a tap
        s.add(Watch(user_id="u1", watch_type="reply", subject_key="seq",
                    title="sequoia reply", importance=60, status="active"))
        s.add(OpenLoop(user_id="u1", content="rsvp wedding", status="active",
                       due_date=NOW + timedelta(days=1)))                    # due tomorrow
        await s.commit()

    items = await rank_attention("u1", now=NOW)
    kinds = [it["kind"] for it in items]
    assert kinds == ["card", "task", "watch"]            # 88 > 75 > 60
    assert items[0]["tier"] == "critical"
    assert items[0]["title"] == "HDFC auto-pay"
    assert {it["kind"] for it in items} == {"card", "task", "watch"}


@pytest.mark.asyncio
async def test_deadline_proximity_and_goal_lift(db):
    from backend.knowledge.attention import rank_attention
    from backend.knowledge.goals import create_or_update_goal

    await create_or_update_goal("u1", "raise a seed round", category="financial", priority=1)

    async with db() as s:
        # two equal-importance watches; only one touches the fundraising goal
        s.add(Watch(user_id="u1", watch_type="reply", subject_key="a",
                    title="series a investor update", importance=55, status="active"))
        s.add(Watch(user_id="u1", watch_type="web", subject_key="b",
                    title="best ramen in town", importance=55, status="active"))
        await s.commit()

    items = await rank_attention("u1", now=NOW)
    by_title = {it["title"]: it["priority"] for it in items}
    assert by_title["series a investor update"] > by_title["best ramen in town"]


@pytest.mark.asyncio
async def test_overdue_task_outranks_a_distant_one(db):
    from backend.knowledge.attention import rank_attention

    async with db() as s:
        s.add(OpenLoop(user_id="u1", content="file taxes", status="active",
                       due_date=NOW - timedelta(days=1)))    # overdue
        s.add(OpenLoop(user_id="u1", content="renew gym", status="active",
                       due_date=NOW + timedelta(days=5)))    # later this week
        await s.commit()

    items = await rank_attention("u1", now=NOW)
    assert items[0]["title"] == "file taxes" and items[0]["tier"] in ("critical", "high")


# ── endpoint + scoping ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_watchbar_endpoint_is_user_scoped(db):
    from api.cards import watchbar
    from api.push import resolve_user_id

    uid = await resolve_user_id("+bar")
    other = await resolve_user_id("+bar2")
    async with db() as s:
        s.add(_card(uid, "heads_up", "mine"))
        s.add(_card(other, "heads_up", "theirs"))
        await s.commit()

    out = await watchbar(user="+bar")
    titles = [it["title"] for it in out["items"]]
    assert titles == ["mine"]  # the other user's card is excluded

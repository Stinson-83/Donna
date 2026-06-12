"""Capability 11 — Personal Operations (admin tasks / errands).

A task is an open loop with a due_date. Covers the service (create/dedupe/list-due)
and the proactive deadline check that surfaces a task approaching its due date —
which also delivers Cap 10's deadline-never-slips guarantee.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from db.models import OpenLoop, User


_BASE = datetime(2026, 8, 1, 9, 0)  # future relative to the test clock


def _at(day, h=9):
    return _BASE.replace(hour=h) + timedelta(days=day - 1)


# ── service ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_task_and_dedupe(db):
    from backend.knowledge.tasks import create_task

    a = await create_task("u1", "renew passport", due=_at(20), category="renewal")
    # re-stating the same task updates it in place, doesn't duplicate
    b = await create_task("u1", "renew passport", due=_at(18), category="renewal")
    assert a == b

    async with db() as s:
        rows = (await s.execute(select(OpenLoop).where(OpenLoop.user_id == "u1"))).scalars().all()
        assert len(rows) == 1
        assert rows[0].category == "renewal"
        assert rows[0].due_date == _at(18)   # updated to the new deadline


@pytest.mark.asyncio
async def test_list_due_tasks_window_and_order(db):
    from backend.knowledge.tasks import create_task, list_due_tasks

    now = _at(10)
    await create_task("u1", "rsvp wedding", due=_at(12), category="rsvp")        # in window
    await create_task("u1", "file taxes", due=_at(11), category="form")          # in window, sooner
    await create_task("u1", "renew license", due=_at(40), category="renewal")    # far future
    await create_task("u1", "no-deadline errand")                               # no due_date

    due = await list_due_tasks("u1", now=now, within_days=14)
    titles = [t["content"] for t in due]
    assert titles == ["file taxes", "rsvp wedding"]  # soonest first, far-future + undated excluded


# ── proactive deadline check ─────────────────────────────────────────────────

def _stub_brain(monkeypatch):
    import backend.proactive.checks as checks
    prompts: list[str] = []

    async def fake_brain(state, config=None):
        prompts.append(state["raw_input"])
        state["_outbound"] = []
        return state

    monkeypatch.setattr(checks, "_invoke_brain", fake_brain)
    return prompts


async def _utc_user(db):
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.timezone = "UTC"
        await s.commit()


@pytest.mark.asyncio
async def test_due_task_surfaces_once(db, monkeypatch):
    from backend.knowledge.tasks import create_task
    from backend.proactive.checks import maybe_surface_due_task

    await _utc_user(db)
    await create_task("u1", "renew passport", due=_at(13), category="renewal")
    prompts = _stub_brain(monkeypatch)
    now = _at(10, 12)  # noon UTC, 3 days before

    await maybe_surface_due_task("u1", now_utc=now)
    assert len(prompts) == 1
    assert "task_due" in prompts[0]
    assert "renew passport" in prompts[0]
    assert "due in 3 days" in prompts[0]

    # already nudged -> no repeat
    await maybe_surface_due_task("u1", now_utc=now)
    assert len(prompts) == 1


@pytest.mark.asyncio
async def test_far_future_silent_and_waking_gate(db, monkeypatch):
    from backend.knowledge.tasks import create_task
    from backend.proactive.checks import maybe_surface_due_task

    await _utc_user(db)
    await create_task("u1", "renew license", due=_at(40), category="renewal")  # 30 days out
    prompts = _stub_brain(monkeypatch)

    await maybe_surface_due_task("u1", now_utc=_at(10, 12))
    assert prompts == []  # outside the 14-day lead window

    # a task due tomorrow, but it's 4am locally -> stay silent
    await create_task("u1", "rsvp dinner", due=_at(11), category="rsvp")
    await maybe_surface_due_task("u1", now_utc=_at(10, 4))
    assert prompts == []

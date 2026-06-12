"""Capability 2 depth — schedule health (conflicts + overload).

Pure detector tests (overlap, banner-ignored, no-false-positive; back-to-back run
vs a broken chain) plus the tick check end to end with a stubbed brain: a clash
surfaces first, dedups, respects waking hours; the overload path fires when there's
no clash.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from db.models import CalendarEntry, User

DAY = datetime(2026, 8, 25)


def _at(h, m=0):
    return DAY.replace(hour=h, minute=m)


def _ev(eid, title, start, end):
    return SimpleNamespace(id=eid, title=title, start_time=start, end_time=end)


# ── conflicts ────────────────────────────────────────────────────────────────

def test_detect_conflicts_overlap_only():
    from backend.proactive.schedule_health import detect_conflicts

    a = _ev("a", "Demo", _at(14, 0), _at(15, 0))
    b = _ev("b", "1:1 with Raghav", _at(14, 30), _at(15, 30))  # overlaps a by 30m
    c = _ev("c", "Gym", _at(16, 0), _at(17, 0))                # no overlap

    conflicts = detect_conflicts([a, b, c])
    assert len(conflicts) == 1
    assert {conflicts[0].a_title, conflicts[0].b_title} == {"Demo", "1:1 with Raghav"}
    assert conflicts[0].overlap_minutes == 30


def test_banner_events_dont_conflict():
    from backend.proactive.schedule_health import detect_conflicts

    banner = _ev("d", "Off-site (all day)", _at(0, 0), _at(0, 0) + timedelta(hours=21))
    x = _ev("x", "Session A", _at(10, 0), _at(11, 0))
    y = _ev("y", "Lunch", _at(12, 0), _at(13, 0))  # disjoint from x
    assert detect_conflicts([banner, x, y]) == []  # banner spans both but isn't a clash


# ── overload ─────────────────────────────────────────────────────────────────

def test_detect_overload_back_to_back_run():
    from backend.proactive.schedule_health import detect_overload

    chain = [
        _ev("1", "m1", _at(14, 0), _at(14, 30)),
        _ev("2", "m2", _at(14, 30), _at(15, 0)),
        _ev("3", "m3", _at(15, 0), _at(15, 30)),
        _ev("4", "m4", _at(15, 35), _at(16, 5)),   # 5-min gap, still no break
        _ev("5", "m5", _at(16, 5), _at(16, 35)),
    ]
    loads = detect_overload(chain)
    assert len(loads) == 1 and loads[0].count == 5


def test_a_real_break_splits_the_run():
    from backend.proactive.schedule_health import detect_overload

    events = [
        _ev("1", "m1", _at(14, 0), _at(14, 30)),
        _ev("2", "m2", _at(14, 30), _at(15, 0)),
        _ev("3", "m3", _at(15, 0), _at(15, 30)),   # only 3 before the break
        _ev("4", "m4", _at(17, 0), _at(17, 30)),   # 90-min break
        _ev("5", "m5", _at(17, 30), _at(18, 0)),
    ]
    assert detect_overload(events) == []  # no run reaches 4


# ── the tick check ───────────────────────────────────────────────────────────

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
async def test_conflict_surfaces_once_and_respects_waking(db, monkeypatch):
    from backend.proactive.schedule_health import maybe_surface_schedule_issue

    await _utc_user(db)
    async with db() as s:
        s.add_all([
            CalendarEntry(user_id="u1", title="Demo", start_time=_at(14, 0), end_time=_at(15, 0)),
            CalendarEntry(user_id="u1", title="1:1 with Raghav", start_time=_at(14, 30), end_time=_at(15, 30)),
        ])
        await s.commit()
    prompts = _stub_brain(monkeypatch)

    # 4am locally -> stay silent
    await maybe_surface_schedule_issue("u1", now_utc=_at(4, 0))
    assert prompts == []

    await maybe_surface_schedule_issue("u1", now_utc=_at(12, 0))
    assert len(prompts) == 1
    assert "schedule_conflict" in prompts[0]
    assert "Demo" in prompts[0] and "Raghav" in prompts[0]

    # same clash later the same day -> deduped
    await maybe_surface_schedule_issue("u1", now_utc=_at(13, 0))
    assert len(prompts) == 1


@pytest.mark.asyncio
async def test_overload_path_when_no_conflict(db, monkeypatch):
    from backend.proactive.schedule_health import maybe_surface_schedule_issue

    await _utc_user(db)
    async with db() as s:
        for i, (h, m) in enumerate([(14, 0), (14, 30), (15, 0), (15, 35), (16, 5)]):
            start = _at(h, m)
            s.add(CalendarEntry(user_id="u1", title=f"meeting {i+1}",
                                start_time=start, end_time=start + timedelta(minutes=30)))
        await s.commit()
    prompts = _stub_brain(monkeypatch)

    await maybe_surface_schedule_issue("u1", now_utc=_at(12, 0))
    assert len(prompts) == 1
    assert "schedule_overload" in prompts[0]
    assert "5 meetings" in prompts[0]

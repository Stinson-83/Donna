"""Capability 5 — Travel (flight tracking).

The flight-status feed is a pluggable provider (None by default — honest, no
aviation key). These tests inject a fixture provider and exercise the engine:
track_flight seeds + links a calendar event; the evaluator establishes a baseline,
then on a delay updates the linked event and surfaces the change WITH its downstream
consequence (the pickup), reusing the cross-connection engine.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from backend.travel.flights import FlightStatus, set_flight_provider, reset_flight_provider
from db.models import CalendarEntry, User, Watch

DAY = datetime(2026, 8, 25)  # future relative to the test clock


def _at(h, m=0):
    return DAY.replace(hour=h, minute=m)


def _status(**kw):
    base = dict(flight_no="SQ516", date="2026-08-25", status="scheduled",
                sched_dep=_at(10, 0), sched_arr=_at(18, 30))
    base.update(kw)
    return FlightStatus(**base)


def _provider(status):
    async def fn(flight_no, date):
        return status
    return fn


@pytest.fixture(autouse=True)
def _clean_provider():
    yield
    reset_flight_provider()


async def _seed_world(db):
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.timezone = "UTC"
        u.living_profile = {"biography": {"relationships": [{"name": "Aniroodh"}]}}
        s.add_all([
            CalendarEntry(user_id="u1", title="SQ516 landing", location="Changi T3",
                          start_time=_at(18, 30), end_time=_at(18, 40), google_event_id="g_sq"),
            CalendarEntry(user_id="u1", title="Pickup · Aniroodh", location="Changi T3",
                          start_time=_at(18, 45), end_time=_at(19, 30)),
        ])
        await s.commit()


async def _load_watch(db, wid):
    async with db() as s:
        return await s.get(Watch, wid)


# ── provider boundary ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_provider_returns_none():
    from backend.travel.flights import get_flight_status
    assert await get_flight_status("SQ516", "2026-08-25") is None


# ── tracking + dispatch ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_track_flight_creates_watch_and_links_calendar(db):
    from backend.travel.flights import track_flight

    await _seed_world(db)
    set_flight_provider(_provider(_status()))

    wid = await track_flight("u1", "sq516", "2026-08-25")
    w = await _load_watch(db, wid)
    assert w.watch_type == "flight"
    assert w.subject_key == "SQ516:2026-08-25"
    assert w.last_known_state["status"] == "scheduled"
    assert w.last_known_state["calendar_event_id"] is not None  # auto-linked by flight number
    assert w.deadline == _at(10, 0)  # scheduled departure drives the cadence


@pytest.mark.asyncio
async def test_dispatch_routes_flight_type():
    from backend.proactive.watches import _evaluator_for
    from backend.travel.flights import evaluate_flight_watch
    assert _evaluator_for("flight") is evaluate_flight_watch


# ── evaluation ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delay_updates_calendar_and_surfaces_consequence(db):
    from backend.travel.flights import evaluate_flight_watch, track_flight, _set_watch_state

    await _seed_world(db)
    set_flight_provider(_provider(_status()))
    wid = await track_flight("u1", "SQ516", "2026-08-25")

    # baseline already seeded -> a check with no change stays silent
    out = await evaluate_flight_watch(await _load_watch(db, wid))
    assert out.surface is False

    # the flight slips to 9:40pm
    set_flight_provider(_provider(_status(status="delayed", est_arr=_at(21, 40))))
    out = await evaluate_flight_watch(await _load_watch(db, wid))

    assert out.surface is True
    assert "arrival" in out.surface_prompt
    assert "Pickup" in out.surface_prompt          # downstream consequence caught
    assert "flight_update" in out.surface_prompt
    assert out.tier == "high"                       # a delay interrupts, but isn't critical

    # the linked calendar event was moved to the new arrival
    async with db() as s:
        ev = (await s.execute(select(CalendarEntry).where(CalendarEntry.google_event_id == "g_sq"))).scalar_one()
        assert ev.start_time == _at(21, 40)

    # persist the new state (as the sweep's rearm would) -> a repeat read is silent
    await _set_watch_state(wid, out.new_state)
    out2 = await evaluate_flight_watch(await _load_watch(db, wid))
    assert out2.surface is False


@pytest.mark.asyncio
async def test_no_live_data_is_silent_not_fake(db):
    from backend.travel.flights import evaluate_flight_watch, track_flight

    await _seed_world(db)
    set_flight_provider(_provider(_status()))
    wid = await track_flight("u1", "SQ516", "2026-08-25")

    reset_flight_provider()  # feed goes away
    out = await evaluate_flight_watch(await _load_watch(db, wid))
    assert out.surface is False  # no data -> no buzz, no invented "on time"


@pytest.mark.asyncio
async def test_landed_retires_the_watch(db):
    from backend.travel.flights import evaluate_flight_watch, track_flight

    await _seed_world(db)
    set_flight_provider(_provider(_status()))
    wid = await track_flight("u1", "SQ516", "2026-08-25")

    set_flight_provider(_provider(_status(status="landed")))
    out = await evaluate_flight_watch(await _load_watch(db, wid))
    assert out.retire is True


@pytest.mark.asyncio
async def test_cancelled_flight_is_critical_tier(db):
    from backend.travel.flights import evaluate_flight_watch, track_flight

    await _seed_world(db)
    set_flight_provider(_provider(_status()))
    wid = await track_flight("u1", "SQ516", "2026-08-25")

    set_flight_provider(_provider(_status(status="cancelled")))
    out = await evaluate_flight_watch(await _load_watch(db, wid))
    assert out.surface is True
    assert out.tier == "critical"   # a cancellation interrupts hard (+ voice when it lands)
    assert out.retire is True

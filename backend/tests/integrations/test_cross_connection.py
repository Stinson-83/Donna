"""Capability 17 — Cross-Connection.

The signature scenario: a flight lands later than planned, so the airport pickup
(aligned to the OLD time) and an overlapping dinner are now affected. Covers the
deterministic engine (find_connections), the proactive shift trigger
(maybe_surface_event_shift), and the calendar-resync wiring that fires it.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from db.models import CalendarEntry, OpenLoop, User

DAY = datetime(2026, 8, 25)  # future relative to the test clock, so the past-guard passes


def _at(h, m=0):
    return DAY.replace(hour=h, minute=m)


async def _seed_scenario(db, *, anchor_start):
    """Flight anchored at anchor_start; pickup aligned to 6:30pm; dinner overlapping
    9:40pm; a related open loop + the Aniroodh relationship."""
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.timezone = "UTC"
        u.living_profile = {"biography": {"relationships": [{"name": "Aniroodh"}]}}
        flight = CalendarEntry(user_id="u1", title="SQ516 · landing", location="Changi T3",
                               start_time=anchor_start, end_time=anchor_start + timedelta(minutes=10),
                               google_event_id="g_flight")
        s.add_all([
            flight,
            CalendarEntry(user_id="u1", title="Pickup · Aniroodh", location="Changi T3",
                          start_time=_at(18, 30), end_time=_at(19, 15)),
            CalendarEntry(user_id="u1", title="Team dinner", start_time=_at(21, 0), end_time=_at(22, 30)),
            OpenLoop(user_id="u1", content="confirm the changi pickup", status="active"),
        ])
        await s.commit()
        return flight.id


def _titles(*lists):
    out = []
    for lst in lists:
        out += [r["title"] for r in lst]
    return out


# ── engine ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_connections_links_shifted_event(db):
    from backend.knowledge.connections import find_connections, has_links

    anchor_id = await _seed_scenario(db, anchor_start=_at(21, 40))  # already at the new time

    conns = await find_connections("u1", anchor_id, also_around=_at(18, 30))  # old time = 6:30pm

    assert has_links(conns)
    # dinner overlaps the new 9:40pm landing
    assert "Team dinner" in [c["title"] for c in conns["conflicts"]]
    # the pickup, aligned to the OLD time, is caught via also_around
    assert "Pickup · Aniroodh" in _titles(conns["neighbors"], conns["referential_events"])
    # the open loop is linked by the shared "changi" entity
    assert any("changi pickup" in c for c in conns["open_loops"])


@pytest.mark.asyncio
async def test_no_links_when_isolated(db):
    from backend.knowledge.connections import find_connections, has_links

    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.timezone = "UTC"
        ev = CalendarEntry(user_id="u1", title="Solo focus block", start_time=_at(15, 0),
                           end_time=_at(16, 0), google_event_id="g_solo")
        s.add(ev)
        await s.commit()
        anchor_id = ev.id

    conns = await find_connections("u1", anchor_id)
    assert not has_links(conns)


# ── reactive read_connections tool (logic) ──────────────────────────────────

@pytest.mark.asyncio
async def test_summarize_connections_reads_links(db):
    from backend.knowledge.connections import summarize_connections

    await _seed_scenario(db, anchor_start=_at(21, 40))
    now = _at(12, 0)  # same future day, so the anchor is in the 30-day resolve window

    out = await summarize_connections("u1", "SQ516", now=now)
    assert "SQ516" in out
    assert "Team dinner" in out          # the clash
    assert "Pickup · Aniroodh" in out    # close in time
    assert "Aniroodh" in out             # people involved


@pytest.mark.asyncio
async def test_summarize_connections_no_match_and_isolated(db):
    from backend.knowledge.connections import summarize_connections

    await _seed_scenario(db, anchor_start=_at(21, 40))
    now = _at(12, 0)

    # a reference that matches no event
    assert "no upcoming event matches" in await summarize_connections("u1", "zzzz", now=now)

    # an event with nothing connected reads as isolated
    async with db() as s:
        s.add(CalendarEntry(user_id="u1", title="Solo focus", start_time=_at(13, 0),
                            end_time=_at(14, 0), google_event_id="g_focus"))
        await s.commit()
    out = await summarize_connections("u1", "Solo focus", now=now)
    assert "nothing else" in out


# ── proactive trigger ────────────────────────────────────────────────────────

def _stub_brain(monkeypatch):
    import backend.proactive.checks as checks
    prompts: list[str] = []

    async def fake_brain(state, config=None):
        prompts.append(state["raw_input"])
        state["_outbound"] = []
        return state

    monkeypatch.setattr(checks, "_invoke_brain", fake_brain)
    return prompts


@pytest.mark.asyncio
async def test_event_shift_surfaces_consequence(db, monkeypatch):
    from backend.proactive.cross_connect import maybe_surface_event_shift

    anchor_id = await _seed_scenario(db, anchor_start=_at(21, 40))  # stored post-shift
    prompts = _stub_brain(monkeypatch)
    now = _at(12, 0)

    await maybe_surface_event_shift("u1", anchor_id, _at(18, 30), _at(21, 40), now_utc=now)
    assert len(prompts) == 1
    p = prompts[0]
    assert "event_shift" in p and "SQ516" in p
    assert "Team dinner" in p and "Pickup" in p  # both consequences surfaced

    # same shift again -> deduped
    await maybe_surface_event_shift("u1", anchor_id, _at(18, 30), _at(21, 40), now_utc=now)
    assert len(prompts) == 1

    # a NEW time is a fresh shift -> re-fires
    async with db() as s:
        ev = (await s.execute(select(CalendarEntry).where(CalendarEntry.id == anchor_id))).scalar_one()
        ev.start_time = _at(22, 30)
        await s.commit()
    await maybe_surface_event_shift("u1", anchor_id, _at(21, 40), _at(22, 30), now_utc=now)
    assert len(prompts) == 2


@pytest.mark.asyncio
async def test_trivial_shift_and_lone_event_stay_silent(db, monkeypatch):
    from backend.proactive.cross_connect import maybe_surface_event_shift

    anchor_id = await _seed_scenario(db, anchor_start=_at(21, 40))
    prompts = _stub_brain(monkeypatch)
    now = _at(12, 0)

    # 10-minute nudge: below the material-shift floor
    await maybe_surface_event_shift("u1", anchor_id, _at(21, 30), _at(21, 40), now_utc=now)
    assert prompts == []

    # a material shift but on an isolated event -> nothing connected -> silent
    async with db() as s:
        ev = CalendarEntry(user_id="u1", title="Solo block", start_time=_at(14, 0),
                           end_time=_at(15, 0), google_event_id="g_solo2")
        s.add(ev)
        await s.commit()
        solo_id = ev.id
    await maybe_surface_event_shift("u1", solo_id, _at(9, 0), _at(14, 0), now_utc=now)
    assert prompts == []


# ── calendar-resync wiring ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calendar_resync_time_change_triggers(db, monkeypatch):
    from backend.integrations.calendar_ingest import ingest_calendar_event

    # seed a connected pickup near the original time + the relationship
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.living_profile = {"biography": {"relationships": [{"name": "Aniroodh"}]}}
        s.add(CalendarEntry(user_id="u1", title="Pickup · Aniroodh", location="Changi T3",
                            start_time=_at(18, 0), end_time=_at(18, 45)))
        await s.commit()

    prompts = _stub_brain(monkeypatch)

    def _gcal(start_iso, end_iso):
        return {"id": "g_sq516", "summary": "SQ516 landing", "location": "Changi T3",
                "start": {"dateTime": start_iso}, "end": {"dateTime": end_iso}}

    # first sync creates the event (no shift -> silent)
    await ingest_calendar_event("u1", _gcal("2026-08-25T18:30:00Z", "2026-08-25T18:40:00Z"))
    assert prompts == []

    # re-sync with a later landing -> material shift, pickup is connected -> fires
    await ingest_calendar_event("u1", _gcal("2026-08-25T21:40:00Z", "2026-08-25T21:50:00Z"))
    assert len(prompts) == 1
    assert "event_shift" in prompts[0]

    # re-sync with the same time again -> no new fire
    await ingest_calendar_event("u1", _gcal("2026-08-25T21:40:00Z", "2026-08-25T21:50:00Z"))
    assert len(prompts) == 1

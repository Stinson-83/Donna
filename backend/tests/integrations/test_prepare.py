"""Capability 14 — the Preparation Engine (backend.proactive.prepare).

Deterministic trigger: finds the soonest un-prepped upcoming event, attaches
who/when/where pointers, and hands a prepare_event stimulus to the BRAIN loop
(stubbed here). Asserts: it fires with a person-aware brief, dedups per event,
respects the lead window, and stays silent outside waking hours.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from db.models import CalendarEntry, User


async def _seed_user_event(db, *, start, title="Demo with Raghav", loc=None, rels=None):
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.timezone = "UTC"
        u.living_profile = {"biography": {"relationships": rels if rels is not None else [{"name": "Raghav"}]}}
        s.add(CalendarEntry(user_id="u1", title=title, start_time=start, location=loc))
        await s.commit()


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
async def test_prepares_soonest_event_with_person_brief(db, monkeypatch):
    from backend.proactive.prepare import maybe_prepare_upcoming

    now = datetime(2026, 4, 18, 12, 0)          # noon UTC — waking hours
    await _seed_user_event(db, start=now + timedelta(hours=3))  # today 3pm
    prompts = _stub_brain(monkeypatch)

    await maybe_prepare_upcoming("u1", now_utc=now)

    assert len(prompts) == 1
    p = prompts[0]
    assert "prepare_event" in p
    assert "Demo with Raghav" in p
    assert "today at 3:00 pm" in p
    assert "Raghav" in p and "someone you know" in p

    # one prep per event — a later tick the same day does not re-fire
    await maybe_prepare_upcoming("u1", now_utc=now + timedelta(hours=1))
    assert len(prompts) == 1


@pytest.mark.asyncio
async def test_lead_window_and_waking_hours(db, monkeypatch):
    from backend.proactive.prepare import maybe_prepare_upcoming

    now = datetime(2026, 4, 18, 12, 0)
    await _seed_user_event(db, start=now + timedelta(hours=40))  # well outside the 20h lead window
    prompts = _stub_brain(monkeypatch)

    await maybe_prepare_upcoming("u1", now_utc=now)
    assert prompts == []  # too far out — nothing to prep yet

    # an in-window event, but it's 4am locally -> stay silent (no 3am briefs)
    async with db() as s:
        s.add(CalendarEntry(user_id="u1", title="Standup", start_time=now + timedelta(hours=6)))
        await s.commit()
    await maybe_prepare_upcoming("u1", now_utc=datetime(2026, 4, 18, 4, 0))
    assert prompts == []


@pytest.mark.asyncio
async def test_no_person_match_still_prepares_without_who(db, monkeypatch):
    from backend.proactive.prepare import maybe_prepare_upcoming

    now = datetime(2026, 4, 18, 9, 0)
    await _seed_user_event(db, start=now + timedelta(hours=2), title="Dentist", rels=[{"name": "Raghav"}])
    prompts = _stub_brain(monkeypatch)

    await maybe_prepare_upcoming("u1", now_utc=now)

    assert len(prompts) == 1
    assert "Dentist" in prompts[0]
    assert "someone you know" not in prompts[0]  # no relationship named in the title

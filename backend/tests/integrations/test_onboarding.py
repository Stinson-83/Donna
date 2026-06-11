"""Onboarding backfill — pulls calendar into entries and derives relationships
from attendees + email senders, without clobbering existing profile data.
Uses the in-memory aiosqlite `db` fixture (seeds u1, u2)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from db.models import CalendarEntry, User

_EVENTS = [
    {"id": "e1", "summary": "1:1 with Priya",
     "start": {"dateTime": "2026-04-18T10:00:00+08:00"},
     "end": {"dateTime": "2026-04-18T10:30:00+08:00"},
     "attendees": [{"email": "priya@co.com", "displayName": "Priya"},
                   {"email": "me@me.com", "self": True}]},
    {"id": "e2", "summary": "Dentist", "start": {"date": "2026-04-19"}, "attendees": []},
    {"id": "e3", "summary": "Sync with Priya",
     "start": {"dateTime": "2026-04-20T09:00:00+08:00"},
     "attendees": [{"email": "priya@co.com", "displayName": "Priya"}]},
]


def _patch_calendar(monkeypatch, events):
    async def fake_list(self, user_id, time_min, time_max, max_results=250):
        return events

    monkeypatch.setattr(
        "backend.integrations.composio_client.ComposioClient.list_calendar_events", fake_list
    )


@pytest.mark.asyncio
async def test_run_onboarding_backfills_calendar_and_relationships(db, monkeypatch):
    _patch_calendar(monkeypatch, _EVENTS)
    from backend.onboarding.service import run_onboarding

    res = await run_onboarding("u1")
    assert res["events"] == 3
    assert res["relationships"] >= 1

    async with db() as s:
        cals = (await s.execute(select(CalendarEntry).where(CalendarEntry.user_id == "u1"))).scalars().all()
        user = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
    assert len(cals) == 3
    assert user.onboarding_complete is True

    rels = user.living_profile["biography"]["relationships"]
    priya = next(r for r in rels if r["name"] == "Priya")
    assert priya["interaction_count"] == 2          # in two events
    assert priya["importance"] == min(100, 30 + 2 * 8)
    # 'me@me.com' (self) is not a relationship
    assert all(r["name"] != "me" for r in rels)


@pytest.mark.asyncio
async def test_onboarding_is_idempotent(db, monkeypatch):
    _patch_calendar(monkeypatch, _EVENTS)
    from backend.onboarding.service import run_onboarding

    await run_onboarding("u1")
    await run_onboarding("u1")  # re-run

    async with db() as s:
        cals = (await s.execute(select(CalendarEntry).where(CalendarEntry.user_id == "u1"))).scalars().all()
    assert len(cals) == 3  # upserted by event id, not duplicated


@pytest.mark.asyncio
async def test_relationships_merge_preserves_existing(db, monkeypatch):
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.living_profile = {"biography": {"relationships": [
            {"name": "Priya", "birthday": "04-20", "importance": 90}
        ]}}
        await s.commit()

    _patch_calendar(monkeypatch, [_EVENTS[0]])  # one event with Priya
    from backend.onboarding.service import run_onboarding

    await run_onboarding("u1")

    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
    priya = next(r for r in u.living_profile["biography"]["relationships"] if r["name"] == "Priya")
    assert priya["birthday"] == "04-20"          # preserved (not clobbered)
    assert priya["importance"] == 90             # max(existing, derived) kept
    assert priya["interaction_count"] == 1       # enriched by backfill


@pytest.mark.asyncio
async def test_onboarding_status(db, monkeypatch):
    from backend.onboarding.service import onboarding_status

    st = await onboarding_status("u1")
    assert st["complete"] is False
    assert st["calendar_events"] == 0

    _patch_calendar(monkeypatch, _EVENTS)
    from backend.onboarding.service import run_onboarding

    await run_onboarding("u1")
    st2 = await onboarding_status("u1")
    assert st2["complete"] is True
    assert st2["calendar_events"] == 3
    assert st2["relationships"] >= 1

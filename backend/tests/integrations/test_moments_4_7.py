"""M4-M7 baseline: action executors (real calendar where possible), the consent
OAuth flow, and the meal/birthday proactive checks. Uses the in-memory aiosqlite
`db` fixture (seeds u1, u2)."""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from backend.cards.gate import classify
from backend.cards.models import DonnaCard
from backend.cards.resolution import resolve_card_action
from backend.cards.service import persist_card
from db.models import Card, User


# ── gate tiers for the new action verbs ──────────────────────────────────

def test_action_gate_tiers():
    assert classify("book_ride", {}).tier == "L0"        # charges a card
    assert classify("order_flowers", {}).tier == "L0"    # money
    assert classify("book_restaurant", {}).tier == "L1"  # reservation as the user


# ── executors (calendar mocked) ──────────────────────────────────────────

def _patch_calendar(monkeypatch, *, fail=False):
    calls: dict = {}

    async def fake_create(self, user_id, *, title, start_iso, duration_minutes=60, location=None, description=None):
        if fail:
            raise RuntimeError("calendar not connected")
        calls.update(user_id=user_id, title=title, start_iso=start_iso)
        return {"ok": True}

    monkeypatch.setattr(
        "backend.integrations.composio_client.ComposioClient.create_calendar_event", fake_create
    )
    return calls


@pytest.mark.asyncio
async def test_book_restaurant_writes_calendar(monkeypatch):
    from backend.cards.executors import book_restaurant

    calls = _patch_calendar(monkeypatch)
    out, ok = await book_restaurant("u1", {"name": "Lotus Thai", "datetime_iso": "2026-04-18T20:00:00+08:00", "party_size": 2})
    assert ok is True
    assert "calendar" in out[0].body and "Lotus Thai" in out[0].body
    assert "Lotus Thai" in calls["title"]


@pytest.mark.asyncio
async def test_book_restaurant_honest_when_calendar_missing(monkeypatch):
    from backend.cards.executors import book_restaurant

    _patch_calendar(monkeypatch, fail=True)
    out, ok = await book_restaurant("u1", {"name": "Lotus Thai", "datetime_iso": "2026-04-18T20:00:00+08:00"})
    assert ok is False  # nothing real happened -> card stays pending
    assert "calendar" in out[0].body


@pytest.mark.asyncio
async def test_book_ride_sets_reminder(monkeypatch):
    from backend.cards.executors import book_ride

    _patch_calendar(monkeypatch)
    out, ok = await book_ride("u1", {"destination": "Changi T1", "pickup_time_iso": "2026-04-19T05:30:00+08:00", "service": "grab"})
    assert ok is True
    assert "reminder" in out[0].body and "grab" in out[0].body.lower()


@pytest.mark.asyncio
async def test_order_flowers_is_honest_stub():
    from backend.cards.executors import order_flowers

    out, ok = await order_flowers("u1", {"recipient": "mom", "item": "lilies", "amount": 1899})
    assert ok is False  # no FNP rail — don't fake a 'done'
    assert "flower-delivery" in out[0].body


# ── consent (real Composio OAuth) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_consent_starts_oauth(db, monkeypatch):
    async def fake_conn(self, user_id, app):
        return ("conn_1", f"https://composio.dev/oauth/{app}")

    monkeypatch.setattr(
        "backend.integrations.composio_client.ComposioClient.get_or_create_connection", fake_conn
    )

    card = DonnaCard.model_validate({
        "version": 1, "card_id": "c_grab", "intent": "consent_integration", "theme": "light",
        "blocks": [
            {"type": "scopes", "service": "grab", "items": ["book rides", "pay via saved card"]},
            {"type": "actions", "actions": [
                {"label": "Connect Grab", "action_id": "a_allow", "style": "primary"},
                {"label": "Not now", "action_id": "a_dismiss", "style": "secondary"},
            ]},
        ],
    })
    await persist_card("u1", card, {"a_allow": {"kind": "consent", "provider": "grab"}, "a_dismiss": {"kind": "dismiss"}})

    res = await resolve_card_action("u1", "c_grab:a_allow")
    assert res.status == "handled"
    assert "oauth/grab" in res.outbound[0].url  # a real OAuth start url

    async with db() as s:
        row = (await s.execute(select(Card).where(Card.id == "c_grab"))).scalar_one()
    assert row.state == "acted"


# ── M4 meal check-in ─────────────────────────────────────────────────────

def test_meal_window():
    from backend.proactive.checks import _meal_for_hour

    assert _meal_for_hour(13) == "lunch"
    assert _meal_for_hour(20) == "dinner"
    assert _meal_for_hour(16) is None


@pytest.mark.asyncio
async def test_meal_checkin_surfaces_once(db, monkeypatch):
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.timezone = "UTC"
        await s.commit()

    import backend.proactive.checks as checks
    surfaced: list[str] = []

    async def fake_brain(state, config=None):
        surfaced.append(state["user_id"]); state["_outbound"] = []; return state

    monkeypatch.setattr(checks, "_invoke_brain", fake_brain)

    lunch = datetime(2026, 4, 18, 13, 0)  # 13:00 UTC = lunch
    await checks.maybe_checkin_meal("u1", now_utc=lunch)
    assert surfaced == ["u1"]
    # asked once — a second tick in the window does not nag
    await checks.maybe_checkin_meal("u1", now_utc=lunch)
    assert surfaced == ["u1"]
    # outside a meal window: silent
    await checks.maybe_checkin_meal("u1", now_utc=datetime(2026, 4, 18, 16, 0))
    assert surfaced == ["u1"]


# ── M7 birthday ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_birthday_surfaces_when_near(db, monkeypatch):
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
        u.living_profile = {"biography": {"relationships": [{"name": "Mom", "birthday": "04-20"}]}}
        await s.commit()

    import backend.proactive.checks as checks
    surfaced: list[str] = []

    async def fake_brain(state, config=None):
        surfaced.append(state["user_id"]); state["_outbound"] = []; return state

    monkeypatch.setattr(checks, "_invoke_brain", fake_brain)

    await checks.maybe_surface_birthday("u1", now_utc=datetime(2026, 4, 18))  # 2 days out
    assert surfaced == ["u1"]
    # u2 has no relationships -> silent
    await checks.maybe_surface_birthday("u2", now_utc=datetime(2026, 4, 18))
    assert surfaced == ["u1"]

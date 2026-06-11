"""M2 — the flagged-email card, end to end at the card layer.

Covers: render/persist a heads_up DonnaCard, project it to a WhatsApp CTA with
the two reply buttons, and resolve taps through the action_map + §10.3 gate
(reopen re-enters the loop; dismiss settles; idempotency/freshness reject a
second tap). Uses the in-memory aiosqlite `db` fixture (conftest).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.cards.models import DonnaCard
from backend.cards.projection import card_to_whatsapp
from backend.cards.resolution import resolve_card_action
from backend.cards.service import persist_card
from db.models import Card
from delivery.messages import CTAMessage

_ROOT = Path(__file__).resolve().parents[3]
_HEADS_UP = _ROOT / "donna-design-spec" / "mocks" / "heads_up.json"

_ACTION_MAP = {
    "a_draft_reply_sequoia": {
        "kind": "reopen",
        "prompt": "draft a reply to sequoia asking for 48 hours, keeps it warm",
    },
    "a_dismiss": {"kind": "dismiss"},
}


def _heads_up_card(card_id: str | None = None) -> DonnaCard:
    card = DonnaCard.model_validate(json.loads(_HEADS_UP.read_text()))
    if card_id:
        card.card_id = card_id
    return card


@pytest.mark.asyncio
async def test_persist_and_project(db):
    card = _heads_up_card()
    await persist_card("u1", card, _ACTION_MAP)

    async with db() as s:
        row = (await s.execute(select(Card).where(Card.id == card.card_id))).scalar_one()
    assert row.intent == "heads_up"
    assert row.state == "pending"
    assert "a_draft_reply_sequoia" in row.action_map
    assert row.payload["blocks"]  # the DonnaCard rode along

    msg = card_to_whatsapp(card)
    assert isinstance(msg, CTAMessage)
    assert [b.title for b in msg.buttons] == ["Draft a reply", "Not now"]
    assert msg.buttons[0].id == f"{card.card_id}:a_draft_reply_sequoia"
    assert "*EOD*" in msg.body  # **bold** -> *bold* for WhatsApp


@pytest.mark.asyncio
async def test_tap_draft_reopens_loop(db):
    card = _heads_up_card()
    await persist_card("u1", card, _ACTION_MAP)

    res = await resolve_card_action("u1", f"{card.card_id}:a_draft_reply_sequoia")
    assert res.status == "reopen"
    assert "draft" in (res.reopen_prompt or "").lower()

    async with db() as s:
        row = (await s.execute(select(Card).where(Card.id == card.card_id))).scalar_one()
    assert row.state == "acted"
    assert row.acted_action_id == "a_draft_reply_sequoia"

    # second tap on a settled card is rejected (idempotency + freshness)
    res2 = await resolve_card_action("u1", f"{card.card_id}:a_draft_reply_sequoia")
    assert res2.status == "rejected"
    assert res2.outbound


@pytest.mark.asyncio
async def test_tap_dismiss_settles_silently(db):
    card = _heads_up_card(card_id="c_m2_dismiss")
    await persist_card("u1", card, _ACTION_MAP)

    res = await resolve_card_action("u1", "c_m2_dismiss:a_dismiss")
    assert res.status == "handled"
    assert res.outbound == []

    async with db() as s:
        row = (await s.execute(select(Card).where(Card.id == "c_m2_dismiss"))).scalar_one()
    assert row.state == "dismissed"


@pytest.mark.asyncio
async def test_tap_unknown_card_rejected(db):
    res = await resolve_card_action("u1", "nonexistent:a_x")
    assert res.status == "rejected"
    assert res.outbound  # explains, never silent


@pytest.mark.asyncio
async def test_tap_belongs_to_other_user_rejected(db):
    card = _heads_up_card(card_id="c_owned_by_u1")
    await persist_card("u1", card, _ACTION_MAP)
    # u2 cannot resolve u1's card
    res = await resolve_card_action("u2", "c_owned_by_u1:a_dismiss")
    assert res.status == "rejected"


# ── app surface projection ──────────────────────────────────────────────

def test_card_to_app_settles_resolved():
    from backend.cards.projection import card_to_app

    payload = {
        "version": 1, "card_id": "c", "intent": "heads_up", "theme": "dark",
        "blocks": [{"type": "body", "text": "x"}],
    }
    assert card_to_app(payload, "pending")["theme"] == "dark"
    assert card_to_app(payload, "acted")["theme"] == "settled"
    assert card_to_app(payload, "dismissed")["theme"] == "settled"
    assert card_to_app(payload, "expired")["theme"] == "settled"
    # the action_map never rides along to the client
    assert "action_map" not in card_to_app(payload, "pending")


# ── send_email executor + execute resolution ────────────────────────────

def _patch_send(monkeypatch, sink: dict):
    async def fake_send_gmail(self, user_id, *, body, thread_id=None, to=None, subject=None):
        sink.update(user_id=user_id, body=body, thread_id=thread_id, to=to, subject=subject)
        return {"ok": True}

    monkeypatch.setattr(
        "backend.integrations.composio_client.ComposioClient.send_gmail", fake_send_gmail
    )


@pytest.mark.asyncio
async def test_send_email_executor(monkeypatch):
    from backend.cards.executors import send_email

    sink: dict = {}
    _patch_send(monkeypatch, sink)

    out, ok = await send_email("u1", {"body": "thanks, can we take 48 hours", "thread_id": "t1"})
    assert ok is True
    assert sink["thread_id"] == "t1"
    assert "48 hours" in sink["body"]

    # nothing to send -> honest no-op
    _, ok2 = await send_email("u1", {"body": "   "})
    assert ok2 is False


@pytest.mark.asyncio
async def test_tap_send_executes_and_settles(db, monkeypatch):
    sink: dict = {}
    _patch_send(monkeypatch, sink)

    card = _heads_up_card(card_id="c_send")
    amap = {
        "a_send": {
            "kind": "execute",
            "tool": "send_email",
            "args": {"thread_id": "t1", "body": "thanks, we're keen. 48 hours to review?"},
        }
    }
    await persist_card("u1", card, amap)

    res = await resolve_card_action("u1", "c_send:a_send")
    assert res.status == "handled"
    assert sink["thread_id"] == "t1"  # actually sent via the executor

    async with db() as s:
        row = (await s.execute(select(Card).where(Card.id == "c_send"))).scalar_one()
    assert row.state == "acted"
    assert row.acted_action_id == "a_send"


@pytest.mark.asyncio
async def test_tap_execute_unknown_tool_stays_pending(db):
    card = _heads_up_card(card_id="c_unknown")
    amap = {"a_x": {"kind": "execute", "tool": "not_a_real_tool", "args": {}}}
    await persist_card("u1", card, amap)

    res = await resolve_card_action("u1", "c_unknown:a_x")
    assert res.status == "handled"
    assert res.outbound  # honest "not connected" message
    async with db() as s:
        row = (await s.execute(select(Card).where(Card.id == "c_unknown"))).scalar_one()
    assert row.state == "pending"  # not settled — can retry when the tool exists

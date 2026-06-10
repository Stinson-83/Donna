"""Hermetic coverage for the demo /chat endpoint and bubble serialization.

Stubs the pipeline (user_lookup/enrich/donna_turn/save) so no API key or DB is
needed — verifies wiring + the JSON shape a frontend renders.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

import api.chat as chat
import api.main as main
from api.chat import _serialize
from delivery.messages import (
    AudioMessage,
    Button,
    CTAMessage,
    CTAUrlMessage,
    Delay,
    ImageMessage,
    ListMessage,
    Section,
    TextMessage,
    VoiceResponseMarker,
)


def test_serialize_each_bubble_type():
    assert _serialize(TextMessage(body="hi")) == {"type": "text", "text": "hi"}
    assert _serialize(Delay(seconds=1.5)) == {"type": "delay", "seconds": 1.5}
    assert _serialize(VoiceResponseMarker()) is None
    assert _serialize(
        CTAMessage(body="go?", buttons=[Button(id="y", title="Yes")])
    ) == {"type": "cta", "text": "go?", "buttons": [{"id": "y", "title": "Yes"}]}
    assert _serialize(
        CTAUrlMessage(body="link", display_text="Open", url="https://x.com")
    ) == {"type": "cta_url", "text": "link", "display_text": "Open", "url": "https://x.com"}
    assert _serialize(ImageMessage(url="https://x/i.jpg", caption="c")) == {
        "type": "image", "url": "https://x/i.jpg", "caption": "c",
    }
    assert _serialize(AudioMessage(url="MID")) == {"type": "audio", "url": "MID"}
    assert _serialize(
        ListMessage(
            body="pick", button_label="Open",
            sections=[Section(title="S", rows=[Button(id="a", title="A")])],
        )
    ) == {
        "type": "list", "text": "pick", "button_label": "Open",
        "sections": [{"title": "S", "rows": [{"id": "a", "title": "A"}]}],
    }


def test_chat_endpoint_returns_bubbles(monkeypatch):
    async def fake_user_lookup(state):
        state["user_id"] = "u-demo"
        return state

    async def fake_enrich(state):
        return state

    async def fake_turn(state):
        state["_outbound"] = [
            TextMessage(body="hey"),
            Delay(seconds=1.0),
            CTAMessage(body="wanna start?", buttons=[Button(id="y", title="Yes")]),
        ]
        return state

    async def fake_save(*_a, **_k):
        return None

    monkeypatch.setattr(chat, "user_lookup", fake_user_lookup)
    monkeypatch.setattr(chat, "enrich_state", fake_enrich)
    monkeypatch.setattr(chat, "donna_turn", fake_turn)
    monkeypatch.setattr(chat, "_save_message", fake_save)

    client = TestClient(main.app)
    resp = client.post("/chat", json={"message": "hi", "user": "demo-aarav"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "u-demo"
    assert [b["type"] for b in data["reply"]] == ["text", "delay", "cta"]
    assert data["reply"][2]["buttons"][0]["title"] == "Yes"


def test_chat_endpoint_brain_failure_falls_back(monkeypatch):
    async def fake_user_lookup(state):
        state["user_id"] = "u-demo"
        return state

    async def fake_enrich(state):
        return state

    async def boom(_state):
        raise RuntimeError("no api key")

    async def fake_save(*_a, **_k):
        return None

    monkeypatch.setattr(chat, "user_lookup", fake_user_lookup)
    monkeypatch.setattr(chat, "enrich_state", fake_enrich)
    monkeypatch.setattr(chat, "donna_turn", boom)
    monkeypatch.setattr(chat, "_save_message", fake_save)

    client = TestClient(main.app)
    resp = client.post("/chat", json={"message": "hi"})
    assert resp.status_code == 200
    assert resp.json()["reply"] == [{"type": "text", "text": "hm, one sec"}]

"""Dashboard card (A2) — send_dashboard_card unit tests.

Uses the in-memory DB fixture. WhatsAppChannel.send is monkeypatched so nothing
hits the Meta API; we assert on what *would* have been sent.
"""
from __future__ import annotations

import pytest

from backend.onboarding.dashboard_card import send_dashboard_card


@pytest.mark.asyncio
async def test_sends_cta_url_card_to_real_phone(db, monkeypatch):
    """A user with a real phone gets a CTAUrlMessage with their magic link."""
    sent = []

    async def _fake_send(self, phone, message):
        sent.append((phone, message))

    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "https://dash.donna.app")
    monkeypatch.setattr(settings, "whatsapp_token", "fake-token")
    import delivery.whatsapp as wa_mod

    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await send_dashboard_card("u1")

    assert len(sent) == 1
    phone, card = sent[0]
    assert phone == "+1"

    from delivery.messages import CTAUrlMessage

    assert isinstance(card, CTAUrlMessage)
    assert card.url.startswith("https://dash.donna.app/#t=")
    assert card.display_text == "open dashboard"


@pytest.mark.asyncio
async def test_skips_composio_only_user(db, monkeypatch):
    """A user whose phone is composio:<id> (no WhatsApp) gets no card."""
    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        s.add(User(id="u3", phone="composio:u3"))
        await s.commit()

    sent = []

    async def _fake_send(self, phone, message):
        sent.append((phone, message))

    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "https://dash.donna.app")
    monkeypatch.setattr(settings, "whatsapp_token", "fake-token")
    import delivery.whatsapp as wa_mod

    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await send_dashboard_card("u3")
    assert sent == []


@pytest.mark.asyncio
async def test_skips_when_dashboard_url_unset(db, monkeypatch):
    """No DASHBOARD_BASE_URL → silently skips (dev/test env)."""
    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "")
    monkeypatch.setattr(settings, "whatsapp_token", "fake-token")

    sent = []

    async def _fake_send(self, phone, message):
        sent.append((phone, message))

    import delivery.whatsapp as wa_mod

    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await send_dashboard_card("u1")
    assert sent == []


@pytest.mark.asyncio
async def test_magic_link_is_per_user(db, monkeypatch):
    """Two different users get different magic links (token is user-scoped)."""
    sent = []

    async def _fake_send(self, phone, message):
        sent.append((phone, message))

    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "https://dash.donna.app")
    monkeypatch.setattr(settings, "whatsapp_token", "fake-token")
    import delivery.whatsapp as wa_mod

    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await send_dashboard_card("u1")
    await send_dashboard_card("u2")

    assert len(sent) == 2
    url_u1 = sent[0][1].url
    url_u2 = sent[1][1].url
    assert url_u1 != url_u2

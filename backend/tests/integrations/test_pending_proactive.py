"""Pending proactive queue (A1) — backend/proactive/pending.py."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.proactive.pending import flush_pending, queue_proactive


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_queue_stores_content_and_flush_delivers_it(db, monkeypatch):
    sent = []

    async def _fake_send(self, phone, message):
        sent.append((phone, message))

    from config import settings
    monkeypatch.setattr(settings, "whatsapp_token", "")  # skip reopen template

    import delivery.whatsapp as wa_mod
    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await queue_proactive("u1", "your 9am with Arjun is confirmed.")
    assert len(sent) == 0  # nothing delivered yet — window was closed

    flushed = await flush_pending("u1", "+1")
    assert flushed is True
    assert len(sent) == 1
    assert "Arjun" in sent[0][1].body


@pytest.mark.asyncio
async def test_flush_empty_returns_false(db, monkeypatch):
    assert await flush_pending("u1", "+1") is False


@pytest.mark.asyncio
async def test_multiple_pending_flushed_in_order(db, monkeypatch):
    sent = []

    async def _fake_send(self, phone, message):
        sent.append(message.body)

    from config import settings
    monkeypatch.setattr(settings, "whatsapp_token", "")

    import delivery.whatsapp as wa_mod
    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await queue_proactive("u1", "first message")
    await queue_proactive("u1", "second message")

    await flush_pending("u1", "+1")
    assert sent == ["first message", "second message"]


@pytest.mark.asyncio
async def test_flush_drops_stale_rows(db, monkeypatch):
    from sqlalchemy import update as sql_update
    from db.models import PendingProactive
    from db.session import async_session

    sent = []

    async def _fake_send(self, phone, message):
        sent.append(message.body)

    from config import settings
    monkeypatch.setattr(settings, "whatsapp_token", "")

    import delivery.whatsapp as wa_mod
    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await queue_proactive("u1", "stale message")

    # backdate the row to 8 days ago
    stale_ts = _utcnow() - timedelta(days=8)
    async with async_session() as s:
        await s.execute(
            sql_update(PendingProactive)
            .where(PendingProactive.user_id == "u1")
            .values(created_at=stale_ts)
        )
        await s.commit()

    flushed = await flush_pending("u1", "+1")
    assert flushed is False
    assert sent == []


@pytest.mark.asyncio
async def test_flush_clears_queue_so_second_flush_is_empty(db, monkeypatch):
    sent = []

    async def _fake_send(self, phone, message):
        sent.append(message.body)

    from config import settings
    monkeypatch.setattr(settings, "whatsapp_token", "")

    import delivery.whatsapp as wa_mod
    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await queue_proactive("u1", "once only")
    await flush_pending("u1", "+1")
    await flush_pending("u1", "+1")  # second flush — should be empty
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_isolation_u1_queue_does_not_flush_to_u2(db, monkeypatch):
    sent = []

    async def _fake_send(self, phone, message):
        sent.append((phone, message.body))

    from config import settings
    monkeypatch.setattr(settings, "whatsapp_token", "")

    import delivery.whatsapp as wa_mod
    monkeypatch.setattr(wa_mod.WhatsAppChannel, "send", _fake_send)

    await queue_proactive("u1", "for u1 only")
    await flush_pending("u2", "+2")  # flushing u2 — should be empty

    assert sent == []
    # now flush u1
    await flush_pending("u1", "+1")
    assert len(sent) == 1
    assert sent[0][0] == "+1"

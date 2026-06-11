"""Single-surface proactive delivery — the user is alerted on ONE surface, never
both (no double-buzz). App push if the app is installed, else WhatsApp."""
from __future__ import annotations

import pytest

from delivery.messages import TextMessage


@pytest.mark.asyncio
async def test_one_surface_not_both(db, monkeypatch):
    from backend.integrations.notify import deliver_proactive

    calls = {"push": 0, "wa": 0}

    async def fake_push(user_id, outbound, title="donna"):
        calls["push"] += 1
        return 1

    async def fake_wa(self, phone, messages):
        calls["wa"] += 1
        return ["w1"]

    monkeypatch.setattr("backend.integrations.push.notify_outbound", fake_push)
    monkeypatch.setattr("delivery.whatsapp.WhatsAppChannel.send_many", fake_wa)

    out = [TextMessage(body="heads up")]

    # u1 has phone "+1" and no device token -> WhatsApp only
    assert await deliver_proactive("u1", out) == "whatsapp"
    assert calls == {"push": 0, "wa": 1}

    # install the app (a device token) -> app push only, WhatsApp NOT called again
    from db.models import DeviceToken
    async with db() as s:
        s.add(DeviceToken(user_id="u1", token="tok1", platform="android"))
        await s.commit()

    assert await deliver_proactive("u1", out) == "app"
    assert calls == {"push": 1, "wa": 1}  # single surface — no double-buzz

    # nothing to send
    assert await deliver_proactive("u1", []) == "none"


@pytest.mark.asyncio
async def test_no_surface_for_unreachable_identity(db, monkeypatch):
    from backend.integrations.notify import deliver_proactive
    from db.models import User

    # a composio/web identity with no device token and no real phone is unreachable
    async with db() as s:
        s.add(User(id="u_web", phone="web-demo"))
        await s.commit()

    monkeypatch.setattr("delivery.whatsapp.WhatsAppChannel.send_many",
                        lambda self, p, m: (_ for _ in ()).throw(AssertionError("should not send")))
    assert await deliver_proactive("u_web", [TextMessage(body="x")]) == "none"


@pytest.mark.asyncio
async def test_preferred_channel_overrides(db, monkeypatch):
    from sqlalchemy import select

    from backend.integrations.notify import deliver_proactive
    from db.models import DeviceToken, User

    calls = {"push": 0, "wa": 0}

    async def fake_push(user_id, outbound, title="donna"):
        calls["push"] += 1
        return 1

    async def fake_wa(self, phone, messages):
        calls["wa"] += 1
        return ["w1"]

    monkeypatch.setattr("backend.integrations.push.notify_outbound", fake_push)
    monkeypatch.setattr("delivery.whatsapp.WhatsAppChannel.send_many", fake_wa)
    out = [TextMessage(body="x")]

    # u1 has BOTH the app (token) and a phone — preference decides.
    async with db() as s:
        s.add(DeviceToken(user_id="u1", token="t", platform="android"))
        await s.commit()

    async def _set(channel):
        async with db() as s:
            u = (await s.execute(select(User).where(User.id == "u1"))).scalar_one()
            u.notify_channel = channel
            await s.commit()

    await _set("whatsapp")
    assert await deliver_proactive("u1", out) == "whatsapp"  # WhatsApp wins despite the app
    await _set("app")
    assert await deliver_proactive("u1", out) == "app"
    assert calls == {"push": 1, "wa": 1}

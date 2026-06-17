from __future__ import annotations

import hashlib
import hmac

import pytest

from backend.integrations.composio_client import (
    ComposioClient,
    verify_webhook_signature,
)


def test_verify_webhook_signature_accepts_valid() -> None:
    secret = "topsecret"
    body = b'{"event":"connection.complete"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, sig, secret) is True


def test_verify_webhook_signature_rejects_invalid() -> None:
    assert verify_webhook_signature(b"x", "deadbeef", "topsecret") is False


@pytest.mark.asyncio
async def test_get_or_create_connection_returns_url(monkeypatch) -> None:
    """Resolves the toolkit's auth_config, then mints a connect link via the v3 REST
    API (the SDK's toolkits.authorize path is deprecated for managed OAuth configs)."""
    captured: dict = {}

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    class FakeHTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            captured["get_url"] = url
            return FakeResp({"items": [{"toolkit": {"slug": "gmail"}, "id": "ac_gmail"}]})

        async def post(self, url, headers=None, json=None):
            captured["post_url"] = url
            captured["post_body"] = json
            return FakeResp(
                {"connected_account_id": "ca_123", "redirect_url": "https://connect.composio.dev/link/lk_abc"}
            )

    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeHTTP())

    client = ComposioClient(api_key="x")
    cid, url = await client.get_or_create_connection(user_id="u1", app="GMAIL")
    assert cid == "ca_123"
    assert url.startswith("https://connect.composio.dev/")
    # GMAIL → toolkit slug 'gmail' resolves to its auth_config, posted with the user id
    assert "auth_configs" in captured["get_url"]
    assert captured["post_body"] == {"auth_config_id": "ac_gmail", "user_id": "u1"}


@pytest.mark.asyncio
async def test_fetch_gmail_message_normalizes_payload(monkeypatch) -> None:
    raw = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX", "IMPORTANT"],
        "snippet": "hi",
        "internalDate": "1714000000000",
        "payload": {
            "headers": [
                {"name": "From", "value": "Sarah <sarah@x.com>"},
                {"name": "To", "value": "you@y.com"},
                {"name": "Subject", "value": "term sheet"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": "aGVsbG8="}},
            ],
        },
    }

    class FakeTools:
        def execute(self, name, user_id, arguments):
            return {"data": raw}

    class FakeComposio:
        tools = FakeTools()

    monkeypatch.setattr(
        "backend.integrations.composio_client._composio", lambda: FakeComposio()
    )

    client = ComposioClient(api_key="x")
    msg = await client.fetch_gmail_message(
        user_id="u1", message_id="m1", include_body=True
    )
    assert msg.gmail_message_id == "m1"
    assert msg.thread_id == "t1"
    assert msg.from_address == "sarah@x.com"
    assert msg.from_name == "Sarah"
    assert msg.subject == "term sheet"
    assert "hello" in (msg.body_text or "")
    assert msg.is_important is True
    assert "IMPORTANT" in msg.labels

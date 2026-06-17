"""Web-dashboard magic-link auth — endpoints + dependency (build plan B1).

Exercises the real flow against the in-memory DB fixture (seeded users u1/u2): mint a
magic link → exchange for a session → resolve a request by Bearer, with the legacy
`?user=` fallback and the `require_auth` lockdown. Tokens are signed with the module's
own (ephemeral, per-process) secret, so mint and verify agree without touching env.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.auth import ExchangeBody, exchange, mint_magic_link, resolve_request_user
from backend.auth.tokens import (
    SESSION,
    mint_magic_token,
    mint_session_token,
    verify_token,
)


@pytest.mark.asyncio
async def test_exchange_magic_for_session(db):
    res = await exchange(ExchangeBody(magic=mint_magic_token("u1")))
    assert res["user_id"] == "u1"
    assert verify_token(res["session_token"], purpose=SESSION) == "u1"


@pytest.mark.asyncio
async def test_exchange_rejects_a_bad_or_wrong_purpose_token(db):
    with pytest.raises(HTTPException) as e:
        await exchange(ExchangeBody(magic="not.a.token"))
    assert e.value.status_code == 401
    # a session token must NOT be exchangeable as a magic token
    with pytest.raises(HTTPException):
        await exchange(ExchangeBody(magic=mint_session_token("u1")))


@pytest.mark.asyncio
async def test_bearer_session_resolves_the_user(db):
    bearer = f"Bearer {mint_session_token('u1')}"
    assert await resolve_request_user(bearer, None) == "u1"


@pytest.mark.asyncio
async def test_bearer_wins_over_the_user_param(db):
    # a Bearer for u1 must override a conflicting ?user=+2
    bearer = f"Bearer {mint_session_token('u1')}"
    assert await resolve_request_user(bearer, "+2") == "u1"


@pytest.mark.asyncio
async def test_user_param_fallback_when_no_bearer(db):
    # legacy/demo path: ?user=<phone> resolves via resolve_user_id (u1 has phone "+1")
    assert await resolve_request_user(None, "+1") == "u1"


@pytest.mark.asyncio
async def test_invalid_bearer_is_401_never_a_fallback(db):
    with pytest.raises(HTTPException) as e:
        await resolve_request_user("Bearer tampered.token", "+1")
    assert e.value.status_code == 401  # a bad token fails closed, doesn't fall back


@pytest.mark.asyncio
async def test_require_auth_refuses_the_user_fallback(db, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "require_auth", True)
    with pytest.raises(HTTPException) as e:
        await resolve_request_user(None, "+1")
    assert e.value.status_code == 401
    # but a valid Bearer still works under lockdown
    assert await resolve_request_user(f"Bearer {mint_session_token('u1')}", None) == "u1"


@pytest.mark.asyncio
async def test_isolation_one_session_never_resolves_to_another_user(db):
    assert await resolve_request_user(f"Bearer {mint_session_token('u1')}", None) == "u1"
    assert await resolve_request_user(f"Bearer {mint_session_token('u2')}", None) == "u2"


@pytest.mark.asyncio
async def test_magic_link_carries_an_exchangeable_token_in_the_fragment(db, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "https://dash.donna.app")
    link = mint_magic_link("u1")
    assert link.startswith("https://dash.donna.app/#t=")
    token = link.split("#t=", 1)[1]
    res = await exchange(ExchangeBody(magic=token))
    assert res["user_id"] == "u1"

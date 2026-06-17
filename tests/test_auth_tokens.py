"""Signed magic/session tokens (build plan B1, backend/auth/tokens.py).

Pure — no API key, no DB. Every test passes an explicit secret so it never touches
settings/env.
"""
from __future__ import annotations

import pytest

from backend.auth.tokens import (
    MAGIC,
    SESSION,
    TokenError,
    mint_magic_token,
    mint_session_token,
    mint_token,
    verify_token,
)

SECRET = b"test-signing-secret"
T0 = 1_000_000  # a fixed clock


def test_round_trip_returns_the_user():
    tok = mint_session_token("u1", secret=SECRET, now=T0)
    assert verify_token(tok, purpose=SESSION, secret=SECRET, now=T0 + 10) == "u1"


def test_expired_token_is_rejected():
    tok = mint_magic_token("u1", ttl_seconds=60, secret=SECRET, now=T0)
    assert verify_token(tok, purpose=MAGIC, secret=SECRET, now=T0 + 59) == "u1"
    with pytest.raises(TokenError) as e:
        verify_token(tok, purpose=MAGIC, secret=SECRET, now=T0 + 61)
    assert e.value.reason == "expired"


def test_wrong_secret_is_a_signature_failure():
    tok = mint_session_token("u1", secret=SECRET, now=T0)
    with pytest.raises(TokenError) as e:
        verify_token(tok, purpose=SESSION, secret=b"other-secret", now=T0)
    assert e.value.reason == "bad_signature"


def test_tampered_payload_fails_signature():
    tok = mint_session_token("u1", secret=SECRET, now=T0)
    pb, sb = tok.split(".")
    forged = mint_session_token("u2", secret=b"attacker", now=T0).split(".")[0]
    with pytest.raises(TokenError) as e:
        verify_token(f"{forged}.{sb}", purpose=SESSION, secret=SECRET, now=T0)
    assert e.value.reason == "bad_signature"


def test_purpose_is_enforced():
    # a magic token must not pass as a session token (and vice-versa)
    magic = mint_magic_token("u1", secret=SECRET, now=T0)
    with pytest.raises(TokenError) as e:
        verify_token(magic, purpose=SESSION, secret=SECRET, now=T0)
    assert e.value.reason == "wrong_purpose"


@pytest.mark.parametrize("bad", ["", "nodot", "a.b.c", "@@@.###"])
def test_malformed_tokens_are_rejected(bad):
    with pytest.raises(TokenError):
        verify_token(bad, purpose=SESSION, secret=SECRET, now=T0)


def test_user_isolation_a_token_never_resolves_to_b():
    a = mint_session_token("user-a", secret=SECRET, now=T0)
    b = mint_session_token("user-b", secret=SECRET, now=T0)
    assert verify_token(a, purpose=SESSION, secret=SECRET, now=T0) == "user-a"
    assert verify_token(b, purpose=SESSION, secret=SECRET, now=T0) == "user-b"
    assert a != b  # distinct even for the same purpose (nonce)


def test_empty_user_id_is_refused_at_mint():
    with pytest.raises(ValueError):
        mint_token("", SESSION, 60, secret=SECRET, now=T0)

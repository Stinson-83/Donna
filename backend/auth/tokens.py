"""Signed, expiring tokens for the web-dashboard magic-link auth (build plan B1).

Two token purposes, one mechanism:
- a *magic* token (short TTL) rides the dashboard link Donna sends in WhatsApp;
- the dashboard exchanges it (POST /auth/exchange) for a *session* token (long TTL)
  it stores and sends as `Authorization: Bearer <session>`.

Tokens are stdlib HMAC-SHA256 signed — zero new deps, fully auditable, no DB lookup
to validate. Format: `base64url(payload).base64url(sig)`, payload a compact JSON
`{u: user_id, p: purpose, i: issued, e: expiry, n: nonce}`. The signature covers the
payload; verification is constant-time. A token carries WHO + a purpose + an expiry —
never a secret, never PII beyond the opaque user id.

Security note: the signing key is `settings.auth_secret` (env AUTH_SECRET). If it is
unset we fall back to an ephemeral per-process secret so dev works — but that means
tokens do not survive a restart or span multiple workers, so production MUST set
AUTH_SECRET (a public/static fallback would let anyone forge a token).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time

logger = logging.getLogger(__name__)

MAGIC = "magic"
SESSION = "session"
DEFAULT_MAGIC_TTL = 15 * 60            # the link is short-lived (single hop to exchange)
DEFAULT_SESSION_TTL = 30 * 24 * 3600  # the session lasts ~a month


class TokenError(Exception):
    """Verification failure. `reason` ∈ {malformed, bad_signature, expired, wrong_purpose}."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


_DEV_SECRET: str | None = None


def _secret() -> bytes:
    from config import settings

    configured = (settings.auth_secret or "").strip()
    if configured:
        return configured.encode()
    global _DEV_SECRET
    if _DEV_SECRET is None:
        _DEV_SECRET = secrets.token_hex(32)
        logger.warning(
            "AUTH_SECRET unset — using an ephemeral dev signing secret. Tokens will "
            "NOT survive a restart or span multiple workers. Set AUTH_SECRET in production."
        )
    return _DEV_SECRET.encode()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(payload_b64: str, secret: bytes) -> str:
    return _b64e(hmac.new(secret, payload_b64.encode(), hashlib.sha256).digest())


def mint_token(
    user_id: str,
    purpose: str,
    ttl_seconds: int,
    *,
    secret: bytes | None = None,
    now: float | None = None,
) -> str:
    """Sign a `{user_id, purpose, expiry}` token. Pure — pass `secret`/`now` in tests."""
    if not user_id:
        raise ValueError("user_id required")
    issued = int(now if now is not None else time.time())
    payload = {
        "u": str(user_id),
        "p": purpose,
        "i": issued,
        "e": issued + int(ttl_seconds),
        "n": secrets.token_hex(6),
    }
    pb = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    return f"{pb}.{_sign(pb, secret or _secret())}"


def verify_token(
    token: str,
    *,
    purpose: str,
    secret: bytes | None = None,
    now: float | None = None,
) -> str:
    """Return the user_id iff the token is well-formed, correctly signed, of the right
    purpose, and unexpired. Raise TokenError otherwise. Signature is checked first and
    in constant time, so a bad token never reveals its payload."""
    if not token or token.count(".") != 1:
        raise TokenError("malformed")
    pb, sb = token.split(".")
    if not hmac.compare_digest(sb, _sign(pb, secret or _secret())):
        raise TokenError("bad_signature")
    try:
        payload = json.loads(_b64d(pb))
    except Exception:
        raise TokenError("malformed")
    if payload.get("p") != purpose:
        raise TokenError("wrong_purpose")
    moment = int(now if now is not None else time.time())
    if int(payload.get("e", 0)) <= moment:
        raise TokenError("expired")
    uid = payload.get("u")
    if not uid:
        raise TokenError("malformed")
    return str(uid)


def mint_magic_token(user_id: str, *, ttl_seconds: int = DEFAULT_MAGIC_TTL,
                     secret: bytes | None = None, now: float | None = None) -> str:
    return mint_token(user_id, MAGIC, ttl_seconds, secret=secret, now=now)


def mint_session_token(user_id: str, *, ttl_seconds: int = DEFAULT_SESSION_TTL,
                       secret: bytes | None = None, now: float | None = None) -> str:
    return mint_token(user_id, SESSION, ttl_seconds, secret=secret, now=now)

"""Thin wrapper around Composio's Python SDK.

Vendor symbols (class names, app codes, trigger names) live ONLY in this
module. All callers go through ComposioClient. If Composio renames things,
the blast radius is one file.

This module covers auth + signature verification. Ingest, fetch, and
bootstrap helpers are added in later phases.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

logger = logging.getLogger(__name__)


# App codes per Composio's vocabulary. Verify against current docs.
APP_GMAIL = "GMAIL"
APP_GOOGLE_CALENDAR = "GOOGLECALENDAR"

# Composio v3 REST base. We call this directly for connection initiation because
# the pinned SDK's toolkits.authorize() hits a now-deprecated endpoint that 400s
# for composio-managed OAuth auth configs ("use /connected_accounts/link instead").
_COMPOSIO_API_BASE = "https://backend.composio.dev/api/v3"


# Trigger name constants — verify against current Composio docs at impl time.
TRIGGER_GMAIL_NEW_MESSAGE = "GMAIL_NEW_GMAIL_MESSAGE"
TRIGGER_CALENDAR_EVENT_CREATED = "GOOGLECALENDAR_NEW_CALENDAR_EVENT"
TRIGGER_CALENDAR_EVENT_UPDATED = "GOOGLECALENDAR_UPDATED_CALENDAR_EVENT"
TRIGGER_CALENDAR_EVENT_DELETED = "GOOGLECALENDAR_DELETED_CALENDAR_EVENT"


# ── Gmail message normalization ───────────────────────────────────────────


@dataclass(frozen=True)
class NormalizedGmailMessage:
    """Vendor-agnostic shape consumed by ingest + bootstrap. Built from
    Composio's wire format so changes upstream are absorbed here."""

    gmail_message_id: str
    thread_id: str
    from_address: str
    from_name: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str | None
    snippet: str | None
    body_text: str | None
    labels: list[str]
    is_important: bool
    is_starred: bool
    is_sent: bool
    internal_date: datetime


_FROM_RE = re.compile(r"^(?:\"?(?P<name>[^\"<]*?)\"?\s*<)?(?P<addr>[^>]+)>?$")


def _parse_address(raw: str) -> tuple[str | None, str]:
    if not raw:
        return None, ""
    m = _FROM_RE.match(raw.strip())
    if not m:
        return None, raw.strip()
    name = (m.group("name") or "").strip() or None
    addr = m.group("addr").strip()
    return name, addr


def _split_addresses(raw: str) -> list[str]:
    if not raw:
        return []
    return [_parse_address(part)[1] for part in raw.split(",") if part.strip()]


def _decode_body(payload: dict | None) -> str | None:
    """Walk MIME parts; prefer text/plain. Returns None if no plain text part."""
    if not payload:
        return None

    def walk(part: dict) -> str | None:
        mime = part.get("mimeType", "")
        body = part.get("body") or {}
        data = body.get("data")
        if data and mime == "text/plain":
            return base64.urlsafe_b64decode(data + "==").decode(
                "utf-8", errors="replace"
            )
        for child in part.get("parts") or []:
            found = walk(child)
            if found:
                return found
        return None

    return walk(payload)


def _normalize_gmail(raw: dict) -> NormalizedGmailMessage:
    headers = {
        (h.get("name") or "").lower(): h.get("value") or ""
        for h in (raw.get("payload") or {}).get("headers", [])
    }
    from_name, from_addr = _parse_address(headers.get("from", ""))
    labels = list(raw.get("labelIds") or [])
    internal_ms = int(raw.get("internalDate") or 0)
    internal_dt = datetime.fromtimestamp(
        internal_ms / 1000, tz=timezone.utc
    ).replace(tzinfo=None)

    return NormalizedGmailMessage(
        gmail_message_id=raw["id"],
        thread_id=raw["threadId"],
        from_address=from_addr,
        from_name=from_name,
        to_addresses=_split_addresses(headers.get("to", "")),
        cc_addresses=_split_addresses(headers.get("cc", "")),
        subject=headers.get("subject") or None,
        snippet=raw.get("snippet"),
        body_text=_decode_body(raw.get("payload")),
        labels=labels,
        is_important="IMPORTANT" in labels,
        is_starred="STARRED" in labels,
        is_sent="SENT" in labels,
        internal_date=internal_dt,
    )


def normalize_v3_gmail(data: dict) -> NormalizedGmailMessage:
    """Build a NormalizedGmailMessage from a Composio V3 GMAIL_NEW_GMAIL_MESSAGE
    webhook `data` block. The message is fully inlined in the webhook payload
    (message_text + payload.headers), so no follow-up fetch is needed."""
    headers = {
        (h.get("name") or "").lower(): h.get("value") or ""
        for h in (data.get("payload") or {}).get("headers", [])
    }
    from_name, from_addr = _parse_address(headers.get("from", ""))
    labels = list(data.get("label_ids") or [])
    msg_id = str(data.get("message_id") or data.get("id") or "")
    ts = str(data.get("message_timestamp") or "")
    try:
        internal_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        internal_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    body = data.get("message_text")
    return NormalizedGmailMessage(
        gmail_message_id=msg_id,
        thread_id=str(data.get("thread_id") or msg_id),
        from_address=from_addr,
        from_name=from_name,
        to_addresses=_split_addresses(headers.get("to", "")),
        cc_addresses=_split_addresses(headers.get("cc", "")),
        subject=headers.get("subject") or None,
        snippet=(body or "")[:200] or None,
        body_text=body,
        labels=labels,
        is_important="IMPORTANT" in labels,
        is_starred="STARRED" in labels,
        is_sent="SENT" in labels,
        internal_date=internal_dt,
    )


def _composio():  # pragma: no cover - thin import site
    from composio import Composio

    return Composio()


def verify_webhook_signature(body: bytes, sig_hex: str, secret: str) -> bool:
    """Constant-time HMAC-SHA256 verify.

    Returns False on missing inputs rather than raising — webhook routes
    treat False as 401 unauthorized.
    """
    if not sig_hex or not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_hex)


def _svix_keys(secret: str) -> list[bytes]:
    """Candidate HMAC keys from a Standard-Webhooks secret. The convention is
    base64-decode of the `whsec_`-stripped value, but Composio/secret-storage
    variations mean we try the raw form too."""
    s = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    keys: list[bytes] = []

    def _add(b: bytes):
        if b and b not in keys:
            keys.append(b)

    try:
        _add(base64.b64decode(s))          # standard: base64-decoded stripped secret
    except Exception:
        pass
    _add(s.encode())                        # raw stripped secret as key
    if s != secret:                         # whsec_-prefixed: also try the full value
        try:
            _add(base64.b64decode(secret))
        except Exception:
            pass
        _add(secret.encode())
    return keys


def _svix_expected(key: bytes, msg_id: str, timestamp: str, body: bytes) -> str:
    signed = f"{msg_id}.{timestamp}.".encode() + body
    return base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()


def _svix_received(signature_header: str) -> list[str]:
    # header: space-separated `v1,<base64sig>` entries
    return [p.split(",", 1)[1] if "," in p else p for p in (signature_header or "").split()]


def verify_svix_signature(
    secret: str, msg_id: str, timestamp: str, body: bytes, signature_header: str
) -> bool:
    """Composio V3 / Svix ('Standard Webhooks') verification.

    signed = f"{webhook-id}.{webhook-timestamp}.{raw-body}";
    sig = base64(HMAC_SHA256(key, signed)); compared (constant-time) against each
    `v1,<sig>` in `webhook-signature`. Tries every valid key derivation.
    """
    if not (secret and msg_id and timestamp and signature_header):
        return False
    received = _svix_received(signature_header)
    for key in _svix_keys(secret):
        expected = _svix_expected(key, msg_id, timestamp, body)
        for sig in received:
            if hmac.compare_digest(expected, sig):
                return True
    return False


def svix_debug(secret: str, msg_id: str, timestamp: str, body: bytes, signature_header: str) -> str:
    """Non-secret debug: the received signatures vs. every computed candidate.
    These are HMAC outputs (not the secret) — safe to log. Lets us see which
    derivation (if any) Composio used."""
    received = _svix_received(signature_header)
    cands = [_svix_expected(k, msg_id, timestamp, body) for k in _svix_keys(secret)]
    return (
        f"id={msg_id} ts={timestamp} body_len={len(body)} "
        f"received={received} computed_candidates={cands}"
    )


@dataclass(frozen=True)
class ComposioClient:
    """Stateless wrapper. SDK reads its key from env via Composio()."""

    api_key: str

    async def get_or_create_connection(
        self, user_id: str, app: str
    ) -> tuple[str, str]:
        """Return (connected_account_id, oauth_redirect_url) for a given (user, app).

        The SDK's toolkits.authorize() path is deprecated for composio-managed OAuth
        auth configs (Composio now 400s it), so we call the v3 REST API directly:
        resolve the auth_config for the app's toolkit, then POST /connected_accounts/link
        to mint the end-user redirect URL. Raises if no auth_config exists for the
        toolkit (e.g. the toolkit was never set up in this Composio account).
        """
        import httpx

        toolkit_slug = app.lower()
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=20) as http:
            cfgs = (
                await http.get(f"{_COMPOSIO_API_BASE}/auth_configs", headers=headers)
            ).json()
            auth_config_id = None
            for ac in cfgs.get("items", []):
                tk = ac.get("toolkit") or {}
                ac_slug = (tk.get("slug") if isinstance(tk, dict) else tk) or ""
                if str(ac_slug).lower() == toolkit_slug:
                    auth_config_id = ac.get("id")
                    break
            if not auth_config_id:
                raise RuntimeError(
                    f"no Composio auth config for toolkit {toolkit_slug!r} — "
                    "set it up in the Composio dashboard first"
                )
            resp = await http.post(
                f"{_COMPOSIO_API_BASE}/connected_accounts/link",
                headers=headers,
                json={"auth_config_id": auth_config_id, "user_id": user_id},
            )
            resp.raise_for_status()
            data = resp.json()
        return data["connected_account_id"], data["redirect_url"]

    async def subscribe_triggers(
        self,
        user_id: str,
        connection_id: str,
        trigger_names: Iterable[str],
    ) -> None:
        """Create Composio triggers so events are delivered to the project
        webhook. Composio v1 SDK: triggers.create(slug, user_id, trigger_config).

        Empty config uses the trigger's defaults (Gmail polls INBOX). The old
        `triggers.subscribe(user_id=, connected_account_id=, trigger_name=)` call
        did not exist in any SDK and silently failed.
        """
        composio = _composio()
        for name in trigger_names:
            try:
                trigger = composio.triggers.create(
                    slug=name,
                    user_id=user_id,
                    trigger_config={},
                )
                logger.info(
                    "subscribe_triggers: created trigger=%s id=%s user=%s",
                    name, getattr(trigger, "trigger_id", "?"), user_id,
                )
            except Exception:
                logger.exception(
                    "subscribe_triggers: failed user=%s trigger=%s", user_id, name
                )

    async def fetch_gmail_message(
        self, user_id: str, message_id: str, include_body: bool = True
    ) -> NormalizedGmailMessage:
        """Fetch one Gmail message and normalize into a vendor-agnostic shape."""
        composio = _composio()
        result = composio.tools.execute(
            "GMAIL_FETCH_MESSAGE_BY_ID",
            user_id=user_id,
            arguments={
                "message_id": message_id,
                "format": "full" if include_body else "metadata",
            },
        )
        return _normalize_gmail(result["data"])

    async def list_gmail_message_ids(
        self,
        user_id: str,
        query: str = "",
        max_results: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[str], str | None]:
        """Page through Gmail message IDs by query string.

        Returns (ids, next_page_token). next_page_token=None means EOF.
        """
        composio = _composio()
        result = composio.tools.execute(
            "GMAIL_LIST_MESSAGES",
            user_id=user_id,
            arguments={
                "q": query,
                "max_results": max_results,
                "page_token": page_token,
            },
        )
        data = result.get("data") or {}
        ids = [m["id"] for m in data.get("messages", [])]
        next_token = data.get("nextPageToken")
        return ids, next_token

    async def list_calendar_events(
        self,
        user_id: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 250,
    ) -> list[dict]:
        """List primary-calendar events in [time_min, time_max). Single events,
        i.e. recurring instances are expanded."""
        composio = _composio()
        result = composio.tools.execute(
            "GOOGLECALENDAR_LIST_EVENTS",
            user_id=user_id,
            arguments={
                "calendar_id": "primary",
                "time_min": time_min.isoformat() + "Z",
                "time_max": time_max.isoformat() + "Z",
                "max_results": max_results,
                "single_events": True,
            },
        )
        return (result.get("data") or {}).get("items", [])

    async def send_gmail(
        self,
        user_id: str,
        *,
        body: str,
        thread_id: str | None = None,
        to: str | None = None,
        subject: str | None = None,
    ) -> dict:
        """Send a new email or reply to a thread via Composio Gmail.

        thread_id present -> GMAIL_REPLY_TO_THREAD (keeps the conversation).
        Otherwise -> GMAIL_SEND_EMAIL (needs to + subject).
        """
        composio = _composio()
        if thread_id:
            slug = "GMAIL_REPLY_TO_THREAD"
            arguments: dict = {"thread_id": thread_id, "message_body": body}
            if to:
                arguments["recipient_email"] = to
        else:
            slug = "GMAIL_SEND_EMAIL"
            arguments = {
                "recipient_email": to or "",
                "subject": subject or "",
                "body": body,
            }
        return composio.tools.execute(slug, user_id=user_id, arguments=arguments)

    async def create_calendar_event(
        self,
        user_id: str,
        *,
        title: str,
        start_iso: str,
        duration_minutes: int = 60,
        location: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Create a primary-calendar event via Composio. Real artifact — used by
        the booking executors so a reservation/ride lands on the user's actual
        calendar even when the third-party rail isn't connected."""
        composio = _composio()
        arguments: dict = {
            "calendar_id": "primary",
            "summary": title,
            "start_datetime": start_iso,
            "event_duration_minutes": duration_minutes,
        }
        if location:
            arguments["location"] = location
        if description:
            arguments["description"] = description
        return composio.tools.execute(
            "GOOGLECALENDAR_CREATE_EVENT", user_id=user_id, arguments=arguments
        )

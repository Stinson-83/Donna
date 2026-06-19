"""open_dashboard tool — mints a fresh per-user magic link to the web dashboard.

Pure: no DB. Sets the current-user contextvar the tool reads, and patches the
dashboard base URL. The token core is exercised via mint_magic_link.
"""
from __future__ import annotations

import pytest

# tools.py reads the current-user contextvar from .hooks (not observability)
from donna_runtime.hooks import _CURRENT_USER_ID
from donna_runtime.tools import open_dashboard


def _text(result) -> str:
    """Flatten an MCP tool result ({"content": [{"type":"text","text":...}]}) to text."""
    if isinstance(result, dict):
        return " ".join(
            p.get("text", "") for p in (result.get("content") or []) if isinstance(p, dict)
        )
    return str(result)


@pytest.mark.asyncio
async def test_open_dashboard_returns_a_fresh_magic_link(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "https://dash.donna.app")
    tok = _CURRENT_USER_ID.set("user-42")
    try:
        out = _text(await open_dashboard.handler({}))
    finally:
        _CURRENT_USER_ID.reset(tok)
    # a real, per-user, exchangeable magic link in the URL fragment
    assert "https://dash.donna.app/#t=" in out


@pytest.mark.asyncio
async def test_two_calls_mint_distinct_links(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "https://dash.donna.app")
    tok = _CURRENT_USER_ID.set("user-42")
    try:
        a = _text(await open_dashboard.handler({}))
        b = _text(await open_dashboard.handler({}))
    finally:
        _CURRENT_USER_ID.reset(tok)
    link_a = a.split("#t=", 1)[1].strip()
    link_b = b.split("#t=", 1)[1].strip()
    assert link_a and link_b and link_a != link_b  # fresh each time (nonce)


@pytest.mark.asyncio
async def test_open_dashboard_degrades_without_base_url(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "dashboard_base_url", "")
    tok = _CURRENT_USER_ID.set("user-42")
    try:
        out = _text(await open_dashboard.handler({}))
    finally:
        _CURRENT_USER_ID.reset(tok)
    assert "#t=" not in out
    assert "dashboard" in out.lower()

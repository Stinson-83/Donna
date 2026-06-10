"""Web search lanes backing the `web_search` and `agentic_web_search` tools.

Provider: Exa (https://exa.ai). `search_web` uses Exa `/search` (with text
contents for snippets); `agentic_search` uses Exa `/answer`, which reads
sources and returns a synthesized answer plus citations. Both return a status
envelope the tools map to text:

    {"status": "ok"|"degraded"|"no_hits", "payload": ...}

When EXA_API_KEY is unset, both return status=degraded so the tool replies
"web search unavailable" rather than raising.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

_EXA_SEARCH_URL = "https://api.exa.ai/search"
_EXA_ANSWER_URL = "https://api.exa.ai/answer"
_RECENCY_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


def _degraded(reason: str) -> dict[str, Any]:
    return {"status": "degraded", "payload": {"reason": reason}}


def _headers(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key, "Content-Type": "application/json"}


def _start_published_date(recency: str | None) -> str | None:
    days = _RECENCY_DAYS.get(recency or "")
    if not days:
        return None
    start = datetime.now(timezone.utc) - timedelta(days=days)
    return start.strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def search_web(
    query: str, *, max_results: int = 5, recency: str | None = None
) -> dict[str, Any]:
    """Single-shot search. payload (when ok) is a list of {title,url,snippet}."""
    settings = get_settings()
    if not settings.exa_api_key:
        return _degraded("web search not configured")

    body: dict[str, Any] = {
        "query": query,
        "numResults": max(1, min(int(max_results), 10)),
        "type": "auto",
        "contents": {"text": {"maxCharacters": 500}},
    }
    start = _start_published_date(recency)
    if start:
        body["startPublishedDate"] = start

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                _EXA_SEARCH_URL, headers=_headers(settings.exa_api_key), json=body
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("search_web: provider error")
        return _degraded("search provider error")

    hits = [
        {
            "title": (r.get("title") or "").strip(),
            "url": (r.get("url") or "").strip(),
            "snippet": (r.get("text") or r.get("snippet") or "").strip(),
        }
        for r in (data.get("results") or [])
        if r.get("url")
    ]
    if not hits:
        return {"status": "no_hits", "payload": []}
    return {"status": "ok", "payload": hits[:max_results]}


async def agentic_search(question: str, *, max_results: int = 5) -> dict[str, Any]:
    """Read sources + synthesize via Exa /answer. payload (when ok) is
    {answer, sources:[{title,url}]}."""
    settings = get_settings()
    if not settings.exa_api_key:
        return _degraded("web search not configured")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _EXA_ANSWER_URL,
                headers=_headers(settings.exa_api_key),
                json={"query": question, "text": True},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("agentic_search: provider error")
        return _degraded("search provider error")

    answer = (data.get("answer") or "").strip()
    citations = data.get("citations") or data.get("results") or []
    sources = [
        {"title": (c.get("title") or "").strip(), "url": (c.get("url") or "").strip()}
        for c in citations
        if c.get("url")
    ][:max_results]
    if not answer and not sources:
        return {"status": "no_hits", "payload": {}}
    return {"status": "ok", "payload": {"answer": answer, "sources": sources}}

"""Deep web research backing the `research` tool.

Builds on agentic_search: fetch + synthesize, fold in an optional seed URL,
and return a structured answer with a confidence score and source list. The
`research` tool reads `answer.answer`, `.sources`, `.confidence`, `.dissent`,
`.metadata` and `trace.merged_count`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.web.search import agentic_search

logger = logging.getLogger(__name__)


@dataclass
class ResearchAnswer:
    answer: str = ""
    sources: list[Any] = field(default_factory=list)
    confidence: float = 0.0
    dissent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchTrace:
    merged_count: int = 0


async def run_web_research(
    question: str, *, top_k: int = 8, seed_url: str | None = None
) -> tuple[ResearchAnswer, ResearchTrace]:
    try:
        res = await agentic_search(question, max_results=top_k)
    except Exception:
        logger.exception("run_web_research: search failed")
        return (
            ResearchAnswer(metadata={"reason": "research provider error", "variant": "merged"}),
            ResearchTrace(merged_count=0),
        )

    status = res.get("status")
    if status == "degraded":
        reason = (res.get("payload") or {}).get("reason", "web research unavailable")
        return (
            ResearchAnswer(metadata={"reason": reason, "variant": "merged"}),
            ResearchTrace(merged_count=0),
        )
    if status == "no_hits" or not res.get("payload"):
        return (
            ResearchAnswer(metadata={"reason": "no hits", "variant": "merged"}),
            ResearchTrace(merged_count=0),
        )

    payload = res["payload"]
    answer = (payload.get("answer") or "").strip()
    sources = list(payload.get("sources") or [])
    if seed_url:
        sources = [{"title": "(seed)", "url": seed_url}, *sources]

    merged = len(sources)
    confidence = max(0.0, min(1.0, 0.4 + 0.1 * merged)) if answer else 0.0
    return (
        ResearchAnswer(
            answer=answer,
            sources=sources,
            confidence=confidence,
            dissent=None,
            metadata={"variant": "merged"},
        ),
        ResearchTrace(merged_count=merged),
    )

"""Deterministic detection of an explicit user request for a spoken reply.

Used by context_builder._detect_voice_request to decide whether to instruct
the model to emit a `voice_response` item this turn. Pure + sync: no LLM, no
I/O. Inbound voice-note mirroring is handled separately (the model sees the
message was a voice note); this only catches explicit text asks.
"""
from __future__ import annotations

import re

_VOICE_RE = re.compile(
    r"\b("
    r"voice note|voice message|voice memo|"
    r"send (?:me )?(?:a )?voice|"
    r"say it|say that|"
    r"talk to me|speak (?:to me|it|that)|"
    r"read it (?:out|aloud)|read that (?:out|aloud)|"
    r"out loud|aloud|"
    r"can you voice|voice this|in your voice"
    r")\b",
    re.IGNORECASE,
)


def detect_voice_request(text: str | None) -> bool:
    """True when the user explicitly asked for an audio/voice reply."""
    if not text:
        return False
    return bool(_VOICE_RE.search(text))

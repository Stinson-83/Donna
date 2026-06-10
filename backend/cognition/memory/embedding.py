"""Lightweight, dependency-free text embedding for offline semantic retrieval.

Hashes uni/bigrams into a fixed signed vector (feature hashing). Not as good as
a neural embedder, but deterministic, instant, and runs with no API key — enough
for in-process cosine retrieval at demo scale. Swap `embed` for a real model
(OpenAI / Voyage) when keys are available; storage + retrieval are unchanged.
"""
from __future__ import annotations

import hashlib
import math
import re

DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    tokens = _TOKEN.findall((text or "").lower())
    for i, tok in enumerate(tokens):
        grams = [tok]
        if i + 1 < len(tokens):
            grams.append(tok + " " + tokens[i + 1])
        for g in grams:
            h = int(hashlib.md5(g.encode()).hexdigest(), 16)
            idx = h % DIM
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))

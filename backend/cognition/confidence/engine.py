"""Confidence engine — turns evidence into a defensible number.

Inputs (per piece of evidence): source_quality (0..1), recency (age days),
polarity (support/contradict). Aggregate signals: amount of supporting vs
contradicting weight, recency, frequency (distinct observations), and
cross-domain consistency (agreement across topics).

Output: an integer 1..99 plus a human-readable breakdown so every score is
explainable. No magic constants without a name.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp

# Named weights — tunable, transparent.
SMOOTHING = 1.2          # Laplace-style prior pulling small samples toward 50%
RECENCY_HALFLIFE_DAYS = 45.0
FREQUENCY_CAP = 6        # diminishing returns past this many supporting observations
CONSISTENCY_BONUS = 0.06  # per extra agreeing topic (cross-domain)
MAX_CONFIDENCE = 99
MIN_CONFIDENCE = 1


@dataclass
class Evidence:
    source_quality: float
    age_days: float
    polarity: str  # "support" | "contradict"
    topic: str = ""


@dataclass
class ConfidenceResult:
    score: int
    support_weight: float
    contradict_weight: float
    recency: float
    frequency: int
    consistency: float
    rationale: str


def _recency_weight(age_days: float) -> float:
    # exponential decay; fresh evidence counts ~1.0, old evidence fades
    return exp(-max(age_days, 0.0) * (0.6931 / RECENCY_HALFLIFE_DAYS))


def score(evidence: list[Evidence]) -> ConfidenceResult:
    if not evidence:
        return ConfidenceResult(50, 0.0, 0.0, 0.0, 0, 0.0, "no evidence yet — prior of 50%")

    support_w = 0.0
    contra_w = 0.0
    support_n = 0
    support_topics: set[str] = set()
    recency_acc = 0.0

    for e in evidence:
        rw = _recency_weight(e.age_days)
        w = max(0.0, min(e.source_quality, 1.0)) * (0.5 + 0.5 * rw)
        recency_acc += rw
        if e.polarity == "contradict":
            contra_w += w
        else:
            support_w += w
            support_n += 1
            if e.topic:
                support_topics.add(e.topic)

    # base balance with smoothing toward 0.5
    base = (support_w + SMOOTHING * 0.5) / (support_w + contra_w + SMOOTHING)

    # frequency lift — more independent corroboration nudges confidence up
    freq_factor = min(support_n, FREQUENCY_CAP) / FREQUENCY_CAP  # 0..1
    base += (1 - base) * 0.35 * freq_factor

    # cross-domain consistency — agreement across distinct topics is stronger
    consistency = CONSISTENCY_BONUS * max(0, len(support_topics) - 1)
    base += (1 - base) * consistency

    # average recency of the whole set gently damps stale-only beliefs
    avg_recency = recency_acc / len(evidence)
    base *= 0.85 + 0.15 * avg_recency

    pct = int(round(base * 100))
    pct = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, pct))

    rationale = (
        f"{support_n} supporting / {sum(1 for e in evidence if e.polarity=='contradict')} contradicting, "
        f"across {len(support_topics)} topic(s); "
        f"recency {avg_recency:.2f}, frequency {min(support_n, FREQUENCY_CAP)}/{FREQUENCY_CAP}."
    )
    return ConfidenceResult(
        score=pct,
        support_weight=round(support_w, 3),
        contradict_weight=round(contra_w, 3),
        recency=round(avg_recency, 3),
        frequency=support_n,
        consistency=round(consistency, 3),
        rationale=rationale,
    )


def evidence_from_observations(observations: list[dict], now: datetime) -> list[Evidence]:
    out: list[Evidence] = []
    for o in observations:
        created = o.get("created_at") or now
        age = max(0.0, (now - created).total_seconds() / 86400.0)
        topics = o.get("topics") or []
        out.append(
            Evidence(
                source_quality=float(o.get("source_quality", 0.6)),
                age_days=age,
                polarity=o.get("polarity", "support"),
                topic=(topics[0] if topics else o.get("subject", "")),
            )
        )
    return out

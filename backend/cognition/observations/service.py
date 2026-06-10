"""Observation engine — beliefs do not come straight from memories; they emerge
from observations *across* memories. This is a small, transparent pattern miner:
each rule matches topics/keywords on a memory and emits an observation that
implies a candidate belief (with a polarity and a source quality).

Deterministic and offline. Swap the rule list for an LLM extractor later; the
downstream belief/question engines don't change.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.cognition.store import Observation

# Each rule: subject (belief key), what to look for, and the belief it implies.
RULES = [
    {
        "subject": "sleep_stress",
        "any_topics": ["sleep"],
        "co_topics": ["stress", "review", "milestone", "deadline"],
        "statement": "sleep dropped ahead of a high-stress stretch",
        "implies": "sleep predicts your stress better than workload",
        "polarity": "support",
        "source_quality": 0.8,
    },
    {
        "subject": "mornings",
        "any_topics": ["focus", "deep-work", "morning"],
        "co_topics": [],
        "statement": "focused work clustered before noon",
        "implies": "your best work happens before noon",
        "polarity": "support",
        "source_quality": 0.75,
    },
    {
        "subject": "overprepare",
        "any_topics": ["deck", "rewrite", "prep", "pitch"],
        "co_topics": ["uncertain", "review", "investor", "launch"],
        "statement": "reworked material before a high-stakes moment",
        "implies": "you overprepare when you're uncertain",
        "polarity": "support",
        "source_quality": 0.7,
    },
    {
        "subject": "priya_pricing",
        "any_topics": ["priya"],
        "co_topics": ["pricing", "price"],
        "statement": "deferred to priya on a pricing call",
        "implies": "you trust priya's judgement on pricing",
        "polarity": "support",
        "source_quality": 0.72,
    },
    {
        "subject": "outreach",
        "any_topics": ["outreach", "email", "intro", "recruiting"],
        "co_topics": ["weak", "story", "narrative", "delay", "postpone"],
        "statement": "outreach stalled while the narrative felt weak",
        "implies": "you avoid outreach when the story feels weak",
        "polarity": "support",
        "source_quality": 0.7,
    },
    # a contradicting signal — keeps confidence honest
    {
        "subject": "outreach",
        "any_topics": ["outreach", "email"],
        "co_topics": ["sent", "shipped", "confident"],
        "statement": "sent cold outreach when momentum was high",
        "implies": "you avoid outreach when the story feels weak",
        "polarity": "contradict",
        "source_quality": 0.6,
    },
]


def _matches(rule: dict, topics: list[str], content: str) -> bool:
    text = (content or "").lower()
    topset = {t.lower() for t in (topics or [])}

    def present(term: str) -> bool:
        return term in topset or term in text

    if rule["any_topics"] and not any(present(t) for t in rule["any_topics"]):
        return False
    if rule["co_topics"] and not any(present(t) for t in rule["co_topics"]):
        return False
    return True


def derive(memory) -> list[dict]:
    out = []
    for rule in RULES:
        if _matches(rule, memory.topics, memory.content):
            out.append(
                {
                    "subject": rule["subject"],
                    "statement": rule["statement"],
                    "implies": rule["implies"],
                    "polarity": rule["polarity"],
                    "source_quality": rule["source_quality"],
                    "memory_ids": [memory.id],
                    "topics": memory.topics,
                }
            )
    return out


async def add_observation(session, *, user_id: str, **fields) -> Observation:
    obs = Observation(user_id=user_id, **fields)
    session.add(obs)
    await session.flush()
    return obs


async def generate_for_memory(session, user_id: str, memory) -> list[Observation]:
    """Run the miner on one memory; create observations not already recorded."""
    created = []
    existing = (
        await session.execute(
            select(Observation).where(Observation.user_id == user_id)
        )
    ).scalars().all()
    seen = {(o.subject, o.polarity, tuple(o.memory_ids)) for o in existing}
    for d in derive(memory):
        key = (d["subject"], d["polarity"], tuple(d["memory_ids"]))
        if key in seen:
            continue
        created.append(await add_observation(session, user_id=user_id, **d))
    return created


async def list_observations(session, user_id: str, subject: str | None = None) -> list[Observation]:
    stmt = select(Observation).where(Observation.user_id == user_id)
    if subject:
        stmt = stmt.where(Observation.subject == subject)
    rows = (await session.execute(stmt.order_by(Observation.created_at.desc()))).scalars().all()
    return list(rows)

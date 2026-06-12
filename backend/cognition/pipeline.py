"""Ingestion pipeline — the chat/journal/voice surface that updates Donna's model.

Every inbound message updates the memory store and the relationship graph:

    content → memory → graph

Belief formation is no longer mined by keyword here. It happens in the BRAIN
loop via the `form_belief` tool, which writes observations + recomputes beliefs
with real (LLM) judgement. The old keyword miner is retained ONLY for seeding the
demo (`seed.py`) and its tests — pass `mine=True` to opt into it.
"""
from __future__ import annotations

from backend.cognition.beliefs.service import recompute_subject
from backend.cognition.memory.service import add_memory
from backend.cognition.observations.service import generate_for_memory
from backend.cognition.questions.service import detect_from_beliefs
from backend.cognition.relationships.service import add_edge, upsert_node

_KIND = {
    "priya": "person", "luca": "person", "mom": "person", "you": "person",
    "donna": "project", "antler": "project",
    "the raise": "goal", "sleep": "pattern", "pitch nerves": "pattern", "focus": "goal",
}


async def ingest(
    session,
    *,
    user_id: str,
    content: str,
    source_type: str = "donna_app",
    source_ref: str | None = None,
    topics: list[str] | None = None,
    entities: list[str] | None = None,
    importance: float = 0.5,
    mine: bool = False,
) -> dict:
    mem = await add_memory(
        session,
        user_id=user_id,
        content=content,
        source_type=source_type,
        source_ref=source_ref,
        topics=topics,
        entities=entities,
        importance=importance,
    )

    # Belief formation is the BRAIN's job now (form_belief). The keyword miner
    # only runs when explicitly opted in — i.e. seeding the demo.
    observations = []
    beliefs = []
    if mine:
        observations = await generate_for_memory(session, user_id, mem)
        for subject in {o.subject for o in observations}:
            b = await recompute_subject(session, user_id, subject, reason="a new memory")
            if b:
                beliefs.append(b)

    # weave entities into the graph
    if entities:
        you = await upsert_node(session, user_id=user_id, label="you", kind="person", weight=1.0)
        for ent in entities:
            node = await upsert_node(session, user_id=user_id, label=ent, kind=_KIND.get(ent.lower(), "pattern"))
            await add_edge(session, user_id=user_id, src=you.id, dst=node.id, relation="mentions")

    questions = await detect_from_beliefs(session, user_id)

    return {
        "memory_id": mem.id,
        "observations": len(observations),
        "beliefs_touched": [b.subject for b in beliefs],
        "questions_open": len(questions),
    }

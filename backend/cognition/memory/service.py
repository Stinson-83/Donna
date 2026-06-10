"""Memory service — persist and semantically retrieve memories.

Every memory is traceable to a source (conversation/message/journal/voice).
Services flush (to populate ids) but leave commit to the caller, so pipelines
can compose multiple writes atomically.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.cognition.store import Memory
from backend.cognition.memory.embedding import cosine, embed

VALID_SOURCE_TYPES = {
    "whatsapp": "WhatsApp",
    "donna_app": "Donna App",
    "journal": "Journal Entry",
    "voice": "Voice Note",
    "observation": "Observation",
    "system": "System Generated",
}


async def add_memory(
    session,
    *,
    user_id: str,
    content: str,
    source_type: str = "donna_app",
    source_ref: str | None = None,
    topics: list[str] | None = None,
    entities: list[str] | None = None,
    importance: float = 0.5,
) -> Memory:
    source = VALID_SOURCE_TYPES.get(source_type, "Donna App")
    mem = Memory(
        user_id=user_id,
        content=content,
        source=source,
        source_type=source_type,
        source_ref=source_ref,
        embedding=embed(content),
        importance=importance,
        entities=entities or [],
        topics=topics or [],
    )
    session.add(mem)
    await session.flush()
    return mem


async def get_memory(session, memory_id: str) -> Memory | None:
    return (
        await session.execute(select(Memory).where(Memory.id == memory_id))
    ).scalar_one_or_none()


async def list_memories(session, user_id: str, limit: int = 50) -> list[Memory]:
    rows = (
        await session.execute(
            select(Memory).where(Memory.user_id == user_id).order_by(Memory.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def search_memories(session, user_id: str, query: str, k: int = 8) -> list[tuple[Memory, float]]:
    q = embed(query)
    rows = (
        await session.execute(select(Memory).where(Memory.user_id == user_id))
    ).scalars().all()
    scored = [(m, cosine(q, m.embedding)) for m in rows]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]

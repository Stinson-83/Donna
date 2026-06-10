"""Reasoning engine — causal chains made explicit and stored.

A chain explains a decision or a belief as a sequence of steps, grounded in the
beliefs that support it. Powers Plan's "because", belief "why this matters", and
recommendation explanations.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.cognition.store import ReasoningChain


async def create_chain(session, *, user_id, root_decision, steps, belief_ids=None, confidence=60) -> ReasoningChain:
    chain = ReasoningChain(
        user_id=user_id,
        root_decision=root_decision,
        steps=list(steps),
        belief_ids=list(belief_ids or []),
        confidence=confidence,
    )
    session.add(chain)
    await session.flush()
    return chain


async def get_chain(session, chain_id: str) -> ReasoningChain | None:
    return (
        await session.execute(select(ReasoningChain).where(ReasoningChain.id == chain_id))
    ).scalar_one_or_none()

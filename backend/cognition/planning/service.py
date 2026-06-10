"""Daily planning engine — Donna makes a choice, and shows her work.

Inputs: open loops (priority), beliefs, an optional calendar peak. Output: a
thesis, the candidates she considered, the one she chose, a reasoning chain for
why, and a nudge sourced from her highest-confidence actionable belief.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.cognition.beliefs.service import get_belief_by_subject, list_beliefs
from backend.cognition.reasoning.service import create_chain
from backend.cognition.store import OpenLoop, Plan, utcnow


async def list_open_loops(session, user_id: str, status: str = "open") -> list[OpenLoop]:
    rows = (
        await session.execute(
            select(OpenLoop)
            .where(OpenLoop.user_id == user_id, OpenLoop.status == status)
            .order_by(OpenLoop.priority.desc())
        )
    ).scalars().all()
    return list(rows)


async def build_plan(
    session,
    user_id: str,
    *,
    date_label: str,
    candidates: list[str],
    chosen: str,
    because_steps: list[str],
    thesis: str,
    thesis_coda: str,
    whisper: str,
    decision_reason: str,
    shape: list | None = None,
) -> Plan:
    beliefs = await list_beliefs(session, user_id)

    # reasoning chain grounded in beliefs influencing this choice
    chain = await create_chain(
        session,
        user_id=user_id,
        root_decision=chosen,
        steps=because_steps,
        belief_ids=[b.id for b in beliefs[:2]],
        confidence=beliefs[0].confidence if beliefs else 60,
    )

    # nudge sourced from the sleep belief if present, else the top belief
    sleep_belief = await get_belief_by_subject(session, user_id, "sleep_stress")
    nudge_belief = sleep_belief or (beliefs[0] if beliefs else None)
    nudge = "protect your evening — you perform sharper rested." if sleep_belief else None

    plan = Plan(
        user_id=user_id,
        date_label=date_label,
        thesis=thesis,
        thesis_coda=thesis_coda,
        considered=candidates,
        chosen=chosen,
        decision_reason=decision_reason,
        because=because_steps,
        nudge=nudge,
        nudge_belief_id=nudge_belief.id if nudge_belief else None,
        whisper=whisper,
        shape=shape or [],
        created_at=utcnow(),
    )
    session.add(plan)
    await session.flush()
    return plan


async def latest_plan(session, user_id: str) -> Plan | None:
    return (
        await session.execute(
            select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()


async def add_open_loop(session, *, user_id, description, source="Donna App", priority=0.5, meta=None) -> OpenLoop:
    loop = OpenLoop(user_id=user_id, description=description, source=source, priority=priority, meta=meta)
    session.add(loop)
    await session.flush()
    return loop

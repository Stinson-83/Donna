"""Belief engine — living hypotheses, not summaries.

A belief is the aggregate of observations sharing a subject. Its confidence is
computed by the confidence engine; its statement tracks the most recent evidence
(so it can be *revised*, not just nudged). Every change is journaled to
BeliefHistory: form / strengthen / weaken / revise.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import select

from backend.cognition.confidence.engine import evidence_from_observations, score
from backend.cognition.store import Belief, BeliefHistory, Observation, utcnow

REVISE_GAP = 6  # min confidence move (pts) to log a strengthen/weaken event


def _obs_dicts(observations: list[Observation]) -> list[dict]:
    return [
        {
            "created_at": o.created_at,
            "source_quality": o.source_quality,
            "polarity": o.polarity,
            "topics": o.topics,
            "subject": o.subject,
        }
        for o in observations
    ]


async def _journal(session, user_id, belief, kind, *, old_s=None, old_c=None, new_s=None, new_c=None, reason=None):
    session.add(
        BeliefHistory(
            user_id=user_id,
            belief_id=belief.id if belief else None,
            kind=kind,
            old_statement=old_s,
            old_confidence=old_c,
            new_statement=new_s,
            new_confidence=new_c,
            reason=reason,
        )
    )


async def recompute_subject(session, user_id: str, subject: str, *, reason: str = "new evidence") -> Belief | None:
    obs = (
        await session.execute(
            select(Observation).where(Observation.user_id == user_id, Observation.subject == subject)
        )
    ).scalars().all()
    if not obs:
        return None

    supporting = [o for o in obs if o.polarity == "support"]
    contradicting = [o for o in obs if o.polarity == "contradict"]
    if not supporting:
        return None

    result = score(evidence_from_observations(_obs_dicts(obs), utcnow()))

    # statement = the implication of the most recent supporting observation,
    # tie-broken by frequency — lets newer evidence *revise* the belief.
    supporting_sorted = sorted(supporting, key=lambda o: o.created_at, reverse=True)
    freq = Counter(o.implies for o in supporting)
    newest_implies = supporting_sorted[0].implies
    statement = newest_implies if freq[newest_implies] >= 1 else freq.most_common(1)[0][0]

    now = utcnow()
    belief = (
        await session.execute(
            select(Belief).where(Belief.user_id == user_id, Belief.subject == subject, Belief.status == "active")
        )
    ).scalar_one_or_none()

    if belief is None:
        belief = Belief(
            user_id=user_id,
            subject=subject,
            statement=statement,
            confidence=result.score,
            reasoning=result.rationale,
            confidence_history=[{"conf": result.score, "at": now.isoformat(), "reason": "formed"}],
            supporting_observation_ids=[o.id for o in supporting],
            contradicting_observation_ids=[o.id for o in contradicting],
            created_at=now,
            updated_at=now,
            last_strengthened=now,
        )
        session.add(belief)
        await session.flush()
        await _journal(session, user_id, belief, "form", new_s=statement, new_c=result.score, reason="enough corroborating evidence")
        return belief

    old_conf = belief.confidence
    old_stmt = belief.statement

    belief.supporting_observation_ids = [o.id for o in supporting]
    belief.contradicting_observation_ids = [o.id for o in contradicting]
    belief.reasoning = result.rationale
    belief.confidence = result.score
    belief.updated_at = now
    belief.confidence_history = list(belief.confidence_history) + [
        {"conf": result.score, "at": now.isoformat(), "reason": reason}
    ]

    # revision: the evidence now points at a different statement
    if statement.strip() != old_stmt.strip():
        belief.statement = statement
        await _journal(
            session, user_id, belief, "revise",
            old_s=old_stmt, old_c=old_conf, new_s=statement, new_c=result.score,
            reason=reason,
        )
    elif result.score - old_conf >= REVISE_GAP:
        belief.last_strengthened = now
        await _journal(session, user_id, belief, "strengthen", old_c=old_conf, new_c=result.score, reason=reason)
    elif old_conf - result.score >= REVISE_GAP:
        belief.last_weakened = now
        await _journal(session, user_id, belief, "weaken", old_c=old_conf, new_c=result.score, reason=reason)

    await session.flush()
    return belief


async def recompute_all(session, user_id: str, *, reason: str = "recompute") -> list[Belief]:
    subjects = (
        await session.execute(
            select(Observation.subject).where(Observation.user_id == user_id).distinct()
        )
    ).scalars().all()
    out = []
    for s in subjects:
        b = await recompute_subject(session, user_id, s, reason=reason)
        if b:
            out.append(b)
    return out


async def set_consequence(session, belief: Belief, *, consequence: str, action: str) -> None:
    belief.consequence = consequence
    belief.actions_influenced = list(belief.actions_influenced) + [action]
    await session.flush()


async def list_beliefs(session, user_id: str) -> list[Belief]:
    rows = (
        await session.execute(
            select(Belief).where(Belief.user_id == user_id, Belief.status == "active").order_by(Belief.confidence.desc())
        )
    ).scalars().all()
    return list(rows)


async def get_belief(session, belief_id: str) -> Belief | None:
    return (await session.execute(select(Belief).where(Belief.id == belief_id))).scalar_one_or_none()


async def get_belief_by_subject(session, user_id: str, subject: str) -> Belief | None:
    return (
        await session.execute(
            select(Belief).where(Belief.user_id == user_id, Belief.subject == subject, Belief.status == "active")
        )
    ).scalar_one_or_none()


async def list_revisions(session, user_id: str) -> list[BeliefHistory]:
    rows = (
        await session.execute(
            select(BeliefHistory)
            .where(BeliefHistory.user_id == user_id, BeliefHistory.kind == "revise")
            .order_by(BeliefHistory.created_at.desc())
        )
    ).scalars().all()
    return list(rows)

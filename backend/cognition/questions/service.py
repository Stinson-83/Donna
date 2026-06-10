"""Question engine — what Donna does *not* yet believe.

A question exists when evidence is ambiguous: either a subject's confidence sits
in the uncertain band, or two hypotheses compete for the same observations.
Questions graduate into beliefs when they resolve; beliefs fall back to questions
when they stop holding.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.cognition.store import Belief, Question, utcnow

UNCERTAIN_LOW = 45
UNCERTAIN_HIGH = 68


async def add_question(
    session,
    *,
    user_id: str,
    question: str,
    subject: str,
    confidence: int,
    leaning: str | None = None,
    supporting: list[str] | None = None,
    conflicting: list[str] | None = None,
) -> Question:
    existing = (
        await session.execute(
            select(Question).where(Question.user_id == user_id, Question.subject == subject, Question.status == "open")
        )
    ).scalar_one_or_none()
    if existing:
        existing.question = question
        existing.confidence = confidence
        existing.leaning = leaning
        existing.supporting = supporting or []
        existing.conflicting = conflicting or []
        existing.updated_at = utcnow()
        await session.flush()
        return existing
    q = Question(
        user_id=user_id,
        question=question,
        subject=subject,
        confidence=confidence,
        leaning=leaning,
        supporting=supporting or [],
        conflicting=conflicting or [],
    )
    session.add(q)
    await session.flush()
    return q


async def detect_from_beliefs(session, user_id: str) -> list[Question]:
    """Mechanism: a belief whose confidence is genuinely uncertain becomes an
    open question; once it leaves the uncertain band, that question resolves
    (graduated into a belief)."""
    beliefs = (
        await session.execute(
            select(Belief).where(Belief.user_id == user_id, Belief.status == "active")
        )
    ).scalars().all()
    in_band: set[str] = set()
    out = []
    for b in beliefs:
        subj = f"belief:{b.subject}"
        if UNCERTAIN_LOW <= b.confidence <= UNCERTAIN_HIGH:
            in_band.add(subj)
            out.append(
                await add_question(
                    session, user_id=user_id, subject=subj,
                    question=f"is it true that {b.statement}?",
                    confidence=b.confidence,
                    leaning="evidence is split — not enough to commit.",
                )
            )
    # resolve belief-questions that have since become confident
    open_qs = await list_questions(session, user_id, status="open")
    for q in open_qs:
        if q.subject.startswith("belief:") and q.subject not in in_band:
            q.status = "resolved"
            q.updated_at = utcnow()
    await session.flush()
    return out


async def list_questions(session, user_id: str, status: str = "open") -> list[Question]:
    rows = (
        await session.execute(
            select(Question)
            .where(Question.user_id == user_id, Question.status == status)
            .order_by(Question.confidence.desc())
        )
    ).scalars().all()
    return list(rows)

"""Cognition storage — first-class persisted entities behind every UI concept.

All cognition tables live on the same engine as the rest of the app (Postgres
in prod, SQLite offline). Lists/vectors are JSON columns so this runs without a
vector DB; semantic search is done in-process (see memory/embedding.py).

Entities: Memory, Observation, Belief, BeliefHistory, Question, GraphNode,
GraphEdge, ReasoningChain, OpenLoop, Plan.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from db.session import _engine, async_session  # shared engine + sessionmaker


def gen_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Memory(Base):
    __tablename__ = "cog_memories"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, default="Donna App")  # human source label
    source_type: Mapped[str] = mapped_column(String, default="donna_app")
    source_ref: Mapped[str | None] = mapped_column(String, nullable=True)  # conversation/message id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    entities: Mapped[list] = mapped_column(JSON, default=list)
    topics: Mapped[list] = mapped_column(JSON, default=list)


class Observation(Base):
    """A pattern noticed across memories — the evidence beliefs are built from."""
    __tablename__ = "cog_observations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    statement: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(String, index=True)   # belief subject key
    implies: Mapped[str] = mapped_column(Text)                 # candidate belief statement
    polarity: Mapped[str] = mapped_column(String, default="support")  # support | contradict
    source_quality: Mapped[float] = mapped_column(Float, default=0.6)
    memory_ids: Mapped[list] = mapped_column(JSON, default=list)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Belief(Base):
    __tablename__ = "cog_beliefs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    subject: Mapped[str] = mapped_column(String, index=True)
    statement: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    status: Mapped[str] = mapped_column(String, default="active")  # active | retired
    consequence: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_history: Mapped[list] = mapped_column(JSON, default=list)  # [{conf, at, reason}]
    supporting_observation_ids: Mapped[list] = mapped_column(JSON, default=list)
    contradicting_observation_ids: Mapped[list] = mapped_column(JSON, default=list)
    actions_influenced: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_strengthened: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_weakened: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BeliefHistory(Base):
    """A revision event — powers 'i changed my mind'."""
    __tablename__ = "cog_belief_history"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    belief_id: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String, default="revise")  # strengthen|weaken|revise|split|merge|form
    old_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Question(Base):
    __tablename__ = "cog_questions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    question: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(String, index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=50)  # confidence in leading hypothesis
    status: Mapped[str] = mapped_column(String, default="open")  # open | resolved
    leaning: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting: Mapped[list] = mapped_column(JSON, default=list)
    conflicting: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class GraphNode(Base):
    __tablename__ = "cog_nodes"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    label: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String, index=True)  # person|project|goal|pattern|memory|belief|question
    weight: Mapped[float] = mapped_column(Float, default=0.6)
    ref_id: Mapped[str | None] = mapped_column(String, nullable=True)  # underlying entity id


class GraphEdge(Base):
    __tablename__ = "cog_edges"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    src: Mapped[str] = mapped_column(String, index=True)  # node id
    dst: Mapped[str] = mapped_column(String, index=True)
    relation: Mapped[str] = mapped_column(String)  # supports|contradicts|related_to|causes|mentions|influences
    weight: Mapped[float] = mapped_column(Float, default=0.5)


class ReasoningChain(Base):
    __tablename__ = "cog_reasoning"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    root_decision: Mapped[str] = mapped_column(Text)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    belief_ids: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OpenLoop(Base):
    __tablename__ = "cog_open_loops"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, default="Donna App")
    status: Mapped[str] = mapped_column(String, default="open")  # open | closed
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    meta: Mapped[str | None] = mapped_column(String, nullable=True)  # human "due friday"
    related: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Plan(Base):
    __tablename__ = "cog_plans"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, index=True)
    date_label: Mapped[str] = mapped_column(String)
    thesis: Mapped[str] = mapped_column(Text)
    thesis_coda: Mapped[str | None] = mapped_column(Text, nullable=True)
    considered: Mapped[list] = mapped_column(JSON, default=list)
    chosen: Mapped[str] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    because: Mapped[list] = mapped_column(JSON, default=list)  # reasoning chain steps
    shape: Mapped[list] = mapped_column(JSON, default=list)    # calendar: [{time,title,tone}]
    nudge: Mapped[str | None] = mapped_column(Text, nullable=True)
    nudge_belief_id: Mapped[str | None] = mapped_column(String, nullable=True)
    whisper: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


async def create_cognition_tables() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = [
    "async_session", "gen_id", "utcnow", "Base", "create_cognition_tables",
    "Memory", "Observation", "Belief", "BeliefHistory", "Question",
    "GraphNode", "GraphEdge", "ReasoningChain", "OpenLoop", "Plan",
]

"""Cognition API — every frontend screen consumes these. Shapes mirror what the
UI renders, but every value is read from the persisted, engine-generated model.

GET  /plan /beliefs /beliefs/{id} /belief-history /questions
GET  /memory /memory/{id} /graph /open-loops /reasoning/{id}
POST /journal /voice /feedback
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from backend.cognition import beliefs as _b  # noqa: F401 (package marker)
from backend.cognition.beliefs.service import (
    get_belief, list_beliefs, list_revisions,
)
from backend.cognition.planning.service import latest_plan, list_open_loops
from backend.cognition.questions.service import list_questions
from backend.cognition.reasoning.service import get_chain
from backend.cognition.relationships.service import build_graph
from backend.cognition.memory.service import get_memory, list_memories
from backend.cognition.pipeline import ingest
from backend.cognition.store import (
    Belief, Observation, async_session, utcnow,
)

router = APIRouter(prefix="/cognition", tags=["cognition"])
DEFAULT_USER = "demo-aarav"


# ── helpers ──────────────────────────────────────────────────────────────────
def rel(dt) -> str:
    if not dt:
        return ""
    d = utcnow() - dt
    if d.days <= 0:
        return "today"
    if d.days == 1:
        return "yesterday"
    if d.days < 7:
        return f"{d.days} days ago"
    w = d.days // 7
    return f"{w} week{'s' if w > 1 else ''} ago"


def conf_label(importance: float) -> str:
    return "high" if importance >= 0.66 else "medium" if importance >= 0.4 else "low"


async def _observations(session, user_id):
    rows = (await session.execute(select(Observation).where(Observation.user_id == user_id))).scalars().all()
    return list(rows)


def _distinct(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


async def serialize_belief(session, b: Belief, obs_by_id: dict, *, full=False) -> dict:
    supporting = [obs_by_id[i] for i in b.supporting_observation_ids if i in obs_by_id]
    contra = [obs_by_id[i] for i in b.contradicting_observation_ids if i in obs_by_id]
    history = [h.get("conf") for h in (b.confidence_history or []) if "conf" in h]
    delta = (history[-1] - history[-2]) if len(history) >= 2 else 0
    newest = sorted(supporting, key=lambda o: o.created_at, reverse=True)
    out = {
        "id": b.id,
        "subject": b.subject,
        "confidence": b.confidence,
        "delta": (f"+{delta}" if delta > 0 else str(delta)) if delta else None,
        "up": delta > 0,
        "strengthened": rel(b.last_strengthened or b.updated_at),
        "statement": b.statement,
        "consequence": b.consequence,
        "evidence": _distinct([o.statement for o in supporting]),
        "counter": _distinct([o.statement for o in contra]) or None,
        "history": history,
        "strengthenedBy": (newest[0].statement if newest else b.reasoning) or "",
        "reasoning": b.reasoning,
        "related": _distinct([t for o in supporting for t in (o.topics or [])])[:4],
    }
    if full:
        out["supporting_memory_ids"] = _distinct([m for o in supporting for m in (o.memory_ids or [])])
        out["contradicting_memory_ids"] = _distinct([m for o in contra for m in (o.memory_ids or [])])
        out["actions_influenced"] = b.actions_influenced
        out["confidence_history"] = b.confidence_history
    return out


# ── reads ────────────────────────────────────────────────────────────────────
@router.get("/plan")
async def get_plan(user: str = DEFAULT_USER) -> dict:
    async with async_session() as s:
        plan = await latest_plan(s, user)
        loops = await list_open_loops(s, user)
        nudge_belief = None
        if plan and plan.nudge_belief_id:
            b = await get_belief(s, plan.nudge_belief_id)
            nudge_belief = b.statement if b else None
        if not plan:
            return {"empty": True}
        return {
            "date": plan.date_label,
            "thesis": plan.thesis,
            "thesisCoda": plan.thesis_coda,
            "because": plan.because,
            "decision": {
                "considered": plan.considered,
                "chose": plan.chosen,
                "because": plan.decision_reason,
            },
            "calendar": plan.shape,
            "openLoops": [{"id": l.id, "text": l.description, "meta": l.meta} for l in loops],
            "nudge": plan.nudge,
            "nudgeBelief": nudge_belief,
            "whisper": plan.whisper,
        }


@router.get("/beliefs")
async def get_beliefs(user: str = DEFAULT_USER) -> list[dict]:
    async with async_session() as s:
        obs_by_id = {o.id: o for o in await _observations(s, user)}
        return [await serialize_belief(s, b, obs_by_id) for b in await list_beliefs(s, user)]


@router.get("/beliefs/{belief_id}")
async def get_one_belief(belief_id: str, user: str = DEFAULT_USER) -> dict:
    async with async_session() as s:
        b = await get_belief(s, belief_id)
        if not b:
            return {"error": "not found"}
        obs_by_id = {o.id: o for o in await _observations(s, user)}
        return await serialize_belief(s, b, obs_by_id, full=True)


@router.get("/belief-history")
async def get_belief_history(user: str = DEFAULT_USER) -> list[dict]:
    async with async_session() as s:
        revs = await list_revisions(s, user)
        return [
            {
                "id": r.id,
                "from": {"statement": r.old_statement, "conf": r.old_confidence},
                "to": {"statement": r.new_statement, "conf": r.new_confidence},
                "why": r.reason,
            }
            for r in revs
        ]


@router.get("/questions")
async def get_questions(user: str = DEFAULT_USER) -> list[dict]:
    async with async_session() as s:
        return [
            {"id": q.id, "confidence": q.confidence, "question": q.question, "status": q.leaning or "", "leaning": None}
            for q in await list_questions(s, user)
        ]


@router.get("/memory")
async def get_memory_list(user: str = DEFAULT_USER, limit: int = 12) -> list[dict]:
    async with async_session() as s:
        mems = await list_memories(s, user, limit=limit)
        observations = await _observations(s, user)
        beliefs = {b.subject: b for b in await list_beliefs(s, user)}
        out = []
        for m in mems:
            supports = _distinct(
                [
                    beliefs[o.subject].statement
                    for o in observations
                    if m.id in (o.memory_ids or []) and o.subject in beliefs
                ]
            )
            out.append({
                "id": m.id,
                "summary": m.content,
                "confidence": conf_label(m.importance),
                "when": rel(m.created_at),
                "source": m.source,
                "supports": supports,
            })
        return out


@router.get("/memory/{memory_id}")
async def get_one_memory(memory_id: str, user: str = DEFAULT_USER) -> dict:
    async with async_session() as s:
        m = await get_memory(s, memory_id)
        if not m:
            return {"error": "not found"}
        observations = await _observations(s, user)
        beliefs = {b.subject: b for b in await list_beliefs(s, user)}
        supports = _distinct(
            [beliefs[o.subject].statement for o in observations if m.id in (o.memory_ids or []) and o.subject in beliefs]
        )
        return {
            "id": m.id,
            "content": m.content,
            "source": m.source,
            "source_type": m.source_type,
            "source_ref": m.source_ref,
            "when": rel(m.created_at),
            "topics": m.topics,
            "entities": m.entities,
            "supports": supports,
        }


@router.get("/graph")
async def get_graph(user: str = DEFAULT_USER) -> dict:
    async with async_session() as s:
        return await build_graph(s, user)


@router.get("/open-loops")
async def get_open_loops(user: str = DEFAULT_USER) -> list[dict]:
    async with async_session() as s:
        return [
            {"id": l.id, "text": l.description, "meta": l.meta, "source": l.source, "priority": l.priority}
            for l in await list_open_loops(s, user)
        ]


@router.get("/reasoning/{chain_id}")
async def get_reasoning(chain_id: str) -> dict:
    async with async_session() as s:
        c = await get_chain(s, chain_id)
        if not c:
            return {"error": "not found"}
        return {"id": c.id, "root_decision": c.root_decision, "steps": c.steps, "belief_ids": c.belief_ids, "confidence": c.confidence}


# ── writes (ingestion) ───────────────────────────────────────────────────────
class IngestBody(BaseModel):
    user: str = DEFAULT_USER
    text: str
    topics: list[str] | None = None
    entities: list[str] | None = None


@router.post("/journal")
async def post_journal(body: IngestBody) -> dict:
    async with async_session() as s:
        res = await ingest(s, user_id=body.user, content=body.text, source_type="journal",
                           topics=body.topics, entities=body.entities, importance=0.6)
        await s.commit()
        return {"ok": True, **res}


@router.post("/voice")
async def post_voice(body: IngestBody) -> dict:
    # transcript-in for now; wire STT (Deepgram) ahead of this when available.
    async with async_session() as s:
        res = await ingest(s, user_id=body.user, content=body.text, source_type="voice",
                           topics=body.topics, entities=body.entities, importance=0.6)
        await s.commit()
        return {"ok": True, **res}


class FeedbackBody(BaseModel):
    user: str = DEFAULT_USER
    belief_id: str
    signal: str  # "agree" | "disagree"


@router.post("/feedback")
async def post_feedback(body: FeedbackBody) -> dict:
    async with async_session() as s:
        b = await get_belief(s, body.belief_id)
        if not b:
            return {"error": "not found"}
        bump = 4 if body.signal == "agree" else -6
        new_conf = max(1, min(99, b.confidence + bump))
        b.confidence = new_conf
        b.confidence_history = list(b.confidence_history) + [
            {"conf": new_conf, "at": utcnow().isoformat(), "reason": f"user {body.signal}d"}
        ]
        b.updated_at = utcnow()
        await s.commit()
        return {"ok": True, "confidence": new_conf}

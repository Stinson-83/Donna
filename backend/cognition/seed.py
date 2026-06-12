"""Seed a full cognitive state by running the REAL engines — nothing hardcoded
downstream. Memories are ingested, observations mined, beliefs formed (confidence
computed by the engine), revisions recorded, questions opened, a plan generated,
and the graph wired. Idempotent per user.

    python -m backend.cognition.seed [user_id]
"""
from __future__ import annotations

import asyncio
import sys
from datetime import timedelta

from sqlalchemy import delete

from backend.cognition.beliefs.service import (
    get_belief_by_subject,
    recompute_subject,
    set_consequence,
)
from backend.cognition.observations.service import add_observation
from backend.cognition.planning.service import add_open_loop, build_plan
from backend.cognition.pipeline import ingest
from backend.cognition.questions.service import add_question
from backend.cognition.relationships.service import add_edge, upsert_node
from backend.cognition.store import (
    Belief, BeliefHistory, GraphEdge, GraphNode, Memory, Observation, Plan,
    OpenLoop, Question, ReasoningChain, async_session, create_cognition_tables, utcnow,
)

DEFAULT_USER = "demo-aarav"

# Memories that, once mined, form the beliefs. Source variety is intentional.
MEMORIES = [
    # sleep → stress
    ("slept ~6h again the night before the antler review", "whatsapp", ["sleep", "review"], ["sleep", "antler"]),
    ("stressed all day, and i barely slept before the board update", "whatsapp", ["sleep", "stress"], ["sleep"]),
    ("noticed i sleep badly the week before every milestone", "journal", ["sleep", "milestone"], ["sleep"]),
    # mornings → focus
    ("got a clean 3-hour deep-work block before noon", "donna_app", ["focus", "deep-work"], ["focus"]),
    ("mornings are when the real work happens for me", "journal", ["focus", "morning"], ["focus"]),
    ("shipped the hardest part of donna before lunch again", "donna_app", ["focus", "deep-work"], ["focus", "donna"]),
    # overprepare when uncertain
    ("rewrote the antler deck twice, still unsure about the story", "whatsapp", ["deck", "uncertain"], ["antler", "pitch nerves"]),
    ("over-prepared for the investor meeting, redid the slides", "journal", ["prep", "investor"], ["antler"]),
    ("kept reworking the pitch because i wasn't sure of the angle", "donna_app", ["pitch", "uncertain"], ["pitch nerves"]),
    # priya on pricing
    ("deferred to priya on the pricing tiers again", "whatsapp", ["priya", "pricing"], ["priya"]),
    ("priya was right on price, reversed my call", "journal", ["priya", "pricing"], ["priya", "donna"]),
    # outreach (refined statement); contradict keeps it honest
    ("postponed the investor email, the narrative still feels weak", "whatsapp", ["email", "weak"], ["antler", "the raise"]),
    ("delayed the recruiting intro until the story is tighter", "donna_app", ["outreach", "delay"], ["luca", "the raise"]),
    ("sent cold outreach the week the demo landed and felt confident", "journal", ["outreach", "sent"], ["the raise"]),
]


async def _wipe(session, user_id: str) -> None:
    for model in (Memory, Observation, Belief, BeliefHistory, Question, GraphNode, GraphEdge, ReasoningChain, OpenLoop, Plan):
        await session.execute(delete(model).where(model.user_id == user_id))


async def seed(user_id: str = DEFAULT_USER) -> None:
    await create_cognition_tables()
    async with async_session() as session:
        await _wipe(session, user_id)

        # Two beliefs are seeded to REVISE: plant an older, cruder hypothesis
        # first (old timestamp) so newer evidence overturns it → "i changed my mind".
        old = utcnow() - timedelta(days=40)
        await add_observation(
            session, user_id=user_id, subject="outreach", statement="skipped a few intros",
            implies="you dislike outreach", polarity="support", source_quality=0.55,
            memory_ids=[], topics=["outreach"], created_at=old,
        )
        await recompute_subject(session, user_id, "outreach", reason="early read")
        await add_observation(
            session, user_id=user_id, subject="mornings", statement="up early most days",
            implies="you're simply a morning person", polarity="support", source_quality=0.5,
            memory_ids=[], topics=["morning"], created_at=old,
        )
        await recompute_subject(session, user_id, "mornings", reason="early read")
        await session.commit()

        # Ingest the demo memories through the keyword miner (mine=True) — this
        # is the one place the legacy miner still runs, to build the showcase.
        for content, st, topics, entities in MEMORIES:
            await ingest(session, user_id=user_id, content=content, source_type=st, topics=topics, entities=entities, importance=0.6, mine=True)
        await session.commit()

        # Consequences — beliefs that changed a recommendation.
        consequences = {
            "sleep_stress": ("i prioritized sleep recovery in today's plan and pushed the 11pm wind-down.", "plan:sleep-recovery"),
            "mornings": ("i scheduled the deck rewrite into your 9–12 block, not the afternoon.", "plan:morning-block"),
            "overprepare": ("i stopped suggesting more deck edits and pushed you toward the story.", "chat:story-over-slide"),
            "priya_pricing": ("i flagged the pricing slide for priya before the review, not for you.", "plan:priya-pricing"),
            "outreach": ("i held the investor-email nudge until the narrative is tighter.", "plan:hold-outreach"),
        }
        for subject, (cons, action) in consequences.items():
            b = await get_belief_by_subject(session, user_id, subject)
            if b:
                await set_consequence(session, b, consequence=cons, action=action)
        await session.commit()

        # Open questions — ambiguous, split-evidence hypotheses (headline three).
        await add_question(session, user_id=user_id, subject="q_stress_source", confidence=61,
                           question="does your stress come from the reviews, or from the lost sleep?",
                           leaning="evidence supports both — leaning sleep, can't separate them yet.")
        await add_question(session, user_id=user_id, subject="q_delays", confidence=58,
                           question="are the investor delays about outreach avoidance, or weak positioning?",
                           leaning="suspect positioning. not enough evidence.")
        await add_question(session, user_id=user_id, subject="q_priya", confidence=54,
                           question="does priya improve your decision quality, or just your confidence?",
                           leaning="too early to call.")
        await session.commit()

        # Open loops.
        await add_open_loop(session, user_id=user_id, description="reply to luca", source="WhatsApp", priority=0.7, meta="open 3 days")
        await add_open_loop(session, user_id=user_id, description="antler intro form", source="Donna App", priority=0.85, meta="due friday")
        await add_open_loop(session, user_id=user_id, description="call mom", source="WhatsApp", priority=0.4, meta="open 1 week")
        await session.commit()

        # Graph: entity → belief support edges (so a tapped memory reveals its belief).
        belief_nodes = {}
        for subject in consequences:
            b = await get_belief_by_subject(session, user_id, subject)
            if b:
                belief_nodes[subject] = await upsert_node(session, user_id=user_id, label=subject, kind="belief", ref_id=b.id)
        entity_to_subject = {
            "sleep": "sleep_stress", "focus": "mornings", "pitch nerves": "overprepare",
            "priya": "priya_pricing", "antler": "outreach",
        }
        for ent, subject in entity_to_subject.items():
            node = await upsert_node(session, user_id=user_id, label=ent, kind="pattern")
            bnode = belief_nodes.get(subject)
            if bnode:
                await add_edge(session, user_id=user_id, src=node.id, dst=bnode.id, relation="supports", weight=0.8)
        await session.commit()

        # Daily plan — generated from beliefs + loops.
        await build_plan(
            session, user_id,
            date_label="tuesday · june 10",
            candidates=["investor outreach", "roadmap planning", "hiring"],
            chosen="the antler deck",
            because_steps=["the deck", "review confidence", "investor conversations", "the raise"],
            thesis="today is about the antler deck.",
            thesis_coda="everything else can wait.",
            whisper="you were nervous before the last pitch too. it went fine.",
            decision_reason="it influences three upcoming decisions, and the others can wait a day.",
            shape=[
                {"time": "11:00", "title": "1:1 with priya", "tone": "normal"},
                {"time": "14:00", "title": "deep work — deck", "tone": "normal"},
                {"time": "18:00", "title": "antler review", "tone": "peak"},
            ],
        )
        await session.commit()

    print(f"seeded cognition for user '{user_id}'")


if __name__ == "__main__":
    asyncio.run(seed(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USER))

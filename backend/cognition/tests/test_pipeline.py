from datetime import timedelta

import pytest

from backend.cognition.beliefs.service import (
    get_belief_by_subject, list_revisions, recompute_subject,
)
from backend.cognition.observations.service import add_observation
from backend.cognition.pipeline import ingest
from backend.cognition.store import utcnow


@pytest.mark.asyncio
async def test_belief_forms_from_memory(cogdb):
    async with cogdb() as s:
        await ingest(
            s, user_id="u", content="slept ~6h before the review and felt stressed",
            source_type="whatsapp", topics=["sleep", "review"], entities=["sleep"], mine=True,
        )
        await s.commit()
        b = await get_belief_by_subject(s, "u", "sleep_stress")
        assert b is not None
        assert "sleep" in b.statement
        assert b.confidence > 40
        assert b.confidence_history  # has a history entry


@pytest.mark.asyncio
async def test_more_evidence_strengthens(cogdb):
    async with cogdb() as s:
        await ingest(s, user_id="u", content="deep work before noon", source_type="donna_app", topics=["focus"], mine=True)
        await s.commit()
        first = (await get_belief_by_subject(s, "u", "mornings")).confidence
        for _ in range(3):
            await ingest(s, user_id="u", content="another morning deep-work block", source_type="donna_app", topics=["focus", "deep-work"], mine=True)
        await s.commit()
        later = (await get_belief_by_subject(s, "u", "mornings")).confidence
        assert later >= first


@pytest.mark.asyncio
async def test_belief_revision_is_recorded(cogdb):
    async with cogdb() as s:
        old = utcnow() - timedelta(days=40)
        await add_observation(
            s, user_id="u", subject="outreach", statement="skipped intros",
            implies="you dislike outreach", polarity="support", source_quality=0.5,
            memory_ids=[], topics=["outreach"], created_at=old,
        )
        await recompute_subject(s, "u", "outreach")
        await s.commit()
        before = await get_belief_by_subject(s, "u", "outreach")
        assert before.statement == "you dislike outreach"

        await ingest(
            s, user_id="u", content="postponed the investor email, the narrative feels weak",
            source_type="whatsapp", topics=["email", "weak"], entities=["antler"], mine=True,
        )
        await s.commit()
        after = await get_belief_by_subject(s, "u", "outreach")
        assert "avoid" in after.statement  # revised, not just nudged
        revs = await list_revisions(s, "u")
        assert any(r.old_statement == "you dislike outreach" for r in revs)

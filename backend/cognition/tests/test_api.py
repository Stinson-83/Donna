"""Exercise the API serializers directly (same event loop as the patched
async_session) — avoids TestClient cross-loop issues with in-memory SQLite."""
import pytest

from backend.cognition.api import routes
from backend.cognition.pipeline import ingest


async def _seed_min(cogdb):
    async with cogdb() as s:
        await ingest(s, user_id="demo-aarav", content="slept 6h before the review, stressed",
                     source_type="whatsapp", topics=["sleep", "review"], entities=["sleep"])
        await ingest(s, user_id="demo-aarav", content="deep work block before noon again",
                     source_type="donna_app", topics=["focus", "deep-work"], entities=["focus"])
        await s.commit()


@pytest.mark.asyncio
async def test_beliefs_endpoint(cogdb):
    await _seed_min(cogdb)
    beliefs = await routes.get_beliefs(user="demo-aarav")
    assert beliefs
    assert any("sleep" in b["statement"] for b in beliefs)
    for b in beliefs:
        assert isinstance(b["confidence"], int)
        assert isinstance(b["history"], list) and b["history"]
        assert "evidence" in b


@pytest.mark.asyncio
async def test_memory_endpoint_traces_to_beliefs(cogdb):
    await _seed_min(cogdb)
    mems = await routes.get_memory_list(user="demo-aarav")
    assert len(mems) >= 2
    # at least one memory should trace forward to a belief it supports
    assert any(m["supports"] for m in mems)


@pytest.mark.asyncio
async def test_questions_and_graph(cogdb):
    await _seed_min(cogdb)
    qs = await routes.get_questions(user="demo-aarav")
    assert isinstance(qs, list)
    graph = await routes.get_graph(user="demo-aarav")
    assert "nodes" in graph and "edges" in graph
    assert any(n["label"] == "you" for n in graph["nodes"])

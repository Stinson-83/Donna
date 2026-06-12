"""Capability 20 — learning from feedback.

The cards table is the feedback log: intent + state (acted | dismissed). These
tests cover the aggregate, the learned-preferences context block (silent until
there's real signal), and the concrete effect — dismissing email heads-ups raises
the proactive-email bar so similar emails stop surfacing.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from backend.integrations.composio_client import NormalizedGmailMessage
from db.models import Card, User


async def _seed_cards(db, user_id, intent, *, acted=0, dismissed=0):
    async with db() as s:
        for _ in range(acted):
            s.add(Card(user_id=user_id, intent=intent, payload={"intent": intent}, state="acted"))
        for _ in range(dismissed):
            s.add(Card(user_id=user_id, intent=intent, payload={"intent": intent}, state="dismissed"))
        await s.commit()


def _msg(**kw):
    base = dict(
        gmail_message_id="m1", thread_id="t1", from_address="x@y.com", from_name="X",
        to_addresses=[], cc_addresses=[], subject="hello", snippet="", body_text="hi",
        labels=[], is_important=True, is_starred=False, is_sent=False,
        internal_date=datetime(2026, 8, 25, 9, 0),
    )
    base.update(kw)
    return NormalizedGmailMessage(**base)


# ── aggregate ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_feedback_stats_and_bias(db):
    from backend.knowledge.feedback import feedback_stats

    await _seed_cards(db, "u1", "heads_up", acted=1, dismissed=4)
    await _seed_cards(db, "u1", "approval", acted=5, dismissed=0)

    stats = await feedback_stats("u1")
    assert stats["heads_up"]["dismissed"] == 4 and stats["heads_up"]["total"] == 5
    assert stats["heads_up"]["bias"] < 0
    assert stats["approval"]["bias"] > 0


# ── learned-preferences block ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_learned_block_silent_until_signal(db):
    from backend.knowledge.feedback import render_feedback_block

    # under the min-sample floor -> nothing learned yet
    await _seed_cards(db, "u1", "heads_up", dismissed=2)
    assert await render_feedback_block("u1") == ""


@pytest.mark.asyncio
async def test_learned_block_reflects_lean(db):
    from backend.knowledge.feedback import render_feedback_block

    await _seed_cards(db, "u1", "heads_up", acted=1, dismissed=5)
    await _seed_cards(db, "u1", "approval", acted=6, dismissed=0)

    block = await render_feedback_block("u1")
    assert "usually dismiss heads_up" in block
    assert "usually act on approval" in block


# ── concrete effect: dismissed heads-ups raise the email bar ─────────────────

def _stub_brain(monkeypatch):
    import backend.integrations.proactive_email_trigger as trig
    prompts: list[str] = []

    async def fake_brain(state, config=None):
        prompts.append(state["raw_input"])
        state["_outbound"] = []
        return state

    monkeypatch.setattr(trig, "_invoke_brain", fake_brain)
    return prompts


@pytest.mark.asyncio
async def test_email_threshold_bump(db):
    from backend.knowledge.feedback import email_threshold_bump

    assert await email_threshold_bump("u1") == 0.0          # no history
    await _seed_cards(db, "u1", "heads_up", acted=0, dismissed=5)
    assert await email_threshold_bump("u1") > 0.0           # learned: be more selective


@pytest.mark.asyncio
async def test_dismissed_history_suppresses_borderline_email(db, monkeypatch):
    import backend.integrations.proactive_email_trigger as trig

    # u1 has dismissed email heads-ups; u2 (seeded by conftest) is the control
    await _seed_cards(db, "u1", "heads_up", acted=0, dismissed=5)
    prompts = _stub_brain(monkeypatch)

    # an important email scores exactly at the 0.5 default threshold
    await trig.maybe_surface_email("u1", _msg(gmail_message_id="ma"))   # bar raised -> suppressed
    await trig.maybe_surface_email("u2", _msg(gmail_message_id="mb"))   # default bar -> surfaces

    assert len(prompts) == 1  # only the control surfaced

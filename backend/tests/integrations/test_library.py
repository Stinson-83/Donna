"""The Library drawer counts (api.cards.library): people (living-profile
relationships), documents, trackers (active watches), to-dos (open loops) and
connected accounts — scoped to the user."""
from __future__ import annotations

import copy

import pytest


@pytest.mark.asyncio
async def test_library_counts(db, monkeypatch):
    from sqlalchemy import select

    from api.cards import library
    from api.push import resolve_user_id
    from db.models import Document, Integration, OpenLoop, User, Watch

    user_id = await resolve_user_id("+lib")

    async with db() as s:
        u = (await s.execute(select(User).where(User.id == user_id))).scalar_one()
        prof = copy.deepcopy(u.living_profile) if isinstance(u.living_profile, dict) else {}
        prof.setdefault("biography", {})["relationships"] = [{"name": "Ava"}, {"name": "Raghav"}]
        u.living_profile = prof
        s.add_all([
            Document(user_id=user_id, storage_path="/d/1", filename="permit.pdf"),
            Watch(user_id=user_id, watch_type="web", subject_key="flights", title="flights", status="active"),
            Watch(user_id=user_id, watch_type="reply", subject_key="x", title="x", status="resolved"),  # not active
            OpenLoop(user_id=user_id, content="reply to landlord", status="active"),
            Integration(user_id=user_id, provider="google", product="googlecalendar"),
        ])
        # a different user's rows must NOT leak into the counts
        other = await resolve_user_id("+other")
        s.add(Document(user_id=other, storage_path="/d/2", filename="other.pdf"))
        await s.commit()

    out = await library(user="+lib")
    assert out["people"] == 2
    assert out["documents"] == 1  # the other user's doc is excluded
    assert out["trackers"] == 1   # only the active watch
    assert out["todos"] == 1
    assert out["connected"] == 1

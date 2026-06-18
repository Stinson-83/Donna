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

    out = await library(user_id=user_id)
    assert out["people"] == 2
    assert out["documents"] == 1  # the other user's doc is excluded
    assert out["trackers"] == 1   # only the active watch
    assert out["todos"] == 1
    assert out["connected"] == 1


@pytest.mark.asyncio
async def test_library_todos_detail_and_done(db):
    from datetime import datetime, timedelta

    from api.cards import library_todo_done, library_todos, TodoDoneBody
    from api.push import resolve_user_id
    from db.models import OpenLoop, utcnow

    user_id = await resolve_user_id("+lib")
    now = utcnow()
    async with db() as s:
        s.add_all([
            OpenLoop(user_id=user_id, content="renew passport", status="active",
                     due_date=now + timedelta(days=3), category="renewal"),
            OpenLoop(user_id=user_id, content="reply to landlord", status="active"),
            OpenLoop(user_id=user_id, content="old thing", status="closed"),
        ])
        await s.commit()

    out = await library_todos(user_id=user_id)
    contents = [t["content"] for t in out["todos"]]
    assert contents == ["renew passport", "reply to landlord"]  # dated first, closed excluded
    assert out["todos"][0]["due"] == "due in 3d"
    assert out["todos"][0]["category"] == "renewal"

    # mark done -> settles like close_open_loop, disappears from the list
    res = await library_todo_done(TodoDoneBody(user="+lib", id=out["todos"][0]["id"]))
    assert res["ok"] is True
    out2 = await library_todos(user_id=user_id)
    assert [t["content"] for t in out2["todos"]] == ["reply to landlord"]

    # another user's todo can't be closed through this user
    other_out = await library_todo_done(TodoDoneBody(user="+other2", id=out2["todos"][0]["id"]))
    assert other_out["ok"] is False


@pytest.mark.asyncio
async def test_library_trackers_detail_and_retire(db):
    from api.cards import library_tracker_retire, library_trackers, TrackerRetireBody
    from api.push import resolve_user_id
    from db.models import Watch

    user_id = await resolve_user_id("+lib")
    async with db() as s:
        s.add_all([
            Watch(user_id=user_id, watch_type="flight", subject_key="SQ516:2026-08-25",
                  title="flight SQ516", importance=80,
                  last_known_state={"status": "delayed", "flight_no": "SQ516"}),
            Watch(user_id=user_id, watch_type="web", subject_key="arsenal", title="arsenal",
                  importance=45, last_known_state={"seen_urls": ["a", "b"]}),
        ])
        await s.commit()

    out = await library_trackers(user_id=user_id)
    assert [t["title"] for t in out["trackers"]] == ["flight SQ516", "arsenal"]  # importance desc
    assert out["trackers"][0]["note"] == "delayed"          # flight carries its status
    assert out["trackers"][1]["note"] == "2 results seen"   # web carries its baseline size

    # retire -> status flip via the watch system, gone from the list
    res = await library_tracker_retire(TrackerRetireBody(user="+lib", id=out["trackers"][0]["id"]))
    assert res["ok"] is True
    out2 = await library_trackers(user_id=user_id)
    assert [t["title"] for t in out2["trackers"]] == ["arsenal"]

    # cross-user retire is refused
    res2 = await library_tracker_retire(TrackerRetireBody(user="+other3", id=out2["trackers"][0]["id"]))
    assert res2["ok"] is False


@pytest.mark.asyncio
async def test_library_people_detail(db):
    from sqlalchemy import select

    from api.cards import library_people
    from api.push import resolve_user_id
    from db.models import User

    user_id = await resolve_user_id("+lib")
    async with db() as s:
        u = (await s.execute(select(User).where(User.id == user_id))).scalar_one()
        u.living_profile = {"biography": {"relationships": [
            {"name": "Raghav", "email": "r@poke.dev", "importance": 90},
            {"name": "Mom", "importance": 95, "birthday": "06-20", "note": "likes lilies"},
        ]}}
        await s.commit()

    out = await library_people(user_id=user_id)
    names = [p["name"] for p in out["people"]]
    assert names == ["Mom", "Raghav"]            # importance desc
    assert out["people"][0]["birthday"] == "06-20"
    assert out["people"][0]["note"] == "likes lilies"
    assert out["people"][1]["email"] == "r@poke.dev"


@pytest.mark.asyncio
async def test_library_documents_and_connected_detail(db):
    from datetime import timedelta

    from api.cards import library_connected, library_documents
    from api.push import resolve_user_id
    from db.models import Document, Integration, utcnow

    user_id = await resolve_user_id("+lib")
    now = utcnow()
    async with db() as s:
        s.add_all([
            Document(user_id=user_id, storage_path="/d/new", filename="lease.pdf",
                     mime_type="application/pdf", file_size_bytes=240_000,
                     processing_status="ready", created_at=now),
            Document(user_id=user_id, storage_path="/d/old", filename="permit.png",
                     processing_status="processing", created_at=now - timedelta(days=2)),
            Integration(user_id=user_id, provider="google", product="googlecalendar",
                        status="connected", last_synced_at=now),
            Integration(user_id=user_id, provider="composio", product="github", status="pending"),
        ])
        await s.commit()

    docs = await library_documents(user_id=user_id)
    assert [d["filename"] for d in docs["documents"]] == ["lease.pdf", "permit.png"]  # newest first
    assert docs["documents"][0]["added"] == "today" and docs["documents"][0]["size"] == "234 KB"
    assert docs["documents"][1]["status"] == "processing"

    conn = await library_connected(user_id=user_id)
    healthy = {c["product"]: c["healthy"] for c in conn["connected"]}
    assert healthy == {"googlecalendar": True, "github": False}  # pending isn't healthy

"""Meta 24h session-window check (A1) — delivery/session_window.py."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from delivery.session_window import _SESSION_WINDOW, is_within_session_window


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_recent_message_is_within_window(db):
    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        s.add(User(id="u_fresh", phone="+9", last_active_at=_utcnow()))
        await s.commit()

    assert await is_within_session_window("u_fresh") is True


@pytest.mark.asyncio
async def test_old_message_is_outside_window(db):
    from db.models import User
    from db.session import async_session

    stale = _utcnow() - _SESSION_WINDOW - timedelta(minutes=5)
    async with async_session() as s:
        s.add(User(id="u_stale", phone="+8", last_active_at=stale))
        await s.commit()

    assert await is_within_session_window("u_stale") is False


@pytest.mark.asyncio
async def test_null_last_active_is_outside_window(db):
    # u1 and u2 are seeded with last_active_at=None (never messaged)
    assert await is_within_session_window("u1") is False


@pytest.mark.asyncio
async def test_unknown_user_is_outside_window(db):
    assert await is_within_session_window("nonexistent") is False

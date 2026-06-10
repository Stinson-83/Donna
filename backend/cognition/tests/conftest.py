"""Cognition tests run on a shared in-memory SQLite (StaticPool so every session
sees the same DB), with store/routes `async_session` pointed at it."""
from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.cognition.store import Base


@pytest_asyncio.fixture
async def cogdb(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import backend.cognition.api.routes as routes
    import backend.cognition.store as store

    monkeypatch.setattr(store, "async_session", sm)
    monkeypatch.setattr(routes, "async_session", sm)
    try:
        yield sm
    finally:
        await engine.dispose()

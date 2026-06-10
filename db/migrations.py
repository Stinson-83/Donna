"""Minimal migrations — create_all on Base metadata.

Usage:
    python -m db.migrations
"""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from db.models import Base
from db.session import _clean_url

logger = logging.getLogger(__name__)


async def create_tables() -> None:
    url_src = settings.database_url_direct or settings.database_url
    if not url_src:
        logger.warning("migrations: DATABASE_URL(_DIRECT) not set; skipping")
        return
    if url_src.startswith("sqlite"):
        # Offline/local dev: plain create_all, no asyncpg args, no pg-only ALTER
        # (the living_profile column is in the model, so create_all makes it).
        engine = create_async_engine(url_src)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
        logger.info("donna tables created (sqlite)")
        return
    direct = url_src.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    ).replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
    url, connect_args = _clean_url(direct)
    engine = create_async_engine(url, connect_args=connect_args)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS living_profile JSONB")
        )
    await engine.dispose()
    logger.info("donna tables created")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_tables())

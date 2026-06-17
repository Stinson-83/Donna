"""Minimal migrations — create_all on Base metadata + additive column reconcile.

Usage:
    python -m db.migrations

create_all() creates any missing *tables*, but it does NOT add missing *columns*
to tables that already exist. So when a column is added to a model after its table
was first created in prod, the column silently never appears and every query that
selects it crashes (e.g. `column users.notify_channel does not exist`). _reconcile_columns
closes that gap: it diffs each model table against the live DB and ADDs any missing
column (additive only — it never drops or alters existing columns), so the schema
self-heals on every boot. This generalizes the old one-off `ALTER TABLE users ADD
COLUMN IF NOT EXISTS living_profile` hack.
"""
import asyncio
import logging

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from db.models import Base
from db.session import _clean_url

logger = logging.getLogger(__name__)


def _default_sql(col) -> str | None:
    """A SQL literal for a column's scalar python default, so an added column
    backfills existing rows sensibly. Returns None when there's no simple default."""
    default = getattr(col, "default", None)
    if default is None or not getattr(default, "is_scalar", False):
        return None
    arg = default.arg
    if isinstance(arg, bool):
        return "true" if arg else "false"
    if isinstance(arg, (int, float)):
        return str(arg)
    if isinstance(arg, str):
        escaped = arg.replace("'", "''")
        return f"'{escaped}'"
    return None


def _reconcile_columns(sync_conn) -> None:
    """Add any model column missing from an existing table (additive, idempotent).

    Columns are added NULLABLE regardless of the model's nullability, so the ALTER
    can never fail against existing rows; a scalar default is attached when the model
    has one so existing rows + future inserts get a sensible value. New inserts get
    proper values from the ORM. Whole missing tables are left to create_all."""
    insp = sa_inspect(sync_conn)
    existing_tables = set(insp.get_table_names())
    dialect = sync_conn.dialect
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_cols = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            coltype = col.type.compile(dialect=dialect)
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN IF NOT EXISTS "{col.name}" {coltype}'
            default_sql = _default_sql(col)
            if default_sql is not None:
                ddl += f" DEFAULT {default_sql}"
            sync_conn.execute(text(ddl))
            logger.info("reconcile: added missing column %s.%s", table.name, col.name)


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
        # Self-heal column drift: add any model column missing from an existing
        # table (covers living_profile and every later column add like notify_channel).
        await conn.run_sync(_reconcile_columns)
    await engine.dispose()
    logger.info("donna tables created + columns reconciled")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_tables())

"""Standalone proactive runner — the 'she texts first' tick.

Periodically runs deterministic proactive checks (finance/M3, and future
sources) across users and surfaces L0/L1 cards when something needs the user.
Launched by ``bin/start.sh`` when ``DONNA_PROCESS_ROLE=proactive``. It must NOT
be co-located with the API (proactive turns can take seconds and would block
inbound webhooks) — run it as its own process.

When ``PORT`` is set (Railway), serves a tiny ``/health`` so the healthcheck
passes. Liveness only — does not poke the DB.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from donna_runtime.env import load_dotenv

load_dotenv(ROOT / ".env")

from backend.proactive.runner import run_forever
from db.migrations import create_tables

logger = logging.getLogger(__name__)


async def _serve_health(port: int) -> None:
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()

    @app.get("/health")
    def _health() -> dict:
        return {"status": "ok", "role": "proactive"}

    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning", access_log=False)
    )
    await server.serve()


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Donna proactive runner — runs deterministic checks across users.",
    )
    parser.add_argument("--poll", type=float, default=300.0)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-36s  %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("proactive runner starting (poll=%.0fs)", args.poll)

    try:
        await create_tables()
    except Exception:
        logger.exception("proactive: create_tables failed (DB unreachable?) — continuing")

    port_raw = os.environ.get("PORT")
    if port_raw:
        try:
            asyncio.create_task(_serve_health(int(port_raw)), name="health")
            logger.info("proactive: /health on :%s", port_raw)
        except ValueError:
            logger.warning("proactive: PORT=%r is not an int — skipping health", port_raw)

    await run_forever(poll_interval_s=args.poll)


if __name__ == "__main__":
    asyncio.run(main())

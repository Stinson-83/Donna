"""The proactive runner — the 'she texts first' tick (proactive_runner.md).

Periodically runs the registered deterministic checks across users. Each check
is cheap until it decides to surface — at which point it invokes the BRAIN loop,
already gated by the proactive rate-limit + notification policy (the three gates,
proactive_runner §2). The runner itself does NO reasoning and makes NO LLM calls;
it only dispatches (ADR §2).

First cut: a periodic full-scan over users. The per-watch `next_check` / Dynamic
Check cadence (proactive_runner §4-6) and the durable `watches` table are the
documented optimization that layers on top of this; until then, the per-(user,
source) rate-limit (`can_fire_proactive`) provides the anti-spam, so even a tight
poll cannot spam or re-surface an unchanged situation.

Inbound-webhook-driven moments (e.g. email, M2) do NOT live here — they fire from
their integration webhook. This runner is for situations with no inbound push:
finance (M3), subscriptions (M8), relationship lead-times (M7), ...
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# A proactive check: deterministic until it decides to surface. (user_id) -> None.
ProactiveCheck = Callable[[str], Awaitable[None]]


def default_checks() -> list[ProactiveCheck]:
    """The registered proactive checks. Imported lazily so the runner module
    stays cheap to import (and tests can pass their own list)."""
    from backend.finance.trigger import maybe_surface_finance
    from backend.proactive.checks import (
        maybe_checkin_meal,
        maybe_surface_birthday,
        maybe_surface_due_task,
        maybe_watch_interests,
    )
    from backend.proactive.prepare import maybe_prepare_upcoming

    return [
        maybe_surface_finance,
        maybe_prepare_upcoming,
        maybe_surface_due_task,
        maybe_checkin_meal,
        maybe_surface_birthday,
        maybe_watch_interests,
    ]


async def _active_user_ids() -> list[str]:
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        return list((await s.execute(select(User.id))).scalars().all())


async def run_once(checks: list[ProactiveCheck] | None = None) -> int:
    """One tick: run every check for every user. Returns the number of
    (user, check) evaluations performed. Each evaluation is isolated — one
    failure never aborts the sweep."""
    explicit = checks is not None
    checks = default_checks() if checks is None else checks
    user_ids = await _active_user_ids()
    evaluations = 0
    for uid in user_ids:
        for check in checks:
            evaluations += 1
            try:
                await check(uid)
            except Exception:
                logger.exception(
                    "proactive: check %s failed for user=%s",
                    getattr(check, "__name__", check), uid[:8],
                )
    # The default tick also sweeps due watches (the active-watch system).
    if not explicit:
        try:
            from backend.proactive.watches import sweep_due_watches

            await sweep_due_watches()
        except Exception:
            logger.exception("proactive: watch sweep failed")
    if user_ids:
        logger.info(
            "proactive: tick swept %d users x %d checks", len(user_ids), len(checks)
        )
    return evaluations


async def run_forever(poll_interval_s: float = 300.0) -> None:
    """Tick loop. Per-tick errors are caught so the runner never dies on a blip."""
    logger.info("proactive runner: starting (poll=%.0fs)", poll_interval_s)
    while True:
        try:
            await run_once()
        except asyncio.CancelledError:
            logger.info("proactive runner: cancelled")
            raise
        except Exception:
            logger.exception("proactive runner: tick failed")
        await asyncio.sleep(poll_interval_s)

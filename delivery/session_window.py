"""Meta 24h session-window check (A1).

Meta allows freeform messages only within 24h of the last user-initiated message.
Outside that window every outbound must use a pre-approved HSM template.

We use 23h as the check threshold (1h safety buffer) so a message that arrives
right at the boundary doesn't race the clock.

last_active_at is stamped by api/main.py._touch_last_active on every inbound
WhatsApp message. A None value (new user, never messaged back) is treated as
outside the window — the first proactive contact must always be a template.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_SESSION_WINDOW = timedelta(hours=23)


async def is_within_session_window(user_id: str) -> bool:
    """True iff the user has sent a WhatsApp message within the last 23 hours."""
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    try:
        async with async_session() as s:
            last_active = (
                await s.execute(
                    select(User.last_active_at).where(User.id == user_id)
                )
            ).scalar_one_or_none()
    except Exception:
        logger.exception("session_window: DB read failed for user=%s — treating as outside", user_id[:8])
        return False

    if last_active is None:
        return False

    # last_active_at is stored as a naive UTC datetime.
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    return (now_utc - last_active) < _SESSION_WINDOW

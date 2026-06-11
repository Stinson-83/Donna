"""Single-surface proactive delivery — no double-buzz.

A proactive message ALERTS the user on exactly ONE surface: the app (push) if
they have the app installed (a registered device token), otherwise WhatsApp. The
message is still recorded in the one conversation, so the unified History shows
it regardless — the user is only buzzed once.

Reactive replies are not routed here — they go back on whatever surface the user
just messaged from. A user-preferred channel (force WhatsApp even with the app)
is the natural refinement on top of this default.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def deliver_proactive(user_id: str, outbound: list, *, title: str = "donna") -> str:
    """Deliver `outbound` on one surface. Returns 'app' | 'whatsapp' | 'none'."""
    if not outbound:
        return "none"

    from sqlalchemy import select

    from db.models import DeviceToken, User
    from db.session import async_session

    async with async_session() as s:
        has_app = (await s.execute(
            select(DeviceToken.id).where(DeviceToken.user_id == user_id).limit(1)
        )).scalar_one_or_none() is not None
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    # Prefer the app when it's installed — one push, deep-linking into the card.
    if has_app:
        try:
            from backend.integrations.push import notify_outbound

            await notify_outbound(user_id, outbound, title=title)
            return "app"
        except Exception:
            logger.exception("deliver_proactive: app push failed user=%s", user_id[:8])

    # No app (or push failed) -> WhatsApp, but only for a real E.164 number
    # (composio:/web-demo identities are not WhatsApp-reachable).
    phone = (user.phone if user else "") or ""
    if phone.startswith("+"):
        try:
            from delivery.whatsapp import WhatsAppChannel

            await WhatsAppChannel().send_many(phone, outbound)
            return "whatsapp"
        except Exception:
            logger.exception("deliver_proactive: whatsapp send failed user=%s", user_id[:8])

    return "none"

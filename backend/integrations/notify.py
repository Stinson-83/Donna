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


async def deliver_proactive(user_id: str, outbound: list, *, tier: str = "high", title: str = "donna") -> str:
    """Deliver `outbound` on one surface, gated by priority tier. Returns
    'app' | 'whatsapp' | 'held' | 'none'.

    critical/high interrupt (push/send); medium/low are HELD — no buzz. A held
    surface still persists as a card on the dashboard + watch bar; it just doesn't
    actively interrupt (ambient model: notifications stay rare)."""
    if not outbound:
        return "none"

    from backend.integrations.delivery_policy import is_voice_tier, should_interrupt

    if not should_interrupt(tier):
        logger.info("deliver_proactive: held quietly (tier=%s) user=%s", tier, user_id[:8])
        return "held"
    if is_voice_tier(tier):
        # critical is voice-eligible; ambient voice is a future surface, so for now
        # it pushes like high. The hook lives here when voice lands.
        logger.info("deliver_proactive: voice-eligible (tier=critical) user=%s", user_id[:8])

    from sqlalchemy import select

    from db.models import DeviceToken, User
    from db.session import async_session

    async with async_session() as s:
        has_app = (await s.execute(
            select(DeviceToken.id).where(DeviceToken.user_id == user_id).limit(1)
        )).scalar_one_or_none() is not None
        user = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    phone = (user.phone if user else "") or ""
    real_phone = phone.startswith("+")  # composio:/web-demo are not WhatsApp-reachable
    channel = ((user.notify_channel if user else None) or "auto").lower()

    # The user's preferred channel sets the order; the other is a fallback.
    if channel == "whatsapp":
        order = ("whatsapp", "app")
    elif channel == "app":
        order = ("app", "whatsapp")
    else:  # auto — app when installed, else WhatsApp
        order = ("app", "whatsapp") if has_app else ("whatsapp", "app")

    for surface in order:
        if surface == "app" and has_app:
            try:
                from backend.integrations.push import notify_outbound

                await notify_outbound(user_id, outbound, title=title)
                return "app"
            except Exception:
                logger.exception("deliver_proactive: app push failed user=%s", user_id[:8])
        elif surface == "whatsapp" and real_phone:
            try:
                from delivery.whatsapp import WhatsAppChannel

                await WhatsAppChannel().send_many(phone, outbound)
                return "whatsapp"
            except Exception:
                logger.exception("deliver_proactive: whatsapp send failed user=%s", user_id[:8])

    return "none"

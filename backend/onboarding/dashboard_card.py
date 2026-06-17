"""Send the 'open your dashboard' WhatsApp card after onboarding completes (A2).

Called by composio_webhook._run_onboarding_bg right after the backfill finishes.
Sends a CTAUrlMessage with a per-user magic link so the user can open their
personal dashboard without ever leaving WhatsApp.

Skips silently when:
- no DASHBOARD_BASE_URL is configured (dev/test)
- the user has no real phone (composio-only entity, created without WhatsApp)
- the WhatsApp token isn't set (non-WhatsApp environments)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def send_dashboard_card(user_id: str) -> None:
    """Mint a magic link for user_id and deliver the dashboard CTA via WhatsApp."""
    from config import settings

    if not settings.dashboard_base_url:
        logger.debug("dashboard_card: DASHBOARD_BASE_URL unset — skipping for user=%s", user_id[:8])
        return
    if not settings.whatsapp_token:
        logger.debug("dashboard_card: WHATSAPP_TOKEN unset — skipping for user=%s", user_id[:8])
        return

    phone = await _phone_for(user_id)
    if not phone:
        return

    from api.auth import mint_magic_link
    from delivery.messages import CTAUrlMessage
    from delivery.whatsapp import WhatsAppChannel

    link = mint_magic_link(user_id)
    card = CTAUrlMessage(
        body=(
            "your dashboard is live. everything i know about your life — "
            "schedule, beliefs, what i'm watching — in one place."
        ),
        display_text="open dashboard",
        url=link,
    )
    try:
        await WhatsAppChannel().send(phone, card)
        logger.info("dashboard_card: sent to user=%s", user_id[:8])
    except Exception:
        logger.exception("dashboard_card: send failed for user=%s", user_id[:8])


async def _phone_for(user_id: str) -> str | None:
    """Return the user's WhatsApp phone, or None if they have no real phone."""
    from sqlalchemy import select

    from db.models import User
    from db.session import async_session

    async with async_session() as s:
        phone = (
            await s.execute(select(User.phone).where(User.id == user_id))
        ).scalar_one_or_none()

    if not phone or phone.startswith("composio:"):
        logger.debug(
            "dashboard_card: no real phone for user=%s (phone=%r) — skipping",
            user_id[:8], phone,
        )
        return None
    return phone

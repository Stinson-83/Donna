"""Card persistence. Action resolution lives in resolution.py (M2 taps)."""
from __future__ import annotations

import logging
from datetime import timezone

from backend.cards.models import DonnaCard

logger = logging.getLogger(__name__)


def _naive_utc(dt):
    """DB DateTime columns are naive UTC (see db.models.utcnow). Normalize any
    tz-aware DonnaCard.expires_at to naive UTC so comparisons stay consistent."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def persist_card(user_id: str, card: DonnaCard, action_map: dict) -> None:
    """Insert a cards row. payload = the validated DonnaCard sent to surfaces;
    action_map = SERVER-ONLY action_id -> {kind,tool,args,...}. Idempotent on
    card_id (a re-render of the same card is ignored, not duplicated)."""
    from sqlalchemy import select

    from db.models import Card
    from db.session import async_session

    async with async_session() as s:
        existing = (
            await s.execute(select(Card.id).where(Card.id == card.card_id))
        ).scalar_one_or_none()
        if existing:
            logger.info("persist_card: card %s already exists — skipping", card.card_id)
            return
        s.add(
            Card(
                id=card.card_id,
                user_id=user_id,
                intent=card.intent,
                payload=card.model_dump(mode="json", by_alias=True),
                action_map=action_map or {},
                state="pending",
                expires_at=_naive_utc(card.expires_at),
            )
        )
        await s.commit()
        logger.info(
            "persist_card: stored %s intent=%s actions=%d user=%s",
            card.card_id, card.intent, len(action_map or {}), user_id[:8],
        )

"""Deterministic surface projection: one DonnaCard renders to each surface
(donna-design-spec/SURFACES.md). WhatsApp first (M2): the Actions block becomes
reply buttons; the body becomes the message text.

No LLM here — pure rendering, per the ADR (projection is deterministic).
"""
from __future__ import annotations

from delivery.messages import Button, CTAMessage, OutboundMessage, TextMessage

from backend.cards.models import (
    ActionsBlock,
    BodyBlock,
    DonnaCard,
    HeaderBlock,
    KeyValuesBlock,
)


def _wa_bold(text: str) -> str:
    # DonnaCard marks facts with **bold**; WhatsApp bold is *single-asterisk*.
    return text.replace("**", "*")


def card_body_text(card: DonnaCard) -> str:
    """The card's primary words (body, else header label)."""
    body = next((b for b in card.blocks if isinstance(b, BodyBlock)), None)
    if body and body.text:
        return body.text
    header = next((b for b in card.blocks if isinstance(b, HeaderBlock)), None)
    return header.label if header else ""


def fallback_text_from_raw(payload: dict) -> str:
    """Best-effort text from an INVALID payload, so a broken card still says
    something (never a broken card — design law)."""
    blocks = payload.get("blocks") or []
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "body" and b.get("text"):
            return _wa_bold(str(b["text"]))
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "header" and b.get("label"):
            return str(b["label"])
    return ""


def card_to_whatsapp(card: DonnaCard) -> OutboundMessage | None:
    """Project a DonnaCard to a WhatsApp message.

    Actions block -> CTA reply buttons. Each button id encodes `card_id:action_id`
    so a tap round-trips to the exact card + action (cards_and_delivery §11).
    """
    body = next((b for b in card.blocks if isinstance(b, BodyBlock)), None)
    header = next((b for b in card.blocks if isinstance(b, HeaderBlock)), None)
    kvs = next((b for b in card.blocks if isinstance(b, KeyValuesBlock)), None)

    lines: list[str] = []
    if body and body.text:
        lines.append(body.text)
    elif header:
        lines.append(header.label)
    if kvs:
        lines.extend(f"{row.k}: {row.v}" for row in kvs.rows)
    text = _wa_bold("\n".join(lines).strip())
    if not text:
        return None

    actions = next((b for b in card.blocks if isinstance(b, ActionsBlock)), None)
    if actions and actions.actions:
        buttons = [
            Button(id=f"{card.card_id}:{a.action_id}", title=a.label)
            for a in actions.actions
        ]
        return CTAMessage(body=text, buttons=buttons)
    return TextMessage(body=text)

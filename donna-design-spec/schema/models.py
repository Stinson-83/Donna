"""Donna card models v1 — backend twin of schema/card.schema.json.

Validate every model-emitted payload with DonnaCard.model_validate(payload).
On ValidationError: fall back to sending body text as a plain message.
Keep this file generated/checked against the JSON Schema in CI so the
frontend TS types and these models can never drift.
"""
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional, Union, List
from pydantic import BaseModel, Field

# ── blocks ────────────────────────────────────────────────────────────

class HeaderBlock(BaseModel):
    type: Literal["header"] = "header"
    label: str = Field(max_length=28)
    ref: Optional[str] = Field(default=None, max_length=24)

class BodyBlock(BaseModel):
    type: Literal["body"] = "body"
    text: str = Field(max_length=200, description="Donna voice: lowercase, no em dashes, **bold** facts")

class DeltaBlock(BaseModel):
    type: Literal["delta"] = "delta"
    from_: Optional[str] = Field(default=None, alias="from")
    to: str
    from_caption: Optional[str] = Field(default=None, max_length=16)
    to_caption: Optional[str] = Field(default=None, max_length=16)
    kind: Literal["time", "money", "count", "text"] = "text"

    model_config = {"populate_by_name": True}

class KVRow(BaseModel):
    k: str = Field(max_length=24)
    v: str = Field(max_length=32)
    strike: Optional[str] = None

class KeyValuesBlock(BaseModel):
    type: Literal["key_values"] = "key_values"
    rows: List[KVRow] = Field(min_length=1, max_length=4)

class Step(BaseModel):
    name: str = Field(max_length=40)
    sub: Optional[str] = Field(default=None, max_length=64)
    state: Literal["done", "now", "next"]

class StepsBlock(BaseModel):
    type: Literal["steps"] = "steps"
    steps: List[Step] = Field(min_length=2, max_length=6)

class ScopesBlock(BaseModel):
    type: Literal["scopes"] = "scopes"
    service: Optional[str] = None
    account: Optional[str] = None
    items: List[str] = Field(min_length=1, max_length=4)
    note: Optional[str] = Field(default=None, max_length=48)

class FileBlock(BaseModel):
    type: Literal["file"] = "file"
    name: str
    kind: Literal["pdf", "image", "doc", "sheet"]
    meta: Optional[str] = None
    url: Optional[str] = None
    downloadable: bool = True

class DeltaChip(BaseModel):
    text: str = Field(max_length=20)
    direction: Literal["up", "down"]
    good: bool

class GraphBlock(BaseModel):
    type: Literal["graph"] = "graph"
    points: List[float] = Field(min_length=4, max_length=90)
    target: Optional[float] = None
    current_label: Optional[str] = None
    target_label: Optional[str] = None
    delta_chip: Optional[DeltaChip] = None

class Action(BaseModel):
    label: str = Field(max_length=18)
    action_id: str
    style: Literal["primary", "secondary"]

class ActionsBlock(BaseModel):
    type: Literal["actions"] = "actions"
    actions: List[Action] = Field(min_length=1, max_length=2)

class FooterBlock(BaseModel):
    type: Literal["footer"] = "footer"
    text: str = Field(max_length=80)
    right: Optional[str] = Field(default=None, max_length=32)

Block = Union[
    HeaderBlock, BodyBlock, DeltaBlock, KeyValuesBlock, StepsBlock,
    ScopesBlock, FileBlock, GraphBlock, ActionsBlock, FooterBlock,
]

# ── card ──────────────────────────────────────────────────────────────

Intent = Literal[
    "approval", "confirmation", "tracker", "consent_integration",
    "document", "heads_up", "options", "info",
]
Theme = Literal["dark", "light", "settled"]

THEME_DEFAULTS: dict[str, Theme] = {
    "approval": "dark",
    "heads_up": "light",
    "tracker": "light",
    "consent_integration": "light",
    "document": "light",
    "options": "light",
    "info": "light",
    "confirmation": "settled",
}

class DonnaCard(BaseModel):
    version: Literal[1] = 1
    card_id: str
    intent: Intent
    theme: Theme
    expires_at: Optional[datetime] = None
    blocks: List[Block] = Field(min_length=1, max_length=8)

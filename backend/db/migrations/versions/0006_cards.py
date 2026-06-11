"""Cards — DonnaCard persistence wrapper (interactive cards + action resolution).

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message_id", sa.String(), nullable=True),
        sa.Column("intent", sa.String(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("action_map", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("state", sa.String(), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("acted_action_id", sa.String(), nullable=True),
        sa.Column("acted_surface", sa.String(), nullable=True),
        sa.Column("acted_at", sa.DateTime(), nullable=True),
        sa.Column("card_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_cards_user_state", "cards", ["user_id", "state"])
    op.create_index("idx_cards_user_created", "cards", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_cards_user_created", table_name="cards")
    op.drop_index("idx_cards_user_state", table_name="cards")
    op.drop_table("cards")

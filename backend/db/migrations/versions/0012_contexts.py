"""Context Layer — the dynamic 'season of life' store.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contexts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("state", sa.String(), nullable=False, server_default="active"),
        sa.Column("source", sa.String(), nullable=False, server_default="inferred"),
        sa.Column("evidence", JSONB(), nullable=False, server_default="{}"),
        sa.Column("domains", JSONB(), nullable=False, server_default="{}"),
        sa.Column("onset_at", sa.DateTime(), nullable=False),
        sa.Column("last_signal_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("uq_context_user_kind", "contexts", ["user_id", "kind"], unique=True)
    op.create_index("idx_context_user_state", "contexts", ["user_id", "state"])


def downgrade() -> None:
    op.drop_index("idx_context_user_state", table_name="contexts")
    op.drop_index("uq_context_user_kind", table_name="contexts")
    op.drop_table("contexts")

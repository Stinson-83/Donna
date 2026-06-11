"""Watches — standing situations Donna monitors (active-watch system).

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("watch_type", sa.String(), nullable=False),
        sa.Column("subject_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("next_check", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_known_state", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("stable_checks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_watch_user_type_subject", "watches", ["user_id", "watch_type", "subject_key"], unique=True)
    op.create_index("idx_watch_status_next", "watches", ["status", "next_check"])
    op.create_index("idx_watch_user_status", "watches", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_watch_user_status", table_name="watches")
    op.drop_index("idx_watch_status_next", table_name="watches")
    op.drop_index("uq_watch_user_type_subject", table_name="watches")
    op.drop_table("watches")

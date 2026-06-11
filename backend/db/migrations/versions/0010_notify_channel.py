"""User preferred notification channel (auto | app | whatsapp).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("notify_channel", sa.String(), nullable=False, server_default="auto"))


def downgrade() -> None:
    op.drop_column("users", "notify_channel")

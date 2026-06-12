"""Open-loop due_date + category (personal-ops admin tasks).

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("open_loops", sa.Column("due_date", sa.DateTime(), nullable=True))
    op.add_column("open_loops", sa.Column("category", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("open_loops", "category")
    op.drop_column("open_loops", "due_date")

"""Finance domain tables — accounts, bills, transactions (M3 + dashboard logistics).

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finance_accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("account_type", sa.String(), nullable=False),
        sa.Column("institution", sa.String(), nullable=True),
        sa.Column("masked_number", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False, server_default="INR"),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("balance_synced_at", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(), nullable=True, server_default="manual"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_finacct_user_type", "finance_accounts", ["user_id", "account_type"])

    op.create_table(
        "bills",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_id", sa.String(), sa.ForeignKey("finance_accounts.id"), nullable=True),
        sa.Column("biller", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="INR"),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("auto_pay", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(), nullable=False, server_default="upcoming"),
        sa.Column("source", sa.String(), nullable=True, server_default="manual"),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_bills_user_due", "bills", ["user_id", "due_date"])
    op.create_index("idx_bills_user_status", "bills", ["user_id", "status"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_id", sa.String(), sa.ForeignKey("finance_accounts.id"), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="INR"),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("merchant", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_txn_user_occurred", "transactions", ["user_id", "occurred_at"])
    op.create_index("idx_txn_account", "transactions", ["account_id"])


def downgrade() -> None:
    op.drop_index("idx_txn_account", table_name="transactions")
    op.drop_index("idx_txn_user_occurred", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("idx_bills_user_status", table_name="bills")
    op.drop_index("idx_bills_user_due", table_name="bills")
    op.drop_table("bills")
    op.drop_index("idx_finacct_user_type", table_name="finance_accounts")
    op.drop_table("finance_accounts")

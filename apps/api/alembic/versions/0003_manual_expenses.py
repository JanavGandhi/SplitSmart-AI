"""Add manually entered group expenses and participant shares.

Revision ID: 0003_manual_expenses
Revises: 0002_receipt_finalize
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_manual_expenses"
down_revision: str | None = "0002_receipt_finalize"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manual_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("paid_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_paise > 0",
            name="ck_manual_expense_amount_positive",
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manual_expenses_group_id", "manual_expenses", ["group_id"])

    op.create_table(
        "expense_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expense_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("share_paise", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "share_paise >= 0",
            name="ck_expense_participant_share_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["expense_id"], ["manual_expenses.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expense_id", "user_id", name="uq_expense_participant"),
    )
    op.create_index("ix_expense_participants_expense_id", "expense_participants", ["expense_id"])


def downgrade() -> None:
    op.drop_index("ix_expense_participants_expense_id", table_name="expense_participants")
    op.drop_table("expense_participants")
    op.drop_index("ix_manual_expenses_group_id", table_name="manual_expenses")
    op.drop_table("manual_expenses")

"""Persist receipt finalization idempotency keys.

Revision ID: 0002_receipt_finalize_idempotency
Revises: 0001_initial
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_receipt_finalize_idempotency"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "receipts",
        sa.Column("finalize_idempotency_key", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("receipts", "finalize_idempotency_key")

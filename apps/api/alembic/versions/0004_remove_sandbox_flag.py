"""Remove the obsolete sandbox marker from groups.

Revision ID: 0004_remove_sandbox_flag
Revises: 0003_manual_expenses
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_remove_sandbox_flag"
down_revision: str | None = "0003_manual_expenses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("groups", "is_sandbox")


def downgrade() -> None:
    op.add_column(
        "groups",
        sa.Column(
            "is_sandbox",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

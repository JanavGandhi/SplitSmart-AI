"""Initial migration — create all SplitSmart AI tables with pgvector.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── ENUM types ─────────────────────────────────────────────────────────
    receipt_status_enum = postgresql.ENUM(
        "QUEUED", "PROCESSING", "READY_FOR_CLAIMS", "LOCKED", "SETTLED", "FAILED",
        name="receipt_status",
    )
    receipt_status_enum.create(op.get_bind())

    entry_type_enum = postgresql.ENUM(
        "EXPENSE_SHARE", "SETTLEMENT",
        name="entry_type",
    )
    entry_type_enum.create(op.get_bind())

    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("upi_id", sa.String(100), nullable=True),
        sa.Column("avatar_color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── groups ─────────────────────────────────────────────────────────────
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("invite_code", sa.String(12), nullable=False, unique=True),
        sa.Column("is_sandbox", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_groups_invite_code", "groups", ["invite_code"])

    # ── group_members ──────────────────────────────────────────────────────
    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])

    # ── receipts ───────────────────────────────────────────────────────────
    op.create_table(
        "receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("paid_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("room_code", sa.String(12), nullable=False, unique=True),
        sa.Column("merchant_name", sa.String(200), nullable=True),
        sa.Column("receipt_date", sa.Date(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("status", receipt_status_enum, nullable=False, server_default="QUEUED"),
        # Monetary values — all in paise (BIGINT)
        sa.Column("subtotal_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tax_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("service_charge_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("delivery_fee_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("discount_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("raw_ocr_json", postgresql.JSONB(), nullable=True),
        # pgvector column — 768 dimensions for text-embedding-004
        sa.Column("embedding", sa.Text(), nullable=True),  # Stored as text then cast
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_receipts_room_code", "receipts", ["room_code"])
    op.create_index("ix_receipts_group_id", "receipts", ["group_id"])

    # Add proper vector column for embedding
    op.execute("ALTER TABLE receipts ADD COLUMN IF NOT EXISTS embedding_vec vector(768)")

    # ── receipt_line_items ─────────────────────────────────────────────────
    op.create_table(
        "receipt_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price_paise", sa.BigInteger(), nullable=False),
        sa.Column("total_price_paise", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
    )
    op.create_index("ix_receipt_line_items_receipt_id", "receipt_line_items", ["receipt_id"])

    # ── item_claims ────────────────────────────────────────────────────────
    op.create_table(
        "item_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("line_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("receipt_line_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("share_fraction_numerator", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("share_fraction_denominator", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("calculated_item_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("calculated_tax_and_fees_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("calculated_final_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.UniqueConstraint("line_item_id", "user_id", name="uq_item_claim"),
    )
    op.create_index("ix_item_claims_line_item_id", "item_claims", ["line_item_id"])
    op.create_index("ix_item_claims_user_id", "item_claims", ["user_id"])

    # ── ledger_entries ─────────────────────────────────────────────────────
    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("entry_type", entry_type_enum, nullable=False, server_default="EXPENSE_SHARE"),
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_paise > 0", name="ck_ledger_amount_positive"),
    )
    op.create_index("ix_ledger_entries_group_id", "ledger_entries", ["group_id"])
    op.create_index("ix_ledger_entries_from_user_id", "ledger_entries", ["from_user_id"])
    op.create_index("ix_ledger_entries_to_user_id", "ledger_entries", ["to_user_id"])


def downgrade() -> None:
    op.drop_table("ledger_entries")
    op.drop_table("item_claims")
    op.drop_table("receipt_line_items")
    op.drop_table("receipts")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS receipt_status")
    op.execute("DROP TYPE IF EXISTS entry_type")
    op.execute("DROP EXTENSION IF EXISTS vector")

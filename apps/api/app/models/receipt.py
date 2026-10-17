"""Receipt ORM model — core entity with paise-based monetary columns and pgvector embedding."""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_TYPE = Vector(768)
except ImportError:
    # Fallback if pgvector not installed locally (Docker will have it)
    from sqlalchemy import JSON
    VECTOR_TYPE = None  # type: ignore[assignment]


class ReceiptStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    READY_FOR_CLAIMS = "READY_FOR_CLAIMS"
    LOCKED = "LOCKED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        Index("ix_receipts_room_code", "room_code"),
        Index("ix_receipts_group_id", "group_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    paid_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Multiplayer room
    room_code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)

    # Receipt details
    merchant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Processing status
    status: Mapped[ReceiptStatus] = mapped_column(
        Enum(ReceiptStatus, name="receipt_status"),
        nullable=False,
        default=ReceiptStatus.QUEUED,
    )

    # Monetary values — ALL in paise (1 INR = 100 paise), stored as BIGINT
    subtotal_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    service_charge_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    delivery_fee_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # OCR output
    raw_ocr_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # pgvector embedding for semantic search (768 dims = text-embedding-004)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768) if VECTOR_TYPE is not None else JSONB,  # type: ignore[arg-type]
        nullable=True,
    )

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    group: Mapped["Group"] = relationship(  # type: ignore[name-defined]
        "Group", back_populates="receipts"
    )
    uploader: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[uploaded_by], back_populates="uploaded_receipts"
    )
    payer: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[paid_by], back_populates="paid_receipts"
    )
    line_items: Mapped[list["ReceiptLineItem"]] = relationship(  # type: ignore[name-defined]
        "ReceiptLineItem", back_populates="receipt", cascade="all, delete-orphan", lazy="select"
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(  # type: ignore[name-defined]
        "LedgerEntry", back_populates="receipt", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Receipt id={self.id} merchant={self.merchant_name!r} status={self.status}>"

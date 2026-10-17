"""LedgerEntry ORM model — ACID double-entry style expense tracking."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EntryType(str, enum.Enum):
    EXPENSE_SHARE = "EXPENSE_SHARE"
    SETTLEMENT = "SETTLEMENT"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_ledger_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receipt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True
    )

    # Debtor → Creditor
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Amount in paise — always positive (direction encoded by from/to)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    entry_type: Mapped[EntryType] = mapped_column(
        Enum(EntryType, name="entry_type"),
        nullable=False,
        default=EntryType.EXPENSE_SHARE,
    )

    # Idempotency key prevents duplicate entries
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    group: Mapped["Group"] = relationship(  # type: ignore[name-defined]
        "Group", back_populates="ledger_entries"
    )
    receipt: Mapped["Receipt | None"] = relationship(  # type: ignore[name-defined]
        "Receipt", back_populates="ledger_entries"
    )
    debtor: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[from_user_id]
    )
    creditor: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[to_user_id]
    )

    def __repr__(self) -> str:
        return (
            f"<LedgerEntry {self.from_user_id} -> {self.to_user_id} "
            f"amount={self.amount_paise}p type={self.entry_type}>"
        )

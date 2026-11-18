"""Manual group expenses and the members' paise-accurate shares."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ManualExpense(Base):
    __tablename__ = "manual_expenses"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_manual_expense_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    participants: Mapped[list["ExpenseParticipant"]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payer: Mapped["User"] = relationship(foreign_keys=[paid_by_user_id])


class ExpenseParticipant(Base):
    __tablename__ = "expense_participants"
    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_participant"),
        CheckConstraint("share_paise >= 0", name="ck_expense_participant_share_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    expense_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manual_expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    share_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    expense: Mapped["ManualExpense"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()

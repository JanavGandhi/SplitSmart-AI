"""Group ORM model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.group_member import GroupMember
    from app.models.ledger_entry import LedgerEntry
    from app.models.receipt import Receipt
    from app.models.user import User


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], lazy="select"
    )
    members: Mapped[list["GroupMember"]] = relationship(
        "GroupMember", back_populates="group", lazy="select", cascade="all, delete-orphan"
    )
    receipts: Mapped[list["Receipt"]] = relationship(
        "Receipt", back_populates="group", lazy="select", cascade="all, delete-orphan"
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        "LedgerEntry", back_populates="group", lazy="select", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r}>"

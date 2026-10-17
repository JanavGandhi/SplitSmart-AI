"""User ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    upi_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    group_memberships: Mapped[list["GroupMember"]] = relationship(  # type: ignore[name-defined]
        "GroupMember", back_populates="user", lazy="select"
    )
    uploaded_receipts: Mapped[list["Receipt"]] = relationship(  # type: ignore[name-defined]
        "Receipt", foreign_keys="Receipt.uploaded_by", back_populates="uploader", lazy="select"
    )
    paid_receipts: Mapped[list["Receipt"]] = relationship(  # type: ignore[name-defined]
        "Receipt", foreign_keys="Receipt.paid_by", back_populates="payer", lazy="select"
    )
    item_claims: Mapped[list["ItemClaim"]] = relationship(  # type: ignore[name-defined]
        "ItemClaim", back_populates="user", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} display_name={self.display_name!r}>"

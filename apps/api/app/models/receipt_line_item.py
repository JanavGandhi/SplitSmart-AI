"""ReceiptLineItem ORM model."""
import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReceiptLineItem(Base):
    __tablename__ = "receipt_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Monetary values in paise
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    receipt: Mapped["Receipt"] = relationship(  # type: ignore[name-defined]
        "Receipt", back_populates="line_items"
    )
    claims: Mapped[list["ItemClaim"]] = relationship(  # type: ignore[name-defined]
        "ItemClaim", back_populates="line_item", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<LineItem id={self.id} name={self.item_name!r} "
            f"total={self.total_price_paise}p>"
        )

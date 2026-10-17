"""ItemClaim ORM model — user's claim on a receipt line item with share fractions."""
import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ItemClaim(Base):
    __tablename__ = "item_claims"
    __table_args__ = (
        UniqueConstraint("line_item_id", "user_id", name="uq_item_claim"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("receipt_line_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Share fraction: e.g. 1/3 means this user pays 1/3 of the item
    share_fraction_numerator: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    share_fraction_denominator: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Computed values (filled after math_engine calculation, stored in paise)
    calculated_item_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    calculated_tax_and_fees_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    calculated_final_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Relationships
    line_item: Mapped["ReceiptLineItem"] = relationship(  # type: ignore[name-defined]
        "ReceiptLineItem", back_populates="claims"
    )
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="item_claims"
    )

    def __repr__(self) -> str:
        return (
            f"<ItemClaim item={self.line_item_id} user={self.user_id} "
            f"share={self.share_fraction_numerator}/{self.share_fraction_denominator}>"
        )

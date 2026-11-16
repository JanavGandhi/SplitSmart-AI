"""
Ledger API — Settlement recording with idempotency.

POST /api/v1/ledger/settle — Record a settlement payment between two users.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.ledger_entry import EntryType, LedgerEntry
from app.models.user import User
from app.schemas.common import BaseSchema
from app.services.upi_generator import generate_settlement_link

router = APIRouter(prefix="/ledger", tags=["ledger"])


class SettlementRequest(BaseSchema):
    """Request body for recording a settlement."""
    group_id: uuid.UUID
    from_user_id: uuid.UUID  # debtor
    to_user_id: uuid.UUID  # creditor
    amount_paise: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=1, max_length=64)


class SettlementResponse(BaseSchema):
    """Response after recording a settlement."""
    id: uuid.UUID
    group_id: uuid.UUID
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    amount_paise: int
    entry_type: str
    idempotency_key: str
    created: bool  # True if new, False if duplicate (idempotent)


class UPIPaymentRequest(BaseSchema):
    group_id: uuid.UUID
    creditor_user_id: uuid.UUID
    amount_paise: int = Field(..., gt=0)


class UPIPaymentResponse(BaseSchema):
    uri: str
    qr_base64: str
    amount_rupees: str
    payee_name: str
    payee_upi_id: str
    note: str


@router.post("/upi-intent", response_model=UPIPaymentResponse)
async def create_upi_intent(
    payload: UPIPaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a UPI deep link and QR code for a group creditor."""
    result = await db.execute(
        select(User, Group.name)
        .join(GroupMember, GroupMember.user_id == User.id)
        .join(Group, Group.id == GroupMember.group_id)
        .where(
            Group.id == payload.group_id,
            User.id == payload.creditor_user_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Creditor is not a member of this group")

    creditor, group_name = row
    if not creditor.upi_id:
        raise HTTPException(status_code=422, detail="Creditor has no UPI ID configured")

    payment = generate_settlement_link(
        debtor_name="SplitSmart member",
        creditor_name=creditor.display_name,
        creditor_upi_id=creditor.upi_id,
        amount_paise=payload.amount_paise,
        group_name=group_name,
    )
    return UPIPaymentResponse(
        uri=payment.uri,
        qr_base64=payment.qr_base64,
        amount_rupees=payment.amount_rupees,
        payee_name=payment.payee_name,
        payee_upi_id=payment.payee_upi_id,
        note=payment.note,
    )


@router.post("/settle", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
async def record_settlement(
    payload: SettlementRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a settlement payment between two users.

    Idempotent: if the same idempotency_key is used, returns the existing entry
    without creating a duplicate.
    """
    # Check for existing entry with same idempotency key
    existing_stmt = select(LedgerEntry).where(
        LedgerEntry.idempotency_key == payload.idempotency_key
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        is_settlement = existing.entry_type == EntryType.SETTLEMENT
        return SettlementResponse(
            id=existing.id,
            group_id=existing.group_id,
            from_user_id=existing.to_user_id if is_settlement else existing.from_user_id,
            to_user_id=existing.from_user_id if is_settlement else existing.to_user_id,
            amount_paise=existing.amount_paise,
            entry_type=existing.entry_type.value,
            idempotency_key=existing.idempotency_key,
            created=False,
        )

    # Verify group exists
    group_stmt = select(Group).where(Group.id == payload.group_id)
    group_result = await db.execute(group_stmt)
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Validate from != to
    if payload.from_user_id == payload.to_user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot settle a debt with yourself",
        )

    # Create settlement entry
    entry = LedgerEntry(
        id=uuid.uuid4(),
        group_id=payload.group_id,
        # A payment reverses the original debt edge in the balance ledger.
        from_user_id=payload.to_user_id,
        to_user_id=payload.from_user_id,
        amount_paise=payload.amount_paise,
        entry_type=EntryType.SETTLEMENT,
        idempotency_key=payload.idempotency_key,
    )
    db.add(entry)
    await db.flush()

    return SettlementResponse(
        id=entry.id,
        group_id=entry.group_id,
        from_user_id=payload.from_user_id,
        to_user_id=payload.to_user_id,
        amount_paise=entry.amount_paise,
        entry_type=entry.entry_type.value,
        idempotency_key=entry.idempotency_key,
        created=True,
    )

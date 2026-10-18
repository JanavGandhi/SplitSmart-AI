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
from app.models.ledger_entry import LedgerEntry, EntryType
from app.schemas.common import BaseSchema

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
        return SettlementResponse(
            id=existing.id,
            group_id=existing.group_id,
            from_user_id=existing.from_user_id,
            to_user_id=existing.to_user_id,
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
        from_user_id=payload.from_user_id,
        to_user_id=payload.to_user_id,
        amount_paise=payload.amount_paise,
        entry_type=EntryType.SETTLEMENT,
        idempotency_key=payload.idempotency_key,
    )
    db.add(entry)
    await db.flush()

    return SettlementResponse(
        id=entry.id,
        group_id=entry.group_id,
        from_user_id=entry.from_user_id,
        to_user_id=entry.to_user_id,
        amount_paise=entry.amount_paise,
        entry_type=entry.entry_type.value,
        idempotency_key=entry.idempotency_key,
        created=True,
    )

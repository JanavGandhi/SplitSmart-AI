"""
Sandbox API — One-click demo initialization.

POST /api/v1/sandbox/init → Creates the "Goa Weekend Squad" demo group
with 5 members, 4 receipts, claims, and ledger entries.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.sandbox import create_sandbox

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.post("/init", status_code=status.HTTP_201_CREATED)
async def init_sandbox(
    db: AsyncSession = Depends(get_db),
):
    """
    Initialize a complete demo sandbox.

    Creates the "Goa Weekend Squad" group with:
    - 5 members (Aryan, Priya, Karan, Meera, Dev)
    - 4 receipts with realistic line items
    - Claims and computed splits
    - Ledger entries for debt tracking

    The debts are designed to simplify from ~11 transactions → ~4 with
    the min-cash-flow algorithm.
    """
    result = await create_sandbox(db)
    return result

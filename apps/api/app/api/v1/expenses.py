"""Manual expense creation and group expense history."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.ledger_entry import EntryType, LedgerEntry
from app.models.manual_expense import ExpenseParticipant, ManualExpense
from app.schemas.expense import (
    ExpenseParticipantResponse,
    ManualExpenseCreate,
    ManualExpenseResponse,
)

router = APIRouter(prefix="/groups", tags=["expenses"])


def _expense_response(expense: ManualExpense) -> ManualExpenseResponse:
    return ManualExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        description=expense.description,
        amount_paise=expense.amount_paise,
        paid_by_user_id=expense.paid_by_user_id,
        participants=[
            ExpenseParticipantResponse(
                user_id=participant.user_id,
                share_paise=participant.share_paise,
            )
            for participant in expense.participants
        ],
        created_at=expense.created_at,
    )


@router.get(
    "/{group_id}/expenses",
    response_model=list[ManualExpenseResponse],
)
async def list_manual_expenses(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    group_result = await db.execute(select(Group.id).where(Group.id == group_id))
    if group_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Group not found")

    result = await db.execute(
        select(ManualExpense)
        .options(selectinload(ManualExpense.participants))
        .where(ManualExpense.group_id == group_id)
        .order_by(ManualExpense.created_at.desc())
    )
    return [_expense_response(expense) for expense in result.scalars().all()]


@router.post(
    "/{group_id}/expenses",
    response_model=ManualExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_expense(
    group_id: uuid.UUID,
    payload: ManualExpenseCreate,
    db: AsyncSession = Depends(get_db),
):
    group_result = await db.execute(select(Group.id).where(Group.id == group_id))
    if group_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Group not found")

    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = members_result.scalars().all()
    member_ids = {member.user_id for member in members}

    if payload.paid_by_user_id not in member_ids:
        raise HTTPException(status_code=422, detail="Payer must be a member of this group")
    if len(set(payload.participant_user_ids)) != len(payload.participant_user_ids):
        raise HTTPException(status_code=422, detail="Participants must not be duplicated")
    if not set(payload.participant_user_ids).issubset(member_ids):
        raise HTTPException(
            status_code=422,
            detail="All participants must be members of this group",
        )

    description = payload.description.strip()
    if not description:
        raise HTTPException(status_code=422, detail="Description cannot be blank")

    expense = ManualExpense(
        id=uuid.uuid4(),
        group_id=group_id,
        description=description,
        amount_paise=payload.amount_paise,
        paid_by_user_id=payload.paid_by_user_id,
        created_at=datetime.now(UTC),
    )
    db.add(expense)

    share, remainder = divmod(payload.amount_paise, len(payload.participant_user_ids))
    participants: list[ExpenseParticipant] = []
    for index, user_id in enumerate(payload.participant_user_ids):
        share_paise = share + (1 if index < remainder else 0)
        participant = ExpenseParticipant(
            id=uuid.uuid4(),
            expense_id=expense.id,
            user_id=user_id,
            share_paise=share_paise,
        )
        db.add(participant)
        participants.append(participant)

        if user_id != payload.paid_by_user_id and share_paise > 0:
            db.add(
                LedgerEntry(
                    id=uuid.uuid4(),
                    group_id=group_id,
                    from_user_id=user_id,
                    to_user_id=payload.paid_by_user_id,
                    amount_paise=share_paise,
                    entry_type=EntryType.EXPENSE_SHARE,
                    idempotency_key=uuid.uuid4().hex,
                )
            )

    expense.participants = participants
    await db.flush()
    return _expense_response(expense)

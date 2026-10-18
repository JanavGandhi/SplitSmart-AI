"""
Groups API — CRUD operations for groups and member management.

Endpoints:
- POST /api/v1/groups — Create a new group
- GET  /api/v1/groups — List user's groups (returns all for now, auth in Stage 4)
- GET  /api/v1/groups/{group_id} — Get group detail with members
- GET  /api/v1/groups/{group_id}/balances — Net balance per member
- GET  /api/v1/groups/{group_id}/simplified — Min-cash-flow simplified debts
"""
from __future__ import annotations

import uuid

import shortuuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.ledger_entry import LedgerEntry
from app.models.user import User
from app.schemas.group import GroupCreate, GroupResponse, GroupDetailResponse, MemberResponse
from app.schemas.user import UserPublic
from app.services.debt_simplifier import (
    BalanceEntry,
    simplify_debts,
    compute_net_balances,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new group and return its details."""
    group = Group(
        id=uuid.uuid4(),
        name=payload.name,
        currency=payload.currency,
        invite_code=shortuuid.uuid()[:8].upper(),
        is_sandbox=False,
    )
    db.add(group)
    await db.flush()

    return GroupResponse(
        id=group.id,
        name=group.name,
        currency=group.currency,
        invite_code=group.invite_code,
        is_sandbox=group.is_sandbox,
        created_by=group.created_by,
        created_at=group.created_at,
        member_count=0,
    )


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    db: AsyncSession = Depends(get_db),
):
    """List all groups (will be scoped to user after auth is implemented)."""
    stmt = (
        select(
            Group,
            func.count(GroupMember.id).label("member_count"),
        )
        .outerjoin(GroupMember, Group.id == GroupMember.group_id)
        .group_by(Group.id)
        .order_by(Group.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        GroupResponse(
            id=group.id,
            name=group.name,
            currency=group.currency,
            invite_code=group.invite_code,
            is_sandbox=group.is_sandbox,
            created_by=group.created_by,
            created_at=group.created_at,
            member_count=count,
        )
        for group, count in rows
    ]


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get group details including all members."""
    stmt = (
        select(Group)
        .options(
            selectinload(Group.members).selectinload(GroupMember.user),
        )
        .where(Group.id == group_id)
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        currency=group.currency,
        invite_code=group.invite_code,
        is_sandbox=group.is_sandbox,
        created_by=group.created_by,
        created_at=group.created_at,
        member_count=len(group.members),
        members=[
            MemberResponse(
                id=m.id,
                user=UserPublic(
                    id=m.user.id,
                    display_name=m.user.display_name,
                    avatar_color=m.user.avatar_color,
                    is_guest=m.user.is_guest,
                ),
                joined_at=m.joined_at,
            )
            for m in group.members
        ],
    )


@router.get("/{group_id}/balances")
async def get_balances(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute net balance for each member of the group.

    Returns per-user balances:
    - Positive = is owed money (creditor)
    - Negative = owes money (debtor)
    """
    # Verify group exists
    group_stmt = select(Group).where(Group.id == group_id)
    group_result = await db.execute(group_stmt)
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Fetch all ledger entries for this group
    ledger_stmt = (
        select(LedgerEntry)
        .where(LedgerEntry.group_id == group_id)
    )
    result = await db.execute(ledger_stmt)
    entries = result.scalars().all()

    # Fetch member names
    member_stmt = (
        select(GroupMember)
        .options(selectinload(GroupMember.user))
        .where(GroupMember.group_id == group_id)
    )
    member_result = await db.execute(member_stmt)
    members = member_result.scalars().all()

    user_names = {m.user_id: m.user.display_name for m in members}
    user_colors = {m.user_id: m.user.avatar_color for m in members}

    # Compute net balances
    ledger_dicts = [
        {
            "from_user_id": e.from_user_id,
            "to_user_id": e.to_user_id,
            "amount_paise": e.amount_paise,
        }
        for e in entries
    ]

    balances = compute_net_balances(ledger_dicts, user_names)

    # Include users with zero balance too
    balance_map = {b.user_id: b.net_balance_paise for b in balances}

    return {
        "group_id": str(group_id),
        "group_name": group.name,
        "currency": group.currency,
        "balances": [
            {
                "user_id": str(uid),
                "display_name": user_names.get(uid, "Unknown"),
                "avatar_color": user_colors.get(uid, "#6366f1"),
                "net_balance_paise": balance_map.get(uid, 0),
                "status": (
                    "creditor" if balance_map.get(uid, 0) > 0
                    else "debtor" if balance_map.get(uid, 0) < 0
                    else "settled"
                ),
            }
            for uid in user_names.keys()
        ],
        "total_entries": len(entries),
    }


@router.get("/{group_id}/simplified")
async def get_simplified_debts(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute minimum-cash-flow simplified debts for the group.

    Returns the optimal set of settlements that reduces the number of transactions.
    """
    # Verify group exists
    group_stmt = select(Group).where(Group.id == group_id)
    group_result = await db.execute(group_stmt)
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Fetch all ledger entries
    ledger_stmt = select(LedgerEntry).where(LedgerEntry.group_id == group_id)
    result = await db.execute(ledger_stmt)
    entries = result.scalars().all()

    if not entries:
        return {
            "group_id": str(group_id),
            "group_name": group.name,
            "original_transactions": 0,
            "simplified_transactions": 0,
            "transactions_saved": 0,
            "settlements": [],
        }

    # Fetch member names and UPI IDs
    member_stmt = (
        select(GroupMember)
        .options(selectinload(GroupMember.user))
        .where(GroupMember.group_id == group_id)
    )
    member_result = await db.execute(member_stmt)
    members = member_result.scalars().all()

    user_names = {m.user_id: m.user.display_name for m in members}
    user_upi = {m.user_id: m.user.upi_id for m in members}
    user_colors = {m.user_id: m.user.avatar_color for m in members}

    # Compute balances and simplify
    ledger_dicts = [
        {
            "from_user_id": e.from_user_id,
            "to_user_id": e.to_user_id,
            "amount_paise": e.amount_paise,
        }
        for e in entries
    ]

    balances = compute_net_balances(ledger_dicts, user_names)
    simplification = simplify_debts(balances, original_transaction_count=len(entries))

    return {
        "group_id": str(group_id),
        "group_name": group.name,
        "currency": group.currency,
        "original_transactions": simplification.original_transaction_count,
        "simplified_transactions": simplification.simplified_count,
        "transactions_saved": simplification.transactions_saved,
        "zero_sum_verified": simplification.zero_sum_verified,
        "settlements": [
            {
                "from_user_id": str(s.from_user_id),
                "from_display_name": s.from_display_name,
                "from_avatar_color": user_colors.get(s.from_user_id, "#6366f1"),
                "to_user_id": str(s.to_user_id),
                "to_display_name": s.to_display_name,
                "to_avatar_color": user_colors.get(s.to_user_id, "#6366f1"),
                "to_upi_id": user_upi.get(s.to_user_id),
                "amount_paise": s.amount_paise,
                "amount_display": f"₹{s.amount_paise / 100:.2f}",
            }
            for s in simplification.settlements
        ],
    }

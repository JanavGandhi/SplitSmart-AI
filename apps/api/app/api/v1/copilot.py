"""Group-aware AI Copilot endpoint."""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.ledger_entry import LedgerEntry
from app.models.receipt import Receipt
from app.models.user import User
from app.services.ai_copilot import CopilotProviderError, generate_reply
from app.services.rate_limiter import enforce_ai_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["copilot"])


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    group_id: uuid.UUID

    @field_validator("message")
    @classmethod
    def normalize_message(cls, message: str) -> str:
        normalized = message.strip()
        if not normalized:
            raise ValueError("message must not be blank")
        return normalized


class CopilotChatResponse(BaseModel):
    reply: str


@router.post(
    "/chat",
    response_model=CopilotChatResponse,
    dependencies=[Depends(enforce_ai_rate_limit)],
)
async def chat(
    payload: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
) -> CopilotChatResponse:
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Copilot is not configured. Set GROQ_API_KEY to enable it.",
        )

    group_result = await db.execute(select(Group).where(Group.id == payload.group_id))
    group = group_result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    member_result = await db.execute(
        select(User.id, User.display_name)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == payload.group_id)
    )
    members = member_result.all()
    balances = {user_id: 0 for user_id, _ in members}
    for_user_result = await db.execute(
        select(
            LedgerEntry.from_user_id,
            LedgerEntry.to_user_id,
            LedgerEntry.amount_paise,
        ).where(LedgerEntry.group_id == payload.group_id)
    )
    for debtor_id, creditor_id, amount_paise in for_user_result.all():
        balances[debtor_id] = balances.get(debtor_id, 0) - amount_paise
        balances[creditor_id] = balances.get(creditor_id, 0) + amount_paise

    receipt_result = await db.execute(
        select(Receipt.merchant_name, Receipt.status, Receipt.total_paise)
        .where(Receipt.group_id == payload.group_id)
        .order_by(Receipt.created_at.desc())
        .limit(12)
    )

    group_context = {
        "group_name": group.name,
        "currency": group.currency,
        "members": [
            {
                "name": display_name,
                "net_balance_paise": balances[user_id],
                "position": (
                    "creditor" if balances[user_id] > 0
                    else "debtor" if balances[user_id] < 0
                    else "settled"
                ),
            }
            for user_id, display_name in members
        ],
        "recent_receipts": [
            {
                "merchant": merchant_name or "Unknown merchant",
                "status": getattr(receipt_status, "value", receipt_status),
                "total_paise": total_paise,
            }
            for merchant_name, receipt_status, total_paise in receipt_result.all()
        ],
    }

    try:
        reply = await asyncio.wait_for(
            asyncio.to_thread(
                generate_reply,
                payload.message,
                group_context,
                settings.groq_api_key,
            ),
            timeout=30,
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Copilot timed out. Please try again.",
        ) from exc
    except CopilotProviderError as exc:
        logger.warning("Copilot provider request failed", extra={"group_id": str(payload.group_id)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Copilot could not get a response from the configured AI service.",
        ) from exc

    return CopilotChatResponse(reply=reply)

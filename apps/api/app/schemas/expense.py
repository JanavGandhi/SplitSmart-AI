"""Manual expense API schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class ManualExpenseCreate(BaseSchema):
    description: str = Field(..., min_length=1, max_length=200)
    amount_paise: int = Field(..., gt=0, le=9_223_372_036_854_775_807)
    paid_by_user_id: UUID
    participant_user_ids: list[UUID] = Field(..., min_length=1)


class ExpenseParticipantResponse(BaseSchema):
    user_id: UUID
    share_paise: int


class ManualExpenseResponse(BaseSchema):
    id: UUID
    group_id: UUID
    description: str
    amount_paise: int
    paid_by_user_id: UUID
    participants: list[ExpenseParticipantResponse]
    created_at: datetime

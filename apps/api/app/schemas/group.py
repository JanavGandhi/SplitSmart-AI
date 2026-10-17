"""Group and GroupMember Pydantic schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.user import UserPublic


class GroupCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=200)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")


class GroupResponse(BaseSchema):
    id: UUID
    name: str
    currency: str
    invite_code: str
    is_sandbox: bool
    created_by: UUID | None
    created_at: datetime
    member_count: int = 0


class GroupDetailResponse(GroupResponse):
    members: list["MemberResponse"] = []


class MemberResponse(BaseSchema):
    id: UUID
    user: UserPublic
    joined_at: datetime

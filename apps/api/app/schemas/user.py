"""User Pydantic schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class UserCreate(BaseSchema):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    upi_id: str | None = None


class GuestUserCreate(BaseSchema):
    display_name: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseSchema):
    id: UUID
    email: str | None
    display_name: str
    upi_id: str | None
    avatar_color: str
    is_guest: bool
    created_at: datetime


class UserPublic(BaseSchema):
    """Minimal user info safe to share publicly (e.g., in room participants)."""
    id: UUID
    display_name: str
    avatar_color: str
    is_guest: bool


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str

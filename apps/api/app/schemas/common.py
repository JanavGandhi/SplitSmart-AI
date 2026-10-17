"""Shared Pydantic schemas and base classes."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedSchema(BaseSchema):
    id: UUID
    created_at: datetime


class PaginationParams(BaseSchema):
    page: int = 1
    per_page: int = 20


class PaginatedResponse(BaseSchema):
    items: list
    total: int
    page: int
    per_page: int
    pages: int

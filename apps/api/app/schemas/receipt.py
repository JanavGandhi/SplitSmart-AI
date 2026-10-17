"""Receipt, LineItem, and Claim Pydantic schemas."""
from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.models.receipt import ReceiptStatus
from app.schemas.common import BaseSchema
from app.schemas.user import UserPublic


class LineItemResponse(BaseSchema):
    id: UUID
    item_name: str
    quantity: int
    unit_price_paise: int
    total_price_paise: int
    category: str | None
    # Who claimed this item
    claims: list["ClaimResponse"] = []


class ClaimResponse(BaseSchema):
    id: UUID
    user: UserPublic
    share_fraction_numerator: int
    share_fraction_denominator: int
    calculated_item_paise: int
    calculated_tax_and_fees_paise: int
    calculated_final_paise: int


class ReceiptResponse(BaseSchema):
    id: UUID
    group_id: UUID
    room_code: str
    merchant_name: str | None
    receipt_date: date | None
    image_url: str | None
    status: ReceiptStatus
    subtotal_paise: int
    tax_paise: int
    service_charge_paise: int
    delivery_fee_paise: int
    discount_paise: int
    total_paise: int
    created_at: datetime
    line_items: list[LineItemResponse] = []


class ReceiptUploadResponse(BaseSchema):
    receipt_id: UUID
    room_code: str
    job_id: str
    status: ReceiptStatus
    sse_url: str


class ReceiptSummary(BaseSchema):
    """Lightweight receipt info for list views."""
    id: UUID
    room_code: str
    merchant_name: str | None
    receipt_date: date | None
    status: ReceiptStatus
    total_paise: int
    created_at: datetime

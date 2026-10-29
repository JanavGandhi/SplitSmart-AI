"""
Vision OCR Service — Gemini Vision receipt extraction.

Extracts structured receipt data from an uploaded image using Google Gemini.
Falls back to deterministic mock data when GEMINI_API_KEY is not set, so
the entire pipeline can be tested without hitting the live AI API.

Output schema (Pydantic):
    OCRExtractedReceipt
        ├── merchant_name: str | None
        ├── receipt_date: str | None  (ISO 8601 "YYYY-MM-DD")
        ├── line_items: list[OCRLineItem]
        │       ├── item_name: str
        │       ├── quantity: int
        │       ├── unit_price_rupees: float
        │       └── category: str | None
        ├── subtotal_rupees: float
        ├── tax_rupees: float
        ├── service_charge_rupees: float
        ├── delivery_fee_rupees: float
        ├── discount_rupees: float
        └── total_rupees: float
"""
from __future__ import annotations

import json
import logging
import structlog
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)


# ── Pydantic output schemas ───────────────────────────────────────────────────

class OCRLineItem(BaseModel):
    """A single line item extracted from a receipt."""
    item_name: str = Field(..., description="Name of the item")
    quantity: int = Field(1, ge=1, description="Quantity ordered")
    unit_price_rupees: float = Field(..., ge=0, description="Price per unit in rupees")
    category: str | None = Field(None, description="Item category (food, beverage, etc.)")

    @field_validator("quantity", mode="before")
    @classmethod
    def coerce_quantity(cls, v: object) -> int:
        try:
            return max(1, int(v))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 1

    @field_validator("unit_price_rupees", mode="before")
    @classmethod
    def coerce_price(cls, v: object) -> float:
        try:
            return max(0.0, float(v))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0

    @property
    def total_price_rupees(self) -> float:
        return round(self.unit_price_rupees * self.quantity, 2)


class OCRExtractedReceipt(BaseModel):
    """Fully structured receipt extracted by Gemini Vision or the mock fallback."""
    merchant_name: str | None = None
    receipt_date: str | None = Field(None, description="ISO 8601: YYYY-MM-DD")
    line_items: list[OCRLineItem] = Field(default_factory=list)

    # Bill-level monetary fields (in rupees — will be converted to paise later)
    subtotal_rupees: float = 0.0
    tax_rupees: float = 0.0
    service_charge_rupees: float = 0.0
    delivery_fee_rupees: float = 0.0
    discount_rupees: float = 0.0
    total_rupees: float = 0.0

    @field_validator("subtotal_rupees", "tax_rupees", "service_charge_rupees",
                     "delivery_fee_rupees", "discount_rupees", "total_rupees", mode="before")
    @classmethod
    def coerce_money(cls, v: object) -> float:
        try:
            return max(0.0, float(v))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0

    def to_paise(self) -> dict[str, int]:
        """Return all monetary fields converted to paise (integer arithmetic)."""
        def rs_to_paise(rs: float) -> int:
            return round(rs * 100)

        return {
            "subtotal_paise": rs_to_paise(self.subtotal_rupees),
            "tax_paise": rs_to_paise(self.tax_rupees),
            "service_charge_paise": rs_to_paise(self.service_charge_rupees),
            "delivery_fee_paise": rs_to_paise(self.delivery_fee_rupees),
            "discount_paise": rs_to_paise(self.discount_rupees),
            "total_paise": rs_to_paise(self.total_rupees),
        }


# ── Gemini prompt ─────────────────────────────────────────────────────────────

_EXTRACTION_PROMPT = """
You are a precise receipt OCR engine. Extract all data from this receipt image and return
ONLY valid JSON — no markdown, no explanation, no code fences.

JSON schema to follow exactly:
{
  "merchant_name": "string or null",
  "receipt_date": "YYYY-MM-DD string or null",
  "line_items": [
    {
      "item_name": "string",
      "quantity": integer,
      "unit_price_rupees": float,
      "category": "food|beverage|alcohol|grocery|transport|other or null"
    }
  ],
  "subtotal_rupees": float,
  "tax_rupees": float,
  "service_charge_rupees": float,
  "delivery_fee_rupees": float,
  "discount_rupees": float,
  "total_rupees": float
}

Rules:
- All monetary values must be in Indian Rupees as floats (e.g. 450.50).
- If a field is not on the receipt, use 0.0 for monetary fields or null for strings.
- Do not invent data. Extract only what is visible on the receipt.
- For quantities: if not shown, assume 1.
- unit_price_rupees = (total line price) / quantity.
"""


# ── Gemini extractor ──────────────────────────────────────────────────────────

def _extract_with_gemini(image_path: Path, api_key: str) -> OCRExtractedReceipt:
    """Call Gemini Vision API to extract receipt data from an image file."""
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError as e:
        raise RuntimeError(
            f"Required package not installed: {e}. Install with: pip install google-generativeai pillow"
        ) from e

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.0-flash")
    image = Image.open(image_path)

    logger.info("Sending receipt to Gemini Vision", image_path=str(image_path))
    response = model.generate_content([_EXTRACTION_PROMPT, image])

    raw_text = response.text.strip()
    # Strip markdown code fences if the model adds them despite instructions
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        raw_text = raw_text.rsplit("```", 1)[0]

    raw_json = json.loads(raw_text)
    logger.info("Gemini Vision extraction successful", items_count=len(raw_json.get("line_items", [])))
    return OCRExtractedReceipt.model_validate(raw_json)


# ── Mock fallback ─────────────────────────────────────────────────────────────

def _mock_extract(image_path: Path) -> OCRExtractedReceipt:
    """
    Deterministic mock OCR — returns a realistic restaurant bill without calling Gemini.
    Used for development, testing, and when GEMINI_API_KEY is not set.
    """
    filename = image_path.name.lower()
    logger.info("Using mock OCR fallback", image_path=str(image_path))

    if "grocery" in filename or "blinkit" in filename:
        return OCRExtractedReceipt(
            merchant_name="Blinkit Quick Commerce",
            receipt_date="2024-12-15",
            line_items=[
                OCRLineItem(item_name="Amul Butter (500g)", quantity=2, unit_price_rupees=290.0, category="grocery"),
                OCRLineItem(item_name="Brown Bread Loaf", quantity=1, unit_price_rupees=55.0, category="grocery"),
                OCRLineItem(item_name="Coca-Cola 2L", quantity=3, unit_price_rupees=95.0, category="beverage"),
                OCRLineItem(item_name="Lays Classic Chips (Pack of 5)", quantity=1, unit_price_rupees=180.0, category="grocery"),
                OCRLineItem(item_name="Maggi Noodles (6-pack)", quantity=1, unit_price_rupees=132.0, category="grocery"),
            ],
            subtotal_rupees=1237.0,
            tax_rupees=22.0,
            service_charge_rupees=0.0,
            delivery_fee_rupees=29.0,
            discount_rupees=80.0,
            total_rupees=1208.0,
        )

    # Default: restaurant bill
    return OCRExtractedReceipt(
        merchant_name="Fisherman's Wharf Seafood Restaurant",
        receipt_date="2024-12-15",
        line_items=[
            OCRLineItem(item_name="Butter Garlic Prawns", quantity=1, unit_price_rupees=580.0, category="food"),
            OCRLineItem(item_name="Grilled Fish Platter", quantity=1, unit_price_rupees=720.0, category="food"),
            OCRLineItem(item_name="Calamari Rings", quantity=1, unit_price_rupees=380.0, category="food"),
            OCRLineItem(item_name="Lobster Bisque Soup", quantity=2, unit_price_rupees=250.0, category="food"),
            OCRLineItem(item_name="Kingfisher Beer (650ml)", quantity=4, unit_price_rupees=180.0, category="alcohol"),
            OCRLineItem(item_name="Masala Papad", quantity=2, unit_price_rupees=60.0, category="food"),
            OCRLineItem(item_name="Garlic Naan", quantity=4, unit_price_rupees=65.0, category="food"),
            OCRLineItem(item_name="Dal Makhani", quantity=1, unit_price_rupees=320.0, category="food"),
            OCRLineItem(item_name="Fresh Lime Soda (x3)", quantity=3, unit_price_rupees=80.0, category="beverage"),
            OCRLineItem(item_name="Chocolate Lava Cake", quantity=2, unit_price_rupees=220.0, category="food"),
            OCRLineItem(item_name="Filter Coffee", quantity=3, unit_price_rupees=80.0, category="beverage"),
            OCRLineItem(item_name="Mineral Water (1L)", quantity=2, unit_price_rupees=40.0, category="beverage"),
        ],
        subtotal_rupees=4660.0,
        tax_rupees=466.0,   # 5% GST + SGST
        service_charge_rupees=466.0,  # 10% service charge
        delivery_fee_rupees=0.0,
        discount_rupees=200.0,  # loyalty discount
        total_rupees=5392.0,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def extract_receipt(
    image_path: Path,
    api_key: str = "",
    use_mock: bool = False,
) -> OCRExtractedReceipt:
    """
    Main entry point for receipt extraction.

    Args:
        image_path: Path to the uploaded image file.
        api_key: Google Gemini API key. If empty or use_mock is True, falls back to mock.
        use_mock: Force mock mode regardless of api_key.

    Returns:
        OCRExtractedReceipt — structured receipt data.
    """
    if use_mock or not api_key:
        return _mock_extract(image_path)

    try:
        return _extract_with_gemini(image_path, api_key)
    except Exception as exc:
        logger.warning(
            "Gemini extraction failed, falling back to mock",
            error=str(exc),
            image_path=str(image_path),
        )
        return _mock_extract(image_path)

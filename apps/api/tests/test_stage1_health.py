"""
Stage 1 Health Check Test — verifies app module imports correctly.
Full test suite begins in Stage 2.
"""
import pytest


def test_app_config_loads():
    """Ensure Pydantic Settings loads without errors."""
    from app.config import get_settings
    settings = get_settings()
    assert settings.app_name == "SplitSmart AI"
    assert settings.app_version == "1.0.0"
    assert settings.jwt_algorithm == "HS256"


def test_settings_mock_ocr_without_key():
    """With empty GEMINI_API_KEY, use_mock_ocr should be True."""
    from app.config import Settings
    settings = Settings(gemini_api_key="")
    assert settings.use_mock_ocr is True


def test_settings_real_ocr_with_key():
    """With a real GEMINI_API_KEY, use_mock_ocr should be False."""
    from app.config import Settings
    settings = Settings(gemini_api_key="AIzaSy-valid-key-here-xxx")
    assert settings.use_mock_ocr is False


def test_database_base_exists():
    """SQLAlchemy Base should be importable."""
    from app.database import Base
    assert Base is not None


def test_all_models_importable():
    """All 7 ORM models must import without errors."""
    from app.models import (
        User, Group, GroupMember, Receipt, ReceiptStatus,
        ReceiptLineItem, ItemClaim, LedgerEntry, EntryType
    )
    assert User.__tablename__ == "users"
    assert Group.__tablename__ == "groups"
    assert GroupMember.__tablename__ == "group_members"
    assert Receipt.__tablename__ == "receipts"
    assert ReceiptLineItem.__tablename__ == "receipt_line_items"
    assert ItemClaim.__tablename__ == "item_claims"
    assert LedgerEntry.__tablename__ == "ledger_entries"
    assert ReceiptStatus.QUEUED == "QUEUED"
    assert EntryType.EXPENSE_SHARE == "EXPENSE_SHARE"


def test_all_schemas_importable():
    """All Pydantic schemas must import without errors."""
    from app.schemas import (
        UserCreate, GuestUserCreate, UserResponse,
        GroupCreate, GroupResponse,
        ReceiptResponse, ReceiptUploadResponse,
    )
    assert UserCreate is not None
    assert GuestUserCreate is not None
    assert GroupCreate is not None


def test_fastapi_app_creates():
    """FastAPI app factory should create app without errors."""
    from app.main import create_app
    app = create_app()
    assert app.title == "SplitSmart AI"
    # Verify all expected routes exist
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/api/v1/health" in routes
    assert "/api/v1/sandbox/init" in routes
    assert "/api/v1/groups" in routes

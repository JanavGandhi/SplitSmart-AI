"""Routers for authentication, copilot, and public system metrics."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.group import Group
from app.models.ledger_entry import LedgerEntry
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User

# ── Auth ──────────────────────────────────────────────────────────────────────
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", status_code=501)
async def register():
    return {"detail": "Not implemented yet — coming in Stage 4"}


@auth_router.post("/login", status_code=501)
async def login():
    return {"detail": "Not implemented yet — coming in Stage 4"}


@auth_router.post("/guest", status_code=501)
async def create_guest():
    return {"detail": "Not implemented yet — coming in Stage 4"}


# ── Copilot ───────────────────────────────────────────────────────────────────
copilot_router = APIRouter(prefix="/copilot", tags=["copilot"])


@copilot_router.post("/chat", status_code=501)
async def chat():
    return {"detail": "Not implemented yet — coming in Stage 5"}


# ── Metrics ───────────────────────────────────────────────────────────────────
metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])


@metrics_router.get("")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Return live counts derived from persisted application data."""
    user_count = await db.scalar(select(func.count(User.id)))
    group_count = await db.scalar(select(func.count(Group.id)))
    receipt_count = await db.scalar(select(func.count(Receipt.id)))
    active_rooms = await db.scalar(
        select(func.count(Receipt.id)).where(
            Receipt.status == ReceiptStatus.READY_FOR_CLAIMS
        )
    )
    ledger_count = await db.scalar(select(func.count(LedgerEntry.id)))
    total_paise = await db.scalar(select(func.coalesce(func.sum(LedgerEntry.amount_paise), 0)))

    return {
        "status": "ok",
        "total_users": user_count or 0,
        "total_groups": group_count or 0,
        "total_receipts": receipt_count or 0,
        "active_rooms": active_rooms or 0,
        "ledger_entries": ledger_count or 0,
        "total_paise_tracked": total_paise or 0,
    }

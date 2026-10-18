"""Stub routers — will be fully implemented in subsequent stages."""
from fastapi import APIRouter

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


# ── Receipts ──────────────────────────────────────────────────────────────────
receipts_router = APIRouter(prefix="/receipts", tags=["receipts"])


@receipts_router.post("/upload", status_code=501)
async def upload_receipt():
    return {"detail": "Not implemented yet — coming in Stage 3"}


# ── Rooms ─────────────────────────────────────────────────────────────────────
rooms_router = APIRouter(prefix="/rooms", tags=["rooms"])


@rooms_router.post("/{room_code}/guest-join", status_code=501)
async def guest_join(room_code: str):
    return {"detail": "Not implemented yet — coming in Stage 4"}


# ── Copilot ───────────────────────────────────────────────────────────────────
copilot_router = APIRouter(prefix="/copilot", tags=["copilot"])


@copilot_router.post("/chat", status_code=501)
async def chat():
    return {"detail": "Not implemented yet — coming in Stage 5"}


# ── Metrics ───────────────────────────────────────────────────────────────────
metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])


@metrics_router.get("", status_code=501)
async def get_metrics():
    return {"detail": "Not implemented yet — coming in Stage 5"}

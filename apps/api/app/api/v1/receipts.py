"""
Receipts API — Upload endpoint and SSE progress stream.

Endpoints:
  POST /api/v1/receipts/upload
      Accepts a multipart image, saves it to disk, creates a DB receipt record,
      dispatches the Celery pipeline task, and returns 202 Accepted + SSE URL.

  GET /api/v1/receipts/{receipt_id}/events
      Server-Sent Events stream. Subscribes to the Redis Pub/Sub channel for
      this receipt and relays pipeline progress events to the browser in real time.

  GET /api/v1/receipts/{receipt_id}
      Return the current receipt status and line items (post-pipeline).

Pipeline stages (broadcast over SSE):
  UPLOADING → OCR_EXTRACTING → VALIDATING_MATH → READY_FOR_CLAIMS
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import shortuuid
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.config import get_settings, Settings
from app.database import get_db
from app.models.receipt import Receipt, ReceiptStatus
from app.models.receipt_line_item import ReceiptLineItem
from app.schemas.receipt import ReceiptResponse, ReceiptUploadResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/receipts", tags=["receipts"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_upload_dir(settings: Settings) -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _validate_image(file: UploadFile) -> None:
    """Raise 422 for non-image content types."""
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/heif"}
    content_type = file.content_type or ""
    if content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{content_type}'. Must be a JPEG, PNG, WebP, or HEIC image.",
        )


# ── POST /receipts/upload ──────────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=ReceiptUploadResponse)
async def upload_receipt(
    request: Request,
    file: UploadFile = File(..., description="Receipt image (JPEG, PNG, WebP, HEIC)"),
    group_id: str = Form(..., description="UUID of the group this receipt belongs to"),
    paid_by: str | None = Form(None, description="UUID of the member who paid the bill"),
    db: AsyncSession = Depends(get_db),
) -> ReceiptUploadResponse:
    """
    Upload a receipt image and kick off the async OCR pipeline.

    Returns immediately (202 Accepted) with:
    - receipt_id — the new DB record UUID
    - job_id     — Celery task ID for status tracking
    - sse_url    — URL to subscribe to for live progress events
    """
    settings = get_settings()
    _validate_image(file)

    # Validate group_id format
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="group_id must be a valid UUID",
        )

    paid_by_uuid: uuid.UUID | None = None
    if paid_by:
        try:
            paid_by_uuid = uuid.UUID(paid_by)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="paid_by must be a valid UUID",
            )

    # ── 1. Save file to disk ───────────────────────────────────────────────────
    upload_dir = _get_upload_dir(settings)
    suffix = Path(file.filename or "receipt.jpg").suffix or ".jpg"
    file_stem = f"{uuid.uuid4().hex}{suffix}"
    image_path = upload_dir / file_stem

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )

    image_path.write_bytes(content)
    logger.info("Receipt image saved", path=str(image_path), size_bytes=len(content))

    # ── 2. Create DB record ────────────────────────────────────────────────────
    room_code = shortuuid.ShortUUID().random(length=8).upper()
    idempotency_key = f"upload-{uuid.uuid4().hex}"

    receipt = Receipt(
        group_id=group_uuid,
        paid_by=paid_by_uuid,
        room_code=room_code,
        image_url=str(image_path),
        status=ReceiptStatus.QUEUED,
        idempotency_key=idempotency_key,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)

    logger.info("Receipt DB record created", receipt_id=str(receipt.id), room_code=room_code)

    # ── 3. Dispatch Celery task ────────────────────────────────────────────────
    try:
        from app.worker.tasks import process_receipt

        task = process_receipt.apply_async(
            kwargs={
                "receipt_id": str(receipt.id),
                "image_path": str(image_path),
                "group_id": str(group_uuid),
            }
        )
        job_id = task.id
        logger.info("Celery task dispatched", task_id=job_id, receipt_id=str(receipt.id))
    except Exception as exc:
        # Celery broker unavailable — still return the receipt, status stays QUEUED
        logger.warning("Celery broker unavailable, task not queued", error=str(exc))
        job_id = f"no-broker-{uuid.uuid4().hex[:8]}"

    # Build SSE URL
    base_url = str(request.base_url).rstrip("/")
    sse_url = f"{base_url}/api/v1/receipts/{receipt.id}/events"

    return ReceiptUploadResponse(
        receipt_id=receipt.id,
        room_code=room_code,
        job_id=job_id,
        status=receipt.status,
        sse_url=sse_url,
    )


# ── GET /receipts/{receipt_id}/events  (SSE stream) ───────────────────────────

@router.get("/{receipt_id}/events")
async def receipt_events(receipt_id: str, request: Request) -> StreamingResponse:
    """
    Server-Sent Events stream for real-time pipeline progress.

    Subscribes to the Redis Pub/Sub channel `receipt:{receipt_id}:events`
    and relays each message as an SSE event to the client.

    Automatically closes when:
    - A READY_FOR_CLAIMS or PIPELINE_FAILED event is received
    - The client disconnects
    - A 5-minute timeout is reached
    """
    try:
        uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid receipt_id")

    settings = get_settings()

    async def event_generator():
        import redis.asyncio as aioredis

        try:
            redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        except Exception as exc:
            # Redis unavailable — send a single error event and close
            yield f"event: error\ndata: {json.dumps({'error': 'Redis unavailable', 'detail': str(exc)})}\n\n"
            return

        pubsub = redis_client.pubsub()
        channel = f"receipt:{receipt_id}:events"

        try:
            await pubsub.subscribe(channel)
            logger.info("SSE client subscribed", channel=channel)

            # Send immediate acknowledgment so browser knows stream is live
            yield (
                f"event: SUBSCRIBED\n"
                f"data: {json.dumps({'receipt_id': receipt_id, 'channel': channel})}\n\n"
            )

            timeout_seconds = 300  # 5-minute max stream lifetime
            deadline = asyncio.get_event_loop().time() + timeout_seconds
            terminal_events = {"READY_FOR_CLAIMS", "PIPELINE_FAILED"}

            while True:
                # Respect client disconnects
                if await request.is_disconnected():
                    logger.info("SSE client disconnected", channel=channel)
                    break

                # Check timeout
                if asyncio.get_event_loop().time() > deadline:
                    yield f"event: TIMEOUT\ndata: {json.dumps({'message': 'Stream timeout'})}\n\n"
                    break

                # Poll for next message (non-blocking with 1s poll)
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                if message and message.get("type") == "message":
                    data_str = message["data"]
                    try:
                        payload = json.loads(data_str)
                        event_type = payload.get("event", "UPDATE")

                        yield f"event: {event_type}\ndata: {data_str}\n\n"
                        logger.debug("SSE event relayed", event=event_type, receipt_id=receipt_id)

                        # Close stream after terminal events
                        if event_type in terminal_events:
                            yield f"event: STREAM_END\ndata: {json.dumps({'reason': event_type})}\n\n"
                            break

                    except json.JSONDecodeError:
                        continue

                # Keep-alive comment every second to prevent proxy timeouts
                yield ": keep-alive\n\n"
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("SSE stream cancelled", channel=channel)
        finally:
            await pubsub.unsubscribe(channel)
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Connection": "keep-alive",
        },
    )


# ── GET /receipts/{receipt_id} ─────────────────────────────────────────────────

@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReceiptResponse:
    """Return the current state of a receipt including all line items and claims."""
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid receipt_id")

    result = await db.execute(
        select(Receipt)
        .options(
            selectinload(Receipt.line_items).selectinload(ReceiptLineItem.claims)
        )
        .where(Receipt.id == receipt_uuid)
    )
    receipt = result.scalar_one_or_none()

    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return ReceiptResponse.model_validate(receipt)


# ── GET /receipts/room/{room_code} ─────────────────────────────────────────────

@router.get("/room/{room_code}", response_model=ReceiptResponse)
async def get_receipt_by_room_code(
    room_code: str,
    db: AsyncSession = Depends(get_db),
) -> ReceiptResponse:
    """Fetch a receipt by its 8-character room code (used by the claim room UI)."""
    result = await db.execute(
        select(Receipt)
        .options(
            selectinload(Receipt.line_items).selectinload(ReceiptLineItem.claims)
        )
        .where(Receipt.room_code == room_code.upper())
    )
    receipt = result.scalar_one_or_none()

    if receipt is None:
        raise HTTPException(status_code=404, detail=f"No receipt found for room code '{room_code}'")

    return ReceiptResponse.model_validate(receipt)

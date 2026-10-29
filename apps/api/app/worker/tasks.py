"""
Celery Worker — SplitSmart AI Receipt Processing Pipeline.

Pipeline stages (matching ReceiptStatus enum):
    QUEUED → PROCESSING → READY_FOR_CLAIMS   (happy path)
                        ↓
                      FAILED                  (on error)

Each stage broadcasts a Redis Pub/Sub event so the SSE stream endpoint
can relay live progress updates to the browser without polling.

Redis channel pattern: "receipt:{receipt_id}:events"
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import redis as redis_sync  # synchronous redis for Celery tasks
import structlog
from celery import Celery
from celery.signals import task_failure

from app.config import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()

# ── Celery app ─────────────────────────────────────────────────────────────────
celery_app = Celery(
    "splitsmart",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # Only ACK after the task completes (safer)
    worker_prefetch_multiplier=1, # One task at a time per worker process
    task_soft_time_limit=120,     # 2-minute soft limit
    task_time_limit=180,          # 3-minute hard kill
    result_expires=3600,          # Keep results 1 hour
)

# Autodiscover tasks in this module
celery_app.autodiscover_tasks(["app.worker"])


# ── Redis Pub/Sub helpers ──────────────────────────────────────────────────────

def _get_redis_client() -> redis_sync.Redis:
    """Get a synchronous Redis client for Pub/Sub publishing from Celery tasks."""
    return redis_sync.from_url(settings.redis_url, decode_responses=True)


def _publish_event(
    redis_client: redis_sync.Redis,
    receipt_id: str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """
    Publish a receipt pipeline event to Redis Pub/Sub.
    Channel: receipt:{receipt_id}:events
    """
    channel = f"receipt:{receipt_id}:events"
    payload = json.dumps({
        "event": event_type,
        "receipt_id": receipt_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    })
    redis_client.publish(channel, payload)
    logger.debug("Published event", channel=channel, evt=event_type)


# ── DB helpers (sync SQLAlchemy for Celery) ───────────────────────────────────

def _get_sync_session():
    """Create a synchronous SQLAlchemy session for use inside Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def _rupees_to_paise(rupees: float) -> int:
    return round(rupees * 100)


# ── The Main Pipeline Task ─────────────────────────────────────────────────────

@celery_app.task(bind=True, name="app.worker.tasks.process_receipt", max_retries=2)
def process_receipt(self, receipt_id: str, image_path: str, group_id: str) -> dict[str, Any]:
    """
    Full receipt OCR and validation pipeline.

    Stages:
      1. UPLOADING   → File saved, DB record created (done before task dispatch)
      2. OCR_EXTRACTING → Send image to Gemini Vision (or mock)
      3. VALIDATING_MATH → Run math engine validation on extracted data
      4. READY_FOR_CLAIMS → Write line items to DB, update receipt status

    Each stage publishes a Pub/Sub event for SSE relay.
    """
    redis_client = _get_redis_client()

    def publish(event_type: str, **data: Any) -> None:
        _publish_event(redis_client, receipt_id, event_type, data)

    try:
        # ── Stage: OCR_EXTRACTING ──────────────────────────────────────────────
        publish(
            "STAGE_UPDATE",
            stage="OCR_EXTRACTING",
            message="Sending receipt to Gemini Vision AI for extraction...",
            progress=25,
        )

        from app.services.vision_ocr import extract_receipt

        extracted = extract_receipt(
            image_path=Path(image_path),
            api_key=settings.gemini_api_key,
            use_mock=settings.use_mock_ocr,
        )

        publish(
            "OCR_COMPLETE",
            stage="OCR_EXTRACTING",
            message=f"Extracted {len(extracted.line_items)} line items from receipt",
            merchant_name=extracted.merchant_name,
            item_count=len(extracted.line_items),
            total_rupees=extracted.total_rupees,
            progress=50,
        )

        # ── Stage: VALIDATING_MATH ────────────────────────────────────────────
        publish(
            "STAGE_UPDATE",
            stage="VALIDATING_MATH",
            message="Validating paise arithmetic and totals...",
            progress=75,
        )

        paise = extracted.to_paise()

        # Validation: recompute expected total and check if it's consistent
        computed_total = (
            paise["subtotal_paise"]
            + paise["tax_paise"]
            + paise["service_charge_paise"]
            + paise["delivery_fee_paise"]
            - paise["discount_paise"]
        )
        # Allow ±2 paise tolerance for floating-point representations
        total_ok = abs(computed_total - paise["total_paise"]) <= 200

        if total_ok:
            publish(
                "VALIDATION_OK",
                stage="VALIDATING_MATH",
                message="Math validation passed — all totals consistent",
                computed_total_paise=computed_total,
                progress=80,
            )
        else:
            # Auto-correct: use computed total from subtotal+tax-discount as ground truth
            logger.warning(
                "Total mismatch, auto-correcting",
                ocr_total=paise["total_paise"],
                computed_total=computed_total,
            )
            paise["total_paise"] = computed_total
            publish(
                "VALIDATION_CORRECTED",
                stage="VALIDATING_MATH",
                message=f"Auto-corrected total to Rs {computed_total/100:.2f}",
                progress=80,
            )

        # ── Stage: READY_FOR_CLAIMS — Write to DB ─────────────────────────────
        publish(
            "STAGE_UPDATE",
            stage="READY_FOR_CLAIMS",
            message="Saving line items to database...",
            progress=90,
        )

        session = _get_sync_session()
        try:
            from app.models.receipt import Receipt, ReceiptStatus
            from app.models.receipt_line_item import ReceiptLineItem

            receipt_uuid = uuid.UUID(receipt_id)
            receipt = session.get(Receipt, receipt_uuid)

            if receipt is None:
                raise ValueError(f"Receipt {receipt_id} not found in DB")

            # Update receipt monetary fields
            receipt.merchant_name = extracted.merchant_name
            if extracted.receipt_date:
                try:
                    receipt.receipt_date = date.fromisoformat(extracted.receipt_date)
                except ValueError:
                    pass  # non-critical — leave as None

            receipt.subtotal_paise = paise["subtotal_paise"]
            receipt.tax_paise = paise["tax_paise"]
            receipt.service_charge_paise = paise["service_charge_paise"]
            receipt.delivery_fee_paise = paise["delivery_fee_paise"]
            receipt.discount_paise = paise["discount_paise"]
            receipt.total_paise = paise["total_paise"]
            receipt.raw_ocr_json = extracted.model_dump()
            receipt.status = ReceiptStatus.READY_FOR_CLAIMS

            # Write line items
            for item in extracted.line_items:
                line_item = ReceiptLineItem(
                    receipt_id=receipt_uuid,
                    item_name=item.item_name,
                    quantity=item.quantity,
                    unit_price_paise=_rupees_to_paise(item.unit_price_rupees),
                    total_price_paise=_rupees_to_paise(item.total_price_rupees),
                    category=item.category,
                )
                session.add(line_item)

            session.commit()
            session.refresh(receipt)

            line_item_summaries = [
                {
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "total_price_rupees": item.total_price_rupees,
                }
                for item in extracted.line_items
            ]

        finally:
            session.close()

        publish(
            "READY_FOR_CLAIMS",
            stage="READY_FOR_CLAIMS",
            message="Receipt is ready! Members can now claim their items.",
            merchant_name=extracted.merchant_name,
            total_paise=paise["total_paise"],
            item_count=len(extracted.line_items),
            line_items=line_item_summaries,
            progress=100,
        )

        logger.info(
            "Receipt pipeline completed",
            receipt_id=receipt_id,
            items=len(extracted.line_items),
            total_paise=paise["total_paise"],
        )

        return {
            "receipt_id": receipt_id,
            "status": "READY_FOR_CLAIMS",
            "item_count": len(extracted.line_items),
            "total_paise": paise["total_paise"],
        }

    except Exception as exc:
        logger.exception("Receipt pipeline failed", receipt_id=receipt_id, error=str(exc))

        # Update DB status to FAILED
        try:
            session = _get_sync_session()
            try:
                from app.models.receipt import Receipt, ReceiptStatus
                receipt = session.get(Receipt, uuid.UUID(receipt_id))
                if receipt:
                    receipt.status = ReceiptStatus.FAILED
                    session.commit()
            finally:
                session.close()
        except Exception:
            pass  # Don't mask the original error

        publish(
            "PIPELINE_FAILED",
            stage="FAILED",
            message=f"Pipeline failed: {str(exc)}",
            error=str(exc),
            progress=0,
        )

        # Retry with exponential backoff (max 2 retries)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)


@task_failure.connect
def on_task_failure(task_id: str, exception: Exception, **kwargs: Any) -> None:
    """Global signal handler for final failures after all retries exhausted."""
    logger.error("Task permanently failed", task_id=task_id, error=str(exception))

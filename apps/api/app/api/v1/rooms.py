"""Guest authentication, real-time receipt claims, and room finalization."""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import JWTError, jwt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.group_member import GroupMember
from app.models.item_claim import ItemClaim
from app.models.ledger_entry import EntryType, LedgerEntry
from app.models.receipt import Receipt, ReceiptStatus
from app.models.receipt_line_item import ReceiptLineItem
from app.models.user import User
from app.schemas.user import UserPublic
from app.services.math_engine import (
    ClaimInput,
    LineItemInput,
    ReceiptInput,
    SplitResult,
    _split_item_among_claimants,
    compute_split,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/rooms", tags=["rooms"])

_AVATAR_COLORS = ("#6366f1", "#ec4899", "#10b981", "#f59e0b", "#3b82f6", "#8b5cf6")


class GuestJoinRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be blank")
        return value


class GuestJoinResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class FinalizeRequest(BaseModel):
    payer_user_id: uuid.UUID
    idempotency_key: str = Field(..., min_length=1, max_length=64)


def _room_token(user: User, room_code: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.guest_token_expire_minutes * 60
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "room_code": room_code,
            "scope": "room:join",
            "display_name": user.display_name,
            "avatar_color": user.avatar_color,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def _decode_room_token(token: str, room_code: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired room token") from exc

    if claims.get("scope") != "room:join" or claims.get("room_code") != room_code:
        raise ValueError("Token is not authorized for this room")
    try:
        uuid.UUID(claims["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Room token has an invalid subject") from exc
    return claims


def calculate_room_split(
    receipt: Receipt,
    line_items: list[ReceiptLineItem],
    claims: list[ItemClaim],
) -> SplitResult:
    """Recalculate all claims and persist each claimant's paise allocation."""
    claims_by_item: dict[uuid.UUID, list[ItemClaim]] = {}
    for claim in claims:
        if claim.share_fraction_numerator <= 0 or claim.share_fraction_denominator <= 0:
            raise ValueError("Claim fractions must be positive")
        claims_by_item.setdefault(claim.line_item_id, []).append(claim)

    claimed_items = [item for item in line_items if claims_by_item.get(item.id)]
    claimed_subtotal = sum(item.total_price_paise for item in claimed_items)
    if not claimed_items:
        for claim in claims:
            claim.calculated_item_paise = 0
            claim.calculated_tax_and_fees_paise = 0
            claim.calculated_final_paise = 0
        return SplitResult(invariant_holds=(receipt.total_paise == 0))

    all_items_claimed = len(claimed_items) == len(line_items)
    extras = (
        receipt.tax_paise
        + receipt.service_charge_paise
        + receipt.delivery_fee_paise
        - receipt.discount_paise
    )
    if not all_items_claimed and receipt.subtotal_paise > 0:
        extras = extras * claimed_subtotal // receipt.subtotal_paise

    # During partial claiming, fees are prorated to the claimed subtotal instead
    # of charging guests for items nobody has claimed yet.
    receipt_input = ReceiptInput(
        subtotal_paise=claimed_subtotal,
        tax_paise=extras,
        total_paise=claimed_subtotal + extras,
        line_items=[
            LineItemInput(
                id=item.id,
                total_price_paise=item.total_price_paise,
                claims=[
                    ClaimInput(
                        line_item_id=claim.line_item_id,
                        user_id=claim.user_id,
                        share_numerator=claim.share_fraction_numerator,
                        share_denominator=claim.share_fraction_denominator,
                    )
                    for claim in claims_by_item[item.id]
                ],
            )
            for item in claimed_items
        ],
    )
    result = compute_split(receipt_input)

    for claim in claims:
        claim.calculated_item_paise = 0
        claim.calculated_tax_and_fees_paise = 0
        claim.calculated_final_paise = 0

    first_claim_by_user: dict[uuid.UUID, ItemClaim] = {}
    for item in claimed_items:
        item_claims = claims_by_item[item.id]
        item_allocations = _split_item_among_claimants(
            item.total_price_paise,
            [
                ClaimInput(
                    line_item_id=claim.line_item_id,
                    user_id=claim.user_id,
                    share_numerator=claim.share_fraction_numerator,
                    share_denominator=claim.share_fraction_denominator,
                )
                for claim in item_claims
            ],
        )
        for claim in item_claims:
            amount = item_allocations.get(claim.user_id, 0)
            claim.calculated_item_paise = amount
            claim.calculated_final_paise = amount
            first_claim_by_user.setdefault(claim.user_id, claim)

    for user_id, split in result.user_splits.items():
        claim = first_claim_by_user[user_id]
        claim.calculated_tax_and_fees_paise = split.tax_and_fees_paise
        claim.calculated_final_paise += split.tax_and_fees_paise

    return result


async def _load_split_data(
    db: AsyncSession,
    receipt: Receipt,
) -> tuple[list[ReceiptLineItem], list[ItemClaim]]:
    items_result = await db.execute(
        select(ReceiptLineItem).where(ReceiptLineItem.receipt_id == receipt.id)
    )
    claims_result = await db.execute(
        select(ItemClaim)
        .join(ReceiptLineItem, ItemClaim.line_item_id == ReceiptLineItem.id)
        .where(ReceiptLineItem.receipt_id == receipt.id)
    )
    return list(items_result.scalars().all()), list(claims_result.scalars().all())


def _claim_totals(result: SplitResult) -> dict[str, int]:
    return {
        str(user_id): split.final_paise
        for user_id, split in sorted(result.user_splits.items(), key=lambda item: str(item[0]))
    }


@router.post(
    "/{room_code}/guest-join",
    response_model=GuestJoinResponse,
    status_code=status.HTTP_201_CREATED,
)
async def guest_join(
    room_code: str,
    payload: GuestJoinRequest,
    db: AsyncSession = Depends(get_db),
) -> GuestJoinResponse:
    normalized_code = room_code.upper()
    result = await db.execute(
        select(Receipt)
        .where(Receipt.room_code == normalized_code)
        .with_for_update()
    )
    receipt = result.scalar_one_or_none()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if receipt.status in {ReceiptStatus.LOCKED, ReceiptStatus.SETTLED, ReceiptStatus.FAILED}:
        raise HTTPException(status_code=409, detail="This room is no longer accepting guests")

    user = User(
        id=uuid.uuid4(),
        display_name=payload.display_name,
        avatar_color=_AVATAR_COLORS[uuid.uuid4().int % len(_AVATAR_COLORS)],
        is_guest=True,
    )
    db.add(user)
    db.add(GroupMember(group_id=receipt.group_id, user_id=user.id))
    await db.flush()

    token, expires_in = _room_token(user, normalized_code)
    return GuestJoinResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserPublic(
            id=user.id,
            display_name=user.display_name,
            avatar_color=user.avatar_color,
            is_guest=user.is_guest,
        ),
    )


async def _toggle_claim(
    db: AsyncSession,
    room_code: str,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[str, SplitResult]:
    receipt_result = await db.execute(
        select(Receipt)
        .where(Receipt.room_code == room_code)
        .with_for_update()
    )
    receipt = receipt_result.scalar_one_or_none()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if receipt.status != ReceiptStatus.READY_FOR_CLAIMS:
        raise HTTPException(status_code=409, detail="Receipt is not open for claims")

    item_result = await db.execute(
        select(ReceiptLineItem).where(
            ReceiptLineItem.id == item_id,
            ReceiptLineItem.receipt_id == receipt.id,
        )
    )
    item = item_result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found in this room")

    claim_result = await db.execute(
        select(ItemClaim).where(
            ItemClaim.line_item_id == item_id,
            ItemClaim.user_id == user_id,
        )
    )
    existing = claim_result.scalar_one_or_none()
    if existing is None:
        db.add(
            ItemClaim(
                line_item_id=item_id,
                user_id=user_id,
                share_fraction_numerator=1,
                share_fraction_denominator=1,
            )
        )
        action = "claimed"
    else:
        await db.delete(existing)
        action = "unclaimed"

    await db.flush()
    line_items, claims = await _load_split_data(db, receipt)
    split = calculate_room_split(receipt, line_items, claims)
    await db.commit()
    return action, split


async def _simulate_friends(
    db: AsyncSession,
    redis_client: Any,
    room_code: str,
    group_id: uuid.UUID,
) -> None:
    for index, (name, color) in enumerate(
        zip(("Roommate 1", "Roommate 2", "Roommate 3"), _AVATAR_COLORS[1:4], strict=True),
        start=1,
    ):
        await asyncio.sleep(2)
        user = User(
            id=uuid.uuid4(),
            display_name=name,
            avatar_color=color,
            is_guest=True,
        )
        db.add(user)
        db.add(GroupMember(group_id=group_id, user_id=user.id))
        await db.flush()
        await db.commit()
        await redis_client.publish(
            f"room:{room_code}:events",
            json.dumps(
                {
                    "event": "PARTICIPANT_JOINED",
                    "user_id": str(user.id),
                    "display_name": user.display_name,
                    "avatar_color": user.avatar_color,
                    "simulated": True,
                    "sequence": index,
                }
            ),
        )


@router.websocket("/{room_code}/ws")
async def room_websocket(
    websocket: WebSocket,
    room_code: str,
    token: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    normalized_code = room_code.upper()
    try:
        token_claims = _decode_room_token(token, normalized_code)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid room token")
        return

    receipt_result = await db.execute(
        select(Receipt).where(Receipt.room_code == normalized_code)
    )
    receipt = receipt_result.scalar_one_or_none()
    user_id = uuid.UUID(token_claims["sub"])
    if receipt is None:
        await websocket.close(code=1008, reason="Room not found")
        return

    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == receipt.group_id,
            GroupMember.user_id == user_id,
        )
    )
    if member_result.scalar_one_or_none() is None:
        await websocket.close(code=1008, reason="Guest is not a room member")
        return

    settings = get_settings()
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        channel = f"room:{normalized_code}:events"
        await pubsub.subscribe(channel)
    except Exception as exc:
        logger.error("Room WebSocket Redis connection failed", error=str(exc))
        await websocket.close(code=1013, reason="Room event service unavailable")
        return

    await websocket.accept()

    async def forward_events() -> None:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message.get("type") == "message":
                await websocket.send_json(json.loads(message["data"]))

    forward_task = asyncio.create_task(forward_events())
    try:
        await redis_client.publish(
            channel,
            json.dumps(
                {
                    "event": "PARTICIPANT_JOINED",
                    "user_id": str(user_id),
                    "display_name": token_claims.get("display_name", "Guest"),
                    "avatar_color": token_claims.get("avatar_color", _AVATAR_COLORS[0]),
                }
            ),
        )
        while True:
            message = await websocket.receive_json()
            event = message.get("event")
            if event == "ITEM_CLAIM_TOGGLED":
                try:
                    item_id = uuid.UUID(message.get("item_id", ""))
                except (ValueError, TypeError, AttributeError):
                    await websocket.send_json(
                        {"event": "ERROR", "detail": "item_id must be a valid UUID"}
                    )
                    continue
                action, split = await _toggle_claim(
                    db,
                    normalized_code,
                    item_id,
                    user_id,
                )
                await redis_client.publish(
                    channel,
                    json.dumps(
                        {
                            "event": "ITEM_CLAIM_TOGGLED",
                            "item_id": str(item_id),
                            "user_id": str(user_id),
                            "action": action,
                            "fraction": {"numerator": 1, "denominator": 1},
                        }
                    ),
                )
                await redis_client.publish(
                    channel,
                    json.dumps(
                        {
                            "event": "TAX_RECALCULATED",
                            "per_user_totals": _claim_totals(split),
                            "invariant_holds": split.invariant_holds,
                        }
                    ),
                )
            elif event == "SIMULATE_FRIENDS":
                await _simulate_friends(
                    db,
                    redis_client,
                    normalized_code,
                    receipt.group_id,
                )
            else:
                await websocket.send_json(
                    {"event": "ERROR", "detail": "Unsupported room event"}
                )
    except WebSocketDisconnect:
        logger.info("Room WebSocket disconnected", room_code=normalized_code, user_id=str(user_id))
    except HTTPException as exc:
        await websocket.send_json(
            {"event": "ERROR", "status_code": exc.status_code, "detail": exc.detail}
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error(
            "Room WebSocket failed",
            room_code=normalized_code,
            user_id=str(user_id),
            error=str(exc),
        )
        await websocket.close(code=1011, reason="Room operation failed")
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
        await pubsub.unsubscribe(channel)
        await redis_client.aclose()


def _ledger_idempotency_key(
    request_key: str,
    receipt_id: uuid.UUID,
    debtor_id: uuid.UUID,
) -> str:
    return hashlib.sha256(
        f"{request_key}:{receipt_id}:{debtor_id}".encode()
    ).hexdigest()


def _finalize_response(
    receipt: Receipt,
    split: SplitResult,
    payer_user_id: uuid.UUID,
    *,
    created: bool,
) -> dict[str, Any]:
    return {
        "receipt_id": str(receipt.id),
        "status": receipt.status.value,
        "created": created,
        "payer_user_id": str(payer_user_id),
        "final_splits": _claim_totals(split),
        "settlements": [
            {
                "from_user_id": str(user_id),
                "to_user_id": str(payer_user_id),
                "amount_paise": user_split.final_paise,
            }
            for user_id, user_split in sorted(
                split.user_splits.items(),
                key=lambda item: str(item[0]),
            )
            if user_id != payer_user_id and user_split.final_paise > 0
        ],
    }


@router.post("/{room_code}/finalize")
async def finalize_room(
    room_code: str,
    payload: FinalizeRequest,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    normalized_code = room_code.upper()
    receipt_result = await db.execute(
        select(Receipt)
        .where(Receipt.room_code == normalized_code)
        .with_for_update()
    )
    receipt = receipt_result.scalar_one_or_none()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Room not found")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Room guest token is required")
    try:
        token_claims = _decode_room_token(authorization[7:].strip(), normalized_code)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    member_result = await db.execute(
        select(GroupMember.user_id).where(GroupMember.group_id == receipt.group_id)
    )
    member_ids = set(member_result.scalars().all())
    actor_id = uuid.UUID(token_claims["sub"])
    if actor_id not in member_ids:
        raise HTTPException(status_code=403, detail="Guest is not a member of this group")

    items, claims = await _load_split_data(db, receipt)
    if receipt.status == ReceiptStatus.LOCKED:
        if receipt.finalize_idempotency_key != payload.idempotency_key:
            raise HTTPException(status_code=409, detail="Receipt has already been finalized")
        if receipt.paid_by != payload.payer_user_id:
            raise HTTPException(status_code=409, detail="Idempotency key was used with a different payer")
        split = calculate_room_split(receipt, items, claims)
        return _finalize_response(receipt, split, payload.payer_user_id, created=False)
    if receipt.status != ReceiptStatus.READY_FOR_CLAIMS:
        raise HTTPException(status_code=409, detail="Receipt is not ready to be finalized")
    if not items:
        raise HTTPException(status_code=409, detail="Receipt has no line items")

    claimed_item_ids = {claim.line_item_id for claim in claims}
    if any(item.id not in claimed_item_ids for item in items):
        raise HTTPException(status_code=409, detail="Every line item must be claimed before finalizing")
    if sum(item.total_price_paise for item in items) != receipt.subtotal_paise:
        raise HTTPException(status_code=422, detail="Receipt subtotal does not match its line items")

    if payload.payer_user_id not in member_ids:
        raise HTTPException(status_code=422, detail="Payer must be a member of this group")
    if any(claim.user_id not in member_ids for claim in claims):
        raise HTTPException(status_code=422, detail="All claimants must be members of this group")

    split = calculate_room_split(receipt, items, claims)
    expected_total = (
        receipt.subtotal_paise
        + receipt.tax_paise
        + receipt.service_charge_paise
        + receipt.delivery_fee_paise
        - receipt.discount_paise
    )
    if expected_total != receipt.total_paise:
        raise HTTPException(
            status_code=422,
            detail="Receipt total does not match its subtotal, fees, and discount",
        )
    if not split.invariant_holds:
        raise HTTPException(status_code=422, detail="Claim totals do not match the receipt total")

    for user_id, user_split in split.user_splits.items():
        if user_id == payload.payer_user_id or user_split.final_paise <= 0:
            continue
        db.add(
            LedgerEntry(
                id=uuid.uuid4(),
                group_id=receipt.group_id,
                receipt_id=receipt.id,
                from_user_id=user_id,
                to_user_id=payload.payer_user_id,
                amount_paise=user_split.final_paise,
                entry_type=EntryType.EXPENSE_SHARE,
                idempotency_key=_ledger_idempotency_key(
                    payload.idempotency_key,
                    receipt.id,
                    user_id,
                ),
            )
        )

    receipt.paid_by = payload.payer_user_id
    receipt.finalize_idempotency_key = payload.idempotency_key
    receipt.status = ReceiptStatus.LOCKED
    await db.flush()
    await db.commit()

    redis_client = None
    try:
        redis_client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        await redis_client.publish(
            f"room:{normalized_code}:events",
            json.dumps(
                {
                    "event": "RECEIPT_LOCKED",
                    "receipt_id": str(receipt.id),
                    "final_splits": _claim_totals(split),
                }
            ),
        )
    except Exception as exc:
        logger.warning(
            "Receipt finalized but lock event could not be published",
            receipt_id=str(receipt.id),
            error=str(exc),
        )
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception as exc:
                logger.warning(
                    "Receipt finalized but Redis connection cleanup failed",
                    receipt_id=str(receipt.id),
                    error=str(exc),
                )

    return _finalize_response(receipt, split, payload.payer_user_id, created=True)

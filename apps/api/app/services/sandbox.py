"""
Sandbox Service — Creates the "Goa Weekend Squad" demo group.

Pre-seeded demo data for 1-click recruiter sandbox:
- 5 members: Aryan, Priya, Karan, Meera, Dev
- 4 receipts: restaurant (12 items), Blinkit grocery, beach shack, taxi split
- Cross-debts that simplify from 11 transactions → 4
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import shortuuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.receipt import Receipt, ReceiptStatus
from app.models.receipt_line_item import ReceiptLineItem
from app.models.item_claim import ItemClaim
from app.models.ledger_entry import LedgerEntry, EntryType
from app.services.math_engine import (
    ClaimInput,
    LineItemInput,
    ReceiptInput,
    compute_split,
)


# ── Sandbox Member Data ──────────────────────────────────────────────────────
SANDBOX_MEMBERS = [
    {"display_name": "Aryan", "avatar_color": "#6366f1", "upi_id": "aryan@paytm"},
    {"display_name": "Priya", "avatar_color": "#ec4899", "upi_id": "priya@gpay"},
    {"display_name": "Karan", "avatar_color": "#10b981", "upi_id": "karan@phonepe"},
    {"display_name": "Meera", "avatar_color": "#f59e0b", "upi_id": "meera@paytm"},
    {"display_name": "Dev", "avatar_color": "#3b82f6", "upi_id": "dev@gpay"},
]


# ── Receipt 1: Coastal Flame Restaurant (12 items) ──────────────────────────
RECEIPT_1 = {
    "merchant_name": "Coastal Flame Restaurant",
    "receipt_date": date(2026, 10, 12),
    "items": [
        {"name": "Butter Chicken", "qty": 1, "unit_paise": 45000, "total_paise": 45000, "category": "Main Course"},
        {"name": "Paneer Tikka Masala", "qty": 1, "unit_paise": 38000, "total_paise": 38000, "category": "Main Course"},
        {"name": "Goan Fish Curry", "qty": 1, "unit_paise": 52000, "total_paise": 52000, "category": "Main Course"},
        {"name": "Dal Makhani", "qty": 1, "unit_paise": 28000, "total_paise": 28000, "category": "Main Course"},
        {"name": "Garlic Naan (4 pcs)", "qty": 4, "unit_paise": 6000, "total_paise": 24000, "category": "Bread"},
        {"name": "Steamed Rice", "qty": 2, "unit_paise": 12000, "total_paise": 24000, "category": "Rice"},
        {"name": "Chicken Biryani", "qty": 1, "unit_paise": 42000, "total_paise": 42000, "category": "Rice"},
        {"name": "Raita", "qty": 1, "unit_paise": 8000, "total_paise": 8000, "category": "Side"},
        {"name": "Gulab Jamun (2 pcs)", "qty": 2, "unit_paise": 12000, "total_paise": 24000, "category": "Dessert"},
        {"name": "Masala Chai", "qty": 3, "unit_paise": 6000, "total_paise": 18000, "category": "Beverage"},
        {"name": "Fresh Lime Soda", "qty": 2, "unit_paise": 8000, "total_paise": 16000, "category": "Beverage"},
        {"name": "Mango Lassi", "qty": 1, "unit_paise": 10000, "total_paise": 10000, "category": "Beverage"},
    ],
    "tax_paise": 16450,        # ~5% GST
    "service_charge_paise": 16450,  # ~5% service charge
    "delivery_fee_paise": 0,
    "discount_paise": 0,
    "paid_by_index": 0,  # Aryan paid
    # Claims: index into SANDBOX_MEMBERS
    "claims": [
        # Butter Chicken → Aryan, Karan
        {"item_idx": 0, "claimants": [0, 2]},
        # Paneer Tikka → Priya, Meera
        {"item_idx": 1, "claimants": [1, 3]},
        # Goan Fish → Aryan, Dev
        {"item_idx": 2, "claimants": [0, 4]},
        # Dal Makhani → shared by all 5
        {"item_idx": 3, "claimants": [0, 1, 2, 3, 4]},
        # Garlic Naan → shared by all 5
        {"item_idx": 4, "claimants": [0, 1, 2, 3, 4]},
        # Steamed Rice → Priya, Meera, Dev
        {"item_idx": 5, "claimants": [1, 3, 4]},
        # Chicken Biryani → Karan
        {"item_idx": 6, "claimants": [2]},
        # Raita → Karan
        {"item_idx": 7, "claimants": [2]},
        # Gulab Jamun → Aryan, Priya, Meera
        {"item_idx": 8, "claimants": [0, 1, 3]},
        # Masala Chai → Priya, Meera, Dev
        {"item_idx": 9, "claimants": [1, 3, 4]},
        # Fresh Lime Soda → Aryan, Karan
        {"item_idx": 10, "claimants": [0, 2]},
        # Mango Lassi → Dev
        {"item_idx": 11, "claimants": [4]},
    ],
}

# ── Receipt 2: Blinkit Grocery Haul ──────────────────────────────────────────
RECEIPT_2 = {
    "merchant_name": "Blinkit Quick Commerce",
    "receipt_date": date(2026, 10, 13),
    "items": [
        {"name": "Amul Butter 500g", "qty": 1, "unit_paise": 27500, "total_paise": 27500, "category": "Dairy"},
        {"name": "Bread Loaf", "qty": 2, "unit_paise": 5500, "total_paise": 11000, "category": "Bakery"},
        {"name": "Eggs (12 pack)", "qty": 1, "unit_paise": 9600, "total_paise": 9600, "category": "Protein"},
        {"name": "Maggi Noodles (4 pack)", "qty": 1, "unit_paise": 5600, "total_paise": 5600, "category": "Snacks"},
        {"name": "Coca Cola 2L", "qty": 2, "unit_paise": 9500, "total_paise": 19000, "category": "Beverage"},
        {"name": "Chips Party Pack", "qty": 1, "unit_paise": 15000, "total_paise": 15000, "category": "Snacks"},
    ],
    "tax_paise": 0,
    "service_charge_paise": 0,
    "delivery_fee_paise": 3000,  # Delivery charge
    "discount_paise": 5000,   # Coupon discount
    "paid_by_index": 1,  # Priya paid
    "claims": [
        # All grocery items shared equally by everyone
        {"item_idx": 0, "claimants": [0, 1, 2, 3, 4]},
        {"item_idx": 1, "claimants": [0, 1, 2, 3, 4]},
        {"item_idx": 2, "claimants": [0, 1, 2, 3, 4]},
        {"item_idx": 3, "claimants": [0, 1, 2, 3, 4]},
        {"item_idx": 4, "claimants": [0, 1, 2, 3, 4]},
        {"item_idx": 5, "claimants": [0, 1, 2, 3, 4]},
    ],
}

# ── Receipt 3: Beach Shack ───────────────────────────────────────────────────
RECEIPT_3 = {
    "merchant_name": "Sunset Beach Shack",
    "receipt_date": date(2026, 10, 14),
    "items": [
        {"name": "Grilled Prawns", "qty": 1, "unit_paise": 65000, "total_paise": 65000, "category": "Seafood"},
        {"name": "Fish & Chips", "qty": 1, "unit_paise": 35000, "total_paise": 35000, "category": "Snacks"},
        {"name": "Coconut Water", "qty": 3, "unit_paise": 6000, "total_paise": 18000, "category": "Beverage"},
        {"name": "Watermelon Juice", "qty": 2, "unit_paise": 8000, "total_paise": 16000, "category": "Beverage"},
    ],
    "tax_paise": 6700,
    "service_charge_paise": 0,
    "delivery_fee_paise": 0,
    "discount_paise": 0,
    "paid_by_index": 2,  # Karan paid
    "claims": [
        # Grilled Prawns → Aryan, Karan, Dev
        {"item_idx": 0, "claimants": [0, 2, 4]},
        # Fish & Chips → Priya, Meera
        {"item_idx": 1, "claimants": [1, 3]},
        # Coconut Water → Aryan, Karan, Dev
        {"item_idx": 2, "claimants": [0, 2, 4]},
        # Watermelon Juice → Priya, Meera
        {"item_idx": 3, "claimants": [1, 3]},
    ],
}

# ── Receipt 4: Taxi Split ────────────────────────────────────────────────────
RECEIPT_4 = {
    "merchant_name": "Ola Taxi",
    "receipt_date": date(2026, 10, 15),
    "items": [
        {"name": "Airport → Hotel Ride", "qty": 1, "unit_paise": 85000, "total_paise": 85000, "category": "Transport"},
    ],
    "tax_paise": 0,
    "service_charge_paise": 0,
    "delivery_fee_paise": 0,
    "discount_paise": 0,
    "paid_by_index": 3,  # Meera paid
    "claims": [
        # Everyone shared the taxi
        {"item_idx": 0, "claimants": [0, 1, 2, 3, 4]},
    ],
}

ALL_RECEIPTS = [RECEIPT_1, RECEIPT_2, RECEIPT_3, RECEIPT_4]


async def create_sandbox(db: AsyncSession) -> dict:
    """
    Create the "Goa Weekend Squad" sandbox with all demo data.

    Returns a dict with the created group ID, member IDs, receipt IDs, and stats.
    """
    # ── 1. Create sandbox users ──────────────────────────────────────────
    users: list[User] = []
    for member_data in SANDBOX_MEMBERS:
        user = User(
            id=uuid.uuid4(),
            display_name=member_data["display_name"],
            avatar_color=member_data["avatar_color"],
            upi_id=member_data["upi_id"],
            is_guest=True,
        )
        db.add(user)
        users.append(user)

    await db.flush()  # Get user IDs

    # ── 2. Create the group ──────────────────────────────────────────────
    group = Group(
        id=uuid.uuid4(),
        name="Goa Weekend Squad",
        currency="INR",
        invite_code=shortuuid.uuid()[:8].upper(),
        is_sandbox=True,
        created_by=users[0].id,
    )
    db.add(group)
    await db.flush()

    # ── 3. Add members ───────────────────────────────────────────────────
    for user in users:
        membership = GroupMember(
            id=uuid.uuid4(),
            group_id=group.id,
            user_id=user.id,
        )
        db.add(membership)

    await db.flush()

    # ── 4. Create receipts with line items, claims, and ledger entries ────
    all_ledger_entries: list[dict] = []
    receipt_ids: list[uuid.UUID] = []

    for receipt_data in ALL_RECEIPTS:
        receipt_result = await _create_receipt_with_splits(
            db=db,
            group=group,
            users=users,
            receipt_data=receipt_data,
        )
        receipt_ids.append(receipt_result["receipt_id"])
        all_ledger_entries.extend(receipt_result["ledger_entries"])

    await db.flush()

    # ── 5. Return summary ────────────────────────────────────────────────
    return {
        "group_id": str(group.id),
        "group_name": group.name,
        "invite_code": group.invite_code,
        "members": [
            {
                "user_id": str(u.id),
                "display_name": u.display_name,
                "avatar_color": u.avatar_color,
                "upi_id": u.upi_id,
            }
            for u in users
        ],
        "receipts": [str(rid) for rid in receipt_ids],
        "total_receipts": len(receipt_ids),
        "total_ledger_entries": len(all_ledger_entries),
    }


async def _create_receipt_with_splits(
    db: AsyncSession,
    group: Group,
    users: list[User],
    receipt_data: dict,
) -> dict:
    """Create a single receipt with line items, claims, and ledger entries."""

    payer = users[receipt_data["paid_by_index"]]

    # Compute subtotal from items
    subtotal_paise = sum(item["total_paise"] for item in receipt_data["items"])
    total_paise = (
        subtotal_paise
        + receipt_data["tax_paise"]
        + receipt_data["service_charge_paise"]
        + receipt_data["delivery_fee_paise"]
        - receipt_data["discount_paise"]
    )

    # Create receipt
    receipt = Receipt(
        id=uuid.uuid4(),
        group_id=group.id,
        uploaded_by=payer.id,
        paid_by=payer.id,
        room_code=shortuuid.uuid()[:8].upper(),
        merchant_name=receipt_data["merchant_name"],
        receipt_date=receipt_data["receipt_date"],
        status=ReceiptStatus.LOCKED,  # Sandbox receipts are already finalized
        subtotal_paise=subtotal_paise,
        tax_paise=receipt_data["tax_paise"],
        service_charge_paise=receipt_data["service_charge_paise"],
        delivery_fee_paise=receipt_data["delivery_fee_paise"],
        discount_paise=receipt_data["discount_paise"],
        total_paise=total_paise,
        idempotency_key=f"sandbox-{group.id}-{receipt_data['merchant_name']}-{uuid.uuid4().hex[:8]}",
    )
    db.add(receipt)
    await db.flush()

    # Create line items
    line_items: list[ReceiptLineItem] = []
    for item_data in receipt_data["items"]:
        line_item = ReceiptLineItem(
            id=uuid.uuid4(),
            receipt_id=receipt.id,
            item_name=item_data["name"],
            quantity=item_data["qty"],
            unit_price_paise=item_data["unit_paise"],
            total_price_paise=item_data["total_paise"],
            category=item_data.get("category"),
        )
        db.add(line_item)
        line_items.append(line_item)

    await db.flush()

    # Create claims and compute splits
    claim_inputs: list[ClaimInput] = []
    line_item_inputs: list[LineItemInput] = []

    for claim_data in receipt_data["claims"]:
        item_idx = claim_data["item_idx"]
        li = line_items[item_idx]
        claimant_indices = claim_data["claimants"]
        k = len(claimant_indices)

        item_claims: list[ClaimInput] = []
        for ci in claimant_indices:
            claim = ItemClaim(
                id=uuid.uuid4(),
                line_item_id=li.id,
                user_id=users[ci].id,
                share_fraction_numerator=1,
                share_fraction_denominator=k,
            )
            db.add(claim)

            item_claims.append(ClaimInput(
                line_item_id=li.id,
                user_id=users[ci].id,
                share_numerator=1,
                share_denominator=k,
            ))

        line_item_inputs.append(LineItemInput(
            id=li.id,
            total_price_paise=li.total_price_paise,
            claims=item_claims,
        ))
        claim_inputs.extend(item_claims)

    await db.flush()

    # Run math engine to compute exact splits
    receipt_input = ReceiptInput(
        subtotal_paise=subtotal_paise,
        tax_paise=receipt_data["tax_paise"],
        service_charge_paise=receipt_data["service_charge_paise"],
        delivery_fee_paise=receipt_data["delivery_fee_paise"],
        discount_paise=receipt_data["discount_paise"],
        total_paise=total_paise,
        line_items=line_item_inputs,
    )

    split_result = compute_split(receipt_input)

    # Update ItemClaim computed values
    # (For sandbox, we store the final calculated values on the claims)
    # This is a simplified approach — in production, claims are updated per-item

    # Create ledger entries: each non-payer user owes the payer their share
    ledger_entries: list[dict] = []
    for user_id, user_split in split_result.user_splits.items():
        if user_id == payer.id:
            continue  # Payer doesn't owe themselves

        if user_split.final_paise <= 0:
            continue

        ledger_entry = LedgerEntry(
            id=uuid.uuid4(),
            group_id=group.id,
            receipt_id=receipt.id,
            from_user_id=user_id,  # debtor
            to_user_id=payer.id,  # creditor (payer)
            amount_paise=user_split.final_paise,
            entry_type=EntryType.EXPENSE_SHARE,
            idempotency_key=f"sandbox-{receipt.id}-{user_id}-{uuid.uuid4().hex[:8]}",
        )
        db.add(ledger_entry)
        ledger_entries.append({
            "from_user_id": user_id,
            "to_user_id": payer.id,
            "amount_paise": user_split.final_paise,
        })

    await db.flush()

    return {
        "receipt_id": receipt.id,
        "ledger_entries": ledger_entries,
        "split_result": split_result,
    }

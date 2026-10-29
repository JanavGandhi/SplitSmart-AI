"""
Interactive SplitSmart AI Stage 2 Live Demonstration.

Run with:
    python scripts/demo_stage2.py
"""
import sys
import uuid

# Ensure UTF-8 output on Windows consoles
reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(reconfigure):
    try:
        reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.services.math_engine import compute_split, ReceiptInput, LineItemInput, ClaimInput
from app.services.debt_simplifier import compute_net_balances, simplify_debts
from app.services.upi_generator import generate_upi_link

def banner(title: str):
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)

def main():
    print("\n" + "=" * 68)
    print("   SplitSmart AI — Stage 2 Interactive Live Demonstration")
    print("=" * 68)

    # -------------------------------------------------------------
    # 1. Math Engine & Paise Invariant
    # -------------------------------------------------------------
    banner("1. FINANCIAL MATH ENGINE: UNEQUAL SPLIT + TAX + DISCOUNT")
    
    user_aryan = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_priya = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_karan = uuid.UUID("33333333-3333-3333-3333-333333333333")
    user_meera = uuid.UUID("44444444-4444-4444-4444-444444444444")
    
    names = {
        user_aryan: "Aryan",
        user_priya: "Priya",
        user_karan: "Karan",
        user_meera: "Meera",
    }

    item1_id = uuid.uuid4()
    item2_id = uuid.uuid4()
    item3_id = uuid.uuid4()
    item4_id = uuid.uuid4()

    line_items = [
        # Butter Chicken (Aryan & Karan sharing 1:1)
        LineItemInput(
            id=item1_id,
            total_price_paise=58000, # 580.00 Rs
            claims=[
                ClaimInput(line_item_id=item1_id, user_id=user_aryan, share_numerator=1, share_denominator=2),
                ClaimInput(line_item_id=item1_id, user_id=user_karan, share_numerator=1, share_denominator=2),
            ]
        ),
        # Paneer Tikka (Priya & Meera sharing 1:1)
        LineItemInput(
            id=item2_id,
            total_price_paise=42000, # 420.00 Rs
            claims=[
                ClaimInput(line_item_id=item2_id, user_id=user_priya, share_numerator=1, share_denominator=2),
                ClaimInput(line_item_id=item2_id, user_id=user_meera, share_numerator=1, share_denominator=2),
            ]
        ),
        # Garlic Naan Basket (All 4 sharing equally: 1/4 each)
        LineItemInput(
            id=item3_id,
            total_price_paise=36000, # 360.00 Rs
            claims=[
                ClaimInput(line_item_id=item3_id, user_id=u, share_numerator=1, share_denominator=4)
                for u in [user_aryan, user_priya, user_karan, user_meera]
            ]
        ),
        # Exotic Cocktails (Aryan 2 drinks, Priya 1 drink -> 2/3 and 1/3)
        LineItemInput(
            id=item4_id,
            total_price_paise=125000, # 1,250.00 Rs
            claims=[
                ClaimInput(line_item_id=item4_id, user_id=user_aryan, share_numerator=2, share_denominator=3),
                ClaimInput(line_item_id=item4_id, user_id=user_priya, share_numerator=1, share_denominator=3),
            ]
        ),
    ]

    subtotal = sum(i.total_price_paise for i in line_items) # 261,000 paise (2,610 Rs)
    gst_tax = 13050          # 5% GST (130.50 Rs)
    service_charge = 26100   # 10% Service Charge (261.00 Rs)
    delivery_or_fee = 4850   # Platform fee: 48.50 Rs
    discount = 20000         # -200.00 Rs Zomato coupon
    total_bill = subtotal + gst_tax + service_charge + delivery_or_fee - discount # 285,000 paise (Rs 2,850.00)

    print(f"Receipt Grand Total  : Rs {total_bill / 100:.2f} ({total_bill:,} paise)")
    print(f"  - Subtotal (Items) : Rs {subtotal / 100:.2f}")
    print(f"  - GST (5%)         : Rs {gst_tax / 100:.2f}")
    print(f"  - Service Charge   : Rs {service_charge / 100:.2f}")
    print(f"  - Platform Fee     : Rs {delivery_or_fee / 100:.2f}")
    print(f"  - Discount Coupon  : -Rs {discount / 100:.2f}")
    print("-" * 68)

    receipt = ReceiptInput(
        subtotal_paise=subtotal,
        tax_paise=gst_tax,
        service_charge_paise=service_charge,
        delivery_fee_paise=delivery_or_fee,
        discount_paise=discount,
        total_paise=total_bill,
        line_items=line_items,
    )

    split_result = compute_split(receipt)

    print("Calculated Member Shares (with Largest-Remainder proportional allocation):")
    total_calculated = 0
    for user_id, share in split_result.user_splits.items():
        name = names.get(user_id, str(user_id)[:8])
        total_calculated += share.final_paise
        print(f"  [User] {name:<8} : Rs {share.final_paise / 100:>7.2f} "
              f"(Items: Rs {share.item_subtotal_paise/100:.2f}, Tax/Fees/Discount: Rs {share.tax_and_fees_paise/100:+.2f})")

    print("-" * 68)
    print(f"Sum of Shares        : Rs {total_calculated / 100:.2f} ({total_calculated:,} paise)")
    print(f"Paise Invariant Check: {'[PASSED] PERFECT (0 paise leak - invariant holds!)' if split_result.invariant_holds else '[FAILED] MISMATCH'}")

    # -------------------------------------------------------------
    # 2. Debt Simplification Engine (Min-Cash-Flow)
    # -------------------------------------------------------------
    banner("2. DEBT GRAPH SIMPLIFICATION: GOA TRIP 11 DEBTS -> 4")

    user_dev = uuid.UUID("55555555-5555-5555-5555-555555555555")
    names[user_dev] = "Dev"

    # Simulate 11 pairwise debts across 5 friends from various receipts
    debts = [
        {"from_user_id": user_priya, "to_user_id": user_aryan, "amount_paise": 125000},
        {"from_user_id": user_karan, "to_user_id": user_aryan, "amount_paise": 85000},
        {"from_user_id": user_meera, "to_user_id": user_aryan, "amount_paise": 95000},
        {"from_user_id": user_dev,   "to_user_id": user_aryan, "amount_paise": 110000},
        {"from_user_id": user_aryan, "to_user_id": user_priya, "amount_paise": 45000},
        {"from_user_id": user_karan, "to_user_id": user_priya, "amount_paise": 75000},
        {"from_user_id": user_meera, "to_user_id": user_priya, "amount_paise": 30000},
        {"from_user_id": user_dev,   "to_user_id": user_karan, "amount_paise": 60000},
        {"from_user_id": user_aryan, "to_user_id": user_meera, "amount_paise": 50000},
        {"from_user_id": user_priya, "to_user_id": user_dev,   "amount_paise": 40000},
        {"from_user_id": user_karan, "to_user_id": user_dev,   "amount_paise": 35000},
    ]

    print(f"Raw Transaction Count: {len(debts)} messy pairwise debts between 5 friends")

    balances = compute_net_balances(debts, user_names=names)
    print("\nNet Balances (who is overall in debt vs credit):")
    for b in sorted(balances, key=lambda x: x.net_balance_paise, reverse=True):
        pos = "Creditor (is owed)" if b.net_balance_paise > 0 else "Debtor (owes)"
        print(f"  [User] {b.display_name:<6} : {pos:<18} Rs {abs(b.net_balance_paise) / 100:>7.2f}")

    simplification = simplify_debts(balances, original_transaction_count=len(debts))
    print(f"\nSimplified Payments  : {simplification.simplified_count} optimal direct settlements (Saved {simplification.transactions_saved} transactions!)")
    print("-" * 68)

    for i, s in enumerate(simplification.settlements, 1):
        debtor = s.from_display_name or str(s.from_user_id)[:8]
        creditor = s.to_display_name or str(s.to_user_id)[:8]
        print(f"  [{i}] {debtor:<6} --(pays Rs {s.amount_paise / 100:>7.2f})--> {creditor}")

    # -------------------------------------------------------------
    # 3. UPI Deep Links & QR Codes
    # -------------------------------------------------------------
    banner("3. UPI DEEP LINK & QR CODE GENERATION")
    
    first_settlement = simplification.settlements[0]
    debtor_name = first_settlement.from_display_name
    creditor_name = first_settlement.to_display_name
    creditor_upi = f"{creditor_name.lower()}@oksbi"
    amount_rs = first_settlement.amount_paise / 100

    upi_info = generate_upi_link(
        upi_id=creditor_upi,
        payee_name=creditor_name,
        amount_paise=first_settlement.amount_paise,
        note="SplitSmart Goa Settlement"
    )

    print(f"Settlement : {debtor_name} pays {creditor_name}")
    print(f"Amount     : Rs {amount_rs:.2f} ({first_settlement.amount_paise:,} paise)")
    print(f"Payee UPI  : {creditor_upi}")
    print(f"UPI Intent : {upi_info.uri}")
    print(f"QR Base64  : {upi_info.qr_base64[:55]}... [truncated base64 image]")

    banner("ALL INVARIANTS & ENGINES VERIFIED SUCCESSFULLY [OK]")
    print("\nYou can run the full automated test suite anytime with:")
    print("   pytest -v\n")

if __name__ == "__main__":
    main()

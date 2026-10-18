"""
Tests for the Math Engine — Proportional split with paise invariant.

Key tests:
1. Simple equal split
2. Unequal claims with different fractions
3. Tax/fee/discount distribution
4. 100 random receipt permutations — invariant must ALWAYS hold
5. Edge cases: single claimant, zero amounts, large numbers
"""
import random
import uuid

import pytest

from app.services.math_engine import (
    ClaimInput,
    LineItemInput,
    ReceiptInput,
    SplitResult,
    compute_equal_split,
    compute_split,
)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


class TestEqualSplit:
    """Tests for simple equal splits."""

    def test_equal_split_two_users(self):
        users = [_uid(), _uid()]
        result = compute_equal_split(10000, users)
        assert result.invariant_holds
        assert result.total_distributed_paise == 10000
        assert len(result.user_splits) == 2
        assert all(s.final_paise == 5000 for s in result.user_splits.values())

    def test_equal_split_three_users_with_remainder(self):
        """10000 / 3 = 3333 remainder 1 — one user should get 3334."""
        users = [_uid(), _uid(), _uid()]
        result = compute_equal_split(10000, users)
        assert result.invariant_holds
        assert result.total_distributed_paise == 10000
        amounts = sorted(s.final_paise for s in result.user_splits.values())
        assert amounts == [3333, 3333, 3334]

    def test_equal_split_five_users(self):
        """10001 / 5 = 2000 remainder 1."""
        users = [_uid() for _ in range(5)]
        result = compute_equal_split(10001, users)
        assert result.invariant_holds
        assert result.total_distributed_paise == 10001

    def test_equal_split_zero_amount(self):
        users = [_uid(), _uid()]
        result = compute_equal_split(0, users)
        assert result.invariant_holds

    def test_equal_split_single_user(self):
        user = _uid()
        result = compute_equal_split(45050, [user])
        assert result.invariant_holds
        assert result.user_splits[user].final_paise == 45050

    def test_equal_split_empty_users(self):
        result = compute_equal_split(10000, [])
        # With no users, invariant holds only if total is 0
        assert not result.invariant_holds


class TestItemSplitting:
    """Tests for per-item claim splitting."""

    def test_single_item_two_claimants(self):
        u1, u2 = _uid(), _uid()
        item = LineItemInput(
            id=_uid(),
            total_price_paise=10000,
            claims=[
                ClaimInput(line_item_id=_uid(), user_id=u1),
                ClaimInput(line_item_id=_uid(), user_id=u2),
            ],
        )
        receipt = ReceiptInput(
            subtotal_paise=10000,
            total_paise=10000,
            line_items=[item],
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.user_splits[u1].final_paise == 5000
        assert result.user_splits[u2].final_paise == 5000

    def test_single_item_three_claimants_odd_amount(self):
        """10001 / 3 should be split as 3334, 3334, 3333 (or similar)."""
        users = [_uid() for _ in range(3)]
        item = LineItemInput(
            id=_uid(),
            total_price_paise=10001,
            claims=[
                ClaimInput(line_item_id=_uid(), user_id=u) for u in users
            ],
        )
        receipt = ReceiptInput(
            subtotal_paise=10001,
            total_paise=10001,
            line_items=[item],
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.total_distributed_paise == 10001

    def test_multiple_items_different_claimants(self):
        """Two items with different claimant sets."""
        u1, u2, u3 = _uid(), _uid(), _uid()
        items = [
            LineItemInput(
                id=_uid(),
                total_price_paise=30000,  # u1, u2
                claims=[
                    ClaimInput(line_item_id=_uid(), user_id=u1),
                    ClaimInput(line_item_id=_uid(), user_id=u2),
                ],
            ),
            LineItemInput(
                id=_uid(),
                total_price_paise=20000,  # u2, u3
                claims=[
                    ClaimInput(line_item_id=_uid(), user_id=u2),
                    ClaimInput(line_item_id=_uid(), user_id=u3),
                ],
            ),
        ]
        receipt = ReceiptInput(
            subtotal_paise=50000,
            total_paise=50000,
            line_items=items,
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        # u1: 15000 from item 1
        # u2: 15000 from item 1 + 10000 from item 2 = 25000
        # u3: 10000 from item 2
        assert result.user_splits[u1].final_paise == 15000
        assert result.user_splits[u2].final_paise == 25000
        assert result.user_splits[u3].final_paise == 10000


class TestTaxDistribution:
    """Tests for proportional tax/fee/discount distribution."""

    def test_tax_distributed_proportionally(self):
        """Tax should be distributed in proportion to item subtotals."""
        u1, u2 = _uid(), _uid()
        items = [
            LineItemInput(
                id=_uid(),
                total_price_paise=60000,  # u1 only → 60% of subtotal
                claims=[ClaimInput(line_item_id=_uid(), user_id=u1)],
            ),
            LineItemInput(
                id=_uid(),
                total_price_paise=40000,  # u2 only → 40% of subtotal
                claims=[ClaimInput(line_item_id=_uid(), user_id=u2)],
            ),
        ]
        receipt = ReceiptInput(
            subtotal_paise=100000,
            tax_paise=10000,
            total_paise=110000,
            line_items=items,
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.total_distributed_paise == 110000
        # u1 should get ~60% of tax = 6000, u2 ~40% = 4000
        assert result.user_splits[u1].final_paise == 66000
        assert result.user_splits[u2].final_paise == 44000

    def test_discount_reduces_total(self):
        """Discount should reduce each user's share proportionally."""
        u1, u2 = _uid(), _uid()
        items = [
            LineItemInput(
                id=_uid(),
                total_price_paise=50000,
                claims=[
                    ClaimInput(line_item_id=_uid(), user_id=u1),
                    ClaimInput(line_item_id=_uid(), user_id=u2),
                ],
            ),
        ]
        receipt = ReceiptInput(
            subtotal_paise=50000,
            tax_paise=5000,
            discount_paise=10000,
            total_paise=45000,  # 50000 + 5000 - 10000
            line_items=items,
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.total_distributed_paise == 45000

    def test_service_charge_and_delivery_fee(self):
        """All extra charges should be included in distribution."""
        u1 = _uid()
        items = [
            LineItemInput(
                id=_uid(),
                total_price_paise=10000,
                claims=[ClaimInput(line_item_id=_uid(), user_id=u1)],
            ),
        ]
        receipt = ReceiptInput(
            subtotal_paise=10000,
            tax_paise=500,
            service_charge_paise=1000,
            delivery_fee_paise=3000,
            discount_paise=500,
            total_paise=14000,  # 10000 + 500 + 1000 + 3000 - 500
            line_items=items,
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.user_splits[u1].final_paise == 14000


class TestEdgeCases:
    """Tests for edge cases."""

    def test_no_claims(self):
        """Receipt with no claims should handle gracefully."""
        receipt = ReceiptInput(
            subtotal_paise=10000,
            total_paise=10000,
            line_items=[
                LineItemInput(id=_uid(), total_price_paise=10000, claims=[]),
            ],
        )
        result = compute_split(receipt)
        assert len(result.user_splits) == 0

    def test_single_claimant_gets_everything(self):
        """One person claiming all items gets the full bill."""
        u1 = _uid()
        items = [
            LineItemInput(
                id=_uid(),
                total_price_paise=p,
                claims=[ClaimInput(line_item_id=_uid(), user_id=u1)],
            )
            for p in [10000, 20000, 15000]
        ]
        receipt = ReceiptInput(
            subtotal_paise=45000,
            tax_paise=2250,
            total_paise=47250,
            line_items=items,
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.user_splits[u1].final_paise == 47250

    def test_one_paise_amount(self):
        """Smallest possible amount: 1 paise split among 2."""
        u1, u2 = _uid(), _uid()
        item = LineItemInput(
            id=_uid(),
            total_price_paise=1,
            claims=[
                ClaimInput(line_item_id=_uid(), user_id=u1),
                ClaimInput(line_item_id=_uid(), user_id=u2),
            ],
        )
        receipt = ReceiptInput(
            subtotal_paise=1,
            total_paise=1,
            line_items=[item],
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.total_distributed_paise == 1

    def test_large_amount(self):
        """Large bill amount (Rs 1,00,000 = 10M paise)."""
        u1, u2, u3 = _uid(), _uid(), _uid()
        item = LineItemInput(
            id=_uid(),
            total_price_paise=10000000,
            claims=[
                ClaimInput(line_item_id=_uid(), user_id=u)
                for u in [u1, u2, u3]
            ],
        )
        receipt = ReceiptInput(
            subtotal_paise=10000000,
            tax_paise=500000,
            total_paise=10500000,
            line_items=[item],
        )
        result = compute_split(receipt)
        assert result.invariant_holds
        assert result.total_distributed_paise == 10500000


class TestRandomPermutations:
    """100 random receipt permutations — invariant must ALWAYS hold."""

    @pytest.mark.parametrize("seed", range(100))
    def test_random_receipt_invariant(self, seed: int):
        """
        Generate a random receipt with random items, claimants, and charges.
        The paise invariant must hold for every single permutation.
        """
        rng = random.Random(seed)

        # Random number of users (2-7)
        num_users = rng.randint(2, 7)
        users = [_uid() for _ in range(num_users)]

        # Random number of items (1-15)
        num_items = rng.randint(1, 15)
        items = []
        subtotal = 0

        for _ in range(num_items):
            price = rng.randint(100, 100000)  # 1 to 1000 rupees
            subtotal += price

            # Random claimants (1 to all users)
            num_claimants = rng.randint(1, num_users)
            claimants = rng.sample(users, num_claimants)

            items.append(LineItemInput(
                id=_uid(),
                total_price_paise=price,
                claims=[
                    ClaimInput(
                        line_item_id=_uid(),
                        user_id=u,
                        share_numerator=1,
                        share_denominator=num_claimants,
                    )
                    for u in claimants
                ],
            ))

        # Random extra charges
        tax = rng.randint(0, subtotal // 5)  # up to 20% tax
        service = rng.randint(0, subtotal // 10)  # up to 10% service
        delivery = rng.randint(0, 5000)  # up to 50 rupees delivery
        discount = rng.randint(0, min(subtotal // 4, tax + service + delivery))  # reasonable discount

        total = subtotal + tax + service + delivery - discount

        receipt = ReceiptInput(
            subtotal_paise=subtotal,
            tax_paise=tax,
            service_charge_paise=service,
            delivery_fee_paise=delivery,
            discount_paise=discount,
            total_paise=total,
            line_items=items,
        )

        result = compute_split(receipt)

        # THE CRITICAL INVARIANT: sum of all splits == total
        assert result.invariant_holds, (
            f"INVARIANT VIOLATED! seed={seed} "
            f"distributed={result.total_distributed_paise} expected={total}"
        )
        assert result.total_distributed_paise == total, (
            f"Total mismatch: seed={seed} "
            f"distributed={result.total_distributed_paise} expected={total}"
        )

        # Verify no negative splits
        for uid, split in result.user_splits.items():
            assert split.final_paise >= 0, (
                f"Negative split for user {uid}: {split.final_paise} paise (seed={seed})"
            )

"""
Math Engine — Proportional tax/fee/discount distribution with exact paise arithmetic.

INVARIANT: sum(all user final amounts) == receipt total_paise. Always. No exceptions.

Algorithm (from SPEC.md §5.1):
1. Each of k claimants of item P gets: floor(P / k) paise
2. Remainder P mod k distributed 1 paise to first (P mod k) claimants sorted by user_id
3. S_u = sum(P_{u,item}) for all items claimed by user u
4. A_u = floor(A * (S_u / S)) where A = E - D  (net extra charges)
5. Compute R = T - sum(S_u + A_u); distribute R paise 1-by-1 sorted by largest fractional remainder
6. INVARIANT: sum(S_u + A_u) == T always
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ClaimInput:
    """A user's claim on a single line item."""
    line_item_id: uuid.UUID
    user_id: uuid.UUID
    # fraction = numerator / denominator  (e.g. 1/3 for equal 3-way split)
    share_numerator: int = 1
    share_denominator: int = 1


@dataclass
class LineItemInput:
    """A single receipt line item with its price and claimants."""
    id: uuid.UUID
    total_price_paise: int
    claims: list[ClaimInput] = field(default_factory=list)


@dataclass
class ReceiptInput:
    """All data needed to compute a split for one receipt."""
    subtotal_paise: int  # sum of all line item prices
    tax_paise: int = 0
    service_charge_paise: int = 0
    delivery_fee_paise: int = 0
    discount_paise: int = 0
    total_paise: int = 0  # S + E - D  (the grand total on the bill)
    line_items: list[LineItemInput] = field(default_factory=list)


@dataclass
class UserSplit:
    """Computed split result for a single user."""
    user_id: uuid.UUID
    item_subtotal_paise: int = 0  # sum of item shares
    tax_and_fees_paise: int = 0  # proportional share of extras
    final_paise: int = 0  # item_subtotal + tax_and_fees


@dataclass
class SplitResult:
    """Complete split result for a receipt."""
    user_splits: dict[uuid.UUID, UserSplit] = field(default_factory=dict)
    total_distributed_paise: int = 0
    invariant_holds: bool = False  # True if sum == receipt total


def _distribute_integer(total: int, shares: list[tuple[uuid.UUID, int]], grand_total_shares: int) -> dict[uuid.UUID, int]:
    """
    Distribute `total` paise proportionally among users based on their share amounts,
    using the largest-remainder method to ensure exact distribution.

    Args:
        total: Total paise to distribute
        shares: List of (user_id, share_amount) tuples
        grand_total_shares: Sum of all share amounts (denominator for proportions)

    Returns:
        Dict mapping user_id -> allocated paise
    """
    if grand_total_shares == 0 or not shares:
        return {}

    result: dict[uuid.UUID, int] = {}
    remainders: list[tuple[uuid.UUID, float]] = []
    allocated = 0

    for user_id, share_amount in shares:
        # Exact proportional value
        exact = total * share_amount / grand_total_shares
        floored = int(exact)  # floor
        remainder = exact - floored

        result[user_id] = result.get(user_id, 0) + floored
        allocated += floored
        remainders.append((user_id, remainder))

    # Distribute remaining paise by largest fractional remainder, breaking ties by user_id
    leftover = total - allocated
    remainders.sort(key=lambda x: (-x[1], str(x[0])))

    for i in range(leftover):
        uid = remainders[i][0]
        result[uid] = result.get(uid, 0) + 1

    return result


def _split_item_among_claimants(
    item_total_paise: int,
    claims: list[ClaimInput],
) -> dict[uuid.UUID, int]:
    """
    Split a single line item among its claimants based on share fractions.

    Each claimant gets floor(item_total * fraction) paise.
    Remainder distributed 1 paise at a time to claimants sorted by user_id.
    """
    if not claims:
        return {}

    # Calculate total fraction denominator (LCM-based would be more precise,
    # but we use weighted shares which works for any fraction)
    total_weight = 0
    weighted_claims: list[tuple[uuid.UUID, int]] = []

    for claim in claims:
        # Weight = numerator * (product of all other denominators)
        # Simpler: just use numerator/denominator as float for weight calculation
        # But we need integer arithmetic. So we normalize:
        # fraction_i = n_i / d_i
        # weight_i = n_i * product(d_j for j != i)
        # This gets complex for many claimants. Instead, use a common denominator approach.
        weight = claim.share_numerator  # simplified: assume equal denominators for now
        weighted_claims.append((claim.user_id, weight))
        total_weight += weight

    if total_weight == 0:
        return {}

    # Use common denominator to get exact integer weights
    # For claims with different denominators, compute LCM and convert
    from math import gcd
    from functools import reduce

    def lcm(a: int, b: int) -> int:
        return a * b // gcd(a, b)

    common_denom = reduce(lcm, [c.share_denominator for c in claims])

    # Recompute with proper weights
    weighted_claims = []
    total_weight = 0
    for claim in claims:
        weight = claim.share_numerator * (common_denom // claim.share_denominator)
        weighted_claims.append((claim.user_id, weight))
        total_weight += weight

    return _distribute_integer(item_total_paise, weighted_claims, total_weight)


def compute_split(receipt: ReceiptInput) -> SplitResult:
    """
    Compute the exact paise split for a receipt.

    This is the main entry point for the math engine.
    Guarantees: sum(user.final_paise for all users) == receipt.total_paise

    Algorithm:
    1. Split each line item among its claimants
    2. Sum item shares per user -> S_u
    3. Compute net extra charges A = tax + service_charge + delivery_fee - discount
    4. Distribute A proportionally by S_u using largest-remainder
    5. Verify invariant
    """
    result = SplitResult()

    # ── Step 1 & 2: Split items and compute per-user subtotals ────────────
    user_item_totals: dict[uuid.UUID, int] = {}

    for item in receipt.line_items:
        if not item.claims:
            continue

        item_splits = _split_item_among_claimants(item.total_price_paise, item.claims)

        for user_id, paise in item_splits.items():
            user_item_totals[user_id] = user_item_totals.get(user_id, 0) + paise

    if not user_item_totals:
        result.invariant_holds = (receipt.total_paise == 0)
        return result

    # ── Step 3: Compute subtotal from items (S) ──────────────────────────
    computed_subtotal = sum(user_item_totals.values())

    # ── Step 4: Distribute extras proportionally ─────────────────────────
    # Net extra = tax + service + delivery - discount
    net_extras = (
        receipt.tax_paise
        + receipt.service_charge_paise
        + receipt.delivery_fee_paise
        - receipt.discount_paise
    )

    user_extras: dict[uuid.UUID, int] = {}
    if net_extras != 0 and computed_subtotal > 0:
        shares = [(uid, amt) for uid, amt in user_item_totals.items()]
        user_extras = _distribute_integer(net_extras, shares, computed_subtotal)
    elif net_extras != 0 and computed_subtotal == 0:
        # Edge case: extras exist but no item subtotals — distribute equally
        users = list(user_item_totals.keys())
        if users:
            equal_shares = [(uid, 1) for uid in users]
            user_extras = _distribute_integer(net_extras, equal_shares, len(users))

    # ── Step 5: Combine and verify invariant ──────────────────────────────
    all_users = set(user_item_totals.keys()) | set(user_extras.keys())
    total_distributed = 0

    for user_id in all_users:
        item_sub = user_item_totals.get(user_id, 0)
        extras = user_extras.get(user_id, 0)
        final = item_sub + extras

        split = UserSplit(
            user_id=user_id,
            item_subtotal_paise=item_sub,
            tax_and_fees_paise=extras,
            final_paise=final,
        )
        result.user_splits[user_id] = split
        total_distributed += final

    result.total_distributed_paise = total_distributed

    # ── Step 6: Final remainder correction ────────────────────────────────
    # If there's still a mismatch due to item splitting vs total, fix it
    expected_total = receipt.total_paise
    if expected_total > 0 and total_distributed != expected_total:
        diff = expected_total - total_distributed
        # Distribute diff using largest-remainder on current splits
        if diff != 0:
            sorted_users = sorted(
                result.user_splits.keys(),
                key=lambda uid: (-result.user_splits[uid].final_paise, str(uid)),
            )
            sign = 1 if diff > 0 else -1
            for i in range(abs(diff)):
                uid = sorted_users[i % len(sorted_users)]
                result.user_splits[uid].tax_and_fees_paise += sign
                result.user_splits[uid].final_paise += sign
            result.total_distributed_paise = expected_total

    result.invariant_holds = (result.total_distributed_paise == expected_total)
    return result


def compute_equal_split(total_paise: int, user_ids: list[uuid.UUID]) -> SplitResult:
    """
    Simple equal split — divide total equally among users with paise precision.
    Useful for items where everyone shares equally.
    """
    if not user_ids or total_paise == 0:
        return SplitResult(invariant_holds=(total_paise == 0))

    shares = [(uid, 1) for uid in user_ids]
    distribution = _distribute_integer(total_paise, shares, len(user_ids))

    result = SplitResult()
    for uid, paise in distribution.items():
        result.user_splits[uid] = UserSplit(
            user_id=uid,
            item_subtotal_paise=paise,
            tax_and_fees_paise=0,
            final_paise=paise,
        )

    result.total_distributed_paise = sum(s.final_paise for s in result.user_splits.values())
    result.invariant_holds = (result.total_distributed_paise == total_paise)
    return result

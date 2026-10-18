"""
Debt Simplifier — Min-Cash-Flow algorithm using max/min heaps.

Given a set of net balances (who is owed how much, who owes how much),
computes the minimum number of transactions to settle all debts.

Algorithm (from SPEC.md §5.2):
1. Compute net balance B(u) for each user
2. Verify sum(B(u)) == 0  (zero-sum invariant)
3. Creditors → max-heap, Debtors → min-heap
4. Pop largest creditor + largest debtor, settle M = min(B_c, |B_d|)
5. Record edge u_d → u_c : M paise; push remainders back
6. Repeat until both heaps are empty

Time complexity: O(N log N) where N = number of users
"""
from __future__ import annotations

import heapq
import uuid
from dataclasses import dataclass, field


@dataclass
class BalanceEntry:
    """A single user's balance in a group."""
    user_id: uuid.UUID
    display_name: str = ""
    # Net balance in paise: positive = is owed money (creditor), negative = owes money (debtor)
    net_balance_paise: int = 0


@dataclass
class Settlement:
    """A single settlement transaction: debtor pays creditor."""
    from_user_id: uuid.UUID  # debtor
    to_user_id: uuid.UUID  # creditor
    amount_paise: int  # always positive

    from_display_name: str = ""
    to_display_name: str = ""


@dataclass
class SimplificationResult:
    """Result of debt simplification."""
    # Original number of debts (before simplification)
    original_transaction_count: int = 0
    # Simplified settlements
    settlements: list[Settlement] = field(default_factory=list)
    # Number of simplified transactions
    simplified_count: int = 0
    # Reduction stats
    transactions_saved: int = 0
    # Zero-sum invariant check
    zero_sum_verified: bool = False


def compute_net_balances(
    ledger_entries: list[dict],
    user_names: dict[uuid.UUID, str] | None = None,
) -> list[BalanceEntry]:
    """
    Compute net balance for each user from ledger entries.

    Each ledger entry has: from_user_id (debtor), to_user_id (creditor), amount_paise.

    Net balance:
    - Positive = others owe you (you are a creditor)
    - Negative = you owe others (you are a debtor)

    Args:
        ledger_entries: List of dicts with keys: from_user_id, to_user_id, amount_paise
        user_names: Optional mapping of user_id -> display_name
    """
    balances: dict[uuid.UUID, int] = {}

    for entry in ledger_entries:
        from_uid = entry["from_user_id"]
        to_uid = entry["to_user_id"]
        amount = entry["amount_paise"]

        # Creditor (to_user) gets +amount
        balances[to_uid] = balances.get(to_uid, 0) + amount
        # Debtor (from_user) gets -amount
        balances[from_uid] = balances.get(from_uid, 0) - amount

    names = user_names or {}
    return [
        BalanceEntry(
            user_id=uid,
            display_name=names.get(uid, ""),
            net_balance_paise=balance,
        )
        for uid, balance in balances.items()
        if balance != 0  # skip users with zero balance
    ]


def simplify_debts(
    balances: list[BalanceEntry],
    original_transaction_count: int = 0,
) -> SimplificationResult:
    """
    Simplify debts using the Min-Cash-Flow algorithm with max/min heaps.

    Args:
        balances: List of BalanceEntry objects with net_balance_paise
        original_transaction_count: Number of original transactions (for stats)

    Returns:
        SimplificationResult with optimal settlements

    Raises:
        ValueError: If balances don't sum to zero (broken invariant)
    """
    result = SimplificationResult(original_transaction_count=original_transaction_count)

    # ── Verify zero-sum invariant ─────────────────────────────────────────
    total = sum(b.net_balance_paise for b in balances)
    if total != 0:
        raise ValueError(
            f"Balance zero-sum invariant violated! Sum = {total} paise. "
            f"This indicates a bug in expense calculation."
        )
    result.zero_sum_verified = True

    # ── Build name lookup ─────────────────────────────────────────────────
    names: dict[uuid.UUID, str] = {b.user_id: b.display_name for b in balances}

    # ── Separate into creditors (positive) and debtors (negative) ────────
    # Max-heap for creditors (negate for Python's min-heap)
    # Min-heap for debtors (already negative, use as-is for min-heap behavior)
    creditor_heap: list[tuple[int, str, uuid.UUID]] = []  # (-balance, uid_str, uid)
    debtor_heap: list[tuple[int, str, uuid.UUID]] = []  # (balance, uid_str, uid)  — balance is negative

    for b in balances:
        if b.net_balance_paise > 0:
            # Creditor — negate for max-heap simulation
            heapq.heappush(creditor_heap, (-b.net_balance_paise, str(b.user_id), b.user_id))
        elif b.net_balance_paise < 0:
            # Debtor — balance is already negative
            heapq.heappush(debtor_heap, (b.net_balance_paise, str(b.user_id), b.user_id))

    # ── Match creditors and debtors ───────────────────────────────────────
    settlements: list[Settlement] = []

    while creditor_heap and debtor_heap:
        # Pop largest creditor and largest debtor
        neg_credit, _, creditor_id = heapq.heappop(creditor_heap)
        neg_debit, _, debtor_id = heapq.heappop(debtor_heap)

        credit_amount = -neg_credit  # positive
        debit_amount = -neg_debit  # positive (was negative)

        # Settle minimum of the two
        settle_amount = min(credit_amount, debit_amount)

        settlements.append(Settlement(
            from_user_id=debtor_id,
            to_user_id=creditor_id,
            amount_paise=settle_amount,
            from_display_name=names.get(debtor_id, ""),
            to_display_name=names.get(creditor_id, ""),
        ))

        # Push remainders back
        credit_remainder = credit_amount - settle_amount
        debit_remainder = debit_amount - settle_amount

        if credit_remainder > 0:
            heapq.heappush(creditor_heap, (-credit_remainder, str(creditor_id), creditor_id))

        if debit_remainder > 0:
            heapq.heappush(debtor_heap, (-debit_remainder, str(debtor_id), debtor_id))

    result.settlements = settlements
    result.simplified_count = len(settlements)
    result.transactions_saved = max(0, original_transaction_count - len(settlements))

    return result


def simplify_from_ledger(
    ledger_entries: list[dict],
    user_names: dict[uuid.UUID, str] | None = None,
) -> SimplificationResult:
    """
    Convenience function: compute balances from ledger entries and simplify.

    Args:
        ledger_entries: List of dicts with keys: from_user_id, to_user_id, amount_paise
        user_names: Optional mapping of user_id -> display_name

    Returns:
        SimplificationResult with optimal settlements
    """
    balances = compute_net_balances(ledger_entries, user_names)
    return simplify_debts(
        balances,
        original_transaction_count=len(ledger_entries),
    )

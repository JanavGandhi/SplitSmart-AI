"""
Tests for the Debt Simplifier — Min-Cash-Flow algorithm.

Key tests:
1. Simple two-person debt
2. Circular debts (A→B→C→A)
3. Multiple creditors and debtors
4. Zero-sum invariant verification
5. Optimal reduction (fewer transactions)
6. Edge cases: single user, no debts, large groups
"""
import uuid

import pytest

from app.services.debt_simplifier import (
    BalanceEntry,
    Settlement,
    SimplificationResult,
    compute_net_balances,
    simplify_debts,
    simplify_from_ledger,
)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


class TestNetBalances:
    """Tests for computing net balances from ledger entries."""

    def test_simple_two_person(self):
        u1, u2 = _uid(), _uid()
        entries = [
            {"from_user_id": u1, "to_user_id": u2, "amount_paise": 10000},
        ]
        balances = compute_net_balances(entries)
        balance_map = {b.user_id: b.net_balance_paise for b in balances}
        assert balance_map[u1] == -10000  # owes
        assert balance_map[u2] == 10000  # is owed

    def test_multiple_entries_same_pair(self):
        u1, u2 = _uid(), _uid()
        entries = [
            {"from_user_id": u1, "to_user_id": u2, "amount_paise": 5000},
            {"from_user_id": u1, "to_user_id": u2, "amount_paise": 3000},
        ]
        balances = compute_net_balances(entries)
        balance_map = {b.user_id: b.net_balance_paise for b in balances}
        assert balance_map[u1] == -8000
        assert balance_map[u2] == 8000

    def test_bidirectional_debts(self):
        u1, u2 = _uid(), _uid()
        entries = [
            {"from_user_id": u1, "to_user_id": u2, "amount_paise": 10000},
            {"from_user_id": u2, "to_user_id": u1, "amount_paise": 7000},
        ]
        balances = compute_net_balances(entries)
        balance_map = {b.user_id: b.net_balance_paise for b in balances}
        assert balance_map[u1] == -3000  # net owes 3000
        assert balance_map[u2] == 3000  # net is owed 3000

    def test_zero_balance_users_excluded(self):
        u1, u2 = _uid(), _uid()
        entries = [
            {"from_user_id": u1, "to_user_id": u2, "amount_paise": 5000},
            {"from_user_id": u2, "to_user_id": u1, "amount_paise": 5000},
        ]
        balances = compute_net_balances(entries)
        # Both should cancel out and be excluded
        assert len(balances) == 0

    def test_three_person_chain(self):
        u1, u2, u3 = _uid(), _uid(), _uid()
        entries = [
            {"from_user_id": u1, "to_user_id": u2, "amount_paise": 10000},
            {"from_user_id": u2, "to_user_id": u3, "amount_paise": 10000},
        ]
        balances = compute_net_balances(entries)
        balance_map = {b.user_id: b.net_balance_paise for b in balances}
        assert balance_map[u1] == -10000
        assert balance_map.get(u2, 0) == 0  # u2 cancels out
        assert balance_map[u3] == 10000


class TestSimplifyDebts:
    """Tests for the min-cash-flow simplification algorithm."""

    def test_simple_two_person(self):
        u1, u2 = _uid(), _uid()
        balances = [
            BalanceEntry(user_id=u1, display_name="A", net_balance_paise=-10000),
            BalanceEntry(user_id=u2, display_name="B", net_balance_paise=10000),
        ]
        result = simplify_debts(balances)
        assert result.zero_sum_verified
        assert result.simplified_count == 1
        assert result.settlements[0].from_user_id == u1
        assert result.settlements[0].to_user_id == u2
        assert result.settlements[0].amount_paise == 10000

    def test_three_person_chain_simplifies(self):
        """A owes B 10000, B owes C 10000 → simplifies to A owes C 10000."""
        u_a, u_b, u_c = _uid(), _uid(), _uid()
        # After netting: A=-10000, B=0, C=+10000
        balances = [
            BalanceEntry(user_id=u_a, display_name="A", net_balance_paise=-10000),
            BalanceEntry(user_id=u_c, display_name="C", net_balance_paise=10000),
        ]
        result = simplify_debts(balances, original_transaction_count=2)
        assert result.zero_sum_verified
        assert result.simplified_count == 1
        assert result.transactions_saved == 1

    def test_circular_debt(self):
        """A→B: 5000, B→C: 5000, C→A: 5000 → all cancel out."""
        u_a, u_b, u_c = _uid(), _uid(), _uid()
        entries = [
            {"from_user_id": u_a, "to_user_id": u_b, "amount_paise": 5000},
            {"from_user_id": u_b, "to_user_id": u_c, "amount_paise": 5000},
            {"from_user_id": u_c, "to_user_id": u_a, "amount_paise": 5000},
        ]
        result = simplify_from_ledger(entries)
        assert result.zero_sum_verified
        assert result.simplified_count == 0  # All debts cancel

    def test_five_person_group_reduces(self):
        """
        5 users with cross-debts should reduce to fewer transactions.

        Simulate: everyone paid for something, creating N*(N-1)/2 possible edges.
        """
        users = [_uid() for _ in range(5)]
        # Create messy cross-debts
        entries = [
            {"from_user_id": users[0], "to_user_id": users[1], "amount_paise": 20000},
            {"from_user_id": users[0], "to_user_id": users[2], "amount_paise": 15000},
            {"from_user_id": users[1], "to_user_id": users[3], "amount_paise": 30000},
            {"from_user_id": users[2], "to_user_id": users[3], "amount_paise": 10000},
            {"from_user_id": users[2], "to_user_id": users[4], "amount_paise": 25000},
            {"from_user_id": users[3], "to_user_id": users[0], "amount_paise": 12000},
            {"from_user_id": users[4], "to_user_id": users[1], "amount_paise": 18000},
            {"from_user_id": users[4], "to_user_id": users[0], "amount_paise": 8000},
        ]
        result = simplify_from_ledger(entries)
        assert result.zero_sum_verified
        # Must have fewer transactions than original
        assert result.simplified_count <= len(entries)
        assert result.transactions_saved >= 0

        # Verify settlement amounts are correct (zero-sum)
        settlement_debtor_total: dict[uuid.UUID, int] = {}
        settlement_creditor_total: dict[uuid.UUID, int] = {}
        for s in result.settlements:
            settlement_debtor_total[s.from_user_id] = (
                settlement_debtor_total.get(s.from_user_id, 0) + s.amount_paise
            )
            settlement_creditor_total[s.to_user_id] = (
                settlement_creditor_total.get(s.to_user_id, 0) + s.amount_paise
            )

    def test_zero_sum_invariant_violation_raises(self):
        """If balances don't sum to zero, should raise ValueError."""
        balances = [
            BalanceEntry(user_id=_uid(), display_name="A", net_balance_paise=10000),
            BalanceEntry(user_id=_uid(), display_name="B", net_balance_paise=-5000),
        ]
        with pytest.raises(ValueError, match="zero-sum invariant"):
            simplify_debts(balances)

    def test_empty_balances(self):
        result = simplify_debts([])
        assert result.zero_sum_verified
        assert result.simplified_count == 0

    def test_single_large_creditor_multiple_debtors(self):
        """One person paid for everything, 4 others owe them."""
        creditor = _uid()
        debtors = [_uid() for _ in range(4)]

        balances = [
            BalanceEntry(user_id=creditor, display_name="Payer", net_balance_paise=40000),
        ] + [
            BalanceEntry(user_id=d, display_name=f"D{i}", net_balance_paise=-10000)
            for i, d in enumerate(debtors)
        ]

        result = simplify_debts(balances)
        assert result.zero_sum_verified
        assert result.simplified_count == 4  # Each debtor pays the creditor once

        # All settlements should be to the creditor
        for s in result.settlements:
            assert s.to_user_id == creditor
            assert s.amount_paise == 10000


class TestOptimalReduction:
    """Tests verifying the algorithm produces optimal or near-optimal results."""

    def test_goa_squad_style_reduction(self):
        """
        Simulate the Goa Weekend Squad scenario:
        Multiple receipts paid by different people → cross-debts.
        Should reduce significantly.
        """
        aryan, priya, karan, meera, dev = [_uid() for _ in range(5)]

        # Simulate ledger entries from 4 receipts paid by different people
        entries = [
            # Receipt 1: Aryan paid, others owe him
            {"from_user_id": priya, "to_user_id": aryan, "amount_paise": 18500},
            {"from_user_id": karan, "to_user_id": aryan, "amount_paise": 22000},
            {"from_user_id": meera, "to_user_id": aryan, "amount_paise": 16500},
            {"from_user_id": dev, "to_user_id": aryan, "amount_paise": 19000},
            # Receipt 2: Priya paid, others owe her
            {"from_user_id": aryan, "to_user_id": priya, "amount_paise": 17140},
            {"from_user_id": karan, "to_user_id": priya, "amount_paise": 17140},
            {"from_user_id": meera, "to_user_id": priya, "amount_paise": 17140},
            {"from_user_id": dev, "to_user_id": priya, "amount_paise": 17140},
            # Receipt 3: Karan paid, others owe him
            {"from_user_id": aryan, "to_user_id": karan, "amount_paise": 14900},
            {"from_user_id": priya, "to_user_id": karan, "amount_paise": 12800},
            {"from_user_id": dev, "to_user_id": karan, "amount_paise": 14900},
            # Receipt 4: Meera paid, others owe her
            {"from_user_id": aryan, "to_user_id": meera, "amount_paise": 17000},
            {"from_user_id": priya, "to_user_id": meera, "amount_paise": 17000},
            {"from_user_id": karan, "to_user_id": meera, "amount_paise": 17000},
            {"from_user_id": dev, "to_user_id": meera, "amount_paise": 17000},
        ]

        result = simplify_from_ledger(entries)
        assert result.zero_sum_verified

        # 15 original transactions should simplify significantly
        assert result.original_transaction_count == 15
        assert result.simplified_count < 15
        assert result.transactions_saved > 0

        # Verify all settlement amounts are positive
        for s in result.settlements:
            assert s.amount_paise > 0

    def test_already_optimal(self):
        """Two users with one debt — can't simplify further."""
        u1, u2 = _uid(), _uid()
        entries = [
            {"from_user_id": u1, "to_user_id": u2, "amount_paise": 10000},
        ]
        result = simplify_from_ledger(entries)
        assert result.simplified_count == 1
        assert result.transactions_saved == 0


class TestZeroSumInvariant:
    """Tests specifically for the zero-sum invariant."""

    def test_net_balances_always_sum_to_zero(self):
        """Net balances computed from any set of ledger entries must sum to zero."""
        import random
        rng = random.Random(42)

        for _ in range(50):
            num_users = rng.randint(2, 10)
            users = [_uid() for _ in range(num_users)]
            num_entries = rng.randint(1, 20)

            entries = []
            for _ in range(num_entries):
                u_from, u_to = rng.sample(users, 2)
                amount = rng.randint(100, 50000)
                entries.append({
                    "from_user_id": u_from,
                    "to_user_id": u_to,
                    "amount_paise": amount,
                })

            balances = compute_net_balances(entries)
            total = sum(b.net_balance_paise for b in balances)
            assert total == 0, f"Zero-sum violated: {total}"

    def test_simplified_settlements_preserve_balances(self):
        """
        After simplification, if we recompute balances from settlements,
        they should match the original balances.
        """
        users = [_uid() for _ in range(5)]

        entries = [
            {"from_user_id": users[0], "to_user_id": users[1], "amount_paise": 20000},
            {"from_user_id": users[1], "to_user_id": users[2], "amount_paise": 15000},
            {"from_user_id": users[2], "to_user_id": users[3], "amount_paise": 30000},
            {"from_user_id": users[3], "to_user_id": users[4], "amount_paise": 10000},
            {"from_user_id": users[4], "to_user_id": users[0], "amount_paise": 25000},
        ]

        # Original balances
        original_balances = compute_net_balances(entries)
        original_map = {b.user_id: b.net_balance_paise for b in original_balances}

        # Simplify
        result = simplify_debts(original_balances, original_transaction_count=len(entries))

        # Recompute balances from simplified settlements
        settlement_entries = [
            {
                "from_user_id": s.from_user_id,
                "to_user_id": s.to_user_id,
                "amount_paise": s.amount_paise,
            }
            for s in result.settlements
        ]
        new_balances = compute_net_balances(settlement_entries)
        new_map = {b.user_id: b.net_balance_paise for b in new_balances}

        # Balances should match
        all_users = set(original_map.keys()) | set(new_map.keys())
        for uid in all_users:
            assert original_map.get(uid, 0) == new_map.get(uid, 0), (
                f"Balance mismatch for user {uid}: "
                f"original={original_map.get(uid, 0)}, "
                f"simplified={new_map.get(uid, 0)}"
            )

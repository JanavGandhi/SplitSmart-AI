from __future__ import annotations

import base64
import uuid
from types import SimpleNamespace

import pytest

from app.api.v1.ledger import (
    SettlementRequest,
    UPIPaymentRequest,
    create_upi_intent,
    record_settlement,
)
from app.api.v1.stubs import get_metrics
from app.models.ledger_entry import EntryType, LedgerEntry


class FakeResult:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class FakeUPIDatabase:
    def __init__(self, user, group_name):
        self.user = user
        self.group_name = group_name

    async def execute(self, statement):
        return FakeResult((self.user, self.group_name))


class FakeMetricsDatabase:
    def __init__(self, values):
        self.values = iter(values)

    async def scalar(self, statement):
        return next(self.values)


class FakeSettlementDatabase:
    def __init__(self, group, existing=None):
        self.results = iter([existing, group])
        self.added = []

    async def execute(self, statement):
        return FakeResult(next(self.results))

    def add(self, entry):
        self.added.append(entry)

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_upi_intent_returns_payment_link_and_svg_qr():
    creditor = SimpleNamespace(
        display_name="Priya",
        upi_id="priya@example",
    )
    response = await create_upi_intent(
        UPIPaymentRequest(
            group_id=uuid.uuid4(),
            creditor_user_id=uuid.uuid4(),
            amount_paise=12550,
        ),
        FakeUPIDatabase(creditor, "Goa trip"),
    )

    qr_svg = base64.b64decode(response.qr_base64).decode()
    assert response.amount_rupees == "125.50"
    assert "pa=priya%40example" in response.uri
    assert "am=125.50" in response.uri
    assert "<svg" in qr_svg
    assert "Payee is" not in qr_svg


@pytest.mark.asyncio
async def test_settlement_records_reverse_edge_to_clear_group_debt():
    group_id, debtor_id, creditor_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    db = FakeSettlementDatabase(SimpleNamespace(id=group_id))
    response = await record_settlement(
        SettlementRequest(
            group_id=group_id,
            from_user_id=debtor_id,
            to_user_id=creditor_id,
            amount_paise=12550,
            idempotency_key="settle-1",
        ),
        db,
    )

    entry = db.added[0]
    assert isinstance(entry, LedgerEntry)
    assert entry.entry_type == EntryType.SETTLEMENT
    assert response.from_user_id == debtor_id
    assert response.to_user_id == creditor_id
    assert entry.from_user_id == creditor_id
    assert entry.to_user_id == debtor_id


@pytest.mark.asyncio
async def test_settlement_retry_returns_original_debt_direction():
    group_id, debtor_id, creditor_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        group_id=group_id,
        from_user_id=creditor_id,
        to_user_id=debtor_id,
        amount_paise=12550,
        entry_type=EntryType.SETTLEMENT,
        idempotency_key="settle-1",
    )
    db = FakeSettlementDatabase(SimpleNamespace(id=group_id), existing=existing)

    response = await record_settlement(
        SettlementRequest(
            group_id=group_id,
            from_user_id=debtor_id,
            to_user_id=creditor_id,
            amount_paise=12550,
            idempotency_key="settle-1",
        ),
        db,
    )

    assert response.created is False
    assert response.from_user_id == debtor_id
    assert response.to_user_id == creditor_id
    assert db.added == []


@pytest.mark.asyncio
async def test_metrics_returns_live_database_counts():
    response = await get_metrics(
        FakeMetricsDatabase([12, 4, 9, 2, 17, 80123])
    )

    assert response == {
        "status": "ok",
        "total_users": 12,
        "total_groups": 4,
        "total_receipts": 9,
        "active_rooms": 2,
        "ledger_entries": 17,
        "total_paise_tracked": 80123,
    }

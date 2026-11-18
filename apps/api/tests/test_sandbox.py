from app.models.ledger_entry import LedgerEntry
from app.models.receipt import Receipt
from app.services.sandbox import _sandbox_idempotency_key


def test_sandbox_idempotency_keys_fit_database_columns():
    key = _sandbox_idempotency_key()
    receipt_key_limit = Receipt.__table__.c.idempotency_key.type.length
    ledger_key_limit = LedgerEntry.__table__.c.idempotency_key.type.length

    assert len(key) <= min(receipt_key_limit, ledger_key_limit)

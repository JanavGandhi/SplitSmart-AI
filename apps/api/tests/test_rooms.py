from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models.group_member import GroupMember
from app.models.item_claim import ItemClaim
from app.models.ledger_entry import LedgerEntry
from app.models.receipt import Receipt, ReceiptStatus
from app.models.receipt_line_item import ReceiptLineItem


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        if isinstance(self.value, list):
            return self.value[0] if self.value else None
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value if isinstance(self.value, list) else [self.value]


class FakeRoomDB:
    def __init__(self, receipt=None, line_items=None, member=None):
        self.receipt = receipt
        self.line_items = line_items or []
        self.member = member
        self.member_ids = []
        self.claims = []
        self.added = []
        self.deleted = []

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Receipt:
            return FakeResult(self.receipt)
        if entity is GroupMember:
            if statement.column_descriptions[0]["expr"] is GroupMember.user_id:
                return FakeResult(self.member_ids)
            return FakeResult(self.member)
        if entity is ReceiptLineItem:
            return FakeResult(self.line_items)
        if entity is ItemClaim:
            parameters = statement.compile().params
            user_id = next(
                (value for name, value in parameters.items() if "user_id" in name),
                None,
            )
            if user_id is not None:
                line_item_id = next(
                    (value for name, value in parameters.items() if "line_item_id" in name),
                    None,
                )
                return FakeResult(
                    next(
                        (
                            claim for claim in self.claims
                            if claim.user_id == user_id
                            and claim.line_item_id == line_item_id
                        ),
                        None,
                    )
                )
            return FakeResult(self.claims)
        raise AssertionError(f"Unexpected query: {statement}")

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, ItemClaim):
            self.claims.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)
        if isinstance(obj, ItemClaim):
            self.claims.remove(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def rollback(self):
        pass


class FakePubSub:
    def __init__(self, broker):
        self.broker = broker
        self.queues = []

    async def subscribe(self, channel):
        queue = asyncio.Queue()
        self.queues.append((channel, queue))
        self.broker[channel].append(queue)

    async def unsubscribe(self, channel):
        self.broker[channel] = [
            queue for subscribed_channel, queue in self.queues
            if subscribed_channel != channel
        ]

    async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
        for channel, queue in self.queues:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=timeout)
                return {"type": "message", "channel": channel, "data": data}
            except TimeoutError:
                return None
        return None


class FakeRedis:
    def __init__(self, broker):
        self.broker = broker

    def pubsub(self):
        return FakePubSub(self.broker)

    async def publish(self, channel, data):
        queues = self.broker[channel]
        for queue in list(queues):
            await queue.put(data)
        return len(queues)

    async def aclose(self):
        pass


@pytest.fixture
def room_receipt():
    return SimpleNamespace(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        room_code="TESTROOM",
        status=ReceiptStatus.READY_FOR_CLAIMS,
        subtotal_paise=1000,
        tax_paise=100,
        service_charge_paise=0,
        delivery_fee_paise=0,
        discount_paise=0,
        total_paise=1100,
        paid_by=None,
        finalize_idempotency_key=None,
    )


@pytest.fixture
def room_db(room_receipt):
    return FakeRoomDB(receipt=room_receipt)


@pytest.fixture
def room_client(room_db):
    async def override_get_db():
        yield room_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _room_token(user_id: uuid.UUID, room_code: str, display_name: str = "Alex") -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": str(user_id),
            "room_code": room_code,
            "scope": "room:join",
            "display_name": display_name,
            "avatar_color": "#6366f1",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def test_guest_join_returns_room_scoped_token(room_client, room_db):
    response = room_client.post(
        "/api/v1/rooms/TESTROOM/guest-join",
        json={"display_name": "  Alex  "},
    )

    assert response.status_code == 201
    body = response.json()
    claims = jwt.decode(
        body["access_token"],
        get_settings().jwt_secret_key,
        algorithms=[get_settings().jwt_algorithm],
    )
    assert claims["room_code"] == "TESTROOM"
    assert claims["scope"] == "room:join"
    assert claims["sub"] == body["user"]["id"]
    assert body["user"]["display_name"] == "Alex"
    assert any(isinstance(item, GroupMember) for item in room_db.added)


def test_room_split_recalculates_claims_and_preserves_receipt_total(
    room_receipt,
):
    from app.api.v1.rooms import calculate_room_split

    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    item_a = SimpleNamespace(id=uuid.uuid4(), total_price_paise=1000)
    item_b = SimpleNamespace(id=uuid.uuid4(), total_price_paise=0)
    claims = [
        SimpleNamespace(
            line_item_id=item_a.id,
            user_id=user_a,
            share_fraction_numerator=1,
            share_fraction_denominator=1,
            calculated_item_paise=0,
            calculated_tax_and_fees_paise=0,
            calculated_final_paise=0,
        ),
        SimpleNamespace(
            line_item_id=item_a.id,
            user_id=user_b,
            share_fraction_numerator=1,
            share_fraction_denominator=1,
            calculated_item_paise=0,
            calculated_tax_and_fees_paise=0,
            calculated_final_paise=0,
        ),
        SimpleNamespace(
            line_item_id=item_b.id,
            user_id=user_b,
            share_fraction_numerator=1,
            share_fraction_denominator=1,
            calculated_item_paise=0,
            calculated_tax_and_fees_paise=0,
            calculated_final_paise=0,
        ),
    ]

    result = calculate_room_split(room_receipt, [item_a, item_b], claims)

    assert result.invariant_holds
    assert result.total_distributed_paise == room_receipt.total_paise
    assert sum(claim.calculated_final_paise for claim in claims) == 1100
    assert claims[0].calculated_item_paise == 500
    assert claims[1].calculated_item_paise == 500
    assert claims[0].calculated_final_paise == 550
    assert claims[1].calculated_final_paise == 550
    assert claims[2].calculated_item_paise == 0


def test_two_websocket_clients_receive_each_others_join_events(
    room_client, room_db, monkeypatch
):
    broker = defaultdict(list)

    def fake_from_url(*args, **kwargs):
        return FakeRedis(broker)

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)
    group_member = SimpleNamespace(group_id=room_db.receipt.group_id)
    room_db.member = group_member
    user_one, user_two = uuid.uuid4(), uuid.uuid4()

    with room_client.websocket_connect(
        f"/api/v1/rooms/TESTROOM/ws?token={_room_token(user_one, 'TESTROOM', 'Alex')}"
    ) as first:
        first_join = first.receive_json()
        assert first_join["event"] == "PARTICIPANT_JOINED"

        with room_client.websocket_connect(
            f"/api/v1/rooms/TESTROOM/ws?token={_room_token(user_two, 'TESTROOM', 'Sam')}"
        ) as second:
            first_seen = first.receive_json()
            second_seen = second.receive_json()
            assert first_seen["event"] == "PARTICIPANT_JOINED"
            assert second_seen["event"] == "PARTICIPANT_JOINED"
            assert first_seen["user_id"] == str(user_two)
            assert second_seen["user_id"] == str(user_two)


def test_websocket_claim_toggle_broadcasts_recalculated_totals(
    room_client, room_db, monkeypatch
):
    broker = defaultdict(list)
    monkeypatch.setattr(
        "redis.asyncio.from_url",
        lambda *args, **kwargs: FakeRedis(broker),
    )
    user_id = uuid.uuid4()
    room_db.member = SimpleNamespace(group_id=room_db.receipt.group_id)
    item = SimpleNamespace(
        id=uuid.uuid4(),
        receipt_id=room_db.receipt.id,
        total_price_paise=1000,
    )
    room_db.line_items = [item]
    token = _room_token(user_id, "TESTROOM")

    with room_client.websocket_connect(
        f"/api/v1/rooms/TESTROOM/ws?token={token}"
    ) as socket:
        assert socket.receive_json()["event"] == "PARTICIPANT_JOINED"
        socket.send_json({"event": "ITEM_CLAIM_TOGGLED", "item_id": str(item.id)})
        claim_event = socket.receive_json()
        totals_event = socket.receive_json()

    assert claim_event["event"] == "ITEM_CLAIM_TOGGLED"
    assert claim_event["action"] == "claimed"
    assert totals_event["event"] == "TAX_RECALCULATED"
    assert totals_event["per_user_totals"] == {str(user_id): 1100}
    assert room_db.claims[0].calculated_final_paise == 1100


def test_second_guest_toggle_recalculates_shared_item(
    room_client, room_db, monkeypatch
):
    broker = defaultdict(list)
    monkeypatch.setattr(
        "redis.asyncio.from_url",
        lambda *args, **kwargs: FakeRedis(broker),
    )
    room_db.member = SimpleNamespace(group_id=room_db.receipt.group_id)
    item = SimpleNamespace(
        id=uuid.uuid4(),
        receipt_id=room_db.receipt.id,
        total_price_paise=1000,
    )
    room_db.line_items = [item]
    user_one, user_two = uuid.uuid4(), uuid.uuid4()

    with room_client.websocket_connect(
        f"/api/v1/rooms/TESTROOM/ws?token={_room_token(user_one, 'TESTROOM', 'Alex')}"
    ) as first:
        assert first.receive_json()["event"] == "PARTICIPANT_JOINED"
        first.send_json({"event": "ITEM_CLAIM_TOGGLED", "item_id": str(item.id)})
        first.receive_json()
        assert first.receive_json()["per_user_totals"] == {str(user_one): 1100}

        with room_client.websocket_connect(
            f"/api/v1/rooms/TESTROOM/ws?token={_room_token(user_two, 'TESTROOM', 'Sam')}"
        ) as second:
            assert first.receive_json()["user_id"] == str(user_two)
            assert second.receive_json()["user_id"] == str(user_two)
            second.send_json({"event": "ITEM_CLAIM_TOGGLED", "item_id": str(item.id)})

            first.receive_json()
            first_totals = first.receive_json()["per_user_totals"]
            second.receive_json()
            second_totals = second.receive_json()["per_user_totals"]

    expected = {str(user_one): 550, str(user_two): 550}
    assert first_totals == expected
    assert second_totals == expected


def test_finalize_is_atomic_and_idempotent(room_client, room_db, monkeypatch):
    broker = defaultdict(list)
    monkeypatch.setattr(
        "redis.asyncio.from_url",
        lambda *args, **kwargs: FakeRedis(broker),
    )
    payer_id, claimant_id = uuid.uuid4(), uuid.uuid4()
    actor_id = payer_id
    item = SimpleNamespace(
        id=uuid.uuid4(),
        receipt_id=room_db.receipt.id,
        total_price_paise=1000,
    )
    claim = SimpleNamespace(
        line_item_id=item.id,
        user_id=claimant_id,
        share_fraction_numerator=1,
        share_fraction_denominator=1,
        calculated_item_paise=1000,
        calculated_tax_and_fees_paise=100,
        calculated_final_paise=1100,
    )
    room_db.line_items = [item]
    room_db.claims = [claim]
    room_db.member_ids = [payer_id, claimant_id]
    token = _room_token(actor_id, "TESTROOM")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "payer_user_id": str(payer_id),
        "idempotency_key": "finalize-request-1",
    }

    first = room_client.post(
        "/api/v1/rooms/TESTROOM/finalize",
        json=payload,
        headers=headers,
    )
    second = room_client.post(
        "/api/v1/rooms/TESTROOM/finalize",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["created"] is True
    assert first.json()["settlements"] == [
        {
            "from_user_id": str(claimant_id),
            "to_user_id": str(payer_id),
            "amount_paise": 1100,
        }
    ]
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert room_db.receipt.status == ReceiptStatus.LOCKED
    assert len([item for item in room_db.added if isinstance(item, LedgerEntry)]) == 1


def test_finalize_requires_a_room_scoped_guest_token(room_client, room_db):
    response = room_client.post(
        "/api/v1/rooms/TESTROOM/finalize",
        json={
            "payer_user_id": str(uuid.uuid4()),
            "idempotency_key": "finalize-request-1",
        },
    )

    assert response.status_code == 401


def test_simulate_friends_broadcasts_three_participants(
    room_client, room_db, monkeypatch
):
    broker = defaultdict(list)
    monkeypatch.setattr(
        "redis.asyncio.from_url",
        lambda *args, **kwargs: FakeRedis(broker),
    )
    monkeypatch.setattr("app.api.v1.rooms.asyncio.sleep", AsyncMock())
    room_db.member = SimpleNamespace(group_id=room_db.receipt.group_id)
    token = _room_token(uuid.uuid4(), "TESTROOM")

    with room_client.websocket_connect(
        f"/api/v1/rooms/TESTROOM/ws?token={token}"
    ) as socket:
        assert socket.receive_json()["event"] == "PARTICIPANT_JOINED"
        socket.send_json({"event": "SIMULATE_FRIENDS"})
        simulated = [socket.receive_json() for _ in range(3)]

    assert all(event["event"] == "PARTICIPANT_JOINED" for event in simulated)
    assert [event["display_name"] for event in simulated] == [
        "Roommate 1",
        "Roommate 2",
        "Roommate 3",
    ]

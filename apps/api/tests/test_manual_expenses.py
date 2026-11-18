import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.expenses import create_manual_expense
from app.api.v1.groups import add_group_member
from app.models.ledger_entry import EntryType, LedgerEntry
from app.models.manual_expense import ExpenseParticipant
from app.schemas.expense import ManualExpenseCreate
from app.schemas.group import GroupMemberCreate


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class FakeDatabase:
    def __init__(self, results):
        self.results = iter(results)
        self.added = []

    async def execute(self, statement):
        return next(self.results)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_manual_expense_splits_exact_paise_and_creates_debts():
    group_id, payer_id, second_id, third_id = (uuid.uuid4() for _ in range(4))
    memberships = [
        SimpleNamespace(user_id=user_id)
        for user_id in (payer_id, second_id, third_id)
    ]
    db = FakeDatabase([FakeResult(group_id), FakeResult(memberships)])

    response = await create_manual_expense(
        group_id,
        ManualExpenseCreate(
            description="Dinner",
            amount_paise=1000,
            paid_by_user_id=payer_id,
            participant_user_ids=[payer_id, second_id, third_id],
        ),
        db,
    )

    shares = [item.share_paise for item in db.added if isinstance(item, ExpenseParticipant)]
    debts = [item for item in db.added if isinstance(item, LedgerEntry)]
    assert shares == [334, 333, 333]
    assert sum(shares) == 1000
    assert [(debt.from_user_id, debt.amount_paise) for debt in debts] == [
        (second_id, 333),
        (third_id, 333),
    ]
    assert all(debt.to_user_id == payer_id for debt in debts)
    assert all(debt.entry_type == EntryType.EXPENSE_SHARE for debt in debts)
    assert sum(participant.share_paise for participant in response.participants) == 1000


@pytest.mark.asyncio
async def test_manual_expense_is_fully_owed_when_payer_is_not_a_participant():
    group_id, payer_id, second_id, third_id = (uuid.uuid4() for _ in range(4))
    memberships = [
        SimpleNamespace(user_id=user_id)
        for user_id in (payer_id, second_id, third_id)
    ]
    db = FakeDatabase([FakeResult(group_id), FakeResult(memberships)])

    response = await create_manual_expense(
        group_id,
        ManualExpenseCreate(
            description="Shared taxi",
            amount_paise=1001,
            paid_by_user_id=payer_id,
            participant_user_ids=[second_id, third_id],
        ),
        db,
    )

    debts = [item for item in db.added if isinstance(item, LedgerEntry)]
    assert [share.share_paise for share in response.participants] == [501, 500]
    assert sum(debt.amount_paise for debt in debts) == 1001
    assert all(debt.to_user_id == payer_id for debt in debts)


@pytest.mark.asyncio
async def test_manual_expense_rejects_nonmember_participants():
    group_id, payer_id, outsider_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    memberships = [SimpleNamespace(user_id=payer_id)]
    db = FakeDatabase([FakeResult(group_id), FakeResult(memberships)])

    with pytest.raises(HTTPException) as error:
        await create_manual_expense(
            group_id,
            ManualExpenseCreate(
                description="Taxi",
                amount_paise=500,
                paid_by_user_id=payer_id,
                participant_user_ids=[outsider_id],
            ),
            db,
        )

    assert error.value.status_code == 422
    assert db.added == []


@pytest.mark.asyncio
async def test_group_member_can_be_added_by_name():
    group_id = uuid.uuid4()
    db = FakeDatabase([FakeResult(group_id)])

    response = await add_group_member(
        group_id,
        GroupMemberCreate(display_name="  Priya  ", upi_id="priya@bank"),
        db,
    )

    assert response.user.display_name == "Priya"
    assert response.user.is_guest is True
    assert response.joined_at is not None
    assert len(db.added) == 2

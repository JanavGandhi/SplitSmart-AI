from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import copilot
from app.api.v1.copilot import CopilotChatRequest, chat
from app.main import app
from app.services import ai_copilot
from app.services.rate_limiter import enforce_ai_rate_limit


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def all(self):
        return self.value


class FakeDatabase:
    def __init__(self, results):
        self.results = iter(results)

    async def execute(self, statement):
        return next(self.results)


@pytest.mark.asyncio
async def test_chat_sends_only_group_summary_to_configured_provider(monkeypatch):
    group_id = uuid.uuid4()
    debtor_id, creditor_id = uuid.uuid4(), uuid.uuid4()
    db = FakeDatabase(
        [
            FakeResult(SimpleNamespace(name="Weekend trip", currency="INR")),
            FakeResult([(debtor_id, "Karan"), (creditor_id, "Priya")]),
            FakeResult([(debtor_id, creditor_id, 12550)]),
            FakeResult([("Cafe", SimpleNamespace(value="READY_FOR_CLAIMS"), 12550)]),
        ]
    )
    monkeypatch.setattr(
        copilot,
        "get_settings",
        lambda: SimpleNamespace(groq_api_key="configured-key"),
    )
    captured = {}

    async def fake_to_thread(function, message, context, api_key):
        captured.update(message=message, context=context, api_key=api_key)
        return "Karan owes Priya ₹125.50."

    monkeypatch.setattr(copilot.asyncio, "to_thread", fake_to_thread)

    response = await chat(
        CopilotChatRequest(message="Who owes whom?", group_id=group_id),
        db,
    )

    assert response.reply == "Karan owes Priya ₹125.50."
    assert captured["api_key"] == "configured-key"
    assert captured["context"]["members"] == [
        {
            "name": "Karan",
            "net_balance_paise": -12550,
            "position": "debtor",
        },
        {
            "name": "Priya",
            "net_balance_paise": 12550,
            "position": "creditor",
        },
    ]
    assert captured["context"]["recent_receipts"] == [
        {
            "merchant": "Cafe",
            "status": "READY_FOR_CLAIMS",
            "total_paise": 12550,
        }
    ]


@pytest.mark.asyncio
async def test_chat_requires_groq_configuration(monkeypatch):
    class UnusedDatabase:
        async def execute(self, statement):
            raise AssertionError("database should not be queried without a provider key")

    monkeypatch.setattr(
        copilot,
        "get_settings",
        lambda: SimpleNamespace(groq_api_key=""),
    )
    with pytest.raises(HTTPException) as error:
        await chat(
            CopilotChatRequest(message="Summarize this group", group_id=uuid.uuid4()),
            UnusedDatabase(),
        )

    assert error.value.status_code == 503
    assert "GROQ_API_KEY" in error.value.detail


@pytest.mark.asyncio
async def test_chat_returns_not_found_for_unknown_group(monkeypatch):
    monkeypatch.setattr(
        copilot,
        "get_settings",
        lambda: SimpleNamespace(groq_api_key="configured-key"),
    )

    with pytest.raises(HTTPException) as error:
        await chat(
            CopilotChatRequest(message="Summarize this group", group_id=uuid.uuid4()),
            FakeDatabase([FakeResult(None)]),
        )

    assert error.value.status_code == 404


def test_chat_route_is_mounted_with_ai_rate_limit():
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/copilot/chat"
    )

    assert "POST" in route.methods
    assert any(
        dependency.call is enforce_ai_rate_limit
        for dependency in route.dependant.dependencies
    )


def test_groq_provider_receives_group_summary_and_returns_text(monkeypatch):
    observed = {}

    class FakeCompletions:
        def create(self, **kwargs):
            observed.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="  Group summary  "))]
            )

    class FakeGroq:
        def __init__(self, api_key):
            observed["api_key"] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(ai_copilot, "Groq", FakeGroq)

    reply = ai_copilot.generate_reply(
        "Summarize",
        {"group_name": "Trip", "members": [{"name": "Priya", "net_balance_paise": 2500}]},
        "configured-key",
    )

    assert reply == "Group summary"
    assert observed["api_key"] == "configured-key"
    assert observed["model"] == "openai/gpt-oss-120b"
    assert '"group_name": "Trip"' in observed["messages"][0]["content"]
    assert observed["max_completion_tokens"] == 400

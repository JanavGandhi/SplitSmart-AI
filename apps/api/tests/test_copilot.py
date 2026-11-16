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
        lambda: SimpleNamespace(gemini_api_key="configured-key"),
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
async def test_chat_requires_gemini_configuration(monkeypatch):
    class UnusedDatabase:
        async def execute(self, statement):
            raise AssertionError("database should not be queried without a provider key")

    monkeypatch.setattr(
        copilot,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key=""),
    )
    with pytest.raises(HTTPException) as error:
        await chat(
            CopilotChatRequest(message="Summarize this group", group_id=uuid.uuid4()),
            UnusedDatabase(),
        )

    assert error.value.status_code == 503
    assert "GEMINI_API_KEY" in error.value.detail


@pytest.mark.asyncio
async def test_chat_returns_not_found_for_unknown_group(monkeypatch):
    monkeypatch.setattr(
        copilot,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key="configured-key"),
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


def test_gemini_provider_receives_group_summary_and_returns_text(monkeypatch):
    observed = {}

    class FakeModel:
        def generate_content(self, prompt, generation_config):
            observed["prompt"] = prompt
            observed["generation_config"] = generation_config
            return SimpleNamespace(text="  Group summary  ")

    monkeypatch.setattr(ai_copilot.genai, "configure", lambda **kwargs: observed.update(kwargs))
    monkeypatch.setattr(ai_copilot.genai, "GenerativeModel", lambda model: FakeModel())

    reply = ai_copilot.generate_reply(
        "Summarize",
        {"group_name": "Trip", "members": [{"name": "Priya", "net_balance_paise": 2500}]},
        "configured-key",
    )

    assert reply == "Group summary"
    assert observed["api_key"] == "configured-key"
    assert '"group_name": "Trip"' in observed["prompt"]
    assert observed["generation_config"]["max_output_tokens"] == 400

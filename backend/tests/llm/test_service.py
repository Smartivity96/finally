"""Tests for chat orchestration: action execution, failures, persistence, routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.llm import router, service
from app.llm.client import LLMError
from app.llm.schema import ChatResponse


def make_response(**kwargs) -> ChatResponse:
    return ChatResponse.model_validate({"message": "ok", **kwargs})


class TestExecuteActions:
    async def test_watchlist_before_trades(self, fakes):
        parsed = make_response(
            trades=[{"ticker": "pypl", "side": "buy", "quantity": 2}],
            watchlist_changes=[{"ticker": "pypl", "action": "add"}],
        )
        result = await service.execute_actions(parsed, None, None)
        assert fakes.calls == [("add", "PYPL"), ("trade", "PYPL", "buy", 2), ("sync", "PYPL")]
        assert result["trades"] == [
            {"ticker": "PYPL", "side": "buy", "quantity": 2, "price": 100.0, "status": "executed"}
        ]
        assert result["watchlist_changes"] == [
            {"ticker": "PYPL", "action": "add", "status": "executed"}
        ]

    async def test_failures_captured_and_others_continue(self, fakes):
        parsed = make_response(
            trades=[
                {"ticker": "FAIL", "side": "buy", "quantity": 1000},
                {"ticker": "AAPL", "side": "sell", "quantity": 1},
            ],
            watchlist_changes=[
                {"ticker": "DUP", "action": "add"},
                {"ticker": "TSLA", "action": "remove"},
            ],
        )
        result = await service.execute_actions(parsed, None, None)
        fail, ok = result["trades"]
        assert fail == {
            "ticker": "FAIL",
            "side": "buy",
            "quantity": 1000,
            "price": None,
            "status": "failed",
            "error": "Insufficient cash",
        }
        assert ok["status"] == "executed"
        dup, removed = result["watchlist_changes"]
        assert dup["status"] == "failed" and "already" in dup["error"]
        assert removed == {"ticker": "TSLA", "action": "remove", "status": "executed"}


class TestHandleChat:
    async def test_mock_mode_executes_and_stores(self, fakes, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        result = await service.handle_chat("buy please", None, None)
        assert result["message"] == "Mock: buying 1 AAPL."
        assert result["trades"][0]["status"] == "executed"
        assert fakes.calls == [("trade", "AAPL", "buy", 1), ("sync", "AAPL")]
        user, assistant = fakes.db.messages
        assert user["role"] == "user" and user["content"] == "buy please"
        assert user["actions"] is None
        assert assistant["role"] == "assistant"
        assert assistant["actions"] == {
            "trades": result["trades"],
            "watchlist_changes": [],
        }

    async def test_llm_failure_is_friendly_and_executes_nothing(self, fakes, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "false")

        async def fail(messages):
            raise LLMError("bad json")

        monkeypatch.setattr(service, "call_llm", fail)
        result = await service.handle_chat("buy 5 NVDA", None, None)
        assert result == {
            "message": service.FAILURE_MESSAGE,
            "trades": [],
            "watchlist_changes": [],
        }
        assert fakes.calls == []
        assert len(fakes.db.messages) == 2

    async def test_missing_api_key_is_friendly(self, fakes, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "false")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = await service.handle_chat("hi", None, None)
        assert result["message"] == service.FAILURE_MESSAGE

    async def test_prompt_contains_context_and_history(self, fakes, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "false")
        fakes.db.insert_chat_message(None, "user", "earlier question")
        fakes.db.insert_chat_message(None, "assistant", "earlier answer", {"trades": []})
        captured = {}

        async def fake_llm(messages):
            captured["messages"] = messages
            return make_response(message="analysis")

        monkeypatch.setattr(service, "call_llm", fake_llm)
        result = await service.handle_chat("how am I doing?", None, None)
        assert result["message"] == "analysis"
        msgs = captured["messages"]
        assert "FinAlly" in msgs[0]["content"]
        assert "10000.0" in msgs[1]["content"] and "AAPL" in msgs[1]["content"]
        assert msgs[2:] == [
            {"role": "user", "content": "earlier question"},
            {"role": "assistant", "content": "earlier answer"},
            {"role": "user", "content": "how am I doing?"},
        ]

    async def test_history_limited_to_20(self, fakes, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "false")
        for i in range(30):
            fakes.db.insert_chat_message(None, "user", f"m{i}")
        captured = {}

        async def fake_llm(messages):
            captured["messages"] = messages
            return make_response()

        monkeypatch.setattr(service, "call_llm", fake_llm)
        await service.handle_chat("now", None, None)
        assert len(captured["messages"]) == 2 + 20 + 1


@pytest.fixture
def client(fakes):
    app = FastAPI()
    app.include_router(router)
    app.state.price_cache = None
    app.state.market_source = None
    return TestClient(app)


class TestRoutes:
    def test_post_chat(self, client, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        resp = client.post("/api/chat", json={"message": "watch something"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Mock: adding PYPL to your watchlist."
        assert body["watchlist_changes"] == [
            {"ticker": "PYPL", "action": "add", "status": "executed"}
        ]
        assert body["trades"] == []

    def test_post_empty_message(self, client):
        resp = client.post("/api/chat", json={"message": "   "})
        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_history(self, client, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        client.post("/api/chat", json={"message": "hello"})
        resp = client.get("/api/chat/history")
        assert resp.status_code == 200
        body = resp.json()
        assert [m["role"] for m in body] == ["user", "assistant"]
        assert set(body[0]) == {"role", "content", "actions", "created_at"}
        assert body[1]["actions"] == {"trades": [], "watchlist_changes": []}

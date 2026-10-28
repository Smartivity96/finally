"""Tests for schema parsing, mock mode and the LLM call wrapper."""

import json

import pytest

from app.llm import client
from app.llm.client import LLMError, call_llm, mock_response, parse_response


class TestParseResponse:
    def test_full_response(self):
        raw = json.dumps(
            {
                "message": "Bought.",
                "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 2.5}],
                "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
            }
        )
        parsed = parse_response(raw)
        assert parsed.message == "Bought."
        assert parsed.trades[0].ticker == "AAPL"
        assert parsed.trades[0].quantity == 2.5
        assert parsed.watchlist_changes[0].action == "add"

    def test_missing_optional_lists(self):
        parsed = parse_response('{"message": "hello"}')
        assert parsed.trades == []
        assert parsed.watchlist_changes == []

    @pytest.mark.parametrize(
        "raw",
        [
            None,
            "",
            "{not json",
            '{"trades": []}',  # missing message
            '{"message": "x", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 1}]}',
            '{"message": "x", "watchlist_changes": [{"ticker": "AAPL", "action": "pin"}]}',
        ],
    )
    def test_malformed(self, raw):
        with pytest.raises(LLMError):
            parse_response(raw)


class TestMockResponse:
    def test_buy(self):
        r = mock_response("Please BUY something")
        assert r.message == "Mock: buying 1 AAPL."
        assert [(t.ticker, t.side, t.quantity) for t in r.trades] == [("AAPL", "buy", 1)]
        assert r.watchlist_changes == []

    def test_sell(self):
        r = mock_response("sell it")
        assert r.message == "Mock: selling 1 AAPL."
        assert [(t.ticker, t.side, t.quantity) for t in r.trades] == [("AAPL", "sell", 1)]

    def test_watch(self):
        r = mock_response("Watch PYPL")
        assert r.message == "Mock: adding PYPL to your watchlist."
        assert [(w.ticker, w.action) for w in r.watchlist_changes] == [("PYPL", "add")]
        assert r.trades == []

    def test_first_match_wins(self):
        assert mock_response("sell then buy").trades[0].side == "buy"

    def test_default(self):
        r = mock_response("hello")
        assert r.message == "Mock: I'm FinAlly, your AI trading assistant."
        assert r.trades == [] and r.watchlist_changes == []


class TestCallLLM:
    async def test_missing_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMError, match="OPENAI_API_KEY"):
            await call_llm([])

    async def test_success(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setattr(client, "_call_sync", lambda m: '{"message": "ok"}')
        assert (await call_llm([])).message == "ok"

    async def test_exception_wrapped(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test")

        def boom(messages):
            raise RuntimeError("network down")

        monkeypatch.setattr(client, "_call_sync", boom)
        with pytest.raises(LLMError, match="network down"):
            await call_llm([])

    async def test_timeout(self, monkeypatch):
        import time

        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setattr(client, "TIMEOUT_SECONDS", 0.05)
        monkeypatch.setattr(client, "_call_sync", lambda m: time.sleep(0.3) or "{}")
        with pytest.raises(LLMError, match="timed out"):
            await call_llm([])

    async def test_bad_json(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setattr(client, "_call_sync", lambda m: "nope")
        with pytest.raises(LLMError):
            await call_llm([])

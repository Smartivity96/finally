"""End-to-end chat flow against the real db and services (tmp DB_PATH, mock LLM)."""

import pytest

from app import db
from app.llm import service
from app.market import PriceCache


class FakeSource:
    def __init__(self):
        self.tickers = set()

    async def add_ticker(self, ticker):
        self.tickers.add(ticker)

    async def remove_ticker(self, ticker):
        self.tickers.discard(ticker)

    def get_tickers(self):
        return list(self.tickers)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LLM_MOCK", "true")
    db.init_db()
    cache = PriceCache()
    cache.update("AAPL", 200.0)
    return cache, FakeSource()


async def test_buy_then_sell_round_trip(env):
    cache, source = env
    result = await service.handle_chat("buy", cache, source)
    assert result["trades"] == [
        {"ticker": "AAPL", "side": "buy", "quantity": 1, "price": 200.0, "status": "executed"}
    ]
    with db.get_connection() as conn:
        assert db.get_cash(conn) == pytest.approx(9800.0)

    result = await service.handle_chat("sell", cache, source)
    assert result["trades"][0]["status"] == "executed"
    with db.get_connection() as conn:
        assert db.get_cash(conn) == pytest.approx(10000.0)

    history = service.get_history()
    assert [m["role"] for m in history] == ["user", "assistant"] * 2
    assert history[1]["actions"]["trades"][0]["price"] == 200.0


async def test_sell_without_position_fails_gracefully(env):
    cache, source = env
    result = await service.handle_chat("sell", cache, source)
    trade = result["trades"][0]
    assert trade["status"] == "failed"
    assert trade["price"] is None
    assert trade["error"]


async def test_watch_adds_pypl(env):
    cache, source = env
    result = await service.handle_chat("watch", cache, source)
    assert result["watchlist_changes"] == [
        {"ticker": "PYPL", "action": "add", "status": "executed"}
    ]
    assert "PYPL" in source.tickers
    # second time: already present -> failed, not an exception
    result = await service.handle_chat("watch", cache, source)
    assert result["watchlist_changes"][0]["status"] == "failed"

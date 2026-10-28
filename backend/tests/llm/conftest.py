"""Fakes for db, portfolio and watchlist services used by chat tests."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app.llm import service


class FakeTradeError(Exception):
    pass


class FakeWatchlistError(Exception):
    pass


class FakeDB:
    def __init__(self):
        self.messages = []

    @contextmanager
    def get_connection(self):
        yield object()

    def get_chat_messages(self, conn, limit=20):
        return self.messages[-limit:]

    def insert_chat_message(self, conn, role, content, actions=None):
        self.messages.append(
            {
                "role": role,
                "content": content,
                "actions": actions,
                "created_at": "2026-10-28T12:00:00+00:00",
            }
        )


@pytest.fixture
def fakes(monkeypatch):
    """Replace service dependencies; records call order in `calls`."""
    calls = []
    fake_db = FakeDB()

    def execute_trade(cache, ticker, side, quantity):
        calls.append(("trade", ticker, side, quantity))
        if ticker == "FAIL":
            raise FakeTradeError("Insufficient cash")
        return {"id": "x", "ticker": ticker, "side": side, "quantity": quantity, "price": 100.0}

    async def add_ticker(source, ticker):
        calls.append(("add", ticker))
        if ticker == "DUP":
            raise FakeWatchlistError("DUP is already in the watchlist")
        return {"ticker": ticker}

    async def remove_ticker(source, cache, ticker):
        calls.append(("remove", ticker))
        return {"ticker": ticker}

    async def sync_tracking(source, ticker):
        calls.append(("sync", ticker))

    portfolio = SimpleNamespace(
        TradeError=FakeTradeError,
        execute_trade=execute_trade,
        sync_tracking=sync_tracking,
        get_portfolio=lambda cache: {"cash_balance": 10000.0, "positions": []},
    )
    watchlist = SimpleNamespace(
        WatchlistError=FakeWatchlistError,
        add_ticker=add_ticker,
        remove_ticker=remove_ticker,
        list_watchlist=lambda cache: [{"ticker": "AAPL", "price": 190.0}],
    )
    monkeypatch.setattr(service, "db", fake_db)
    monkeypatch.setattr(service, "portfolio_service", portfolio)
    monkeypatch.setattr(service, "watchlist_service", watchlist)
    return SimpleNamespace(calls=calls, db=fake_db)

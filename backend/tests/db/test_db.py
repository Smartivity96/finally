"""Tests for the SQLite persistence layer."""

import sqlite3
import threading

import pytest

from app import db
from app.db import DEFAULT_CASH, DEFAULT_TICKERS, get_connection, init_db


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "nested" / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    init_db()
    return path


class TestInit:
    def test_creates_parent_dir_and_file(self, db_path):
        assert db_path.exists()

    def test_creates_all_tables(self, db_path):
        with get_connection() as conn:
            names = {
                r["name"]
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        assert {
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        } <= names

    def test_seeds_default_user_and_watchlist(self, db_path):
        with get_connection() as conn:
            assert db.get_cash(conn) == DEFAULT_CASH
            assert [w["ticker"] for w in db.get_watchlist(conn)] == DEFAULT_TICKERS

    def test_idempotent(self, db_path):
        with get_connection() as conn:
            db.set_cash(conn, 500.0)
            db.add_to_watchlist(conn, "PYPL")
        init_db()
        init_db()
        with get_connection() as conn:
            assert db.get_cash(conn) == 500.0
            assert len(db.get_watchlist(conn)) == len(DEFAULT_TICKERS) + 1

    def test_does_not_reseed_emptied_watchlist_into_duplicates(self, db_path):
        with get_connection() as conn:
            db.remove_from_watchlist(conn, "AAPL")
        init_db()
        with get_connection() as conn:
            tickers = [w["ticker"] for w in db.get_watchlist(conn)]
        assert "AAPL" not in tickers
        assert len(tickers) == len(DEFAULT_TICKERS) - 1

    def test_db_path_read_at_call_time(self, db_path, tmp_path, monkeypatch):
        other = tmp_path / "other.db"
        monkeypatch.setenv("DB_PATH", str(other))
        init_db()
        assert other.exists()


class TestConnection:
    def test_row_factory(self, db_path):
        with get_connection() as conn:
            row = conn.execute("SELECT cash_balance FROM users_profile").fetchone()
            assert isinstance(row, sqlite3.Row)

    def test_commits_on_success(self, db_path):
        with get_connection() as conn:
            db.set_cash(conn, 1234.5)
        with get_connection() as conn:
            assert db.get_cash(conn) == 1234.5

    def test_rolls_back_on_exception(self, db_path):
        with pytest.raises(RuntimeError):
            with get_connection() as conn:
                db.set_cash(conn, 1.0)
                db.insert_trade(conn, "AAPL", "buy", 1, 100.0)
                raise RuntimeError("boom")
        with get_connection() as conn:
            assert db.get_cash(conn) == DEFAULT_CASH
            assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 0

    def test_closes_connection(self, db_path):
        with get_connection() as conn:
            pass
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_concurrent_writers_wait(self, db_path):
        errors = []

        def worker():
            try:
                for _ in range(20):
                    with get_connection() as conn:
                        db.set_cash(conn, db.get_cash(conn) - 1)
            except Exception as e:  # pragma: no cover - only on failure
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        with get_connection() as conn:
            assert db.get_cash(conn) == DEFAULT_CASH - 80


class TestCash:
    def test_get_set(self, db_path):
        with get_connection() as conn:
            db.set_cash(conn, 42.0)
            assert db.get_cash(conn) == 42.0


class TestWatchlist:
    def test_add_returns_row(self, db_path):
        with get_connection() as conn:
            row = db.add_to_watchlist(conn, "PYPL")
            assert row["ticker"] == "PYPL"
            assert row["added_at"].endswith("+00:00")
            assert db.get_watchlist(conn)[-1] == row

    def test_add_duplicate_returns_none(self, db_path):
        with get_connection() as conn:
            assert db.add_to_watchlist(conn, "AAPL") is None
            assert len(db.get_watchlist(conn)) == len(DEFAULT_TICKERS)

    def test_remove(self, db_path):
        with get_connection() as conn:
            assert db.remove_from_watchlist(conn, "AAPL") is True
            assert db.remove_from_watchlist(conn, "AAPL") is False
            assert "AAPL" not in [w["ticker"] for w in db.get_watchlist(conn)]


class TestPositions:
    def test_empty(self, db_path):
        with get_connection() as conn:
            assert db.get_positions(conn) == []
            assert db.get_position(conn, "AAPL") is None

    def test_upsert_insert_and_update(self, db_path):
        with get_connection() as conn:
            db.upsert_position(conn, "AAPL", 10, 190.0)
            pos = db.get_position(conn, "AAPL")
            assert pos["quantity"] == 10
            assert pos["avg_cost"] == 190.0
            assert set(pos) == {"ticker", "quantity", "avg_cost", "updated_at"}

            db.upsert_position(conn, "AAPL", 15.5, 195.0)
            assert db.get_position(conn, "AAPL")["quantity"] == 15.5
            assert len(db.get_positions(conn)) == 1

    def test_delete(self, db_path):
        with get_connection() as conn:
            db.upsert_position(conn, "AAPL", 10, 190.0)
            db.upsert_position(conn, "MSFT", 1, 400.0)
            db.delete_position(conn, "AAPL")
            assert [p["ticker"] for p in db.get_positions(conn)] == ["MSFT"]


class TestTrades:
    def test_insert_returns_full_row(self, db_path):
        with get_connection() as conn:
            trade = db.insert_trade(conn, "AAPL", "buy", 2.5, 190.0)
            assert set(trade) == {"id", "ticker", "side", "quantity", "price", "executed_at"}
            stored = conn.execute("SELECT * FROM trades WHERE id = ?", (trade["id"],)).fetchone()
            assert stored["user_id"] == "default"
            assert stored["quantity"] == 2.5

    def test_invalid_side_rejected(self, db_path):
        with get_connection() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                db.insert_trade(conn, "AAPL", "hold", 1, 1.0)


class TestSnapshots:
    def test_ascending_and_limited(self, db_path):
        with get_connection() as conn:
            for v in range(5):
                db.insert_snapshot(conn, float(v))
            assert [s["total_value"] for s in db.get_snapshots(conn)] == [0, 1, 2, 3, 4]
            latest = db.get_snapshots(conn, limit=2)
            assert [s["total_value"] for s in latest] == [3.0, 4.0]
            assert set(latest[0]) == {"total_value", "recorded_at"}


class TestChat:
    def test_insert_and_get(self, db_path):
        actions = {"trades": [{"ticker": "AAPL", "status": "executed"}]}
        with get_connection() as conn:
            db.insert_chat_message(conn, "user", "hi")
            db.insert_chat_message(conn, "assistant", "hello", actions)
            msgs = db.get_chat_messages(conn)
        assert [m["role"] for m in msgs] == ["user", "assistant"]
        assert msgs[0]["actions"] is None
        assert msgs[1]["actions"] == actions
        assert set(msgs[0]) == {"role", "content", "actions", "created_at"}

    def test_limit_keeps_latest_ascending(self, db_path):
        with get_connection() as conn:
            for i in range(5):
                db.insert_chat_message(conn, "user", f"m{i}")
            msgs = db.get_chat_messages(conn, limit=3)
        assert [m["content"] for m in msgs] == ["m2", "m3", "m4"]

"""SQLite connection handling and lazy initialization."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .repository import DEFAULT_USER_ID, new_id, now_iso

# backend/app/db/connection.py -> project root is 3 levels above backend/app/db/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "finally.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_CASH = 10000.0
DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]

# Seconds a writer waits for a lock held by another connection before failing
BUSY_TIMEOUT = 10.0


def get_db_path() -> Path:
    """Return the database path from DB_PATH (read at call time) or the default."""
    return Path(os.environ.get("DB_PATH") or DEFAULT_DB_PATH)


def _connect() -> sqlite3.Connection:
    # isolation_level=None: we manage transactions explicitly
    conn = sqlite3.connect(get_db_path(), timeout=BUSY_TIMEOUT, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a connection inside a BEGIN IMMEDIATE transaction.

    Commits on success, rolls back on exception, always closes.
    """
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException:
            conn.rollback()
            raise
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the DB file, tables, and seed default data if empty. Idempotent."""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect()
    try:
        conn.executescript(SCHEMA_PATH.read_text())
    finally:
        conn.close()

    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH, now_iso()),
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
        ).fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                [(new_id(), DEFAULT_USER_ID, t, now_iso()) for t in DEFAULT_TICKERS],
            )

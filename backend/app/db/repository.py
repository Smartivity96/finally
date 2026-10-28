"""Repository functions. All take an open connection first and a user_id kwarg."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime

DEFAULT_USER_ID = "default"


def now_iso() -> str:
    """Current time as an ISO 8601 UTC string with fixed microsecond precision."""
    return datetime.now(UTC).isoformat(timespec="microseconds")


def new_id() -> str:
    return str(uuid.uuid4())


# --- Cash ---


def get_cash(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> float:
    row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"No user profile for {user_id!r}")
    return row["cash_balance"]


def set_cash(conn: sqlite3.Connection, amount: float, user_id: str = DEFAULT_USER_ID) -> None:
    conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (amount, user_id))


# --- Watchlist ---


def get_watchlist(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[dict]:
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def add_to_watchlist(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> dict | None:
    """Add a ticker. Returns {ticker, added_at}, or None if already present."""
    added_at = now_iso()
    cur = conn.execute(
        "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (new_id(), user_id, ticker, added_at),
    )
    if cur.rowcount == 0:
        return None
    return {"ticker": ticker, "added_at": added_at}


def remove_from_watchlist(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    cur = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    return cur.rowcount > 0


# --- Positions ---

_POSITION_COLS = "ticker, quantity, avg_cost, updated_at"


def get_positions(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[dict]:
    rows = conn.execute(
        f"SELECT {_POSITION_COLS} FROM positions WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_position(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> dict | None:
    row = conn.execute(
        f"SELECT {_POSITION_COLS} FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    return dict(row) if row else None


def upsert_position(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    avg_cost: float,
    user_id: str = DEFAULT_USER_ID,
) -> None:
    conn.execute(
        """
        INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (user_id, ticker) DO UPDATE SET
            quantity = excluded.quantity,
            avg_cost = excluded.avg_cost,
            updated_at = excluded.updated_at
        """,
        (new_id(), user_id, ticker, quantity, avg_cost, now_iso()),
    )


def delete_position(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> None:
    conn.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker))


# --- Trades ---


def insert_trade(
    conn: sqlite3.Connection,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Append a trade. Returns {id, ticker, side, quantity, price, executed_at}."""
    trade = {
        "id": new_id(),
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": now_iso(),
    }
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade["id"], user_id, ticker, side, quantity, price, trade["executed_at"]),
    )
    return trade


# --- Portfolio snapshots ---


def insert_snapshot(
    conn: sqlite3.Connection, total_value: float, user_id: str = DEFAULT_USER_ID
) -> None:
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)"
        " VALUES (?, ?, ?, ?)",
        (new_id(), user_id, total_value, now_iso()),
    )


def get_snapshots(
    conn: sqlite3.Connection, limit: int = 500, user_id: str = DEFAULT_USER_ID
) -> list[dict]:
    """Latest `limit` snapshots, returned in ascending time order."""
    rows = conn.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id = ?"
        " ORDER BY recorded_at DESC, rowid DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


# --- Chat ---


def insert_chat_message(
    conn: sqlite3.Connection,
    role: str,
    content: str,
    actions: dict | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> None:
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            new_id(),
            user_id,
            role,
            content,
            json.dumps(actions) if actions is not None else None,
            now_iso(),
        ),
    )


def get_chat_messages(
    conn: sqlite3.Connection, limit: int = 20, user_id: str = DEFAULT_USER_ID
) -> list[dict]:
    """Latest `limit` messages in ascending order: [{role, content, actions, created_at}]."""
    rows = conn.execute(
        "SELECT role, content, actions, created_at FROM chat_messages WHERE user_id = ?"
        " ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    messages = []
    for r in reversed(rows):
        msg = dict(r)
        msg["actions"] = json.loads(msg["actions"]) if msg["actions"] is not None else None
        messages.append(msg)
    return messages

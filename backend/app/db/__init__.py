"""SQLite persistence: connection, lazy init/seed, and repository functions."""

from .connection import (
    DEFAULT_CASH,
    DEFAULT_TICKERS,
    get_connection,
    get_db_path,
    init_db,
)
from .repository import (
    DEFAULT_USER_ID,
    add_to_watchlist,
    delete_position,
    get_cash,
    get_chat_messages,
    get_position,
    get_positions,
    get_snapshots,
    get_watchlist,
    insert_chat_message,
    insert_snapshot,
    insert_trade,
    remove_from_watchlist,
    set_cash,
    upsert_position,
)

__all__ = [
    "DEFAULT_CASH",
    "DEFAULT_TICKERS",
    "DEFAULT_USER_ID",
    "add_to_watchlist",
    "delete_position",
    "get_cash",
    "get_chat_messages",
    "get_connection",
    "get_db_path",
    "get_position",
    "get_positions",
    "get_snapshots",
    "get_watchlist",
    "init_db",
    "insert_chat_message",
    "insert_snapshot",
    "insert_trade",
    "remove_from_watchlist",
    "set_cash",
    "upsert_position",
]

"""Watchlist service: list, add and remove watched tickers."""

from __future__ import annotations

from app import db
from app.market import MarketDataSource, PriceCache
from app.portfolio.service import normalize_ticker


class WatchlistError(Exception):
    """A watchlist operation failed. `status_code` is 400 or 404."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _normalize(ticker: str) -> str:
    try:
        return normalize_ticker(ticker)
    except ValueError as e:
        raise WatchlistError(str(e)) from e


def list_watchlist(cache: PriceCache) -> list[dict]:
    """Watchlist entries with latest prices (price fields None if not yet priced)."""
    with db.get_connection() as conn:
        entries = db.get_watchlist(conn)
    result = []
    for entry in entries:
        update = cache.get(entry["ticker"])
        result.append(
            {
                "ticker": entry["ticker"],
                "price": update.price if update else None,
                "previous_price": update.previous_price if update else None,
                "change_percent": update.change_percent if update else None,
                "direction": update.direction if update else None,
                "added_at": entry["added_at"],
            }
        )
    return result


async def add_ticker(source: MarketDataSource, ticker: str) -> dict:
    """Add a ticker to the watchlist and start pricing it."""
    ticker = _normalize(ticker)
    with db.get_connection() as conn:
        entry = db.add_to_watchlist(conn, ticker)
    if entry is None:
        raise WatchlistError(f"{ticker} is already in the watchlist")
    await source.add_ticker(ticker)
    return {"ticker": entry["ticker"], "added_at": entry["added_at"]}


async def remove_ticker(source: MarketDataSource, cache: PriceCache, ticker: str) -> dict:
    """Remove a ticker from the watchlist; stop pricing it unless a position is open."""
    ticker = _normalize(ticker)
    with db.get_connection() as conn:
        removed = db.remove_from_watchlist(conn, ticker)
        has_position = db.get_position(conn, ticker) is not None
    if not removed:
        raise WatchlistError(f"{ticker} is not in the watchlist", status_code=404)
    if not has_position:
        await source.remove_ticker(ticker)
        cache.remove(ticker)
    return {"ticker": ticker}

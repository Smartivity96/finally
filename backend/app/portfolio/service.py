"""Portfolio service: valuation, trade execution and snapshots."""

from __future__ import annotations

import re

from app import db
from app.market import MarketDataSource, PriceCache

TICKER_RE = re.compile(r"^[A-Z]{1,5}$")
ZERO_QTY = 1e-6
EPSILON = 1e-9


class TradeError(Exception):
    """A trade failed validation (bad input, insufficient cash/shares, no price)."""


def normalize_ticker(ticker: str) -> str:
    """Uppercase and validate a ticker symbol. Raises ValueError if invalid."""
    normalized = (ticker or "").strip().upper()
    if not TICKER_RE.match(normalized):
        raise ValueError(f"Invalid ticker: {ticker!r} (expected 1-5 letters)")
    return normalized


def _build_portfolio(conn, cache: PriceCache) -> dict:
    cash = db.get_cash(conn)
    positions = []
    positions_value = 0.0
    total_cost = 0.0
    for pos in db.get_positions(conn):
        quantity = pos["quantity"]
        avg_cost = pos["avg_cost"]
        price = cache.get_price(pos["ticker"])
        current_price = price if price is not None else avg_cost
        market_value = quantity * current_price
        cost_basis = quantity * avg_cost
        pnl = market_value - cost_basis
        positions.append(
            {
                "ticker": pos["ticker"],
                "quantity": quantity,
                "avg_cost": round(avg_cost, 4),
                "current_price": round(current_price, 4),
                "market_value": round(market_value, 2),
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_percent": round(pnl / cost_basis * 100, 4) if cost_basis else 0.0,
            }
        )
        positions_value += market_value
        total_cost += cost_basis
    return {
        "cash_balance": round(cash, 2),
        "total_value": round(cash + positions_value, 2),
        "positions_value": round(positions_value, 2),
        "unrealized_pnl": round(positions_value - total_cost, 2),
        "positions": positions,
    }


def get_portfolio(cache: PriceCache) -> dict:
    """Return cash, positions valued at the latest cached prices, and totals."""
    with db.get_connection() as conn:
        return _build_portfolio(conn, cache)


def execute_trade(cache: PriceCache, ticker: str, side: str, quantity: float) -> dict:
    """Execute a market order at the cached price in a single transaction.

    Returns the inserted trade row. Raises TradeError on any validation failure.
    """
    try:
        ticker = normalize_ticker(ticker)
    except ValueError as e:
        raise TradeError(str(e)) from e
    side = (side or "").strip().lower()
    if side not in ("buy", "sell"):
        raise TradeError(f"Invalid side: {side!r} (expected 'buy' or 'sell')")
    try:
        quantity = round(float(quantity), 4)
    except (TypeError, ValueError) as e:
        raise TradeError(f"Invalid quantity: {quantity!r}") from e
    if not quantity > 0:
        raise TradeError("Quantity must be greater than 0")

    price = cache.get_price(ticker)
    if price is None:
        raise TradeError(f"No price available for {ticker}; add it to the watchlist first")

    with db.get_connection() as conn:
        cash = db.get_cash(conn)
        position = db.get_position(conn, ticker)
        held = position["quantity"] if position else 0.0
        cost = quantity * price

        if side == "buy":
            if cost > cash + EPSILON:
                raise TradeError("Insufficient cash")
            new_qty = held + quantity
            avg_cost = (held * position["avg_cost"] + cost) / new_qty if position else price
            db.set_cash(conn, cash - cost)
            db.upsert_position(conn, ticker, round(new_qty, 4), avg_cost)
        else:
            if quantity > held + EPSILON:
                raise TradeError("Insufficient shares")
            new_qty = held - quantity
            db.set_cash(conn, cash + cost)
            if new_qty < ZERO_QTY:
                db.delete_position(conn, ticker)
            else:
                db.upsert_position(conn, ticker, round(new_qty, 4), position["avg_cost"])

        trade = db.insert_trade(conn, ticker, side, quantity, price)
        db.insert_snapshot(conn, _build_portfolio(conn, cache)["total_value"])
        return trade


def record_snapshot(cache: PriceCache) -> None:
    """Record the current total portfolio value."""
    with db.get_connection() as conn:
        db.insert_snapshot(conn, _build_portfolio(conn, cache)["total_value"])


def get_history(limit: int = 500) -> list[dict]:
    """Portfolio value snapshots, ascending by time."""
    with db.get_connection() as conn:
        return db.get_snapshots(conn, limit=limit)


def tracked_tickers() -> list[str]:
    """Tickers that should be priced: watchlist ∪ open positions."""
    with db.get_connection() as conn:
        tickers = [w["ticker"] for w in db.get_watchlist(conn)]
        tickers += [p["ticker"] for p in db.get_positions(conn) if p["ticker"] not in tickers]
    return tickers


async def sync_tracking(source: MarketDataSource, ticker: str) -> None:
    """Start or stop pricing `ticker` so the source tracks watchlist ∪ positions.

    Call after a trade (or watchlist change) that may change whether the ticker is tracked.
    """
    should_track = ticker in tracked_tickers()
    is_tracked = ticker in source.get_tickers()
    if should_track and not is_tracked:
        await source.add_ticker(ticker)
    elif not should_track and is_tracked:
        await source.remove_ticker(ticker)

import pytest

from app import db
from app.portfolio import service
from app.portfolio.service import TradeError
from tests.api.fakes import FakeSource

pytestmark = pytest.mark.usefixtures("fresh_db")


def test_fresh_portfolio(cache):
    p = service.get_portfolio(cache)
    assert p == {
        "cash_balance": 10000.0,
        "total_value": 10000.0,
        "positions_value": 0.0,
        "unrealized_pnl": 0.0,
        "positions": [],
    }


def test_buy_updates_cash_position_trade_and_snapshot(cache):
    trade = service.execute_trade(cache, "aapl", "BUY", 10)
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 10
    assert trade["price"] == 100.0
    assert trade["id"] and trade["executed_at"]

    p = service.get_portfolio(cache)
    assert p["cash_balance"] == 9000.0
    assert p["total_value"] == 10000.0
    [pos] = p["positions"]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 10
    assert pos["avg_cost"] == 100.0
    assert service.get_history()[-1]["total_value"] == 10000.0


def test_weighted_avg_cost_on_buys(cache):
    service.execute_trade(cache, "AAPL", "buy", 10)
    cache.update("AAPL", 130.0)
    service.execute_trade(cache, "AAPL", "buy", 20)
    [pos] = service.get_portfolio(cache)["positions"]
    assert pos["quantity"] == 30
    assert pos["avg_cost"] == pytest.approx(120.0)


def test_unrealized_pnl(cache):
    service.execute_trade(cache, "AAPL", "buy", 10)
    cache.update("AAPL", 110.0)
    p = service.get_portfolio(cache)
    [pos] = p["positions"]
    assert pos["current_price"] == 110.0
    assert pos["market_value"] == 1100.0
    assert pos["unrealized_pnl"] == 100.0
    assert pos["unrealized_pnl_percent"] == 10.0
    assert p["unrealized_pnl"] == 100.0
    assert p["positions_value"] == 1100.0
    assert p["total_value"] == 10100.0


def test_sell_at_loss_keeps_avg_cost(cache):
    service.execute_trade(cache, "AAPL", "buy", 10)
    cache.update("AAPL", 80.0)
    service.execute_trade(cache, "AAPL", "sell", 4)
    p = service.get_portfolio(cache)
    [pos] = p["positions"]
    assert pos["quantity"] == 6
    assert pos["avg_cost"] == 100.0
    assert pos["unrealized_pnl"] == -120.0
    assert p["cash_balance"] == 9000.0 + 320.0


def test_sell_to_zero_deletes_position(cache):
    service.execute_trade(cache, "AAPL", "buy", 1.5)
    service.execute_trade(cache, "AAPL", "sell", 1.5)
    p = service.get_portfolio(cache)
    assert p["positions"] == []
    assert p["cash_balance"] == 10000.0


def test_fractional_quantity_rounded(cache):
    trade = service.execute_trade(cache, "AAPL", "buy", 0.123456)
    assert trade["quantity"] == 0.1235


def test_missing_price_falls_back_to_avg_cost(cache):
    service.execute_trade(cache, "AAPL", "buy", 10)
    cache.remove("AAPL")
    [pos] = service.get_portfolio(cache)["positions"]
    assert pos["current_price"] == 100.0
    assert pos["unrealized_pnl"] == 0.0


@pytest.mark.parametrize(
    "ticker,side,qty,message",
    [
        ("AAPL", "buy", 101, "Insufficient cash"),
        ("AAPL", "sell", 1, "Insufficient shares"),
        ("XYZ", "buy", 1, "No price available for XYZ; add it to the watchlist first"),
        ("AAPL1", "buy", 1, "Invalid ticker"),
        ("AAPL", "hold", 1, "Invalid side"),
        ("AAPL", "buy", 0, "Quantity must be greater than 0"),
        ("AAPL", "buy", -5, "Quantity must be greater than 0"),
        ("AAPL", "buy", 0.00001, "Quantity must be greater than 0"),
    ],
)
def test_trade_errors_leave_state_unchanged(cache, ticker, side, qty, message):
    with pytest.raises(TradeError, match=message):
        service.execute_trade(cache, ticker, side, qty)
    assert service.get_portfolio(cache)["cash_balance"] == 10000.0
    assert service.get_history() == []


def test_oversell_after_buy(cache):
    service.execute_trade(cache, "AAPL", "buy", 2)
    with pytest.raises(TradeError, match="Insufficient shares"):
        service.execute_trade(cache, "AAPL", "sell", 3)
    assert service.get_portfolio(cache)["positions"][0]["quantity"] == 2


def test_buy_exact_cash(cache):
    service.execute_trade(cache, "AAPL", "buy", 100)
    assert service.get_portfolio(cache)["cash_balance"] == 0.0


def test_record_snapshot(cache):
    service.record_snapshot(cache)
    [snap] = service.get_history()
    assert snap["total_value"] == 10000.0
    assert snap["recorded_at"]


def test_tracked_tickers_union(cache):
    service.execute_trade(cache, "AAPL", "buy", 1)
    with db.get_connection() as conn:
        db.remove_from_watchlist(conn, "AAPL")
    tracked = service.tracked_tickers()
    assert "AAPL" in tracked
    assert "GOOGL" in tracked
    assert len(tracked) == 10


async def test_sync_tracking_adds_and_removes(cache):
    source = FakeSource(cache)
    service.execute_trade(cache, "AAPL", "buy", 1)
    with db.get_connection() as conn:
        db.remove_from_watchlist(conn, "AAPL")
    await service.sync_tracking(source, "AAPL")
    assert "AAPL" in source.get_tickers()

    service.execute_trade(cache, "AAPL", "sell", 1)
    await service.sync_tracking(source, "AAPL")
    assert "AAPL" not in source.get_tickers()
    assert cache.get_price("AAPL") is None

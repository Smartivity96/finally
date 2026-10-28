import pytest

from app import db
from app.market import PriceCache
from app.portfolio import service as portfolio_service
from app.watchlist import service
from app.watchlist.service import WatchlistError
from tests.api.fakes import FakeSource


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return PriceCache()


@pytest.fixture
async def source(cache):
    s = FakeSource(cache)
    await s.start(portfolio_service.tracked_tickers())
    return s


async def test_list_has_prices(cache, source):
    items = service.list_watchlist(cache)
    assert len(items) == 10
    aapl = next(i for i in items if i["ticker"] == "AAPL")
    assert aapl["price"] == 100.0
    assert aapl["direction"] == "flat"
    assert aapl["added_at"]


def test_list_unpriced_is_none(cache):
    items = service.list_watchlist(cache)
    assert items[0]["price"] is None
    assert items[0]["change_percent"] is None


async def test_add_normalises_and_tracks(cache, source):
    entry = await service.add_ticker(source, " pypl ")
    assert entry["ticker"] == "PYPL"
    assert entry["added_at"]
    assert "PYPL" in source.get_tickers()
    assert cache.get_price("PYPL") == 50.0


async def test_add_duplicate(source):
    with pytest.raises(WatchlistError, match="AAPL is already in the watchlist") as e:
        await service.add_ticker(source, "aapl")
    assert e.value.status_code == 400


@pytest.mark.parametrize("ticker", ["", "TOOLONG", "AB1", "A-B"])
async def test_add_invalid(source, ticker):
    with pytest.raises(WatchlistError) as e:
        await service.add_ticker(source, ticker)
    assert e.value.status_code == 400


async def test_remove_stops_pricing(cache, source):
    assert await service.remove_ticker(source, cache, "googl") == {"ticker": "GOOGL"}
    assert "GOOGL" not in source.get_tickers()
    assert cache.get("GOOGL") is None


async def test_remove_missing_is_404(cache, source):
    with pytest.raises(WatchlistError, match="PYPL is not in the watchlist") as e:
        await service.remove_ticker(source, cache, "PYPL")
    assert e.value.status_code == 404


async def test_remove_keeps_pricing_with_open_position(cache, source):
    portfolio_service.execute_trade(cache, "AAPL", "buy", 1)
    await service.remove_ticker(source, cache, "AAPL")
    assert "AAPL" in source.get_tickers()
    assert cache.get_price("AAPL") == 100.0

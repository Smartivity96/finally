"""Deterministic test doubles shared by API, portfolio and watchlist tests."""

from app.market import MarketDataSource, PriceCache

PRICES = {"AAPL": 100.0, "GOOGL": 200.0, "PYPL": 50.0}
DEFAULT_PRICE = 10.0


class FakeSource(MarketDataSource):
    """Seeds the cache with fixed prices; never moves them."""

    def __init__(self, cache: PriceCache) -> None:
        self._cache = cache
        self._tickers: list[str] = []

    async def start(self, tickers: list[str]) -> None:
        for t in tickers:
            await self.add_ticker(t)

    async def stop(self) -> None:
        pass

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            self._cache.update(ticker, PRICES.get(ticker, DEFAULT_PRICE))

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self._tickers:
            self._tickers.remove(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

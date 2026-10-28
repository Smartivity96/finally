import pytest

from app import db
from app.market import PriceCache


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def cache():
    c = PriceCache()
    c.update("AAPL", 100.0)
    c.update("GOOGL", 200.0)
    return c

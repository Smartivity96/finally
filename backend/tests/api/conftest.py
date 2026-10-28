import pytest
from fastapi.testclient import TestClient

import app.main as main
from tests.api.fakes import FakeSource


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
    monkeypatch.setattr(main, "create_market_data_source", FakeSource)
    with TestClient(main.create_app()) as c:
        yield c

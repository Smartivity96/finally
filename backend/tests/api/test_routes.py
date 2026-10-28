def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_portfolio_initial(client):
    r = client.get("/api/portfolio")
    assert r.status_code == 200
    body = r.json()
    assert body["cash_balance"] == 10000.0
    assert body["total_value"] == 10000.0
    assert body["positions"] == []
    assert set(body) == {"cash_balance", "total_value", "positions_value", "unrealized_pnl", "positions"}


def test_startup_snapshot_recorded(client):
    r = client.get("/api/portfolio/history")
    assert r.status_code == 200
    [snap] = r.json()
    assert snap["total_value"] == 10000.0
    assert set(snap) == {"total_value", "recorded_at"}


def test_buy_trade(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 5, "side": "buy"})
    assert r.status_code == 200
    body = r.json()
    assert set(body["trade"]) >= {"id", "ticker", "side", "quantity", "price", "executed_at"}
    assert body["trade"]["price"] == 100.0
    assert body["portfolio"]["cash_balance"] == 9500.0
    [pos] = body["portfolio"]["positions"]
    assert set(pos) == {
        "ticker", "quantity", "avg_cost", "current_price",
        "market_value", "unrealized_pnl", "unrealized_pnl_percent",
    }
    assert len(client.get("/api/portfolio/history").json()) == 2


def test_sell_trade(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "buy"})
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "sell"})
    assert r.status_code == 200
    assert r.json()["portfolio"]["positions"] == []
    assert r.json()["portfolio"]["cash_balance"] == 10000.0


def test_trade_business_errors(client):
    cases = [
        ({"ticker": "AAPL", "quantity": 1000, "side": "buy"}, "Insufficient cash"),
        ({"ticker": "AAPL", "quantity": 1, "side": "sell"}, "Insufficient shares"),
        ({"ticker": "PYPL", "quantity": 1, "side": "buy"},
         "No price available for PYPL; add it to the watchlist first"),
    ]
    for payload, error in cases:
        r = client.post("/api/portfolio/trade", json=payload)
        assert r.status_code == 400
        assert r.json() == {"error": error}


def test_trade_invalid_body_is_400(client):
    for payload in [
        {"ticker": "AAPL", "side": "buy"},
        {"ticker": "AAPL", "quantity": "lots", "side": "buy"},
        {"ticker": "AAPL", "quantity": 1, "side": "short"},
        {"ticker": "123", "quantity": 1, "side": "buy"},
    ]:
        r = client.post("/api/portfolio/trade", json=payload)
        assert r.status_code == 400, payload
        assert isinstance(r.json()["error"], str)


def test_watchlist_list(client):
    r = client.get("/api/watchlist")
    assert r.status_code == 200
    items = r.json()
    assert [i["ticker"] for i in items][:1] == ["AAPL"]
    assert len(items) == 10
    assert set(items[0]) == {"ticker", "price", "previous_price", "change_percent", "direction", "added_at"}


def test_watchlist_add_remove(client):
    r = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert r.status_code == 200
    assert r.json()["ticker"] == "PYPL"
    assert any(i["ticker"] == "PYPL" and i["price"] == 50.0 for i in client.get("/api/watchlist").json())

    r = client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert r.status_code == 400
    assert r.json() == {"error": "PYPL is already in the watchlist"}

    r = client.delete("/api/watchlist/pypl")
    assert r.status_code == 200
    assert r.json() == {"ticker": "PYPL"}

    r = client.delete("/api/watchlist/PYPL")
    assert r.status_code == 404
    assert r.json() == {"error": "PYPL is not in the watchlist"}


def test_watchlist_add_invalid(client):
    assert client.post("/api/watchlist", json={"ticker": "TOOLONG"}).status_code == 400
    r = client.post("/api/watchlist", json={})
    assert r.status_code == 400
    assert "error" in r.json()


def test_unwatched_position_stays_priced_until_sold(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    client.delete("/api/watchlist/AAPL")
    source = client.app.state.market_source
    assert "AAPL" in source.get_tickers()
    assert client.get("/api/portfolio").json()["positions"][0]["current_price"] == 100.0

    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert "AAPL" not in source.get_tickers()


def test_chat_router_included(client):
    paths = {r.path for r in client.app.routes}
    assert {"/api/chat", "/api/chat/history", "/api/stream/prices"} <= paths

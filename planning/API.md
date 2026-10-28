# FinAlly — API & Team Contract

This is the binding contract between team members. It resolves the open questions in PLAN.md §13 using the suggested defaults. If you need to change something here, message the team lead first.

## 1. Ownership

| Owner | Owns (write access) |
|---|---|
| **db-engineer** | `backend/app/db/` (schema.sql, connection, init/seed, repository functions), `backend/tests/db/` |
| **backend-engineer** | `backend/app/main.py`, `backend/app/portfolio/`, `backend/app/watchlist/`, `backend/app/routes/` (except chat), `backend/tests/api/`, `backend/tests/portfolio/`, `backend/tests/watchlist/` |
| **llm-engineer** | `backend/app/llm/` (incl. its chat router), `backend/tests/llm/` |
| **frontend-engineer** | `frontend/` |
| **devops-engineer** | `Dockerfile`, `.dockerignore`, `scripts/`, `.env.example`, `db/.gitkeep`, `.gitignore` additions |
| **integration-tester** | `test/` (Playwright E2E), `planning/ISSUES.md` |

`backend/app/market/` is complete — do not modify it (report needed changes to the lead).
`backend/pyproject.toml` / `uv.lock`: add deps only via `uv add` (retry if another agent is mid-write).

## 2. Conventions

- **Timestamps**: SSE = Unix seconds (float). DB and REST = ISO 8601 UTC strings (`2026-10-28T12:00:00+00:00`).
- **Tickers**: uppercased, must match `^[A-Z]{1,5}$`.
- **Quantity**: `> 0`, rounded to 4 decimals. A sell leaving `quantity < 1e-6` deletes the position row.
- **Errors**: every API error is a JSON body `{"error": "<human readable message>"}`. 400 for validation/business errors (incl. request body validation — override FastAPI's 422), 404 for not found.
- **Tracked tickers** (priced by the market source) = watchlist ∪ tickers with open positions.
- **user_id** is always `"default"` (the `users_profile.id` plays that role).
- **DB path**: env `DB_PATH`, default `<project_root>/db/finally.db`. Docker sets `DB_PATH=/app/db/finally.db`.
- **Static files**: env `STATIC_DIR`, default `backend/static`. Mounted at `/` **after** all `/api/*` routers, with `html=True`. If the dir does not exist, skip the mount.
- **Env**: backend loads the project-root `.env` with `python-dotenv` (`load_dotenv(override=False)`) at startup.

## 3. REST endpoints

### GET /api/health
`200 {"status": "ok"}`

### GET /api/stream/prices (exists)
SSE. One event per cache change containing **all** tracked tickers:
```
data: {"AAPL": {"ticker":"AAPL","price":190.5,"previous_price":190.42,"timestamp":1761652800.12,"change":0.08,"change_percent":0.042,"direction":"up"}, "GOOGL": {...}}
```
`change_percent` is tick-to-tick. "Daily change %" in the watchlist is computed by the frontend vs. the first price it received for that ticker since page load.

### GET /api/portfolio
```json
{
  "cash_balance": 8095.0,
  "total_value": 10012.4,
  "positions_value": 1917.4,
  "unrealized_pnl": 12.4,
  "positions": [
    {"ticker": "AAPL", "quantity": 10, "avg_cost": 190.5, "current_price": 191.74,
     "market_value": 1917.4, "unrealized_pnl": 12.4, "unrealized_pnl_percent": 0.6509}
  ]
}
```
If no price is cached for a position, use `avg_cost` as `current_price`.

### POST /api/portfolio/trade
Request: `{"ticker": "AAPL", "quantity": 10, "side": "buy"}` (`side` ∈ `buy|sell`)
Response `200`:
```json
{"trade": {"id": "uuid", "ticker": "AAPL", "side": "buy", "quantity": 10, "price": 190.5, "executed_at": "ISO"},
 "portfolio": { ...same shape as GET /api/portfolio... }}
```
Errors (400): `"Insufficient cash"`, `"Insufficient shares"`, `"No price available for XYZ; add it to the watchlist first"`, invalid ticker/quantity/side.
Each trade (cash update + position upsert/delete + trade insert + snapshot insert) runs in **one SQLite transaction**.

### GET /api/portfolio/history
`200 [{"total_value": 10000.0, "recorded_at": "ISO"}, ...]` — ascending by time, at most the latest 500 points.
Snapshots are recorded at startup, every 30 s by a background task, and after each trade.

### GET /api/watchlist
`200 [{"ticker": "AAPL", "price": 190.5, "previous_price": 190.42, "change_percent": 0.042, "direction": "up", "added_at": "ISO"}, ...]` — ordered by `added_at`; price fields are `null` if not yet priced.

### POST /api/watchlist
Request `{"ticker": "pypl"}` → normalised to `PYPL`. Adds to DB and to the market source.
`200 {"ticker": "PYPL", "added_at": "ISO"}`. Errors 400: invalid format, `"PYPL is already in the watchlist"`.

### DELETE /api/watchlist/{ticker}
`200 {"ticker": "PYPL"}`; `404 {"error": "PYPL is not in the watchlist"}`.
Removes from the market source (and cache) **only if** no open position exists for it.

### POST /api/chat
Request `{"message": "Buy 5 NVDA"}`
Response `200`:
```json
{
  "message": "Done — bought 5 NVDA at $875.20.",
  "trades": [{"ticker": "NVDA", "side": "buy", "quantity": 5, "price": 875.2, "status": "executed"},
             {"ticker": "TSLA", "side": "buy", "quantity": 1000, "price": null, "status": "failed", "error": "Insufficient cash"}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add", "status": "executed"}]
}
```
`action` ∈ `add|remove`; `status` ∈ `executed|failed`. Watchlist changes execute **before** trades.
LLM failure (timeout, bad JSON, missing key) → `200` with a friendly `message` and empty action lists; never execute partial/unparsed actions.

### GET /api/chat/history
`200 [{"role": "user"|"assistant", "content": "...", "actions": {...}|null, "created_at": "ISO"}, ...]` — ascending, latest 50. (Lets the chat panel restore on reload.)

## 4. Internal Python interfaces

Routes read shared objects from `request.app.state`: `app.state.price_cache: PriceCache`, `app.state.market_source: MarketDataSource`.

### `app.db` (db-engineer)
```python
init_db() -> None                         # create dir/file, tables, seed if empty; idempotent
get_connection() -> ContextManager[sqlite3.Connection]
    # opens DB_PATH (read at call time), row_factory=sqlite3.Row,
    # BEGIN IMMEDIATE; commit on success, rollback on exception, always close.
# Repository functions — all take conn first, user_id="default" kwarg:
get_cash(conn) -> float
set_cash(conn, amount: float) -> None
get_watchlist(conn) -> list[dict]          # [{ticker, added_at}] ordered by added_at
add_to_watchlist(conn, ticker) -> dict | None   # None if already present
remove_from_watchlist(conn, ticker) -> bool     # False if absent
get_positions(conn) -> list[dict]          # [{ticker, quantity, avg_cost, updated_at}]
get_position(conn, ticker) -> dict | None
upsert_position(conn, ticker, quantity, avg_cost) -> None
delete_position(conn, ticker) -> None
insert_trade(conn, ticker, side, quantity, price) -> dict   # full trade row incl. id, executed_at
insert_snapshot(conn, total_value) -> None
get_snapshots(conn, limit=500) -> list[dict]  # ascending [{total_value, recorded_at}]
insert_chat_message(conn, role, content, actions: dict | None = None) -> None
get_chat_messages(conn, limit=20) -> list[dict]  # ascending, actions JSON-decoded
```

### `app.portfolio` and `app.watchlist` (backend-engineer)
```python
# app/portfolio/service.py
class TradeError(Exception): ...
get_portfolio(cache) -> dict                               # GET /api/portfolio shape
execute_trade(cache, ticker, side, quantity) -> dict        # trade dict; raises TradeError
record_snapshot(cache) -> None
async sync_tracking(source, ticker) -> None                # call after every successful trade (manual or chat)
# app/watchlist/service.py
class WatchlistError(Exception): ...                        # .status_code 400 or 404
list_watchlist(cache) -> list[dict]
async add_ticker(source, ticker) -> dict                    # raises WatchlistError
async remove_ticker(source, cache, ticker) -> dict          # raises WatchlistError
```

### `app.llm` (llm-engineer)
```python
router: APIRouter            # POST /api/chat, GET /api/chat/history — included by main.py
```
Uses the services above to execute actions. Model `openai/gpt-6.1-sol` via LiteLLM structured outputs (see `.claude/skills/openai/SKILL.md`). Last 20 messages as history.

**Mock mode** (`LLM_MOCK=true`), deterministic, case-insensitive keyword rules on the user message, first match wins:
| Message contains | Response |
|---|---|
| `buy` | message `"Mock: buying 1 AAPL."`, trades `[{AAPL, buy, 1}]` |
| `sell` | message `"Mock: selling 1 AAPL."`, trades `[{AAPL, sell, 1}]` |
| `watch` | message `"Mock: adding PYPL to your watchlist."`, watchlist_changes `[{PYPL, add}]` |
| otherwise | message `"Mock: I'm FinAlly, your AI trading assistant."`, no actions |

## 5. Frontend notes
- Static export (`output: 'export'`) to `frontend/out/`; DevOps copies it to `backend/static` in the image.
- Local dev: `next.config` adds `rewrites` for `/api/:path*` → `http://localhost:8000/api/:path*` only when `NODE_ENV === 'development'` (rewrites are incompatible with export builds).
- Give key elements stable `data-testid` attributes for E2E: `watchlist-row-{TICKER}`, `price-{TICKER}`, `cash-balance`, `total-value`, `connection-status` (with `data-status="connected|reconnecting|disconnected"`), `trade-ticker`, `trade-quantity`, `trade-buy`, `trade-sell`, `trade-error`, `positions-table`, `position-row-{TICKER}`, `watchlist-add-input`, `watchlist-add-button`, `watchlist-remove-{TICKER}`, `chat-input`, `chat-send`, `chat-message` (each message), `chat-loading`, `heatmap`, `pnl-chart`, `main-chart`.

## 6. Local run
```bash
cd backend && uv run uvicorn app.main:app --port 8000      # API + static (if built)
cd frontend && npm run dev                                  # UI on :3000, proxies /api
```

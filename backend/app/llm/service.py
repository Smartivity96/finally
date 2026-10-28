"""Chat orchestration: context -> LLM -> action execution -> persistence."""

import json
import logging

from app import db
from app.portfolio import service as portfolio_service
from app.watchlist import service as watchlist_service

from .client import LLMError, call_llm, is_mock_mode, mock_response
from .schema import ChatResponse

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20
FAILURE_MESSAGE = "Sorry, I couldn't process that request right now. Please try again in a moment."

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation.
The user trades a virtual portfolio with fake money; market orders fill instantly at the current price.

Your job:
- Analyze portfolio composition, risk concentration and P&L.
- Suggest trades with brief reasoning.
- Execute trades when the user asks or agrees, by listing them in "trades".
- Manage the watchlist proactively via "watchlist_changes" (add/remove tickers).
- Be concise and data-driven; cite numbers from the portfolio context.

Rules:
- Tickers are 1-5 uppercase letters. Quantities must be > 0 (fractional shares allowed).
- Only trade what the user asked for or agreed to. Buys need enough cash; sells need enough shares.
- To trade a ticker that is not on the watchlist, also add it to the watchlist.
- Always respond with valid JSON matching the required schema:
  "message" (text shown to the user), "trades" and "watchlist_changes" (empty lists if none)."""


def build_messages(user_message: str, history: list[dict], context: dict) -> list[dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "Current portfolio context (JSON):\n" + json.dumps(context)},
    ]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})
    return messages


def build_context(cache) -> dict:
    return {
        "portfolio": portfolio_service.get_portfolio(cache),
        "watchlist": watchlist_service.list_watchlist(cache),
    }


async def execute_actions(parsed: ChatResponse, cache, source) -> dict:
    """Run watchlist changes first, then trades; capture per-action status."""
    watchlist_results = []
    for change in parsed.watchlist_changes:
        ticker = change.ticker.strip().upper()
        result = {"ticker": ticker, "action": change.action, "status": "executed"}
        try:
            if change.action == "add":
                await watchlist_service.add_ticker(source, ticker)
            else:
                await watchlist_service.remove_ticker(source, cache, ticker)
        except watchlist_service.WatchlistError as e:
            result.update(status="failed", error=str(e))
        except Exception as e:
            logger.exception("Watchlist change failed: %s", change)
            result.update(status="failed", error=f"Unexpected error: {e}")
        watchlist_results.append(result)

    trade_results = []
    for trade in parsed.trades:
        ticker = trade.ticker.strip().upper()
        result = {
            "ticker": ticker,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": None,
            "status": "executed",
        }
        try:
            executed = portfolio_service.execute_trade(cache, ticker, trade.side, trade.quantity)
            result.update(quantity=executed["quantity"], price=executed["price"])
            await portfolio_service.sync_tracking(source, executed["ticker"])
        except portfolio_service.TradeError as e:
            result.update(status="failed", error=str(e))
        except Exception as e:
            logger.exception("Trade failed: %s", trade)
            result.update(status="failed", error=f"Unexpected error: {e}")
        trade_results.append(result)

    return {
        "message": parsed.message,
        "trades": trade_results,
        "watchlist_changes": watchlist_results,
    }


async def handle_chat(user_message: str, cache, source) -> dict:
    with db.get_connection() as conn:
        history = db.get_chat_messages(conn, limit=HISTORY_LIMIT)

    if is_mock_mode():
        parsed = mock_response(user_message)
    else:
        try:
            messages = build_messages(user_message, history, build_context(cache))
            parsed = await call_llm(messages)
        except LLMError as e:
            logger.warning("LLM failure: %s", e)
            parsed = None

    if parsed is None:
        result = {"message": FAILURE_MESSAGE, "trades": [], "watchlist_changes": []}
    else:
        result = await execute_actions(parsed, cache, source)

    actions = {"trades": result["trades"], "watchlist_changes": result["watchlist_changes"]}
    with db.get_connection() as conn:
        db.insert_chat_message(conn, "user", user_message)
        db.insert_chat_message(conn, "assistant", result["message"], actions)
    return result


def get_history(limit: int = 50) -> list[dict]:
    with db.get_connection() as conn:
        rows = db.get_chat_messages(conn, limit=limit)
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "actions": r.get("actions"),
            "created_at": r["created_at"],
        }
        for r in rows
    ]

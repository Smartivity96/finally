"""LLM call (LiteLLM -> OpenAI structured outputs) and deterministic mock mode."""

import asyncio
import logging
import os

from .schema import ChatResponse, TradeAction, WatchlistAction

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-6.1-sol"
TIMEOUT_SECONDS = 60.0


class LLMError(Exception):
    """The LLM call failed or returned an unusable response."""


def is_mock_mode() -> bool:
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


def mock_response(user_message: str) -> ChatResponse:
    """Deterministic keyword rules (API.md §4), first match wins."""
    text = user_message.lower()
    if "buy" in text:
        return ChatResponse(
            message="Mock: buying 1 AAPL.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=1)],
        )
    if "sell" in text:
        return ChatResponse(
            message="Mock: selling 1 AAPL.",
            trades=[TradeAction(ticker="AAPL", side="sell", quantity=1)],
        )
    if "watch" in text:
        return ChatResponse(
            message="Mock: adding PYPL to your watchlist.",
            watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
        )
    return ChatResponse(message="Mock: I'm FinAlly, your AI trading assistant.")


def parse_response(content: str | None) -> ChatResponse:
    """Validate the raw JSON content returned by the model."""
    if not content:
        raise LLMError("Empty LLM response")
    try:
        return ChatResponse.model_validate_json(content)
    except ValueError as e:
        raise LLMError(f"Malformed LLM response: {e}") from e


def _call_sync(messages: list[dict]) -> str | None:
    from litellm import completion

    response = completion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
    )
    return response.choices[0].message.content


async def call_llm(messages: list[dict]) -> ChatResponse:
    """Call the model in a worker thread with a timeout; raise LLMError on any failure."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise LLMError("OPENAI_API_KEY is not set")
    try:
        content = await asyncio.wait_for(
            asyncio.to_thread(_call_sync, messages), timeout=TIMEOUT_SECONDS
        )
    except TimeoutError as e:
        raise LLMError("LLM call timed out") from e
    except Exception as e:
        raise LLMError(f"LLM call failed: {e}") from e
    return parse_response(content)

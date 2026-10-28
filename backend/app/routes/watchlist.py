"""Watchlist routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.watchlist import service

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("")
async def list_watchlist(request: Request) -> list[dict]:
    return service.list_watchlist(request.app.state.price_cache)


@router.post("")
async def add_ticker(body: AddTickerRequest, request: Request):
    try:
        return await service.add_ticker(request.app.state.market_source, body.ticker)
    except service.WatchlistError as e:
        return JSONResponse(status_code=e.status_code, content={"error": str(e)})


@router.delete("/{ticker}")
async def remove_ticker(ticker: str, request: Request):
    state = request.app.state
    try:
        return await service.remove_ticker(state.market_source, state.price_cache, ticker)
    except service.WatchlistError as e:
        return JSONResponse(status_code=e.status_code, content={"error": str(e)})

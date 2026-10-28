"""Portfolio routes: valuation, trades and history."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.portfolio import service

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str


@router.get("")
async def get_portfolio(request: Request) -> dict:
    return service.get_portfolio(request.app.state.price_cache)


@router.post("/trade")
async def trade(body: TradeRequest, request: Request):
    cache = request.app.state.price_cache
    try:
        trade = service.execute_trade(cache, body.ticker, body.side, body.quantity)
    except service.TradeError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    await service.sync_tracking(request.app.state.market_source, trade["ticker"])
    return {"trade": trade, "portfolio": service.get_portfolio(cache)}


@router.get("/history")
async def history() -> list[dict]:
    return service.get_history()

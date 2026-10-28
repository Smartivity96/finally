"""FastAPI application: API routers, SSE stream, background tasks, static frontend."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR.parent / ".env", override=False)

from app import db  # noqa: E402
from app.llm import router as chat_router  # noqa: E402
from app.market import PriceCache, create_market_data_source, create_stream_router  # noqa: E402
from app.portfolio import service as portfolio_service  # noqa: E402
from app.routes import health_router, portfolio_router, watchlist_router  # noqa: E402

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL = 30.0


async def _snapshot_loop(cache: PriceCache, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            portfolio_service.record_snapshot(cache)
        except Exception:
            logger.exception("Portfolio snapshot failed")


def create_app() -> FastAPI:
    price_cache = PriceCache()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.init_db()
        source = create_market_data_source(price_cache)
        app.state.price_cache = price_cache
        app.state.market_source = source
        await source.start(portfolio_service.tracked_tickers())
        portfolio_service.record_snapshot(price_cache)
        snapshot_task = asyncio.create_task(
            _snapshot_loop(price_cache, SNAPSHOT_INTERVAL), name="portfolio-snapshots"
        )
        try:
            yield
        finally:
            snapshot_task.cancel()
            try:
                await snapshot_task
            except asyncio.CancelledError:
                pass
            await source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if errors:
            loc = ".".join(str(p) for p in errors[0].get("loc", ()) if p != "body")
            message = f"{loc}: {errors[0].get('msg')}" if loc else errors[0].get("msg")
        else:
            message = "Invalid request"
        return JSONResponse(status_code=400, content={"error": message})

    app.include_router(health_router)
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    app.include_router(create_stream_router(price_cache))
    app.include_router(chat_router)

    static_dir = Path(os.environ.get("STATIC_DIR", BACKEND_DIR / "static"))
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


app = create_app()

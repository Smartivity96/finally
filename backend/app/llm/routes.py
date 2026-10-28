"""Chat API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(body: ChatRequest, request: Request):
    message = body.message.strip()
    if not message:
        return JSONResponse(status_code=400, content={"error": "Message must not be empty"})
    state = request.app.state
    return await service.handle_chat(message, state.price_cache, state.market_source)


@router.get("/history")
async def history():
    return service.get_history()

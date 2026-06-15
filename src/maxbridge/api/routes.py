from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from maxbridge.api.dependencies import get_max_webhook_adapter, get_telegram_webhook_adapter
from maxbridge.api.schemas import HealthResponse, MaxWebhookPayload
from maxbridge.api.webhook_adapters import MaxWebhookAdapter, TelegramWebhookAdapter
from maxbridge.infrastructure.config import Settings, get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/u/{public_id}")
async def redirect_to_telegram(
    public_id: str,
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    bot_username = settings.telegram_bot_username
    target = f"https://t.me/{bot_username}?start={quote(public_id, safe='')}"
    return RedirectResponse(url=target, status_code=302)


@router.post("/api/internal/telegram/webhook")
async def telegram_webhook(
    payload: dict[str, Any],
    adapter: TelegramWebhookAdapter = Depends(get_telegram_webhook_adapter),
) -> dict[str, bool]:
    return await adapter.handle_update(payload)


@router.post("/api/internal/max/webhook")
async def max_webhook(
    payload: MaxWebhookPayload,
    adapter: MaxWebhookAdapter = Depends(get_max_webhook_adapter),
) -> dict[str, bool]:
    return await adapter.handle_payload(payload)

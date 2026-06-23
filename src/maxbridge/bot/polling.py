from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

from maxbridge.api.webhook_adapters import TelegramWebhookAdapter
from maxbridge.application.use_cases import (
    SendTelegramMessageToMaxUseCase,
    StartTelegramConversationUseCase,
)
from maxbridge.infrastructure.config import get_settings
from maxbridge.infrastructure.db import async_session_factory, dispose_engine
from maxbridge.infrastructure.gateways import AiogramTelegramGateway, MockMaxGateway
from maxbridge.infrastructure.rate_limit import InMemoryRateLimiter
from maxbridge.infrastructure.unit_of_work import SqlAlchemyUnitOfWorkFactory

logger = logging.getLogger(__name__)


def build_telegram_polling_adapter(bot: Bot) -> TelegramWebhookAdapter:
    settings = get_settings()
    uow_factory = SqlAlchemyUnitOfWorkFactory(async_session_factory)
    telegram_gateway = AiogramTelegramGateway(bot)
    max_gateway = MockMaxGateway()
    rate_limiter = InMemoryRateLimiter(
        window_seconds=settings.rate_limit_window_seconds,
        max_messages=settings.rate_limit_max_messages,
    )

    return TelegramWebhookAdapter(
        start_conversation=StartTelegramConversationUseCase(
            uow_factory=uow_factory,
            telegram_gateway=telegram_gateway,
        ),
        send_message_to_max=SendTelegramMessageToMaxUseCase(
            uow_factory=uow_factory,
            max_gateway=max_gateway,
            rate_limiter=rate_limiter,
            max_message_length=settings.max_message_length,
        ),
        telegram_gateway=telegram_gateway,
    )


async def run_polling() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    adapter = build_telegram_polling_adapter(bot)

    @dispatcher.message(F.text)
    async def handle_text_message(message: Message) -> None:
        await adapter.handle_message(message)

    try:
        await bot.delete_webhook(drop_pending_updates=settings.telegram_drop_pending_updates)
        logger.info("Starting Telegram polling for @%s", settings.telegram_bot_username)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await dispose_engine()


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()

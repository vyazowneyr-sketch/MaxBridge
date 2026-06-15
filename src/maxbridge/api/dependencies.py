from __future__ import annotations

from functools import lru_cache

from aiogram import Bot
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from maxbridge.api.webhook_adapters import MaxWebhookAdapter, TelegramWebhookAdapter
from maxbridge.application.ports import ConversationRepository, MessageRepository, UserRepository
from maxbridge.application.use_cases import (
    GetConversationUseCase,
    GetPublicLinkUseCase,
    RegisterMaxUserUseCase,
    SendMaxReplyToTelegramUseCase,
    SendTelegramMessageToMaxUseCase,
    StartTelegramConversationUseCase,
)
from maxbridge.infrastructure.config import Settings, get_settings
from maxbridge.infrastructure.db import async_session_factory, get_session
from maxbridge.infrastructure.gateways import AiogramTelegramGateway, MockMaxGateway
from maxbridge.infrastructure.rate_limit import InMemoryRateLimiter
from maxbridge.infrastructure.repositories import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
    SqlAlchemyUserRepository,
)
from maxbridge.infrastructure.unit_of_work import SqlAlchemyUnitOfWorkFactory

_telegram_bot: Bot | None = None
_telegram_bot_token: str | None = None


def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_conversation_repository(
    session: AsyncSession = Depends(get_session),
) -> ConversationRepository:
    return SqlAlchemyConversationRepository(session)


def get_message_repository(
    session: AsyncSession = Depends(get_session),
) -> MessageRepository:
    return SqlAlchemyMessageRepository(session)


@lru_cache
def get_uow_factory() -> SqlAlchemyUnitOfWorkFactory:
    return SqlAlchemyUnitOfWorkFactory(async_session_factory)


def get_telegram_bot(settings: Settings = Depends(get_settings)) -> Bot:
    global _telegram_bot, _telegram_bot_token
    if _telegram_bot is None or _telegram_bot_token != settings.telegram_bot_token:
        _telegram_bot = Bot(token=settings.telegram_bot_token)
        _telegram_bot_token = settings.telegram_bot_token
    return _telegram_bot


async def close_telegram_bot() -> None:
    if _telegram_bot is not None:
        await _telegram_bot.session.close()


def get_telegram_gateway(bot: Bot = Depends(get_telegram_bot)) -> AiogramTelegramGateway:
    return AiogramTelegramGateway(bot)


@lru_cache
def get_max_gateway() -> MockMaxGateway:
    return MockMaxGateway()


@lru_cache
def get_rate_limiter() -> InMemoryRateLimiter:
    settings = get_settings()
    return InMemoryRateLimiter(
        window_seconds=settings.rate_limit_window_seconds,
        max_messages=settings.rate_limit_max_messages,
    )


def get_register_max_user_use_case(
    settings: Settings = Depends(get_settings),
    uow_factory: SqlAlchemyUnitOfWorkFactory = Depends(get_uow_factory),
) -> RegisterMaxUserUseCase:
    return RegisterMaxUserUseCase(
        uow_factory=uow_factory,
        public_base_url=settings.public_base_url,
    )


def get_public_link_use_case(
    settings: Settings = Depends(get_settings),
    uow_factory: SqlAlchemyUnitOfWorkFactory = Depends(get_uow_factory),
) -> GetPublicLinkUseCase:
    return GetPublicLinkUseCase(
        uow_factory=uow_factory,
        public_base_url=settings.public_base_url,
    )


def get_start_telegram_conversation_use_case(
    uow_factory: SqlAlchemyUnitOfWorkFactory = Depends(get_uow_factory),
    telegram_gateway: AiogramTelegramGateway = Depends(get_telegram_gateway),
) -> StartTelegramConversationUseCase:
    return StartTelegramConversationUseCase(
        uow_factory=uow_factory,
        telegram_gateway=telegram_gateway,
    )


def get_send_telegram_message_to_max_use_case(
    settings: Settings = Depends(get_settings),
    uow_factory: SqlAlchemyUnitOfWorkFactory = Depends(get_uow_factory),
    max_gateway: MockMaxGateway = Depends(get_max_gateway),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> SendTelegramMessageToMaxUseCase:
    return SendTelegramMessageToMaxUseCase(
        uow_factory=uow_factory,
        max_gateway=max_gateway,
        rate_limiter=rate_limiter,
        max_message_length=settings.max_message_length,
    )


def get_send_max_reply_to_telegram_use_case(
    settings: Settings = Depends(get_settings),
    uow_factory: SqlAlchemyUnitOfWorkFactory = Depends(get_uow_factory),
    telegram_gateway: AiogramTelegramGateway = Depends(get_telegram_gateway),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> SendMaxReplyToTelegramUseCase:
    return SendMaxReplyToTelegramUseCase(
        uow_factory=uow_factory,
        telegram_gateway=telegram_gateway,
        rate_limiter=rate_limiter,
        max_message_length=settings.max_message_length,
    )


def get_conversation_use_case(
    uow_factory: SqlAlchemyUnitOfWorkFactory = Depends(get_uow_factory),
) -> GetConversationUseCase:
    return GetConversationUseCase(uow_factory=uow_factory)


def get_telegram_webhook_adapter(
    start_conversation: StartTelegramConversationUseCase = Depends(
        get_start_telegram_conversation_use_case,
    ),
    send_message_to_max: SendTelegramMessageToMaxUseCase = Depends(
        get_send_telegram_message_to_max_use_case,
    ),
    telegram_gateway: AiogramTelegramGateway = Depends(get_telegram_gateway),
) -> TelegramWebhookAdapter:
    return TelegramWebhookAdapter(
        start_conversation=start_conversation,
        send_message_to_max=send_message_to_max,
        telegram_gateway=telegram_gateway,
    )


def get_max_webhook_adapter(
    register_max_user: RegisterMaxUserUseCase = Depends(get_register_max_user_use_case),
    send_reply_to_telegram: SendMaxReplyToTelegramUseCase = Depends(
        get_send_max_reply_to_telegram_use_case,
    ),
    max_gateway: MockMaxGateway = Depends(get_max_gateway),
) -> MaxWebhookAdapter:
    return MaxWebhookAdapter(
        register_max_user=register_max_user,
        send_reply_to_telegram=send_reply_to_telegram,
        max_gateway=max_gateway,
    )

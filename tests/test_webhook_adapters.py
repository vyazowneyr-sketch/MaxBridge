from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from maxbridge.api.schemas import MaxWebhookPayload
from maxbridge.api.webhook_adapters import MaxWebhookAdapter, TelegramWebhookAdapter
from maxbridge.application.services import NoopRateLimiter
from maxbridge.application.use_cases import (
    RegisterMaxUserUseCase,
    SendMaxReplyToTelegramUseCase,
    SendTelegramMessageToMaxUseCase,
    StartTelegramConversationUseCase,
)
from tests.fakes import (
    FakeMaxGateway,
    FakeTelegramGateway,
    FakeUnitOfWorkFactory,
    InMemoryStore,
)


def run(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def test_telegram_start_command_with_bot_mention_creates_conversation() -> None:
    async def scenario() -> None:
        store, adapter, telegram_gateway = await build_telegram_adapter()

        result = await adapter.handle_update(telegram_update("/start@MaxBridgeBot public123"))

        assert result == {"ok": True}
        assert len(store.conversations) == 1
        assert telegram_gateway.messages[-1].recipient_id == "1001"
        assert "Диалог создан" in telegram_gateway.messages[-1].text

    run(scenario())


def test_telegram_start_with_unknown_public_id_returns_user_message() -> None:
    async def scenario() -> None:
        store, adapter, telegram_gateway = await build_telegram_adapter()

        result = await adapter.handle_update(telegram_update("/start missing"))

        assert result == {"ok": True}
        assert len(store.conversations) == 0
        assert "не найдена" in telegram_gateway.messages[-1].text

    run(scenario())


def test_telegram_does_not_treat_startup_as_start_command() -> None:
    async def scenario() -> None:
        store, adapter, telegram_gateway = await build_telegram_adapter()

        result = await adapter.handle_update(telegram_update("/startup public123"))

        assert result == {"ok": True}
        assert len(store.conversations) == 0
        assert "Активный диалог не найден" in telegram_gateway.messages[-1].text

    run(scenario())


def test_max_does_not_treat_startup_as_start_command() -> None:
    async def scenario() -> None:
        store, adapter, max_gateway = build_max_adapter()

        result = await adapter.handle_payload(
            MaxWebhookPayload(user_id="max-1", text="/startup public123"),
        )

        assert result == {"ok": True}
        assert len(store.users) == 0
        assert "Отправьте /start" in max_gateway.messages[-1].text

    run(scenario())


def test_max_empty_reply_returns_user_message() -> None:
    async def scenario() -> None:
        _, adapter, max_gateway = build_max_adapter()

        result = await adapter.handle_payload(MaxWebhookPayload(user_id="max-1", text="   "))

        assert result == {"ok": True}
        assert "Сообщение пустое" in max_gateway.messages[-1].text

    run(scenario())


async def build_telegram_adapter() -> tuple[
    InMemoryStore,
    TelegramWebhookAdapter,
    FakeTelegramGateway,
]:
    store = InMemoryStore()
    uow_factory = FakeUnitOfWorkFactory(store)
    telegram_gateway = FakeTelegramGateway()
    max_gateway = FakeMaxGateway()
    register = RegisterMaxUserUseCase(
        uow_factory,
        "https://maxbridge.app",
        public_id_generator=lambda: "public123",
    )
    await register("max-1")
    adapter = TelegramWebhookAdapter(
        StartTelegramConversationUseCase(uow_factory, telegram_gateway),
        SendTelegramMessageToMaxUseCase(
            uow_factory,
            max_gateway,
            NoopRateLimiter(),
            max_message_length=4000,
        ),
        telegram_gateway,
    )
    return store, adapter, telegram_gateway


def build_max_adapter() -> tuple[InMemoryStore, MaxWebhookAdapter, FakeMaxGateway]:
    store = InMemoryStore()
    uow_factory = FakeUnitOfWorkFactory(store)
    telegram_gateway = FakeTelegramGateway()
    max_gateway = FakeMaxGateway()
    adapter = MaxWebhookAdapter(
        RegisterMaxUserUseCase(
            uow_factory,
            "https://maxbridge.app",
            public_id_generator=lambda: "public123",
        ),
        SendMaxReplyToTelegramUseCase(
            uow_factory,
            telegram_gateway,
            NoopRateLimiter(),
            max_message_length=4000,
        ),
        max_gateway,
    )
    return store, adapter, max_gateway


def telegram_update(text: str) -> dict[str, Any]:
    return {
        "update_id": 42,
        "message": {
            "message_id": 10,
            "date": 1_700_000_000,
            "chat": {"id": 1001, "type": "private", "first_name": "Ivan"},
            "from": {
                "id": 1001,
                "is_bot": False,
                "first_name": "Ivan",
                "username": "ivan",
            },
            "text": text,
        },
    }

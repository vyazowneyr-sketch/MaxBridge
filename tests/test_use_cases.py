from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest

from maxbridge.application.services import NoopRateLimiter
from maxbridge.application.use_cases import (
    RegisterMaxUserUseCase,
    SendMaxReplyToTelegramUseCase,
    SendTelegramMessageToMaxUseCase,
    StartTelegramConversationUseCase,
)
from maxbridge.domain.entities import SenderType
from maxbridge.domain.exceptions import EmptyMessage, MessageTooLong, RateLimitExceeded
from tests.fakes import (
    FakeMaxGateway,
    FakeTelegramGateway,
    FakeUnitOfWorkFactory,
    InMemoryStore,
    RejectingRateLimiter,
)


def run(coro: Coroutine[Any, Any, None]) -> None:
    return asyncio.run(coro)


def test_registers_new_max_user() -> None:
    async def scenario() -> None:
        store = InMemoryStore()
        use_case = RegisterMaxUserUseCase(
            FakeUnitOfWorkFactory(store),
            "https://maxbridge.app",
            public_id_generator=lambda: "public123",
        )

        link = await use_case("max-1")

        assert link.public_id == "public123"
        assert link.url == "https://maxbridge.app/u/public123"
        assert len(store.users) == 1
        assert next(iter(store.users.values())).max_user_id == "max-1"

    run(scenario())


def test_registering_existing_max_user_returns_existing_link() -> None:
    async def scenario() -> None:
        store = InMemoryStore()
        public_ids = iter(["firstid", "secondid"])
        use_case = RegisterMaxUserUseCase(
            FakeUnitOfWorkFactory(store),
            "https://maxbridge.app",
            public_id_generator=lambda: next(public_ids),
        )

        first = await use_case("max-1")
        second = await use_case("max-1")

        assert first == second
        assert second.public_id == "firstid"
        assert len(store.users) == 1

    run(scenario())


def test_starts_telegram_conversation_by_public_id() -> None:
    async def scenario() -> None:
        store = InMemoryStore()
        uow_factory = FakeUnitOfWorkFactory(store)
        telegram_gateway = FakeTelegramGateway()
        register = RegisterMaxUserUseCase(
            uow_factory,
            "https://maxbridge.app",
            public_id_generator=lambda: "public123",
        )
        await register("max-1")
        use_case = StartTelegramConversationUseCase(uow_factory, telegram_gateway)

        conversation = await use_case(
            public_id="public123",
            telegram_user_id="tg-1",
            telegram_username="ivan",
            telegram_first_name="Иван",
        )

        assert conversation.telegram_user_id == "tg-1"
        assert len(store.conversations) == 1
        assert telegram_gateway.messages[-1].recipient_id == "tg-1"

    run(scenario())


def test_sends_telegram_message_to_max() -> None:
    async def scenario() -> None:
        store, uow_factory, _, max_gateway = await prepared_conversation()
        use_case = SendTelegramMessageToMaxUseCase(
            uow_factory,
            max_gateway,
            NoopRateLimiter(),
            max_message_length=4000,
        )

        message = await use_case(telegram_user_id="tg-1", text="Привет")

        assert message.sender_type == SenderType.TELEGRAM
        assert store.messages[-1].text == "Привет"
        assert max_gateway.messages[-1].recipient_id == "max-1"
        assert "Новое сообщение из Telegram" in max_gateway.messages[-1].text

    run(scenario())


def test_sends_max_reply_to_telegram() -> None:
    async def scenario() -> None:
        store, uow_factory, telegram_gateway, _ = await prepared_conversation()
        use_case = SendMaxReplyToTelegramUseCase(
            uow_factory,
            telegram_gateway,
            NoopRateLimiter(),
            max_message_length=4000,
        )

        message = await use_case(max_user_id="max-1", text="Здравствуйте")

        assert message.sender_type == SenderType.MAX
        assert store.messages[-1].text == "Здравствуйте"
        assert telegram_gateway.messages[-1].recipient_id == "tg-1"
        assert telegram_gateway.messages[-1].text == "Здравствуйте"

    run(scenario())


def test_rejects_empty_message() -> None:
    async def scenario() -> None:
        store, uow_factory, _, max_gateway = await prepared_conversation()
        use_case = SendTelegramMessageToMaxUseCase(
            uow_factory,
            max_gateway,
            NoopRateLimiter(),
            max_message_length=4000,
        )

        with pytest.raises(EmptyMessage):
            await use_case(telegram_user_id="tg-1", text="   ")
        assert store.messages == []

    run(scenario())


def test_rejects_too_long_message() -> None:
    async def scenario() -> None:
        store, uow_factory, _, max_gateway = await prepared_conversation()
        use_case = SendTelegramMessageToMaxUseCase(
            uow_factory,
            max_gateway,
            NoopRateLimiter(),
            max_message_length=5,
        )

        with pytest.raises(MessageTooLong):
            await use_case(telegram_user_id="tg-1", text="123456")
        assert store.messages == []

    run(scenario())


def test_rejects_rate_limited_message_before_persisting() -> None:
    async def scenario() -> None:
        store, uow_factory, _, max_gateway = await prepared_conversation()
        use_case = SendTelegramMessageToMaxUseCase(
            uow_factory,
            max_gateway,
            RejectingRateLimiter(),
            max_message_length=4000,
        )

        with pytest.raises(RateLimitExceeded):
            await use_case(telegram_user_id="tg-1", text="Привет")
        assert store.messages == []
        assert max_gateway.messages == []

    run(scenario())


async def prepared_conversation() -> tuple[
    InMemoryStore,
    FakeUnitOfWorkFactory,
    FakeTelegramGateway,
    FakeMaxGateway,
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
    start_conversation = StartTelegramConversationUseCase(uow_factory, telegram_gateway)
    await start_conversation(
        public_id="public123",
        telegram_user_id="tg-1",
        telegram_username="ivan",
        telegram_first_name="Иван",
    )
    telegram_gateway.messages.clear()
    return store, uow_factory, telegram_gateway, max_gateway

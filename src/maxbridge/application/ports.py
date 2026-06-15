from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from maxbridge.domain.entities import Conversation, Message, User


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_max_user_id(self, max_user_id: str) -> User | None: ...

    async def get_by_public_id(self, public_id: str) -> User | None: ...


class ConversationRepository(Protocol):
    async def add(self, conversation: Conversation) -> None: ...

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...

    async def get_latest_active_by_telegram_user_id(
        self,
        telegram_user_id: str,
    ) -> Conversation | None: ...

    async def get_latest_active_by_user_id(self, user_id: UUID) -> Conversation | None: ...


class MessageRepository(Protocol):
    async def add(self, message: Message) -> None: ...


class MaxGateway(Protocol):
    async def send_message(self, max_user_id: str, text: str) -> None: ...


class TelegramGateway(Protocol):
    async def send_message(self, telegram_user_id: str, text: str) -> None: ...


class RateLimiter(Protocol):
    async def check(self, key: str) -> None: ...


class UnitOfWork(Protocol):
    users: UserRepository
    conversations: ConversationRepository
    messages: MessageRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...

from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType
from uuid import UUID

from maxbridge.application.ports import ConversationRepository, MessageRepository, UserRepository
from maxbridge.domain.entities import Conversation, ConversationStatus, Message, User
from maxbridge.domain.exceptions import RateLimitExceeded


@dataclass(slots=True)
class InMemoryStore:
    users: dict[UUID, User] = field(default_factory=dict)
    conversations: dict[UUID, Conversation] = field(default_factory=dict)
    messages: list[Message] = field(default_factory=list)


class FakeUserRepository(UserRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, user: User) -> None:
        self._store.users[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._store.users.get(user_id)

    async def get_by_max_user_id(self, max_user_id: str) -> User | None:
        return next(
            (user for user in self._store.users.values() if user.max_user_id == max_user_id),
            None,
        )

    async def get_by_public_id(self, public_id: str) -> User | None:
        return next(
            (user for user in self._store.users.values() if user.public_id == public_id),
            None,
        )


class FakeConversationRepository(ConversationRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, conversation: Conversation) -> None:
        self._store.conversations[conversation.id] = conversation

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        return self._store.conversations.get(conversation_id)

    async def get_latest_active_by_telegram_user_id(
        self,
        telegram_user_id: str,
    ) -> Conversation | None:
        conversations = [
            conversation
            for conversation in self._store.conversations.values()
            if conversation.telegram_user_id == telegram_user_id
            and conversation.status == ConversationStatus.ACTIVE
        ]
        return max(conversations, key=lambda conversation: conversation.created_at, default=None)

    async def get_latest_active_by_user_id(self, user_id: UUID) -> Conversation | None:
        conversations = [
            conversation
            for conversation in self._store.conversations.values()
            if conversation.user_id == user_id and conversation.status == ConversationStatus.ACTIVE
        ]
        return max(conversations, key=lambda conversation: conversation.created_at, default=None)


class FakeMessageRepository(MessageRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, message: Message) -> None:
        self._store.messages.append(message)


class FakeUnitOfWork:
    users: UserRepository
    conversations: ConversationRepository
    messages: MessageRepository

    def __init__(self, store: InMemoryStore) -> None:
        self.users = FakeUserRepository(store)
        self.conversations = FakeConversationRepository(store)
        self.messages = FakeMessageRepository(store)
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        _ = exc, tb
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeUnitOfWorkFactory:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self.instances: list[FakeUnitOfWork] = []

    def __call__(self) -> FakeUnitOfWork:
        uow = FakeUnitOfWork(self._store)
        self.instances.append(uow)
        return uow


@dataclass(frozen=True, slots=True)
class GatewayMessage:
    recipient_id: str
    text: str


class FakeMaxGateway:
    def __init__(self) -> None:
        self.messages: list[GatewayMessage] = []

    async def send_message(self, max_user_id: str, text: str) -> None:
        self.messages.append(GatewayMessage(recipient_id=max_user_id, text=text))


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.messages: list[GatewayMessage] = []

    async def send_message(self, telegram_user_id: str, text: str) -> None:
        self.messages.append(GatewayMessage(recipient_id=telegram_user_id, text=text))


class RejectingRateLimiter:
    async def check(self, key: str) -> None:
        _ = key
        raise RateLimitExceeded("Rate limit exceeded.")

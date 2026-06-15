from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from maxbridge.application.ports import ConversationRepository, MessageRepository, UserRepository
from maxbridge.infrastructure.repositories import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork:
    users: UserRepository
    conversations: ConversationRepository
    messages: MessageRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self._committed = False
        self.users = SqlAlchemyUserRepository(self._session)
        self.conversations = SqlAlchemyConversationRepository(self._session)
        self.messages = SqlAlchemyMessageRepository(self._session)
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        _ = exc, tb
        session = self._ensure_session()
        if exc_type is not None or not self._committed:
            await self.rollback()
        await session.close()

    async def commit(self) -> None:
        session = self._ensure_session()
        await session.commit()
        self._committed = True

    async def rollback(self) -> None:
        session = self._ensure_session()
        if session.in_transaction():
            await session.rollback()

    def _ensure_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._session


class SqlAlchemyUnitOfWorkFactory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self._session_factory)

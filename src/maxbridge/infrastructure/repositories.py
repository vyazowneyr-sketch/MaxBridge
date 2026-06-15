from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from maxbridge.application.ports import ConversationRepository, MessageRepository, UserRepository
from maxbridge.domain.entities import Conversation, ConversationStatus, Message, User
from maxbridge.infrastructure.models import ConversationModel, MessageModel, UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                max_user_id=user.max_user_id,
                public_id=user.public_id,
                created_at=user.created_at,
            ),
        )
        await self._session.flush()

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _user_from_model(model) if model is not None else None

    async def get_by_max_user_id(self, max_user_id: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.max_user_id == max_user_id),
        )
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model is not None else None

    async def get_by_public_id(self, public_id: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.public_id == public_id),
        )
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model is not None else None


class SqlAlchemyConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> None:
        self._session.add(
            ConversationModel(
                id=conversation.id,
                user_id=conversation.user_id,
                telegram_user_id=conversation.telegram_user_id,
                telegram_username=conversation.telegram_username,
                telegram_first_name=conversation.telegram_first_name,
                status=conversation.status.value,
                created_at=conversation.created_at,
            ),
        )
        await self._session.flush()

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        model = await self._session.get(ConversationModel, conversation_id)
        return _conversation_from_model(model) if model is not None else None

    async def get_latest_active_by_telegram_user_id(
        self,
        telegram_user_id: str,
    ) -> Conversation | None:
        result = await self._session.execute(
            select(ConversationModel)
            .where(
                ConversationModel.telegram_user_id == telegram_user_id,
                ConversationModel.status == ConversationStatus.ACTIVE.value,
            )
            .order_by(ConversationModel.created_at.desc())
            .limit(1),
        )
        model = result.scalar_one_or_none()
        return _conversation_from_model(model) if model is not None else None

    async def get_latest_active_by_user_id(self, user_id: UUID) -> Conversation | None:
        result = await self._session.execute(
            select(ConversationModel)
            .where(
                ConversationModel.user_id == user_id,
                ConversationModel.status == ConversationStatus.ACTIVE.value,
            )
            .order_by(ConversationModel.created_at.desc())
            .limit(1),
        )
        model = result.scalar_one_or_none()
        return _conversation_from_model(model) if model is not None else None


class SqlAlchemyMessageRepository(MessageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: Message) -> None:
        self._session.add(
            MessageModel(
                id=message.id,
                conversation_id=message.conversation_id,
                sender_type=message.sender_type.value,
                text=message.text,
                created_at=message.created_at,
            ),
        )
        await self._session.flush()


def _user_from_model(model: UserModel) -> User:
    return User(
        id=model.id,
        max_user_id=model.max_user_id,
        public_id=model.public_id,
        created_at=model.created_at,
    )


def _conversation_from_model(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id,
        user_id=model.user_id,
        telegram_user_id=model.telegram_user_id,
        telegram_username=model.telegram_username,
        telegram_first_name=model.telegram_first_name,
        status=ConversationStatus(model.status),
        created_at=model.created_at,
    )

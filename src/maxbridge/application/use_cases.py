from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from maxbridge.application.dto import ConversationDTO, MessageDTO, PublicLinkDTO
from maxbridge.application.ports import (
    MaxGateway,
    RateLimiter,
    TelegramGateway,
    UnitOfWork,
    UnitOfWorkFactory,
)
from maxbridge.application.services import (
    build_public_link,
    generate_public_id,
    validate_message_text,
)
from maxbridge.domain.entities import Conversation, Message, SenderType, User
from maxbridge.domain.exceptions import (
    ConversationNotFound,
    MaxBridgeError,
    PublicIdNotFound,
    UserNotFound,
)

PublicIdGenerator = Callable[[], str]


class RegisterMaxUserUseCase:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        public_base_url: str,
        public_id_generator: PublicIdGenerator = generate_public_id,
    ) -> None:
        self._uow_factory = uow_factory
        self._public_base_url = public_base_url
        self._public_id_generator = public_id_generator

    async def __call__(self, max_user_id: str) -> PublicLinkDTO:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_max_user_id(max_user_id)
            if user is None:
                public_id = await self._generate_unique_public_id(uow)
                user = User.create(max_user_id=max_user_id, public_id=public_id)
                await uow.users.add(user)

            await uow.commit()

        return PublicLinkDTO(
            public_id=user.public_id,
            url=build_public_link(self._public_base_url, user.public_id),
        )

    async def _generate_unique_public_id(self, uow: UnitOfWork) -> str:
        for _ in range(10):
            public_id = self._public_id_generator()
            if await uow.users.get_by_public_id(public_id) is None:
                return public_id
        raise MaxBridgeError("Could not generate a unique public_id.")


class GetPublicLinkUseCase:
    def __init__(self, uow_factory: UnitOfWorkFactory, public_base_url: str) -> None:
        self._uow_factory = uow_factory
        self._public_base_url = public_base_url

    async def __call__(self, max_user_id: str) -> PublicLinkDTO:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_max_user_id(max_user_id)
            if user is None:
                raise UserNotFound("Max user was not found.")

        return PublicLinkDTO(
            public_id=user.public_id,
            url=build_public_link(self._public_base_url, user.public_id),
        )


class StartTelegramConversationUseCase:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        telegram_gateway: TelegramGateway,
    ) -> None:
        self._uow_factory = uow_factory
        self._telegram_gateway = telegram_gateway

    async def __call__(
        self,
        *,
        public_id: str,
        telegram_user_id: str,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> ConversationDTO:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_public_id(public_id)
            if user is None:
                raise PublicIdNotFound("Public id was not found.")

            conversation = Conversation.create(
                user_id=user.id,
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                telegram_first_name=telegram_first_name,
            )
            await uow.conversations.add(conversation)
            await uow.commit()

        await self._telegram_gateway.send_message(
            telegram_user_id,
            "Диалог создан. Напишите сообщение, и я передам его пользователю Max.",
        )
        return ConversationDTO.from_entity(conversation)


class SendTelegramMessageToMaxUseCase:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        max_gateway: MaxGateway,
        rate_limiter: RateLimiter,
        max_message_length: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._max_gateway = max_gateway
        self._rate_limiter = rate_limiter
        self._max_message_length = max_message_length

    async def __call__(self, *, telegram_user_id: str, text: str) -> MessageDTO:
        normalized_text = validate_message_text(text, self._max_message_length)
        await self._rate_limiter.check(f"telegram:{telegram_user_id}")

        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_latest_active_by_telegram_user_id(
                telegram_user_id,
            )
            if conversation is None:
                raise ConversationNotFound("Active Telegram conversation was not found.")

            user = await uow.users.get_by_id(conversation.user_id)
            if user is None:
                raise UserNotFound("Max user was not found.")

            message = Message.create(
                conversation_id=conversation.id,
                sender_type=SenderType.TELEGRAM,
                text=normalized_text,
            )
            await uow.messages.add(message)
            await uow.commit()

        await self._max_gateway.send_message(
            user.max_user_id,
            self._format_message_for_max(conversation, normalized_text),
        )
        return MessageDTO.from_entity(message)

    @staticmethod
    def _format_message_for_max(conversation: Conversation, text: str) -> str:
        first_name = conversation.telegram_first_name or "не указано"
        username = (
            f"@{conversation.telegram_username}" if conversation.telegram_username else "не указан"
        )
        return (
            "Новое сообщение из Telegram\n"
            f"Имя: {first_name}\n"
            f"Telegram: {username}\n"
            f"Текст: {text}\n\n"
            "Ответьте на это сообщение, чтобы отправить ответ обратно в Telegram."
        )


class SendMaxReplyToTelegramUseCase:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        telegram_gateway: TelegramGateway,
        rate_limiter: RateLimiter,
        max_message_length: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._telegram_gateway = telegram_gateway
        self._rate_limiter = rate_limiter
        self._max_message_length = max_message_length

    async def __call__(self, *, max_user_id: str, text: str) -> MessageDTO:
        normalized_text = validate_message_text(text, self._max_message_length)
        await self._rate_limiter.check(f"max:{max_user_id}")

        async with self._uow_factory() as uow:
            user = await uow.users.get_by_max_user_id(max_user_id)
            if user is None:
                raise UserNotFound("Max user was not found.")

            conversation = await uow.conversations.get_latest_active_by_user_id(user.id)
            if conversation is None:
                raise ConversationNotFound("Active Max conversation was not found.")

            message = Message.create(
                conversation_id=conversation.id,
                sender_type=SenderType.MAX,
                text=normalized_text,
            )
            await uow.messages.add(message)
            await uow.commit()

        await self._telegram_gateway.send_message(conversation.telegram_user_id, normalized_text)
        return MessageDTO.from_entity(message)


class GetConversationUseCase:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def __call__(self, conversation_id: UUID) -> ConversationDTO:
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id)
            if conversation is None:
                raise ConversationNotFound("Conversation was not found.")
            return ConversationDTO.from_entity(conversation)

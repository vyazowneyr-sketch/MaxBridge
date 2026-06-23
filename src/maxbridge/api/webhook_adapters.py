from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aiogram.types import Message as TelegramMessage
from aiogram.types import Update

from maxbridge.api.schemas import MaxWebhookPayload
from maxbridge.application.ports import MaxGateway, TelegramGateway
from maxbridge.application.use_cases import (
    RegisterMaxUserUseCase,
    SendMaxReplyToTelegramUseCase,
    SendTelegramMessageToMaxUseCase,
    StartTelegramConversationUseCase,
)
from maxbridge.domain.exceptions import (
    ConversationNotFound,
    EmptyMessage,
    MessageTooLong,
    PublicIdNotFound,
    RateLimitExceeded,
    UserNotFound,
)


@dataclass(frozen=True, slots=True)
class StartCommand:
    is_start: bool
    payload: str | None


class TelegramWebhookAdapter:
    def __init__(
        self,
        start_conversation: StartTelegramConversationUseCase,
        send_message_to_max: SendTelegramMessageToMaxUseCase,
        telegram_gateway: TelegramGateway,
    ) -> None:
        self._start_conversation = start_conversation
        self._send_message_to_max = send_message_to_max
        self._telegram_gateway = telegram_gateway

    async def handle_update(self, payload: Mapping[str, Any]) -> dict[str, bool]:
        update = Update.model_validate(payload)
        message = update.message
        if message is None:
            return {"ok": True}

        await self.handle_message(message)
        return {"ok": True}

    async def handle_message(self, message: TelegramMessage) -> None:
        if message.text is None or message.from_user is None:
            return

        telegram_user = message.from_user
        telegram_user_id = str(telegram_user.id)
        text = message.text

        start_command = self._parse_start_command(text)
        if start_command.is_start:
            public_id = start_command.payload
            if public_id is None:
                await self._telegram_gateway.send_message(
                    telegram_user_id,
                    "Откройте публичную ссылку MaxBridge и нажмите Start в этом боте.",
                )
                return

            try:
                await self._start_conversation(
                    public_id=public_id,
                    telegram_user_id=telegram_user_id,
                    telegram_username=telegram_user.username,
                    telegram_first_name=telegram_user.first_name,
                )
            except PublicIdNotFound:
                await self._telegram_gateway.send_message(
                    telegram_user_id,
                    "Публичная ссылка MaxBridge не найдена или уже недействительна.",
                )
            return

        try:
            await self._send_message_to_max(telegram_user_id=telegram_user_id, text=text)
        except EmptyMessage:
            await self._telegram_gateway.send_message(
                telegram_user_id,
                "Сообщение пустое. Напишите текст, который нужно передать в Max.",
            )
        except MessageTooLong:
            await self._telegram_gateway.send_message(
                telegram_user_id,
                "Сообщение слишком длинное. Сократите текст и отправьте его снова.",
            )
        except RateLimitExceeded:
            await self._telegram_gateway.send_message(
                telegram_user_id,
                "Слишком много сообщений подряд. Подождите немного и попробуйте снова.",
            )
        except (ConversationNotFound, UserNotFound):
            await self._telegram_gateway.send_message(
                telegram_user_id,
                "Активный диалог не найден. Откройте публичную ссылку MaxBridge заново.",
            )

    @staticmethod
    def _parse_start_command(text: str) -> StartCommand:
        parts = text.split(maxsplit=1)
        if not parts:
            return StartCommand(is_start=False, payload=None)

        command = parts[0].split("@", maxsplit=1)[0]
        if command != "/start":
            return StartCommand(is_start=False, payload=None)

        payload = parts[1].strip() if len(parts) > 1 else None
        return StartCommand(is_start=True, payload=payload or None)


class MaxWebhookAdapter:
    def __init__(
        self,
        register_max_user: RegisterMaxUserUseCase,
        send_reply_to_telegram: SendMaxReplyToTelegramUseCase,
        max_gateway: MaxGateway,
    ) -> None:
        self._register_max_user = register_max_user
        self._send_reply_to_telegram = send_reply_to_telegram
        self._max_gateway = max_gateway

    async def handle_payload(self, payload: MaxWebhookPayload) -> dict[str, bool]:
        text = payload.text.strip()
        if self._is_start_command(text):
            public_link = await self._register_max_user(payload.user_id)
            await self._max_gateway.send_message(
                payload.user_id,
                f"Ваша публичная ссылка MaxBridge:\n{public_link.url}",
            )
            return {"ok": True}

        try:
            await self._send_reply_to_telegram(max_user_id=payload.user_id, text=payload.text)
        except EmptyMessage:
            await self._max_gateway.send_message(
                payload.user_id,
                "Сообщение пустое. Напишите текст ответа для Telegram-пользователя.",
            )
        except MessageTooLong:
            await self._max_gateway.send_message(
                payload.user_id,
                "Сообщение слишком длинное. Сократите текст и отправьте его снова.",
            )
        except RateLimitExceeded:
            await self._max_gateway.send_message(
                payload.user_id,
                "Слишком много сообщений подряд. Подождите немного и попробуйте снова.",
            )
        except ConversationNotFound:
            await self._max_gateway.send_message(
                payload.user_id,
                "Активный Telegram-диалог не найден. Дождитесь нового входящего сообщения.",
            )
        except UserNotFound:
            await self._max_gateway.send_message(
                payload.user_id,
                "Профиль MaxBridge не найден. Отправьте /start, чтобы получить публичную ссылку.",
            )
        return {"ok": True}

    @staticmethod
    def _is_start_command(text: str) -> bool:
        parts = text.split(maxsplit=1)
        return bool(parts) and parts[0] == "/start"

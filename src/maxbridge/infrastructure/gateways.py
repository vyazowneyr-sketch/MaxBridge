from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot

from maxbridge.application.ports import MaxGateway, TelegramGateway

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SentMaxMessage:
    max_user_id: str
    text: str


class AiogramTelegramGateway(TelegramGateway):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(self, telegram_user_id: str, text: str) -> None:
        chat_id: int | str
        chat_id = (
            int(telegram_user_id) if telegram_user_id.lstrip("-").isdigit() else telegram_user_id
        )
        await self._bot.send_message(chat_id=chat_id, text=text)


class MockMaxGateway(MaxGateway):
    def __init__(self) -> None:
        self.sent_messages: list[SentMaxMessage] = []

    async def send_message(self, max_user_id: str, text: str) -> None:
        self.sent_messages.append(SentMaxMessage(max_user_id=max_user_id, text=text))
        logger.info("Mock Max message to %s: %s", max_user_id, text)

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class SenderType(StrEnum):
    TELEGRAM = "telegram"
    MAX = "max"


@dataclass(slots=True)
class User:
    id: UUID
    max_user_id: str
    public_id: str
    created_at: datetime

    @classmethod
    def create(cls, max_user_id: str, public_id: str) -> User:
        return cls(
            id=uuid4(),
            max_user_id=max_user_id,
            public_id=public_id,
            created_at=utc_now(),
        )


@dataclass(slots=True)
class Conversation:
    id: UUID
    user_id: UUID
    telegram_user_id: str
    telegram_username: str | None
    telegram_first_name: str | None
    status: ConversationStatus
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        telegram_user_id: str,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> Conversation:
        return cls(
            id=uuid4(),
            user_id=user_id,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            telegram_first_name=telegram_first_name,
            status=ConversationStatus.ACTIVE,
            created_at=utc_now(),
        )


@dataclass(slots=True)
class Message:
    id: UUID
    conversation_id: UUID
    sender_type: SenderType
    text: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        conversation_id: UUID,
        sender_type: SenderType,
        text: str,
    ) -> Message:
        return cls(
            id=uuid4(),
            conversation_id=conversation_id,
            sender_type=sender_type,
            text=text,
            created_at=utc_now(),
        )

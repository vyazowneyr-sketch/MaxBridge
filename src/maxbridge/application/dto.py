from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from maxbridge.domain.entities import Conversation, ConversationStatus, Message, SenderType


@dataclass(frozen=True, slots=True)
class PublicLinkDTO:
    public_id: str
    url: str


@dataclass(frozen=True, slots=True)
class ConversationDTO:
    id: UUID
    user_id: UUID
    telegram_user_id: str
    telegram_username: str | None
    telegram_first_name: str | None
    status: ConversationStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, conversation: Conversation) -> ConversationDTO:
        return cls(
            id=conversation.id,
            user_id=conversation.user_id,
            telegram_user_id=conversation.telegram_user_id,
            telegram_username=conversation.telegram_username,
            telegram_first_name=conversation.telegram_first_name,
            status=conversation.status,
            created_at=conversation.created_at,
        )


@dataclass(frozen=True, slots=True)
class MessageDTO:
    id: UUID
    conversation_id: UUID
    sender_type: SenderType
    text: str
    created_at: datetime

    @classmethod
    def from_entity(cls, message: Message) -> MessageDTO:
        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_type=message.sender_type,
            text=message.text,
            created_at=message.created_at,
        )

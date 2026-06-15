from __future__ import annotations

import secrets
import string

from maxbridge.application.ports import RateLimiter
from maxbridge.domain.exceptions import EmptyMessage, MessageTooLong

PUBLIC_ID_ALPHABET = string.ascii_letters + string.digits


def generate_public_id(length: int = 10) -> str:
    if length < 1:
        raise ValueError("public_id length must be positive.")
    return "".join(secrets.choice(PUBLIC_ID_ALPHABET) for _ in range(length))


def build_public_link(public_base_url: str, public_id: str) -> str:
    return f"{public_base_url.rstrip('/')}/u/{public_id}"


def validate_message_text(text: str, max_length: int) -> str:
    normalized = text.strip()
    if not normalized:
        raise EmptyMessage("Message text is empty.")
    if len(normalized) > max_length:
        raise MessageTooLong(f"Message text exceeds {max_length} characters.")
    return normalized


class NoopRateLimiter(RateLimiter):
    async def check(self, key: str) -> None:
        _ = key

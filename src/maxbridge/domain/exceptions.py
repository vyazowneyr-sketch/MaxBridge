class MaxBridgeError(Exception):
    """Base application/domain exception."""


class UserNotFound(MaxBridgeError):
    """Max user was not found."""


class ConversationNotFound(MaxBridgeError):
    """Active conversation was not found."""


class PublicIdNotFound(MaxBridgeError):
    """Public link id was not found."""


class EmptyMessage(MaxBridgeError):
    """Message text is empty."""


class MessageTooLong(MaxBridgeError):
    """Message text is longer than the configured limit."""


class RateLimitExceeded(MaxBridgeError):
    """User or IP has exceeded the allowed request rate."""

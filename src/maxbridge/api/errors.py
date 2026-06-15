from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from maxbridge.domain.exceptions import (
    ConversationNotFound,
    EmptyMessage,
    MaxBridgeError,
    MessageTooLong,
    PublicIdNotFound,
    RateLimitExceeded,
    UserNotFound,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MaxBridgeError)
    async def handle_maxbridge_error(request: Request, exc: MaxBridgeError) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=_status_code_for(exc),
            content={"detail": str(exc) or exc.__class__.__name__},
        )


def _status_code_for(exc: MaxBridgeError) -> int:
    if isinstance(exc, RateLimitExceeded):
        return status.HTTP_429_TOO_MANY_REQUESTS
    if isinstance(exc, UserNotFound | ConversationNotFound | PublicIdNotFound):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, EmptyMessage | MessageTooLong):
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_400_BAD_REQUEST

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from maxbridge.api.dependencies import close_telegram_bot
from maxbridge.api.errors import register_exception_handlers
from maxbridge.api.routes import router
from maxbridge.infrastructure.config import get_settings
from maxbridge.infrastructure.db import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ = app
    yield
    await close_telegram_bot()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()

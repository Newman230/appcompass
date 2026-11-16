"""AppCompass API entry point: `uvicorn app.main:app`."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__, errors
from .api import apps, health, sessions
from .config import get_settings
from .db import close_pool, migrate, open_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    pool = open_pool(settings.database_url)
    if settings.run_migrations:
        migrate(pool)
    yield
    close_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AppCompass API",
        version=__version__,
        summary="In-app AI support agent: your app guide",
        lifespan=lifespan,
    )
    errors.install(app)
    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(apps.router)
    return app


app = create_app()

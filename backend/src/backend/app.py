"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import backend.models  # noqa: F401  # ensure ORM tables register on Base.metadata
from backend.api.health import router as health_router
from backend.core import database
from backend.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create tables on startup so fresh volumes (e.g. Postgres) work."""
    await database.init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health_router)
    return app


# ASGI entrypoint: `uv run uvicorn backend.app:app --reload`
app = create_app()

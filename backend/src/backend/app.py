"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import backend.models  # noqa: F401  # ensure ORM tables register on Base.metadata
from backend.api.examples import router as examples_router
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(examples_router)
    return app


# ASGI entrypoint: `uv run uvicorn backend.app:app --reload`
app = create_app()

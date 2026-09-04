"""FastAPI application factory."""

from fastapi import FastAPI

from backend.api.health import router as health_router
from backend.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    return app


# ASGI entrypoint: `uv run uvicorn backend.app:app --reload`
app = create_app()

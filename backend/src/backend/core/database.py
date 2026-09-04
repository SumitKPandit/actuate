"""Database engine / session wiring (SQLite locally, PostgreSQL when deployed)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models. Import in `backend.models`."""


def build_engine(database_url: str = settings.database_url) -> AsyncEngine:
    """Build an async engine for either backend.

    SQLite (local default, `sqlite+aiosqlite:///...`) needs
    `check_same_thread=False` for async use. Anything else (e.g.
    `postgresql+asyncpg://...` in deployed envs) gets `pool_pre_ping`
    so stale connections are recycled.
    """
    if database_url.startswith("sqlite"):
        return create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(database_url, pool_pre_ping=True)


engine = build_engine()
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: `db: AsyncSession = Depends(get_db)`."""
    async with SessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create tables from `Base.metadata`."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

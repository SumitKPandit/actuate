"""Async SQLAlchemy engine / session wiring (PostgreSQL + SQLite fallback)."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from backend.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models. Import in `backend.models`."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine(database_url: str, echo: bool) -> AsyncEngine:
    if database_url.startswith("sqlite"):
        # Single shared in-memory/thread-safe connection (tests + local fallback).
        return create_async_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_async_engine(
        database_url,
        echo=echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )


def get_engine() -> AsyncEngine:
    """Return the cached async engine, creating it from settings on first use."""
    global _engine
    if _engine is None:
        _engine = _build_engine(settings.database_url, settings.db_echo)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: `db: AsyncSession = Depends(get_db)`."""
    async with get_session_factory()() as session:
        yield session


async def init_db() -> None:
    """Create tables from `Base.metadata`. Dev/test bootstrap (use Alembic in prod)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose engine + reset cached state (app shutdown / tests)."""
    global _engine, _session_factory
    _session_factory = None
    if _engine is not None:
        await _engine.dispose()
        _engine = None


async def check_db() -> bool:
    """Return True when `SELECT 1` succeeds, else False (never raises)."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - connectivity probe must return False, never raise
        return False

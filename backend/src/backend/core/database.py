"""SQLite engine / session wiring."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models. Import in `backend.models`."""


engine = create_async_engine(settings.database_url)
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: `db: AsyncSession = Depends(get_db)`."""
    async with SessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create tables from `Base.metadata`."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

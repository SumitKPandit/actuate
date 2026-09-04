"""DB integration tests (SQLite in-memory — no Postgres required)."""

import asyncio

from sqlalchemy import String, func, select
from sqlalchemy.orm import Mapped, mapped_column

from backend.core import database as db_module
from backend.core.config import settings
from backend.core.database import Base


def _run(coro):
    return asyncio.run(coro)


def _use_sqlite(monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(settings, "db_echo", False)
    _run(db_module.close_db())


class _Widget(Base):
    __tablename__ = "_test_widgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))


def test_check_db_ok_on_sqlite(monkeypatch) -> None:
    _use_sqlite(monkeypatch)
    try:
        assert _run(db_module.check_db()) is True
    finally:
        _run(db_module.close_db())


def test_init_and_crud_via_session(monkeypatch) -> None:
    _use_sqlite(monkeypatch)
    try:

        async def _flow() -> None:
            await db_module.init_db()
            async with db_module.get_session_factory()() as session:
                session.add(_Widget(name="rotor"))
                await session.commit()
                count = await session.scalar(select(func.count()).select_from(_Widget))
                assert count == 1
                name = await session.scalar(select(_Widget.name).limit(1))
                assert name == "rotor"

        _run(_flow())
    finally:
        # Drop the temp table so global metadata stays clean for other tests.
        async def _cleanup() -> None:
            async with db_module.get_engine().begin() as conn:
                await conn.run_sync(_Widget.__table__.drop, checkfirst=True)

        _run(_cleanup())
        _run(db_module.close_db())


def test_get_db_dependency_yields_session(monkeypatch) -> None:
    _use_sqlite(monkeypatch)
    try:

        async def _flow() -> None:
            async for session in db_module.get_db():
                assert session.bind is not None
                break

        _run(_flow())
    finally:
        _run(db_module.close_db())


def test_ready_reports_connected_on_sqlite(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    _use_sqlite(monkeypatch)
    try:
        from backend.app import create_app

        client = TestClient(create_app())
        res = client.get("/ready")
        assert res.status_code == 200
        assert res.json() == {"ready": True, "database": "connected"}
    finally:
        _run(db_module.close_db())

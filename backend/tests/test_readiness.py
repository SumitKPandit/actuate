"""Readiness must reflect real DB connectivity."""

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app import create_app
from backend.core import database


def _patch_db_to_tmp(tmp_path, monkeypatch) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path}/ready.db"
    test_engine = database.build_engine(url)
    test_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionFactory", test_factory)


def test_ready_ok_against_real_db(tmp_path, monkeypatch) -> None:
    _patch_db_to_tmp(tmp_path, monkeypatch)
    with TestClient(create_app()) as client:
        res = client.get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": "up"}


def test_ready_down_returns_503(monkeypatch) -> None:
    async def boom() -> None:
        raise RuntimeError("db down")

    async def skip_init() -> None:
        return None

    monkeypatch.setattr(database, "init_db", skip_init)
    monkeypatch.setattr(database, "ping_db", boom)
    with TestClient(create_app()) as client:
        res = client.get("/ready")
    assert res.status_code == 503
    assert res.json() == {"status": "down", "db": "down"}

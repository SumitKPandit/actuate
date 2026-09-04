"""App startup must create tables so a fresh (Postgres) volume works."""

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core import database


def test_startup_calls_init_db(monkeypatch) -> None:
    called = False

    async def fake_init_db() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(database, "init_db", fake_init_db)
    with TestClient(create_app()):
        pass
    assert called is True

"""Example resource proves the get_db session pattern for future domain work."""

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app import create_app
from backend.core import database


def _client_with_tmp_db(tmp_path, monkeypatch) -> TestClient:
    url = f"sqlite+aiosqlite:///{tmp_path}/examples.db"
    test_engine = database.build_engine(url)
    test_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionFactory", test_factory)
    return TestClient(create_app())


def test_create_and_list_examples(tmp_path, monkeypatch) -> None:
    with _client_with_tmp_db(tmp_path, monkeypatch) as client:
        created = client.post("/examples", json={"content": "hello stack"})
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["content"] == "hello stack"
        assert body["id"] >= 1

        listed = client.get("/examples")
        assert listed.status_code == 200
        assert any(r["content"] == "hello stack" for r in listed.json())


def test_create_rejects_empty_content(tmp_path, monkeypatch) -> None:
    with _client_with_tmp_db(tmp_path, monkeypatch) as client:
        res = client.post("/examples", json={"content": ""})
        assert res.status_code == 422

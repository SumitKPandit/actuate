from fastapi.testclient import TestClient

from backend.app import create_app


def test_root() -> None:
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["health"] == "/health"


def test_health_endpoints() -> None:
    client = TestClient(create_app())
    for path in ("/health", "/api/v1/health", "/ready", "/api/v1/ready"):
        res = client.get(path)
        assert res.status_code == 200, path

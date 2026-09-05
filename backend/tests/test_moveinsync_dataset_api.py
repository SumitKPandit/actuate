"""The uploaded trip-feedback CSV must be exposed through cached API services."""

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core import database


def test_dataset_endpoints_and_execution_trace(monkeypatch) -> None:
    async def skip_init() -> None:
        return None

    monkeypatch.setattr(database, "init_db", skip_init)
    with TestClient(create_app()) as client:
        info = client.get("/api/dataset/info")
        assert info.status_code == 200
        payload = info.json()
        assert payload["dataset"] == "trip_feedback_clean.csv"
        assert payload["rows"] > 0
        assert payload["columns"] == len(payload["column_names"])

        sample = client.get("/api/dataset/sample")
        assert sample.status_code == 200
        assert 1 <= len(sample.json()["rows"]) <= 5

        trace = client.get("/api/agent/execution-trace")
        assert trace.status_code == 200
        assert trace.json()["dataset"] == "trip_feedback_clean.csv"
        assert trace.json()["rows_analyzed"] == payload["rows"]

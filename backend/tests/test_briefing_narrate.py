"""Story 07 briefing narration must not enter the deterministic cache."""

import asyncio

from sqlalchemy import select

from backend.models.marts import InsightCache
from tests.test_ops_api import CUR, _client_factory, _seed_marts


def test_narrated_briefing_reuses_cache_without_mutating_it(tmp_path, monkeypatch) -> None:
    factory = _client_factory(tmp_path, monkeypatch)
    calls = []

    async def fake_narrate(facts):
        calls.append(facts)
        return "Narrated briefing."

    monkeypatch.setattr("backend.api.ops.narrate_with_sarvam", fake_narrate)
    from fastapi.testclient import TestClient

    from backend.app import create_app

    with TestClient(create_app()) as client:
        asyncio.run(_seed_marts(factory))
        deterministic = client.get("/briefing", params={"cycle": CUR}).json()["data"]
        narrated = client.get("/briefing", params={"cycle": CUR, "narrate": True})
        assert narrated.status_code == 200
        assert narrated.json()["data"]["narrative"] == "Narrated briefing."
        assert "narrative" not in deterministic
        assert calls[0]["intent"] == "briefing"

        async def cached_payload():
            async with factory() as session:
                row = (await session.execute(select(InsightCache).where(InsightCache.key == f"briefing:{CUR}"))).scalar_one()
                return row.payload_json

        assert "narrative" not in asyncio.run(cached_payload())

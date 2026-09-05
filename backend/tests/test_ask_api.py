"""Story 07 /ask API contract tests."""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app import create_app
from backend.core import database
from backend.models.marts import VendorKpi


def test_ask_returns_grounded_rows_and_rejects_unsupported(tmp_path, monkeypatch) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path}/ask-api.db"
    engine = database.build_engine(url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionFactory", factory)

    async def seed() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(database.Base.metadata.create_all)
        async with factory() as session:
            session.add(VendorKpi(vendor="Vendor A", cycle_or_month="2026-06-H1", trips=10, ota_pct=90, delayed_trips=1, avg_delay_min=20))
            await session.commit()

    asyncio.run(seed())
    with TestClient(create_app()) as client:
        response = client.post("/ask", json={"question": "show OTA by vendor", "cycle": "2026-06-H1"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["rows"][0]["vendor"] == "Vendor A"
        assert body["grounded_from"] == {"marts": ["vendor_kpi"], "cycle": "2026-06-H1"}
        assert "SELECT" in body["sql"].upper()

        unsupported = client.post("/ask", json={"question": "show OTA"})
        assert unsupported.status_code == 422
        assert unsupported.json()["supported_intents"][0] == "ota_by_vendor"
    asyncio.run(engine.dispose())

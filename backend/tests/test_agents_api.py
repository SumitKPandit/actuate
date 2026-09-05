"""End-to-end tests for the deterministic mobility agent API."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app import create_app
from backend.core import database
from backend.models.marts import DailyKpi, VendorKpi


def _client(tmp_path, monkeypatch) -> TestClient:
    engine = database.build_engine(f"sqlite+aiosqlite:///{tmp_path}/agents.db")
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(
        database,
        "SessionFactory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )
    return TestClient(create_app())


async def _seed() -> None:
    async with database.SessionFactory() as session:
        session.add_all(
            [
                VendorKpi(
                    vendor="Vendor ABC", cycle_or_month="2026-06-H1", trips=100,
                    ota_pct=78, cost_per_trip=1250, cost_per_km=20,
                    alert_rate_per_1k=8, csat_avg=3.5, low_rating_share=20,
                    delayed_trips=22, avg_delay_min=21, no_show_rate=4,
                    zero_km_count=0, unslabbed_count=0, sev1_count=2,
                    avg_ack_minutes=45, ack_sla_met_share=60, late_reason_counts={},
                ),
                VendorKpi(
                    vendor="Vendor Peer", cycle_or_month="2026-06-H1", trips=100,
                    ota_pct=96, cost_per_trip=1000, cost_per_km=16,
                    alert_rate_per_1k=2, csat_avg=4.7, low_rating_share=2,
                    delayed_trips=4, avg_delay_min=6, no_show_rate=1,
                    zero_km_count=0, unslabbed_count=0, sev1_count=0,
                    avg_ack_minutes=10, ack_sla_met_share=100, late_reason_counts={},
                ),
                DailyKpi(
                    date=date(2026, 6, 1), trips=100, delayed_trips=22, sev1_count=2,
                    ota_pct=78, avg_delay_min=21, no_show_rate=4, cost_per_trip=1250,
                    alert_rate_per_1k=8, csat_avg=3.5, max_trip_cost=3000,
                ),
            ]
        )
        await session.commit()


def test_agents_workflow_and_safe_action(tmp_path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        assert len(client.get("/api/agents").json()["agents"]) == 5
        assert client.get("/api/agent/workflow").json()["workflow"] == [
            "SENSE", "REASON", "BENCHMARK", "RECOMMEND", "ACT"
        ]
        waiting = client.post("/api/agent/action", json={"action": "vendor_escalation", "target": "Vendor ABC", "approved": False})
        assert waiting.json()["status"] == "approval_required"
        executed = client.post("/api/agent/action", json={"action": "vendor_escalation", "target": "Vendor ABC", "approved": True})
        assert executed.json()["status"] == "executed_demo"


def test_dashboard_insights_and_vendor_question_use_mart_data(tmp_path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        import asyncio

        asyncio.run(_seed())
        dashboard = client.get("/api/dashboard", params={"cycle": "2026-06-H1"})
        assert dashboard.status_code == 200
        assert dashboard.json()["overview"]["ota_pct"] == 87.0
        insights = client.get("/api/insights", params={"cycle": "2026-06-H1"}).json()["insights"]
        assert any(item["type"] == "SLA_BREACH" for item in insights)
        answer = client.post("/api/agent/ask", json={"question": "Why is Vendor ABC underperforming?", "cycle": "2026-06-H1"})
        assert answer.status_code == 200
        assert answer.json()["agent"] == "vendor_agent"
        assert answer.json()["metrics"]["ota_pct"] == 78.0

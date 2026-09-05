"""Ops API tests — Story 04 TECH_SPEC §6 (test-first, TestClient + seeded mini-marts)."""

import asyncio
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app import create_app
from backend.core import database
from backend.models.marts import DailyKpi, OfficeKpi, VendorKpi

CUR = "2026-06-H1"
PRIOR = "2026-05-H2"

EMPTY_WARNING = "marts empty — run ingest"


def _client_factory(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path}/ops.db"
    test_engine = database.build_engine(url)
    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionFactory", test_factory)
    return test_factory


async def _seed_marts(factory) -> None:
    async with factory() as s:
        # 15 current daily rows Jun 1-15: 800 trips/day.
        for day in range(1, 16):
            delayed = 59 if day <= 10 else 58
            ota = 100 * (1 - delayed / 800)
            sev1 = 1 if day <= 6 else 0
            s.add(
                DailyKpi(
                    date=date(2026, 6, day),
                    trips=800,
                    delayed_trips=delayed,
                    sev1_count=sev1,
                    ota_pct=ota,
                    avg_delay_min=3.0,
                    no_show_rate=2.3,
                    cost_per_trip=1300.0,
                    alert_rate_per_1k=8.5,
                    csat_avg=4.5,
                    max_trip_cost=3200.0,
                )
            )
        # 2 prior daily rows May 30-31 flat ota 95.5.
        for day in (30, 31):
            s.add(
                DailyKpi(
                    date=date(2026, 5, day),
                    trips=800,
                    delayed_trips=36,
                    sev1_count=0,
                    ota_pct=95.5,
                    avg_delay_min=3.0,
                    no_show_rate=2.3,
                    cost_per_trip=1150.0,
                    alert_rate_per_1k=8.5,
                    csat_avg=4.5,
                    max_trip_cost=2800.0,
                )
            )
        vendors_cur = [
            ("A", 6000, 90.0, 600, 1450.00, 48.50, 12.0, 4.2, 8.0, 300, 1200, 5, 3.0, 4.5, 22.0, 80.0,
             {"TRAFFIC": 300, "DRIVER": 200, "EMPLOYEE": 100}),
            ("B", 4000, 94.0, 240, 1200.00, 40.00, 6.0, 4.7, 4.0, 80, 800, 1, 2.0, 2.0, 18.0, 92.0,
             {"TRAFFIC": 120, "DRIVER": 80, "EMPLOYEE": 40}),
            ("C", 2000, 98.0, 40, 1100.00, 36.70, 3.0, 4.9, 1.5, 20, 100, 0, 1.0, 0.8, 15.0, 98.0,
             {"TRAFFIC": 20, "DRIVER": 10, "EMPLOYEE": 10}),
        ]
        for v, trips, ota, delayed, cpt, cpk, alert, csat, low, zero, unslab, sev1, ns, delay, ack, ackm, reasons in vendors_cur:
            s.add(
                VendorKpi(
                    vendor=v, cycle_or_month=CUR, trips=trips, ota_pct=ota,
                    cost_per_trip=cpt, cost_per_km=cpk, alert_rate_per_1k=alert,
                    csat_avg=csat, low_rating_share=low, delayed_trips=delayed,
                    avg_delay_min=delay, no_show_rate=ns, zero_km_count=zero,
                    unslabbed_count=unslab, sev1_count=sev1, avg_ack_minutes=ack,
                    ack_sla_met_share=ackm, late_reason_counts=reasons,
                )
            )
        vendors_prior = [
            ("A", 6000, 95.0, 300, 1250.00, 47.00, 12.0, 4.2, 8.0, 300, 1200, 2, 3.0, 4.5, 22.0, 80.0,
             {"TRAFFIC": 150, "DRIVER": 100, "EMPLOYEE": 50}),
            ("B", 4000, 96.0, 160, 1100.00, 39.00, 6.0, 4.7, 4.0, 80, 800, 1, 2.0, 2.0, 18.0, 92.0,
             {"TRAFFIC": 80, "DRIVER": 50, "EMPLOYEE": 30}),
            ("C", 2000, 96.0, 80, 1000.00, 35.50, 3.0, 4.9, 1.5, 20, 100, 1, 1.0, 0.8, 15.0, 98.0,
             {"TRAFFIC": 40, "DRIVER": 25, "EMPLOYEE": 15}),
        ]
        for v, trips, ota, delayed, cpt, cpk, alert, csat, low, zero, unslab, sev1, ns, delay, ack, ackm, reasons in vendors_prior:
            s.add(
                VendorKpi(
                    vendor=v, cycle_or_month=PRIOR, trips=trips, ota_pct=ota,
                    cost_per_trip=cpt, cost_per_km=cpk, alert_rate_per_1k=alert,
                    csat_avg=csat, low_rating_share=low, delayed_trips=delayed,
                    avg_delay_min=delay, no_show_rate=ns, zero_km_count=zero,
                    unslabbed_count=unslab, sev1_count=sev1, avg_ack_minutes=ack,
                    ack_sla_met_share=ackm, late_reason_counts=reasons,
                )
            )
        offices = [
            ("O1", CUR, 7000, 91.5, 595, 1320.00, 44.00, 9.0, 4.4, 5.8, 250, 1100, 4, 2.4, 3.2, 20.0, 86.0,
             {"TRAFFIC": 300, "DRIVER": 200, "EMPLOYEE": 95}),
            ("O2", CUR, 5000, 94.5, 275, 1290.00, 43.00, 7.8, 4.6, 5.3, 150, 800, 2, 2.2, 2.7, 18.5, 88.5,
             {"TRAFFIC": 140, "DRIVER": 90, "EMPLOYEE": 45}),
            ("O1", PRIOR, 7000, 94.8, 364, 1180.00, 40.00, 9.0, 4.4, 5.8, 250, 1100, 3, 2.4, 3.0, 20.0, 86.0,
             {"TRAFFIC": 180, "DRIVER": 120, "EMPLOYEE": 64}),
            ("O2", PRIOR, 5000, 96.4, 180, 1130.00, 38.50, 7.8, 4.6, 5.3, 150, 800, 1, 2.2, 2.5, 18.5, 88.5,
             {"TRAFFIC": 90, "DRIVER": 60, "EMPLOYEE": 30}),
        ]
        for o, cyc, trips, ota, delayed, cpt, cpk, alert, csat, low, zero, unslab, sev1, ns, delay, ack, ackm, reasons in offices:
            s.add(
                OfficeKpi(
                    office=o, cycle_or_month=cyc, trips=trips, ota_pct=ota,
                    cost_per_trip=cpt, cost_per_km=cpk, alert_rate_per_1k=alert,
                    csat_avg=csat, low_rating_share=low, delayed_trips=delayed,
                    avg_delay_min=delay, no_show_rate=ns, zero_km_count=zero,
                    unslabbed_count=unslab, sev1_count=sev1, avg_ack_minutes=ack,
                    ack_sla_met_share=ackm, late_reason_counts=reasons,
                )
            )
        await s.commit()


# NOTE: TestClient lifespan handling — seed after startup tables exist.
def _start_seeded(tmp_path, monkeypatch):
    factory = _client_factory(tmp_path, monkeypatch)
    app = create_app()
    client = TestClient(app)
    client.__enter__()
    asyncio.run(_seed_marts(factory))
    return client


def test_overview_shape_and_benchmarks(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        res = client.get("/overview", params={"cycle": CUR})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["warning"] is None
        data = body["data"]
        for key in ("trips", "ota_pct", "avg_delay_min", "delay_reason_mix", "no_show_rate",
                    "cost_per_trip", "cost_per_km", "zero_km_share", "alert_rate_per_1k",
                    "sev1_count", "ack_sla_met_share", "csat_avg", "low_rating_share", "benchmarks"):
            assert key in data, key
        assert data["ota_pct"] == 92.7
        assert data["cost_per_trip"] == 1308.33
        assert data["cost_per_km"] == 43.7
        assert data["alert_rate_per_1k"] == 8.5
        assert data["zero_km_share"] == 3.3
        assert data["sev1_count"] == 6
        mix = data["delay_reason_mix"]
        assert mix["TRAFFIC"]["share"] == 0.5
        assert mix["DRIVER"]["share"] == 0.33
        assert mix["EMPLOYEE"]["share"] == 0.17
        assert data["benchmarks"] == {"ota_sla": 95, "ack_sla_min": 30}
        # Office-filter slice proves the §2.5 grain rule: any office= switches
        # to the office grain (all office rows) -> ota 92.8 vs vendor 92.7.
        res2 = client.get("/overview", params={"cycle": CUR, "office": "O1"})
        assert res2.status_code == 200
        assert res2.json()["data"]["ota_pct"] == 92.8
        assert res2.json()["data"]["trips"] == 12000
    finally:
        client.__exit__(None, None, None)


def test_overview_office_grain(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        default = client.get("/overview", params={"cycle": CUR}).json()["data"]
        assert default["ota_pct"] == 92.7
        assert default["trips"] == 12000
        o2 = client.get("/overview", params={"cycle": CUR, "office": "O2"}).json()["data"]
        assert o2["ota_pct"] == 92.8
        assert o2["trips"] == 12000
    finally:
        client.__exit__(None, None, None)


def test_insights_ranked(tmp_path, monkeypatch) -> None:
    from backend.core.reason import build_insights

    client = _start_seeded(tmp_path, monkeypatch)
    try:
        res = client.get("/insights", params={"cycle": CUR})
        assert res.status_code == 200, res.text
        api_insights = res.json()["data"]
        assert len(api_insights) == 7
        assert api_insights[0]["kpi"] == "ota_pct"
        assert api_insights[0]["reason"] == "vs_sla"

        snapshot = {
            "trips": 12000, "ota_pct": 100 * (1 - 880 / 12000),
            "avg_delay_min": 3.05, "no_show_rate": 28000 / 12000,
            "cost_per_trip": 15700000 / 12000, "cost_per_km": 524400 / 12000,
            "alert_rate_per_1k": 8.5, "sev1_count": 6, "avg_ack_minutes": 19.5,
            "ack_sla_met_share": 87.0, "csat_avg": 53800 / 12000,
            "low_rating_share": 67000 / 12000, "max_trip_cost": 3200.0,
        }
        prior = {
            "trips": 12000, "ota_pct": 95.5,
            "avg_delay_min": 3.0, "no_show_rate": 28000 / 12000,
            "cost_per_trip": 13900000 / 12000, "cost_per_km": 509000 / 12000,
            "alert_rate_per_1k": 8.5, "sev1_count": 4, "avg_ack_minutes": 19.5,
            "ack_sla_met_share": 87.0, "csat_avg": 53800 / 12000,
            "low_rating_share": 67000 / 12000, "max_trip_cost": 2800.0,
        }
        vendor_rows = [
            {"vendor": "A", "trips": 6000, "ota_pct": 90.0, "cost_per_trip": 1450.0,
             "alert_rate_per_1k": 12.0, "low_rating_share": 8.0},
            {"vendor": "B", "trips": 4000, "ota_pct": 94.0, "cost_per_trip": 1200.0,
             "alert_rate_per_1k": 6.0, "low_rating_share": 4.0},
            {"vendor": "C", "trips": 2000, "ota_pct": 98.0, "cost_per_trip": 1100.0,
             "alert_rate_per_1k": 3.0, "low_rating_share": 1.5},
        ]
        office_rows = [
            {"office": "O1", "trips": 7000, "ota_pct": 91.5, "cost_per_trip": 1320.0,
             "alert_rate_per_1k": 9.0, "low_rating_share": 5.8},
            {"office": "O2", "trips": 5000, "ota_pct": 94.5, "cost_per_trip": 1290.0,
             "alert_rate_per_1k": 7.8, "low_rating_share": 5.3},
        ]
        delay_splits = [
            {"key": "A", "trips": 6000, "late_count": 600},
            {"key": "B", "trips": 4000, "late_count": 240},
            {"key": "C", "trips": 2000, "late_count": 40},
        ]
        daily_series = {
            "ota_pct": [92.625] * 10 + [92.75] * 5,
            "sev1": [1] * 6 + [0] * 9,
            "ack": [8.5] * 15,
            "cost": [1300.0] * 15,
            "csat": [4.5] * 15,
            "no_show": [2.3] * 15,
        }
        expected = build_insights(
            snapshot=snapshot, prior=prior, vendor_rows=vendor_rows,
            office_rows=office_rows, delay_splits=delay_splits,
            daily_series=daily_series, cycle=CUR,
        )
        assert [i["id"] for i in api_insights] == [i["id"] for i in expected]
    finally:
        client.__exit__(None, None, None)


def test_briefing_cached(tmp_path, monkeypatch) -> None:
    from sqlalchemy import select

    from backend.models.marts import InsightCache

    factory = _client_factory(tmp_path, monkeypatch)
    app = create_app()
    with TestClient(app) as client:
        asyncio.run(_seed_marts(factory))
        r1 = client.get("/briefing", params={"cycle": CUR})
        assert r1.status_code == 200, r1.text
        d1 = r1.json()["data"]
        assert 3 <= len(d1["headline_facts"]) <= 5
        assert "92.7" in d1["headline_facts"][0]
        assert CUR in d1["headline_facts"][0]

        async def _read_ts():
            async with factory() as s:
                row = (await s.execute(select(InsightCache).where(InsightCache.key == f"briefing:{CUR}"))).scalar_one()
                return row.computed_at

        ts1 = asyncio.run(_read_ts())
        r2 = client.get("/briefing", params={"cycle": CUR})
        assert r2.status_code == 200
        ts2 = asyncio.run(_read_ts())
        assert ts1 == ts2
        assert r1.json() == r2.json()


def test_vendors_sort_and_peer_rank(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        res = client.get("/vendors", params={"cycle": CUR, "sort": "ota"})
        assert res.status_code == 200, res.text
        rows = res.json()["data"]
        assert [r["vendor"] for r in rows] == ["C", "B", "A"]
        assert [r["peer_rank"] for r in rows] == [1, 2, 3]
        res_cost = client.get("/vendors", params={"cycle": CUR, "sort": "cost"})
        assert [r["vendor"] for r in res_cost.json()["data"]] == ["C", "B", "A"]
        by_vendor = {r["vendor"]: r for r in rows}
        assert by_vendor["A"]["zero_km_count"] == 300
        assert by_vendor["A"]["unslabbed_count"] == 1200
        assert by_vendor["A"]["contribution_share"] == 1.0
        assert by_vendor["B"]["contribution_share"] == 0.0
        assert by_vendor["C"]["contribution_share"] is None
    finally:
        client.__exit__(None, None, None)


def test_actions_copy_text(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        res = client.get("/actions", params={"cycle": CUR})
        assert res.status_code == 200, res.text
        items = res.json()["data"]
        assert len(items) == 7
        for it in items:
            assert len(it["copy_for_vendor"]) <= 500
            assert CUR in it["copy_for_vendor"]
            assert it["status"] == "proposed"
            assert it["due_hint"] in ("within 48 hours", "this cycle", "next cycle")
        # high severity maps to 48h
        insights = client.get("/insights", params={"cycle": CUR}).json()["data"]
        by_id = {a["id"]: a for a in items}
        for ins in insights:
            act = by_id[ins["id"]]
            if ins["severity"] == "high":
                assert act["due_hint"] == "within 48 hours"
            assert ins["kpi"] in act["copy_for_vendor"]
    finally:
        client.__exit__(None, None, None)


def test_ack_flips_status(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        items = client.get("/actions", params={"cycle": CUR}).json()["data"]
        target = items[0]["id"]
        assert items[0]["status"] == "proposed"
        ack = client.post(f"/actions/{target}/ack", json={"actor": "ops-manager"})
        assert ack.status_code == 200, ack.text
        body = ack.json()
        assert body["status"] == "acked"
        assert body["actor"] == "ops-manager"
        items2 = client.get("/actions", params={"cycle": CUR}).json()["data"]
        assert {a["id"]: a["status"] for a in items2}[target] == "acked"
    finally:
        client.__exit__(None, None, None)


def test_ack_unknown_id_404(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        res = client.post("/actions/nope/ack", json={"actor": "x"})
        assert res.status_code == 404
        assert res.json()["id"] == "nope"
    finally:
        client.__exit__(None, None, None)


def test_ack_idempotent(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        target = client.get("/actions", params={"cycle": CUR}).json()["data"][0]["id"]
        first = client.post(f"/actions/{target}/ack", json={"actor": "alice"}).json()
        second = client.post(f"/actions/{target}/ack", json={"actor": "alice"}).json()
        assert first == second
        third = client.post(f"/actions/{target}/ack", json={"actor": "bob"}).json()
        assert third["actor"] == "bob"
        assert third["acked_at"] != first["acked_at"] or third["actor"] != first["actor"]
    finally:
        client.__exit__(None, None, None)


def test_unknown_cycle_404(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        res = client.get("/overview", params={"cycle": "2026-01-H1"})
        assert res.status_code == 404
        body = res.json()
        assert CUR in body["valid_cycles"]
        bad = client.get("/overview", params={"cycle": "june"})
        assert bad.status_code == 404
    finally:
        client.__exit__(None, None, None)


def test_empty_marts_warning(tmp_path, monkeypatch) -> None:
    _client_factory(tmp_path, monkeypatch)
    app = create_app()
    with TestClient(app) as client:
        for path, params in [
            ("/overview", {"cycle": CUR}),
            ("/insights", {"cycle": CUR}),
            ("/briefing", {"cycle": CUR}),
            ("/vendors", {"cycle": CUR}),
            ("/actions", {"cycle": CUR}),
        ]:
            res = client.get(path, params=params)
            assert res.status_code == 200, (path, res.text)
            assert res.json() == {"data": None, "warning": EMPTY_WARNING}


def test_no_raw_table_scans(tmp_path, monkeypatch) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession as _AS

    seen: list[str] = []
    orig = _AS.execute

    async def _rec(self, statement, *args, **kwargs):
        try:
            compiled = str(statement)
        except Exception:  # noqa: BLE001 - record best-effort SQL text
            compiled = ""
        seen.append(compiled.lower())
        return await orig(self, statement, *args, **kwargs)

    monkeypatch.setattr(_AS, "execute", _rec)
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        client.get("/overview", params={"cycle": CUR})
        client.get("/insights", params={"cycle": CUR})
        client.get("/briefing", params={"cycle": CUR})
        client.get("/vendors", params={"cycle": CUR})
        client.get("/actions", params={"cycle": CUR})
        target = client.get("/actions", params={"cycle": CUR}).json()["data"][0]["id"]
        client.post(f"/actions/{target}/ack", json={"actor": "audit"})
        joined = "\n".join(seen)
        for tbl in ("trips", "legs", "bills", "alerts", "feedback"):
            assert f"from {tbl}" not in joined
            assert f"join {tbl}" not in joined
    finally:
        client.__exit__(None, None, None)


def test_narrate_and_ask_contracts(tmp_path, monkeypatch) -> None:
    client = _start_seeded(tmp_path, monkeypatch)
    try:
        res = client.get("/briefing", params={"cycle": CUR, "narrate": True})
        assert res.status_code == 200
        assert res.json()["data"]["narrative"]
        ask = client.post("/ask", json={})
        assert ask.status_code == 422
    finally:
        client.__exit__(None, None, None)


def test_cache_timestamp_matches_timezone_naive_column() -> None:
    from backend.api.ops import _cache_timestamp

    assert _cache_timestamp().tzinfo is None

"""All 9 Story-01 tables exist with TECH_SPEC §3 columns; marts start empty."""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core import database


def _init_tmp_db(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path}/marts.db"
    test_engine = database.build_engine(url)
    test_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionFactory", test_factory)
    return test_engine


def test_all_tables_exist_with_expected_columns(tmp_path, monkeypatch) -> None:
    _init_tmp_db(tmp_path, monkeypatch)
    asyncio.run(database.init_db())

    import backend.models  # noqa: F401  # ensure registration

    tables = database.Base.metadata.tables
    for name in (
        "trips",
        "legs",
        "bills",
        "alerts",
        "feedback",
        "daily_kpi",
        "vendor_kpi",
        "office_kpi",
        "shift_kpi",
        "insight_cache",
    ):
        assert name in tables, f"missing table {name}"

    assert "trip_id" in tables["trips"].c
    assert "trip_nodal" in tables["trips"].c
    assert "plannedemployee_cnt" in tables["trips"].c
    assert "stwid" in tables["legs"].c
    assert "is_placeholder" in tables["legs"].c
    assert "dq_flag" in tables["legs"].c
    assert "is_no_show" in tables["legs"].c
    assert "is_zero_km" in tables["bills"].c
    assert "slab_name" in tables["bills"].c
    assert "severity" in tables["alerts"].c
    assert "severity_raw" in tables["alerts"].c
    assert "event_id" in tables["alerts"].c
    assert "route_rating" in tables["feedback"].c
    assert "marshal_rating" in tables["feedback"].c
    assert "creation_time" in tables["feedback"].c
    assert "ota_pct" in tables["daily_kpi"].c
    assert "sev1_count" in tables["daily_kpi"].c
    assert "cycle_or_month" in tables["vendor_kpi"].c
    assert "cycle_or_month" in tables["office_kpi"].c
    assert "no_show_rate" in tables["shift_kpi"].c
    assert "payload_json" in tables["insight_cache"].c


def test_marts_start_empty(tmp_path, monkeypatch) -> None:
    test_engine = _init_tmp_db(tmp_path, monkeypatch)
    asyncio.run(database.init_db())

    from backend.models.marts import DailyKpi, InsightCache, OfficeKpi, VendorKpi

    async def _counts() -> tuple[int, int, int, int]:
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            d = (await session.execute(select(func.count()).select_from(DailyKpi))).scalar()
            v = (await session.execute(select(func.count()).select_from(VendorKpi))).scalar()
            o = (await session.execute(select(func.count()).select_from(OfficeKpi))).scalar()
            i = (await session.execute(select(func.count()).select_from(InsightCache))).scalar()
            return d, v, o, i

    assert asyncio.run(_counts()) == (0, 0, 0, 0)

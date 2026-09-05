"""Story 07 query planner tests."""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core import database
from backend.core.ask import (
    ALLOWED_MARTS,
    SUPPORTED_INTENTS,
    QueryPlan,
    build_plan,
    execute_plan,
    match_intent,
    normalize_question,
)
from backend.models.marts import OfficeKpi, VendorKpi


def test_supported_intents_and_deterministic_parser() -> None:
    assert SUPPORTED_INTENTS == (
        "ota_by_vendor",
        "ota_by_office",
        "cost_outliers_by_vendor",
        "open_sev1_by_vendor",
        "open_sev1_by_office",
        "low_csat_by_vendor",
        "low_csat_by_office",
        "no_show_by_shift",
        "no_show_by_office",
    )
    assert normalize_question("Show on-time performance for a supplier") == "show on time performance for a supplier"
    assert match_intent("show on-time performance for a supplier") == "ota_by_vendor"
    assert match_intent("show severity one alerts by hub") == "open_sev1_by_office"
    assert match_intent("show sev one alerts by office") == "open_sev1_by_office"
    assert match_intent("show sev1 alerts by vendor") == "open_sev1_by_vendor"
    assert match_intent("show missed rides by shift") == "no_show_by_shift"
    assert match_intent("show select * from trips") is None
    assert match_intent("show OTA") is None
    assert match_intent("show OTA by vendor and cost by vendor") is None


def test_plans_are_bounded_and_use_only_marts() -> None:
    cases = {
        "ota_by_vendor": VendorKpi,
        "ota_by_office": OfficeKpi,
        "cost_outliers_by_vendor": VendorKpi,
        "open_sev1_by_vendor": VendorKpi,
        "open_sev1_by_office": OfficeKpi,
        "low_csat_by_vendor": VendorKpi,
        "low_csat_by_office": OfficeKpi,
        "no_show_by_office": OfficeKpi,
    }
    for intent, model in cases.items():
        plan = build_plan(intent, "2026-06-H1", {})
        assert isinstance(plan, QueryPlan)
        assert plan.marts == (model.__tablename__,)
        assert plan.statement._limit_clause is not None
        assert plan.statement._limit_clause.value == 50
        assert model.__tablename__ in ALLOWED_MARTS

    shift = build_plan("no_show_by_shift", "2026-06-H1", {})
    assert shift.marts == ("shift_kpi",)
    assert shift.statement._limit_clause.value == 50


def test_execute_plan_returns_compiled_sql_and_rows(tmp_path) -> None:
    async def run() -> None:
        url = f"sqlite+aiosqlite:///{tmp_path}/ask.db"
        engine = database.build_engine(url)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(database.Base.metadata.create_all)
        async with factory() as session:
            session.add(VendorKpi(vendor="Vendor A", cycle_or_month="2026-06-H1", trips=10, ota_pct=90))
            await session.commit()
            plan = build_plan("ota_by_vendor", "2026-06-H1", {})
            rows, sql = await execute_plan(session, plan)
            assert rows[0]["vendor"] == "Vendor A"
            assert "SELECT" in sql.upper()
            assert "LIMIT 50" in sql.upper()
            assert "vendor_kpi" in sql
            assert all(raw not in sql.lower() for raw in ("trips ", "legs ", "bills ", "alerts ", "feedback "))
        await engine.dispose()

    asyncio.run(run())


def test_execute_plan_rejects_unsafe_statements(tmp_path) -> None:
    async def run() -> None:
        url = f"sqlite+aiosqlite:///{tmp_path}/unsafe.db"
        engine = database.build_engine(url)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(database.Base.metadata.create_all)
        async with factory() as session:
            unsafe = QueryPlan("ota_by_vendor", select(VendorKpi.vendor), ("trips",), "2026-06-H1", {})
            with pytest.raises(ValueError):
                await execute_plan(session, unsafe)
        await engine.dispose()

    asyncio.run(run())

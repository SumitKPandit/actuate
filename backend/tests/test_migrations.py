"""Story 07 migration runner tests."""

import asyncio

from sqlalchemy import inspect, text

from backend.core.database import build_engine
from backend.scripts.migrate import apply_migrations


def test_story07_migration_is_idempotent_on_fresh_sqlite(tmp_path) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path}/migration.db"
    assert asyncio.run(apply_migrations(url)) == [
        "001_story07_ask_marts.sql",
        "002_story07_legacy_mart_columns.sql",
    ]
    assert asyncio.run(apply_migrations(url)) == []

    async def check() -> None:
        engine = build_engine(url)
        async with engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            columns = await conn.run_sync(lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("vendor_kpi")})
            daily_columns = await conn.run_sync(lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("daily_kpi")})
            versions = (await conn.execute(text("SELECT version FROM schema_migrations"))).scalars().all()
            assert "shift_kpi" in tables
            assert {"open_sev1_count", "unclassified_severity_count", "cost_outlier"} <= columns
            assert "max_trip_cost" in daily_columns
            assert versions == ["001_story07_ask_marts.sql", "002_story07_legacy_mart_columns.sql"]
        await engine.dispose()

    asyncio.run(check())

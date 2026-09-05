"""Apply numbered PostgreSQL schema migrations."""

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import inspect, text

import backend.models  # noqa: F401 - register all ORM tables before create_all
from backend.core.config import settings
from backend.core.database import Base, build_engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


async def _sqlite_migration(conn, migration: Path) -> None:
    if migration.name not in {"001_story07_ask_marts.sql", "002_story07_legacy_mart_columns.sql"}:
        await conn.exec_driver_sql(migration.read_text(encoding="utf-8"))
        return
    additions = {
        "daily_kpi": (
            ("open_sev1_count INTEGER", "unclassified_severity_count INTEGER")
            if migration.name.startswith("001")
            else ("max_trip_cost FLOAT",)
        ),
        "vendor_kpi": (
            ("open_sev1_count INTEGER", "unclassified_severity_count INTEGER", "cost_outlier BOOLEAN")
            if migration.name.startswith("001")
            else (
                "delayed_trips INTEGER", "avg_delay_min FLOAT", "no_show_rate FLOAT",
                "zero_km_count INTEGER", "unslabbed_count INTEGER", "sev1_count INTEGER",
                "avg_ack_minutes FLOAT", "ack_sla_met_share FLOAT", "late_reason_counts JSON",
            )
        ),
        "office_kpi": (
            ("open_sev1_count INTEGER", "unclassified_severity_count INTEGER")
            if migration.name.startswith("001")
            else (
                "delayed_trips INTEGER", "avg_delay_min FLOAT", "no_show_rate FLOAT",
                "zero_km_count INTEGER", "unslabbed_count INTEGER", "sev1_count INTEGER",
                "avg_ack_minutes FLOAT", "ack_sla_met_share FLOAT", "late_reason_counts JSON",
            )
        ),
    }
    existing = await conn.run_sync(
        lambda sync_conn: {
            table: {column["name"] for column in inspect(sync_conn).get_columns(table)}
            for table in additions
        }
    )
    for table, columns in additions.items():
        for definition in columns:
            name = definition.split()[0]
            if name not in existing[table]:
                await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {definition}")
    if migration.name.startswith("001"):
        await conn.run_sync(lambda sync_conn: Base.metadata.tables["shift_kpi"].create(sync_conn, checkfirst=True))


async def apply_migrations(database_url: str | None = None) -> list[str]:
    engine = build_engine(database_url or settings.database_url)
    migrations = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(255) PRIMARY KEY)"))
            applied = {row[0] for row in (await conn.execute(text("SELECT version FROM schema_migrations"))).all()}

        applied_now = []
        for migration in migrations:
            if migration.name in applied:
                continue
            async with engine.begin() as conn:
                if conn.dialect.name == "sqlite":
                    await _sqlite_migration(conn, migration)
                else:
                    for statement in migration.read_text(encoding="utf-8").split(";"):
                        if statement.strip():
                            await conn.exec_driver_sql(statement)
                await conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:version)"), {"version": migration.name})
            applied_now.append(migration.name)
        return applied_now
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply Actuate database migrations.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    asyncio.run(apply_migrations(args.database_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

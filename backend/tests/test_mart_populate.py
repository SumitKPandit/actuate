"""Mart population tests — Story 05 (test-first)."""

import asyncio
import csv
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core import database
from backend.scripts.ingest import run_ingest

TRIP_HEADER = [
    "business_unit",
    "office",
    "product_type",
    "trip_date",
    "shift_type",
    "trip_id",
    "trip_direction",
    "actual_escort",
    "vendor_id",
    "planned_cab_registration",
    "actual_cab_registration",
    "actual_cab_capacity",
    "planned_km",
    "traveled_km",
    "planned_start_epoch",
    "planned_end_epoch",
    "actual_start_epoch",
    "actual_end_epoch",
    "delay_reason",
    "delay_minutes",
    "route_source",
    "actual_cab_fuel_type",
    "is_driver_nc",
    "is_cab_nc",
    "trip_nodal",
    "plannedemployee_cnt",
    "actualemployee_cnt",
    "noshow_cnt",
]

TRIP_ROWS = [
    [
        "vanta-Aus", "Office A", "CAB", "May 1, 2026", "00:15",
        "1097076", "LOGOUT", "true", "VendorX",
        "TSC 921 GP", "TSC 921 GP", "3", "10.0", "10.0",
        "1777595400", "1777598280", "1777594061", "1777597937",
        "NODELAY", "0", "AUTO", "Diesel",
        "false", "false", "NODAL", "2", "2", "0",
    ],
    [
        "vanta-Aus", "Office A", "CAB", "May 1, 2026", "02:15",
        "1097357", "LOGOUT", "true", "VendorX",
        "JVM 364 GP", "JVM 364 GP", "4", "12.0", "12.0",
        "1777602600", "1777604880", "1777601297", "1777603580",
        "TRAFFIC", "20", "MANUAL", "Petrol",
        "false", "false", "NODAL", "1", "1", "0",
    ],
    [
        "vanta-Aus", "Office B", "CAB", "May 16, 2026", "00:15",
        "1098000", "LOGOUT", "true", "VendorY",
        "TSC 921 GP", "TSC 921 GP", "3", "10.0", "10.0",
        "1777595400", "1777598280", "1777594061", "1777597937",
        "DRIVER", "30", "AUTO", "Diesel",
        "false", "false", "NODAL", "2", "2", "0",
    ],
    [
        "vanta-Aus", "Office B", "CAB", "May 16, 2026", "02:15",
        "1098001", "LOGOUT", "true", "VendorY",
        "JVM 364 GP", "JVM 364 GP", "4", "12.0", "12.0",
        "1777602600", "1777604880", "1777601297", "1777603580",
        "EMPLOYEE", "5", "MANUAL", "Petrol",
        "false", "false", "NODAL", "1", "1", "0",
    ],
]

LEG_ROWS = [
    [
        "vanta-Aus", "Office A", "CAB", "2026-05-01", "00:15",
        "1097076", "1777595400", "1777598280", "1777594061", "1777597937",
        "10.0", "10.0", "484475", "Planned", "MALE", "employee",
        "Boarded", "", "False",
    ],
    [
        "vanta-Aus", "Office A", "CAB", "2026-05-01", "02:15",
        "1097357", "1777602600", "1777604880", "1777601297", "1777603580",
        "12.0", "12.0", "484476", "Planned", "FEMALE", "employee",
        "Not Boarded", "NO_SHOW", "True",
    ],
    [
        "vanta-Aus", "Office B", "CAB", "2026-05-16", "00:15",
        "1098000", "1777595400", "1777598280", "1777594061", "1777597937",
        "10.0", "10.0", "484477", "Planned", "MALE", "employee",
        "Boarded", "", "False",
    ],
    [
        "vanta-Aus", "Office B", "CAB", "2026-05-16", "02:15",
        "1098001", "1777602600", "1777604880", "1777601297", "1777603580",
        "12.0", "12.0", "484478", "Planned", "FEMALE", "employee",
        "Boarded", "", "False",
    ],
]

BILL_ROWS = [
    [
        "vanta-Aus", "Office A", "VendorX",
        "May 1, 2026, 12:00 AM", "May 15, 2026, 12:00 AM",
        "1097076", "4S-EV-Z", "Medium", "10.0", "1000",
    ],
    [
        "vanta-Aus", "Office A", "VendorX",
        "May 1, 2026, 12:00 AM", "May 15, 2026, 12:00 AM",
        "1097357", "4S-EV-Z", "Medium", "12.0", "1200",
    ],
    [
        "vanta-Aus", "Office B", "VendorY",
        "May 16, 2026, 12:00 AM", "May 31, 2026, 12:00 AM",
        "1098000", "4S-EV-Z", "Medium", "10.0", "1000",
    ],
    [
        "vanta-Aus", "Office B", "VendorY",
        "May 16, 2026, 12:00 AM", "May 31, 2026, 12:00 AM",
        "1098001", "4S-EV-Z", "Medium", "12.0", "1200",
    ],
]

ALERT_ROWS = [
    [
        "vanta-Aus", "1097076", "484475",
        "37ceae1c-7fe7-4081-a96e-da66602024a7",
        "DEVICE_NOT_REACHABLE",
        "May 1, 2026, 12:03 AM", "May 1, 2026, 12:10 AM",
        "CLOSED", "Sev-3", "MOBILE",
    ],
    [
        "vanta-Aus", "1097357", "484476",
        "43a48dc7-b668-4c65-8b5c-06d37d1f8876",
        "OVER_SPEEDING",
        "May 1, 2026, 12:12 AM", "",
        "OPEN", "Sev-1", "NA",
    ],
    [
        "vanta-Aus", "1098000", "484477",
        "37ceae1c-7fe7-4081-a96e-da66602024a7",
        "DEVICE_NOT_REACHABLE",
        "May 16, 2026, 12:03 AM", "May 16, 2026, 12:10 AM",
        "CLOSED", "Sev-3", "MOBILE",
    ],
    [
        "vanta-Aus", "1098001", "484478",
        "43a48dc7-b668-4c65-8b5c-06d37d1f8876",
        "OVER_SPEEDING",
        "May 16, 2026, 12:12 AM", "",
        "OPEN", "Sev-1", "NA",
    ],
]

FEEDBACK_ROWS = [
    [
        "vanta-Aus", "1097076", "LOGIN", "June 3, 2026, 11:00 AM",
        "484475", "5", "5", "5", "5", "5", "June 3, 2026, 10:44 AM",
    ],
    [
        "vanta-Aus", "1097357", "LOGOUT", "June 3, 2026, 11:00 AM",
        "484476", "4", "4", "4", "4", "0", "June 3, 2026, 2:47 PM",
    ],
    [
        "vanta-Aus", "1098000", "LOGIN", "June 3, 2026, 11:00 AM",
        "484477", "5", "5", "5", "5", "5", "June 3, 2026, 10:44 AM",
    ],
    [
        "vanta-Aus", "1098001", "LOGOUT", "June 3, 2026, 11:00 AM",
        "484478", "3", "3", "3", "3", "0", "June 3, 2026, 2:47 PM",
    ],
]


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _make_fixtures(data_dir: Path) -> None:
    _write(data_dir / "Ride_data _trip-may_2026.csv", TRIP_HEADER, TRIP_ROWS)
    _write(
        data_dir / "Ride_data _trip-June_2026.csv",
        TRIP_HEADER, [],
    )
    _write(
        data_dir / "Ride_data _trip-July_2026.csv",
        TRIP_HEADER, [],
    )
    _write(
        data_dir / "emp_Data.csv",
        [
            "business_unit", "office", "product_type", "trip_date", "shift_type",
            "trip_id", "planned_pickup_epoch", "planned_drop_epoch",
            "actual_pickup_epoch", "actual_drop_epoch",
            "planned_km", "traveled_km", "stwid", "signintype", "gender",
            "emp_role", "boarding_status", "not_boarding_reason", "is_no_show",
        ],
        LEG_ROWS,
    )
    _write(
        data_dir / "bill_data.csv",
        [
            "business_unit", "office", "vendor",
            "cycle_start", "cycle_end", "trip_id",
            "contract", "slab_name", "total_trip_km", "trip_cost",
        ],
        BILL_ROWS,
    )
    _write(
        data_dir / "alerts_data.csv",
        [
            "business_unit", "trip_id", "stwid", "event_id", "event_type",
            "start_time", "acknowledge_time", "state_text", "severity", "source",
        ],
        ALERT_ROWS,
    )
    _write(
        data_dir / "trip_feedback.csv",
        [
            "business_unit", "trip_id", "trip_type", "trip_date", "stwid",
            "route_rating", "driver_rating", "cab_rating", "safety_rating",
            "marshal_rating", "creation_time",
        ],
        FEEDBACK_ROWS,
    )


def _mart_counts(engine) -> dict:
    async def _go() -> dict:
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            daily = (await session.execute(text("SELECT COUNT(*) FROM daily_kpi"))).scalar()
            vendor = (await session.execute(text("SELECT COUNT(*) FROM vendor_kpi"))).scalar()
            office = (await session.execute(text("SELECT COUNT(*) FROM office_kpi"))).scalar()
            shift = (await session.execute(text("SELECT COUNT(*) FROM shift_kpi"))).scalar()
            return {"daily_kpi": daily, "vendor_kpi": vendor, "office_kpi": office, "shift_kpi": shift}

    return asyncio.run(_go())


def test_marts_populated_after_ingest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fixtures(data_dir)
    url = f"sqlite+aiosqlite:///{tmp_path}/marts.db"

    asyncio.run(run_ingest(data_dir, url))
    engine = database.build_engine(url)
    counts = _mart_counts(engine)

    assert counts["daily_kpi"] == 2
    assert counts["vendor_kpi"] == 2
    assert counts["office_kpi"] == 2
    assert counts["shift_kpi"] == 4


def test_mart_values_are_correct(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fixtures(data_dir)
    url = f"sqlite+aiosqlite:///{tmp_path}/values.db"

    asyncio.run(run_ingest(data_dir, url))
    engine = database.build_engine(url)

    async def _check() -> None:
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            daily = (await session.execute(text("SELECT * FROM daily_kpi ORDER BY date"))).mappings().all()
            assert len(daily) == 2
            may1 = daily[0]
            assert may1["trips"] == 2
            assert may1["ota_pct"] == 50.0
            assert may1["delayed_trips"] == 1
            assert may1["alert_rate_per_1k"] == 1000.0
            assert may1["sev1_count"] == 1
            assert may1["no_show_rate"] == 50.0
            assert may1["cost_per_trip"] == 1100.0

            may16 = daily[1]
            assert may16["trips"] == 2
            assert may16["ota_pct"] == 50.0
            assert may16["delayed_trips"] == 1

            vendor = (await session.execute(text("SELECT * FROM vendor_kpi ORDER BY vendor, cycle_or_month"))).mappings().all()
            assert len(vendor) == 2
            vx = vendor[0]
            assert vx["vendor"] == "VendorX"
            assert vx["cycle_or_month"] == "2026-05-H1"
            assert vx["trips"] == 2
            assert vx["ota_pct"] == 50.0
            assert vx["cost_per_trip"] == 1100.0
            assert vx["zero_km_count"] == 0
            assert vx["unslabbed_count"] == 0
            assert vx["sev1_count"] == 1
            assert vx["alert_rate_per_1k"] == 1000.0

            vy = vendor[1]
            assert vy["vendor"] == "VendorY"
            assert vy["cycle_or_month"] == "2026-05-H2"
            assert vy["trips"] == 2
            assert vy["ota_pct"] == 50.0
            assert vy["delayed_trips"] == 1

            office = (await session.execute(text("SELECT * FROM office_kpi ORDER BY office, cycle_or_month"))).mappings().all()
            assert len(office) == 2
            oa = office[0]
            assert oa["office"] == "Office A"
            assert oa["cycle_or_month"] == "2026-05-H1"
            assert oa["trips"] == 2
            assert oa["ota_pct"] == 50.0

            ob = office[1]
            assert ob["office"] == "Office B"
            assert ob["cycle_or_month"] == "2026-05-H2"
            assert ob["trips"] == 2
            assert ob["ota_pct"] == 50.0

    asyncio.run(_check())


def test_mart_rebuild_is_idempotent(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fixtures(data_dir)
    url = f"sqlite+aiosqlite:///{tmp_path}/idem.db"

    asyncio.run(run_ingest(data_dir, url))
    first = _mart_counts(database.build_engine(url))

    asyncio.run(run_ingest(data_dir, url))
    second = _mart_counts(database.build_engine(url))

    assert first == second
    assert first["daily_kpi"] == 2
    assert first["vendor_kpi"] == 2
    assert first["office_kpi"] == 2


def test_ops_api_returns_data_after_marts(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from backend.app import create_app

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fixtures(data_dir)
    url = f"sqlite+aiosqlite:///{tmp_path}/api.db"

    asyncio.run(run_ingest(data_dir, url))
    engine = database.build_engine(url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from unittest.mock import patch
    with patch.object(database, "engine", engine), patch.object(database, "SessionFactory", factory):
        app = create_app()
        client = TestClient(app)
        with client:
            res = client.get("/overview", params={"cycle": "2026-05-H1"})
            assert res.status_code == 200
            body = res.json()
            assert body["warning"] is None
            assert body["data"] is not None
            assert body["data"]["trips"] == 2
            assert body["data"]["ota_pct"] == 50.0

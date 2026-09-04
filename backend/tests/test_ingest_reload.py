"""Reload idempotency + joins + flags on tiny inline fixtures (Story 01)."""

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
        "vanta-Aus",
        "Cedar Ridge Office",
        "CAB",
        "May 1, 2026",
        "00:15",
        "1,097,076",
        "LOGOUT",
        "false",
        "Sneha Mikhailov Travel",
        "TSC 921 GP",
        "TSC 921 GP",
        "3",
        "27.92",
        "26.9",
        "1,777,595,400",
        "1,777,598,280",
        "1,777,594,061",
        "1,777,597,937",
        "NODELAY",
        "0",
        "AUTO",
        "Diesel",
        "false",
        "false",
        "NA",
        "2",
        "2",
        "0",
    ],
    [
        "vanta-Aus",
        "Cedar Ridge Office",
        "CAB",
        "May 1, 2026",
        "02:15",
        "1,097,357",
        "LOGOUT",
        "true",
        "Priya Mikhailov Travel",
        "JVM 364 GP",
        "JVM 364 GP",
        "4",
        "1,092.56",
        "29.1",
        "1,777,602,600",
        "1,777,604,880",
        "1,777,601,297",
        "1,777,603,580",
        "TRAFFIC",
        "20",
        "MANUAL",
        "Petrol",
        "",
        "",
        "NODAL",
        "1",
        "1",
        "0",
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
        TRIP_HEADER,
        [],
    )
    _write(
        data_dir / "Ride_data _trip-July_2026.csv",
        TRIP_HEADER,
        [],
    )
    _write(
        data_dir / "emp_Data.csv",
        [
            "business_unit",
            "office",
            "product_type",
            "trip_date",
            "shift_type",
            "trip_id",
            "planned_pickup_epoch",
            "planned_drop_epoch",
            "actual_pickup_epoch",
            "actual_drop_epoch",
            "planned_km",
            "traveled_km",
            "stwid",
            "signintype",
            "gender",
            "emp_role",
            "boarding_status",
            "not_boarding_reason",
            "is_no_show",
        ],
        [
            [
                "vanta-Aus",
                "Cedar Ridge Office",
                "CAB",
                "2026-05-01",
                "00:15",
                "1097076",
                "1777595400.0",
                "1777598280.0",
                "1777594061.0",
                "1777597937.0",
                "9.967",
                "9.3",
                "484475",
                "Planned",
                "MALE",
                "employee",
                "Boarded",
                "",
                "False",
            ],
            [
                "vanta-Aus",
                "Cedar Ridge Office",
                "CAB",
                "2026-05-01",
                "02:15",
                "1097357",
                "1777602600.0",
                "1777604880.0",
                "",
                "",
                "-2.0",
                "5.0",
                "0",
                "",
                "FEMALE",
                "employee",
                "Not Boarded",
                "NO_SHOW",
                "True",
            ],
        ],
    )
    _write(
        data_dir / "bill_data.csv",
        [
            "business_unit",
            "office",
            "vendor",
            "cycle_start",
            "cycle_end",
            "trip_id",
            "contract",
            "slab_name",
            "total_trip_km",
            "trip_cost",
        ],
        [
            [
                "vanta-Aus",
                "Cedar Ridge Office",
                "Priya Mikhailov Travel",
                "May 1, 2026, 12:00 AM",
                "May 31, 2026, 12:00 AM",
                "1097076",
                "4S-EV-Z",
                "Medium",
                "12.5",
                "1,200",
            ],
            [
                "vanta-Aus",
                "Cedar Ridge Office",
                "Sneha Mikhailov Travel",
                "May 1, 2026, 12:00 AM",
                "May 31, 2026, 12:00 AM",
                "1097357",
                "null",
                "NA",
                "0",
                "1,800",
            ],
        ],
    )
    _write(
        data_dir / "alerts_data.csv",
        [
            "business_unit",
            "trip_id",
            "stwid",
            "event_id",
            "event_type",
            "start_time",
            "acknowledge_time",
            "state_text",
            "severity",
            "source",
        ],
        [
            [
                "vanta-Aus",
                "1,097,076",
                "0",
                "37ceae1c-7fe7-4081-a96e-da66602024a7",
                "DEVICE_NOT_REACHABLE",
                "May 1, 2026, 12:03 AM",
                "May 1, 2026, 12:10 AM",
                "CLOSED",
                "Sev-3",
                "MOBILE",
            ],
            [
                "vanta-Aus",
                "1,097,357",
                "484475",
                "43a48dc7-b668-4c65-8b5c-06d37d1f8876",
                "OVER_SPEEDING",
                "May 1, 2026, 12:12 AM",
                "",
                "OPEN",
                "False",
                "NA",
            ],
        ],
    )
    _write(
        data_dir / "trip_feedback.csv",
        [
            "business_unit",
            "trip_id",
            "trip_type",
            "trip_date",
            "stwid",
            "route_rating",
            "driver_rating",
            "cab_rating",
            "safety_rating",
            "marshal_rating",
            "creation_time",
        ],
        [
            [
                "orbit-Slc",
                "1,097,076",
                "LOGIN",
                "June 3, 2026, 11:00 AM",
                "149,530",
                "5",
                "5",
                "5",
                "5",
                "0",
                "June 3, 2026, 10:44 AM",
            ],
            [
                "orbit-Slc",
                "1,097,357",
                "LOGOUT",
                "June 3, 2026, 11:00 AM",
                "0",
                "4",
                "4",
                "4",
                "4",
                "0",
                "June 3, 2026, 2:47 PM",
            ],
        ],
    )


def _counts(engine) -> dict[str, int]:
    async def _go() -> dict[str, int]:
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            out = {}
            for table in ("trips", "legs", "bills", "alerts", "feedback"):
                out[table] = (
                    await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                ).scalar()
            return out

    return asyncio.run(_go())


def _scalar(engine, sql: str):
    async def _go():
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            return (await session.execute(text(sql))).scalar()

    return asyncio.run(_go())


def test_idempotent_reload(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fixtures(data_dir)
    url = f"sqlite+aiosqlite:///{tmp_path}/reload.db"

    first = asyncio.run(run_ingest(data_dir, url))
    engine = database.build_engine(url)
    counts_first = _counts(engine)

    second = asyncio.run(run_ingest(data_dir, url))
    counts_second = _counts(engine)

    assert counts_first == {"trips": 2, "legs": 2, "bills": 2, "alerts": 2, "feedback": 2}
    assert counts_second == counts_first
    assert first["counts"] == second["counts"]


def test_spot_joins_return_rows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fixtures(data_dir)
    url = f"sqlite+aiosqlite:///{tmp_path}/joins.db"
    asyncio.run(run_ingest(data_dir, url))
    engine = database.build_engine(url)

    assert _scalar(engine, "SELECT COUNT(*) FROM alerts a JOIN trips t ON a.trip_id = t.trip_id") > 0
    assert _scalar(engine, "SELECT COUNT(*) FROM bills b JOIN trips t ON b.trip_id = t.trip_id") > 0
    assert (
        _scalar(engine, "SELECT COUNT(*) FROM feedback f JOIN trips t ON f.trip_id = t.trip_id")
        > 0
    )
    assert _scalar(engine, "SELECT COUNT(*) FROM legs l JOIN trips t ON l.trip_id = t.trip_id") > 0


def test_flag_counts_match_fixtures(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fixtures(data_dir)
    url = f"sqlite+aiosqlite:///{tmp_path}/flags.db"
    asyncio.run(run_ingest(data_dir, url))
    engine = database.build_engine(url)

    assert _scalar(engine, "SELECT COUNT(*) FROM alerts WHERE severity IS NULL") == 1
    assert _scalar(engine, "SELECT COUNT(*) FROM bills WHERE is_zero_km = 1") == 1
    assert _scalar(engine, "SELECT COUNT(*) FROM legs WHERE dq_flag = 'negative_km'") == 1
    assert _scalar(engine, "SELECT COUNT(*) FROM legs WHERE is_placeholder = 1") == 1
    # NULL slab kept as explicit NULL storage (UNSLABBED is a Story-02 display rule).
    assert _scalar(engine, "SELECT COUNT(*) FROM bills WHERE slab_name IS NULL") == 1

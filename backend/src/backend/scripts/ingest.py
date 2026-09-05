"""CSV -> DB loader for Story 01 (idempotent DELETE + reload).

Rerunning yields identical counts: each table is DELETEd before its files are
streamed in (no TRUNCATE — not SQLite-compatible; no upsert — messy input has
no reliable unique key). Exit non-zero only on schema mismatch (missing
file/column); count deviation past ±0.5% is a logged warning, not a failure.

Run from backend/: PYTHONPATH=src uv run python -m backend.scripts.ingest
--data ../problem-statement/dataset/data
"""

import argparse
import asyncio
import csv
import sys
from collections import Counter
from datetime import date as _date
from datetime import datetime as _datetime
from pathlib import Path

from sqlalchemy import delete

import backend.models  # noqa: F401  # register tables on Base.metadata
from backend.core.config import settings
from backend.core.database import Base, build_engine
from backend.core.marts import populate_marts
from backend.core.normalize import (
    is_real_rider,  # noqa: F401  (re-exported for Story 02 use)
    norm_bool,
    norm_contract,
    norm_float,
    norm_int,
    norm_km,
    norm_rating,
    norm_severity,
    norm_slab,
    norm_string,
    norm_stwid,
    norm_trip_id,
    parse_alert_time,
    parse_cycle_time,
    parse_feedback_creation_time,
    parse_feedback_trip_date,
    parse_iso_date,
    parse_trip_date,
)
from backend.models.marts import DailyKpi, InsightCache, OfficeKpi, VendorKpi  # noqa: F401
from backend.models.ops import Alert, Bill, Feedback, Leg, Trip

BATCH_SIZE = 10_000

EXPECTED_COUNTS = {
    "trips": 615546,
    "legs": 1637906,
    "bills": 620942,
    "alerts": 51699,
    "feedback": 512873,
}

TRIP_FILES = [
    "Ride_data _trip-may_2026.csv",
    "Ride_data _trip-June_2026.csv",
    "Ride_data _trip-July_2026.csv",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "trips": [
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
    ],
    "legs": [
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
    "bills": [
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
    "alerts": [
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
    "feedback": [
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
}

TABLE_MODELS = {
    "trips": Trip,
    "legs": Leg,
    "bills": Bill,
    "alerts": Alert,
    "feedback": Feedback,
}


class SchemaMismatchError(RuntimeError):
    """Missing file or column — CLI maps this to exit 2."""


def _check_file(path: Path, table: str) -> list[str]:
    if not path.is_file():
        raise SchemaMismatchError(f"missing file for {table}: {path}")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
    missing = [c for c in REQUIRED_COLUMNS[table] if c not in header]
    if missing:
        raise SchemaMismatchError(f"schema mismatch in {path.name}: missing {missing}")
    return header


def _convert_trip(raw: dict, flags: Counter) -> dict | None:
    try:
        trip_id = norm_trip_id(raw.get("trip_id"))
    except ValueError:
        flags["trip_id_errors"] += 1
        return None
    trip_date = parse_trip_date(raw.get("trip_date"))
    if trip_date is None:
        flags["trips_date_null"] += 1
    nc_driver = norm_bool(raw.get("is_driver_nc"))
    nc_cab = norm_bool(raw.get("is_cab_nc"))
    if nc_driver is None and (raw.get("is_driver_nc") or "").strip() == "":
        pass
    nodal = norm_string(raw.get("trip_nodal"))
    if nodal is None:
        flags["trips_nodal_null"] += 1
    return {
        "business_unit": norm_string(raw.get("business_unit")),
        "office": norm_string(raw.get("office")),
        "product_type": norm_string(raw.get("product_type")),
        "trip_date": trip_date,
        "shift_type": norm_string(raw.get("shift_type")),
        "trip_id": trip_id,
        "trip_direction": norm_string(raw.get("trip_direction")),
        "actual_escort": norm_bool(raw.get("actual_escort")),
        "vendor_id": norm_string(raw.get("vendor_id")),
        "planned_cab_registration": norm_string(raw.get("planned_cab_registration")),
        "actual_cab_registration": norm_string(raw.get("actual_cab_registration")),
        "actual_cab_capacity": norm_int(raw.get("actual_cab_capacity")),
        "planned_km": norm_float(raw.get("planned_km")),
        "traveled_km": norm_float(raw.get("traveled_km")),
        "planned_start_epoch": norm_float(raw.get("planned_start_epoch")),
        "planned_end_epoch": norm_float(raw.get("planned_end_epoch")),
        "actual_start_epoch": norm_float(raw.get("actual_start_epoch")),
        "actual_end_epoch": norm_float(raw.get("actual_end_epoch")),
        "delay_reason": norm_string(raw.get("delay_reason")),
        "delay_minutes": norm_float(raw.get("delay_minutes")),
        "route_source": norm_string(raw.get("route_source")),
        "actual_cab_fuel_type": norm_string(raw.get("actual_cab_fuel_type")),
        "is_driver_nc": nc_driver,
        "is_cab_nc": nc_cab,
        "trip_nodal": nodal,
        "plannedemployee_cnt": norm_int(raw.get("plannedemployee_cnt")),
        "actualemployee_cnt": norm_int(raw.get("actualemployee_cnt")),
        "noshow_cnt": norm_int(raw.get("noshow_cnt")),
    }


def _convert_leg(raw: dict, flags: Counter) -> dict | None:
    try:
        trip_id = norm_trip_id(raw.get("trip_id"))
    except ValueError:
        flags["trip_id_errors"] += 1
        return None
    planned_km, planned_flag = norm_km(raw.get("planned_km"))
    traveled_km, traveled_flag = norm_km(raw.get("traveled_km"))
    dq_flag = None
    if planned_flag == "negative_km" or traveled_flag == "negative_km":
        dq_flag = "negative_km"
        flags["negative_km"] += 1
    stwid, is_placeholder = norm_stwid(raw.get("stwid"))
    if is_placeholder:
        flags["legs_placeholder"] += 1
    trip_date = parse_iso_date(raw.get("trip_date"))
    if trip_date is None:
        flags["legs_date_null"] += 1
    return {
        "business_unit": norm_string(raw.get("business_unit")),
        "office": norm_string(raw.get("office")),
        "product_type": norm_string(raw.get("product_type")),
        "trip_date": trip_date,
        "shift_type": norm_string(raw.get("shift_type")),
        "trip_id": trip_id,
        "planned_pickup_epoch": norm_float(raw.get("planned_pickup_epoch")),
        "planned_drop_epoch": norm_float(raw.get("planned_drop_epoch")),
        "actual_pickup_epoch": norm_float(raw.get("actual_pickup_epoch")),
        "actual_drop_epoch": norm_float(raw.get("actual_drop_epoch")),
        "planned_km": planned_km,
        "traveled_km": traveled_km,
        "stwid": stwid,
        "is_placeholder": is_placeholder,
        "dq_flag": dq_flag,
        "signintype": norm_string(raw.get("signintype")),
        "gender": norm_string(raw.get("gender")),
        "emp_role": norm_string(raw.get("emp_role")),
        "boarding_status": norm_string(raw.get("boarding_status")),
        "not_boarding_reason": norm_string(raw.get("not_boarding_reason")),
        "is_no_show": norm_bool(raw.get("is_no_show")),
    }


def _convert_bill(raw: dict, flags: Counter) -> dict | None:
    try:
        trip_id = norm_trip_id(raw.get("trip_id"))
    except ValueError:
        flags["trip_id_errors"] += 1
        return None
    total_km = norm_float(raw.get("total_trip_km"))
    is_zero_km = total_km == 0
    if is_zero_km:
        flags["zero_km"] += 1
    slab = norm_slab(raw.get("slab_name"))
    if slab is None:
        flags["null_slab"] += 1
    return {
        "business_unit": norm_string(raw.get("business_unit")),
        "office": norm_string(raw.get("office")),
        "vendor": norm_string(raw.get("vendor")),
        "cycle_start": parse_cycle_time(raw.get("cycle_start")),
        "cycle_end": parse_cycle_time(raw.get("cycle_end")),
        "trip_id": trip_id,
        "contract": norm_contract(raw.get("contract")),
        "slab_name": slab,
        "total_trip_km": total_km,
        "is_zero_km": bool(is_zero_km),
        "trip_cost": norm_float(raw.get("trip_cost")),
    }


def _convert_alert(raw: dict, flags: Counter) -> dict | None:
    try:
        trip_id = norm_trip_id(raw.get("trip_id"))
    except ValueError:
        flags["trip_id_errors"] += 1
        return None
    stwid, is_placeholder = norm_stwid(raw.get("stwid"))
    if is_placeholder:
        flags["alerts_placeholder"] += 1
    severity, severity_raw, dq_flag = norm_severity(raw.get("severity"))
    if dq_flag == "severity_false":
        flags["severity_false"] += 1
    elif dq_flag == "severity_unknown":
        flags["severity_unknown"] += 1
    elif severity is None:
        flags["severity_unclassified"] += 1
    return {
        "business_unit": norm_string(raw.get("business_unit")),
        "trip_id": trip_id,
        "stwid": stwid,
        "is_placeholder": is_placeholder,
        "event_id": norm_string(raw.get("event_id")),
        "event_type": norm_string(raw.get("event_type")),
        "start_time": parse_alert_time(raw.get("start_time")),
        "acknowledge_time": parse_alert_time(raw.get("acknowledge_time")),
        "state_text": norm_string(raw.get("state_text")),
        "severity": severity,
        "severity_raw": severity_raw,
        "dq_flag": dq_flag,
        "source": norm_string(raw.get("source")),
    }


def _convert_feedback(raw: dict, flags: Counter) -> dict | None:
    try:
        trip_id = norm_trip_id(raw.get("trip_id"))
    except ValueError:
        flags["trip_id_errors"] += 1
        return None
    stwid, is_placeholder = norm_stwid(raw.get("stwid"))
    if is_placeholder:
        flags["feedback_placeholder"] += 1
    return {
        "business_unit": norm_string(raw.get("business_unit")),
        "trip_id": trip_id,
        "trip_type": norm_string(raw.get("trip_type")),
        "trip_date": parse_feedback_trip_date(raw.get("trip_date")),
        "stwid": stwid,
        "is_placeholder": is_placeholder,
        "route_rating": norm_rating(raw.get("route_rating")),
        "driver_rating": norm_rating(raw.get("driver_rating")),
        "cab_rating": norm_rating(raw.get("cab_rating")),
        "safety_rating": norm_rating(raw.get("safety_rating")),
        "marshal_rating": norm_rating(raw.get("marshal_rating")),
        "creation_time": parse_feedback_creation_time(raw.get("creation_time")),
    }


_CONVERTERS = {
    "trips": _convert_trip,
    "legs": _convert_leg,
    "bills": _convert_bill,
    "alerts": _convert_alert,
    "feedback": _convert_feedback,
}


def _table_files(data_dir: Path, table: str) -> list[Path]:
    if table == "trips":
        return [data_dir / name for name in TRIP_FILES]
    names = {
        "legs": "emp_Data.csv",
        "bills": "bill_data.csv",
        "alerts": "alerts_data.csv",
        "feedback": "trip_feedback.csv",
    }
    return [data_dir / names[table]]


async def run_ingest(
    data_dir: Path | str,
    database_url: str | None = None,
    tables: list[str] | None = None,
) -> dict:
    """Load requested tables; return {counts, flags, dates} for the load report."""
    data_dir = Path(data_dir)
    url = database_url or settings.database_url
    wanted = list(tables) if tables else ["trips", "legs", "bills", "alerts", "feedback"]
    unknown = [t for t in wanted if t not in TABLE_MODELS]
    if unknown:
        raise SchemaMismatchError(f"unknown tables: {unknown}")

    # Schema check first — fail before touching the DB.
    for table in wanted:
        for path in _table_files(data_dir, table):
            _check_file(path, table)

    engine = build_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    flags: Counter = Counter()
    counts: dict[str, int] = {}
    dates: dict[str, dict[str, str | None]] = {}

    try:
        for table in wanted:
            model = TABLE_MODELS[table]
            converter = _CONVERTERS[table]
            date_min = None
            date_max = None
            loaded = 0
            async with engine.begin() as conn:
                await conn.execute(delete(model))
                batch: list[dict] = []
                for path in _table_files(data_dir, table):
                    with open(path, encoding="utf-8-sig", newline="") as fh:  # noqa: ASYNC230 — CLI bulk load streams sync CSV
                        for raw in csv.DictReader(fh):
                            row = converter(raw, flags)
                            if row is None:
                                continue
                            batch.append(row)
                            loaded += 1
                            marker = (
                                row.get("trip_date")
                                or row.get("start_time")
                                or row.get("cycle_start")
                                or row.get("creation_time")
                            )
                            day = None
                            if isinstance(marker, _datetime):
                                day = marker.date()
                            elif isinstance(marker, _date):
                                day = marker
                            if day is not None:
                                if date_min is None or day < date_min:
                                    date_min = day
                                if date_max is None or day > date_max:
                                    date_max = day
                            if len(batch) >= BATCH_SIZE:
                                await conn.execute(model.__table__.insert(), batch)
                                batch.clear()
                if batch:
                    await conn.execute(model.__table__.insert(), batch)
                    batch.clear()
            counts[table] = loaded
            dates[table] = {
                "min": date_min.isoformat() if date_min is not None else None,
                "max": date_max.isoformat() if date_max is not None else None,
            }

        mart_counts = {}
        async with engine.begin() as conn:
            mart_counts = await populate_marts(conn)
    finally:
        await engine.dispose()

    _print_report(counts, flags, dates)
    if mart_counts:
        print("== mart load report ==")
        for table, n in mart_counts.items():
            print(f"{table}: {n} rows")
    return {"counts": counts, "flags": dict(flags), "dates": dates, "mart_counts": mart_counts}


def _print_report(counts: dict[str, int], flags: Counter, dates: dict) -> None:
    print("== ingest load report ==")
    for table, n in counts.items():
        span = dates.get(table, {})
        print(f"{table}: {n} rows (date min={span.get('min')} max={span.get('max')})")
        expected = EXPECTED_COUNTS.get(table)
        if expected:
            dev = (n - expected) / expected if expected else 0
            if abs(dev) > 0.005:
                print(
                    f"WARNING: {table} count {n} deviates {dev:+.2%} from expected "
                    f"{expected} — reason: dataset version drift or skipped "
                    "bad-trip_id rows; joins still valid if spot checks pass."
                )
    if flags:
        print("flags:")
        for key in sorted(flags):
            print(f"  {key}: {flags[key]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load transport CSVs into the DB.")
    parser.add_argument(
        "--data",
        default=str(Path.cwd() / "problem-statement" / "dataset" / "data"),
        help="Directory holding the 7 dataset CSVs.",
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument(
        "--tables",
        default=None,
        help="Comma-separated subset of trips,legs,bills,alerts,feedback.",
    )
    args = parser.parse_args(argv)
    tables = [t.strip() for t in args.tables.split(",") if t.strip()] if args.tables else None
    try:
        asyncio.run(run_ingest(Path(args.data), args.database_url, tables))
    except SchemaMismatchError as exc:
        print(f"schema mismatch: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

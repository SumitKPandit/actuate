"""Pure normalization helpers — no DB (Story 01, TECH_SPEC §4/§6)."""

from datetime import date, datetime

from backend.core.normalize import (
    is_real_rider,
    norm_bool,
    norm_contract,
    norm_float,
    norm_int,
    norm_km,
    norm_rating,
    norm_severity,
    norm_slab,
    norm_stwid,
    norm_trip_id,
    parse_alert_time,
    parse_cycle_time,
    parse_feedback_creation_time,
    parse_feedback_trip_date,
    parse_iso_date,
    parse_moment,
    parse_trip_date,
)


def test_trip_id_three_shapes() -> None:
    assert norm_trip_id("1,097,076") == 1097076
    assert norm_trip_id("1123974") == 1123974
    assert norm_trip_id(1123974) == 1123974


def test_stwid_placeholder_and_real_rider() -> None:
    assert norm_stwid(0) == (0, True)
    assert norm_stwid("0") == (0, True)
    assert norm_stwid("149,530") == (149530, False)
    assert norm_stwid(484475) == (484475, False)
    assert is_real_rider(0) is False
    assert is_real_rider(None) is False
    assert is_real_rider(149530) is True


def test_date_formats() -> None:
    assert parse_trip_date("May 1, 2026") == date(2026, 5, 1)
    assert parse_iso_date("2026-07-09") == date(2026, 7, 9)
    assert parse_moment("June 3, 2026, 11:00 AM") == datetime(2026, 6, 3, 11, 0)  # noqa: DTZ001 — naive dataset dates
    assert parse_moment("May 1, 2026, 12:03 AM") == datetime(2026, 5, 1, 0, 3)  # noqa: DTZ001 — naive dataset dates
    # Per-file wrappers share the moment format; feedback trip_date keeps date part.
    assert parse_feedback_trip_date("June 3, 2026, 11:00 AM") == date(2026, 6, 3)
    assert parse_feedback_creation_time("June 3, 2026, 10:44 AM") == datetime(  # noqa: DTZ001 — naive dataset dates
        2026, 6, 3, 10, 44
    )
    assert parse_alert_time("May 1, 2026, 12:03 AM") == datetime(2026, 5, 1, 0, 3)  # noqa: DTZ001 — naive dataset dates
    assert parse_cycle_time("May 1, 2026, 12:00 AM") == datetime(2026, 5, 1, 0, 0)  # noqa: DTZ001 — naive dataset dates


def test_severity_false_and_na() -> None:
    assert norm_severity("False") == (None, "False", "severity_false")
    assert norm_severity("NA") == (None, None, None)
    assert norm_severity("Sev-1") == ("Sev-1", "Sev-1", None)
    assert norm_severity("Sev-2") == ("Sev-2", "Sev-2", None)


def test_negative_km_flagged() -> None:
    assert norm_km("-2.0") == (None, "negative_km")
    assert norm_km("-6.63") == (None, "negative_km")
    value, flag = norm_km("9.967")
    assert value == 9.967
    assert flag is None


def test_zero_km_and_null_slab_kept() -> None:
    assert norm_float("0") == 0.0
    assert norm_float("0.0") == 0.0
    assert norm_slab("null") is None
    assert norm_slab("NA") is None
    assert norm_slab("") is None
    assert norm_slab("Medium") == "Medium"
    assert norm_contract("null") is None
    assert norm_contract("4S-EV-Z") == "4S-EV-Z"


def test_bool_variants() -> None:
    assert norm_bool("true") is True
    assert norm_bool("false") is False
    assert norm_bool("False") is False
    assert norm_bool("True") is True
    assert norm_bool("") is None
    assert norm_bool(True) is True
    assert norm_bool(False) is False


def test_comma_numerics_including_july_planned_km() -> None:
    assert norm_float("1,200") == 1200.0
    assert norm_float("1,777,595,400") == 1777595400.0
    assert norm_float("1,092.56") == 1092.56
    assert norm_float("10,644") == 10644.0
    assert norm_int("1,200") == 1200
    assert norm_rating("5") == 5
    assert norm_rating(0) == 0

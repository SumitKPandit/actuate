"""KPI analytics tests — Story 02 TECH_SPEC §6 (test-first, plain dicts, no DB)."""

import statistics
from datetime import datetime

from backend.core.analytics import (
    alert_stats,
    cost_stats,
    csat_stats,
    delay_stats,
    flag_cost_outliers,
    no_show_stats,
    ota_pct,
)


def test_ota_boundary() -> None:
    rows = [
        {"delay_minutes": 15.0},
        {"delay_minutes": 15.01},
        {"delay_minutes": 16.0},
    ]
    assert ota_pct(rows) == {"all": {"n": 3, "late_count": 2, "ota_pct": 33.33}}


def test_ota_hand_computed() -> None:
    rows = [{"delay_minutes": 0.0}] * 95 + [{"delay_minutes": 20.0}] * 5
    assert ota_pct(rows) == {"all": {"n": 100, "late_count": 5, "ota_pct": 95.0}}


def test_ota_grouped() -> None:
    rows = [
        {"vendor_id": "A", "delay_minutes": 0.0},
        {"vendor_id": "A", "delay_minutes": 20.0},
        {"vendor_id": "B", "delay_minutes": 0.0},
        {"vendor_id": "B", "delay_minutes": 0.0},
        {"delay_minutes": 20.0},
        {"vendor_id": None, "delay_minutes": 0.0},
    ]
    got = ota_pct(rows, group_key="vendor_id")
    assert got["A"] == {"n": 2, "late_count": 1, "ota_pct": 50.0}
    assert got["B"] == {"n": 2, "late_count": 0, "ota_pct": 100.0}
    assert got["UNKNOWN"] == {"n": 2, "late_count": 1, "ota_pct": 50.0}


def test_ota_empty_returns_none() -> None:
    assert ota_pct([]) == {"all": {"n": 0, "late_count": 0, "ota_pct": None}}
    rows = [{"delay_minutes": None}, {"delay_minutes": None}]
    assert ota_pct(rows) == {"all": {"n": 0, "late_count": 0, "ota_pct": None}}


def test_delay_avg_and_reason_mix() -> None:
    rows = [
        {"delay_minutes": 0.0, "delay_reason": "NODELAY"},
        {"delay_minutes": 20.0, "delay_reason": "TRAFFIC"},
        {"delay_minutes": 30.0, "delay_reason": "driver"},
        {"delay_minutes": 10.0, "delay_reason": None},
    ]
    got = delay_stats(rows)["all"]
    assert got["n"] == 4
    assert got["late_count"] == 2
    assert got["avg_delay_min"] == 15.0
    # reason_mix is late-only: on-time rows (0/NODELAY, 10/None) excluded.
    assert got["reason_mix"]["NODELAY"] == {"count": 0, "share": 0.0}
    assert got["reason_mix"]["TRAFFIC"] == {"count": 1, "share": 0.5}
    assert got["reason_mix"]["DRIVER"] == {"count": 1, "share": 0.5}
    assert got["reason_mix"]["UNKNOWN"] == {"count": 0, "share": 0.0}
    assert got["reason_mix"]["EMPLOYEE"] == {"count": 0, "share": 0.0}


def test_reason_mix_late_only_excludes_on_time() -> None:
    rows = [
        {"delay_minutes": 0.0, "delay_reason": "TRAFFIC"},
        {"delay_minutes": 20.0, "delay_reason": "TRAFFIC"},
        {"delay_minutes": 30.0, "delay_reason": "DRIVER"},
        {"delay_minutes": 40.0, "delay_reason": None},
    ]
    got = delay_stats(rows)["all"]
    assert got["late_count"] == 3
    assert got["reason_mix"]["TRAFFIC"] == {"count": 1, "share": 0.33}
    assert got["reason_mix"]["DRIVER"] == {"count": 1, "share": 0.33}
    assert got["reason_mix"]["UNKNOWN"] == {"count": 1, "share": 0.33}
    assert got["reason_mix"]["NODELAY"] == {"count": 0, "share": 0.0}


def test_reason_mix_no_late_shares_none() -> None:
    rows = [
        {"delay_minutes": 0.0, "delay_reason": "NODELAY"},
        {"delay_minutes": 10.0, "delay_reason": "TRAFFIC"},
    ]
    got = delay_stats(rows)["all"]
    assert got["n"] == 2
    assert got["late_count"] == 0
    for bucket in ("NODELAY", "TRAFFIC", "DRIVER", "EMPLOYEE", "UNKNOWN"):
        assert got["reason_mix"][bucket]["count"] == 0
        assert got["reason_mix"][bucket]["share"] is None


def test_delay_all_none() -> None:
    rows = [{"delay_minutes": None, "delay_reason": "TRAFFIC"}]
    got = delay_stats(rows)["all"]
    assert got["n"] == 0
    assert got["late_count"] == 0
    assert got["avg_delay_min"] is None
    for bucket in ("NODELAY", "TRAFFIC", "DRIVER", "EMPLOYEE", "UNKNOWN"):
        assert got["reason_mix"][bucket]["count"] == 0
        assert got["reason_mix"][bucket]["share"] is None


def test_no_show_rate() -> None:
    legs = [{"is_no_show": True}] * 2 + [{"is_no_show": False}] * 7 + [{"is_no_show": None}]
    got = no_show_stats(legs)["all"]
    assert got == {"legs": 10, "no_shows": 2, "no_show_pct": 20.0}


def test_no_show_split_and_labels() -> None:
    legs = [
        {"shift_type": "A", "is_no_show": True, "boarding_status": "Boarded"},
        {"shift_type": "A", "is_no_show": False, "boarding_status": "No Show"},
        {"shift_type": "B", "is_no_show": True, "boarding_status": "x"},
        {"shift_type": "B", "is_no_show": 1, "boarding_status": "x"},
        {"shift_type": "B", "is_no_show": "true", "boarding_status": "x"},
    ]
    got = no_show_stats(legs, group_key="shift_type")
    assert got["A"] == {"legs": 2, "no_shows": 1, "no_show_pct": 50.0}
    # 1 / "true" do not count (strict identity); disagreeing label ignored.
    assert got["B"] == {"legs": 3, "no_shows": 1, "no_show_pct": 33.33}
    assert no_show_stats([]) == {"all": {"legs": 0, "no_shows": 0, "no_show_pct": None}}


def test_cost_per_km_ignores_zero_km() -> None:
    rows = [
        {"trip_cost": 1000.0, "total_trip_km": 10.0},
        {"trip_cost": 1200.0, "total_trip_km": 0.0},
    ]
    got = cost_stats(rows)["all"]
    assert got["billed_trips"] == 2
    assert got["total_cost"] == 2200.0
    assert got["total_km"] == 10.0
    assert got["cost_per_trip"] == 1100.0
    assert got["cost_per_km"] == 220.0
    assert got["zero_km_count"] == 1
    assert got["zero_km_share"] == 50.0


def test_zero_km_counted_and_negative_excluded() -> None:
    rows = [
        {"trip_cost": 1000.0, "total_trip_km": 0.0},
        {"trip_cost": 1000.0, "total_trip_km": 0.0},
    ]
    got = cost_stats(rows)["all"]
    assert got["cost_per_km"] is None
    assert got["zero_km_count"] == 2
    assert got["zero_km_share"] == 100.0

    rows = [
        {"trip_cost": 1000.0, "total_trip_km": 10.0},
        {"trip_cost": 500.0, "total_trip_km": -5.0},
        {"trip_cost": None, "total_trip_km": 0.0},
    ]
    got = cost_stats(rows)["all"]
    assert got["billed_trips"] == 2
    assert got["total_cost"] == 1500.0
    assert got["total_km"] == 10.0
    assert got["zero_km_count"] == 1
    assert got["zero_km_share"] == 33.33


def test_outlier_flagged() -> None:
    costs = [1200.0] * 10 + [16000.0]
    threshold = statistics.mean(costs) + 3 * statistics.pstdev(costs)
    assert round(threshold, 2) == 15309.56
    # sample stdev would give a different threshold — locks pstdev.
    sample_threshold = statistics.mean(costs) + 3 * statistics.stdev(costs)
    assert round(sample_threshold, 2) == 15932.56

    rows = [{"trip_cost": c, "total_trip_km": 10.0} for c in costs]
    snapshot = [dict(r) for r in rows]
    flagged = flag_cost_outliers(rows)
    assert [f["is_outlier"] for f in flagged].count(True) == 1
    assert flagged[-1]["is_outlier"] is True
    assert all(f["is_outlier"] is False for f in flagged[:-1])
    # input never mutated
    assert rows == snapshot
    assert all("is_outlier" not in r for r in rows)


def test_outlier_single_row_group() -> None:
    assert flag_cost_outliers([{"trip_cost": 5000.0}])[0]["is_outlier"] is False
    rows = [
        {"vendor": "A", "trip_cost": 1000.0},
        {"vendor": "B", "trip_cost": 99999.0},
    ]
    flagged = flag_cost_outliers(rows, group_key="vendor")
    assert all(f["is_outlier"] is False for f in flagged)


def test_csat_excludes_zeros() -> None:
    rows = [
        {
            "route_rating": 5,
            "driver_rating": 0,
            "cab_rating": 4,
            "safety_rating": 0,
            "marshal_rating": 0,
        },
        {
            "route_rating": 4,
            "driver_rating": 4,
            "cab_rating": 0,
            "safety_rating": 4,
            "marshal_rating": 4,
        },
    ]
    got = csat_stats(rows)
    assert got["per_dim"]["route_rating"] == {"avg": 4.5, "n_rated": 2, "n_unrated": 0}
    # route has no zeros here; check a dim with a zero:
    assert got["per_dim"]["driver_rating"] == {"avg": 4.0, "n_rated": 1, "n_unrated": 1}
    assert got["per_dim"]["cab_rating"] == {"avg": 4.0, "n_rated": 1, "n_unrated": 1}
    assert got["per_dim"]["marshal_rating"] == {"avg": 4.0, "n_rated": 1, "n_unrated": 1}


def test_low_rating_share() -> None:
    rows = [
        {
            "route_rating": 5,
            "driver_rating": 2,
            "cab_rating": 4,
            "safety_rating": 1,
            "marshal_rating": 1,  # excluded from low_rating_share pool
        },
        {
            "route_rating": 5,
            "driver_rating": 5,
            "cab_rating": 5,
            "safety_rating": 5,
            "marshal_rating": 0,
        },
    ]
    got = csat_stats(rows)
    # pooled 8 rated across 4 non-marshal dims, 2 below 3 -> 25.0 (percent)
    assert got["low_rating_share"] == 25.0
    assert got["csat_avg"] == 4.0


def test_marshal_unrated() -> None:
    rows = [
        {"route_rating": 5, "driver_rating": 5, "cab_rating": 5, "safety_rating": 5, "marshal_rating": 0},
        {"route_rating": 5, "driver_rating": 5, "cab_rating": 5, "safety_rating": 5, "marshal_rating": 0},
        {"route_rating": 5, "driver_rating": 5, "cab_rating": 5, "safety_rating": 5, "marshal_rating": 5},
    ]
    got = csat_stats(rows)
    assert got["marshal_unrated_share"] == 66.67


def test_csat_all_zero_and_all_none() -> None:
    rows = [
        {"route_rating": 0, "driver_rating": 0, "cab_rating": 0, "safety_rating": 0, "marshal_rating": 0},
        {"route_rating": 0, "driver_rating": 0, "cab_rating": 0, "safety_rating": 0, "marshal_rating": 0},
    ]
    got = csat_stats(rows)
    assert got["per_dim"]["route_rating"] == {"avg": None, "n_rated": 0, "n_unrated": 2}
    assert got["low_rating_share"] is None
    assert got["csat_avg"] is None

    rows = [
        {"route_rating": None, "driver_rating": None, "cab_rating": None, "safety_rating": None, "marshal_rating": None},
    ]
    got = csat_stats(rows)
    assert got["per_dim"]["route_rating"] == {"avg": None, "n_rated": 0, "n_unrated": 0}
    assert got["csat_avg"] is None
    assert got["low_rating_share"] is None
    assert got["marshal_unrated_share"] is None
    assert csat_stats([])["csat_avg"] is None


def test_alert_rate_and_unclassified_severity() -> None:
    base = datetime(2026, 5, 1, 0, 0)  # noqa: DTZ001 — naive dataset dates
    alerts = [
        {"severity": "Sev-1", "start_time": base, "acknowledge_time": base},
        {"severity": None, "start_time": base, "acknowledge_time": base},
        {"severity": None, "start_time": base, "acknowledge_time": base},
    ]
    got = alert_stats(alerts, 1000)
    assert got["alerts"] == 3
    assert got["trips"] == 1000
    assert got["alert_rate_per_1k"] == 3.0
    assert got["sev1_count"] == 1
    assert got["sev2_count"] == 0
    assert got["sev_breakdown"]["Sev-1"] == {"count": 1, "share": 0.33}
    assert got["sev_breakdown"]["unclassified"] == {"count": 2, "share": 0.67}

    got = alert_stats(alerts, 0)
    assert got["alert_rate_per_1k"] is None
    got = alert_stats(alerts, None)
    assert got["alert_rate_per_1k"] is None

    got = alert_stats([], 100)
    assert got["alerts"] == 0
    assert got["sev_breakdown"]["Sev-1"] == {"count": 0, "share": None}

    # all-None severity folds into unclassified share 1.0
    got = alert_stats(
        [{"severity": None, "start_time": base, "acknowledge_time": base}], 10
    )
    assert got["sev_breakdown"]["unclassified"] == {"count": 1, "share": 1.0}


def test_ack_sla() -> None:
    base = datetime(2026, 5, 1, 8, 0)  # noqa: DTZ001 — naive dataset dates
    alerts = [
        {"severity": "Sev-1", "start_time": base, "acknowledge_time": datetime(2026, 5, 1, 8, 10)},  # noqa: DTZ001 — naive dataset dates
        {"severity": "Sev-2", "start_time": base, "acknowledge_time": datetime(2026, 5, 1, 8, 40)},  # noqa: DTZ001 — naive dataset dates
        {"severity": "Sev-3", "start_time": base, "acknowledge_time": None},
    ]
    got = alert_stats(alerts, 100)
    assert got["avg_ack_minutes"] == 25.0
    assert got["ack_sla_met_share"] == 33.33
    assert got["unacknowledged_count"] == 1


def test_ack_negative_clamped_and_start_none() -> None:
    base = datetime(2026, 5, 1, 12, 0)  # noqa: DTZ001 — naive dataset dates
    alerts = [
        {
            "severity": "Sev-1",
            "start_time": base,
            "acknowledge_time": datetime(2026, 5, 1, 11, 50),  # noqa: DTZ001 — naive dataset dates
        },
        {"severity": "Sev-2", "start_time": None, "acknowledge_time": None},
    ]
    got = alert_stats(alerts, 10)
    assert got["alerts"] == 2
    assert got["avg_ack_minutes"] == 0.0
    assert got["ack_sla_met_share"] == 100.0
    assert got["unacknowledged_count"] == 1


def test_nan_inf_skipped() -> None:
    rows = [
        {"delay_minutes": float("nan")},
        {"delay_minutes": float("inf")},
        {"delay_minutes": 20.0},
        {"delay_minutes": None},
    ]
    assert ota_pct(rows) == {"all": {"n": 1, "late_count": 1, "ota_pct": 0.0}}

    rows = [
        {"trip_cost": float("nan"), "total_trip_km": 10.0},
        {"trip_cost": float("inf"), "total_trip_km": 10.0},
        {"trip_cost": 1000.0, "total_trip_km": 10.0},
    ]
    got = cost_stats(rows)["all"]
    assert got["billed_trips"] == 1
    assert got["total_cost"] == 1000.0


def test_group_unknown_only_for_none_missing() -> None:
    rows = [
        {"office": 0, "delay_minutes": 0.0},
        {"office": "", "delay_minutes": 0.0},
        {"delay_minutes": 0.0},
    ]
    got = ota_pct(rows, group_key="office")
    assert got[0]["n"] == 1
    assert got[""]["n"] == 1
    assert got["UNKNOWN"]["n"] == 1
    # False is falsy-but-present: stays as-is, never maps to UNKNOWN.
    got = ota_pct([{"office": False, "delay_minutes": 0.0}], group_key="office")
    assert got[False]["n"] == 1
    assert "UNKNOWN" not in got


def test_object_rows_supported() -> None:
    class Row:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    rows = [Row(delay_minutes=0.0), Row(delay_minutes=20.0)]
    assert ota_pct(rows) == {"all": {"n": 2, "late_count": 1, "ota_pct": 50.0}}

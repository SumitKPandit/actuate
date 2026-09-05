"""Reasoning + ranking tests — Story 03 TECH_SPEC §6 (test-first, plain dicts, no DB)."""

import statistics

import pytest

from backend.core.reason import (
    ACTION_MAP,
    BENCHMARKS,
    build_insights,
    check_absolute,
    check_mom_delta,
    check_peer,
    check_zscore,
    contribution_top2,
    rank_insights,
)

CYCLE = "2026-06-H2"


def test_ota_breach_vs_sla() -> None:
    got = check_absolute({"trips": 12000, "ota_pct": 93.0}, cycle=CYCLE)
    assert len(got) == 1
    ins = got[0]
    assert ins["kpi"] == "ota_pct"
    assert ins["baseline"] == 95.0
    assert ins["delta_pp"] == -2.0
    assert ins["severity"] == "high"
    assert ins["reason"] == "vs_sla"
    assert ins["recommended_action"], ins["owner"] == ACTION_MAP["ota_pct"]
    assert ins["id"] == "ota_pct_vs_sla_2026_06_h2_all"


def test_no_breach_when_above_sla() -> None:
    assert check_absolute({"trips": 100, "ota_pct": 96.5}, cycle=CYCLE) == []
    assert check_absolute({"trips": 100, "avg_ack_minutes": 30.0}, cycle=CYCLE) == []
    assert check_absolute({"trips": 100, "max_trip_cost": 16000.0}, cycle=CYCLE) == []


def test_ack_breach() -> None:
    got = check_absolute({"trips": 500, "avg_ack_minutes": 35.0}, cycle=CYCLE)
    assert len(got) == 1
    ins = got[0]
    assert ins["kpi"] == "ack"
    assert ins["baseline"] == 30.0
    assert ins["delta_pp"] == 5.0
    assert ins["severity"] == "high"
    assert ins["reason"] == "vs_sla"


def test_cost_sanity() -> None:
    got = check_absolute({"trips": 100, "max_trip_cost": 16500.0}, cycle=CYCLE)
    assert len(got) == 1
    ins = got[0]
    assert ins["kpi"] == "cost"
    assert ins["reason"] == "anomaly"
    assert ins["baseline"] == 16000.0
    assert ins["delta_pp"] == 3.12  # 100*500/16000 = 3.125 -> 3.12
    assert ins["severity"] == "high"
    assert ins["reach_trips"] == 1


def test_cost_outlier_vendor() -> None:
    rows = [{"vendor": f"V{i}", "cost_per_trip": 1200.0, "trips": 100} for i in range(10)]
    rows.append({"vendor": "OUT", "cost_per_trip": 16000.0, "trips": 50})
    got = check_absolute({"trips": 1000}, cycle=CYCLE, vendor_rows=rows)
    assert len(got) == 1
    ins = got[0]
    assert ins["kpi"] == "cost"
    assert ins["reason"] == "anomaly"
    assert ins["severity"] == "medium"
    assert ins["scope"]["vendor"] == "OUT"
    assert ins["baseline"] == 15309.56
    tight = [
        {"vendor": "A", "cost_per_trip": 1200.0, "trips": 100},
        {"vendor": "B", "cost_per_trip": 1250.0, "trips": 100},
        {"vendor": "C", "cost_per_trip": 1300.0, "trips": 100},
    ]
    assert check_absolute({"trips": 100}, cycle=CYCLE, vendor_rows=tight) == []


def test_contribution_top2() -> None:
    v1 = [
        {"key": "A", "trips": 6000, "late_count": 600},
        {"key": "B", "trips": 4000, "late_count": 300},
        {"key": "C", "trips": 2000, "late_count": 40},
    ]
    got = contribution_top2(v1)
    assert [t["key"] for t in got["top2"]] == ["A", "B"]
    assert got["top2"][0]["excess"] == 130.0
    assert got["top2"][0]["share"] == 1.0
    assert got["top2"][1]["excess"] == 0.0
    assert got["top2"][1]["share"] == 0.0
    assert got["contribution_share"] == 1.0

    v2 = [
        {"key": "A", "trips": 1000, "late_count": 200},
        {"key": "B", "trips": 1000, "late_count": 190},
        {"key": "C", "trips": 1000, "late_count": 170},
        {"key": "D", "trips": 1000, "late_count": 140},
        {"key": "E", "trips": 6000, "late_count": 300},
    ]
    got = contribution_top2(v2)
    assert [t["key"] for t in got["top2"]] == ["A", "B"]
    assert got["top2"][0]["share"] == 0.33
    assert got["top2"][1]["share"] == 0.3
    assert got["contribution_share"] == 0.63


def test_ranking_severity_x_reach() -> None:
    ins = [
        {"id": "b", "severity": "medium", "reach_trips": 12000, "delta_pp": 1.0},
        {"id": "a", "severity": "high", "reach_trips": 100, "delta_pp": 5.0},
    ]
    assert [i["id"] for i in rank_insights(ins)] == ["b", "a"]

    tie = [
        {"id": "x", "severity": "medium", "reach_trips": 1000, "delta_pp": 1.0},
        {"id": "y", "severity": "medium", "reach_trips": 1000, "delta_pp": 3.0},
    ]
    assert [i["id"] for i in rank_insights(tie)] == ["y", "x"]

    full_tie = [
        {"id": "b", "severity": "medium", "reach_trips": 1000, "delta_pp": 1.0},
        {"id": "a", "severity": "medium", "reach_trips": 1000, "delta_pp": 1.0},
    ]
    assert [i["id"] for i in rank_insights(full_tie)] == ["a", "b"]


def test_zscore_needs_min_points() -> None:
    scope = {"vendor": None, "office": None, "trips": 1000}
    short = [95.0] * 12 + [80.0]
    got = check_zscore(short, kpi="ota_pct", scope=scope, cycle=CYCLE)
    assert got["insights"] == []
    assert got["skipped"] is True
    assert got["reason_skipped"] == "zscore_needs_14_points"
    assert got["n"] == 13

    flat = [95.0] * 14
    got = check_zscore(flat, kpi="ota_pct", scope=scope, cycle=CYCLE)
    assert got["insights"] == []
    assert got["skipped"] is False

    series = [95.0] * 19 + [80.0]
    got = check_zscore(series, kpi="ota_pct", scope=scope, cycle=CYCLE)
    assert len(got["insights"]) == 1
    ins = got["insights"][0]
    assert ins["reason"] == "anomaly"
    assert ins["baseline"] == 94.25
    assert ins["current"] == 80.0
    assert ins["severity"] == "medium"
    mean = statistics.mean(series)
    sd = statistics.pstdev(series)
    assert (series[-1] - mean) / sd == pytest.approx(-4.36, abs=0.01)

    good = [80.0] * 19 + [95.0]
    got = check_zscore(good, kpi="ota_pct", scope=scope, cycle=CYCLE)
    assert got["insights"] == []


def test_mom_delta_threshold() -> None:
    assert check_mom_delta({"ota_pct": 97.0, "trips": 100}, {"ota_pct": 95.0}, cycle=CYCLE) == []
    got = check_mom_delta({"ota_pct": 97.01, "trips": 100}, {"ota_pct": 95.0}, cycle=CYCLE)
    assert len(got) == 1
    assert got[0]["delta_pp"] == 2.01

    assert check_mom_delta({"cost_per_trip": 1100.0, "trips": 100}, {"cost_per_trip": 1000.0}, cycle=CYCLE) == []
    got = check_mom_delta({"cost_per_trip": 1100.01, "trips": 100}, {"cost_per_trip": 1000.0}, cycle=CYCLE)
    assert len(got) == 1

    assert check_mom_delta({"cost_per_trip": 1000.0, "trips": 100}, {"cost_per_trip": 0}, cycle=CYCLE) == []

    assert check_mom_delta({"csat_avg": 2.0, "trips": 100}, {"csat_avg": 4.8}, cycle=CYCLE) == []
    got = check_mom_delta({"low_rating_share": 7.01, "trips": 100}, {"low_rating_share": 5.0}, cycle=CYCLE)
    assert len(got) == 1
    assert got[0]["kpi"] == "csat"


def test_peer_worst_and_tight() -> None:
    splits = [
        {"key": "A", "value": 96.0, "trips": 5000},
        {"key": "B", "value": 95.5, "trips": 4000},
        {"key": "C", "value": 88.0, "trips": 3000},
    ]
    got = check_peer(splits, kpi="ota_pct", cycle=CYCLE, dim="vendor")
    assert len(got) == 1
    assert got[0]["scope"]["vendor"] == "C"
    assert got[0]["baseline"] == 93.17
    assert got[0]["delta_pp"] == -5.17
    assert got[0]["reach_trips"] == 3000
    assert got[0]["reason"] == "vs_peer"

    tight = [
        {"key": "A", "value": 96.0, "trips": 5000},
        {"key": "B", "value": 95.5, "trips": 4000},
        {"key": "C", "value": 95.0, "trips": 3000},
    ]
    assert check_peer(tight, kpi="ota_pct", cycle=CYCLE, dim="vendor") == []

    cost = [
        {"key": "A", "value": 1200.0, "trips": 100},
        {"key": "B", "value": 1250.0, "trips": 100},
        {"key": "C", "value": 1800.0, "trips": 100},
    ]
    got = check_peer(cost, kpi="cost", cycle=CYCLE, dim="vendor")
    assert len(got) == 1
    assert got[0]["scope"]["vendor"] == "C"

    with_none = [
        {"key": "A", "value": None, "trips": 100},
        {"key": "B", "value": 96.0, "trips": 100},
        {"key": "C", "value": 95.5, "trips": 100},
    ]
    assert check_peer(with_none, kpi="ota_pct", cycle=CYCLE, dim="vendor") == []


def test_sev1_small_series_fallback() -> None:
    got = check_mom_delta({"sev1_count": 9, "trips": 500}, {"sev1_count": 4}, cycle=CYCLE)
    assert len(got) == 1
    assert got[0]["kpi"] == "sev1"
    assert got[0]["severity"] == "high"
    assert got[0]["reason"] == "vs_prior"
    assert got[0]["delta_pp"] == 5.0

    got = check_mom_delta({"sev1_count": 1, "trips": 10}, {"sev1_count": 0}, cycle=CYCLE)
    assert len(got) == 1

    got = check_mom_delta(
        {"sev1_count": 9, "trips": 500}, {"sev1_count": 4}, cycle=CYCLE, allow_sev1_fallback=False
    )
    assert got == []


def test_benchmarks_single_source() -> None:
    assert set(BENCHMARKS) == {
        "ota_sla_pct",
        "ack_sla_min",
        "rate_delta_pp",
        "cost_delta_pct",
        "z_thresh",
        "z_min_points",
        "sev1_spike_sigma",
        "sev1_spike_prior_mult",
        "cost_outlier_sigma",
        "cost_sanity_max",
        "severity_weights",
    }


def test_ota_top_insight_with_contributors() -> None:
    snapshot = {"trips": 12000, "ota_pct": 93.0, "cost_per_trip": 1150.0}
    prior = {"ota_pct": 95.0, "cost_per_trip": 1000.0}
    delay_splits = [
        {"key": "A", "trips": 1000, "late_count": 200},
        {"key": "B", "trips": 1000, "late_count": 190},
        {"key": "C", "trips": 1000, "late_count": 170},
        {"key": "D", "trips": 1000, "late_count": 140},
        {"key": "E", "trips": 6000, "late_count": 300},
    ]
    vendor_rows = [
        {"vendor": "A", "ota_pct": 96.0, "cost_per_trip": 1200.0, "trips": 5000},
        {"vendor": "B", "ota_pct": 95.5, "cost_per_trip": 1250.0, "trips": 4000},
        {"vendor": "C", "ota_pct": 88.0, "cost_per_trip": 1300.0, "trips": 3000},
    ]
    kwargs: dict = {"snapshot": snapshot, "prior": prior, "vendor_rows": vendor_rows, "delay_splits": delay_splits, "cycle": CYCLE}
    first = build_insights(**kwargs)
    second = build_insights(**kwargs)
    assert [i["id"] for i in first] == [i["id"] for i in second]
    top = first[0]
    assert top["kpi"] == "ota_pct"
    assert top["reason"] == "vs_sla"
    assert top["severity"] == "high"
    assert top["contribution_share"] == 0.63
    assert top["scope"]["cycle"] == CYCLE
    ids = [i["id"] for i in first]
    assert top["id"] == "ota_pct_vs_sla_2026_06_h2_all"
    assert any("_v_" in i for i in ids)
    assert top["id"] not in [i for i in ids if "_v_" in i]

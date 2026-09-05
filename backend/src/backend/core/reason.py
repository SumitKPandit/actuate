"""Deterministic Reason+Ranks — benchmarks, anomalies, contribution, ranking (Story 03). See stories/03-reason-rank/SPEC.md."""

import math
import statistics
from collections.abc import Mapping

BENCHMARKS = {
    "ota_sla_pct": 95.0,
    "ack_sla_min": 30.0,
    "rate_delta_pp": 2.0,
    "cost_delta_pct": 10.0,
    "z_thresh": 2.0,
    "z_min_points": 14,
    "sev1_spike_sigma": 2.0,
    "sev1_spike_prior_mult": 2.0,
    "cost_outlier_sigma": 3.0,
    "cost_sanity_max": 16000.0,
    "severity_weights": {"high": 3, "medium": 2, "low": 1},
}

ACTION_MAP = {
    "ota_pct": ("Re-route / add buffer + vendor penalty review", "vendor"),
    "sev1": ("Acknowledge open Sev-1s + escort audit", "ops"),
    "ack": ("Acknowledge open Sev-1s + escort audit", "ops"),
    "cost": ("Hold bill line + verify km slab", "ops"),
    "csat": ("Driver/cab review with vendor", "vendor"),
    "no_show": ("Shift reminder + standby cab", "office"),
}

KPI_IDS = ("ota_pct", "sev1", "ack", "cost", "csat", "no_show")
REASONS = ("vs_sla", "vs_prior", "vs_peer", "anomaly")


def _get(row, key, default=None):
    if isinstance(row, Mapping):
        if key in row:
            return row[key]
        return getattr(row, key, default)
    return getattr(row, key, default)


def _r2(x):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return round(f, 2)


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _slug(s):
    if s is None:
        return "unknown"
    text = str(s).lower()
    if text == "":
        return "unknown"
    out: list[str] = []
    prev_us = False
    for ch in text:
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            out.append(ch)
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    slug = "".join(out).strip("_")
    return slug if slug else "unknown"


def _score(severity, reach):
    w = BENCHMARKS["severity_weights"].get(severity, 0)
    r = int(reach) if _is_num(reach) else 0
    return w * r


def _peer_splits(rows, field, name_key):
    if not rows:
        return []
    out = []
    for r in rows:
        v = _get(r, field)
        if not _is_num(v):
            continue
        out.append({"key": _get(r, name_key), "value": float(v), "trips": _reach(_get(r, "trips", 0))})
    return out


def _reach(v):
    return int(v) if _is_num(v) else 0


def _scope(vendor, office, cycle):
    return {"vendor": vendor, "office": office, "cycle": cycle}


def _insight(kpi, reason, cycle, vendor, office, current, baseline, delta, severity, reach):
    scope_part = f"v_{vendor}" if vendor is not None else f"o_{office}" if office is not None else "all"
    cycle_part = cycle if cycle else "unknown"
    action, owner = ACTION_MAP[kpi]
    return {
        "id": _slug(f"{kpi}_{reason}_{cycle_part}_{scope_part}"),
        "kpi": kpi,
        "scope": _scope(vendor, office, cycle),
        "current": current,
        "baseline": baseline,
        "delta_pp": delta,
        "severity": severity,
        "reach_trips": int(reach),
        "contribution_share": None,
        "reason": reason,
        "recommended_action": action,
        "owner": owner,
    }


def check_absolute(snapshot, *, cycle, vendor_rows=None, as_of=None):
    snap = snapshot or {}
    out = []
    reach = _reach(_get(snap, "trips", 0))
    cur = _get(snap, "ota_pct")
    if _is_num(cur) and float(cur) < BENCHMARKS["ota_sla_pct"]:
        base = BENCHMARKS["ota_sla_pct"]
        out.append(_insight("ota_pct", "vs_sla", cycle, None, None, float(cur), base, _r2(float(cur) - base), "high", reach))
    cur = _get(snap, "avg_ack_minutes")
    if _is_num(cur) and float(cur) > BENCHMARKS["ack_sla_min"]:
        base = BENCHMARKS["ack_sla_min"]
        out.append(_insight("ack", "vs_sla", cycle, None, None, float(cur), base, _r2(float(cur) - base), "high", reach))
    cur = _get(snap, "max_trip_cost")
    if _is_num(cur) and float(cur) > BENCHMARKS["cost_sanity_max"]:
        base = BENCHMARKS["cost_sanity_max"]
        out.append(_insight("cost", "anomaly", cycle, None, None, float(cur), base, _r2(100 * (float(cur) - base) / base), "high", 1))
    vals = [float(_get(r, "cost_per_trip")) for r in (vendor_rows or []) if _is_num(_get(r, "cost_per_trip"))]
    if len(vals) >= 2:
        sd = statistics.pstdev(vals)
        if sd != 0:
            limit = statistics.mean(vals) + BENCHMARKS["cost_outlier_sigma"] * sd
            for r in vendor_rows or []:
                v = _get(r, "cost_per_trip")
                if _is_num(v) and float(v) > limit:
                    out.append(_insight("cost", "anomaly", cycle, _get(r, "vendor"), None, float(v), _r2(limit), _r2(100 * (float(v) - limit) / limit), "medium", _reach(_get(r, "trips", 0))))
    return out


def _mom_rate(cur, pri):
    return _is_num(cur) and _is_num(pri) and abs(float(cur) - float(pri)) > BENCHMARKS["rate_delta_pp"]


def _mom_cost(cur, pri):
    return _is_num(cur) and _is_num(pri) and float(pri) != 0 and abs(100 * (float(cur) - float(pri)) / float(pri)) > BENCHMARKS["cost_delta_pct"]


def check_mom_delta(current, prior, *, cycle, scope=None, allow_sev1_fallback=True, as_of=None):
    if current is None or prior is None:
        return []
    out = []
    vendor = _get(scope, "vendor") if scope else None
    office = _get(scope, "office") if scope else None
    reach = _reach(_get(current, "trips", 0))
    for field, kpi in (("ota_pct", "ota_pct"), ("alert_rate_per_1k", "ack"), ("avg_ack_minutes", "ack"), ("low_rating_share", "csat")):
        c, p = _get(current, field), _get(prior, field)
        if _mom_rate(c, p):
            out.append(_insight(kpi, "vs_prior", cycle, vendor, office, float(c), float(p), _r2(float(c) - float(p)), "medium", reach))
    c = _get(current, "no_show_rate") if _get(current, "no_show_rate") is not None else _get(current, "no_show_pct")
    p = _get(prior, "no_show_rate") if _get(prior, "no_show_rate") is not None else _get(prior, "no_show_pct")
    if _mom_rate(c, p):
        out.append(_insight("no_show", "vs_prior", cycle, vendor, office, float(c), float(p), _r2(float(c) - float(p)), "medium", reach))
    for field in ("cost_per_trip", "cost_per_km"):
        c, p = _get(current, field), _get(prior, field)
        if _mom_cost(c, p):
            out.append(_insight("cost", "vs_prior", cycle, vendor, office, float(c), float(p), _r2(100 * (float(c) - float(p)) / float(p)), "medium", reach))
    if allow_sev1_fallback:
        c, p = _get(current, "sev1_count"), _get(prior, "sev1_count")
        fired = _is_num(c) and _is_num(p) and (float(c) > 0 if float(p) == 0 else float(c) > BENCHMARKS["sev1_spike_prior_mult"] * float(p))
        if fired:
            out.append(_insight("sev1", "vs_prior", cycle, vendor, office, float(c), float(p), _r2(float(c) - float(p)), "high", reach))
    return out


def check_peer(splits, *, kpi, cycle, dim, as_of=None):
    if dim not in ("vendor", "office"):
        raise ValueError("dim must be 'vendor' or 'office'")
    if kpi not in ACTION_MAP:
        return []
    rows = [{"key": _get(s, "key"), "value": float(_get(s, "value")), "trips": _reach(_get(s, "trips", 0))} for s in (splits or []) if _is_num(_get(s, "value"))]
    if len(rows) < 2:
        return []
    vals = [r["value"] for r in rows]
    mean = statistics.mean(vals)
    if kpi == "ota_pct":
        worst = min(rows, key=lambda r: r["value"])
        if not (mean - worst["value"]) > BENCHMARKS["rate_delta_pp"]:
            return []
        delta = _r2(worst["value"] - mean)
    elif kpi == "cost":
        worst = max(rows, key=lambda r: r["value"])
        if mean == 0 or not abs(100 * (worst["value"] - mean) / mean) > BENCHMARKS["cost_delta_pct"] or worst["value"] <= mean:
            return []
        delta = _r2(100 * (worst["value"] - mean) / mean)
    else:
        worst = max(rows, key=lambda r: r["value"])
        if not (worst["value"] - mean) > BENCHMARKS["rate_delta_pp"]:
            return []
        delta = _r2(worst["value"] - mean)
    vendor = worst["key"] if dim == "vendor" else None
    office = worst["key"] if dim == "office" else None
    return [_insight(kpi, "vs_peer", cycle, vendor, office, worst["value"], _r2(mean), delta, "medium", worst["trips"])]


def check_zscore(series, *, kpi, scope, cycle, as_of=None):
    filt = [float(x) for x in (series or []) if _is_num(x)]
    n = len(filt)
    if n < BENCHMARKS["z_min_points"]:
        return {"insights": [], "skipped": True, "reason_skipped": "zscore_needs_14_points", "kpi": kpi, "n": n}
    if kpi not in ACTION_MAP:
        return {"insights": [], "skipped": False, "kpi": kpi, "n": n}
    mean = statistics.mean(filt)
    sd = statistics.pstdev(filt)
    if sd == 0:
        return {"insights": [], "skipped": False, "kpi": kpi, "n": n}
    last = filt[-1]
    z = (last - mean) / sd
    thresh = BENCHMARKS["z_thresh"]
    fires = z < -thresh if kpi in ("ota_pct", "csat") else z > thresh
    if not fires:
        return {"insights": [], "skipped": False, "kpi": kpi, "n": n}
    base = _r2(mean)
    delta = _r2(100 * (last - mean) / mean) if kpi == "cost" and mean != 0 else None if kpi == "cost" else _r2(last - base)
    vendor = _get(scope, "vendor") if scope else None
    office = _get(scope, "office") if scope else None
    ins = _insight(kpi, "anomaly", cycle, vendor, office, last, base, delta, "high" if kpi == "sev1" else "medium", _reach(_get(scope, "trips", 0) if scope else 0))
    return {"insights": [ins], "skipped": False, "kpi": kpi, "n": n}


def contribution_top2(splits):
    valid = []
    for s in splits or []:
        t, late = _get(s, "trips"), _get(s, "late_count")
        if not _is_num(t) or not _is_num(late) or float(t) <= 0:
            continue
        valid.append({"key": _get(s, "key"), "trips": float(t), "late": float(late)})
    if not valid:
        return {"top2": [], "contribution_share": None}
    overall = sum(v["late"] for v in valid) / sum(v["trips"] for v in valid)
    for v in valid:
        v["excess"] = max(0.0, v["late"] - v["trips"] * overall)
    total = sum(v["excess"] for v in valid)
    top = sorted(valid, key=lambda r: -r["excess"])[: min(2, len(valid))]
    if total == 0:
        return {"top2": [{"key": r["key"], "excess": _r2(r["excess"]), "share": None} for r in top], "contribution_share": None}
    return {
        "top2": [{"key": r["key"], "excess": _r2(r["excess"]), "share": _r2(r["excess"] / total)} for r in top],
        "contribution_share": _r2(sum(r["excess"] for r in top) / total),
    }


def rank_insights(insights):
    def keyfn(ins):
        return (-_score(_get(ins, "severity"), _get(ins, "reach_trips", 0)), -abs(float(_get(ins, "delta_pp"))) if _is_num(_get(ins, "delta_pp")) else 0.0, str(_get(ins, "id", "") or ""))

    return sorted(insights or [], key=keyfn)


def _has_long_series(daily_series, kpi):
    if not isinstance(daily_series, Mapping):
        return False
    s = daily_series.get(kpi) if isinstance(daily_series, dict) else _get(daily_series, kpi)
    if not isinstance(s, (list, tuple)):
        return False
    return sum(1 for x in s if _is_num(x)) >= BENCHMARKS["z_min_points"]


def build_insights(*, snapshot, prior=None, vendor_rows=None, office_rows=None, delay_splits=None, daily_series=None, cycle, as_of=None):
    snap = snapshot or {}
    insights = check_absolute(snap, cycle=cycle, vendor_rows=vendor_rows, as_of=as_of)
    if prior is not None:
        insights.extend(check_mom_delta(snap, prior, cycle=cycle, scope=None, allow_sev1_fallback=not _has_long_series(daily_series, "sev1"), as_of=as_of))
    for kpi, field in (("ota_pct", "ota_pct"), ("ack", "alert_rate_per_1k"), ("cost", "cost_per_trip"), ("csat", "low_rating_share")):
        if vendor_rows:
            sp = _peer_splits(vendor_rows, field, "vendor")
            if sp:
                insights.extend(check_peer(sp, kpi=kpi, cycle=cycle, dim="vendor", as_of=as_of))
        if office_rows:
            sp = _peer_splits(office_rows, field, "office")
            if sp:
                insights.extend(check_peer(sp, kpi=kpi, cycle=cycle, dim="office", as_of=as_of))
    if isinstance(daily_series, Mapping) and daily_series:
        zscope = {"vendor": None, "office": None, "trips": _reach(_get(snap, "trips", 0))}
        for kpi, series in daily_series.items():
            if kpi not in KPI_IDS or not isinstance(series, (list, tuple)):
                continue
            insights.extend(check_zscore(list(series), kpi=kpi, scope=zscope, cycle=cycle, as_of=as_of).get("insights", []))
    if delay_splits and any(_get(i, "kpi") in ("ota_pct", "no_show") for i in insights):
        share = contribution_top2(delay_splits).get("contribution_share")
        for ins in insights:
            if _get(ins, "kpi") in ("ota_pct", "no_show"):
                ins["contribution_share"] = share
    return rank_insights(insights)

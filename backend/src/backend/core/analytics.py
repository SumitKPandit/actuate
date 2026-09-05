"""Pure MVP KPI math — no DB, no HTTP, no LLM (Story 02). See stories/02-analytics-kpis/SPEC.md."""

import math
import statistics
from collections.abc import Mapping
from datetime import datetime

LATE_THRESHOLD_MIN = 15.0
ACK_SLA_MIN = 30.0
REASONS = ("NODELAY", "TRAFFIC", "DRIVER", "EMPLOYEE")
CSAT_DIMS = ("route_rating", "driver_rating", "cab_rating", "safety_rating")
MARSHAL_DIM = "marshal_rating"
SEVERITIES = ("Sev-1", "Sev-2", "Sev-3")


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


def _group_rows(rows, group_key):
    items = list(rows)
    if group_key is None:
        return {"all": items}
    groups: dict = {}
    for r in items:
        v = _get(r, group_key, None)
        k = "UNKNOWN" if v is None else v
        groups.setdefault(k, []).append(r)
    return groups


def ota_pct(rows, group_key=None):
    out = {}
    for g, grp in _group_rows(rows, group_key).items():
        n = 0
        late = 0
        for r in grp:
            v = _get(r, "delay_minutes")
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            if not math.isfinite(v):
                continue
            n += 1
            if float(v) > LATE_THRESHOLD_MIN:
                late += 1
        out[g] = {"n": n, "late_count": late, "ota_pct": _r2(100 * (1 - late / n)) if n else None}
    return out


def delay_stats(rows, group_key=None):
    out = {}
    for g, grp in _group_rows(rows, group_key).items():
        vals: list[float] = []
        counts = {k: 0 for k in (*REASONS, "UNKNOWN")}
        for r in grp:
            v = _get(r, "delay_minutes")
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            if not math.isfinite(v):
                continue
            vals.append(float(v))
            if float(v) <= LATE_THRESHOLD_MIN:
                continue
            raw = _get(r, "delay_reason")
            b = raw.strip().upper() if isinstance(raw, str) else ""
            counts[b if b in REASONS else "UNKNOWN"] += 1
        n = len(vals)
        late = sum(1 for d in vals if d > LATE_THRESHOLD_MIN)
        avg = _r2(sum(vals) / n) if n else None
        mix = {k: {"count": c, "share": _r2(c / late) if late else None} for k, c in counts.items()}
        out[g] = {"n": n, "late_count": late, "avg_delay_min": avg, "reason_mix": mix}
    return out


def no_show_stats(rows, group_key=None):
    out = {}
    for g, grp in _group_rows(rows, group_key).items():
        legs = len(grp)
        ns = sum(1 for r in grp if _get(r, "is_no_show") is True)
        out[g] = {"legs": legs, "no_shows": ns, "no_show_pct": _r2(100 * ns / legs) if legs else None}
    return out


def cost_stats(rows, group_key=None):
    out = {}
    for g, grp in _group_rows(rows, group_key).items():
        costs: list[float] = []
        km_sum = 0.0
        zero = 0
        for r in grp:
            c = _get(r, "trip_cost")
            if not isinstance(c, bool) and isinstance(c, (int, float)) and math.isfinite(c):
                costs.append(float(c))
            k = _get(r, "total_trip_km")
            if not isinstance(k, bool) and isinstance(k, (int, float)) and math.isfinite(k):
                if k > 0:
                    km_sum += float(k)
                if k == 0:
                    zero += 1
        billed = len(costs)
        total = _r2(sum(costs)) if costs else 0.0
        tkm = _r2(km_sum)
        cpt = _r2(total / billed) if billed else None
        cpk = _r2(total / km_sum) if km_sum > 0 else None
        share = _r2(100 * zero / len(grp)) if grp else None
        out[g] = {
            "billed_trips": billed,
            "total_cost": total,
            "total_km": tkm,
            "cost_per_trip": cpt,
            "cost_per_km": cpk,
            "zero_km_count": zero,
            "zero_km_share": share,
        }
    return out


def flag_cost_outliers(rows, group_key=None):
    items = list(rows)
    limits: dict = {}
    for g, grp in _group_rows(items, group_key).items():
        vals = []
        for r in grp:
            c = _get(r, "trip_cost")
            if not isinstance(c, bool) and isinstance(c, (int, float)) and math.isfinite(c):
                vals.append(float(c))
        if len(vals) < 2:
            limits[g] = None
            continue
        sd = statistics.pstdev(vals)
        limits[g] = statistics.mean(vals) + 3 * sd if sd != 0 else None
    out = []
    for r in items:
        if group_key is None:
            g = "all"
        else:
            v = _get(r, group_key, None)
            g = "UNKNOWN" if v is None else v
        lim = limits.get(g)
        c = _get(r, "trip_cost")
        ok = not isinstance(c, bool) and isinstance(c, (int, float)) and math.isfinite(c)
        flag = bool(lim is not None and ok and float(c) > lim)
        if isinstance(r, Mapping):
            d = dict(r)
        else:
            try:
                d = {k: v2 for k, v2 in vars(r).items() if not k.startswith("_")}
            except TypeError:
                d = {}
        d["is_outlier"] = flag
        out.append(d)
    return out


def alert_stats(alerts, trips_count):
    items = list(alerts)
    total = len(items)
    try:
        rate = None if trips_count is None or trips_count == 0 else _r2(1000 * total / float(trips_count))
    except (TypeError, ValueError):
        rate = None
    counts = {"Sev-1": 0, "Sev-2": 0, "Sev-3": 0, "unclassified": 0}
    ack_vals: list[float] = []
    met = 0
    denom = 0
    unack = 0
    for r in items:
        s = _get(r, "severity")
        counts[s if s in SEVERITIES else "unclassified"] += 1
        start = _get(r, "start_time")
        ack = _get(r, "acknowledge_time")
        if ack is None:
            unack += 1
        if not isinstance(start, datetime):
            continue
        denom += 1
        if not isinstance(ack, datetime):
            continue
        try:
            mins = (ack - start).total_seconds() / 60
        except (TypeError, ValueError, OverflowError):
            continue
        mins = max(0.0, mins)
        ack_vals.append(mins)
        if mins <= ACK_SLA_MIN:
            met += 1
    avg = _r2(sum(ack_vals) / len(ack_vals)) if ack_vals else None
    share = _r2(100 * met / denom) if denom else None
    bd = {k: {"count": c, "share": _r2(c / total) if total else None} for k, c in counts.items()}
    return {"alerts": total, "trips": trips_count, "alert_rate_per_1k": rate, "sev1_count": counts["Sev-1"],
            "sev2_count": counts["Sev-2"], "sev_breakdown": bd, "avg_ack_minutes": avg,
            "ack_sla_met_share": share, "unacknowledged_count": unack}


def csat_stats(rows):
    items = list(rows)
    per: dict = {}
    avgs: dict = {}
    pool: list[int] = []
    for dim in (*CSAT_DIMS, MARSHAL_DIM):
        s = 0
        rated = 0
        unrated = 0
        for r in items:
            v = _get(r, dim)
            if isinstance(v, bool) or not isinstance(v, int):
                continue
            if v == 0:
                unrated += 1
            else:
                rated += 1
                s += v
                if dim in CSAT_DIMS:
                    pool.append(v)
        avg = _r2(s / rated) if rated else None
        per[dim] = {"avg": avg, "n_rated": rated, "n_unrated": unrated}
        if dim in CSAT_DIMS:
            avgs[dim] = avg
    low = _r2(100 * sum(1 for x in pool if x < 3) / len(pool)) if pool else None
    m_rated = per[MARSHAL_DIM]["n_rated"]
    m_unrated = per[MARSHAL_DIM]["n_unrated"]
    m_total = m_rated + m_unrated
    m_share = _r2(100 * m_unrated / m_total) if m_total else None
    avail = [a for a in avgs.values() if a is not None]
    cavg = _r2(sum(avail) / len(avail)) if avail else None
    return {"per_dim": per, "low_rating_share": low, "marshal_unrated_share": m_share, "csat_avg": cavg}

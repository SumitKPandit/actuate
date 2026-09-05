"""Mart-backed ops routes — overview/insights/briefing/vendors/actions (Story 04)."""

import logging
import math
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.reason import BENCHMARKS, build_insights, contribution_top2
from backend.models.marts import DailyKpi, InsightCache, OfficeKpi, VendorKpi

router = APIRouter(tags=["ops"])
logger = logging.getLogger(__name__)

EMPTY_WARNING = "marts empty — run ingest"


# Pydantic schemas (frontend Stories 05-06 codegen against these).
class OverviewData(BaseModel):
    trips: int | None = None
    ota_pct: float | None = None
    avg_delay_min: float | None = None
    delay_reason_mix: dict | None = None
    no_show_rate: float | None = None
    cost_per_trip: float | None = None
    cost_per_km: float | None = None
    zero_km_share: float | None = None
    alert_rate_per_1k: float | None = None
    sev1_count: int | None = None
    ack_sla_met_share: float | None = None
    csat_avg: float | None = None
    low_rating_share: float | None = None
    benchmarks: dict | None = None


class OverviewResponse(BaseModel):
    data: OverviewData | None = None
    warning: str | None = None


class InsightSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    kpi: str
    scope: dict
    current: float | None = None
    baseline: float | None = None
    delta_pp: float | None = None
    severity: str
    reach_trips: int
    contribution_share: float | None = None
    reason: str
    recommended_action: str
    owner: str


class BriefingData(BaseModel):
    generated_at: str
    headline_facts: list[str]
    insights_top5: list[dict]
    safety_open_sev1: int
    actions_top3: list[dict]


class BriefingResponse(BaseModel):
    data: BriefingData | None = None
    warning: str | None = None


class VendorRow(BaseModel):
    vendor: str
    trips: int | None = None
    ota_pct: float | None = None
    cost_per_trip: float | None = None
    cost_per_km: float | None = None
    alert_rate_per_1k: float | None = None
    csat_avg: float | None = None
    low_rating_share: float | None = None
    peer_rank: int | None = None
    contribution_share: float | None = None
    zero_km_count: int | None = None
    unslabbed_count: int | None = None


class VendorsResponse(BaseModel):
    data: list[VendorRow] | None = None
    warning: str | None = None


class ActionItem(BaseModel):
    id: str
    action: str
    owner: str
    due_hint: str
    copy_for_vendor: str
    status: str


class ActionsResponse(BaseModel):
    data: list[ActionItem] | None = None
    warning: str | None = None


class AckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str = Field(min_length=1)


class AckResponse(BaseModel):
    id: str
    status: str
    actor: str
    acked_at: str


def _r1(x):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return round(f, 1)


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


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _weighted_mean(pairs) -> float | None:
    num = 0.0
    den = 0.0
    for value, weight in pairs:
        if not _is_num(value) or not _is_num(weight) or float(weight) <= 0:
            continue
        num += float(value) * float(weight)
        den += float(weight)
    if den == 0:
        return None
    return num / den


def _sum(values) -> int:
    total = 0
    for v in values:
        if isinstance(v, bool):
            continue
        if isinstance(v, int) and math.isfinite(float(v)):
            total += v
        elif isinstance(v, float) and math.isfinite(v):
            total += int(v)
    return total


def _share(part, whole):
    if not _is_num(part) or not _is_num(whole) or float(whole) == 0:
        return None
    return _r2(float(part) / float(whole))


def _benchmarks() -> dict:
    ota = BENCHMARKS.get("ota_sla_pct", 95.0)
    ack = BENCHMARKS.get("ack_sla_min", 30.0)
    return {"ota_sla": ota, "ack_sla_min": ack}


def _parse_cycle(cycle: str):
    # Form YYYY-MM-H1 | YYYY-MM-H2. H1 = 1st-15th, H2 = 16th-month-end.
    try:
        year_s, mon_s, half = str(cycle).split("-")
        year = int(year_s)
        mon = int(mon_s)
        if len(year_s) != 4 or len(mon_s) != 2 or half not in ("H1", "H2"):
            raise ValueError("bad cycle")
        if not 1 <= mon <= 12:
            raise ValueError("bad month")
    except (ValueError, AttributeError):
        raise ValueError(f"unknown cycle: {cycle}")

    if half == "H1":
        start = date(year, mon, 1)
        end = date(year, mon, 15)
        if mon == 1:
            prior = f"{year - 1}-12-H2"
        else:
            prior = f"{year}-{mon - 1:02d}-H2"
    else:
        start = date(year, mon, 16)
        if mon == 12:
            first_next = date(year + 1, 1, 1)
        else:
            first_next = date(year, mon + 1, 1)
        end = first_next - timedelta(days=1)
        prior = f"{year}-{mon:02d}-H1"
    return start, end, prior


def _valid_cycles(vendor_labels, office_labels) -> list[str]:
    return sorted(set(vendor_labels) | set(office_labels))


def _late_count_for(row) -> int | None:
    delayed = getattr(row, "delayed_trips", None)
    if isinstance(delayed, bool):
        delayed = None
    if isinstance(delayed, (int, float)) and math.isfinite(float(delayed)):
        return int(delayed)
    trips = getattr(row, "trips", None)
    ota = getattr(row, "ota_pct", None)
    if _is_num(trips) and _is_num(ota) and float(trips) > 0:
        return round(float(trips) * (100.0 - float(ota)) / 100.0)
    return None


def _snapshot_from_vendor_rows(rows) -> dict:
    rows = list(rows or [])
    trips = _sum(getattr(r, "trips", None) for r in rows)
    late_total = 0
    late_known = False
    for r in rows:
        lc = _late_count_for(r)
        if lc is not None:
            late_total += lc
            late_known = True
    ota = (100.0 * (1 - late_total / trips)) if trips > 0 and late_known else None
    if trips == 0:
        ota = None
    sev1 = _sum(getattr(r, "sev1_count", None) for r in rows)
    return {
        "trips": trips,
        "ota_pct": ota,
        "avg_delay_min": _weighted_mean([(getattr(r, "avg_delay_min", None), getattr(r, "trips", None)) for r in rows]),
        "no_show_rate": _weighted_mean([(getattr(r, "no_show_rate", None), getattr(r, "trips", None)) for r in rows]),
        "cost_per_trip": _weighted_mean([(getattr(r, "cost_per_trip", None), getattr(r, "trips", None)) for r in rows]),
        "cost_per_km": _weighted_mean([(getattr(r, "cost_per_km", None), getattr(r, "trips", None)) for r in rows]),
        "alert_rate_per_1k": _weighted_mean([(getattr(r, "alert_rate_per_1k", None), getattr(r, "trips", None)) for r in rows]),
        "sev1_count": sev1,
        "avg_ack_minutes": _weighted_mean([(getattr(r, "avg_ack_minutes", None), getattr(r, "trips", None)) for r in rows]),
        "ack_sla_met_share": _weighted_mean([(getattr(r, "ack_sla_met_share", None), getattr(r, "trips", None)) for r in rows]),
        "csat_avg": _weighted_mean([(getattr(r, "csat_avg", None), getattr(r, "trips", None)) for r in rows]),
        "low_rating_share": _weighted_mean([(getattr(r, "low_rating_share", None), getattr(r, "trips", None)) for r in rows]),
        "max_trip_cost": None,
    }


def _delay_splits(rows, key: str) -> list[dict]:
    out = []
    for r in rows or []:
        name = getattr(r, key, None)
        trips = getattr(r, "trips", None)
        late = _late_count_for(r)
        out.append({"key": name, "trips": trips, "late_count": late})
    return out


def _daily_series(daily_rows) -> dict:
    ordered = sorted(daily_rows or [], key=lambda r: r.date)
    return {
        "ota_pct": [getattr(r, "ota_pct", None) for r in ordered],
        "sev1": [getattr(r, "sev1_count", None) for r in ordered],
        "ack": [getattr(r, "alert_rate_per_1k", None) for r in ordered],
        "cost": [getattr(r, "cost_per_trip", None) for r in ordered],
        "csat": [getattr(r, "csat_avg", None) for r in ordered],
        "no_show": [getattr(r, "no_show_rate", None) for r in ordered],
    }


def _fmt1(v) -> str:
    r = _r1(v)
    return "—" if r is None else f"{r}"


def _fmt_cost(v) -> str:
    r = _r2(v)
    return "—" if r is None else f"{r:.2f}"


def _fmt_insight_value(kpi: str, v) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(f):
        return "—"
    if kpi == "cost":
        return f"{round(f, 2):.2f}"
    if kpi == "sev1":
        return f"{int(f)}" if f.is_integer() else f"{round(f, 1)}"
    return f"{round(f, 1)}"


def _headline_facts(snapshot_view: dict, insights: list[dict], cycle: str, benchmarks: dict) -> list[str]:
    facts: list[str] = []
    ota = snapshot_view.get("ota_pct")
    trips = snapshot_view.get("trips")
    ota_sla = benchmarks.get("ota_sla")
    trips_s = f"{int(trips)}" if isinstance(trips, (int, float)) and math.isfinite(float(trips)) else "—"
    facts.append(f"OTA {cycle} was {_fmt1(ota)}% vs SLA {ota_sla}% across {trips_s} trips.")
    if insights:
        top = insights[0]
        scope = top.get("scope", {}) or {}
        scope_str = scope.get("vendor") or scope.get("office") or "all"
        kpi = top.get("kpi")
        facts.append(
            f"Top exception: {kpi} {_fmt_insight_value(kpi, top.get('current'))} vs "
            f"{_fmt_insight_value(kpi, top.get('baseline'))} ({scope_str}) — "
            f"{int(top.get('reach_trips', 0))} trips affected."
        )
    sev1 = snapshot_view.get("sev1_count")
    if isinstance(sev1, (int, float)) and not isinstance(sev1, bool) and int(sev1) > 0 and len(facts) < 5:
        facts.append(f"{int(sev1)} Sev-1 alerts this cycle — acknowledge open items + escort audit.")
    cost_ins = next((i for i in insights if i.get("kpi") == "cost"), None)
    if cost_ins is not None and len(facts) < 5:
        scope = cost_ins.get("scope", {}) or {}
        vendor = scope.get("vendor") or scope.get("office") or "All vendors"
        facts.append(
            f"Cost outlier: {vendor} at ₹{_fmt_cost(cost_ins.get('current'))}/trip — hold bill line + verify km slab."
        )
    fillers = [
        f"CSAT {_fmt1(snapshot_view.get('csat_avg'))} with {_fmt1(snapshot_view.get('low_rating_share'))}% low ratings.",
        f"No-show rate {_fmt1(snapshot_view.get('no_show_rate'))}%.",
    ]
    idx = 0
    while len(facts) < 3 and idx < len(fillers):
        facts.append(fillers[idx])
        idx += 1
    return facts


def _action_from_insight(insight: dict, ack_map: dict) -> dict:
    iid = insight.get("id", "")
    action = insight.get("recommended_action", "")
    owner = insight.get("owner", "")
    severity = insight.get("severity", "")
    if severity == "high":
        due = "within 48 hours"
    elif severity == "medium":
        due = "this cycle"
    else:
        due = "next cycle"
    scope = insight.get("scope", {}) or {}
    vendor_slot = scope.get("vendor") or scope.get("office") or "All vendors"
    kpi = insight.get("kpi", "")
    cycle = scope.get("cycle", "")
    cur = _fmt_insight_value(kpi, insight.get("current"))
    base = _fmt_insight_value(kpi, insight.get("baseline"))
    reach = insight.get("reach_trips", 0)
    try:
        reach_s = int(reach)
    except (TypeError, ValueError):
        reach_s = 0
    copy = (
        f"{vendor_slot}: {action} — {kpi} {cur} vs baseline {base} in "
        f"{cycle} ({reach_s} trips). Owner: {owner}, due {due}."
    )
    if len(copy) > 500:
        copy = copy[:499] + "…"
    status = "acked" if iid in ack_map else "proposed"
    return {
        "id": iid,
        "action": action,
        "owner": owner,
        "due_hint": due,
        "copy_for_vendor": copy,
        "status": status,
    }


async def _is_empty(db: AsyncSession) -> bool:
    for model in (DailyKpi, VendorKpi, OfficeKpi):
        res = await db.execute(select(model).limit(1))
        if res.scalars().first() is not None:
            return False
    return True


async def _get_valid_cycles(db: AsyncSession) -> list[str]:
    res_v = await db.execute(select(VendorKpi.cycle_or_month).distinct())
    res_o = await db.execute(select(OfficeKpi.cycle_or_month).distinct())
    return _valid_cycles([r for (r,) in res_v.all()], [r for (r,) in res_o.all()])


def _unknown_cycle(detail_cycle: str, valid: list[str]):
    return JSONResponse(
        status_code=404,
        content={"detail": "unknown cycle", "cycle": detail_cycle, "valid_cycles": valid},
    )


async def _load_cycle_rows(db: AsyncSession, cycle: str):
    res_v = await db.execute(select(VendorKpi).where(VendorKpi.cycle_or_month == cycle))
    vendor_rows = list(res_v.scalars().all())
    res_o = await db.execute(select(OfficeKpi).where(OfficeKpi.cycle_or_month == cycle))
    office_rows = list(res_o.scalars().all())
    try:
        start, end, prior = _parse_cycle(cycle)
    except ValueError:
        start = end = prior = None
    daily_rows: list = []
    if start is not None and end is not None:
        res_d = await db.execute(select(DailyKpi).where(DailyKpi.date >= start, DailyKpi.date <= end).order_by(DailyKpi.date))
        daily_rows = list(res_d.scalars().all())
    return vendor_rows, office_rows, daily_rows, prior


async def _compute_insights(db: AsyncSession, cycle: str) -> list[dict]:
    vendor_rows, office_rows, daily_rows, prior_label = await _load_cycle_rows(db, cycle)
    snapshot = _snapshot_from_vendor_rows(vendor_rows)
    if daily_rows:
        mx = [getattr(r, "max_trip_cost", None) for r in daily_rows]
        mx = [float(v) for v in mx if _is_num(v)]
        snapshot["max_trip_cost"] = max(mx) if mx else None
    prior = None
    if prior_label is not None:
        res_pv = await db.execute(select(VendorKpi).where(VendorKpi.cycle_or_month == prior_label))
        prior_rows = list(res_pv.scalars().all())
        if prior_rows:
            prior = _snapshot_from_vendor_rows(prior_rows)
    delay_splits = _delay_splits(vendor_rows, "vendor")
    daily_series = _daily_series(daily_rows)
    office_dicts = office_rows
    vendor_dicts = vendor_rows
    return build_insights(
        snapshot=snapshot, prior=prior, vendor_rows=vendor_dicts,
        office_rows=office_dicts, delay_splits=delay_splits,
        daily_series=daily_series, cycle=cycle,
    )


async def _ack_map(db: AsyncSession) -> dict:
    res = await db.execute(select(InsightCache).where(InsightCache.key.like("action:%")))
    out = {}
    for row in res.scalars().all():
        payload = row.payload_json or {}
        iid = payload.get("id")
        if iid:
            out[iid] = payload
    return out


def _overview_from_rows(rows) -> dict:
    rows = list(rows or [])
    trips = _sum(getattr(r, "trips", None) for r in rows)
    late_total = 0
    late_known = False
    for r in rows:
        lc = _late_count_for(r)
        if lc is not None:
            late_total += lc
            late_known = True
    ota = (100.0 * (1 - late_total / trips)) if trips > 0 and late_known else None
    if trips == 0:
        ota = None
    zero_total = _sum(getattr(r, "zero_km_count", None) for r in rows)
    zero_share = (100.0 * zero_total / trips) if trips > 0 else None
    counts: dict[str, int] = {}
    for r in rows:
        m = getattr(r, "late_reason_counts", None) or {}
        if isinstance(m, dict):
            for k, v in m.items():
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    counts[k] = counts.get(k, 0) + int(v)
    late_for_mix = sum(counts.values())
    if counts:
        if late_for_mix > 0:
            mix = {k: {"count": c, "share": _r2(c / late_for_mix)} for k, c in counts.items()}
        else:
            mix = {k: {"count": c, "share": None} for k, c in counts.items()}
    else:
        mix = {}
    sev1 = _sum(getattr(r, "sev1_count", None) for r in rows)
    return {
        "trips": trips,
        "ota_pct": _r1(ota),
        "avg_delay_min": _r1(_weighted_mean([(getattr(r, "avg_delay_min", None), getattr(r, "trips", None)) for r in rows])),
        "delay_reason_mix": mix,
        "no_show_rate": _r1(_weighted_mean([(getattr(r, "no_show_rate", None), getattr(r, "trips", None)) for r in rows])),
        "cost_per_trip": _r2(_weighted_mean([(getattr(r, "cost_per_trip", None), getattr(r, "trips", None)) for r in rows])),
        "cost_per_km": _r2(_weighted_mean([(getattr(r, "cost_per_km", None), getattr(r, "trips", None)) for r in rows])),
        "zero_km_share": _r1(zero_share),
        "alert_rate_per_1k": _r1(_weighted_mean([(getattr(r, "alert_rate_per_1k", None), getattr(r, "trips", None)) for r in rows])),
        "sev1_count": sev1,
        "ack_sla_met_share": _r1(_weighted_mean([(getattr(r, "ack_sla_met_share", None), getattr(r, "trips", None)) for r in rows])),
        "csat_avg": _r1(_weighted_mean([(getattr(r, "csat_avg", None), getattr(r, "trips", None)) for r in rows])),
        "low_rating_share": _r1(_weighted_mean([(getattr(r, "low_rating_share", None), getattr(r, "trips", None)) for r in rows])),
        "benchmarks": _benchmarks(),
    }


def _utcnow():
    return datetime.now(UTC)


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@router.get("/overview")
async def get_overview(
    cycle: str,
    office: str | None = None,
    vendor: str | None = None,
    business_unit: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    _ = business_unit
    if await _is_empty(db):
        return {"data": None, "warning": EMPTY_WARNING}
    try:
        _parse_cycle(cycle)
    except ValueError:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    if vendor is not None:
        res = await db.execute(select(VendorKpi).where(VendorKpi.cycle_or_month == cycle, VendorKpi.vendor == vendor))
        rows = list(res.scalars().all())
    elif office is not None:
        res = await db.execute(select(OfficeKpi).where(OfficeKpi.cycle_or_month == cycle))
        rows = list(res.scalars().all())
    else:
        res = await db.execute(select(VendorKpi).where(VendorKpi.cycle_or_month == cycle))
        rows = list(res.scalars().all())
    if not rows:
        # Distinguish unknown cycle from empty slice: check any rows for cycle.
        vr, orows, dr, _ = await _load_cycle_rows(db, cycle)
        if not vr and not orows and not dr:
            return _unknown_cycle(cycle, await _get_valid_cycles(db))
    return {"data": _overview_from_rows(rows), "warning": None}


@router.get("/insights")
async def get_insights(cycle: str, db: AsyncSession = Depends(get_db)):  # noqa: B008
    if await _is_empty(db):
        return {"data": None, "warning": EMPTY_WARNING}
    try:
        _parse_cycle(cycle)
    except ValueError:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    vendor_rows, office_rows, daily_rows, _ = await _load_cycle_rows(db, cycle)
    if not vendor_rows and not office_rows and not daily_rows:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    return {"data": await _compute_insights(db, cycle), "warning": None}


@router.get("/briefing")
async def get_briefing(cycle: str, narrate: bool | None = None, db: AsyncSession = Depends(get_db)):  # noqa: B008
    if narrate is True:
        raise HTTPException(status_code=422, detail="narrate lands in Story 07")
    if await _is_empty(db):
        return {"data": None, "warning": EMPTY_WARNING}
    try:
        _parse_cycle(cycle)
    except ValueError:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    vendor_rows, office_rows, daily_rows, _ = await _load_cycle_rows(db, cycle)
    if not vendor_rows and not office_rows and not daily_rows:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    key = f"briefing:{cycle}"
    res = await db.execute(select(InsightCache).where(InsightCache.key == key))
    cached = res.scalars().first()
    now = _utcnow()
    if cached is not None and cached.payload_json is not None and cached.computed_at is not None:
        age = (now - _as_utc(cached.computed_at)).total_seconds()
        if age < 6 * 60 * 60:
            return {"data": cached.payload_json, "warning": None}
    insights = await _compute_insights(db, cycle)
    ackmap = await _ack_map(db)
    actions = [_action_from_insight(i, ackmap) for i in insights]
    vendor_rows_all, _, _, _ = await _load_cycle_rows(db, cycle)
    snapshot_raw = _snapshot_from_vendor_rows(vendor_rows_all)
    overview = _overview_from_rows(vendor_rows_all)
    # safety uses raw sev1 sum; overview carries the same int.
    benchmarks = _benchmarks()
    facts = _headline_facts(
        {
            "ota_pct": overview.get("ota_pct"),
            "trips": overview.get("trips"),
            "sev1_count": overview.get("sev1_count"),
            "csat_avg": overview.get("csat_avg"),
            "low_rating_share": overview.get("low_rating_share"),
            "no_show_rate": overview.get("no_show_rate"),
        },
        insights,
        cycle,
        benchmarks,
    )
    _ = snapshot_raw
    payload = {
        "generated_at": now.isoformat(),
        "headline_facts": facts,
        "insights_top5": insights[:5],
        "safety_open_sev1": int(overview.get("sev1_count") or 0),
        "actions_top3": actions[:3],
    }
    if cached is None:
        db.add(InsightCache(key=key, payload_json=payload, computed_at=now))
    else:
        cached.payload_json = payload
        cached.computed_at = now
    await db.commit()
    return {"data": payload, "warning": None}


@router.get("/vendors")
async def get_vendors(
    cycle: str,
    sort: str = "ota",
    business_unit: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    _ = business_unit
    allowed = ("ota", "cost", "alerts", "csat")
    if sort not in allowed:
        return JSONResponse(status_code=422, content={"detail": "invalid sort", "allowed": list(allowed)})
    if await _is_empty(db):
        return {"data": None, "warning": EMPTY_WARNING}
    try:
        _parse_cycle(cycle)
    except ValueError:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    res = await db.execute(select(VendorKpi).where(VendorKpi.cycle_or_month == cycle))
    rows = list(res.scalars().all())
    if not rows:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))

    def _val(r, s: str):
        if s == "ota":
            return getattr(r, "ota_pct", None)
        if s == "cost":
            return getattr(r, "cost_per_trip", None)
        if s == "alerts":
            return getattr(r, "alert_rate_per_1k", None)
        return getattr(r, "csat_avg", None)

    reverse = sort in ("ota", "csat")
    valued = [(r, _val(r, sort)) for r in rows]

    def _sort_key(item):
        r, v = item
        is_none = 1 if (v is None or (isinstance(v, float) and not math.isfinite(v))) else 0
        if is_none:
            return (1, 0, getattr(r, "vendor", ""))
        f = float(v)
        primary = -f if reverse else f
        return (0, primary, getattr(r, "vendor", ""))

    ordered = [r for r, _ in sorted(valued, key=_sort_key)]
    # Competition rank 1,2,2,4 on the displayed sort KPI.
    val_by_vendor = {getattr(r, "vendor", ""): _val(r, sort) for r in ordered}
    ranks: dict[str, int] = {}
    prev = object()
    prev_rank = 0
    for idx, r in enumerate(ordered):
        name = getattr(r, "vendor", "")
        v = val_by_vendor[name]
        norm = None if (v is None or (isinstance(v, float) and not math.isfinite(v))) else float(v)
        if idx == 0:
            rank = 1
        elif norm == prev:
            rank = prev_rank
        else:
            rank = idx + 1
        ranks[name] = rank
        prev = norm
        prev_rank = rank
    splits = _delay_splits(rows, "vendor")
    contrib = contribution_top2(splits)
    share_by_vendor = {t.get("key"): t.get("share") for t in (contrib.get("top2") or [])}
    out = []
    for r in ordered:
        name = getattr(r, "vendor", "")
        out.append(
            {
                "vendor": name,
                "trips": getattr(r, "trips", None),
                "ota_pct": _r1(getattr(r, "ota_pct", None)),
                "cost_per_trip": _r2(getattr(r, "cost_per_trip", None)),
                "cost_per_km": _r2(getattr(r, "cost_per_km", None)),
                "alert_rate_per_1k": _r1(getattr(r, "alert_rate_per_1k", None)),
                "csat_avg": _r1(getattr(r, "csat_avg", None)),
                "low_rating_share": _r1(getattr(r, "low_rating_share", None)),
                "peer_rank": ranks[name],
                "contribution_share": share_by_vendor.get(name),
                "zero_km_count": getattr(r, "zero_km_count", None),
                "unslabbed_count": getattr(r, "unslabbed_count", None),
            }
        )
    return {"data": out, "warning": None}


@router.get("/actions")
async def get_actions(cycle: str, db: AsyncSession = Depends(get_db)):  # noqa: B008
    if await _is_empty(db):
        return {"data": None, "warning": EMPTY_WARNING}
    try:
        _parse_cycle(cycle)
    except ValueError:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    vendor_rows, office_rows, daily_rows, _ = await _load_cycle_rows(db, cycle)
    if not vendor_rows and not office_rows and not daily_rows:
        return _unknown_cycle(cycle, await _get_valid_cycles(db))
    insights = await _compute_insights(db, cycle)
    ackmap = await _ack_map(db)
    return {"data": [_action_from_insight(i, ackmap) for i in insights], "warning": None}


async def _all_action_ids(db: AsyncSession) -> set[str]:
    valid = await _get_valid_cycles(db)
    ids: set[str] = set()
    for cyc in valid:
        try:
            insights = await _compute_insights(db, cyc)
        except Exception:  # noqa: BLE001, S112 - skip bad cycles when scanning ids
            continue
        for ins in insights:
            iid = ins.get("id")
            if iid:
                ids.add(iid)
    return ids


@router.post("/actions/{action_id}/ack")
async def ack_action(action_id: str, payload: AckRequest, db: AsyncSession = Depends(get_db)):  # noqa: B008
    actor = (payload.actor or "").strip()
    if not actor:
        raise HTTPException(status_code=422, detail="actor must be non-blank")
    key = f"action:{action_id}"
    res = await db.execute(select(InsightCache).where(InsightCache.key == key))
    existing = res.scalars().first()
    if existing is not None and existing.payload_json:
        stored = existing.payload_json
        if stored.get("actor") == actor:
            return stored
    else:
        known = await _all_action_ids(db)
        if action_id not in known:
            # Re-ack path: allow if cache row exists (handled above); else 404.
            return JSONResponse(status_code=404, content={"detail": "unknown action id", "id": action_id})
    now = _utcnow()
    record = {"id": action_id, "status": "acked", "actor": actor, "acked_at": now.isoformat()}
    if existing is None:
        db.add(InsightCache(key=key, payload_json=record, computed_at=now))
    else:
        existing.payload_json = record
        existing.computed_at = now
    await db.commit()
    logger.info("action_ack id=%s actor=%s acked_at=%s", action_id, actor, record["acked_at"])
    return record


@router.post("/ask")
async def ask_reserved():
    raise HTTPException(status_code=501, detail="reserved for Story 07 (NL-to-SQL over marts)")

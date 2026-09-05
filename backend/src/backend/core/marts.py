"""Mart population: raw tables → daily_kpi / vendor_kpi / office_kpi (Story 05)."""

import statistics
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import delete, select

from backend.core.analytics import (
    alert_stats,
    cost_stats,
    csat_stats,
    delay_stats,
    no_show_stats,
    ota_pct,
)
from backend.core.reason import BENCHMARKS
from backend.models.marts import DailyKpi, OfficeKpi, ShiftKpi, VendorKpi
from backend.models.ops import Alert, Bill, Feedback, Leg, Trip


def _cycle_for_date(d: date | None) -> str | None:
    if d is None:
        return None
    half = "H1" if d.day <= 15 else "H2"
    return f"{d.year}-{d.month:02d}-{half}"


def _cycle_for_bill(bill: dict) -> str | None:
    start = bill.get("cycle_start")
    if start is None:
        return None
    if isinstance(start, datetime):
        return _cycle_for_date(start.date())
    if isinstance(start, date):
        return _cycle_for_date(start)
    return None


def _vendor_cost_outliers(rows: list[dict]) -> None:
    """Populate persisted outlier flags from each cycle's vendor population."""
    by_cycle: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_cycle[row["cycle_or_month"]].append(row)
    for cycle_rows in by_cycle.values():
        values = [
            float(row["cost_per_trip"])
            for row in cycle_rows
            if isinstance(row.get("cost_per_trip"), (int, float))
            and not isinstance(row["cost_per_trip"], bool)
        ]
        if len(values) < 2:
            for row in cycle_rows:
                row["cost_outlier"] = None
            continue
        threshold = statistics.mean(values) + BENCHMARKS["cost_outlier_sigma"] * statistics.pstdev(values)
        for row in cycle_rows:
            value = row.get("cost_per_trip")
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            row["cost_outlier"] = bool(valid and float(value) > threshold)


async def populate_marts(conn, business_unit: str | None = None) -> dict:
    """Rebuild all marts from raw tables. Returns counts per mart."""
    trips = (await conn.execute(select(Trip))).mappings().all()
    legs = (await conn.execute(select(Leg))).mappings().all()
    bills = (await conn.execute(select(Bill))).mappings().all()
    alerts = (await conn.execute(select(Alert))).mappings().all()
    feedback = (await conn.execute(select(Feedback))).mappings().all()

    trip_by_id = {t["trip_id"]: t for t in trips if t.get("trip_id") is not None}
    legs_by_trip = defaultdict(list)
    for leg in legs:
        if leg.get("trip_id") is not None:
            legs_by_trip[leg["trip_id"]].append(leg)

    alerts_by_trip = defaultdict(list)
    for alert in alerts:
        if alert.get("trip_id") is not None:
            alerts_by_trip[alert["trip_id"]].append(alert)

    feedback_by_trip = defaultdict(list)
    for fb in feedback:
        if fb.get("trip_id") is not None:
            feedback_by_trip[fb["trip_id"]].append(fb)

    bills_by_trip = defaultdict(list)
    for bill in bills:
        if bill.get("trip_id") is not None:
            bills_by_trip[bill["trip_id"]].append(bill)

    # Daily KPIs
    trips_by_date = defaultdict(list)
    for t in trips:
        d = t.get("trip_date")
        if d is not None:
            trips_by_date[d].append(t)

    daily_rows = []
    for d in sorted(trips_by_date.keys()):
        day_trips = trips_by_date[d]
        day_legs = []
        day_alerts = []
        day_bills = []
        day_feedback = []
        for t in day_trips:
            tid = t["trip_id"]
            day_legs.extend(legs_by_trip.get(tid, []))
            day_alerts.extend(alerts_by_trip.get(tid, []))
            day_bills.extend(bills_by_trip.get(tid, []))
            day_feedback.extend(feedback_by_trip.get(tid, []))

        ota = ota_pct(day_trips)
        delay = delay_stats(day_trips)
        no_show = no_show_stats(day_legs)
        cost = cost_stats(day_bills)
        alert = alert_stats(day_alerts, len(day_trips))
        csat = csat_stats(day_feedback)

        all_ota = ota.get("all", {})
        all_delay = delay.get("all", {})
        all_no_show = no_show.get("all", {})
        all_cost = cost.get("all", {})

        max_cost = None
        cost_vals = [b.get("trip_cost") for b in day_bills if b.get("trip_cost") is not None]
        if cost_vals:
            try:
                max_cost = max(cost_vals)
            except TypeError:
                max_cost = None

        daily_rows.append({
            "date": d,
            "trips": len(day_trips),
            "delayed_trips": all_delay.get("late_count"),
            "sev1_count": alert.get("sev1_count"),
            "ota_pct": all_ota.get("ota_pct"),
            "avg_delay_min": all_delay.get("avg_delay_min"),
            "no_show_rate": all_no_show.get("no_show_pct"),
            "cost_per_trip": all_cost.get("cost_per_trip"),
            "alert_rate_per_1k": alert.get("alert_rate_per_1k"),
            "csat_avg": csat.get("csat_avg"),
            "max_trip_cost": max_cost,
            "open_sev1_count": alert.get("open_sev1_count"),
            "unclassified_severity_count": alert.get("unclassified_severity_count"),
        })

    # Vendor KPIs (grouped by vendor + billing cycle)
    vendor_bill_groups = defaultdict(list)
    for bill in bills:
        cycle = _cycle_for_bill(bill)
        vendor = bill.get("vendor")
        if cycle and vendor:
            vendor_bill_groups[(vendor, cycle)].append(bill)

    vendor_rows = []
    for (vendor, cycle), grp_bills in sorted(vendor_bill_groups.items()):
        trip_ids = {b["trip_id"] for b in grp_bills if b.get("trip_id") is not None}
        grp_trips = [trip_by_id[tid] for tid in trip_ids if tid in trip_by_id]
        grp_legs = []
        grp_alerts = []
        grp_feedback = []
        for tid in trip_ids:
            grp_legs.extend(legs_by_trip.get(tid, []))
            grp_alerts.extend(alerts_by_trip.get(tid, []))
            grp_feedback.extend(feedback_by_trip.get(tid, []))

        cost = cost_stats(grp_bills)
        ota = ota_pct(grp_trips)
        delay = delay_stats(grp_trips)
        no_show = no_show_stats(grp_legs)
        alert = alert_stats(grp_alerts, len(grp_trips))
        csat = csat_stats(grp_feedback)

        all_cost = cost.get("all", {})
        all_ota = ota.get("all", {})
        all_delay = delay.get("all", {})
        all_no_show = no_show.get("all", {})

        unslabbed = sum(1 for b in grp_bills if b.get("slab_name") is None)

        vendor_rows.append({
            "vendor": vendor,
            "cycle_or_month": cycle,
            "trips": len(grp_trips),
            "ota_pct": all_ota.get("ota_pct"),
            "cost_per_trip": all_cost.get("cost_per_trip"),
            "cost_per_km": all_cost.get("cost_per_km"),
            "alert_rate_per_1k": alert.get("alert_rate_per_1k"),
            "csat_avg": csat.get("csat_avg"),
            "low_rating_share": csat.get("low_rating_share"),
            "delayed_trips": all_delay.get("late_count"),
            "avg_delay_min": all_delay.get("avg_delay_min"),
            "no_show_rate": all_no_show.get("no_show_pct"),
            "zero_km_count": all_cost.get("zero_km_count"),
            "unslabbed_count": unslabbed,
            "sev1_count": alert.get("sev1_count"),
            "avg_ack_minutes": alert.get("avg_ack_minutes"),
            "ack_sla_met_share": alert.get("ack_sla_met_share"),
            "late_reason_counts": all_delay.get("reason_mix"),
            "open_sev1_count": alert.get("open_sev1_count"),
            "unclassified_severity_count": alert.get("unclassified_severity_count"),
        })

    _vendor_cost_outliers(vendor_rows)

    # Office KPIs (grouped by office + trip cycle)
    trips_by_office_cycle = defaultdict(list)
    for t in trips:
        cycle = _cycle_for_date(t.get("trip_date"))
        office = t.get("office")
        if cycle and office:
            trips_by_office_cycle[(office, cycle)].append(t)

    office_rows = []
    for (office, cycle), grp_trips in sorted(trips_by_office_cycle.items()):
        trip_ids = {t["trip_id"] for t in grp_trips if t.get("trip_id") is not None}
        grp_legs = []
        grp_alerts = []
        grp_bills = []
        grp_feedback = []
        for tid in trip_ids:
            grp_legs.extend(legs_by_trip.get(tid, []))
            grp_alerts.extend(alerts_by_trip.get(tid, []))
            grp_bills.extend(bills_by_trip.get(tid, []))
            grp_feedback.extend(feedback_by_trip.get(tid, []))

        cost = cost_stats(grp_bills)
        ota = ota_pct(grp_trips)
        delay = delay_stats(grp_trips)
        no_show = no_show_stats(grp_legs)
        alert = alert_stats(grp_alerts, len(grp_trips))
        csat = csat_stats(grp_feedback)

        all_cost = cost.get("all", {})
        all_ota = ota.get("all", {})
        all_delay = delay.get("all", {})
        all_no_show = no_show.get("all", {})

        unslabbed = sum(1 for b in grp_bills if b.get("slab_name") is None)

        office_rows.append({
            "office": office,
            "cycle_or_month": cycle,
            "trips": len(grp_trips),
            "ota_pct": all_ota.get("ota_pct"),
            "cost_per_trip": all_cost.get("cost_per_trip"),
            "cost_per_km": all_cost.get("cost_per_km"),
            "alert_rate_per_1k": alert.get("alert_rate_per_1k"),
            "csat_avg": csat.get("csat_avg"),
            "low_rating_share": csat.get("low_rating_share"),
            "delayed_trips": all_delay.get("late_count"),
            "avg_delay_min": all_delay.get("avg_delay_min"),
            "no_show_rate": all_no_show.get("no_show_pct"),
            "zero_km_count": all_cost.get("zero_km_count"),
            "unslabbed_count": unslabbed,
            "sev1_count": alert.get("sev1_count"),
            "avg_ack_minutes": alert.get("avg_ack_minutes"),
            "ack_sla_met_share": alert.get("ack_sla_met_share"),
            "late_reason_counts": all_delay.get("reason_mix"),
            "open_sev1_count": alert.get("open_sev1_count"),
            "unclassified_severity_count": alert.get("unclassified_severity_count"),
        })

    # Shift rows use rider legs as the no-show denominator.
    shift_groups = defaultdict(list)
    for leg in legs:
        shift = leg.get("shift_type")
        cycle = _cycle_for_date(leg.get("trip_date"))
        if shift and cycle:
            shift_groups[(shift, cycle)].append(leg)
    shift_rows = []
    for (shift, cycle), group in sorted(shift_groups.items()):
        stats = no_show_stats(group).get("all", {})
        shift_rows.append({
            "shift_type": shift,
            "cycle_or_month": cycle,
            "legs": stats.get("legs"),
            "no_show_count": stats.get("no_shows"),
            "no_show_rate": stats.get("no_show_pct"),
        })

    await conn.execute(delete(DailyKpi))
    await conn.execute(delete(VendorKpi))
    await conn.execute(delete(OfficeKpi))
    await conn.execute(delete(ShiftKpi))

    if daily_rows:
        await conn.execute(DailyKpi.__table__.insert(), daily_rows)
    if vendor_rows:
        await conn.execute(VendorKpi.__table__.insert(), vendor_rows)
    if office_rows:
        await conn.execute(OfficeKpi.__table__.insert(), office_rows)
    if shift_rows:
        await conn.execute(ShiftKpi.__table__.insert(), shift_rows)

    return {
        "daily_kpi": len(daily_rows),
        "vendor_kpi": len(vendor_rows),
        "office_kpi": len(office_rows),
        "shift_kpi": len(shift_rows),
    }

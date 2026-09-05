"""Precomputed mart tables — schemas land in Story 01, rows in Story 02."""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class DailyKpi(Base):
    __tablename__ = "daily_kpi"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    trips: Mapped[int | None] = mapped_column(Integer)
    delayed_trips: Mapped[int | None] = mapped_column(Integer)
    sev1_count: Mapped[int | None] = mapped_column(Integer)
    ota_pct: Mapped[float | None] = mapped_column(Float)
    avg_delay_min: Mapped[float | None] = mapped_column(Float)
    no_show_rate: Mapped[float | None] = mapped_column(Float)
    cost_per_trip: Mapped[float | None] = mapped_column(Float)
    alert_rate_per_1k: Mapped[float | None] = mapped_column(Float)
    csat_avg: Mapped[float | None] = mapped_column(Float)
    max_trip_cost: Mapped[float | None] = mapped_column(Float)
    open_sev1_count: Mapped[int | None] = mapped_column(Integer)
    unclassified_severity_count: Mapped[int | None] = mapped_column(Integer)


class VendorKpi(Base):
    __tablename__ = "vendor_kpi"

    vendor: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_or_month: Mapped[str] = mapped_column(String(32), primary_key=True)
    trips: Mapped[int | None] = mapped_column(Integer)
    ota_pct: Mapped[float | None] = mapped_column(Float)
    cost_per_trip: Mapped[float | None] = mapped_column(Float)
    cost_per_km: Mapped[float | None] = mapped_column(Float)
    alert_rate_per_1k: Mapped[float | None] = mapped_column(Float)
    csat_avg: Mapped[float | None] = mapped_column(Float)
    low_rating_share: Mapped[float | None] = mapped_column(Float)
    delayed_trips: Mapped[int | None] = mapped_column(Integer)
    avg_delay_min: Mapped[float | None] = mapped_column(Float)
    no_show_rate: Mapped[float | None] = mapped_column(Float)
    zero_km_count: Mapped[int | None] = mapped_column(Integer)
    unslabbed_count: Mapped[int | None] = mapped_column(Integer)
    sev1_count: Mapped[int | None] = mapped_column(Integer)
    avg_ack_minutes: Mapped[float | None] = mapped_column(Float)
    ack_sla_met_share: Mapped[float | None] = mapped_column(Float)
    late_reason_counts: Mapped[dict | None] = mapped_column(JSON)
    open_sev1_count: Mapped[int | None] = mapped_column(Integer)
    unclassified_severity_count: Mapped[int | None] = mapped_column(Integer)
    cost_outlier: Mapped[bool | None] = mapped_column(Boolean)


class OfficeKpi(Base):
    __tablename__ = "office_kpi"

    office: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_or_month: Mapped[str] = mapped_column(String(32), primary_key=True)
    trips: Mapped[int | None] = mapped_column(Integer)
    ota_pct: Mapped[float | None] = mapped_column(Float)
    cost_per_trip: Mapped[float | None] = mapped_column(Float)
    cost_per_km: Mapped[float | None] = mapped_column(Float)
    alert_rate_per_1k: Mapped[float | None] = mapped_column(Float)
    csat_avg: Mapped[float | None] = mapped_column(Float)
    low_rating_share: Mapped[float | None] = mapped_column(Float)
    delayed_trips: Mapped[int | None] = mapped_column(Integer)
    avg_delay_min: Mapped[float | None] = mapped_column(Float)
    no_show_rate: Mapped[float | None] = mapped_column(Float)
    zero_km_count: Mapped[int | None] = mapped_column(Integer)
    unslabbed_count: Mapped[int | None] = mapped_column(Integer)
    sev1_count: Mapped[int | None] = mapped_column(Integer)
    avg_ack_minutes: Mapped[float | None] = mapped_column(Float)
    ack_sla_met_share: Mapped[float | None] = mapped_column(Float)
    late_reason_counts: Mapped[dict | None] = mapped_column(JSON)
    open_sev1_count: Mapped[int | None] = mapped_column(Integer)
    unclassified_severity_count: Mapped[int | None] = mapped_column(Integer)


class ShiftKpi(Base):
    __tablename__ = "shift_kpi"

    shift_type: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_or_month: Mapped[str] = mapped_column(String(32), primary_key=True)
    legs: Mapped[int | None] = mapped_column(Integer)
    no_show_count: Mapped[int | None] = mapped_column(Integer)
    no_show_rate: Mapped[float | None] = mapped_column(Float)


class InsightCache(Base):
    __tablename__ = "insight_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime)

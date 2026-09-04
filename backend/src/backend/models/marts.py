"""Precomputed mart tables — schemas land in Story 01, rows in Story 02."""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String
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


class InsightCache(Base):
    __tablename__ = "insight_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime)

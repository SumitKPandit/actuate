"""Raw ops tables: trips, legs, bills, alerts, feedback (Story 01)."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_unit: Mapped[str | None] = mapped_column(String)
    office: Mapped[str | None] = mapped_column(String)
    product_type: Mapped[str | None] = mapped_column(String)
    trip_date: Mapped[date | None] = mapped_column(Date)
    shift_type: Mapped[str | None] = mapped_column(String)
    trip_id: Mapped[int] = mapped_column(BigInteger, index=True)
    trip_direction: Mapped[str | None] = mapped_column(String)
    actual_escort: Mapped[bool | None] = mapped_column(Boolean)
    vendor_id: Mapped[str | None] = mapped_column(String)
    planned_cab_registration: Mapped[str | None] = mapped_column(String)
    actual_cab_registration: Mapped[str | None] = mapped_column(String)
    actual_cab_capacity: Mapped[int | None] = mapped_column(Integer)
    planned_km: Mapped[float | None] = mapped_column(Float)
    traveled_km: Mapped[float | None] = mapped_column(Float)
    planned_start_epoch: Mapped[float | None] = mapped_column(Float)
    planned_end_epoch: Mapped[float | None] = mapped_column(Float)
    actual_start_epoch: Mapped[float | None] = mapped_column(Float)
    actual_end_epoch: Mapped[float | None] = mapped_column(Float)
    delay_reason: Mapped[str | None] = mapped_column(String)
    delay_minutes: Mapped[float | None] = mapped_column(Float)
    route_source: Mapped[str | None] = mapped_column(String)
    actual_cab_fuel_type: Mapped[str | None] = mapped_column(String)
    is_driver_nc: Mapped[bool | None] = mapped_column(Boolean)
    is_cab_nc: Mapped[bool | None] = mapped_column(Boolean)
    trip_nodal: Mapped[str | None] = mapped_column(String)
    plannedemployee_cnt: Mapped[int | None] = mapped_column(Integer)
    actualemployee_cnt: Mapped[int | None] = mapped_column(Integer)
    noshow_cnt: Mapped[int | None] = mapped_column(Integer)


class Leg(Base):
    __tablename__ = "legs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_unit: Mapped[str | None] = mapped_column(String)
    office: Mapped[str | None] = mapped_column(String)
    product_type: Mapped[str | None] = mapped_column(String)
    trip_date: Mapped[date | None] = mapped_column(Date)
    shift_type: Mapped[str | None] = mapped_column(String)
    trip_id: Mapped[int] = mapped_column(BigInteger, index=True)
    planned_pickup_epoch: Mapped[float | None] = mapped_column(Float)
    planned_drop_epoch: Mapped[float | None] = mapped_column(Float)
    actual_pickup_epoch: Mapped[float | None] = mapped_column(Float)
    actual_drop_epoch: Mapped[float | None] = mapped_column(Float)
    planned_km: Mapped[float | None] = mapped_column(Float)
    traveled_km: Mapped[float | None] = mapped_column(Float)
    stwid: Mapped[int | None] = mapped_column(BigInteger, index=True)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    dq_flag: Mapped[str | None] = mapped_column(String)
    signintype: Mapped[str | None] = mapped_column(String)
    gender: Mapped[str | None] = mapped_column(String)
    emp_role: Mapped[str | None] = mapped_column(String)
    boarding_status: Mapped[str | None] = mapped_column(String)
    not_boarding_reason: Mapped[str | None] = mapped_column(String)
    is_no_show: Mapped[bool | None] = mapped_column(Boolean)


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_unit: Mapped[str | None] = mapped_column(String)
    office: Mapped[str | None] = mapped_column(String)
    vendor: Mapped[str | None] = mapped_column(String)
    cycle_start: Mapped[datetime | None] = mapped_column(DateTime)
    cycle_end: Mapped[datetime | None] = mapped_column(DateTime)
    trip_id: Mapped[int] = mapped_column(BigInteger, index=True)
    contract: Mapped[str | None] = mapped_column(String)
    slab_name: Mapped[str | None] = mapped_column(String)
    total_trip_km: Mapped[float | None] = mapped_column(Float)
    is_zero_km: Mapped[bool] = mapped_column(Boolean, default=False)
    trip_cost: Mapped[float | None] = mapped_column(Float)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_unit: Mapped[str | None] = mapped_column(String)
    trip_id: Mapped[int] = mapped_column(BigInteger, index=True)
    stwid: Mapped[int | None] = mapped_column(BigInteger, index=True)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    event_id: Mapped[str | None] = mapped_column(String, index=True)
    event_type: Mapped[str | None] = mapped_column(String)
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    acknowledge_time: Mapped[datetime | None] = mapped_column(DateTime)
    state_text: Mapped[str | None] = mapped_column(String)
    severity: Mapped[str | None] = mapped_column(String)
    severity_raw: Mapped[str | None] = mapped_column(String)
    dq_flag: Mapped[str | None] = mapped_column(String)
    source: Mapped[str | None] = mapped_column(String)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_unit: Mapped[str | None] = mapped_column(String)
    trip_id: Mapped[int] = mapped_column(BigInteger, index=True)
    trip_type: Mapped[str | None] = mapped_column(String)
    trip_date: Mapped[date | None] = mapped_column(Date)
    stwid: Mapped[int | None] = mapped_column(BigInteger, index=True)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    route_rating: Mapped[int | None] = mapped_column(SmallInteger)
    driver_rating: Mapped[int | None] = mapped_column(SmallInteger)
    cab_rating: Mapped[int | None] = mapped_column(SmallInteger)
    safety_rating: Mapped[int | None] = mapped_column(SmallInteger)
    marshal_rating: Mapped[int | None] = mapped_column(SmallInteger)
    creation_time: Mapped[datetime | None] = mapped_column(DateTime)

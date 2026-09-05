"""ORM models. Define domain tables here and import them so `Base.metadata` picks them up."""

from backend.core.database import Base
from backend.models.example import Example
from backend.models.marts import DailyKpi, InsightCache, OfficeKpi, ShiftKpi, VendorKpi
from backend.models.ops import Alert, Bill, Feedback, Leg, Trip

__all__ = [
    "Alert",
    "Base",
    "Bill",
    "DailyKpi",
    "Example",
    "Feedback",
    "InsightCache",
    "Leg",
    "OfficeKpi",
    "ShiftKpi",
    "Trip",
    "VendorKpi",
]

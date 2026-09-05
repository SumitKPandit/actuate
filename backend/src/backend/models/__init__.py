"""ORM models. Define domain tables here and import them so `Base.metadata` picks them up."""

from backend.core.database import Base
from backend.models.example import Example
from backend.models.marts import DailyKpi, InsightCache, OfficeKpi, VendorKpi
from backend.models.ops import Alert, Bill, Feedback, Leg, Trip
from backend.models.vector import KnowledgeChunk

__all__ = [
    "Alert",
    "Base",
    "Bill",
    "DailyKpi",
    "Example",
    "Feedback",
    "InsightCache",
    "KnowledgeChunk",
    "Leg",
    "OfficeKpi",
    "Trip",
    "VendorKpi",
]

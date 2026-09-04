"""ORM models. Define domain tables here and import them so `Base.metadata` picks them up."""

from backend.core.database import Base
from backend.models.example import Example

__all__ = ["Base", "Example"]

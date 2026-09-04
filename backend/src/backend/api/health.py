"""Liveness / readiness probes and version info."""

from fastapi import APIRouter

from backend.core.config import settings
from backend.core.database import check_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/ready")
async def ready() -> dict[str, object]:
    db_ok = await check_db()
    return {
        "ready": db_ok,
        "database": "connected" if db_ok else "disconnected",
    }


@router.get("/live")
def live() -> dict[str, bool]:
    return {"alive": True}

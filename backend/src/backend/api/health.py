"""Liveness / readiness probes and version info."""

from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/ready")
def ready() -> dict[str, bool]:
    # Extend later with DB / dataset / model checks.
    return {"ready": True}


@router.get("/live")
def live() -> dict[str, bool]:
    return {"alive": True}

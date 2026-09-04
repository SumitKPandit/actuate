"""Health + readiness probes."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.core import database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
async def readiness():
    """Return 200 only when a DB round-trip succeeds."""
    try:
        await database.ping_db()
    except Exception:  # noqa: BLE001 - probe must map any DB failure to 503
        return JSONResponse(status_code=503, content={"status": "down", "db": "down"})
    return {"status": "ok", "db": "up"}

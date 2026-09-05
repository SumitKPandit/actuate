"""Read-only endpoints over the cached MoveInSync trip-feedback dataset."""

from fastapi import APIRouter, HTTPException

from backend.services import moveinsync_data as dset

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.get("/info")
def dataset_info() -> dict:
    """Dataset shape, columns, missing-value and duplicate counts."""
    return dset.get_dataset_info()


@router.get("/sample")
def dataset_sample(limit: int = 5) -> dict:
    """Return a small slice of actual dataset rows (JSON-safe)."""
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200")
    return {"dataset": dset.DSET_NAME, "limit": limit, "rows": dset.sample_rows(limit)}
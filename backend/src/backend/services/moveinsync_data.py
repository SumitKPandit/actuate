"""Cached MoveInSync trip-feedback dataset service.

Loads ``backend/data/moveinsync/trip_feedback_clean.csv`` once per process so the
45 MB CSV is never re-read on every request. The service validates that the file
exists, handles missing values safely, and inspects the *actual* columns at
runtime instead of assuming fields that may not be present. Any requested field
that the current schema does not contain is reported as ``"not_available"``.
"""

from __future__ import annotations

import math
import threading
from pathlib import Path

import numpy as np
import pandas as pd

DSET_NAME = "trip_feedback_clean.csv"
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
DSET_PATH = _BACKEND_ROOT / "data" / "moveinsync" / DSET_NAME

# Process-wide cache: the CSV is parsed exactly once and shared by all requests.
_df: pd.DataFrame | None = None
_lock = threading.Lock()


def _require_dataset() -> None:
    """Raise a clear error when the dataset file is missing."""
    if not DSET_PATH.is_file():
        raise FileNotFoundError(f"MoveInSync dataset not found: {DSET_PATH}")


def get_dataframe() -> pd.DataFrame:
    """Return the dataset, loading and caching the CSV on first call."""
    global _df
    _require_dataset()
    if _df is None:
        with _lock:
            if _df is None:
                _df = pd.read_csv(DSET_PATH)
    return _df


def _columns_with(df: pd.DataFrame, *tokens: str) -> list[str]:
    """Return real columns whose lower-cased name contains any token."""
    lowered = {col: str(col).lower() for col in df.columns}
    return [col for col, low in lowered.items() if any(tok in low for tok in tokens)]


def _missing_counts(df: pd.DataFrame) -> dict[str, int]:
    return {str(col): int(df[col].isna().sum()) for col in df.columns}


def _r2(value: object) -> float | None:
    """Safe 2-decimal rounding; NaN/None/NaN-like → None."""
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return round(f, 2)


def _num_stats(series: pd.Series) -> dict:
    valid = series.dropna()
    stats = {
        "count": int(len(valid)),
        "mean": None,
        "median": None,
        "min": None,
        "max": None,
        "missing": int(series.isna().sum()),
    }
    if len(valid) == 0:
        return stats
    stats["mean"] = _r2(valid.mean())
    stats["median"] = _r2(valid.median())
    stats["min"] = _r2(valid.min())
    stats["max"] = _r2(valid.max())
    return stats


def _value_distribution(series: pd.Series, limit: int = 20) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, count in series.value_counts(dropna=False).head(limit).items():
        label = "<missing>" if pd.isna(key) else str(key)
        out[label] = int(count)
    return out


def _json_safe(value: object) -> object:
    """Convert pandas/numpy scalars to plain JSON-compatible Python objects."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.floating):
        f = float(value)
        return None if not math.isfinite(f) else f
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)
def get_dataset_info() -> dict:
    """Shape, columns, missing-value counts and duplicate count of the CSV."""
    df = get_dataframe()
    return {
        "dataset": DSET_NAME,
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "column_names": [str(col) for col in df.columns],
        "missing_values": _missing_counts(df),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def get_trip_feedback_summary() -> dict:
    """Schema-driven trip-feedback aggregates (no invented dimensions)."""
    df = get_dataframe()
    summary: dict = {
        "dataset": DSET_NAME,
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values": _missing_counts(df),
    }
    if "trip_id" in df.columns:
        summary["unique_trip_ids"] = int(df["trip_id"].nunique(dropna=True))
    if "stwid" in df.columns:
        summary["unique_employees"] = int(df["stwid"].nunique(dropna=True))
    for group in ("business_unit", "trip_type", "trip_date"):
        if group in df.columns:
            summary[f"{group}_distribution"] = _value_distribution(df[group])
    rating_cols = _columns_with(df, "rating")
    if rating_cols:
        summary["ratings"] = {col: _num_stats(df[col]) for col in rating_cols}
    for field in ("ota_pct", "average_delay_min", "trip_cost", "delay_reason", "vendor"):
        if field not in df.columns:
            summary[field] = "not_available"
    return summary


def get_vendor_metrics() -> dict:
    """Vendor metrics only when a vendor-ish column really exists."""
    df = get_dataframe()
    tokens = ("vendor", "supplier", "provider", "partner", "fleet", "cab_name")
    vendor_cols = _columns_with(df, *tokens)
    if not vendor_cols:
        return {
            "status": "not_available",
            "reason": "No vendor/supplier/provider column exists in the dataset.",
            "columns_inspected": [str(col) for col in df.columns],
        }
    grouping = vendor_cols[0]
    metrics: dict = {"status": "available", "grouped_by": grouping}
    for key, group in df.groupby(grouping, dropna=False):
        label = "<missing>" if pd.isna(key) else str(key)
        row: dict = {"rows": int(len(group))}
        for rating in _columns_with(group, "rating"):
            row[rating] = _r2(group[rating].mean()) if group[rating].notna().any() else None
        metrics[label] = row
    return metrics


def get_route_metrics() -> dict:
    """Route metrics computed only from route-related columns that exist."""
    df = get_dataframe()
    route_cols = _columns_with(df, "route")
    if not route_cols:
        return {
            "status": "not_available",
            "reason": "No route column (route_id, route_name, route_rating) exists.",
            "columns_inspected": [str(col) for col in df.columns],
        }
    metrics: dict = {"status": "available", "route_columns": route_cols}
    for identifier in ("route_id", "route_name", "origin", "destination"):
        if identifier not in df.columns:
            metrics[identifier] = "not_available"
    rating_col = "route_rating" if "route_rating" in df.columns else route_cols[0]
    if pd.api.types.is_numeric_dtype(df[rating_col]):
        metrics["route_rating"] = _num_stats(df[rating_col])
        metrics["route_rating_distribution"] = _value_distribution(df[rating_col])
    if "business_unit" in df.columns:
        by_unit: dict[str, dict] = {}
        for unit, group in df.groupby("business_unit", dropna=False):
            label = "<missing>" if pd.isna(unit) else str(unit)
            by_unit[label] = {
                "rows": int(len(group)),
                "avg_route_rating": (
                    _r2(group[rating_col].mean()) if group[rating_col].notna().any() else None
                ),
            }
        metrics["by_business_unit"] = by_unit
    return metrics


def sample_rows(n: int = 5) -> list[dict]:
    """Return the first ``n`` actual rows as JSON-safe dicts."""
    df = get_dataframe()
    take = max(1, min(int(n), int(len(df))))
    head = df.head(take)
    records = head.where(pd.notna(head), None).to_dict(orient="records")
    return [{str(key): _json_safe(value) for key, value in row.items()} for row in records]
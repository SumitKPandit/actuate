"""Numeric anomaly detection with an explicit small-sample fallback."""

from __future__ import annotations

import math
from collections.abc import Iterable


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def detect_daily_anomalies(rows: Iterable[object]) -> list[dict]:
    """Return anomalous daily KPI records without making ML a startup dependency.

    IsolationForest needs enough comparable observations to be meaningful.  For
    fewer than five complete rows, use a transparent OTA/SLA and cost threshold
    rather than pretending a model was trained.
    """
    records = []
    for row in rows:
        delay = _number(getattr(row, "avg_delay_min", None))
        cost = _number(getattr(row, "cost_per_trip", None))
        ota = _number(getattr(row, "ota_pct", None))
        csat = _number(getattr(row, "csat_avg", None))
        if None not in (delay, cost, ota, csat):
            records.append((row, [delay, cost, ota, csat]))

    if len(records) < 5:
        return [
            {
                "date": str(getattr(row, "date", "")),
                "method": "threshold_fallback",
                "reason": "OTA below 95% SLA" if features[2] < 95 else "cost per trip exceeds 150% of sample median",
            }
            for row, features in records
            if features[2] < 95
            or features[1] > 1.5 * sorted(item[1][1] for item in records)[len(records) // 2]
        ]

    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return []

    model = IsolationForest(contamination="auto", random_state=42)
    labels = model.fit_predict([features for _, features in records])
    return [
        {
            "date": str(getattr(row, "date", "")),
            "method": "isolation_forest",
            "reason": "multivariate daily KPI outlier",
        }
        for (row, _), label in zip(records, labels, strict=True)
        if label == -1
    ]

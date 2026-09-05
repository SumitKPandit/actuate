# Story 05 — Mart Population (raw tables → marts)

**Status:** ready for implementation. **Depends on:** 01 (raw tables + mart schemas), 02 (analytics functions), 04 (ops API reads marts).

## 1. Goal

The ops API endpoints return `{"data": null, "warning": "marts empty — run ingest"}` because `ingest.py` creates mart schemas but writes zero rows. This story fills and refreshes `daily_kpi`, `vendor_kpi`, and `office_kpi` from raw tables whenever new data appears in the DB (i.e. after every `ingest.py` run).

## 2. Scope

**In:**
- `backend/src/backend/core/marts.py`: `populate_marts(conn, business_unit=None)` — reads raw tables, computes KPIs via existing `analytics.py`, writes mart rows.
- `backend/scripts/ingest.py`: call `populate_marts` after each raw table load (inside the same transaction).
- `backend/tests/test_mart_populate.py`: tests for daily/vendor/office aggregation, idempotency, and empty-input safety.

**Out:** incremental/CDC refresh (deferred — full rebuild on each ingest is the MVP contract), trigger evaluation (Story 08).

## 3. Functional requirements

1. **Idempotent full rebuild:** each `populate_marts` call DELETEs all rows from `daily_kpi`, `vendor_kpi`, `office_kpi` and reinserts fresh aggregates. Rerunning `ingest.py` produces identical mart counts.
2. **Reuses `analytics.py`:** OTA, delay, no-show, cost, alert, and CSAT functions are called exactly as Story 02 defined them — no new math.
3. **Cycle derivation:** vendor/office marts use semi-monthly cycle labels (`YYYY-MM-H1` / `YYYY-MM-H2`) derived from:
   - `bills.cycle_start` date (1st–15th → H1, 16th–end → H2) for vendor grain.
   - `trips.trip_date` date for office grain.
4. **Daily grain:** one `daily_kpi` row per distinct `trip_date` in `trips`.
5. **Vendor grain:** one `vendor_kpi` row per `(vendor, cycle)` found in `bills`.
6. **Office grain:** one `office_kpi` row per `(office, cycle)` found in `trips`.
7. **Null-safe:** days/vendors/offices with no matching raw rows produce no mart row (not a row of NULLs).
8. **Works on both backends:** uses SQLAlchemy async Core (no dialect-specific SQL), so SQLite and Postgres are both supported.

## 4. Acceptance criteria

- [ ] After `python -m backend.scripts.ingest --data ...`, `SELECT COUNT(*) FROM daily_kpi` returns > 0 and matches distinct trip dates in raw data.
- [ ] `vendor_kpi` and `office_kpi` rows exist with non-NULL KPIs for cycles present in the dataset.
- [ ] Rerunning ingest produces the same mart counts (idempotent).
- [ ] Ops API endpoints (`/overview`, `/insights`, `/briefing`, `/vendors`, `/actions`) return real data instead of the empty-marts warning.
- [ ] `ruff` clean, `uv run pytest backend/tests/test_mart_populate.py` green.

## 5. Test plan (test-first)

`backend/tests/test_mart_populate.py`:

- `test_daily_kpi_populated`: tiny fixture with 2 dates → 2 daily rows, correct trip counts and OTA.
- `test_vendor_kpi_populated`: 2 vendors across 2 cycles → 4 vendor rows, cost and OTA match analytics output.
- `test_office_kpi_populated`: 2 offices across 2 cycles → correct office aggregates.
- `test_idempotent_rebuild`: run populate_marts twice → same counts.
- `test_ops_api_returns_data_after_marts`: end-to-end — ingest + API call returns non-null data.

## 6. Files to touch

- New: `backend/src/backend/core/marts.py`, `backend/tests/test_mart_populate.py`, `stories/05-mart-populate/SPEC.md`.
- Edit: `backend/src/backend/scripts/ingest.py` (call `populate_marts` after raw load).

## 7. Notes

- The mart writer lives in `core/` (not `scripts/`) so it is importable by tests and future schedulers.
- `populate_marts` takes an `AsyncConnection` (not `AsyncSession`) because it does bulk INSERT via `conn.execute(table.insert(), [...])` matching the existing ingest pattern.
- For very large datasets, row-by-row Python grouping may be slow; if needed, optimize later with SQL CTEs. MVP correctness first.

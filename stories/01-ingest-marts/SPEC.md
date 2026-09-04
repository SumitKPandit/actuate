# Story 01 — Ingest + Normalization + Marts (Sense foundation)

**Status:** complete (verified 2026-09-05: SQLite full load, PG alerts subset + idempotent rerun). **Depends on:** nothing but repo scaffolding.

## 1. Goal

Transport manager sees numbers they can trust. All 5 CSV families land in one database with join keys normalized, messy values flagged (not silently dropped), and precomputed marts so every later story reads marts — never raw CSVs at request time.

## 2. Scope

**In:**
- `backend/scripts/ingest.py` (new): CSVs → DB → marts. Idempotent rerun (truncate + reload or upsert on natural key; document choice).
- 5 raw tables via SQLAlchemy models subclassing `backend.core.database.Base`:
  - `trips` ← `Ride_data _trip-may_2026.csv` + June + July (615,546 rows expected)
  - `legs` ← `emp_Data.csv` (1,637,906 rows, grain = employee-leg)
  - `bills` ← `bill_data.csv` (620,942 rows)
  - `alerts` ← `alerts_data.csv` (51,699 rows)
  - `feedback` ← `trip_feedback.csv` (512,873 rows)
- 4 mart tables: `daily_kpi`, `vendor_kpi`, `office_kpi`, `insight_cache` (empty-cache rows allowed; computation lands in Story 02/03, schema lands here).
- Normalization per `PLAN.md §6` + `problem-statement/dataset/dictionary/README.md` quirks list.

**Out:** KPI math (Story 02), ranking (Story 03), APIs (Story 04), any LLM use.

## 3. Functional requirements

1. **Join key normalization (must):** `trip_id`: strip commas → `BIGINT` on every table (`bill_data` already plain digits; others comma-formatted; `emp_data` already int). `stwid`: strip commas → `BIGINT`; `0`/`"0"` preserved but flagged `is_placeholder=true`, excluded from rider stats downstream.
2. **Date parsing per file:** `ride_data_trip`: `"May 1, 2026"` → date; `emp_data`: ISO `YYYY-MM-DD`; `trip_feedback`: `"June 3, 2026, 11:00 AM"`; `alerts_data`/`bill_data`: `"May 1, 2026, 12:03 AM"` timestamps. One parser per file, unparseable → NULL + counted in load report.
3. **Numerics:** `delay_minutes`, `trip_cost`, `*_epoch` in trip files: strip commas → numeric. `planned_km` dtype drift (float May/Jun, object Jul with one comma value) reconciled to float.
4. **Invalid-but-expected values → NULL + flag, never drop row:**
   - `alerts.severity = "False"` → NULL + `severity_raw='False'`, `dq_flag='severity_false'`; other NULLs kept as `"unclassified"`.
   - `legs.planned_km / traveled_km < 0` → NULL + `dq_flag='negative_km'`.
   - `feedback` rating `0` kept as-is (Story 02 excludes 0s from averages); `marshal_rating = 0` → treated as unrated downstream, stored raw.
   - `bills.total_trip_km = 0` kept + `is_zero_km=true`; `slab_name` NULL kept as explicit `'UNSLABBED'` category downstream with counts.
   - `is_driver_nc / is_cab_nc` May nulls (4 rows) preserved as NULL (bool-nullable).
5. **Marts schemas (minimal, extensible):**
   - `daily_kpi(date, trips, delayed_trips, ota_pct, avg_delay_min, no_show_rate, cost_per_trip, alert_rate_per_1k, sev1_count, csat_avg)`
   - `vendor_kpi(vendor, cycle_or_month, trips, ota_pct, cost_per_trip, cost_per_km, alert_rate_per_1k, csat_avg, low_rating_share)`
   - `office_kpi(office, cycle_or_month, ...same as vendor...)`
   - `insight_cache(key, payload_json, computed_at)` — key e.g. `briefing:latest`.
6. **Load report:** script prints counts loaded, rows flagged per rule, date min/max per table; exit non-zero on schema mismatch.
7. **Works on both backends:** SQLite locally (`sqlite+aiosqlite:///./actuate.db`), Postgres in compose (`postgresql+asyncpg://...`). No raw SQL that breaks either (or branch by dialect explicitly).

## 4. Acceptance criteria

- [x] Fresh `actuate.db` / fresh Postgres volume → `python -m backend.scripts.ingest --data problem-statement/dataset/data` loads all 5 tables with row counts matching §2 (±0.5% with reason logged).
- [x] Spot join works: `SELECT COUNT(*) FROM alerts a JOIN trips t ON a.trip_id = t.trip_id` returns > 0 (no comma-mismatch); same for bills→trips, feedback→trips, legs→trips.
- [x] `SELECT COUNT(*) FROM alerts WHERE severity IS NULL` ≈ 16k + 15k `"False"`-as-null (≈31k unclassified incl. flag); `SELECT COUNT(*) FROM bills WHERE is_zero_km` > 0; negative-km legs flagged not dropped.
- [x] Rerun is idempotent (row counts unchanged, no duplicates).
- [x] `daily_kpi / vendor_kpi / office_kpi` tables exist with columns in §3.5 (rows may be stub until Story 02 fills them — schema + load path must exist).

## 5. Test plan (test-first, per AGENTS.md)

`backend/tests/test_ingest_*.py` with small inline CSV fixtures (do not commit full dataset):
- `test_trip_id_normalization`: comma `"1,097,076"` + plain `"1123974"` + int `1123974` → all join to `1123974`.
- `test_stwid_zero_placeholder`: `0`/`"0"` flagged placeholder, excluded by `is_real_rider` helper.
- `test_date_formats`: one sample per file format parses to expected date.
- `test_severity_false_to_null`: `"False"` → NULL + flag; null count preserved.
- `test_negative_km_to_null`: `-2.0`/`-6.63` → NULL + flag, row kept.
- `test_zero_km_and_null_slab_kept`: `0.0` km + NULL slab kept with flags.
- `test_idempotent_reload`: ingest twice → same counts.
- Confirm red before implementing, then green via `uv run pytest`.

## 6. Files to touch

- New: `backend/scripts/ingest.py`, `backend/src/backend/models/trips.py` (or one `models/ops.py`), `backend/src/backend/models/marts.py`, `backend/tests/test_ingest_*.py`.
- Untouched: `api/health.py`, `api/examples.py`, `core/config.py`, `core/database.py` (reuse `Base`/`init_db`).
- Docs: update `backend/README.md` with ingest command + env note.

## 7. Notes / evidence

- Expected volumes in `PLAN.md §2`; column quirks in `problem-statement/dataset/dictionary/*.md`; Business units fixed to 5 (`vanta-Aus`, `catalyst-Sac`, `orbit-Slc`, `vanta-Sea`, `pinnacle-Slc`).
- Billing cycles: 6 semi-monthly (`cycle_start`/`cycle_end` in `bill_data.md`) — store raw, aggregate by cycle in Story 02.

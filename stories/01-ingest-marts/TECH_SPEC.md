# Story 01 — Technical Spec: Ingest + Normalization + Marts

Companion to `SPEC.md`. This file is the build blueprint: schemas, normalization
rules, module design, and test plan. Derived from `PLAN.md`, `stories/README.md`,
the dataset dictionaries, raw CSV sampling, and the backend scaffold.

## 1. Evidence summary

- Volumes (data rows, header excluded): trips 188,992 + 210,669 + 215,885 =
  615,546; legs 1,637,906; bills 620,942; alerts 51,699; feedback 512,873.
  Matches `SPEC.md` §2 exactly.
- `trip_id`: comma-formatted strings in trips/alerts/feedback, plain digit
  strings in bills, `int64` in legs. `stwid`: comma-formatted in feedback
  (509k of 513k), mixed in alerts (29k comma / 22k plain incl. `0`), int in legs.
- **Missing values are encoded per file, not as uniform NULLs** (verified by
  sampling raw CSVs):
  - `alerts_data.csv`: literal `NA` = missing (`severity` 16,348; `source`
    39,350); literal `False` in `severity` (15,037). No empty strings.
  - `bill_data.csv`: literal `null` (121,111) **and** `NA` (3,801) in
    `slab_name`.
  - `Ride_data _trip-*.csv`: literal `NA` in `trip_nodal` (106,536 = non-nodal,
    expected); **empty string** in `is_driver_nc`/`is_cab_nc` (4 rows, May
    only); booleans are lowercase `true`/`false`.
  - `emp_Data.csv`: **empty strings** for `not_boarding_reason`, `signintype`,
    epoch nulls.
- Negative leg distances exist (48 rows). `bills.total_trip_km = 0` is common
  (248,191 rows). Feedback `route_rating = 0` is rare (~2/200k) — kept as-is.
  July `planned_km` parses clean after comma-strip.
- Backend: no `pandas` dependency (`backend/pyproject.toml`); package layout is
  `backend/src/backend/` with `pytest` `pythonpath = ["src"]`. DB wiring
  (`build_engine`, `Base`, `init_db`) already handles SQLite/Postgres branching
  in `backend/src/backend/core/database.py`.

## 2. Design decisions

1. **Idempotency = DELETE + reload**, documented in the script docstring. No
   `TRUNCATE` (not SQLite-compatible), no upsert (would need unique keys on
   messy data). Rerun yields identical counts.
2. **Surrogate autoincrement `id` PK on all 5 raw tables**; plain indexes on
   `trip_id` everywhere (+ `stwid`, date cols). **No FKs, no UNIQUEs** — joins
   are logical, insert order is irrelevant, and messy input can never hard-fail
   the load. Cross-month `trip_id` uniqueness is assumed, not enforced; the
   load report logs distinct counts as a check.
3. **No new dependencies.** Ingest uses stdlib `csv` (`utf-8-sig`) + SQLAlchemy
   Core `insert()` in ~10k-row chunks, one transaction per file.
4. **Script lives at `backend/src/backend/scripts/ingest.py`** (package with
   `__init__.py`) so `python -m backend.scripts.ingest` resolves under
   `PYTHONPATH=src`, consistent with the `src/` layout and pytest config.
   Run from `backend/`: `PYTHONPATH=src uv run python -m
   backend.scripts.ingest --data ../problem-statement/dataset/data`.
   (`SPEC.md` §6's `backend/scripts/ingest.py` is interpreted as repo-relative
   shorthand for this module.)
5. **Pure parsing helpers in `backend/src/backend/core/normalize.py`** —
   unit-testable without a DB. Models stay dumb; the script orchestrates.
6. **Flag, never drop.** Raw offending values preserved next to flags
   (details in §4).
7. **Marts created empty** via existing `init_db()`; Story 02 fills rows.
8. **Exit non-zero only on schema mismatch** (missing file/column). Count
   deviation beyond ±0.5% is a logged warning with reason, not a failure.

## 3. Schemas

Column names stay verbatim from the CSVs (e.g. `plannedemployee_cnt`).

### 3.1 `trips` ← 3 `Ride_data _trip-*.csv` files, concatenated

`id` PK; `business_unit`, `office`, `product_type` String; `trip_date` Date;
`shift_type` String; `trip_id` BIGINT indexed; `trip_direction` String;
`actual_escort` Boolean nullable; `vendor_id` String;
`planned_cab_registration`, `actual_cab_registration` String nullable;
`actual_cab_capacity` Integer; `planned_km`, `traveled_km` Float nullable;
`planned_start_epoch`, `planned_end_epoch`, `actual_start_epoch`,
`actual_end_epoch` Float nullable; `delay_reason` String;
`delay_minutes` Float nullable; `route_source`, `actual_cab_fuel_type` String;
`is_driver_nc`, `is_cab_nc` Boolean nullable; `trip_nodal` String nullable;
`plannedemployee_cnt`, `actualemployee_cnt`, `noshow_cnt` Integer.

### 3.2 `legs` ← `emp_Data.csv`

`id` PK; `business_unit`, `office`, `product_type` String; `trip_date` Date;
`shift_type` String; `trip_id` BIGINT indexed; `planned_pickup_epoch`,
`planned_drop_epoch`, `actual_pickup_epoch`, `actual_drop_epoch` Float
nullable; `planned_km`, `traveled_km` Float nullable; `stwid` BIGINT indexed +
`is_placeholder` Boolean (true iff `stwid == 0`); `dq_flag` String nullable
(`'negative_km'` when either km < 0 → value set NULL, row kept); `signintype`,
`gender`, `emp_role` String nullable; `boarding_status` String;
`not_boarding_reason` String nullable; `is_no_show` Boolean.

### 3.3 `bills` ← `bill_data.csv`

`id` PK; `business_unit`, `office`, `vendor` String; `cycle_start`,
`cycle_end` DateTime nullable (raw cycle strings stored parsed; aggregation by
cycle is Story 02); `trip_id` BIGINT indexed; `contract`, `slab_name` String
nullable; `total_trip_km` Float; `is_zero_km` Boolean (true iff km == 0);
`trip_cost` Float nullable (comma-stripped before cast).

### 3.4 `alerts` ← `alerts_data.csv`

`id` PK; `business_unit` String; `trip_id` BIGINT indexed; `stwid` BIGINT
indexed + `is_placeholder` Boolean; `event_id` String indexed (UUID, unique in
practice — plain index, deliberately not UNIQUE so messy input can't fail the
load); `event_type` String; `start_time`, `acknowledge_time` DateTime nullable;
`state_text` String; `severity` String nullable + `severity_raw` String nullable
+ `dq_flag` String nullable (see rule 9); `source` String nullable.

### 3.5 `feedback` ← `trip_feedback.csv`

`id` PK; `business_unit` String; `trip_id` BIGINT indexed; `trip_type` String;
`trip_date` Date nullable (date part of `"June 3, 2026, 11:00 AM"`); `stwid`
BIGINT indexed + `is_placeholder` Boolean; `route_rating`, `driver_rating`,
`cab_rating`, `safety_rating`, `marshal_rating` SmallInteger, stored raw
including 0; `creation_time` DateTime nullable.

### 3.6 Marts (empty in Story 01; rows land in Story 02)

- `daily_kpi`: `date` Date PK; `trips`, `delayed_trips`, `sev1_count` Integer
  nullable; `ota_pct`, `avg_delay_min`, `no_show_rate`, `cost_per_trip`,
  `alert_rate_per_1k`, `csat_avg` Float nullable.
- `vendor_kpi`: `vendor` String + `cycle_or_month` String(32) composite PK;
  `trips` Integer nullable; `ota_pct`, `cost_per_trip`, `cost_per_km`,
  `alert_rate_per_1k`, `csat_avg`, `low_rating_share` Float nullable.
- `office_kpi`: same shape with `office` String in place of `vendor`.
- `insight_cache`: `key` String PK (e.g. `briefing:latest`); `payload_json`
  JSON nullable; `computed_at` DateTime nullable.
- Portability: only generic SQLAlchemy types (`JSON` included) — no PG-only
  DDL, no server defaults — so `init_db()` creates identical schemas on
  SQLite (`aiosqlite`) and Postgres (`asyncpg`).

## 4. Normalization rules (implement in `core/normalize.py`)

Shared null rule, applied first in every parser: `None`, `''`,
whitespace-only, or case-insensitive `na`, `null`, `none`, `nan`, `nat` →
`None`. During implementation, spot-check `vendor_id`, `office`, `event_type`,
`contract` for a legitimate literal `NA` (none observed in sampling).

| # | Function | Input → output |
|---|---|---|
| 1 | `norm_trip_id(v)` | strip commas → `int`. `"1,097,076"` / `"1123974"` / `1123974` → `1123974`. Unparseable → raise `ValueError`: `trip_id` is the join spine, fail loud. |
| 2 | `norm_stwid(v)` | → `(value, is_placeholder)`. `0` / `"0"` → `(0, True)`; else comma-strip → int. |
| 3 | `is_real_rider(stwid)` | `stwid is not None and stwid != 0`. Story 02 excludes placeholders from rider stats. |
| 4 | `parse_trip_date(v)` | `"May 1, 2026"` → `date(2026, 5, 1)` via `%B %d, %Y`. |
| 5 | `parse_iso_date(v)` | `"2026-07-09"` → date via `date.fromisoformat`. |
| 6 | `parse_moment(v)` | `"June 3, 2026, 11:00 AM"` / `"May 1, 2026, 12:03 AM"` → datetime via `%B %d, %Y, %I:%M %p`. One thin per-file wrapper each for feedback `trip_date`/`creation_time`, alerts `start_time`/`acknowledge_time`, bills `cycle_start`/`cycle_end`. |
| 7 | `norm_float(v)` | null-rule → `None`, else strip commas → `float`. Covers `delay_minutes`, `trip_cost`, all `*_epoch` cols, km cols, July `planned_km` object drift. |
| 8 | `norm_bool(v)` | case-insensitive `true`/`1` → `True`, `false`/`0` → `False`; null-rule → `None`. Covers lowercase trip flags, capitalized emp flags, May's 4 empty NC cells → NULL. |
| 9 | `norm_severity(v)` | `"False"` → `(None, 'False', 'severity_false')`; null-rule (`NA`) → `(None, None, None)` = unclassified, no flag; `Sev-1/2/3` → `(value, value, None)`; anything else → `(None, raw, 'severity_unknown')`, logged. Returns `(severity, severity_raw, dq_flag)`. |
| 10 | `norm_km(v)` | `norm_float`, then `< 0` → `(None, 'negative_km')`, else `(value, None)`. Row always kept. |
| 11 | `norm_slab(v)` / `norm_contract(v)` | null-rule → `None` (covers bills' `null` + `NA`); else stripped string. The `'UNSLABBED'` display category is a Story 02 query-time mapping, not storage. |
| 12 | ratings | `int(v)`, stored raw including 0. `marshal_rating == 0` = unrated is a Story 02 averaging rule. |

Any other unparseable date/numeric → `None` + increment the per-rule counter
in the load report. Never drop the row (except rule 1, `trip_id`).

## 5. Ingest script (`src/backend/scripts/ingest.py`)

CLI: `--data DIR` (defaults to `problem-statement/dataset/data` resolved from
the current working directory, overridable), `--database-url` (defaults to
`settings.database_url`), `--tables` (comma-separated subset of
`trips,legs,bills,alerts,feedback`; default all — useful for dev iteration).

Flow per table:

1. Check file exists and required columns are present → otherwise print the
   mismatch and exit 2 (schema mismatch, per SPEC §3.6).
2. `DELETE FROM <table>` (idempotent base; order irrelevant, no FKs).
3. Stream `csv.DictReader` (`utf-8-sig` encoding), normalize each row (§4),
   accumulate ~10k-row batches, `await conn.execute(Table.insert(), batch)`
   on a single connection, one commit per file.
4. Collect: rows loaded, per-rule flagged counts, date min/max from the parsed
   date columns.
5. After all tables: print the load report; compare counts to expected
   (trips 615546, legs 1637906, bills 620942, alerts 51699, feedback 512873)
   and warn-with-reason past ±0.5%. Exit 0 unless step 1 failed.

Engine comes from `database.build_engine(url)` — dialect branching stays
centralized in `core/database.py`. No raw SQL; Core inserts run on both
backends unmodified.

## 6. Test plan (test-first, per AGENTS.md)

- `backend/tests/test_normalize.py` — pure functions, no DB: trip_id in 3
  shapes; stwid placeholder + `is_real_rider`; all 4 date formats; severity
  `False` / `NA` / `Sev-*`; negative km; zero-km + `null`/`NA`/empty slab;
  bool variants (`true` / `False` / `""`); comma numerics incl. a July-style
  `planned_km` object value.
- `backend/tests/test_ingest_models.py` — `init_db` on tmp SQLite, reusing the
  monkeypatched-engine pattern from `tests/test_examples.py:10`: all 9 tables
  exist with the §3 columns; marts are empty.
- `backend/tests/test_ingest_reload.py` — small inline CSV fixtures (one trip
  month + one file per other family, <50 rows each) written to `tmp_path`:
  ingest twice → identical counts (`test_idempotent_reload`); spot joins
  legs/bills/alerts/feedback → trips return > 0; flag counts
  (`severity IS NULL`, `is_zero_km`, `dq_flag = 'negative_km'`,
  `is_placeholder`) match fixture expectations.
- After every change from `backend/`: `uv run pytest`, then
  `uv run ruff check .`, loop until green.
- The full-dataset load is acceptance (manual, §7), not a unit test. Never
  commit dataset excerpts beyond inline fixture rows.

## 7. Acceptance mapping (SPEC §4)

1. Fresh DB → ingest loads all 5 tables, counts within ±0.5% → script count
   check (§5.5) + one manual full run.
2. Spot joins > 0 on the full load (`alerts`/`bills`/`feedback`/`legs` →
   `trips`) → fixture test + manual `SELECT COUNT(*) … JOIN`.
3. `alerts.severity IS NULL` ≈ 31k (16,348 `NA` + 15,037 `False`);
   `bills.is_zero_km` ≈ 248k; 48 negative-km legs flagged, rows kept →
   manual SQL on the full load.
4. Rerun idempotent → `test_idempotent_reload` + manual rerun comparison.
5. `daily_kpi` / `vendor_kpi` / `office_kpi` / `insight_cache` exist with §3.6
   columns (rows may be empty) → `test_ingest_models`.

## 8. Files to touch (final list)

- New: `backend/src/backend/core/normalize.py`,
  `backend/src/backend/models/ops.py`, `backend/src/backend/models/marts.py`,
  `backend/src/backend/scripts/__init__.py`,
  `backend/src/backend/scripts/ingest.py`,
  `backend/tests/test_normalize.py`,
  `backend/tests/test_ingest_models.py`,
  `backend/tests/test_ingest_reload.py`.
- Edit: `backend/src/backend/models/__init__.py` (register new models),
  `backend/README.md` (ingest command + `DATABASE_URL` note + null-marker
  table).
- Untouched: `api/health.py`, `api/examples.py`, `core/config.py`,
  `core/database.py` (import-only reuse).

## 9. Risks

- **Bulk-load time**: ~3.4M rows via `aiosqlite` executemany may take several
  minutes. Accept; if measured past ~10 min, follow up with a sync-`sqlite3`
  fast path or PG `COPY` (out of scope for this story).
- **`cycle_or_month` semantics** deferred to Story 02 (raw cycle strings
  stored until then).
- `Example` model + `examples.py` stay in place; removing them is later
  cleanup, not Story 01.
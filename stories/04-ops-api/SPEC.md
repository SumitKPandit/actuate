# Story 04 — Ops API `api/ops.py` (marts → FastAPI)

**Status:** complete (verified 2026-09-05: 13 API tests green, all endpoints mart-backed, CORS + error handling verified). **Depends on:** 01 (marts exist), 02–03 (logic to serve).

## 1. Goal

Frontend and Q&A have one fast, cached, mart-backed API. Transport manager's brief, dashboard, and vendor views all read here — p95 stays low because no endpoint scans raw tables.

## 2. Scope

**In:** `backend/src/backend/api/ops.py` (new router) + `backend/tests/test_ops_api.py`. Register router in `app.py` without touching `health/ready/examples`.
**Out:** narration text (Story 07 — endpoints return facts + template fallback string only, `?narrate=true` hook lands there), frontend (Stories 05–06), `/ask` full NL→SQL (Story 07; reserve path here with 501 or minimal stub). Push delivery out (Story 08 — log + `triggers[]` flag only).

## 3. Functional requirements

Base: all endpoints read marts (`daily_kpi`, `vendor_kpi`, `office_kpi`, `insight_cache`); query params `cycle` (e.g. `2026-06-H1`), `office`, `vendor`, `business_unit`. All responses JSON, ISO dates, rounded to 1 decimal for % / 2 for cost.

1. `GET /overview?cycle=&office=&vendor=` → KPI snapshot for filters: `{ trips, ota_pct, avg_delay_min, delay_reason_mix (late-only shares, `count / late_count`), no_show_rate, cost_per_trip, cost_per_km, zero_km_share, alert_rate_per_1k, sev1_count, ack_sla_met_share, csat_avg, low_rating_share }` + `benchmarks: { ota_sla: 95, ack_sla_min: 30 }`.
2. `GET /insights?cycle=` → ranked exception list from Story 03 schema (compute on mart read, or read `insight_cache` if fresh — document choice; max age 6h via `computed_at`).
3. `GET /briefing?cycle=` → `{ generated_at, headline_facts[3-5 strings, template-rendered], insights_top5, safety_open_sev1, actions_top3 }`. No LLM call here (Story 07 adds optional `?narrate=true` later). Cached in `insight_cache` under `briefing:{cycle}`. Story 08 extends (not breaks) this shape with `triggers[]`.
4. `GET /vendors?cycle=&sort=ota|cost|alerts|csat` → vendor rows with peer rank per KPI + `contribution_share` to delay/cost gap. Explicit `UNSLABBED`/zero-km counts included.
5. `GET /actions?cycle=` → flattened `{ id, action, owner, due_hint, copy_for_vendor, status }` derived from insights (copy text is template fill, ≤ 500 chars, includes vendor name + KPI + cycle). `status` defaults to `proposed`.
6. `POST /actions/{id}/ack` (human approval) → `{ id, status: "acked", actor, acked_at }` with `{ actor }` in body. Mock execution only (no vendor integration per Constraints); persists status to `insight_cache` under `action:{id}` + server log line for audit. Unknown id → 404. This closes the Act step's approval half; trigger firing half closes in Story 08.
7. Errors: unknown cycle → 404 with valid cycle list; empty mart → 200 with `data: null, warning: "marts empty — run ingest"`. Never 500 on empty data.

## 4. Acceptance criteria

- [ ] `GET /overview?cycle=2026-06-H1` returns all keys in §3.1 with types correct on seeded mini-marts (test DB, not full dataset).
- [ ] `GET /insights` order matches `reason.py` ranking on same fixture.
- [ ] `GET /briefing` second call within 6h hits `insight_cache` (test asserts `computed_at` unchanged).
- [ ] `POST /actions/{id}/ack` flips `proposed → acked`, persists to `insight_cache`, second ack is idempotent (same `acked_at` not overwritten unless new actor — document choice); unknown id → 404.
- [ ] `/health`, `/ready`, `/examples` still pass unchanged.
- [ ] p95 note: no endpoint issues a full-table scan in tests (assert query count or mock session to mart-only — document approach).

## 5. Test plan (test-first)

`backend/tests/test_ops_api.py` (use TestClient + SQLite test DB seeded with 20–50 rows of mini-marts):
- `test_overview_shape_and_benchmarks`.
- `test_insights_ranked`.
- `test_briefing_cached`.
- `test_vendors_sort_and_peer_rank`.
- `test_actions_copy_text`.
- `test_ack_flips_status` + `test_ack_unknown_id_404` + `test_ack_idempotent`.
- `test_unknown_cycle_404` + `test_empty_marts_warning`.
- Red → implement → `uv run pytest` green.

## 6. Files to touch

- New: `backend/src/backend/api/ops.py`, `backend/tests/test_ops_api.py`.
- Edit: `backend/src/backend/app.py` (add `include_router` only), `backend/README.md` (endpoint table).
- Do not modify: `api/health.py`, `api/examples.py`, `core/database.py`.

## 7. Notes

- Route prefix: `/` (i.e. `/overview`, not `/api/overview`) to match PLAN §5 paths. CORS already covers `localhost:3000` via `core/config.py`.
- Keep response models as Pydantic schemas in `api/ops.py` (or `models/schemas.py` if it grows) — frontend Stories 05–06 codegen against these shapes.

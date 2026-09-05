# Story 04 — Technical Spec: Ops API (`api/ops.py`, marts → FastAPI)

Companion to `SPEC.md`. Build blueprint: frozen cycle convention, additive
mart columns, exact endpoint/schema contracts, aggregation semantics,
cache + ack rules, and test vectors. Derived from `PLAN.md` §3/§4,
`stories/README.md`, Story 01 contracts (raw shapes, mart schemas),
Story 02 contracts (`core/analytics.py` KPI math/rounding),
Story 03 contracts (`core/reason.py`, `TECH_SPEC.md`), downstream shapes
(Stories 05/06/07/08 SPECs + `frontend/SPEC.md` §2), and the backend
scaffold (`app.py`, `api/examples.py`, `api/health.py`, `core/database.py`,
`models/marts.py`, `models/ops.py`).

Decisions locked while writing (no user round-trip; all marked `FROZEN`):
cycle labels, mart additions, per-field aggregation sources, compute-always
`/insights`, envelope shape, ack transfer rule, `business_unit` handling,
`POST /ask` 501. Anything Story 07/08 owns is fenced off, never stubbed
with fake data.

## 1. Evidence summary

- **Marts exist as schemas only — all four are empty.**
  Live `backend/actuate.db`: `daily_kpi / vendor_kpi / office_kpi /
  insight_cache` all hold **0 rows**. Ingest creates the schemas; Story 02
  shipped pure functions with persistence explicitly out of scope, so no
  story so far writes mart rows. Consequence: Story 04 serves whatever is
  in the marts, tests seed mini-marts (SPEC §5), and **production
  population is a documented follow-up** (§9) — this story adds no
  populator, no raw-table reads at request time, ever.
- **Billing cycles in the data (read from `bills`, not assumed).**
  Nine distinct `(cycle_start, cycle_end)` pairs: 3 full-month
  (`2026-05-01→05-31`, `2026-06-01→06-30`, `2026-07-01→07-31`) plus 6
  halves (`…-01→…-15`, `…-16→…-end` for May/Jun/Jul). `bill_data.md` names
  the 6 semi-monthly cycles; the full-month rows are out of scope
  (documented, never served). This spec freezes the label convention in
  §3.1 — `cycle_or_month` semantics were deferred by Stories 01/02 and
  land here.
- **Current mart shapes** (`models/marts.py:11-59`):
  `daily_kpi {date PK, trips, delayed_trips, sev1_count, ota_pct,
  avg_delay_min, no_show_rate, cost_per_trip, alert_rate_per_1k,
  csat_avg}`, `vendor_kpi {vendor, cycle_or_month composite PK, trips,
  ota_pct, cost_per_trip, cost_per_km, alert_rate_per_1k, csat_avg,
  low_rating_share}`, `office_kpi` (same keys by `office`),
  `insight_cache {key PK, payload_json JSON, computed_at DateTime}`.
  Gaps against SPEC §3.1/§3.4 (no source for `delay_reason_mix`,
  `zero_km_*`, `UNSLABBED`, `ack_sla_met_share`, `avg_ack_minutes`,
  `max_trip_cost`, per-cycle `no_show/avg_delay/sev1` by vendor/office)
  are closed by **additive nullable columns** (§3.2) — allowed because
  SPEC §6 forbids only `api/health.py`, `api/examples.py`,
  `core/database.py`. Story 03 already booked one of these:
  `DailyKpi.max_trip_cost` (Story 03 `TECH_SPEC.md` §8).
- **Reason brain is the only ranking contract** (`core/reason.py`):
  `BENCHMARKS` (OTA SLA 95, ack SLA 30, rate Δ 2pp, cost Δ 10%, z |z|>2
  min 14pts), `build_insights(*, snapshot, prior, vendor_rows,
  office_rows, delay_splits, daily_series, cycle, as_of)`,
  `contribution_top2`, `rank_insights`, stable slug ids
  (`{kpi}_{reason}_{cycle}_{scope}`, `v_`/`o_`/`all` segments).
  `/insights` returns `build_insights` output verbatim — the order-match
  acceptance test is then comparative, not hand-computed.
- **Analytics conventions reused, not redefined** (`core/analytics.py`):
  late = `delay > 15` strictly; reason mix is **late-only**
  (`count / late_count`); CSAT excludes 0s, `< 3` = low;
  `cost_per_km` excludes zero-km denominator; `_r2` = 2dp None-safe.
  SPEC §3.1's display rounding (1dp % / 2dp cost) is applied at the API
  boundary only (§2.7) — `analytics`/`reason` internals are untouched.
- **Scaffold patterns to copy**: `api/examples.py:13,29-43` (router +
  `db: AsyncSession = Depends(get_db)` + Pydantic schemas);
  `app.py:32-33` (one `include_router` line each); `core/database.py`
  (`get_db`, `init_db` on lifespan — local SQLite migration note in
  §8: existing `actuate.db` needs its mart tables recreated for the new
  columns). `pyproject.toml`: no `pandas`; stdlib + fastapi/pydantic/
  sqlalchemy only.
- **Downstream constraints that pin shapes:**
  - Stories 05/06 + `frontend/SPEC.md` §2 read `/overview /vendors`
    with filters `cycle, office, vendor, business_unit`; cards show
    current + Δ vs prior + benchmark badges (OTA 95, ack 30) + peer
    rank; missing cells render `—`, never `0`; `warning` banner surfaced
    verbatim; 404-cycle falls back to latest.
  - Story 07 adds `POST /ask` (in `api/ops.py` or new `api/ask.py`) +
    `GET /briefing?narrate=true`; this story only **reserves** `/ask`.
  - Story 08 extends `/briefing` with `triggers[]` (never breaks §4.3
    shape) and reuses the ack endpoint as the approval half.

## 2. Design decisions (FROZEN)

1. **Mart-only reads, enforced by test.** No endpoint imports
   `models/ops.py` or queries `trips/legs/bills/alerts/feedback`. The
   suite wraps `session.execute` and fails any statement touching a raw
   table (§6, `test_no_raw_table_scans`). This is the p95 acceptance
   proof — no timing flakes, no query-count thresholds.
2. **`/insights` computes on every mart read; `insight_cache` is for
   briefing + ack only.** Rationale: computed insights can never go
   stale relative to the marts, and order==`reason.py` holds by
   construction. The 6h `computed_at` rule then governs `briefing:{cycle}`
   exclusively. (SPEC §3.2 explicitly permits either choice with
   documentation — this is the documentation.)
3. **Envelope `{data, warning}` on all five GETs.** Non-empty →
   `{"data": {…}, "warning": null}`; empty marts → HTTP 200
   `{"data": null, "warning": "marts empty — run ingest"}` (exact SPEC
   string, frozen). Frontend codegens against `data.*` (Stories 05–06).
   `POST ack` returns the bare ack object per SPEC §3.6; errors are
   `{"detail", …}` per §5.
4. **`cycle` is required on all five GETs** (FastAPI required query
   param; missing → 422). Unknown cycle → 404 + `valid_cycles` (§5).
   Empty-mart check runs **before** cycle validation (no valid cycles
   exist when marts are empty).
5. **Overview filter semantics (mart grain is what it is).**
   `daily_kpi` carries no office/vendor/business_unit grain;
   `vendor_kpi` is keyed `(vendor, cycle)`, `office_kpi` `(office,
   cycle)`. Frozen rule: the snapshot aggregates **vendor rows** by
   default (or the single `vendor=` row); when `office=` is given
   **without** `vendor=`, it aggregates **office rows** instead; when
   both are given, the vendor slice wins (documented precedence —
    vendor attribution is the primary transport-manager workflow).
    `business_unit` is accepted (query param) and ignored — a **documented no-op**:
    no mart carries BU grain; adding it is a filed follow-up (§9), not
    silent behavior. Frontend keeps sending it; nothing 422s on it.
    Nothing in the response echoes it back (no `business_unit` key in §4).
6. **Trips-weighted means with documented approximations.** Ratio KPIs
   cannot be reconstructed exactly from per-vendor means, so every
   aggregated mean is `Σ(v·trips)/Σ(trips)`; counts are exact sums.
   Per-field sources are frozen in §4.1 — tests assert the weighted
   arithmetic exactly on the fixture (§6 vectors).
7. **Boundary rounding at the API edge only.** Percent-scale KPIs →
   1dp, costs → 2dp, counts → int, 0–1 shares
   (`contribution_share`, mix shares) → `_r2` fractions (frontend
   multiplies by 100; consistent with `analytics`/`reason` share
   semantics). Missing (`None`) renders as JSON `null` — never `0`
   (frontend shows `—`). Rounding helpers live in `api/ops.py`
   (`_r1` mirrors `reason._r2` at 1dp); `core/` files are untouched.
8. **No new dependencies, no forbidden imports.** `api/ops.py` imports
   `reason` (pure), mart models, `get_db`, fastapi/pydantic/sqlalchemy/
   stdlib (`datetime`, `logging`, `math`) only. No LLM SDK, no
   `datetime.now()` in `core/` (API timestamps use UTC now at the edge
   — allowed; testability comes from asserting shape/recency, and
   briefing-cache tests read `computed_at` from the DB row).

## 3. Static contracts

### 3.1 Cycle labels (FROZEN)

- Label form: `YYYY-MM-H1 | YYYY-MM-H2`. `H1` = 1st–15th inclusive,
  `H2` = 16th–month-end inclusive. Matches the six bill halves in §1.
- `vendor_kpi.cycle_or_month` / `office_kpi.cycle_or_month` store the
  label verbatim (e.g. `2026-06-H1`). Full-month rollups are out of
  scope: rows keyed by month alone are ignored by cycle matching
  (documented; a month label never equals a half label).
- `daily_kpi` range for a cycle: H1 → `[YYYY-MM-01, YYYY-MM-15]`,
  H2 → `[YYYY-MM-16, last-day-of-month]` (calendar-aware, no hardcoded
  30/31).
- Prior cycle (MoM): H1 → previous-month H2; H2 → same-month H1
  (e.g. prior of `2026-06-H1` is `2026-05-H2`). Year boundary handled
  (`2026-01-H1` → `2025-12-H2`).
- `valid_cycles` = sorted distinct `cycle_or_month` across
  `vendor_kpi ∪ office_kpi`. Daily-only dates never invent a cycle.

### 3.2 Mart additions (additive, nullable — `models/marts.py`)

```python
class DailyKpi:  # +=
    max_trip_cost: Mapped[float | None] = mapped_column(Float)  # Story 03 booking: max(bills.trip_cost) per date

class VendorKpi / OfficeKpi:  # += each (same names both tables)
    delayed_trips: Mapped[int | None] = mapped_column(Integer)   # late (delay>15) trip count in cycle slice
    avg_delay_min: Mapped[float | None] = mapped_column(Float)
    no_show_rate: Mapped[float | None] = mapped_column(Float)    # percent 0-100
    zero_km_count: Mapped[int | None] = mapped_column(Integer)   # billed rows with km == 0
    unslabbed_count: Mapped[int | None] = mapped_column(Integer) # billed rows with slab NULL (display 'UNSLABBED')
    sev1_count: Mapped[int | None] = mapped_column(Integer)
    avg_ack_minutes: Mapped[float | None] = mapped_column(Float)
    ack_sla_met_share: Mapped[float | None] = mapped_column(Float)  # percent 0-100, ≤30 min
    late_reason_counts: Mapped[dict | None] = mapped_column(JSON)   # late-only {REASON: count}, keys ⊆ {NODELAY,TRAFFIC,DRIVER,EMPLOYEE,UNKNOWN}
```

No PK changes, no non-null constraints, no raw-table changes. Seeded
tests insert these directly; production population is the §9 follow-up
(same gap as the already-empty base columns — this story changes
nothing about that). Local dev note (§8): recreate mart tables after
pulling (existing `actuate.db` keeps the old schema; `init_db` only
creates missing tables).

### 3.3 Module layout (`backend/src/backend/api/ops.py`)

```text
"""Mart-backed ops routes — overview/insights/briefing/vendors/actions (Story 04)."""

router = APIRouter(tags=["ops"])          # NO prefix: paths are /overview … (SPEC §7)

# Pydantic schemas (frontend Stories 05-06 codegen against these):
OverviewData / OverviewResponse            # §4.1 + benchmarks
InsightSchema                              # re-exports reason.py Insight keys verbatim (scope/current/baseline/…)
BriefingData / BriefingResponse            # §4.3 (NO triggers key — Story 08 adds it)
VendorRow / VendorsResponse                # §4.4
ActionItem / ActionsResponse               # §4.5
AckRequest {actor} / AckResponse           # §4.6
Envelope wrappers: {data, warning}         # §2.3; ErrorShapes §5

# Pure helpers (< ~40 lines each, unit-testable without a DB):
_r1(x)                                     # None-safe round(x,1); non-finite -> None
_parse_cycle(cycle) -> (start_date, end_date, prior_label)   # §3.1; ValueError on bad form
_weighted_mean(pairs) / _sum / _share      # aggregation primitives (§4.1)
_snapshot_from_vendor_rows(rows)            # rows -> reason.build_insights snapshot dict
_delay_splits(rows, key)                   # rows -> [{key, trips, late_count}] (late_count = delayed_trips if present
                                           #   else round(trips*(100-ota_pct)/100); documents the fallback)
_daily_series(daily_rows)                  # date-ordered {kpi: [values]} per §3.5 canonical metrics
_headline_facts(snapshot, insights, cycle) # 3-5 template strings (§4.3)
_action_from_insight(insight, ack_map)     # insight -> ActionItem (§4.5; copy ≤500 chars)
_valid_cycles(vendor_labels, office_labels)

# Routes (all mart-only; db: AsyncSession = Depends(get_db)):
GET  /overview?cycle=&office=&vendor=&business_unit=
GET  /insights?cycle=
GET  /briefing?cycle=
GET  /vendors?cycle=&sort=&business_unit=
GET  /actions?cycle=
POST /actions/{id}/ack            # body {actor}
POST /ask                         # 501 reserved (§4.7)
```

`GET /vendors` accepts `business_unit` (accepted-no-op per §2.5, same
as overview) — kept so dashboard filter state round-trips without
special-casing. `sort ∈ {ota,cost,alerts,csat}` default `ota`; anything
else → 422.

### 3.4 Benchmarks (single-sourced)

`benchmarks: {ota_sla: 95, ack_sla_min: 30}` is built from
`reason.BENCHMARKS["ota_sla_pct" / "ack_sla_min"]` at request time —
never literals in `api/ops.py`. (A `rg` for `95`/`30` outside tests
must hit only the fallback-safe accessor, mirroring Story 03 §2.9.)

## 4. Endpoint contracts

Common: `cycle` required; filters optional (`None` = all). All datetimes
ISO-8601 (`generated_at`/`acked_at` timezone-aware UTC). The §4.1/§4.3/§4.4
tables below describe the `data` payload **inside** the §2.3 envelope —
frontend unwraps `data.*` and surfaces `warning` verbatim (Stories 05–06).
Every GET
hits at most: 1 distinct-cycles query (for 404 payloads — skippable when
the cycle hit), 1–3 mart `SELECT`s with equality filters on
`(cycle_or_month)` / `(vendor, cycle_or_month)` / `(office,
cycle_or_month)` / date range, plus 1 `insight_cache` read for
`/briefing` and `/actions` (ack overlay). No `JOIN`s, no raw tables.

### 4.1 `GET /overview` — KPI snapshot + benchmarks

Row selection per §2.5 (vendor rows default / office rows iff
`office=`-only). Aggregation (frozen per-field semantics):

| Response key | Aggregation | Type/scale |
|---|---|---|
| `trips` | Σ trips | int |
| `ota_pct` | `100·(1 − Σdelayed/Σtrips)`; `None` if Σtrips 0 | 1dp % |
| `avg_delay_min` | trips-weighted mean | 1dp |
| `delay_reason_mix` | Σ `late_reason_counts` → `{reason: {count, share}}`, late-only `share = count/Σlate`, `None` shares when Σlate 0; keys ⊆ analytics `REASONS + UNKNOWN` | counts int, shares 0–1 `_r2` |
| `no_show_rate` | trips-weighted mean | 1dp % |
| `cost_per_trip` | trips-weighted mean (documented approx) | 2dp |
| `cost_per_km` | trips-weighted mean (documented approx) | 2dp |
| `zero_km_share` | `100·Σzero_km/Σtrips`; `None` if Σtrips 0 | 1dp % |
| `alert_rate_per_1k` | trips-weighted mean (documented approx) | 1dp |
| `sev1_count` | Σ | int |
| `ack_sla_met_share` | trips-weighted mean | 1dp % |
| `csat_avg` | trips-weighted mean | 1dp (1–5) |
| `low_rating_share` | trips-weighted mean | 1dp % |
| `benchmarks` | `{ota_sla: 95, ack_sla_min: 30}` from `BENCHMARKS` | literals never in `ops.py` |

`trips == 0` (rows exist, all zero/None) → numeric keys `None`, still
HTTP 200 with `data` present (distinct from the no-rows envelope).

### 4.2 `GET /insights` — ranked exceptions (compute-always)

1. Load cycle rows: vendor rows, office rows, daily rows in range
   (§4.1 row rule does **not** apply — insights always sees all three
   sets; filters beyond `cycle` are not accepted on this route).
2. `snapshot = _snapshot_from_vendor_rows(cycle vendor rows)` completed
   with cycle-wide `max_trip_cost = max(daily.max_trip_cost)` and
   `avg_ack_minutes` (weighted) for the absolute checks.
3. `prior` = same builder on the prior-cycle label (§3.1); absent prior
   rows → `prior=None` (MoM checks skip per Story 03 §4.2).
4. `delay_splits` from vendor rows (§3.3 fallback documented).
5. `daily_series` from daily rows (needs ≥14 finite points per metric
   to fire — else the Story 03 skip path, never a false positive).
6. Return `rank_insights(build_insights(…))` **verbatim** (Story 03
   schema, no re-rounding — insight numbers keep reason precision;
   display rounding is a frontend concern).

### 4.3 `GET /briefing` — cached template brief

- Cache: `insight_cache` key exactly `briefing:{cycle}` (cycle-scoped
  only — no filter dims on this route). Hit with
  `now − computed_at < 6h` → return stored payload **untouched**
  (test asserts `computed_at` unchanged, §6). Miss/stale → compute,
  upsert `{key, payload_json, computed_at: now UTC}`, return.
- Payload (frozen; Story 08 **adds** `triggers[]`, never renames):
  `{generated_at (UTC ISO), headline_facts[3–5], insights_top5 (full
  Insight dicts), safety_open_sev1 (int), actions_top3 (full
  ActionItems)}`.
- `headline_facts` templates (verbatim slots, values 1dp/2dp per §2.7):
  1. OTA lead (always): `"OTA {cycle} was {ota}% vs SLA 95% across
     {trips} trips."`
  2. Top insight (if any): `"Top exception: {kpi} {current} vs
     {baseline} ({scope_str}) — {reach} trips affected."`
  3. Safety (iff `sev1_count > 0`): `"{sev1} Sev-1 alerts this cycle —
     acknowledge open items + escort audit."`
  4. Cost (iff a cost insight fires): `"Cost outlier: {vendor} at
     ₹{cpt}/trip — hold bill line + verify km slab."`
  5. CSAT/noshow filler (iff needed to reach 3): `"CSAT {csat} with
     {low}% low ratings."` / `"No-show rate {ns}%."`
  Rules: facts 1–2 always; 3–5 appended in order while `len < 5`;
  minimum 3 guaranteed on non-empty marts (OTA + top-insight + one
  filler — filler uses `None`-safe `"—"` wording when its KPI is
  missing, never crashes).
- `safety_open_sev1` = cycle `sev1_count` (FROZEN approximation:
  marts carry no open-vs-acked alert state; documented here, not
  hidden — alert-level truth arrives with richer marts).
- `?narrate=true` is **rejected with 422** (`{"detail": "narrate
  lands in Story 07"}`) — distinct from `/ask`'s 501 so Story 07 can
  claim the hook without changing this route's default behavior.

### 4.4 `GET /vendors` — peer table

- Rows: all `vendor_kpi` rows for `cycle` (each row → one `VendorRow`).
  Sort keys (frozen directions): `ota` = `ota_pct` desc; `cost` =
  `cost_per_trip` asc; `alerts` = `alert_rate_per_1k` asc; `csat` =
  `csat_avg` desc. `None` sorts last regardless of direction. Ties →
  vendor name asc (total order, deterministic).
- `peer_rank`: 1-based rank **per displayed sort KPI** (rank 1 = best
  in that direction; equal values share the same rank — competition
  ranking `1,2,2,4`, frozen). Response also carries the row's own
  values for the other KPIs (no extra rank fields — dashboard needs
  one rank context per sort view).
- `contribution_share`: from `reason.contribution_top2` over cycle
  vendor splits (§3.3); the cycle-level share is echoed on every row
  whose vendor is in `top2`, `None` elsewhere (row-level shares are
  not invented — the map is `top2[k].share` by vendor name).
- Explicit counts (never folded into prose): `zero_km_count`,
  `unslabbed_count` verbatim from the row (`None` → `null`, frontend
  shows `—`). Row KPIs: `{vendor, trips, ota_pct, cost_per_trip,
  cost_per_km, alert_rate_per_1k, csat_avg, low_rating_share,
  peer_rank, contribution_share, zero_km_count, unslabbed_count}`.
  Canonical keys are the suffixed mart names above — `frontend/SPEC.md`
  §2 shorthand maps `ota→ota_pct`, `alert_per_1k→alert_rate_per_1k`,
  `csat→csat_avg`. README documents the mapping with a curl example
  showing the envelope.

### 4.5 `GET /actions` — flattened proposals + ack overlay

- Source: `GET /insights` computation for the cycle (shared helper,
  not an HTTP call), mapped one-insight→one-action.
- `ActionItem` (frozen keys): `{id (insight id verbatim — ack addressing
  is stable across calls), action (insight `recommended_action`),
  owner, due_hint, copy_for_vendor, status}`.
- `due_hint` rule (deterministic, severity-based): `high` → `"within
  48 hours"`; `medium` → `"this cycle"`; `low` → `"next cycle"`.
- `copy_for_vendor` template (≤ 500 chars, hard-truncated with `…`
  only if over — templates below are ~200 chars so truncation should
  never fire; the cap is a guard, asserted in tests):
  `"{Vendor}: {action} — {kpi} {current} vs baseline {baseline} in
  {cycle} ({reach} trips). Owner: {owner}, due {due_hint}."`
  Vendor slot = `scope.vendor or scope.office or "All vendors"`; must
  contain vendor/office name + KPI id + cycle (SPEC §3.5 assertion).
- `status`: `"proposed"` default; `"acked"` iff `insight_cache` holds
  `action:{id}` (overlay map loaded once per request; no N+1 — single
  `IN` query or one full `action:%`… note: `LIKE 'action:%'` scan is
  on the tiny cache table, frozen as acceptable; keyset is bounded by
  insight count).

### 4.6 `POST /actions/{id}/ack` — human approval (mock execution)

- Body: `{actor: str}` — required, non-blank after strip (missing →
  422). No other fields accepted (extra → 422 via strict model —
  keeps the audit shape closed).
- ID validity: `{id}` must appear in the derived action set for **any
  known cycle** (recomputed across `valid_cycles`) **or** already exist
  as `action:{id}` in cache (re-ack path). Else 404
  `{"detail": "unknown action id", "id": …}`.
- Write: upsert `insight_cache{key: "action:{id}", payload_json:
  {id, status: "acked", actor, acked_at (UTC ISO)}, computed_at: now}`.
- Idempotency (FROZEN per SPEC §4 "document choice"): same-actor
  re-ack → returns the **stored** record unchanged (`acked_at`
  preserved — test asserts byte-equality); different-actor ack →
  **transfers** approval (actor + `acked_at` overwritten) — the audit
  trail for superseded acks is the server log (§4.6 log line), not the
  row. Both paths HTTP 200.
- Audit: `logger.info("action_ack id=%s actor=%s acked_at=%s",
  …)` on every write (not on idempotent same-actor repeats —
  frozen, so log volume equals approval transfers). Mock execution
  only: no vendor call, no side effects beyond cache + log
  (Constraints + Stories README global rules).
- Response: the stored record verbatim `{id, status: "acked", actor,
  acked_at}`.

### 4.7 `POST /ask` — reserved (FROZEN)

`501 {"detail": "reserved for Story 07 (NL-to-SQL over marts)"}` on any
body (including empty). Rationale: 501 is honest about unimplemented
vs malformed; Story 07 owns both the 422 taxonomy and the route's
final home (`api/ops.py` or new `api/ask.py` — this reservation does
not pin the file).

## 5. Errors + edge cases (must never 500)

| Input | Result |
|---|---|
| All four marts empty (any GET) | 200 `{"data": null, "warning": "marts empty — run ingest"}` (checked first) |
| Unknown `cycle` (marts non-empty) | 404 `{"detail": "unknown cycle", "cycle": …, "valid_cycles": […]}` |
| `cycle` missing | 422 (required query param) |
| `cycle` malformed (`"june"`, `"2026-6-1"`, `"2026-06-H3"`) | 404 with `valid_cycles` (treated as unknown, not 422 — friendlier for the cycle-selector fallback; frozen) |
| `sort=` outside `{ota,cost,alerts,csat}` | 422 `{"detail": "invalid sort", "allowed": […]}` |
| Rows exist but all-None/zero-trips slice | 200 with `data` present, numeric keys `null` (never the empty envelope) |
| `briefing` insights empty | facts 1 + filler path (§4.3); `insights_top5 []`, `actions_top3 []`, `safety_open_sev1 0` |
| `POST ack` missing/blank `actor` | 422 |
| `POST ack` unknown id | 404 + `id` echo (§4.6) |
| `POST ack` same actor twice | 200 stored record, `acked_at` byte-identical |
| `POST ack` different actor | 200 transfer record + log line |
| `GET /briefing?narrate=true` | 422 `"narrate lands in Story 07"` (§4.3) |
| Any `POST /ask` body | 501 (§4.7) |
| `insight_cache` JSON `null` payload / missing row | treated as miss (recompute / `proposed`) — never crash on `None` payload |
| Naive vs aware datetimes (SQLite) | compare/normalize in UTC; SQLite-naive `computed_at` assumed UTC (documented) |
| Postgres vs SQLite | equality filters + `IN` + `LIKE 'action:%'` only; JSON column read as dict on both (SQLAlchemy `JSON`); no dialect branches |

## 6. Test plan (test-first, per AGENTS.md)

`backend/tests/test_ops_api.py` — TestClient + per-test SQLite file DB
(mirror `test_examples.py`: `build_engine(url)` + monkeypatch
`database.engine`/`SessionFactory` + `create_app()`; lifespan
`init_db` creates schemas). One shared seeder, frozen fixture below
(20–50 mini-mart rows: 17 daily [15 current + 2 prior] + 6 vendor
[3 + 3] + 4 office [2 + 2] = 27 rows).

Frozen fixture (hand-computed — implementation asserts these exactly):

- Cycles: current `2026-06-H1` (daily 15 rows Jun 1–15: 800 trips/day,
  delayed 59×10 days + 58×5 days = 880 total, `ota_pct` 92.6/92.8 per
  day sd≈0.07 so **no z-score anomaly fires**; `sev1_count` 1×6 days +
  0×9 days = 6 total, sd≈0.49, |z|<2 so no fire; `max_trip_cost`
  3200.0 every day → cycle max 3200.0, below the 16k sanity cap so no
  cost-sanity fire); prior `2026-05-H2` (2 daily rows May 30–31 flat
  `ota_pct 95.5`, `max_trip_cost` 2800.0 — proves date-range filtering,
  never used for `daily_series` which reads the current cycle only).
- Current vendor rows (cycle `2026-06-H1`):

  | vendor | trips | ota | delayed | cost/trip | cost/km | alert/1k | csat | low% | zero | unslab | sev1 | noshow% | delay | avg_ack | ack_met% | reasons late-only |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | A | 6000 | 90.0 | 600 | 1450.00 | 48.50 | 12.0 | 4.2 | 8.0 | 300 | 1200 | 5 | 3.0 | 4.5 | 22.0 | 80.0 | T300/D200/E100 |
  | B | 4000 | 94.0 | 240 | 1200.00 | 40.00 | 6.0 | 4.7 | 4.0 | 80 | 800 | 1 | 2.0 | 2.0 | 18.0 | 92.0 | T120/D80/E40 |
  | C | 2000 | 98.0 | 40 | 1100.00 | 36.70 | 3.0 | 4.9 | 1.5 | 20 | 100 | 0 | 1.0 | 0.8 | 15.0 | 98.0 | T20/D10/E10 |

  Totals: trips 12000, late 880 → `ota_pct 92.7`
  (`100·(1−880/12000) = 92.666… → 92.7`); `zero_km_share 3.3`
  (`400/12000`); mix shares T `0.5` / D `0.33` (`290/880 = 0.3295`) /
  E `0.17` (`150/880 = 0.1705`); contribution: overall rate
  `880/12000 = 0.07333`, excess A `600−440 = 160.0`, B/C → 0 →
  `top2 [A share 1.0, B share 0.0]`, `contribution_share 1.0`
  (same arithmetic as Story 03 §6 vector 1); weighted `cost_per_trip`
  `1308.33`, `cost_per_km` `43.7`, `alert_rate_per_1k` `8.5`,
  `low_rating_share` `5.58→5.6`, `no_show_rate` `2.33→2.3`,
  `avg_delay_min` `3.05`, `avg_ack_minutes` `19.5`
  (`(6000·22+4000·18+2000·15)/12000`), `ack_sla_met_share` `87.0`,
  `csat_avg` `4.48→4.5`, `sev1_count` `6`. `avg_ack 19.5 < 30` so no
  absolute ack fire; `max_trip_cost 3200 < 16000` so no sanity fire.
- Prior vendor rows (cycle `2026-05-H2`, same trips, FROZEN — only OTA
  and `cost_per_trip` MoMs fire, everything else suppressed so insight
  ids stay unique):

  | vendor | trips | ota | delayed | cost/trip | cost/km | alert/1k | low% | noshow% | avg_ack | sev1 | reasons late-only |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | A | 6000 | 95.0 | 300 | 1250.00 | 47.00 | 12.0 | 8.0 | 3.0 | 22.0 | 2 | T150/D100/E50 |
  | B | 4000 | 96.0 | 160 | 1100.00 | 39.00 | 6.0 | 4.0 | 2.0 | 18.0 | 1 | T80/D50/E30 |
  | C | 2000 | 96.0 | 80 | 1000.00 | 35.50 | 3.0 | 1.5 | 1.0 | 15.0 | 1 | T40/D25/E15 |

  Prior totals: trips 12000, late 540 → `ota_pct 95.5`
  (`100·(1−540/12000) = 95.5`); weighted `cost_per_trip 1158.33`,
  `cost_per_km 42.42`, `alert 8.5`, `low 5.58`, `no_show 2.33`,
  `avg_ack 19.5`, `sev1 4`. MoM deltas: OTA `|92.7−95.5|=2.8>2`
  fires; `cost_per_trip` `+12.95%` (`(1308.33−1158.33)/1158.33`)
  fires; `cost_per_km` `+3.02%` does **not** fire (keeps the single
  `cost_vs_prior_*_all` id unique — two cost MoMs would collide);
  alert/low/no-show/avg_ack diffs are `0.0` so no fire; sev1
  `6 > 2·4` is false so no spike fire.
- Office rows (both cycles, FROZEN — full columns so the office-filter
  overview is fully populated; values chosen so **no office peer
  fires**):

  | office | cycle | trips | ota | delayed | cost/trip | cost/km | alert/1k | csat | low% | zero | unslab | sev1 | noshow% | delay | avg_ack | ack_met% |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | O1 | 2026-06-H1 | 7000 | 91.5 | 595 | 1320.00 | 44.00 | 9.0 | 4.4 | 5.8 | 250 | 1100 | 4 | 2.4 | 3.2 | 20.0 | 86.0 |
  | O2 | 2026-06-H1 | 5000 | 94.5 | 275 | 1290.00 | 43.00 | 7.8 | 4.6 | 5.3 | 150 | 800 | 2 | 2.2 | 2.7 | 18.5 | 88.5 |
  | O1 | 2026-05-H2 | 7000 | 94.8 | 364 | 1180.00 | 40.00 | 9.0 | 4.4 | 5.8 | 250 | 1100 | 3 | 2.4 | 3.0 | 20.0 | 86.0 |
  | O2 | 2026-05-H2 | 5000 | 96.4 | 180 | 1130.00 | 38.50 | 7.8 | 4.6 | 5.3 | 150 | 800 | 1 | 2.2 | 2.5 | 18.5 | 88.5 |

  Current office totals: trips 12000, late 870 → `ota_pct 92.8`
  (`100·(1−870/12000) = 92.75 → 92.8`, 0.1 above the vendor slice —
  the office-filter test asserts `92.8`, proving the §2.5 grain rule).
  Office peer gaps (current): OTA `93.0−91.5=1.5<2`, alert
  `9.0−8.4=0.6<2`, cost `+1.15%<10%`, low `0.25<2` → no office peer.
  Prior office rows exist only for `valid_cycles` completeness.
- Expected firing set (current, 7 insights, all deterministic): OTA
  `vs_sla` (high, 92.7<95), OTA `vs_prior` (medium, 2.8>2), cost
  `vs_prior` on `cost_per_trip` only (medium, +12.95%>10%), plus four
  vendor `vs_peer` on A (all medium: OTA mean 94.0 gap 4.0>2; ack mean
  7.0 gap 5.0>2; cost mean 1250.0 +16.0%>10%; csat-low mean 4.5 gap
  3.5>2). No z-score (sd≈0 / |z|<2), no sev1 spike, no office peer,
  no ack-absolute, no cost-sanity. Rank head is `vs_sla`
  (3·12000=36000); the two MoMs follow (2·12000, cost 12.95 before
  OTA 2.8 on the |delta| tie-break); then the four A-peers (2·6000,
  ordered by |delta|: cost 16.0 → ack 5.0 → ota 4.0 → csat 3.5) —
  test asserts **exact id order equality** against direct
  `build_insights` on the same dicts (comparative, robust to reason
  internals) plus head-is-`vs_sla`.

Tests (SPEC §5 1:1 + guards):

- `test_overview_shape_and_benchmarks` — all §4.1 keys present with
  frozen types/scales; `ota_pct == 92.7`; `cost_per_trip == 1308.33`;
  `cost_per_km == 43.7`; `alert_rate_per_1k == 8.5`;
  `zero_km_share == 3.3`; `sev1_count == 6`;
  mix shares `{TRAFFIC 0.5, DRIVER 0.33, EMPLOYEE 0.17}`;
  `benchmarks == {ota_sla: 95, ack_sla_min: 30}`; office-filter
  variant asserts the office slice (`ota_pct == 92.8`,
  `trips == 12000`), proving the §2.5 grain rule.
- `test_insights_ranked` — API id order == `build_insights` id order
  on fixture dicts; `len == 7`; head is the OTA `vs_sla` insight.
- `test_briefing_cached` — call twice; read `insight_cache` row
  directly, assert `computed_at` **unchanged**; facts `len 3–5`,
  lead fact contains `92.7` + `2026-06-H1`.
- `test_vendors_sort_and_peer_rank` — `sort=ota` → `[C,B,A]` ranks
  `1,2,3`; `sort=cost` → `[C,B,A]`; `zero_km_count`/`unslabbed_count`
  verbatim (A: 300/1200); `contribution_share` mapping frozen
  (A `1.0`, B `0.0`, C `None` — row shares are `top2[k].share`, never
  invented).
- `test_actions_copy_text` — every item `len(copy) ≤ 500`, contains
  vendor/office name + KPI id + cycle; `status == "proposed"`;
  `due_hint ∈ {within 48 hours, this cycle, next cycle}` with high →
  48h.
- `test_ack_flips_status` — `GET` shows `proposed` → `POST {actor}`
  → 200 `{acked,…}` → `GET` shows `acked`; cache row exists.
- `test_ack_unknown_id_404` — `POST /actions/nope/ack` → 404 + echo.
- `test_ack_idempotent` — same actor twice → byte-identical bodies;
  different actor → transfer (new actor, newer `acked_at`).
- `test_unknown_cycle_404` — `?cycle=2026-01-H1` → 404 +
  `valid_cycles` containing `2026-06-H1`.
- `test_empty_marts_warning` — fresh DB → all five GETs 200
  `{"data": null, "warning": "marts empty — run ingest"}`.
- `test_no_raw_table_scans` — session-execute wrapper records
  compiled statements; assert none reference
  `trips/legs/bills/alerts/feedback` across all six routes (the p95
  acceptance proof, §2.1).
- `test_narrate_and_ask_reserved` — `?narrate=true` → 422;
  `POST /ask` → 501.
- Flow: write tests → `uv run pytest tests/test_ops_api.py`
  confirms **red** → implement → green; then full `uv run pytest` +
  `uv run ruff check .` from `backend/`, loop until green. Existing
  `test_health/readiness/examples/app_lifespan` run unchanged (SPEC §4
  regression = the full suite staying green; no new assertions on
  those routes).

## 7. Acceptance mapping (SPEC §4)

1. Overview keys+types on seeded marts → §4.1 table + fixture
   vectors + `test_overview_shape_and_benchmarks`.
2. Insights order == `reason.py` ranking → verbatim passthrough
   (§4.2) + comparative `test_insights_ranked`.
3. Briefing 2nd call hits cache → §4.3 6h rule +
   `test_briefing_cached` (`computed_at` read from DB row).
4. Ack flip + persist + idempotent + unknown→404 → §4.6 frozen
   same-actor-preserve / different-actor-transfer + three ack tests.
5. Health/ready/examples unchanged → no touches (§8) + full suite
   green.
6. No full-table scans → §2.1 + `test_no_raw_table_scans`
   (statement-table assertion, documented approach).

## 8. Files to touch (final list)

- New: `backend/src/backend/api/ops.py`, `backend/tests/test_ops_api.py`.
- Edit: `backend/src/backend/app.py` (2 lines: import + one
  `include_router(ops_router)` after health/examples),
  `backend/README.md` (endpoint table: method/path/params/shapes +
  cycle convention pointer + cache/ack semantics),
  `backend/src/backend/models/marts.py` (**additive columns only**,
  §3.2 — amendment to SPEC §6's list, booked by Story 03 §8; local
  devs recreate mart tables in `actuate.db` afterwards).
- Do not modify: `api/health.py`, `api/examples.py`,
  `core/database.py`, `core/analytics.py`, `core/reason.py`,
  `scripts/ingest.py`, frontend (Stories 05–06 consume the frozen
  schemas; `POST /ask` reservation does not pin Story 07's file).
- Untouched behaviors: narration (Story 07 owns `narrate.py`,
  `?narrate=true`, `/ask` semantics), triggers + audit docs
  (Story 08 appends `triggers[]`, wraps `reason.py`, writes samples).

## 9. Risks + follow-ups (not this story)

- **Production marts are empty (§1).** Tests seed; nothing in prod
  fills base *or* new columns. Follow-up (ingest extension or
  mart-build script reusing `analytics.py`) must populate all of §3.2
  before any demo on real data — file it, don't smuggle a populator
  into this story (would violate SPEC §6 scope + AGENTS.md minimality).
- **`business_unit` is accept-but-no-op (§2.5).** No mart carries BU
  grain. If dashboard filtering by BU must actually slice numbers,
  that needs BU-grained marts — a schema + backfill story, not a
  one-line filter. Surfaced here so Stories 05–06 don't assume it.
- **Weighted-mean approximations (§2.6).** `cost_per_km`,
  `alert_rate_per_1k`, `cost_per_trip` aggregates are
  trips-weighted means of slice means, not true ratios. Exact while
  slices are homogeneous; documented so a future true-ratio mart
  (storing Σcost/Σkm numerators) can replace the helper without
  shape changes.
- **`safety_open_sev1 ≈ sev1_count` (§4.3).** "Open" overstates when
  Sev-1s were acked. True open-count needs alert-level mart state —
  same follow-up as row 1.
- **Late-count fallback (§3.3).** `round(trips·(100−ota)/100)` drifts
  ±1 vs true late counts; fixtures seed `delayed_trips` explicitly so
  tests never depend on the fallback. Backfill should populate the
  column, not rely on it.
- **`LIKE 'action:%'` overlay (§4.5).** Fine while the cache table is
  tiny (briefings + acks); revisit if `insight_cache` ever grows
  unbounded (Story 08 docs).
- **Malformed cycle → 404 (§5).** Chosen over 422 for the frontend
  fallback-to-latest flow; if API guidelines later demand strict
  422-on-malformed, the branch is isolated in `_parse_cycle`
  callers — one-line change, tests already pin current behavior.

# Story 02 — Technical Spec: KPI Analytics (`core/analytics.py`)

Companion to `SPEC.md`. Build blueprint: input contracts, exact function
signatures, frozen edge-case rules, and test vectors. Derived from `PLAN.md`
§4/§6, `stories/README.md`, Story 01 contracts (`models/ops.py`,
`core/normalize.py`, `TECH_SPEC.md`), the dataset dictionaries, and the
backend scaffold (`pyproject.toml`, `core/database.py`).

## 1. Evidence summary

- **Story 01 is done and is the only input contract.** Column names stay
  verbatim from the CSVs (`backend/src/backend/models/ops.py:11-123`):
  trips carry `delay_minutes: Float nullable` + `delay_reason: String`;
  legs carry `is_no_show: Boolean nullable` + `shift_type`/`office` +
  `boarding_status` text; bills carry `trip_cost: Float nullable` +
  `total_trip_km: Float` + `is_zero_km` + `vendor`/`cycle_start`/`slab_name`;
  alerts carry `severity: String nullable` (post-`norm_severity`: `"False"` →
  `None`) + `start_time`/`acknowledge_time: DateTime nullable`;
  feedback carries five `SmallInteger` ratings stored **raw including 0**.
- **Normalization is already applied upstream** (`core/normalize.py`):
  commas stripped before numeric cast; `severity "False"` → `(None, 'False',
  'severity_false')`; negative **legs** km → `(None, 'negative_km')`, row kept
  (`scripts/ingest.py:235-239` — `norm_km` applies to legs only; trips km and
   bills `total_trip_km` use `norm_float` (`ingest.py:210-211,278`), so negative
   bills km survive ingest and must be excluded at query time in `cost_stats`);
   zero-km bills kept with `is_zero_km=true`; `null`/`NA`/empty slab → `None`
   (the `'UNSLABBED'` display category is a Story 04 concern, not storage —
   Story 02 performs no slab grouping). `analytics.py` does **no parsing** —
   it assumes numeric-or-`None` inputs and never imports `normalize` (pure
   math; callers pass DB-shaped dicts/objects).
- **Backend constraints** (`backend/pyproject.toml`): no `pandas`
  dependency — iterables + stdlib only (`math`, `statistics`, `datetime`,
  `collections`).   `pytest` runs with `pythonpath = ["src"]`; commands run
  from `backend/`: `uv run pytest tests/test_analytics.py`, then
  `uv run ruff check .`. `core/database.py` (engine/session/`Base`) must not
  be imported — SPEC §4 bans `database`, `fastapi`, `httpx`, any LLM SDK.
- **Marts already exist, rows empty** (`models/marts.py:11-59`):
  `daily_kpi` / `vendor_kpi` / `office_kpi` / `insight_cache`. Story 02
  writes no rows — it only returns JSON-serializable dicts Story 03
  (`reason.py`) will consume. The raw→marts writer is explicitly **out of
  scope here and deferred to Story 04** (which persists/displays; no earlier
  story owns it: Story 01 left marts empty, Story 02 SPEC excludes
  persistence, Story 04 reads marts).
- **Calibration anchors** (`PLAN.md` §2, SPEC §7 — sanity only, never test
  fixtures): OTA ~93–97% (delayed ~2.4% May / ~7% Jun / ~3.9% Jul);
  cost median ~1236, mean ~1394, max ~16k; alerts Sev-1 = 656, Sev-2 = 572
  (`severity` ~16k nulls + ~15k `"False"`-as-null); `acknowledge_time`
  54 nulls (`alerts_data.md` acknowledge row — this is what SPEC §3 item 5's
  "54 nulls" refers to); feedback avg ~4.85, `marshal_rating` ~0.85 (mostly unrated).

## 2. Design decisions

1. **Row-in, JSON-out, uniform grouping.** Every KPI takes
   `Sequence[Mapping | object]` (plain dicts in tests; ORM objects also work
   via attribute fallback) and returns a `dict` of plain
   `dict/str/float/int/bool/None/list` values (`flag_cost_outliers` returns
   `list[dict]` instead, §4.5). Every grouped function takes
   `group_key: str | None = None` (including `ota_pct`, since PLAN requires
   vendor/office OTA peer rank); return shape is **always**
   `{group_value: stats}` with key `"all"` when ungrouped, `"UNKNOWN"` for
   missing/`None` group values (only `None`/missing maps to `"UNKNOWN"` —
   falsy-but-present `0`/`""`/`False` stay as-is). Uniform shape keeps Story
   03/04 mart writers branch-free. Sole exception: `flag_cost_outliers`
   returns a flat `list[dict]` (one entry per input row, §4.5).
2. **One KPI per function, <40 lines each.** Seven public functions (§4);
   three private helpers (`_get`, `_r2`, `_group_rows`; keep each under
   ~15 lines). No per-vendor/per-office
   special cases in code — caller passes `group_key="vendor_id"`,
   `"vendor"`, `"office"`, or `"shift_type"`.
3. **Rounding frozen at 2 decimals.** SPEC says "rounded" without precision:
   `_r2(x) = round(x, 2)`, `None`-safe (non-finite → `None`). All pcts,
   means, rates, shares, and money sums use it. Counts stay `int`.
   Rounded bucket shares are computed independently, so they carry rounding
   drift (e.g. three `0.33` shares sum to `0.99`) — exact-sum-to-1.0 is **not**
   guaranteed; tests assert individual shares, never the total.
4. **Scale convention (frozen per-field).** Headline rates use percent scale
   (0–100): `ota_pct`, `no_show_pct`, `zero_km_share`, `ack_sla_met_share`,
   `low_rating_share`, `marshal_unrated_share` (names keep the `_share`
   suffix to match the already-spec'd Story 04 `GET /overview` keys
   `zero_km_share`/`ack_sla_met_share`/`low_rating_share`). Nested bucket
   shares use fraction scale (0–1): `reason_mix` and `sev_breakdown`
   `{count, share}`. (`contribution_share` in Story 03 is a separate,
   Story-03-owned 0–1 definition.)
5. **`None` means "no data", never `0.0`.** Any zero denominator → `None`
   for the rate, with explicit `*_count`/`n` fields preserved so callers can
   distinguish "zero of many" from "no rows".
6. **Skip-missing, never crash, never invent.** `None`/`NaN`/`inf` numerics
   are skipped in means/sums (documented per function in §5); unknown
   categories fold into an explicit bucket (`"UNKNOWN"` reason,
   `"unclassified"` severity) instead of being dropped silently.
7. **Outlier uses population stdev.** `trip_cost > mean + 3 * pstdev`
   (`statistics.pstdev`; defined for n ≥ 2, stable on tiny fixtures).
   `statistics.stdev` (sample) is rejected: it needs n ≥ 2 with different
   scaling and would flag differently on small vendor groups. n < 2 or
   stdev == 0 → no outliers. Frozen vector: ten `1200` + one `16000` →
   threshold `15309.56` (sample-stdev would give `15932.56`), so the test
   asserts the threshold value itself to lock `pstdev`. Documented so Story
   03 anomaly checks reuse the same definition instead of redefining it.
8. **No new dependencies, no DB/HTTP/LLM imports.** Stdlib only. CI guard
   (matches `import x` and `from x import …` forms only, so prose comments
   can't trip it):
   `rg "^\s*(import|from)\s+.*(database|fastapi|httpx|openai|sarvam)" backend/src/backend/core/analytics.py`
   must return nothing.

## 3. Module layout (`backend/src/backend/core/analytics.py`)

```text
"""Pure MVP KPI math — no DB, no HTTP, no LLM (Story 02). See stories/02-analytics-kpis/SPEC.md."""

LATE_THRESHOLD_MIN = 15.0
ACK_SLA_MIN = 30.0
REASONS = ("NODELAY", "TRAFFIC", "DRIVER", "EMPLOYEE")
CSAT_DIMS = ("route_rating", "driver_rating", "cab_rating", "safety_rating")
MARSHAL_DIM = "marshal_rating"
SEVERITIES = ("Sev-1", "Sev-2", "Sev-3")

_get(row, key, default=None)      # dict lookup with object-attribute fallback
_r2(x)                            # None-safe round(x, 2); non-finite -> None
_group_rows(rows, group_key)      # None -> {"all": rows}; missing value -> "UNKNOWN"

ota_pct(rows, group_key=None) -> dict
delay_stats(rows, group_key=None) -> dict
no_show_stats(rows, group_key=None) -> dict
cost_stats(rows, group_key=None) -> dict
flag_cost_outliers(rows, group_key=None) -> list[dict]
alert_stats(alerts, trips_count) -> dict
csat_stats(rows) -> dict
```

## 4. Function contracts

### 4.1 `ota_pct(rows, group_key=None) -> dict`

- Per group: `{n, late_count, ota_pct}`. Extracts `delay_minutes` via
  `_get`; skips `None`/non-finite; `n` = rows with finite `delay_minutes`.
- `late = delay > 15.0` (strictly; `15.0` is on-time, `15.01`/`16` late).
- `ota_pct = 100 * (1 - late / n)` (percent scale, §2.4); empty/fully-missing
  group → `ota_pct None` with `n 0`, `late_count 0`.
- Grouped OTA is the single OTA path — callers must not re-derive it from
  `delay_stats`; `delay_stats` carries no OTA field.
- Example: 100 trips, 5 late → `{all: {n: 100, late_count: 5,
  ota_pct: 95.0}}`.

### 4.2 `delay_stats(rows, group_key=None) -> dict`

- Per group: `{n, late_count, avg_delay_min, reason_mix}`.
- `n` = rows with finite `delay_minutes`; `avg_delay_min` = mean, `None`
  when `n == 0`.
- `reason_mix`: `delay_reason` upper-stripped; buckets `REASONS` +
  `"UNKNOWN"` (`None`/other). `{reason: {count, share}}`; shares are 0–1
  fractions over group `n` (rows with finite `delay_minutes` — rows missing
  `delay_minutes` are excluded from both `n` and `reason_mix` even when a
  reason string is present). `None` group → all shares `None`.
  Independently rounded per §2.3, so the shares may not sum to exactly 1.0.

### 4.3 `no_show_stats(rows, group_key=None) -> dict`

- Legs grain. Per group: `{legs, no_shows, no_show_pct}`.
- Numerator counts only `is_no_show is True` (strict identity — `1`/`"true"`
  do not count); denominator = all rows in group (including `None`).
- `boarding_status` text never read (tests use it only as a cross-check
  that a disagreeing label does not change the result).

### 4.4 `cost_stats(rows, group_key=None) -> dict`

- Per group: `{billed_trips, total_cost, total_km, cost_per_trip,
  cost_per_km, zero_km_count, zero_km_share}`.
- `billed_trips` = rows with finite `trip_cost` (rows with `None` cost
  contribute to neither numerator nor count).
- `total_cost` = sum of finite costs (`_r2`-rounded); `total_km` = sum of
  `total_trip_km` where km is finite **and > 0** (zero/`None`/negative
  excluded; the negative guard is load-bearing for bills because Story 01
  nulls negatives only for legs km — §1).
- `cost_per_trip = total_cost / billed_trips` (`None` when 0);
  `cost_per_km = total_cost / total_km` (`None` when no positive km —
  the all-zero-km edge).
- `zero_km_count` = rows with `total_trip_km == 0`; `zero_km_share` over all
  rows in group.

### 4.5 `flag_cost_outliers(rows, group_key=None) -> list[dict]`

- Threshold computed **per group**: `mean + 3 * pstdev` over finite costs.
- n < 2 or pstdev == 0 → no row in that group flagged.
- Returns a **new flat list** (the §2.1 `{group: stats}` exception — one
  entry per input row, ungrouped shape) of dict copies each with added
  `is_outlier: bool`. Copies are plain-data dicts: `dict(row)` for mappings;
  for objects, `{k: v for k, v in vars(row).items() if not
  k.startswith("_")}` (drops SQLAlchemy `_sa_instance_state` and any
  private attr). Input never mutated.

### 4.6 `alert_stats(alerts, trips_count) -> dict`

- `{alerts, trips, alert_rate_per_1k, sev1_count, sev2_count,
  sev_breakdown, avg_ack_minutes, ack_sla_met_share, unacknowledged_count}`.
- `trips_count: int | None`; rate = `1000 * alerts / trips_count`
  (`None` when `trips_count` is `None`/0; zero trips edge).
- `sev_breakdown`: keys always `Sev-1/Sev-2/Sev-3/unclassified`, each
  `{count, share}` with shares as 0–1 fractions over all alerts (independently
  rounded per §2.3). Exact match only — `None`,
  `"False"`-as-`None` (arrives as `None`), and any unknown string fold into
  `"unclassified"`. Empty input → counts `0`, shares `None`.
- Ack: `ack_minutes = (acknowledge_time - start_time).total_seconds() / 60`
  per alert with both timestamps present; **negative deltas clamp to
  `0.0`** (ack-before-start is bad data; counted as met, documented).
  `avg_ack_minutes` over acked alerts only (`None` when none).
  `ack_sla_met_share` (percent scale, §2.4) = met(`<= 30`) /
  alerts-with-valid-`start_time` (rows with `NULL acknowledge_time` count as
  missed in this denominator, never dropped — covers the 54-null fixture
  requirement; a row missing `start_time` is excluded from ack stats only but
  still increments `unacknowledged_count` when its `acknowledge_time` is
  `NULL`, and stays in alert totals).

### 4.7 `csat_stats(rows) -> dict`

- `{per_dim: {route_rating: {avg, n_rated, n_unrated}, ...,
  marshal_rating: {...}}, low_rating_share, marshal_unrated_share,
  csat_avg}`.
- Per dimension: `0` = unrated (excluded from `avg`, counted in
  `n_unrated`); `None`/non-`int` = missing (excluded from both);
  `avg` over rated (1–5) only, `None` when `n_rated == 0` (all-ratings-0
  edge).
- `low_rating_share` (percent scale, §2.4) = pooled ratings `< 3` / pooled
  non-zero **and non-missing** ratings across the **4 non-marshal dims only**
  (`None` when pool empty). Marshal is excluded: its mostly-unrated
  distribution would otherwise dominate the headline share.
- `marshal_unrated_share` (percent scale, §2.4) = `= 0` / rows with
  non-missing marshal rating (`None` when no non-missing marshal ratings).
- `csat_avg` = mean of the **available** (non-`None`) dim avgs among the 4
  non-marshal dims; `None` when all four are `None`. Frozen per SPEC.

## 5. Edge-case table (must never raise)

| Input | Result |
|---|---|
| `[]` (any function) | rate/avg/`csat_avg` → `None`; counts `0`; nested bucket shares `None` |
| `delay_minutes` all `None` | `ota_pct None` (`n=0`), `delay_stats n=0, avg None` |
| All `total_trip_km == 0` | `cost_per_km None`, `zero_km_count = n`, `zero_km_share = 100.0` (percent scale) |
| All ratings `0` | dim `avg None`, `low_rating_share None`, `csat_avg None` |
| All ratings `None` | dim `avg None`, `n_rated 0`, `n_unrated 0`, `csat_avg None` |
| All `severity None` | `sev_breakdown unclassified share 1.0` (fraction scale), `sev1/sev2 = 0` |
| `trips_count` `0`/`None` | `alert_rate_per_1k None`, counts preserved |
| Outlier group n = 1 | `is_outlier False` for that row |
| `acknowledge_time None` | `unacknowledged_count++`, SLA share denominator keeps row |
| `start_time None` | row excluded from ack stats only (still in totals; still counts as unacknowledged when ack is `NULL`) |
| Negative ack delta | clamped to `0.0`, counted as met |
| Negative bills `total_trip_km` | excluded from `total_km`, not counted as zero-km |
| `NaN`/`inf` numerics | treated as missing (skipped) |

## 6. Test plan (test-first, per AGENTS.md)

- `backend/tests/test_analytics.py` — plain-dict fixtures shaped like
  `ops.py` columns (reuse Story 01 quirk values: `None` severity for
  `"False"`-as-null, `0` ratings, `0.0` km, `None` ack). No DB, no fixtures
  beyond inline rows. Minimum cases (SPEC §5) with frozen hand-computed
  vectors (headline `_share` fields assert percent scale per §2.4; nested
  bucket shares assert fraction scale):
  - `test_ota_boundary`: `[15 → on-time, 15.01 → late, 16 → late]`.
  - `test_ota_hand_computed`: 100 trips / 5 late → `{all: {n: 100,
    late_count: 5, ota_pct: 95.0}}`.
  - `test_ota_grouped`: two `vendor_id` values split `n`/`late_count`/`ota_pct`
    correctly; missing vendor → `"UNKNOWN"`.
  - `test_ota_empty_returns_none`: `[]` and all-`None` → `ota_pct None`.
  - `test_delay_avg_and_reason_mix`: 4 rows (`NODELAY 0, TRAFFIC 20,
    DRIVER 30, None 10`) → `avg 15.0`, shares `0.25` each (fractions).
  - `test_delay_all_none`: all-`None` delays → `n=0, avg None`, reason shares
    `None`.
  - `test_no_show_rate` (+ split): 10 legs / 2 `True` → `20.0`; grouped by
    `shift_type` splits correctly; disagreeing `boarding_status` label does
    not change the count; `1`/`"true"` do not count.
  - `test_cost_per_km_ignores_zero_km` + `test_zero_km_counted`: costs
    `[1000, 1200]`, km `[10, 0]` → `cost_per_trip 1100.0`,
    `cost_per_km 220.0`, `zero_km_count 1`, `zero_km_share 50.0` (percent);
    all-zero-km → `cost_per_km None`; negative-km bill excluded from
    `total_km`, not counted as zero-km.
  - `test_outlier_flagged`: exactly ten `1200` + one `16000` → threshold
    `15309.56` asserted (locks `pstdev` over sample `15932.56`) and only max
    flagged; single-row group → none flagged; input list unmutated.
  - `test_csat_excludes_zeros` + `test_low_rating_share` +
    `test_marshal_unrated`: dims with `0`s excluded from avgs; pooled
    `< 3` share hand-computed (percent scale); `marshal_unrated_share`
    (percent scale); all-`0` dims → `avg None`, `csat_avg None`; all-`None`
    dims → `n_rated 0, n_unrated 0`.
  - `test_alert_rate_and_unclassified_severity`: 3 alerts
    (`Sev-1`, `None`, `None` for `"False"`) with `trips_count=1000` →
    `3.0`, `sev1_count 1`, `unclassified` count 2 share `0.67` (fraction);
    zero trips → rate `None`; `[]` → counts `0`, shares `None`.
  - `test_ack_sla`: ack 10 min → met, 40 min → missed, `None` → unacked →
    `ack_sla_met_share 33.33` (percent), `unacknowledged_count 1`.
  - `test_ack_negative_clamped_and_start_none`: negative delta → `0.0`/met;
    `start_time None` row excluded from ack stats but kept in totals.
  - `test_nan_inf_skipped`: `NaN`/`inf` `delay_minutes`/`trip_cost` behave
    like `None`.
- Flow: write tests → run from `backend/`: `uv run pytest
  tests/test_analytics.py` confirms **red** → implement → green. Then full
  `uv run pytest` + `uv run ruff check .` from `backend/`, loop until green.
- Full-dataset calibration is **not** a unit test (same rule as Story 01):
  PLAN §2 anchors checked manually later during mart validation.

## 7. Acceptance mapping (SPEC §4)

1. Each KPI ≥ 1 hand-computed test → §6 vectors (grouped OTA `{all: {n:
   100, late_count: 5, ota_pct: 95.0}}` example incl.).
2. Edge cases → §5 table; every row covered by at least one test in §6
   (map: `[]` → empty tests; all-`None` delays → `test_delay_all_none`;
   all-zero-km → cost tests; all-`0`/all-`None` ratings → csat tests;
   all-`None` severity → alert test; `trips_count` 0 → alert test; n=1
   outlier → outlier test; ack/start `None` → ack tests; negative bills km
   → cost tests; `NaN`/`inf` → `test_nan_inf_skipped`).
3. `ruff` clean; one KPI per function, each < ~40 lines → §3 layout +
   §2.2; verify with `uv run ruff check .` and line-count review.
4. No forbidden imports → §2.8 guard command.

## 8. Files to touch (final list)

- New: `backend/src/backend/core/analytics.py`,
  `backend/tests/test_analytics.py`.
- Reuse (read-only): `models/ops.py` (key names), Story 01 quirk fixtures
  (input shapes). Do not modify models, ingest, `normalize.py`, or
  `database.py`.
- Untouched: `api/*`, frontend, `core/config.py`, `core/database.py`,
  existing `health/ready/examples` routes.

## 9. Risks

- **SPEC rounding precision unspecified** — frozen at 2 decimals here (§2.3)
  with the §2.4 per-field scale table; if Story 03/04 need different display
  precision, they format at the edge (cf. Story 04 SPEC §3: 1-decimal `%`),
  never re-round the stored value.
- **`pstdev` vs `stdev` outlier scaling** — frozen as population stdev
  (§2.7, threshold `15309.56` on the frozen fixture); with real vendor groups
  (n ≫ 30) the difference is negligible, but the choice matters for tiny
  test groups, hence the threshold assertion.
- **Negative ack deltas** — clamped to `0.0`/met (§4.6); alternative
  (drop row) would undercount volume, violating flag-never-drop.
- **`cost_per_km` numerator scope** — sums all finite costs regardless of
  slab/contract nulls. Slab grouping is out of scope here (no
  `group_key="slab_name"` support); `UNSLABBED` display + `UNSLABBED`/zero-km
  counts in the vendor table are a Story 04 concern (Story 04 SPEC §3.4).
- **Mart writer unowned until Story 04** — if Story 04's build disputes that
  placement, revisit then; Story 02's dict shapes (§4) are the writer's input
  contract either way.

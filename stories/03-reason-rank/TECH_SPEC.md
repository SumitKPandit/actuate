# Story 03 — Technical Spec: Reasoning + Ranking (`core/reason.py`)

Companion to `SPEC.md`. Build blueprint: input contracts, exact function
signatures, frozen thresholds, severity/action maps, and test vectors.
Derived from `PLAN.md` §3/§4, `stories/README.md`, Story 02 contracts
(`core/analytics.py`, `TECH_SPEC.md`), Story 04/08 downstream shapes
(`api/ops.py` SPEC, `triggers` SPEC), and the backend scaffold
(`pyproject.toml`, `models/marts.py`).

Decisions locked with the user (2026-09-06): `max_trip_cost` is added to the
marts (Story 04 writer populates it; Story 03 only reads it); CSAT MoM uses
`low_rating_share` only; cost-sanity `reach_trips` is `1`; `build_insights`
keeps every firing reason as a separate insight (no dedupe).

## 1. Evidence summary

- **Story 02 is done and is the only KPI contract.**
  `backend/src/backend/core/analytics.py:1-240` is pure row-in/dict-out,
  stdlib only (`math`, `statistics`, `datetime`), no `pandas`, no DB/HTTP/LLM.
  Shapes `reason.py` consumes verbatim:
  - `ota_pct` → `{group: {n, late_count, ota_pct}}` (percent 0–100, `None`
    on empty; late = `delay > 15.0` strictly, `analytics.py:60`).
  - `delay_stats` → `{n, late_count, avg_delay_min, reason_mix}` (mix shares
    0–1 fractions, **late-only**: `count / late_count`, `None` when
    `late_count == 0`).
  - `no_show_stats` → `{legs, no_shows, no_show_pct}` (percent; strict
    `is True` count).
  - `cost_stats` → `{billed_trips, total_cost, total_km, cost_per_trip,
    cost_per_km, zero_km_count, zero_km_share}` (`cost_per_km None` on
    all-zero-km; negative bills km excluded, not counted as zero-km).
  - `flag_cost_outliers` → per-group `mean + 3 * pstdev`
    (`statistics.pstdev`, n ≥ 2, sd ≠ 0 else no flag; `analytics.py:144-145`).
  - `alert_stats` → `{alerts, trips, alert_rate_per_1k, sev1_count,
    sev2_count, sev_breakdown, avg_ack_minutes, ack_sla_met_share,
    unacknowledged_count}` (`"False"`-as-null already `None` upstream).
  - `csat_stats` → `{per_dim, low_rating_share, marshal_unrated_share,
    csat_avg}` (percent scales for `low_rating_share`; marshal excluded
    from pool; `csat_avg` = mean of available non-marshal dims).
  - Rounding frozen at `_r2` (2 decimals, `None`-safe, non-finite → `None`);
    counts stay `int`. Story 03 reuses `_r2` semantics, never re-rounds.
- **Marts already exist, rows owned elsewhere** (`models/marts.py:11-59`):
  `daily_kpi {date, trips, delayed_trips, sev1_count, ota_pct,
  avg_delay_min, no_show_rate, cost_per_trip, alert_rate_per_1k, csat_avg}`,
  `vendor_kpi {vendor, cycle_or_month, trips, ota_pct, cost_per_trip,
  cost_per_km, alert_rate_per_1k, csat_avg, low_rating_share}`,
  `office_kpi` (same keys by `office`), `insight_cache {key,
  payload_json, computed_at}`. Story 03 reads **plain dicts/lists shaped
  like these rows** — it never imports `database`, never queries, never
  writes `insight_cache` (Story 04 owns persistence/caching, max age 6h).
  One addition (user decision, Story 04 implements): `daily_kpi` gains
  `max_trip_cost` (per-cycle `max(bills.trip_cost)`), which is the single
  source for the cost-sanity check (§4.1). Story 03 does not migrate models.
- **Downstream contracts that constrain this spec:**
  - Story 04 `GET /insights` returns the ranked exception list **in
    `reason.py` order**; `GET /briefing` takes `insights_top5` +
    `actions_top3` derived from it; `GET /vendors` shows peer rank +
    `contribution_share`; `GET /actions` flattens `recommended_action` +
    `owner` into copy text (≤ 500 chars).
  - Story 08 `core/triggers.py` is a **thin wrapper over `reason.py` — no
    duplicated thresholds**. Its three rules pin primitives this spec must
    expose with identical math: Sev-1 spike = `> mean + 2σ` (or `> 2×
    prior` if < 14 points); OTA drop = `< 95 AND Δ ≤ −2pp` vs prior; cost
    outlier = vendor `cost_per_trip > mean + 3σ` within cycle **or** any
    trip `> ₹16k` sanity flag (PLAN max observed ~16k, `PLAN.md` §2).
    Note: `reason.py` emits the OTA halves (`vs_sla` + `vs_prior`) as
    separate insights; the Story 08 wrapper composes the `AND` — there is
    no combined OTA-drop insight in this module.
- **Backend constraints** (`backend/pyproject.toml`): no `pandas`
  dependency (deps are fastapi/pydantic/sqlalchemy-centric; full list in
  `pyproject.toml`). `pytest` runs with `pythonpath = ["src"]`; commands
  run from `backend/`: `uv run pytest tests/test_reason.py`, then
  `uv run pytest` + `uv run ruff check .`. `core/database.py`
  (engine/session/`Base`) must not be imported — SPEC §6 bans DB/API/UI
  touches; SPEC §3.6 bans LLM, I/O, and `datetime.now()` inside logic.
- **Calibration anchors** (`PLAN.md` §2 — sanity only, never fixtures):
  OTA ~93–97%; cost median ~1236, mean ~1394, max ~16k; Sev-1 = 656;
  feedback avg ~4.85. Tests use tiny hand-computed fixtures, not these.

## 2. Design decisions

1. **Aggregates-in, insights-out, no I/O.** Every public function takes
   plain `dict`/`list`/`float`/`int`/`str`/`None` (mart-shaped dicts or
   `analytics.py` outputs) and returns plain JSON-serializable
   `dict`/`list`. No ORM objects required (accept `Mapping` via `_get`
   fallback like Story 02, but tests pass dicts). No file/DB/network
   access, no LLM SDK, no `datetime.now()` — callers pass `as_of`
   (`datetime | str | None`, opaque, stored nowhere, only threaded for
   testability per SPEC §3.6).
2. **One `BENCHMARKS` dict owns every tuning number.** All thresholds,
   sigmas, minima, sanity caps, and severity weights live in a single
   module-level `BENCHMARKS` constant, importable by API/docs (`from
   backend.core.reason import BENCHMARKS`). Helpers read tuning numbers
   from `BENCHMARKS`, never from literals. Frozen contents (§3.1); Story
   08 imports this dict, never copies it. Mechanical constants are
   **exempt** from this rule and need no dict entry: `100` (percent
   scaling), `2` (decimal places, only inside `_r2`), `2` (top-2 count),
   `0`/`1` (defaults, comparisons, `reach = 1` for the sanity flag).
3. **One anomaly family per function, <40 lines each.** Seven public
   functions (§4): absolute, MoM-delta, peer, z-score, contribution, rank,
   plus one thin `build_insights` orchestrator. No per-vendor/per-office
   special cases — caller passes rows/splits/series; scope is data.
4. **Stable `Insight` schema, deterministic IDs and order.** Output keys
   exactly per SPEC §3 (frozen names/types, §3.2). `id` is a slug of
   `{kpi}_{reason}_{cycle}_{scope}` where scope is `v_<vendor>` /
   `o_<office>` / `all` (lowercased, non-alnum → `_`; the `v_`/`o_`
   prefix is what keeps a vendor and an office with the same name
   distinct). SPEC's example id (`ota_drop_jun`) is illustrative only;
   this scheme is frozen. Ranking sorts by `(-score, -abs(delta), id)` —
   the trailing `id` tie-break is what makes "same input, same order"
   total (SPEC §3.4 ties on `|delta|` alone leave order undefined when
   deltas also tie). `build_insights` keeps **every** firing reason as a
   separate insight (OTA absolute + MoM + peer can coexist with distinct
   `id`s/reasons/baselines — user decision; no dedupe).
5. **Scale convention (frozen).** Percent-scale KPIs (0–100): `ota_pct`,
   `no_show_rate`, `low_rating_share`, `ack_sla_met_share`,
   `alert_rate_per_1k` is a per-1k rate (raw difference, **not** pp —
   see MoM table). `current`, `baseline`, `delta_pp` mirror the KPI's own
   scale: **rates → raw difference** (`current − baseline`, pp for true
   percents, minutes for `avg_ack_minutes`, points-per-1k for alert
   rate); **costs → percent change** (`100 * (current − baseline) /
   baseline`, `None` when baseline 0/`None`) stored in the `delta_pp`
   field (SPEC fixes the field name; this documents its dual meaning).
   `csat_avg` (1–5 stars) is **excluded from MoM by design** (user
   decision): a `2.0` threshold on a 1–5 scale (4.85 → 2.85 to fire)
   would never trigger — CSAT trend rides `low_rating_share` instead,
   while `csat_avg` still gets peer + z-score coverage (z is
   scale-free). `contribution_share` is always 0–1 fraction
   (`_r2`-rounded). `reach_trips` is always `int`.
6. **`None` means "no data", never `0.0`.** Any missing `current`/`baseline`
   → that check emits nothing (skip, never an insight with `None`
   arithmetic). Zero denominators (`reach 0`, `baseline 0` for pct change,
   zero total excess) → `None` share/delta, no crash.
7. **Population stdev everywhere.** z-score and cost-outlier both use
   `statistics.pstdev` (consistent with `flag_cost_outliers`; defined for
   n ≥ 2, stable on tiny fixtures). `statistics.stdev` (sample) is
   rejected — it would flag differently on small vendor groups and break
   Story 08 reuse. n < 2 or sd == 0 → no flag. Missing `cycle` never
   raises either — it slugs as `"unknown"`.
8. **Severity and action are maps, not prose.** Severity follows the §3.3
   table (complete if/else per check, never invented strings);
   `ACTION_MAP` (§3.4) is a module dict; logic looks up, never invents
   strings. Owner ∈ `{"vendor", "office", "ops"}` (role, not name —
   `scope.vendor`/`scope.office` disambiguates which vendor/office;
   SPEC §3's `"vendor|X|office|ops"` header is read as roles, matching
   PLAN §4 decision→owner table and Story 04 `GET /actions` shape).
9. **No new dependencies, no forbidden imports.** Stdlib only (`math`,
   `statistics`). CI guard (matches `import x` / `from x import …` forms
   only so prose can't trip it):
   `rg "^\s*(import|from)\s+.*(database|fastapi|httpx|openai|sarvam)" backend/src/backend/core/reason.py`
   must return nothing, and
   `rg "datetime\.now|time\.time|os\.|open\(" backend/src/backend/core/reason.py`
   must return nothing (`as_of` is the only time input).

## 3. Module layout (`backend/src/backend/core/reason.py`)

```text
"""Deterministic Reason+Ranks — benchmarks, anomalies, contribution, ranking (Story 03). See stories/03-reason-rank/SPEC.md."""

BENCHMARKS = {...}        # §3.1 — the single threshold source
ACTION_MAP = {...}        # §3.4 — (recommended_action, owner) per kpi
KPI_IDS = (...)           # ("ota_pct","sev1","ack","cost","csat","no_show")
REASONS = ("vs_sla","vs_prior","vs_peer","anomaly")

_r2(x)                    # None-safe round(x,2); non-finite -> None (same semantics as analytics.py)
_get(row, key, default)   # Mapping-or-object fallback (same as analytics.py)
_slug(s)                  # lower, non-[a-z0-9]+ -> "_", for stable insight ids
_score(severity, reach)   # BENCHMARKS weights × reach_trips
_peer_splits(rows, field, name_key)  # mart rows -> [{key, value, trips}], finite values only

check_absolute(snapshot, *, cycle, vendor_rows=None, as_of=None) -> list[Insight]
check_mom_delta(current, prior, *, cycle, scope=None, allow_sev1_fallback=True, as_of=None) -> list[Insight]
check_peer(splits, *, kpi, cycle, dim, as_of=None) -> list[Insight]
check_zscore(series, *, kpi, scope, cycle, as_of=None) -> dict  # {insights, skipped, reason_skipped?, kpi, n}
contribution_top2(splits) -> dict  # {top2: [...], contribution_share: float|None}
rank_insights(insights) -> list[Insight]
build_insights(*, snapshot, prior=None, vendor_rows=None, office_rows=None,
               delay_splits=None, daily_series=None, cycle, as_of=None) -> list[Insight]
```

### 3.1 `BENCHMARKS` (frozen — implement exactly)

```python
BENCHMARKS = {
    "ota_sla_pct": 95.0,          # SPEC §3.1; Story 04 /overview benchmarks.ota_sla mirrors this
    "ack_sla_min": 30.0,          # SPEC §3.1; single owner for reason/triggers (analytics.ACK_SLA_MIN stays 30.0 upstream — joint update if ever changed)
    "rate_delta_pp": 2.0,         # SPEC §3.2 MoM freeze: |Δ| > 2 flags for rate-family
    "cost_delta_pct": 10.0,       # SPEC §3.2 MoM freeze: |Δ| > 10% flags for costs
    "z_thresh": 2.0,              # SPEC §3.2: |z| > 2
    "z_min_points": 14,           # SPEC §3.2: < 14 points -> skip with reason_skipped
    "sev1_spike_sigma": 2.0,      # Story 08 reuse: sev1 > mean + 2*pstdev
    "sev1_spike_prior_mult": 2.0, # Story 08 reuse: > 2x prior when < 14 points
    "cost_outlier_sigma": 3.0,    # Story 08 reuse + analytics parity: mean + 3*pstdev
    "cost_sanity_max": 16000.0,   # Story 08 reuse: any trip > 16k (PLAN §2 max observed)
    "severity_weights": {"high": 3, "medium": 2, "low": 1},  # SPEC §3.4 freeze
}
```

No other numeric **tuning** constants permitted (mechanical `100` / `_r2`
`2` / top-`2` / `0`/`1` exempt per §2.2). CSAT-star-average, no-show and
alert-rate **absolute** thresholds are intentionally **absent**: those KPIs
flag via MoM-delta (§4.2), peer-worst-rank (§4.3), or z-score (§4.4) only —
adding absolute cutoffs would contradict SPEC's frozen threshold list and
PLAN's trend+peer benchmarks for those rows. (OTA/ack/cost-sanity absolutes
live in §4.1.)

### 3.2 `Insight` schema (frozen names/types)

```python
{
  "id": "ota_pct_vs_sla_2026_06_h2_all",  # str, stable slug (§2.4)
  "kpi": "ota_pct",                     # one of KPI_IDS
  "scope": {"vendor": "X"|None, "office": None|str, "cycle": "2026-06-H2"},
  "current": 93.0,                      # float | None (KPI native scale)
  "baseline": 95.0,                     # float | None (SLA / prior / peer-mean / series-mean)
  "delta_pp": -2.0,                     # float | None (raw diff for rates, % for costs per §2.5)
  "severity": "high|medium|low",
  "reach_trips": 12000,                 # int
  "contribution_share": 0.42,           # float 0-1 | None (top-2 excess share, §4.5)
  "reason": "vs_sla|vs_prior|vs_peer|anomaly",
  "recommended_action": "...",          # from ACTION_MAP, never free text
  "owner": "vendor|office|ops",         # role per §2.8
}
```

`id = _slug(f"{kpi}_{reason}_{cycle}_{scope}")` with scope =
`f"v_{vendor}"` if vendor set, elif `f"o_{office}"` if office set, else
`"all"`; `cycle None`/empty slugs as `"unknown"` (never raise). Each check
sets `recommended_action`/`owner` from `ACTION_MAP[kpi]` at creation.

z-score skip returns **no insight** plus a skip marker (never a
false-positive insight): `{"insights": [], "skipped": True,
"reason_skipped": "zscore_needs_14_points", "kpi": ..., "n":
<len(series)>}` from `check_zscore` (§4.4); `build_insights` drops skips
from the ranked list (SPEC acceptance: "returns empty with skip flag" is
asserted via direct `check_zscore` calls).

### 3.3 Severity map (frozen)

| Condition | severity | Rationale |
|---|---|---|
| OTA `current < ota_sla_pct` (§4.1) | `high` | SPEC acceptance fixture (93 vs 95 → high) |
| Sev-1 spike fired (§4.2/§4.4) | `high` | Safety; matches Story 08 trigger gravity |
| Cost sanity `trip > cost_sanity_max` (§4.1) | `high` | Real-money data-quality breach |
| Ack `avg_ack_minutes > ack_sla_min` (§4.1) | `high` | SLA breach, same class as OTA |
| MoM-delta fired (§4.2) — except Sev-1 | `medium` | Trend breach, needs context not siren |
| Peer worst-rank fired (§4.3) | `medium` | Relative, not absolute, failure |
| z-score `\|z\| > z_thresh` (§4.4, non-sev1) | `medium` | Statistical anomaly, confirm before act |
| Cost-outlier `> mean + 3σ` (§4.1) | `medium` | Vendor-level money flag (sanity flag above is `high`) |
| Fallback (unreachable while maps complete) | `low` | Keeps ranking total; `low` weight 1 is currently dead weight by design |

### 3.4 `ACTION_MAP` (verbatim strings from SPEC §3.5 — implement exactly)

```python
ACTION_MAP = {
    "ota_pct": ("Re-route / add buffer + vendor penalty review", "vendor"),
    "sev1":    ("Acknowledge open Sev-1s + escort audit", "ops"),
    "ack":     ("Acknowledge open Sev-1s + escort audit", "ops"),
    "cost":    ("Hold bill line + verify km slab", "ops"),
    "csat":    ("Driver/cab review with vendor", "vendor"),
    "no_show": ("Shift reminder + standby cab", "office"),
}
```

`ack` reuses the Sev-1 action (both are acknowledge-and-audit safety work;
SPEC lists five entries, this adds the sixth key without new prose).
Unknown `kpi` → `KeyError` is forbidden; helpers only emit `KPI_IDS` keys.

### 3.5 KPI map (frozen — which mart/analytics field feeds which `kpi`)

| `kpi` | MoM fields (§4.2) | Peer metric from mart rows (§4.3) | Daily-series metric (§4.4) |
|---|---|---|---|
| `ota_pct` | `ota_pct` (rate) | `ota_pct`, flag **min** | `ota_pct`, flag `z < −thresh` |
| `sev1` | `sev1_count` (spike `>2×`) | — (no mart field; skip) | `sev1_count`, flag `z > +thresh`, `high` |
| `ack` | `alert_rate_per_1k`, `avg_ack_minutes` (rate-like) | `alert_rate_per_1k`, flag **max** | `alert_rate_per_1k`, flag `z > +thresh` |
| `cost` | `cost_per_trip`, `cost_per_km` (percent) | `cost_per_trip`, flag **max** | `cost_per_trip`, flag `z > +thresh` (delta = % vs mean) |
| `csat` | `low_rating_share` only (rate); `csat_avg` **skipped** (§2.5) | `low_rating_share`, flag **max** | `csat_avg`, flag `z < −thresh` (z is scale-free) |
| `no_show` | `no_show_rate` (rate) | — (no mart field; skip) | `no_show_rate`, flag `z > +thresh` |

`no_show_rate` (marts/daily) and `no_show_pct` (analytics) are the same
percent-scale metric under two names — accept either key on input, emit
`kpi="no_show"`.

## 4. Function contracts

Inputs are **mart/analytics-shaped plain data**. Field names below match
`models/marts.py` + `analytics.py` outputs so Story 04's mart reader can
pass rows straight through. All numeric inputs skip `None`/`NaN`/`inf`
(`math.isfinite` guard); `bool` never counts as numeric.

### 4.1 `check_absolute(snapshot, *, cycle, vendor_rows=None, as_of=None) -> list[dict]`

- `snapshot`: `{trips, ota_pct, avg_ack_minutes, max_trip_cost}` (daily_kpi-shaped
  plus the new `max_trip_cost` mart field Story 04 populates per cycle) — each
  optional; missing/`None` → that sub-check skips silently. (`sev1_count` is
  deliberately **not** read here.)
- `vendor_rows`: list of vendor_kpi-shaped `{vendor, cost_per_trip, trips}` for
  the vendor-outlier sub-check; `None`/empty → that sub-check skips.
- Fires (each at most one insight per vendor/global key):
  - OTA: `ota_pct is not None and ota_pct < BENCHMARKS["ota_sla_pct"]` →
    `kpi="ota_pct"`, `reason="vs_sla"`, `baseline=ota_sla_pct`,
    `delta_pp=_r2(current−baseline)`, severity `high`,
    `reach_trips=snapshot["trips"] or 0`.
    Boundary: exactly `95.0` → **no insight** (strict `<`).
  - Ack: `avg_ack_minutes is not None and avg_ack_minutes >
    BENCHMARKS["ack_sla_min"]` → `kpi="ack"`, `reason="vs_sla"`,
    `baseline=ack_sla_min`, `delta_pp=_r2(current−baseline)`, severity
    `high`, `reach_trips=snapshot["trips"] or 0`. Exactly `30.0` → none.
  - Cost sanity: `max_trip_cost is not None and max_trip_cost >
    BENCHMARKS["cost_sanity_max"]` → `kpi="cost"`, `reason="anomaly"`
    (a sanity cap is not an SLA), `baseline=cost_sanity_max`,
    `delta_pp`= percent over baseline (`100*(cur−base)/base`, `_r2`),
    severity `high`, `reach_trips=1` (user decision — one bad row must not
    outrank systemic breaches). Exactly `16000.0` → none.
  - Cost outlier (vendor-level, Story 08 reuse): finite `cost_per_trip`
    values from `vendor_rows`; if len ≥ 2 and `pstdev ≠ 0`, limit =
    `mean + cost_outlier_sigma * pstdev`; each vendor above limit → one
    `kpi="cost"`, `reason="anomaly"`, `baseline=_r2(limit)`,
    `delta_pp`= percent over limit (`_r2`), severity `medium`,
    `scope.vendor` set, `reach_trips` = that vendor's `trips` or `0`.
    n < 2 or sd == 0 → none. (Single-outlier tiny groups rarely fire under
    `3σ` — by design, same conservatism as `flag_cost_outliers`; §6 freezes
    an 11-vendor vector that does fire.)
  - Sev-1 absolute path is **not here** — Sev-1 fires via MoM-fallback
    (§4.2) or z-score (§4.4) only, so Story 08's two-branch definition has
    one implementation each and no competing absolute count threshold.
- `scope` = `{vendor: None, office: None, cycle}` except vendor cost
  outliers (vendor set). `contribution_share` left `None` here;
  `build_insights` fills it via §4.5. `as_of` accepted, ignored (signature
  parity for testability).

### 4.2 `check_mom_delta(current, prior, *, cycle, scope=None, allow_sev1_fallback=True, as_of=None) -> list[dict]`

- `current`/`prior`: snapshot dicts with any of `{ota_pct,
  no_show_rate/no_show_pct, low_rating_share, alert_rate_per_1k,
  cost_per_trip, cost_per_km, sev1_count, avg_ack_minutes, trips}`.
  `csat_avg` is accepted on input but **skipped by design** (§2.5).
- Rate family (`ota_pct`, `no_show_rate`, `low_rating_share`,
  `alert_rate_per_1k`, `avg_ack_minutes` as raw minutes): flag iff both
  finite and `abs(current − prior) > BENCHMARKS["rate_delta_pp"]`
  (**strict `>`**; exactly 2.0 → no flag). Follows SPEC's `|Δ|` (both
  directions flag — an improvement also emits, matching the freeze).
  `delta_pp = _r2(cur − prior)`, `baseline = prior`, `reason="vs_prior"`,
  severity `medium`. `kpi` per §3.5.
- Cost family (`cost_per_trip`, `cost_per_km`): flag iff prior finite/nonzero
  and `abs(100*(cur−prior)/prior) > BENCHMARKS["cost_delta_pct"]`
  (strict `>`; exactly 10% → no flag). `delta_pp` stores the **percent**
  change (`_r2`), `baseline = prior`, `reason="vs_prior"`, severity
  `medium`, `kpi="cost"`. Prior `0`/`None` → skip (never divide-by-zero).
- Sev-1 small-series fallback (Story 08 reuse, frozen): evaluated **only**
  when `allow_sev1_fallback is True` (`build_insights` passes `False` when
  `daily_series` holds a ≥14-point finite `sev1` series, so the large-series
  branch in §4.4 owns those cycles and the two branches never overlap):
  flag iff `prior` finite and `current > sev1_spike_prior_mult * prior`
  (i.e. `> 2× prior`). `prior == 0` → flag iff `current > 0` (any Sev-1
  from clean prior is a spike). `reason="vs_prior"`, `kpi="sev1"`,
  severity `high`, `delta_pp = _r2(current − prior)` (count delta).
- `reach_trips` = `current.get("trips") or 0`. `scope`: `None` → global
  `{vendor: None, office: None, cycle}`; otherwise caller passes
  `{"vendor": X}` / `{"office": Y}` and it is echoed with `cycle`.

### 4.3 `check_peer(splits, *, kpi, cycle, dim, as_of=None) -> list[dict]`

- `splits`: `[{key, value, trips}]` where `key` is vendor/office name,
  `value` the KPI number, `trips` reach. Finite `value` only; `None`/`NaN`
  rows skipped (never ranked). `dim` is **required**: `"vendor"` sets
  `scope.vendor`, `"office"` sets `scope.office`.
- Flags the **worst-1** performer iff n ≥ 2 and the worst value differs from
  the group **mean-of-all** by more than the MoM threshold for its family —
  direction per §3.5 (`ota_pct`: `mean − worst > rate_delta_pp`;
  `cost`/`ack`/`csat`: worst is the max; rates `worst − mean >
  rate_delta_pp`, costs percent over mean > `cost_delta_pct`). Mean-of-all
  is frozen (note: for n = 2 the gap is halved, so a 4pp spread is needed
  to fire — accepted strictness). Prevents flagging healthy tight groups
  (e.g. all vendors 99.1–99.3 OTA → no peer insight).
- Output: at most one insight, `reason="vs_peer"`, `baseline=_r2(mean)`,
  `delta_pp` per §2.5 convention, severity `medium`,
  `reach_trips` = worst row's trips. `kpi` ∈ `KPI_IDS`.

### 4.4 `check_zscore(series, *, kpi, scope, cycle, as_of=None) -> dict`

- `series`: list of daily finite floats (oldest → newest) in the §3.5
  canonical metric for `kpi`; non-finite entries dropped before counting.
  `scope`: `{vendor, office, trips}`-ish dict (only `trips` is read for
  reach; vendor/office echoed into the insight scope).
- `len(series) < BENCHMARKS["z_min_points"]` (14) → return exactly
  `{"insights": [], "skipped": True, "reason_skipped":
  "zscore_needs_14_points", "kpi": kpi, "n": len(series)}`. **Never a
  false positive** (SPEC acceptance).
- Else: `mean = statistics.mean(series)`, `sd = statistics.pstdev(series)`;
  sd == 0 → return exactly `{"insights": [], "skipped": False, "kpi":
  kpi, "n": len(series)}` (flat series carries no signal). Else `z =
  (series[-1] − mean) / sd`; flag iff `abs(z) > BENCHMARKS["z_thresh"]`
  (strict `>`; exactly 2.0 → no flag).
  - Direction guard (frozen, §3.5): `ota_pct`/`csat` fire only on
    `z < −thresh`; `sev1`/`ack`/`cost`/`no_show` only on `z > +thresh`.
    Prevents celebrating a good outlier as an exception.
  - Fired insight: `reason="anomaly"`, `baseline=_r2(mean)`,
    `current=series[-1]`, `delta_pp` per §2.5 (costs: percent vs mean,
    `None` when mean is 0; else `_r2(current−baseline)`), severity per
    §3.3 (`sev1` → `high`, else `medium`), `reach_trips` from `scope`
    trips or `0`. Return `{"insights": [insight], "skipped": False,
    "kpi": kpi, "n": len(series)}`.
- Sev-1 large-series branch (Story 08 reuse, frozen): `sev1` series with
  ≥ 14 points firing iff `last > mean + sev1_spike_sigma * pstdev` is
  **the same computation** as the directional z-check above (σ = 2) —
  implementation **must** delegate to the same z-math (no second stdev
  call path); the raw-count form exists only so trigger logs read
  naturally.

### 4.5 `contribution_top2(splits) -> dict`

- `splits`: `[{key, trips, late_count}]` (delay/no-show splits for the
  degraded cycle — **field name is `late_count`** everywhere, matching
  `delay_stats`). Rows with missing/non-finite counts or `trips == 0`
  skipped. Scope is delay/no-show attribution only (the generic
  cost-over-budget reuse is dropped — no budget threshold exists in
  `BENCHMARKS`).
- `overall_rate = total_late / total_trips`; total `0` → return
  `{"top2": sorted-rows-with-None-shares, "contribution_share": None}`
  (never raise). Per row: `expected = trips * overall_rate`, `excess =
  max(0.0, late_count − expected)`. Sort by `excess` desc, take top
  `min(2, n)` (n = 1 → single-entry `top2`).
- Returns `{"top2": [{"key":..., "excess": _r2, "share": 0–1|None}],
  "contribution_share": _r2(sum(top2 excess) / sum(all excess)) | None}`.
  Zero total excess → `contribution_share None`, `top2` still returned
  (sorted, shares `None`) so callers can distinguish "no gap to attribute"
  from "no data". Shares independently `_r2`-rounded (drift OK, same rule
  as Story 02 §2.3 — tests assert individual shares, never the total).

### 4.6 `rank_insights(insights) -> list[dict]`

- Pure sort, no filtering: `key = (−_score(severity, reach_trips),
  −abs(delta_pp or 0), id or "")`. Weights from
  `BENCHMARKS["severity_weights"]`. `reach_trips None` → `0`.
  `delta_pp None` → `0` for tie-break only (stored value untouched).
  Missing `id` → `""` (sorts first; `build_insights` always sets `id` so
  this only affects hand-built unit fixtures — documented, frozen).
- Returns a **new list** (input unmutated; same dict objects, reordered).
  Stability is by construction (total key — no input-order dependence), so
  "same input, same order" holds across runs/processes without seeding.
- Worked freeze (SPEC §5 `test_ranking_severity_x_reach` vector): insights
  `[{sev medium, reach 12000}, {sev high, reach 100}]` → medium first
  (24000 > 300). Test asserts exact `id` order.

### 4.7 `build_insights(*, snapshot, prior=None, vendor_rows=None, office_rows=None, delay_splits=None, daily_series=None, cycle, as_of=None) -> list[dict]`

- Thin orchestrator (no thresholds of its own — reads `BENCHMARKS` only
  via callees), fixed order: §4.1 (with `vendor_rows` for the outlier
  sub-check) → §4.2 (with `allow_sev1_fallback = not
  _has_long_series(daily_series, "sev1")`, scope global) → §4.3 (peer per
  §3.5 metric from `vendor_rows` then `office_rows`; KPIs without a mart
  field skip silently) → §4.4 (each `kpi: series` in `daily_series`).
  `daily_series` keys are `KPI_IDS`, values the §3.5 canonical metric.
- Fills `contribution_share` on `ota_pct`/`no_show` insights from
  `delay_splits` via §4.5 (`None` when splits absent/empty/gapless; cost
  insights keep `None` — no cost attribution input exists); stamps `id`
  via `_slug`; sets `recommended_action`/`owner` at creation per §3.4;
  keeps **all** firing reasons (no dedupe, §2.4); then `rank_insights`.
  Drops z-score skip markers from the ranked list (caller can re-run
  `check_zscore` directly when it needs the skip flag — acceptance test
  does exactly this).
- `snapshot`/`cycle` required but never raise: missing `trips` → reach
  `0`; `cycle None`/empty → slug `"unknown"`. All other optionals
  `None`/empty → skipped; all-`None` optionals → `[]`. `as_of` threaded
  to callees, never `now()`.

## 5. Edge-case table (must never raise)

| Input | Result |
|---|---|
| `snapshot` empty / all KPIs `None` | `[]` (every sub-check skips) |
| `cycle` `None`/empty | slug `"unknown"`, never raise |
| OTA exactly `95.0` / ack exactly `30.0` / sanity exactly `16000.0` | no insight for that sub-check (strict `>`/`<`) |
| MoM rate `\|Δ\|` exactly `2.0` | no flag (strict `>`) |
| MoM cost `\|Δ\|` exactly `10%` | no flag (strict `>`) |
| `csat_avg` moves, `low_rating_share` flat | no CSAT MoM insight (`csat_avg` skipped by design) |
| z-score exactly `\|z\| == 2.0` | no flag (strict `>`) |
| `series` < 14 points | `insights []`, `skipped True`, `reason_skipped "zscore_needs_14_points"` |
| `series` all-equal (sd == 0) | `insights []`, `skipped False` |
| `series` with `None`/`NaN`/`inf` | dropped before counting (may cause <14 → skip path) |
| Good-direction outlier (OTA spike up) | no flag (direction guard) |
| Cost `prior == 0` / `None` | MoM cost skips (never divide-by-zero) |
| Sev-1 `prior == 0`, `current > 0` | spike fires when fallback allowed (any-from-clean is a spike) |
| Sev-1 fallback when long series exists | suppressed (`allow_sev1_fallback=False` from `build_insights`) |
| Peer n < 2 / tight group within threshold | no peer insight |
| Peer rows with `None` values / all-`None` | skipped, remaining ranked; none left → no insight |
| Peer `kpi` with no mart field (`sev1`/`no_show`) in `build_insights` | skipped silently |
| Zero total excess in `contribution_top2` | `contribution_share None`, `top2` still sorted |
| `splits`/`rows` empty or `None` | `contribution_share None` / sub-check skips |
| `reach_trips None` | treated as `0` in ranking only |
| `NaN`/`inf` numerics anywhere | treated as missing (skipped) |
| Ranking tie on score + `\|delta\|` | `id` asc decides (total order, input-order independent) |

## 6. Test plan (test-first, per AGENTS.md)

`backend/tests/test_reason.py` — plain-dict fixtures shaped like §4
(mart/analytics-shaped, **not** full-dataset rows). No DB, no fixtures
beyond inline dicts/lists. Frozen hand-computed vectors:

- `test_ota_breach_vs_sla`: `snapshot {trips: 12000, ota_pct: 93.0}`,
  `cycle "2026-06-H2"` → one insight, `kpi ota_pct`, `baseline 95.0`,
  `delta_pp −2.0`, `severity high`, `reason vs_sla`, action/owner per
  `ACTION_MAP["ota_pct"]`, `id "ota_pct_vs_sla_2026_06_h2_all"`.
- `test_no_breach_when_above_sla`: `ota_pct 96.5` → `check_absolute`
  emits no `ota_pct` insight (`[]` when snapshot holds only OTA);
  ack `30.0` → none; sanity `16000.0` → none.
- `test_ack_breach`: `avg_ack_minutes 35.0` → `kpi ack`, `baseline 30.0`,
  `delta_pp 5.0`, `severity high`, `reason vs_sla`.
- `test_cost_sanity`: `max_trip_cost 16500.0` → `kpi cost`,
  `reason anomaly`, `baseline 16000.0`, `delta_pp 3.12`
  (`100*500/16000 = 3.125 → 3.12`), `severity high`, `reach_trips 1`.
- `test_cost_outlier_vendor`: `vendor_rows` ten `1200` + one `16000`
  (trips `100`/`50`) → limit `15309.56` (locks `pstdev`, same arithmetic
  as Story 02 §2.7), exactly one insight on the `16000` vendor
  (`reason anomaly`, `severity medium`, `scope.vendor` set); tight trio
  (`1200/1250/1300`) → `[]`.
- `test_contribution_top2`: vector 1 `[{A, trips 6000, late_count 600},
  {B, trips 4000, late_count 300}, {C, trips 2000, late_count 40}]`
  (total 12000/940, rate 0.078333): excess A `130.0`, B/C → 0 →
  `top2 [A, B]` (B `excess 0.0`, `share 0.0`), `contribution_share 1.0`;
  vector 2 `[{A,1000,200},{B,1000,190},{C,1000,170},{D,1000,140},
  {E,6000,300}]` (total 10000/1000, rate exactly `0.10`): excess
  `100/90/70/40/0` → `top2 [A, B]`, shares `0.33/0.30`,
  `contribution_share 0.63` (`190/300 = 0.6333`). Assert `_r2` exactly.
- `test_ranking_severity_x_reach`: hand-built `[{id b, medium, reach
  12000, delta 1.0}, {id a, high, reach 100, delta 5.0}]` → order `[b,
  a]` (24000 > 300); plus tie vector `same score, |delta| 3.0 vs 1.0` →
  larger `|delta|` first; plus full-tie vector → `id` asc.
- `test_zscore_needs_min_points`: 13-point series ending in a spike →
  `insights []`, `skipped True`, `reason_skipped
  "zscore_needs_14_points"`, `n 13`; 14-point flat series → `skipped
  False`, still `[]` (sd == 0 path); fired vector `19× 95.0 + [80.0]`
  (`kpi ota_pct`) → one `anomaly` insight, `baseline 94.25`
  (`(19*95+80)/20`), `current 80.0`, `z ≈ −4.36` (`pytest.approx`),
  `severity medium`; mirror good-direction series (`19× 95.0 + [110.0]`
  clipped to scale — use `19× 80.0 + [95.0]` for OTA, `z > +thresh`) →
  `[]` (direction guard).
- `test_mom_delta_threshold`: `ota_pct` `95→97.0` (Δ exactly 2.0 → no
  flag) vs `95→97.01` (flags, `delta_pp 2.01`); costs `1000→1100`
  (exactly 10% → no flag) vs `1000→1100.01` (flags); cost `prior 0` →
  no flag, no raise; `csat_avg` `4.8→2.0` → no insight (skipped by
  design) while `low_rating_share` `5.0→7.01` flags (`kpi csat`).
- `test_peer_worst_and_tight`: OTA splits `[{A,96.0,5000},{B,95.5,4000},
  {C,88.0,3000}]` (`dim="vendor"`) → one insight on `C`
  (`baseline 93.17`, `delta_pp −5.17`, `reach 3000`, `reason vs_peer`);
  tight `[{96.0},{95.5},{95.0}]` → `[]`; cost splits
  `[{1200},{1250},{1800}]` → fires on the max (`1800`, `+27.06%` over
  mean `1416.67`); `None`-valued rows skipped.
- `test_sev1_small_series_fallback`: `current {sev1_count: 9, trips: 500}`,
  `prior {sev1_count: 4}` → fires (`high`, `vs_prior`, `delta_pp 5.0`);
  `prior 0 / current 1` → fires; same pair with
  `allow_sev1_fallback=False` → `[]` (no overlap with §4.4).
- `test_benchmarks_single_source`: `from backend.core.reason import
  BENCHMARKS` exposes exactly the 11 keys in §3.1.
- Acceptance test `test_ota_top_insight_with_contributors`: SPEC §4
  fixture — OTA 93 vs 95, `delay_splits` with 60%+ top-2 excess (vector 2
  above), plus a weaker cost MoM insight in the same `build_insights`
  call → ranked `[0]` is the OTA breach (`severity high`, correct
  `contribution_share 0.63`, `scope.cycle` echo, vendor vs global `id`s
  distinct); run `build_insights` twice, assert exact `id` order equality
  (stability).
- Flow: write tests → run from `backend/`: `uv run pytest
  tests/test_reason.py` confirms **red** → implement → green. Then full
  `uv run pytest` + `uv run ruff check .` from `backend/`, loop until
  green. Full-dataset calibration is **not** a unit test (same rule as
  Stories 01/02).

## 7. Acceptance mapping (SPEC §4)

1. OTA 93 vs 95 + 60%+ vendor gap → rank #1 with contributors →
   `test_ota_breach_vs_sla` + `test_contribution_top2` (vector 2) +
   `test_ota_top_insight_with_contributors` (§6).
2. z-score < 14 → empty + skip flag, no false positive →
   `test_zscore_needs_min_points` (§6) + §4.4 contract + §5.
3. Stable ranking, exact order asserted →
   `test_ranking_severity_x_reach` + double-run assertion in acceptance
   test (§6); total sort key in §4.6.
4. All thresholds in one importable `BENCHMARKS` →
   §3.1 frozen dict; `test_benchmarks_single_source` asserts `from
   backend.core.reason import BENCHMARKS` exposes exactly the §3.1 keys;
   no other tuning literal ships (review + `rg` guards in §2.9, mechanical
   constants exempt per §2.2).

## 8. Files to touch (final list)

- New: `backend/src/backend/core/reason.py`,
  `backend/tests/test_reason.py`.
- Reuse (read-only): `core/analytics.py` (KPI shapes/rounding/stdev
  semantics), `models/marts.py` (mart field names), `models/ops.py`
  (raw key provenance only — never imported).
- Story 03 does **not** modify `models/*`, `core/database.py`,
  `core/config.py`, `api/*` (Story 04 owns router + `insight_cache`
  writes), `scripts/ingest.py`, frontend, existing
  `health/ready/examples` routes. Companion ask of Story 04 (not this
  story): add `DailyKpi.max_trip_cost` + populate it as
  `max(bills.trip_cost)` per cycle — this spec's optional-key skipping
  (§4.1) tolerates its absence until then, so no shape renegotiation is
  needed.
- Untouched by this story: narration (Story 07), trigger delivery/logging
  (Story 08 wraps this module's functions and `BENCHMARKS`).

## 9. Risks

- **SPEC fixes the `Insight` field name `delta_pp` but costs need percent.**
  Frozen here (§2.5): rates store raw diff, costs store % in the same field.
  Alternative (add `delta_pct`) would break the SPEC schema Story 04
  codegens against — rejected.
- **Absolute thresholds exist only for OTA/ack/cost-sanity.** CSAT-star,
  no-show, alert-rate have no absolute cutoff in SPEC/PLAN (trend + peer
  only). Adding e.g. `csat_avg < 4.0` would be new product policy —
  explicitly out; CSAT trend rides `low_rating_share` (§2.5), stars fire
  via peer/z-score paths.
- **Sev-1 has two branches by design** (small-series `> 2× prior` in
  §4.2 gated by `allow_sev1_fallback`, large-series `mean + 2σ` in §4.4).
  Both are frozen Story 08 language; `build_insights` flips the gate on
  the 14-point boundary so there is no gap/overlap in coverage.
- **`pstdev` vs `stdev` (again).** Frozen as population stdev (§2.7) for
  parity with `flag_cost_outliers`. On real cycles (n ≫ 30) the difference
  is negligible; on tiny fixtures it decides flags, hence the strict-`>`
  boundary tests plus the frozen `15309.56` outlier limit in §6.
- **`id` slug collisions across dims.** Solved by the `v_`/`o_`/`all`
  scope segment (§2.4): vendor and office insights for the same KPI/cycle
  differ even when names collide (`..._v_hq` vs `..._o_hq`); global ends
  `_all`. Slug review is part of the acceptance test (assert distinct
  `id`s for vendor vs global OTA).
- **Cost-sanity mart addition.** User decision: `max_trip_cost` is added to
  the marts by Story 04 (§8); Story 03 reads `snapshot["max_trip_cost"]`
  and skips when absent. No bills scan at request time, mart-only holds.

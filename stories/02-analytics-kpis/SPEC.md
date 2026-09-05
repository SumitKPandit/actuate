# Story 02 — KPI Analytics `core/analytics.py` (pure functions)

**Status:** complete (verified 2026-09-05: 22 analytics tests + 41 full suite green, ruff clean, no forbidden imports). **Depends on:** 01 (raw table shapes + quirk fixtures).

## 1. Goal

One trusted place for every MVP KPI so API, brief, dashboard, and Q&A can never disagree. Pure, deterministic, unit-tested math — no DB, no LLM, no HTTP.

## 2. Scope

**In:** new `backend/src/backend/core/analytics.py` + `backend/tests/test_analytics.py`.
**Out:** benchmarks/ranking (Story 03), narration (Story 07), persistence (Story 01).

## 3. Functional requirements (frozen definitions from PLAN.md §4)

All functions take plain rows/dicts (or pandas-free iterables — no pandas dependency) and return rounded, JSON-serializable numbers. Denominators of 0 → `None` (never divide-by-zero, never 0% masquerading as data).

1. **OTA %:** `ota_pct = 100 * (1 - late / total)` where late = `delay_minutes > 15`. Input `delay_minutes` already numeric (Story 01 stripped commas). Empty → `None`.
2. **Delay:** `avg_delay_min` (mean of `delay_minutes` over all trips), plus `reason_mix` counts/share **late-only** (`delay_minutes > 15`) over `{NODELAY, TRAFFIC, DRIVER, EMPLOYEE, UNKNOWN}` with `share = count / late_count` (`None` when `late_count == 0`). Vendor/office attribution = group-by caller provides, function supports `group_key` param.
3. **No-show %:** legs grain: `100 * SUM(is_no_show) / COUNT(legs)`. Only `is_no_show` bool from `legs`; ignore `boarding_status` text except in tests as cross-check. Support split by `shift_type`/`office`.
4. **Cost:** `cost_per_trip = SUM(trip_cost)/COUNT(billed_trips)`; `cost_per_km = SUM(trip_cost)/SUM(total_trip_km WHERE km > 0)`. `trip_cost` comma-stripped numeric. Zero-km rows excluded from `cost_per_km` denominator but counted in `zero_km_count` + share. Outlier flag: `trip_cost > mean + 3*stdev` (per vendor/cycle group when grouped) → `is_outlier`.
5. **Alerts:** `alert_rate_per_1k = 1000 * alerts / trips`; `sev1_count`, `sev2_count`; `sev_breakdown` with `"unclassified"` bucket for NULL severity (incl. `"False"`-as-null). `ack_minutes` = `acknowledge_time - start_time`; `ack_sla_met_share` vs 30 min; NULL `acknowledge_time` = unacknowledged (counted, not dropped). 54 nulls expected in full data — fixture must cover.
6. **CSAT:** per dimension (`route/driver/cab/safety/marshal`): average **excluding 0s**; `low_rating_share` = share `< 3` among non-zero ratings; `marshal_unrated_share` = share `= 0`. Overall `csat_avg` = mean of the 4 non-marshal dimension avgs (document and freeze).

## 4. Acceptance criteria

- [x] Each KPI has ≥1 unit test with hand-computed expected value (e.g. 100 trips, 5 late → OTA 95.0).
- [x] Edge cases return `None`/explicit counts, never crash: empty input, all-zero-km, all ratings 0, all severity NULL, zero trips.
- [x] `ruff` clean; functions < ~40 lines each, one KPI per function (modularity per AGENTS.md).
- [x] No imports from `database`, `fastapi`, `httpx`, or any LLM SDK.

## 5. Test plan (test-first)

`backend/tests/test_analytics.py` — minimum cases:
- `test_ota_boundary`: delay exactly 15 → on-time; 15.01/16 → late.
- `test_ota_empty_returns_none`.
- `test_delay_avg_and_reason_mix` (late-only) + `test_reason_mix_no_late_shares_none`.
- `test_cost_per_km_ignores_zero_km` + `test_zero_km_counted`.
- `test_outlier_flagged`.
- `test_csat_excludes_zeros` + `test_low_rating_share` + `test_marshal_unrated`.
- `test_alert_rate_and_unclassified_severity`.
- `test_ack_sla` (ack 10 min → met; 40 min → missed; NULL → unacknowledged).
- `test_no_show_rate`.
- Confirm red → implement → `uv run pytest backend/tests/test_analytics.py` green.

## 6. Files to touch

- New: `backend/src/backend/core/analytics.py`, `backend/tests/test_analytics.py`.
- Reuse: Story 01 quirk fixtures as input shapes. Do not modify models or ingest.

## 7. Notes

- PLAN evidence for calibration: delayed share ~2.4% May / ~7% Jun / ~3.9% Jul; cost median ~1236, mean ~1394, max ~16k; feedback avg ~4.85. Tests use tiny fixtures, not these — values are sanity anchors for later mart validation.

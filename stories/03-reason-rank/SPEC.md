# Story 03 — Reasoning + Ranking `core/reason.py` (deterministic-first agent brain)

**Status:** pick up after Story 02. **Depends on:** 02 (KPI outputs as input facts).

## 1. Goal

Turn KPI numbers into a ranked exception feed the transport manager can act on: what slipped, versus what benchmark, who drives it, and how big the gap is — all deterministic rules, no LLM.

## 2. Scope

**In:** new `backend/src/backend/core/reason.py` + `backend/tests/test_reason.py`.
**Out:** API shapes (Story 04), wording/narration (Story 07), trigger delivery (Story 08).

## 3. Functional requirements

Input: KPI aggregates (from Story 02 / marts) + benchmark config. Output: list of `Insight` dicts with stable schema:

```json
{ "id": "ota_drop_jun", "kpi": "ota_pct", "scope": {"vendor": "X"|null, "office": null, "cycle": "2026-06-H2"},
  "current": 93.0, "baseline": 95.0, "delta_pp": -2.0, "severity": "high|medium|low",
  "reach_trips": 12000, "contribution_share": 0.42, "reason": "vs_sla|vs_prior|vs_peer|anomaly",
  "recommended_action": "…", "owner": "vendor|X|office|ops" }
```

Rules (implement exactly, keep thresholds in one `BENCHMARKS` dict):

1. **Benchmarks:** OTA SLA 95%; ack SLA 30 min; peer = vendor/office rank within same cycle; prior = previous cycle/month.
2. **Anomaly checks (all three):** absolute threshold breach (OTA < 95, Sev-1 count spike); MoM/cycle-over-cycle delta (flag if |Δ| > 2pp for rates, > 10% for costs — freeze these); z-score (|z| > 2 on daily series, min 14 points else skip with `reason_skipped`).
3. **Contribution analysis:** for each degraded KPI, attribute gap to top-2 vendors/offices by `(vendor_late - expected_late)` share; store `contribution_share` (e.g. "2 vendors = 63% of delay gap").
4. **Ranking:** `score = severity_weight × reach_trips` (weights: high=3, medium=2, low=1); sort desc; ties → larger `|delta|` first. Deterministic — same input, same order.
5. **Recommended action + owner:** rule-mapped, not free text. Minimum map: OTA breach → "Re-route / add buffer + vendor penalty review" (owner: vendor); Sev-1 spike → "Acknowledge open Sev-1s + escort audit" (owner: ops); cost outlier → "Hold bill line + verify km slab" (owner: ops); CSAT low cluster → "Driver/cab review with vendor" (owner: vendor); no-show spike → "Shift reminder + standby cab" (owner: office).
6. No LLM, no I/O, no datetime-now inside logic (pass `as_of` in for testability).

## 4. Acceptance criteria

- [ ] Given fixture: OTA 93% vs SLA 95% with 2 vendors driving 60%+ gap → top insight is OTA breach with correct contributors, severity high, rank #1.
- [ ] z-score with < 14 points returns empty with skip flag, not a false positive.
- [ ] Ranking is stable across runs (test asserts exact order on fixed fixture).
- [ ] All thresholds live in one `BENCHMARKS` constant importable by API/docs.

## 5. Test plan (test-first)

`backend/tests/test_reason.py`:
- `test_ota_breach_vs_sla` (93 vs 95 → high).
- `test_no_breach_when_above_sla` (96.5 → no OTA insight).
- `test_contribution_top2` (hand-built vendor splits → expected shares).
- `test_ranking_severity_x_reach` (medium×large beats high×tiny — assert order).
- `test_zscore_needs_min_points`.
- `test_mom_delta_threshold`.
- Red → implement → green.

## 6. Files to touch

- New: `backend/src/backend/core/reason.py`, `backend/tests/test_reason.py`.
- Reuse: `core/analytics.py` output shapes. Do not touch DB/API/UI.

## 7. Notes

- This is the "Reason" step of PLAN §3 agentic loop (Sense→Reason→Act). Story 04 persists/displays these insights; Story 07 only narrates them.

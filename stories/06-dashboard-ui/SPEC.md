# Story 06 — Dashboard + Vendors `/dashboard`

**Status:** pick up after Story 04 (can parallelize with Story 05 once `lib/ops.ts` exists). **Depends on:** 04 (`/overview`, `/vendors`).

## 1. Goal

Transport manager drills from "what slipped" (brief) into "where exactly + who owns it": KPI trends with benchmark badges and a sortable vendor table with peer ranks.

## 2. Scope

**In:** new route `frontend/src/routes/dashboard.tsx` + components under `frontend/src/components/dashboard/`, reusing `lib/ops.ts` from Story 05.
**Out:** Q&A drawer (Story 07), ingest/API changes.

## 3. Functional requirements

1. **Filters (persist in URL query):** `cycle`, `office`, `vendor`, `business_unit`. Changing any refetches `/overview` + `/vendors`. Defaults: latest cycle, all offices/vendors.
2. **KPI cards (6, matching PLAN §4):** OTA % · Avg delay + reason mix · No-show % · Cost/trip (+ cost/km + zero-km share) · Alert rate/1k (+ Sev-1 + ack SLA share) · CSAT (+ low-rating share). Each card: current value, Δ vs prior cycle, **benchmark badge** (✓ ≥ SLA green / ✗ breach red: OTA 95%, ack 30 min), peer context ("rank #3/23 vendors").
3. **Vendor table:** columns vendor · trips · OTA · cost/trip · cost/km · alert/1k · CSAT · contribution% · peer rank; sortable by `sort=` param values (`ota|cost|alerts|csat`); zero-km and `UNSLABBED` counts as sub-text, not hidden. Row click sets `?vendor=` filter (drives brief safety link from Story 05).
4. **States:** loading skeleton, API `warning` banner, 404-cycle fallback to latest, empty cells show `—` (never `0` for missing).
5. **No heavy chart lib:** CSS bars / inline SVG sparklines from `daily_kpi` via `/overview` trend array (if API lacks trend, render cycle Δ only — do not invent a new endpoint here; file follow-up for Story 08 if needed).

## 4. Acceptance criteria

- [ ] With stubbed `/overview` + `/vendors` fixtures, all 6 cards render with badges and deltas; vendor sort by each key reorders rows correctly.
- [ ] URL filters round-trip: reload with `?cycle=…&vendor=…` restores state.
- [ ] Missing data renders `—` + banner, never crashes.
- [ ] `npm run build` + `eslint` clean; `/` brief unaffected.

## 5. Test plan

- Vitest: `dashboard cards render`, `vendor sort`, `filter round-trip`, `empty state`.
- Fixtures to add: `stories/06-dashboard-ui/sample-overview.json`, `sample-vendors.json` (match Story 04 schemas).
- Manual: compose up → `/dashboard` against live API; screenshot/note in folder.

## 6. Files to touch

- New: `frontend/src/routes/dashboard.tsx`, `frontend/src/components/dashboard/*`, fixtures in this story folder.
- Reuse/edit: `frontend/src/lib/ops.ts` (extend, don't fork), header nav to link `/` ↔ `/dashboard`.
- Do not hand-edit `routeTree.gen.ts`.

## 7. Notes

- Vendor name reconciliation: trip `vendor_id` vs bill `vendor` strings may differ slightly (e.g. "Sneha" vs "Priya Mikhailov Travel") — display API's canonical string; file mismatches as Story 08 data-quality note, do not fuzzy-match here.

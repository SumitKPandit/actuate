# Story 06 — Dashboard `/dashboard`

**Status:** pick up after Story 05. **Depends on:** 05 (`lib/ops.ts`, routing pattern, vitest harness), 04 (`/overview`, `/vendors` contracts).

## 1. Goal

Transport manager drills from "what slipped" (brief) into "where exactly + who owns it": KPI trends with benchmark badges and a sortable vendor table with peer ranks.

## 2. Scope

**In:**
- `frontend/src/components/dashboard/DashboardPage.tsx` (new): top-level dashboard page, loads `/overview` + `/vendors` via `lib/ops.ts`.
- `frontend/src/components/dashboard/KpiCards.tsx` (new): 6 KPI cards with benchmark badges and deltas.
- `frontend/src/components/dashboard/VendorTable.tsx` (new): sortable vendor table.
- `frontend/src/components/dashboard/FilterBar.tsx` (new): cycle/office/vendor/BU selectors persisting in URL query.
- `frontend/src/components/dashboard/__tests__/*` (new): dashboard integration tests.

**Out:** Q&A drawer (Story 07), ingest/API changes.

## 3. Functional requirements

1. **Routing:** accessible at `/?page=dashboard` (same conditional routing pattern established in Story 05). No new router dependency.
2. **Filters (persist in URL query):** `cycle`, `office`, `vendor`, `business_unit`. Changing any refetches `/overview` + `/vendors`. Defaults: latest cycle, all offices/vendors. Read from `window.location.search` on mount; update via `history.pushState` or `<a>` links.
3. **KPI cards (6, matching PLAN §4):** OTA % · Avg delay + reason mix (late-only shares) · No-show % · Cost/trip (+ cost/km + zero-km share) · Alert rate/1k (+ Sev-1 + ack SLA share) · CSAT (+ low-rating share). Each card: current value, Δ vs prior cycle, **benchmark badge** (✓ ≥ SLA green / ✗ breach red: OTA 95%, ack 30 min), peer context ("rank #3/23 vendors").
   - Benchmarks read from `/overview.data.benchmarks` (`{ota_sla: 95, ack_sla_min: 30}`).
   - Delta calculation: current value from `/overview` minus prior cycle value. If prior is null, show `—` and no delta.
4. **Vendor table:** columns vendor · trips · OTA · cost/trip · cost/km · alert/1k · CSAT · contribution% · peer rank; sortable by `sort=` param values (`ota|cost|alerts|csat`); zero-km and `UNSLABBED` counts as sub-text, not hidden. Row click sets `?vendor=` filter (drives brief safety link from Story 05).
5. **States:** loading skeleton, API `warning` banner, 404-cycle fallback to latest (parse `valid_cycles` from 404 body), empty cells show `—` (never `0` for missing).
6. **No heavy chart lib:** CSS bars or inline SVG sparklines from `daily_kpi` via `/overview` trend array. **But `/overview` does not return a trend array** — it returns a single snapshot. Per spec: render cycle Δ only. Do not invent a new endpoint here; file follow-up for Story 08 if trend data is needed.

## 4. Acceptance criteria

- [ ] With stubbed `/overview` + `/vendors` fixtures (via mocked `lib/ops.ts`), all 6 cards render with badges and deltas.
- [ ] Vendor sort by each key (`ota|cost|alerts|csat`) reorders rows correctly.
- [ ] URL filters round-trip: reload with `?cycle=…&vendor=…` restores state.
- [ ] Missing data renders `—` + banner, never crashes.
- [ ] `npm run build` + `eslint` clean; `/` brief unaffected.
- [ ] Row click on vendor sets `?vendor=` and filters `/overview` + `/vendors` accordingly.

## 5. Test plan (test-first)

- `frontend/src/components/dashboard/__tests__/DashboardPage.test.tsx`: render with mocked `/overview` + `/vendors` → 6 cards render with badges, deltas, vendor table populated.
- `frontend/src/components/dashboard/__tests__/VendorTable.test.tsx`: sort by `ota`, `cost`, `alerts`, `csat` reorders rows; zero-km and UNSLABBED shown as sub-text.
- `frontend/src/components/dashboard/__tests__/FilterRoundTrip.test.tsx`: set `?cycle=&vendor=` → reload → filters restored.
- `frontend/src/components/dashboard/__tests__/EmptyState.test.tsx`: mock null values → `—` + warning banner.

Fixtures to use/update: `stories/06-dashboard-ui/sample-overview.json`, `stories/06-dashboard-ui/sample-vendors.json`.

Commands: `npx vitest run` green; `npm run lint` clean; `npm run build` clean.

## 6. Files to touch

- New: `frontend/src/components/dashboard/DashboardPage.tsx`, `frontend/src/components/dashboard/KpiCards.tsx`, `frontend/src/components/dashboard/VendorTable.tsx`, `frontend/src/components/dashboard/FilterBar.tsx`, `frontend/src/components/dashboard/__tests__/*`, `stories/06-dashboard-ui/sample-overview.json`, `stories/06-dashboard-ui/sample-vendors.json`.
- Edit: none required (reuses `lib/ops.ts`, `App.jsx` routing, `Header.jsx` from Story 05).
- Do not modify: `backend/**`, `frontend/src/lib/ops.ts` (extend only if new endpoints added in later stories).

## 7. Notes

- Vendor name reconciliation: trip `vendor_id` vs bill `vendor` strings may differ slightly (e.g. "Sneha" vs "Priya Mikhailov Travel") — display API's canonical string; file mismatches as Story 08 data-quality note, do not fuzzy-match here.
- `/overview` returns a single snapshot, not a time series. If trend sparklines are desired, they must come from a new endpoint (Story 08) or from `/insights` deltas. Do not invent data in the UI.
- The `?vendor=` filter is shared with Story 05's safety strip link — both pages must read/write the same query param so the brief → dashboard → brief round-trip preserves context.

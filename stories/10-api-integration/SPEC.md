# Story 10 — API Integration: Live Data in Brief + Dashboard, Ack Write-Path

**Status:** implemented (verified 2026-09-05: live brief/dashboard wiring, ack write-path, URL state, adapter/integration tests, frontend gates, and backend regression checks; compose smoke pending a running Docker daemon). **Depends on:** 09 (`lib/ops.ts`, hooks, harness, fixtures), 04 (ops API), 01–03 (mart data). Delivers the deferred Story 05 §3.1/§3.3 data wiring and Story 06 §3.3–§3.5 dashboard wiring; Story 05/06 status lines said "wiring pending Story 07" — corrected: this story owns it.

## 1. Goal

Replace every `data.js` mock with live API data so the transport manager sees the real current cycle: KPI cards, exception feed, actions, safety count, vendor table — with the ack write-path working end-to-end and `data.js` deleted.

## 2. Scope

**In:**
- Wire brief read-path: `TriggerBanner`, `AlertsSection` (→ exception feed), `RecommendedActions` (→ actions), `KpiPulse` KPI values — from `useOpsData` payloads via adapter mappers.
- Ack write-path: `POST /actions/{id}/ack` with optimistic update + rollback.
- Copy-for-vendor: use API `copy_for_vendor` string (replaces hardcoded template in `App.jsx:91`).
- Dashboard wiring: `KpiPulse` from `/overview.data` + `benchmarks` + `/insights` deltas; add sortable vendor table from `/vendors?cycle=&sort=`.
- Delete `frontend/src/data.js` once the last consumer is gone.
- Documentation touch-ups listed in §6.

**Out:** `ChatPanel` (stays mock + disabled until Story 07), `DataQualityBar`/`Modals` (static until 08), backend changes, narrate toggle (`?narrate=true` → Story 07), push triggers.

## 3. Functional requirements

1. **Mock → API mapping (adapters in `frontend/src/lib/adapters.js`):**

   | Mock (data.js) | Source |
   |---|---|
   | `kpis[]` card values/deltas | `/overview.data` + `benchmarks`; Δ vs prior cycle via `/insights` baselines (`null` prior → `—`, no delta) |
   | `alerts[]` exception cards | `/briefing.data.insights_top5`: kpi, scope, current vs baseline, severity badge, reach_trips, contribution_share, recommended_action, owner |
   | `recommendedActions[]` | `/briefing.data.actions_top3` (falls back to `GET /actions`): due_hint, copy_for_vendor, status (`proposed/acked`) |
   | Sev-1 "18 Open" | `briefing.safety_open_sev1` |
   | Vendor table | `/vendors?cycle=&sort=`: peer_rank, contribution_share, zero_km_count, unslabbed_count; sort keys `ota|cost|alerts|csat` (422 body lists `allowed`) |
   | `copyVendorMessage()` text | `action.copy_for_vendor` (backend truncates ≤ 500 chars) |

2. **States (both surfaces):** loading skeleton; error state; empty-marts `warning` rendered as banner, never blank page; missing values render `—` (never `0`).
3. **Cycle:** selector from `useCycle` (`valid_cycles` on 404); changing it refetches all surfaces.
4. **TriggerBanner forward-compat:** render only when `(briefing.data as any).triggers` is a non-empty array with `fired=true` entries (name + scope); missing key or empty → nothing. Never crash on pre-Story-08 payloads.
5. **Ack flow:** approve button → optimistic `status: "acked"` flip + toast; on 404/422/error roll back and toast the failure; button disabled while pending. Actor: `"Transport Manager"` (Story 05 §3.3).
6. **Routing divergence (deliberate):** the single-page layout stays — brief and dashboard surfaces co-exist on one scroll; the `?page=` conditional routing from Story 05 §3.2 is **not** implemented (both surfaces already co-exist; splitting adds no manager value now). Header nav links are dropped; flagged for the Story 08 docs pass.
7. **ChatPanel:** shows a disabled "Ask lands in Story 07" state instead of mock conversation, but is otherwise untouched.

## 4. Acceptance criteria

- [ ] With msw stubbing the real endpoints (fixtures from Story 09), brief shows all sections with correct numbers/badges; no `data.js` import remains anywhere.
- [ ] Trigger banner: fixture with `triggers:[{fired:true}]` shows banner; `triggers:[]`/missing key shows nothing.
- [ ] Copy-for-vendor copies the exact API `copy_for_vendor` string (test asserts clipboard content).
- [ ] Empty-marts warning renders as banner, not blank page.
- [ ] Ack: optimistic flip on 200; rollback + error toast on 404 (unknown id); request body `{actor:"Transport Manager"}`.
- [ ] Vendor table: all 4 sorts reorder rows; zero-km/unslabbed counts visible as sub-text; URL round-trip `?cycle=&vendor=` restores state.
- [ ] `frontend/src/data.js` deleted.
- [ ] `npx vitest run` green; `npm run lint` + `npm run build` clean; backend `uv run pytest` + `ruff` untouched green.
- [ ] E2E smoke: `docker compose up --build` → brief + dashboard render live data at `127.0.0.1:3000`.

## 5. Test plan (test-first)

- `frontend/src/lib/__tests__/adapters.test.js`: each mapping row above, including null/missing-value → `—` cases.
- `frontend/src/__tests__/BriefLive.test.jsx`: msw-served fixtures → sections render; warning banner; trigger-banner fire/no-fire/missing-key.
- `frontend/src/__tests__/AckFlow.test.jsx`: optimistic flip, rollback on 404, clipboard content assertion.
- `frontend/src/__tests__/VendorTable.test.jsx`: sorts + counts + URL round-trip.

Commands: `npx vitest run` green; `npm run lint` clean; `npm run build` clean; `uv run pytest` green.

## 6. Files to touch

- Edit: `frontend/src/App.jsx`, `frontend/src/components/TriggerBanner.jsx`, `frontend/src/components/KpiPulse.jsx`, `frontend/src/components/AlertsSection.jsx`, `frontend/src/components/RecommendedActions.jsx`, `frontend/src/components/ChatPanel.jsx`, `frontend/src/components/Header.jsx`, `frontend/src/components/Modals.jsx` (safety counts → `safety_open_sev1`).
- New: `frontend/src/lib/adapters.js`, `frontend/src/__tests__/*`.
- Delete: `frontend/src/data.js`.
- Docs: update status lines of `stories/05-brief-ui/SPEC.md` + `stories/06-dashboard-ui/SPEC.md` (wiring done here), this SPEC status, `stories/README.md` table.
- Do not modify: `backend/**` (contract changes belong to 07/08), `frontend/src/lib/ops.ts` (Story 09).

## 7. Notes

- 05 §3.2 (`?page=` routing) and 06 §3.1 (separate `DashboardPage.tsx`) anticipated a split-page layout; the built UI merged both surfaces on one page (06 status: "dashboard elements embedded in single-page layout"). Story 10 keeps the merged layout (§3.6) — 05/06 routing requirements are superseded; Story 08 docs pass records this.
- Component renames from 05 §6 (`ExceptionFeed`, `ActionsPanel`, …) are likewise superseded — existing component names stay; only their data source changes.
- `KpiPulse` deltas need prior-cycle numbers: `/insights` carries `baseline`; if absent, show `—` (do not invent).

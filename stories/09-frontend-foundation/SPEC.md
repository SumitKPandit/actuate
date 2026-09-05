# Story 09 — Frontend↔API Foundation: Typed Client + Test Harness

**Status:** ready — pick up after Stories 04–06 (may run before 07/08). **Depends on:** 04 (ops API contracts frozen in `backend/src/backend/api/ops.py`), 01–03 (mart data present). Delivers the deferred Story 05 §3.4 foundation: today `frontend/src/lib/` is empty, there is no test harness, and no fixtures exist.

## 1. Goal

Establish the frontend data layer so Story 10 can wire UI to live API with zero backend changes: a typed fetch client mirroring the Story 04 Pydantic schemas, a test harness (vitest + msw), cycle/data hooks, and committed fixtures snapshotting real API responses.

## 2. Scope

**In:**
- `frontend/src/lib/ops.ts` (new): typed fetch client for all Story 04 endpoints.
- `frontend/vitest.config.ts` + `frontend/src/test-setup.ts` (new): Vitest + Testing Library + msw harness.
- `frontend/src/lib/useCycle.js` + `frontend/src/lib/useOpsData.js` (new): cycle resolution + parallel data loading hooks.
- Fixtures (new): `stories/05-brief-ui/sample-briefing.json`, `stories/06-dashboard-ui/sample-overview.json`, `stories/06-dashboard-ui/sample-vendors.json`, `stories/06-dashboard-ui/sample-insights.json` — snapshot real responses from a running backend against ingested data.
- `frontend/.env.example` (new): `VITE_API_URL=http://127.0.0.1:8000`.
- `frontend/package.json` (edit): add dev deps (`vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `msw`), `test` script.

**Out:** any component wiring (Story 10), backend changes, `?page=` routing, TanStack Start migration.

## 3. Functional requirements

1. **API client (`lib/ops.ts`):**
   - Functions: `getOverview(cycle)`, `getBriefing(cycle)`, `getInsights(cycle)`, `getActions(cycle)`, `getVendors(cycle, sort)`, `ackAction(id, actor)`. (`getInsights` extends the Story 05 list — needed for prior-cycle deltas in Story 10.)
   - All functions read `import.meta.env.VITE_API_URL` (default `http://127.0.0.1:8000`). Missing env var → inline error, verbatim: `"Set VITE_API_URL in frontend/.env"`.
   - Envelope-aware: parses `{data, warning}` from all GETs; returns both (caller decides). Non-2xx → throws typed `ApiError` carrying `status` + parsed `detail` body (404 `valid_cycles`, 422 `allowed`, empty-marts warnings flow through untouched).
   - Types match backend Pydantic schemas exactly: `OverviewData`, `BriefingData`, `InsightSchema`, `VendorRow`, `ActionItem`, `AckRequest`, `AckResponse` (Story 04 `ops.py:24-121`). `triggers` typed as optional passthrough (`triggers?: unknown[]`) — Story 08 fills it.
2. **Hooks:**
   - `useCycle()`: resolves the working cycle. Strategy: request with default `2026-06-H1`; on 404 use `valid_cycles[0]` from the error body; if that is empty, keep the hardcoded fallback. Exposes `{cycle, setCycle, cycles}`.
   - `useOpsData(cycle)`: `Promise.all([getBriefing, getActions, getOverview])` in one round-trip set; exposes `{data, warning, loading, error, refetch}`. Surfaces API `warning` verbatim.
3. **Fixtures** must satisfy a schema-conformance test (parsed fixture passes the `lib/ops.ts` types) so they cannot drift from the backend contract silently.

## 4. Acceptance criteria

- [ ] Each client function: success envelope parsed; 404 body (`valid_cycles`) and 422 body (`allowed`) surfaced on `ApiError`; network failure → thrown error, no silent undefined.
- [ ] `ackAction` POSTs `{actor}` and returns the ack record (`{id, status, actor, acked_at}`).
- [ ] `useCycle` resolves from 404 `valid_cycles`; `useOpsData` exposes loading/error/warning states.
- [ ] All 4 fixtures pass the schema-conformance test.
- [ ] `npx vitest run` green; `npm run lint` + `npm run build` clean; backend untouched (`uv run pytest` still green).

## 5. Test plan (test-first)

- `frontend/src/lib/__tests__/ops.test.ts`: per-endpoint success/404/422/network-failure against msw handlers; `ackAction` request body + response shape.
- `frontend/src/lib/__tests__/useCycle.test.jsx`: 200 → default cycle; 404 → `valid_cycles[0]`; empty valid list → `2026-06-H1` fallback.
- `frontend/src/lib/__tests__/useOpsData.test.jsx`: Promise.all ordering; `warning` passthrough; loading/error flags.
- `frontend/src/lib/__tests__/fixtures.test.ts`: fixture files conform to exported types.

Commands: `npx vitest run` green; `npm run lint` clean; `npm run build` clean.

## 6. Files to touch

- New: `frontend/src/lib/ops.ts`, `frontend/src/lib/useCycle.js`, `frontend/src/lib/useOpsData.js`, `frontend/src/lib/__tests__/*`, `frontend/vitest.config.ts`, `frontend/src/test-setup.ts`, `frontend/.env.example`, the 4 fixture JSONs under `stories/05-brief-ui/` + `stories/06-dashboard-ui/`.
- Edit: `frontend/package.json`.
- Do not modify: `backend/**`, `frontend/src/App.jsx`, `frontend/src/data.js`, any component (Story 10).

## 7. Notes

- Story 05 is marked complete with wiring "pending Story 07" — that was wrong: Story 07 is backend narration + `/ask` and does not wire the brief. This story (09) + Story 10 own the wiring; 05's status line is updated accordingly.
- Fixtures are hand-snapshots of real API responses (run backend, `curl` the endpoints against ingested data, save) — not invented JSON.
- `POST /ask` is a 501 stub and stays out of the client until Story 07.

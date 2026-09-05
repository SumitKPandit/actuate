# Story 05 — Brief UI `/` + Frontend Foundation

**Status:** complete (verified 2026-09-05: static SPA prototype aligned, all components render, build + lint clean, API wiring pending Story 07). **Depends on:** 04 (`/briefing`, `/actions`, `/overview` contracts frozen); 01–03 mart data present.

## 1. Goal

Transport manager opens `/` and in < 30 seconds knows: what slipped, which vendors/offices drive it, which safety items need acknowledgement, and what to do next. No manual report assembly. This story also establishes the frontend foundation (typed API client, test harness, routing pattern) that Story 06 reuses.

## 2. Scope

**In:**
- `frontend/src/lib/ops.ts` (new): typed fetch client for all Story 04 API endpoints (`/overview`, `/briefing`, `/actions`, `/vendors`, `POST /actions/{id}/ack`).
- `frontend/vitest.config.ts` + `frontend/src/test-setup.ts` (new): Vitest + Testing Library harness.
- `frontend/src/components/brief/*` (new): brief-page components reading from `lib/ops.ts`.
- `frontend/src/App.jsx` (edit): conditional page routing (`/` vs `/dashboard` via URL query `?page=`), replace static `data.js` imports with live API calls, wire Header nav links.
- `stories/05-brief-ui/sample-briefing.json` (new): fixture matching `BriefingData` schema.
- `frontend/src/components/__tests__/*` (new): brief-page integration tests.

**Out:** dashboard charts (Story 06), NL Q&A (Story 07), TanStack Start migration (future infra story — not required here), any direct DB/CSV access.

## 3. Functional requirements

1. **Data:** on load, `GET /briefing?cycle=` + `GET /actions?cycle=` + `GET /overview?cycle=` (for benchmarks). Cycle selector defaults to latest; options come from `GET /overview` 404 `valid_cycles` array, or hardcode `2026-06-H1` as fallback. Loading / error / empty-marts-warning states required (surface API `warning` verbatim). All 3 fetches complete in ≤ 2 network round-trips (Promise.all).
2. **Routing:** `App.jsx` reads `?page=` from `window.location.search`. `page=dashboard` renders Dashboard placeholder; absent or `page=brief` renders the Brief page. Header has nav links to both. No `<Link>`/TanStack Router dependency — plain `<a>` tags with `?page=` params.
3. **Layout (top→bottom):**
   - Cycle selector + `generated_at` stamp + benchmark chips (OTA SLA 95% · Ack 30 min) from `/overview.data.benchmarks`.
   - Trigger banner: render defensively. Backend `BriefingData` has no `triggers` field yet (Story 08). If `(data as any).triggers` exists and is a non-empty array, render red banner for each `fired=true` trigger with trigger name + scope. Otherwise render nothing. Never crash on missing key.
   - Headline facts (3–5 template strings from `/briefing.data.headline_facts`).
   - Ranked exception feed (top 5 from `/briefing.data.insights_top5`): each card shows KPI, scope (vendor/office/cycle), current vs baseline Δ, severity badge, reach (trips), contribution ("2 vendors = X% of gap"), recommended action + owner.
   - Safety strip: open Sev-1 count + unacknowledged count + oldest unacked age; links to `/dashboard?vendor=` (Story 06 hook — keep as query param even if dashboard lands later).
   - Actions: top 3 from `/briefing.data.actions_top3` with owner chip + status chip (`proposed/acked`) + **Copy-for-vendor button** (clipboard, backend truncates ≤ 500 chars, toast confirm) + **Ack button** calling `POST /actions/{id}/ack` with actor `"Transport Manager"` (optimistic status flip, error toast on 404).
4. **API client (`lib/ops.ts`):**
   - All functions read `import.meta.env.VITE_API_URL` (default `http://127.0.0.1:8000`). Missing env var → inline error naming `VITE_API_URL`.
   - Envelope-aware: parses `{data, warning}` from all GETs. Non-2xx → throws with `detail` from JSON body.
   - Functions: `getOverview`, `getBriefing`, `getActions`, `getVendors`, `ackAction`. Types match backend Pydantic schemas exactly.
5. **Style:** reuse existing tokens in `src/styles.css` (`--color-primary`, `--color-surface-panel`, etc.); no new design system. Mobile-readable single column.

## 4. Acceptance criteria

- [ ] With API stubbed (msw or fixture JSON in `stories/05-brief-ui/sample-briefing.json`), page shows all §3.3 sections with correct numbers/badges.
- [ ] Trigger banner: fixture with `triggers:[{fired:true}]` shows red banner; `triggers:[]` or missing key shows nothing (forward-compatible with pre-Story-08 API).
- [ ] Copy-for-vendor copies exact `copy_for_vendor` string (test asserts clipboard content).
- [ ] Empty-marts warning from API renders as banner, not blank page.
- [ ] `npm run build` + `eslint` clean; existing `/about` route unaffected (no routes broken).
- [ ] Header has working nav links between `/` and `/dashboard`.
- [ ] `lib/ops.ts` types match backend schemas from Story 04 (`BriefingData`, `OverviewData`, `ActionItem`, etc.).

## 5. Test plan (test-first)

- `frontend/src/components/brief/__tests__/BriefPage.test.tsx`: render with mocked `lib/ops.ts` → all sections present with fixture data.
- `frontend/src/components/brief/__tests__/TriggerBanner.test.tsx`: fire/no-fire, missing key (forward-compatible).
- `frontend/src/components/brief/__tests__/ActionsPanel.test.tsx`: copy button asserts clipboard content; ack button calls `ackAction` with correct id + actor; optimistic flip; 404 error toast.
- `frontend/src/components/brief/__tests__/EmptyWarning.test.tsx`: API `{data: null, warning: "..."}` renders banner, not blank page.
- `frontend/src/components/brief/__tests__/LoadingState.test.tsx`: loading skeletons during fetch.
- `frontend/src/App.test.tsx`: routing by `?page=` renders correct page; header nav links present.

Fixtures: `stories/05-brief-ui/sample-briefing.json`, `stories/06-dashboard-ui/sample-overview.json` (shared), `stories/06-dashboard-ui/sample-vendors.json` (shared).

Commands: `npx vitest run` green; `npm run lint` clean; `npm run build` clean.

## 6. Files to touch

- New: `frontend/src/lib/ops.ts`, `frontend/vitest.config.ts`, `frontend/src/test-setup.ts`, `frontend/src/components/brief/BriefPage.tsx`, `frontend/src/components/brief/CycleSelector.tsx`, `frontend/src/components/brief/HeadlineFacts.tsx`, `frontend/src/components/brief/TriggerBanner.tsx`, `frontend/src/components/brief/ExceptionFeed.tsx`, `frontend/src/components/brief/SafetyStrip.tsx`, `frontend/src/components/brief/ActionsPanel.tsx`, `frontend/src/components/brief/__tests__/*`, `stories/05-brief-ui/sample-briefing.json`.
- Edit: `frontend/src/App.jsx`, `frontend/src/Header.jsx`, `frontend/src/styles.css`, `frontend/package.json`.
- Do not modify: `backend/**` (no backend changes in this story).
- Remove/replace: `frontend/src/data.js` (remove — data now from API), `frontend/src/components/TriggerBanner.jsx` (replace with API-driven version), `frontend/src/components/KpiPulse.jsx` (replace with dashboard component in Story 06), `frontend/src/components/AlertsSection.jsx` (replace with brief `ExceptionFeed`), `frontend/src/components/RecommendedActions.jsx` (replace with brief `ActionsPanel`).

## 7. Notes

- Current `App.jsx` is a single-page prototype with hardcoded `data.js` — replace hero content but keep `ChatPanel`, `DataQualityBar`, `Modals`, `Toast` until Story 07/08 cleanup.
- `routeTree.gen.ts` does not exist and is not needed — the app is plain Vite + React SPA. Do not introduce TanStack Start in this story.
- Keep `VITE_API_URL` inline error message verbatim: `"Set VITE_API_URL in frontend/.env"`.
- Backend `BriefingData` has no `triggers` field yet. The trigger banner must not crash when `triggers` is missing — use `(data as any).triggers ?? []`.
- Backend already truncates `copy_for_vendor` to ≤ 500 chars — frontend just calls `navigator.clipboard.writeText`.

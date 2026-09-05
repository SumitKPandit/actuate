# Frontend SPEC — Actuate Ops Brief (simple build)

**Location:** `frontend/` (this file). **Persona:** transport manager only; briefing is forwardable to transport & facilities head without rework. **Surface:** brief + dashboard + Q&A. **Status:** spec for implementation per `PLAN.md` + `stories/05-brief-ui`, `06-dashboard-ui`, `07-ask-narrate` contracts.

Visual reference only: `src/routes/mockup.tsx` (static data, no API calls — do not ship). Design tokens: `moveinsync.com-design.md` + `src/styles.css` (`island-shell`, `demo-button`, `demo-pill`, `demo-table`, `demo-alert-*`). No new design system.

## 1. Why (from `problem-statement/`)

Enterprise mobility ops (May–Jul 2026 slice: ~189k + ~211k + ~216k trips, 1.6M legs, 621k bills, 51.7k alerts, 513k feedback) is signal-rich but insight-poor. Managers assemble reports instead of acting. A metric without context is just a number — "OTA 93%" only matters as "vs SLA 95%, −2pp vs May, 2 vendors drive 68% of the gap."

The hackathon asks for an **agentic layer that senses → reasons → acts** with minimal prompting, serving the **transport manager** (day-to-day: vendor coordination, escalations, shift planning), contextualising every metric against **SLA / prior cycle / peer**, and combining: conversational Q&A + proactive triggers + auto narratives + anomaly insights + dashboard + vendor comms. Judged on business impact (35), agentic cost-at-scale (20), architecture (20), working demo (25). Messy data must be handled gracefully (see §5).

This frontend is the **Sense→Reason→Act surface**: it never computes KPIs — it renders what the backend reasons.

## 2. What backend supplies (contracts to code against)

Base: `VITE_API_URL` (see `.env.example`, default `http://127.0.0.1:8000`). All reads are mart-backed (`daily_kpi`, `vendor_kpi`, `office_kpi`, `insight_cache`); no raw-table scans, no CSV/DB access from frontend. Filters: `cycle` (e.g. `2026-06-H1`), `office`, `vendor`, `business_unit`. `%` rounded to 1 decimal, cost to 2.

| Method + path                                            | Used by                                 | Returns (frozen shapes, see `stories/04-ops-api/SPEC.md`)                                                                                                                                                                                                                                                           |
| -------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /overview?cycle=&office=&vendor=`                   | Dashboard cards                         | `{ trips, ota_pct, avg_delay_min, delay_reason_mix (late-only shares), no_show_rate, cost_per_trip, cost_per_km, zero_km_share, alert_rate_per_1k, sev1_count, ack_sla_met_share, csat_avg, low_rating_share }` + `benchmarks: { ota_sla: 95, ack_sla_min: 30 }`                                                    |
| `GET /insights?cycle=`                                   | Brief exception feed                    | Ranked insights `[{ id, kpi, scope{vendor,office,cycle}, current, baseline, delta_pp, severity(high/med/low), reach_trips, contribution_share, reason(vs_sla/vs_prior/vs_peer/anomaly), recommended_action, owner }]` (severity×reach rank; max age 6h)                                                             |
| `GET /briefing?cycle=` (`?narrate=true` later, Story 07) | Brief page (≤2 fetches with `/actions`) | `{ generated_at, headline_facts[3-5 template strings], insights_top5, safety_open_sev1, actions_top3, triggers[] }`. `triggers[]` = `{ trigger, fired, scope, current, baseline, insight_id }` (Sev-1 spike / OTA drop / cost outlier); empty array = no-fire, key may be missing pre-Story-08 — render defensively |
| `GET /vendors?cycle=&sort=ota\|cost\|alerts\|csat`       | Dashboard table                         | Rows `{ vendor, trips, ota, cost_per_trip, cost_per_km, alert_per_1k, csat, contribution_share, peer_rank }` + explicit `zero_km` / `UNSLABBED` counts as sub-text                                                                                                                                                  |
| `GET /actions?cycle=`                                    | Brief actions                           | `[{ id, action, owner, due_hint, copy_for_vendor (≤500 chars, vendor+KPI+cycle), status: proposed }]`                                                                                                                                                                                                               |
| `POST /actions/{id}/ack {actor}`                         | Brief Ack button                        | `{ id, status: "acked", actor, acked_at }`; unknown id → 404; idempotent                                                                                                                                                                                                                                            |
| `POST /ask {question, cycle?, scope?}`                   | Chat drawer                             | `{ sql (executed allowlisted SELECT, LIMIT ≤50), rows, narrative, grounded_from }`; off-intent/injection → **422 + `supported_intents`** (intents: OTA by vendor/office, cost outlier, Sev-1/open alerts, CSAT low cluster, no-show by shift/office)                                                                |
| Errors (all endpoints)                                   | Every view                              | Unknown cycle → 404 + valid cycle list; empty marts → 200 `{ data: null, warning: "marts empty — run ingest" }` — surface `warning` verbatim as banner, never blank page                                                                                                                                            |

KPI/benchmark/owner table (frozen, `PLAN.md §4`): OTA>15min late / SLA 95% → vendor; delay mix → vendor; no-show → office; cost/trip·cost/km·outliers (+`>₹16k` sanity flag) → ops; alert/1k·Sev-1·ack<30min → ops; CSAT excl. 0s, `<3`=low → vendor. Out of MVP: sustainability, GPS-trace replay.

## 3. Scope

**In:** two routes + one drawer + typed client, wired to the table above:

- `/` brief feed (Story 05), `/dashboard` KPI + vendor drill-down (Story 06), floating **Ask Actuate** drawer on both (Story 07), `src/lib/ops.ts` typed fetch client reused by both routes.
- Cycle selector defaulting to latest (options from 404 payload or `/overview` cycles); `generated_at` stamp; benchmark chips (OTA SLA 95% · Ack 30 min).

**Out:** any KPI math/ranking/narration in browser; heavy chart lib (CSS bars / inline SVG sparkline only, else cycle-Δ text); chat history persistence (single-session list ok); push delivery (banner only); auth; fuzzy vendor-name matching (display API canonical string); new endpoints (file follow-up, don't invent).

## 4. Information architecture (top→bottom)

**`/` Brief — "<30s: what slipped, who drives it, safety, next action":**

1. Cycle selector + `generated_at` + benchmark chips.
2. Trigger banner — red `demo-alert-danger` iff any `triggers[]` has `fired=true` (name + scope); hidden on `[]`/missing key; never crash.
3. Headline facts — 3–5 template strings verbatim (`?narrate=true` text is a drop-in swap later).
4. Ranked exceptions (top 5 cards): KPI · scope · current vs baseline Δ · severity badge · reach (trips) · contribution ("2 vendors = X% of gap") · recommended action + owner chip.
5. Safety strip: open Sev-1 + unacked count + oldest unacked age; "View by vendor" links to `/dashboard?vendor=`.
6. Actions top 3: owner + `proposed/acked` chips + **Copy-for-vendor** (clipboard exact string + toast) + **Ack** (`POST …/ack`, optimistic flip, error toast on 404).

**`/dashboard` — "where exactly + who owns it":** URL-persisted filters (`cycle, office, vendor, business_unit`; change → refetch `/overview` + `/vendors`); 6 KPI cards (OTA · delay+mix · no-show · cost/trip+cost/km+zero-km · alert/1k+Sev-1+ack share · CSAT+low share), each with current, Δ vs prior, benchmark badge (✓ green ≥SLA / ✗ red breach), peer context ("rank #3/23"); sortable vendor table (`sort=` values only; row click sets `?vendor=`); missing cells render `—`, never `0`.

**Chat drawer (both routes):** FAB → side drawer; shows question, narrative, mini table (≤50 rows), collapsible "SQL + sources" (`sql` + `grounded_from`); input with loading / error / 422 (`supported_intents` list) states.

## 5. Messy-data display rules (from dataset dictionary + `PLAN.md §6`)

`severity "False"`/null → count as **unclassified** (footnote when relevant, never hide); zero-km bills + null `slab_name` → explicit **zero-km / UNSLABBED** counts; `marshal_rating 0` = unrated (excluded from CSAT); negative km already nulled server-side; vendor strings shown as returned. Empty-marts `warning` → banner. Numbers use the API's rounding; no client-side recomputation.

## 6. Technical notes

- Stack as-is: TanStack Start (file routes; never hand-edit `routeTree.gen.ts`), TanStack Query or route `loader`, Tailwind + existing `demo-*`/`island-*` classes, Inter, flat cards (`8px`), pill CTAs (`30px`, green `#43B02A`, hover blue `#1E4A9B`), single-column mobile.
- `src/lib/ops.ts`: extend existing `getApiBaseUrl()` + typed fns per §2 row; throw on non-OK except map 404-cycle → fallback-to-latest and 422-ask → intents UI; missing `VITE_API_URL` → inline error naming the var. Brief needs ≤2 fetches; aggregate cards only, no per-row rendering.
- Keep header nav `/` ↔ `/dashboard` (retire `mockup`/`demo` links when removing starter cruft in Story 08).

## 7. Acceptance + verification

- [ ] Stubbed fixtures (match Story 04 schemas) render every §4 section with correct badges/numbers; `triggers:[{fired:true}]` → red banner, `[]`/missing → nothing; copy button copies exact string; ack flips via POST; `warning` → banner; loading skeletons present.
- [ ] Dashboard: 6 cards with deltas/badges, all 4 sorts reorder, URL filters round-trip on reload, missing → `—` + banner.
- [ ] Drawer: open/ask/render/SQL-sources/422 states against mocked fetch.
- [ ] `npm run build` + `eslint` clean; `/about` unaffected; no backend changes (mock at fetch boundary); live check `docker compose up --build` → `:3000` vs `:8000/docs` noted.
- Tests: Vitest + Testing Library (add minimal if missing): brief feed, trigger fire/no-fire + missing-key, copy, ack POST, empty warning, loading; dashboard cards/sort/filter-round-trip/empty. Manual live note per story folder.

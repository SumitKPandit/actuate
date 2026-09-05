# Story 09 — Technical Spec: Frontend↔API Foundation (typed client + test harness)

Companion to `SPEC.md`. Build blueprint: exact TS type contracts mirroring
Story 04 Pydantic schemas, client + hook module layout, harness wiring,
error-shape table, fixture snapshot procedure, and the test-first case
list. Derived from `stories/README.md`, Story 04 contracts
(`backend/src/backend/api/ops.py:24-121` + `backend/README.md:115`),
Story 05/06 SPECs (envelope consumption rules), the frontend scaffold
(`package.json`, `tsconfig.json`, `vite.config.ts`, `eslint.config.js`,
`.env.example`), and the live mart state (`actuate.db`).

Decisions locked while writing (no user round-trip; all marked `FROZEN`):
fail-fast env var, `Envelope<T>` return shape, `ApiError` body semantics,
`Promise.all` + first-warning rule, `useCycle` probe endpoint, harness
pins, and two `SPEC.md` amendments (dep list, `.env.example` status).
Anything Story 10 owns (component wiring, `data.js` deletion) is fenced
off, never stubbed with fake data.

## 1. Evidence summary

- **Backend contract is frozen and documented** (`ops.py:24-121`,
  `backend/README.md:115`): all five GETs return envelope
  `{data, warning}`; empty marts → `200 {"data": null, "warning":
  "marts empty — run ingest"}` (exact string); unknown/malformed cycle →
  `404 {"detail": "unknown cycle", "cycle", "valid_cycles": [...]}` via
  `JSONResponse` (**flat body** — `valid_cycles` is top-level, not under
  `detail`); bad `sort` → `422 {"detail": "invalid sort", "allowed":
  ["ota","cost","alerts","csat"]}`; `?narrate=true` → `422
  {"detail": "narrate lands in Story 07"}`; blank ack actor → `422
  {"detail": "actor must be non-blank"}`; unknown ack id → `404
  {"detail": "unknown action id", "id"}`; `POST /ask` → `501`. `ack`
  returns the **bare record** `{id, status, actor, acked_at}` — no
  envelope. `InsightSchema` is `extra="allow"` (Story 08 `triggers[]`
  rides in later).
- **Marts are populated (fixtures are real snapshots, not mocks).**
  Live `backend/actuate.db`: `daily_kpi` 92 rows, `vendor_kpi` 78,
  `office_kpi` 103, `insight_cache` 1 (`briefing:2026-06-H1` — cache
  warm). `valid_cycles` = `2026-05-H1 … 2026-07-H2` (6 labels, sorted).
  So the SPEC §2 fixture step is unblocked: boot the backend, `curl`
  four endpoints at `cycle=2026-06-H1`, save.
- **Frontend toolchain, as found** (`frontend/package.json`,
  `tsconfig.json`, `vite.config.ts`, `eslint.config.js`):
  - Runtime deps: React **19.2**, `lucide-react`, Tailwind **4** via
    `@tailwindcss/vite`. Build: Vite + `@vitejs/plugin-react` **6**.
    Node: v23.11.0.
  - TypeScript **6.0.2 is a devDep but no script runs it** (no
    `typecheck`/`build` type gate — `build` is bare `vite build`, esbuild
    strips types without checking). `tsconfig`: `noEmit`, `allowJs`,
    `checkJs: false`, `moduleResolution: "Bundler"`, include =
    `["src/**/*", "vite.config.ts"]` — a new `vitest.config.ts` at root
    is **not** included until the include list gains it (§2.7).
  - ESLint 9 flat config is ignores-only; flat-config default file set
    is `**/*.{js,mjs,cjs}` — **`.ts`/`.jsx` files are not linted** and
    adding them without a TS parser would crash lint. Consequence:
    `npm run lint` stays green trivially; TS correctness is enforced by
    the new `typecheck` script, not ESLint (§2.7, §9).
  - `frontend/.env.example` **already exists** (commit `c0517ed`) with
    `VITE_API_URL="http://127.0.0.1:8000"` — SPEC §2 lists it as new;
    amendment: verify-only, no write.
  - `frontend/src/lib/` is empty; all components are `.jsx` on mock
    `data.js`; `App.jsx` routes via `?page=`. No test infra of any kind.
- **Version pins (FROZEN ranges at install time):** `vitest ^4`
  (amended during install: `vitest ^3` bundles vite ≤7, incompatible with
  `@vitejs/plugin-react` 6.1.1's `vite ^8` peer; vitest 4.1.11 peers
  `vite ^6||^7||^8` and dedupes with the installed vite 8.2.2 — API used
  here is unchanged), `jsdom ^26`, `msw ^2` (v2 API:
  `setupServer`/`http`/`HttpResponse`),
  `@testing-library/react ^16` (React 19 support; requires
  `@testing-library/dom ^10` as peer — **not in SPEC §2's dep list**),
  `@testing-library/jest-dom ^6`. All devDeps; zero new runtime deps.

## 2. Design decisions (FROZEN)

1. **Envelope-aware client, no unwrapping.** Every GET returns
   `Envelope<T> = {data: T | null, warning: string | null}` verbatim —
   the caller (hook or component) decides how to surface `warning`
   (Stories 05–06 rule: banner, verbatim). Only `ackAction` returns the
   bare ack record (backend has no envelope on POST). Non-2xx → throw
   `ApiError`; the client never returns `undefined` on failure.
2. **Env: fail-fast beats silent default.** SPEC §3.1 says both
   "default `http://127.0.0.1:8000`" and "missing env var → inline
   error" — contradictory in code. Locked resolution: `apiBase()` reads
   `import.meta.env.VITE_API_URL`; falsy (unset **or** empty) → throw
   `Error("Set VITE_API_URL in frontend/.env")` at call time (SPEC's
   verbatim string). The "default" survives as documentation, not
   behavior: `.env.example` carries it, dev copies it, and test-setup
   pins it (§3.4). Rationale: a silent localhost fallback masks
   misconfiguration in deployed builds; fail-fast is testable
   (`vi.stubEnv`) and the error string is SPEC-mandated.
3. **Types mirror `ops.py:24-121` field-for-field** (§3.2 table) —
   hand-written interfaces, no codegen dependency (backend is the single
   source; the fixtures conformance test + typecheck are the drift
   alarm). `BriefingData` gains `triggers?: unknown[]` (optional
   passthrough — Story 08 fills it; absent today, never fabricated).
   `InsightSchema` mirrors the frozen keys; backend `extra="allow"`
   means unknown keys may appear — TS type carries the known set, and
   fixtures may carry extras (documented, allowed).
4. **`ApiError` carries `status` + parsed `body`.** `body` = parsed JSON
   when the response body is JSON, else `{raw: text}` — never `undefined`
   (network failure throws the original `TypeError` instead, per SPEC
   "no silent undefined"). `message` = `body.detail` when it is a string,
   else `"HTTP {status}"`. One class, no subclasses per status — callers
   branch on `.status`/`.body.valid_cycles`/`.body.allowed` (§5).
5. **`useOpsData` = `Promise.all` of three GETs, one state update.**
   Shape: `{data: {briefing, actions, overview} | null, warning: string |
   null, loading: boolean, error: Error | null, refetch}`. First
   non-null `warning` wins (in practice all three carry the identical
   `EMPTY_WARNING`; no dedup logic beyond first-hit). Any rejection →
   `error` set (first rejection reason), `data: null`. Stale-response
   guard: effect-scoped `cancelled` flag ignores resolutions after
   cycle/refetch change; `fetch` itself is not aborted (KISS — responses
   are cheap, backend briefing cache makes reloads ~free).
6. **`useCycle` probes with `getBriefing`** (the endpoint Story 10's UI
   needs first; any GET 404s identically). One probe on mount while
   `cycles === null`; success → cycle stays `2026-06-H1` (`cycles` stays
   `null` — a 200 proves one cycle valid but not the full set);
   `ApiError` 404 → `valid_cycles` non-empty → `cycle =
   valid_cycles[0]`, `cycles = valid_cycles`; 404 with empty/missing
   list → keep `2026-06-H1`, `cycles = []`; network failure → keep
   default, `cycles` stays `null` (mount must never crash; no error
   surface — SPEC exposes only `{cycle, setCycle, cycles}`). Known cost:
   one extra briefing call per mount alongside `useOpsData`'s — backend
   6h cache absorbs it; Story 10 may dedupe (§9).
7. **Harness + type gate.** `vitest.config.ts` (standalone — Vitest
   auto-prefers it over `vite.config.ts`; react plugin reused, Tailwind
   plugin omitted — no CSS in unit tests), `environment: 'jsdom'`,
   `globals: false` (explicit imports), `css: false`,
   `setupFiles: ['src/test-setup.ts']`. `test-setup.ts`: jest-dom matchers,
   `import.meta.env.VITE_API_URL ||= 'http://127.0.0.1:8000'` (keeps
   tests deterministic without a local `.env`), msw `setupServer` with
   `onUnhandledRequest: 'error'` + `beforeAll/afterAll` lifecycle +
   `resetHandlers` per test. `package.json` gains `"test": "vitest run"`
   and `"typecheck": "tsc --noEmit"`; `tsconfig.json` include gains
   `vitest.config.ts`. SPEC §2 dep-list amendment: **+`jsdom`**
   (vitest DOM environment) and **+`@testing-library/dom`** (RTL v16
   peer). No ESLint config change — flat config ignores `.ts` by default,
   lint stays green as-is (§9 documents the gap).
8. **Fixtures: real snapshots + runtime conformance.** Four files
   snapshot the running backend at `cycle=2026-06-H1` (§3.6 procedure).
   Conformance is **runtime** required-field checks in
   `fixtures.test.ts` (vitest/esbuild strips types, so a
   compile-time-only test would have no teeth); `npm run typecheck`
   provides the type-level half over `src/**` (fixtures read via
   `fs` + `JSON.parse`, never `import` — keeps JSON out of the TS
   module graph, no `resolveJsonModule` needed).
9. **No component, no backend, no `data.js` changes.** `lib/ops.ts` is
   imported by nothing until Story 10 → `npm run build` output is
   unchanged (tree-shaken dead code), satisfying "build clean" without
   scope creep. `POST /ask` stays out of the client (501 stub; Story 07).

## 3. Static contracts

### 3.1 Module layout (`frontend/src/lib/ops.ts`)

```text
// Types (mirror ops.py:24-121 — §3.2):
OverviewData, BriefingData, InsightSchema, VendorRow, ActionItem,
AckRequest, AckResponse
Envelope<T> = {data: T | null, warning: string | null}
VendorSort   = 'ota' | 'cost' | 'alerts' | 'csat'
class ApiError extends Error {status: number; body: unknown}

// Helpers (private, <15 lines each):
apiBase()                 # §2.2 fail-fast
async parseBody(res)      # JSON parse; failure -> {raw: text}
async request<T>(path)    # fetch -> !ok -> ApiError(status, body) -> envelope JSON

// Public API:
getOverview(cycle):  Promise<Envelope<OverviewData>>     # GET /overview?cycle=
getBriefing(cycle):  Promise<Envelope<BriefingData>>     # GET /briefing?cycle=
getInsights(cycle):  Promise<Envelope<InsightSchema[]>>  # GET /insights?cycle=
getActions(cycle):   Promise<Envelope<ActionItem[]>>     # GET /actions?cycle=
getVendors(cycle, sort='ota'): Promise<Envelope<VendorRow[]>>  # sort ∈ VendorSort
ackAction(id, actor): Promise<AckResponse>               # POST /actions/{id}/ack {actor}
```

Query strings via `URLSearchParams`; `sort` always sent (default
`'ota'`); `cycle` required — no caller-side default (the default cycle
belongs to `useCycle`, §3.5). No retry, no timeout, no AbortController.

### 3.2 Type mapping (`ops.py` → `ops.ts`, field-for-field)

| TS type | Fields (all exact names) |
|---|---|
| `OverviewData` | `trips: number \| null`; `ota_pct, avg_delay_min, no_show_rate, cost_per_trip, cost_per_km, zero_km_share, alert_rate_per_1k, ack_sla_met_share, csat_avg, low_rating_share: number \| null`; `sev1_count: number \| null`; `delay_reason_mix: Record<string, {count: number \| null; share: number \| null}> \| null`; `benchmarks: {ota_sla: number; ack_sla_min: number} \| null` |
| `BriefingData` | `generated_at: string`; `headline_facts: string[]`; `insights_top5: InsightSchema[]`; `safety_open_sev1: number`; `actions_top3: ActionItem[]`; `triggers?: unknown[]` (optional — Story 08) |
| `InsightSchema` | `id: string`; `kpi: string`; `scope: Record<string, unknown>`; `current, baseline, delta_pp, contribution_share: number \| null`; `severity: string`; `reach_trips: number`; `reason, recommended_action, owner: string` (backend `extra="allow"`: unknown extra keys may appear; TS carries the frozen set) |
| `VendorRow` | `vendor: string`; `trips: number \| null`; `ota_pct, cost_per_trip, cost_per_km, alert_rate_per_1k, csat_avg, low_rating_share, contribution_share: number \| null`; `peer_rank, zero_km_count, unslabbed_count: number \| null` |
| `ActionItem` | `id, action, owner, due_hint, copy_for_vendor, status: string` |
| `AckRequest` | `{actor: string}` (backend `extra="forbid"` — client sends exactly `{actor}`) |
| `AckResponse` | `{id, status, actor, acked_at: string}` |
| `Envelope<T>` | `{data: T \| null; warning: string \| null}` |
| `VendorSort` | `'ota' \| 'cost' \| 'alerts' \| 'csat'` (mirrors §5 allowed list) |

### 3.3 Error shapes (backend-verbatim — `ApiError.body` cases)

| Trigger | Status | Body (verbatim keys) |
|---|---|---|
| Unknown/malformed cycle (all GETs) | 404 | `{"detail": "unknown cycle", "cycle": "…", "valid_cycles": ["…"]}` — flat; `valid_cycles` top-level |
| `sort` outside allowed | 422 | `{"detail": "invalid sort", "allowed": ["ota","cost","alerts","csat"]}` |
| `?narrate=true` on briefing | 422 | `{"detail": "narrate lands in Story 07"}` |
| Ack blank `actor` | 422 | `{"detail": "actor must be non-blank"}` |
| Ack unknown id | 404 | `{"detail": "unknown action id", "id": "…"}` |
| `POST /ask` | 501 | `{"detail": "reserved for Story 07 (NL-to-SQL over marts)"}` (route absent from client — listed for completeness) |
| Marts empty | 200 | `{"data": null, "warning": "marts empty — run ingest"}` — **not an error**; flows through the envelope |
| Transport failure | — | `fetch` rejects (original `TypeError` propagates; never wrapped, never swallowed) |

### 3.4 Harness layout

```text
frontend/vitest.config.ts        # defineConfig from 'vitest/config'; plugins: [react()];
                                 # test: {environment 'jsdom', setupFiles ['src/test-setup.ts'],
                                 #        globals false, css false, include defaults}
frontend/src/test-setup.ts       # jest-dom matchers; VITE_API_URL pin; export msw `server`
                                 # (setupServer(...handlers)); beforeAll listen /
                                 # afterEach resetHandlers / afterAll close
frontend/src/lib/__tests__/
  ops.test.ts                    # §6.1
  useCycle.test.jsx              # §6.2 (renderHook)
  useOpsData.test.jsx            # §6.3 (renderHook)
  fixtures.test.ts               # §6.4 (node fs — no msw)
```

Handlers live per-test-file (each file owns its routes — no shared
handler module until Story 10 needs one). `onUnhandledRequest: 'error'`
keeps accidental endpoint drift loud.

### 3.5 Hook signatures (plain `.js`, matching the `.jsx` codebase; `checkJs` off)

```text
useCycle()  -> {cycle: string, cycles: string[] | null, setCycle}
  state: cycle ('2026-06-H1'), cycles (null)
  effect (mount-only): if cycles === null -> getBriefing(cycle)
    200            -> no state change (cycles stays null)
    ApiError 404   -> vc = body.valid_cycles; non-empty -> {cycle: vc[0], cycles: vc}
                                                    empty/absent -> {cycle unchanged, cycles: []}
    other/throw    -> no state change (silent-by-design; §2.6)
  setCycle(c)      -> manual override (Story 10 selector); skips the probe

useOpsData(cycle) -> {data, warning, loading, error, refetch}
  data:    {briefing, actions, overview} | null   # keys = the three GETs
  warning: string | null                          # first non-null envelope warning
  loading: boolean                                # true while in flight
  error:   Error | null                           # first rejection (ApiError|TypeError)
  refetch(): void                                 # bump -> effect re-runs
  effect [cycle, tick]: loading true -> Promise.all([getBriefing, getActions,
    getOverview](cycle)) -> one setState {data, warning, loading:false} /
    catch -> {error, data:null, loading:false}; cancelled flag guards stale set
```

### 3.6 Fixture snapshot procedure (real responses — SPEC §7 note)

```bash
cd backend && uv run uvicorn backend.app:app --port 8000 &   # marts already populated
curl -s 'http://127.0.0.1:8000/briefing?cycle=2026-06-H1'  > stories/05-brief-ui/sample-briefing.json
curl -s 'http://127.0.0.1:8000/overview?cycle=2026-06-H1'  > stories/06-dashboard-ui/sample-overview.json
curl -s 'http://127.0.0.1:8000/vendors?cycle=2026-06-H1'   > stories/06-dashboard-ui/sample-vendors.json
curl -s 'http://127.0.0.1:8000/insights?cycle=2026-06-H1'  > stories/06-dashboard-ui/sample-insights.json
```

Cycle FROZEN: `2026-06-H1` (SPEC default, cache warm, within
`valid_cycles`). Files are the full envelope `{data, warning}` verbatim
— no hand-editing, no pretty-print contract (readers parse JSON). If a
snap shows `{"data": null, "warning": "marts empty — run ingest"}`, the
ingest step (`backend/README.md:75`) runs first — never commit an
empty-snapshot as a fixture.

## 4. Functional contracts

1. **`getOverview(cycle)`** — `GET {base}/overview?cycle={cycle}` →
   envelope. Success → `data` = §3.2 `OverviewData` (all 14 keys,
   `null`s preserved — frontend renders `—`, never `0`).
2. **`getBriefing(cycle)`** — same shape on `/briefing`; also the
   `useCycle` probe. (Client never sends `narrate` — Story 07 owns it.)
3. **`getInsights(cycle)`** — `data` = `InsightSchema[]` in backend
   rank order (client never re-sorts; Story 10 uses prior-cycle deltas).
4. **`getActions(cycle)`** — `data` = `ActionItem[]`; `status` ∈
   `proposed | acked` (ack overlay applied server-side).
5. **`getVendors(cycle, sort='ota')`** — `sort` ∈ `VendorSort`;
   `data` = `VendorRow[]` sorted + `peer_rank`ed server-side (client
   never re-ranks — §4.4 of Story 04 is the contract).
6. **`ackAction(id, actor)`** — `POST {base}/actions/{id}/ack`, JSON
   body exactly `{"actor": actor}`; returns the record verbatim. Actor
   non-blank is the backend's rule (422); client sends as-is (blank
   actor is a caller bug, tested §6.1).
7. **`getCycle` fallback chain is `useCycle`'s job, not the client's** —
   client functions are cycle-parametric, zero hidden state.

## 5. Errors + edge cases (client-side; must never throw raw non-Error)

| Input | Result |
|---|---|
| `VITE_API_URL` unset/empty | `Error("Set VITE_API_URL in frontend/.env")` at call time (§2.2) |
| 2xx envelope | `{data, warning}` returned verbatim; `warning` may be the empty-marts string — not an error |
| 404 cycle | `ApiError{status:404, body.valid_cycles}` — `useCycle` consumes |
| 422 sort / narrate / ack | `ApiError` with `body.allowed` / `body.detail` |
| Network down / DNS / CORS-refused | original `TypeError` from `fetch` propagates — no `undefined`, no retry |
| Malformed JSON on 2xx | `parseBody` failure → throw (never return partial envelope) |
| `useOpsData` one of three rejects | `error` set, `data: null`, `loading: false`; no partial data (Promise.all semantics, §2.5) |
| `useOpsData` cycle changes mid-flight | stale resolution discarded (cancelled flag) |
| `useOpsData` refetch double-fire | last tick wins; in-flight guards via effect re-run + cancelled flag |
| `useCycle` network failure on mount | default cycle kept, `cycles: null` — UI must render, Story 10 decides messaging |
| Fixture missing/renamed | `fixtures.test.ts` fails with explicit file-not-found (no silent skip) |

## 6. Test plan (test-first, per AGENTS.md)

Order: harness smoke (§6.0) → `ops.test.ts` red → `ops.ts` green →
hook tests red → hooks green → fixtures snapshot → `fixtures.test.ts`
red → snapshot verify green. Every step's red/green confirmed in
terminal output.

**§6.0 Harness smoke (one commit with harness):** trivial test asserts
`import.meta.env.VITE_API_URL` is the pinned URL — proves jsdom,
setupFiles, and env pin all wired before any real test is written.

**§6.1 `ops.test.ts`** (msw handlers, per route):

- `getOverview` success → envelope shape `{data, warning: null}`;
  handler-captured URL has `cycle` param; same pattern for
  `getBriefing` / `getInsights` / `getActions`.
- `getVendors('c', 'cost')` → captured query `sort=cost`; default-arg
  call → `sort=ota`.
- Empty-marts envelope `{data: null, warning: "marts empty — run
  ingest"}` → returned verbatim (warning ≠ error).
- 404 handler → `ApiError`, `status === 404`,
  `body.valid_cycles` array, `message === 'unknown cycle'`.
- 422 handler → `status === 422`, `body.allowed`.
- Network failure (`server.use` abort handler) → rejects (not
  `undefined`).
- `ackAction('id-1', 'Priya')` → captured body deep-equals
  `{actor: 'Priya'}` (extra: none), response = bare
  `{id, status: 'acked', actor, acked_at}`.
- Missing env: `vi.stubEnv('VITE_API_URL', '')` → call rejects with
  the verbatim `"Set VITE_API_URL in frontend/.env"`; `vi.unstubAllEnvs()`.

**§6.2 `useCycle.test.jsx`** (`renderHook`, msw):

- Briefing 200 → `cycle === '2026-06-H1'`, `cycles === null`.
- 404 + `valid_cycles: ['2026-07-H1','2026-07-H2']` →
  `cycle === '2026-07-H1'`, `cycles` = that array.
- 404 with `valid_cycles: []` → cycle unchanged, `cycles === []`.
- Network failure → cycle unchanged, `cycles` null.
- `setCycle('2026-05-H1')` → cycle updates, no extra probe (handler
  call-count asserted).

**§6.3 `useOpsData.test.jsx`**:

- All three 200 → single settle: `loading` false, `data` has all three
  keys (Promise.all semantics), `warning` null.
- One envelope warning → `warning` verbatim, `data` still set.
- One route 500s → `error` set (ApiError), `data` null, `loading` false.
- `refetch()` → handler call count +1, state stays consistent.
- Cycle change → new fetch issued, stale resolution ignored (delayed
  first handler).

**§6.4 `fixtures.test.ts`** (fs-based runtime conformance — §2.8):

- Each of the 4 files: parses; `warning` is `null` or string; `data`
  non-null (a null-data snapshot fails the commit — §3.6).
- `overview`: all 14 `OverviewData` keys present; `benchmarks` has
  `ota_sla`/`ack_sla_min`.
- `briefing`: `headline_facts` length ≥ 3; `insights_top5` ≤ 5, each
  with `id/kpi/scope/severity/reach_trips`; `actions_top3` each with
  `copy_for_vendor` length ≤ 500; `safety_open_sev1` number.
- `vendors`: non-empty; every row has `vendor` string + `peer_rank`
  int ≥ 1; all 12 `VendorRow` keys present.
- `insights`: non-empty; every item has the 12 frozen `InsightSchema`
  keys; `severity` ∈ `high|medium|low`.

Commands (from `frontend/`): `npx vitest run` (or `npm test`) green →
`npm run lint` → `npm run typecheck` → `npm run build` → from
`backend/`: `uv run pytest` (regression: backend untouched).

## 7. Acceptance mapping (SPEC §4)

1. Per-function envelope/404/422/network → §6.1 cases.
2. `ackAction` body + record → §6.1 ack case.
3. `useCycle` 404 resolution + `useOpsData` states → §6.2/§6.3.
4. Fixtures conform → §6.4 (+ `typecheck` half, §2.8).
5. `vitest run` / `lint` / `build` / `uv run pytest` → §6 commands,
   all green in terminal before close.

## 8. Files to touch (final list)

- New: `frontend/src/lib/ops.ts`, `frontend/src/lib/useCycle.js`,
  `frontend/src/lib/useOpsData.js`,
  `frontend/src/lib/__tests__/{ops.test.ts, useCycle.test.jsx,
  useOpsData.test.jsx, fixtures.test.ts, harness.test.ts}`,
  `frontend/vitest.config.ts`, `frontend/src/test-setup.ts`,
  `frontend/src/vite-env.d.ts` (vite/client types for
  `import.meta.env` — required by the `typecheck` gate), and the 4
  fixture JSONs (§3.6 paths).
- Edit: `frontend/package.json` (devDeps §1 + `test` + `typecheck`
  scripts), `frontend/tsconfig.json` (include += `vitest.config.ts`).
- Verify-only (SPEC §2 amendment — already correct, commit `c0517ed`):
  `frontend/.env.example`.
- Do not modify: `backend/**`, `frontend/src/App.jsx`,
  `frontend/src/data.js`, any component, `vite.config.ts`,
  `eslint.config.js` (Story 10 owns wiring; Story 07 owns `/ask`).

## 9. Risks + follow-ups (not this story)

- **ESLint gap:** flat config lints `.js/.mjs/.cjs` only — `ops.ts` and
  tests are outside lint scope. Green lint ≠ linted TS. Follow-up:
  `typescript-eslint` parser + files override (config-only, separate
  change; not smuggled in here).
- **Duplicate briefing fetch** (useCycle probe + useOpsData) per mount.
  Backend 6h cache makes it cheap; if it matters, Story 10 lifts cycle
  resolution into a context or reuses the `useOpsData` response.
- **Fixture staleness:** snapshots freeze one cycle's numbers
  (`generated_at` included). Conformance tests assert *shape*, never
  values — re-snapshot only when the backend contract changes (then
  Stories 05–06 docs note the refresh).
- **React 19 + RTL:** requires `@testing-library/react ^16` +
  `@testing-library/dom`; `act` environment handled by RTL 16.1+. If a
  peer warning appears at install, pin `@testing-library/dom@^10`
  explicitly (already in the dep list, §1).
- **`import.meta.env` in vitest:** set up by Vitest automatically; the
  test-setup pin guarantees determinism, and `vi.stubEnv` covers the
  missing-env path — no `.env` file required to run tests (CI-safe).
- **`triggers?: unknown[]`** is deliberately optional+unknown: Story 08
  will widen it server-side first, then a one-line client type update —
  the passthrough type means Story 08 cannot break this client
  compile-time or runtime.

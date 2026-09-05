# Story 10 - Technical Spec: Live API Integration and Ack Write-Path

Companion technical specification for `SPEC.md`. This document is the implementation blueprint for replacing the frontend mock data with the Story 04 API contracts while preserving the existing single-page layout.

The design is derived from:

- Story 04's frozen ops API in `backend/src/backend/api/ops.py`.
- Story 09's typed client, hooks, msw harness, and real response fixtures.
- The existing frontend components and `frontend/src/data.js` consumers.
- `backend/src/backend/core/reason.py` insight and delta semantics.
- The two implementation decisions confirmed during planning: `?vendor=` is a row-selection URL state, and the KPI drilldown is wired to live data while the decorative Header filters remain unchanged.

Anything not explicitly changed here remains outside this story's scope. In particular, `backend/**`, `frontend/src/lib/ops.ts`, the Story 07 chat API, and push-trigger behavior are not changed.

## 1. Evidence Summary

### 1.1 Story 09 foundation

Story 09 already provides the data transport primitives that Story 10 must consume:

- `frontend/src/lib/ops.ts` exposes `getOverview`, `getBriefing`, `getInsights`, `getActions`, `getVendors`, and `ackAction`.
- All GET functions return `Envelope<T>` without unwrapping `{data, warning}`.
- `ackAction` returns the backend's bare `{id, status, actor, acked_at}` record.
- `ApiError` preserves the HTTP `status` and parsed response `body`.
- `useCycle` provides the default cycle and `valid_cycles` fallback behavior.
- `useOpsData` fetches briefing, actions, and overview together and applies the first non-null warning.
- `frontend/src/test-setup.ts` provides the msw server with `onUnhandledRequest: 'error'`.
- The real fixture files are:
  - `stories/05-brief-ui/sample-briefing.json`
  - `stories/06-dashboard-ui/sample-overview.json`
  - `stories/06-dashboard-ui/sample-insights.json`
  - `stories/06-dashboard-ui/sample-vendors.json`

The three-key `useOpsData` result shape and `frontend/src/lib/ops.ts` client are treated as frozen Story 09 contracts. Story 10 adds focused hooks for the independent `/insights` and `/vendors` queries rather than changing the existing hook's result shape.

### 1.2 Backend response contract

The backend contract is frozen in `backend/src/backend/api/ops.py`:

- `EMPTY_WARNING` is the exact string `marts empty — run ingest` (`ops.py:20`).
- `/overview`, `/briefing`, `/insights`, `/actions`, and `/vendors` return `{data, warning}` envelopes.
- Empty marts return HTTP 200 with `data: null` and the warning; this is not an API error.
- Unknown cycles return HTTP 404 with a flat body containing `detail`, `cycle`, and `valid_cycles` (`ops.py:406-410`).
- Invalid vendor sort returns HTTP 422 with `detail: "invalid sort"` and an `allowed` array (`ops.py:640-642`).
- Unknown action ids return HTTP 404 with `detail: "unknown action id"` and `id` (`ops.py:763-766`).
- Ack requests reject a blank actor with HTTP 422; the frontend always sends the fixed actor `Transport Manager`.
- Ack success is a bare record, not an envelope (`ops.py:750-776`).
- `/ask` remains reserved for Story 07.

`_action_from_insight` uses the insight id as the action id (`ops.py:353-389`). Therefore an alert card and a recommended-action card referring to the same insight use the same ack endpoint and status identity.

### 1.3 Insight and delta semantics

`backend/src/backend/core/reason.py` defines the KPI ids as `ota_pct`, `sev1`, `ack`, `cost`, `csat`, and `no_show` (`reason.py:30`). The frontend's six existing KPI slots are mapped to the available overview fields; they are not renamed or expanded in this story.

For KPI deltas:

- Select the all-scope `vs_prior` insight for the relevant KPI, where `scope.vendor` and `scope.office` are both null.
- `baseline` is the prior-cycle value.
- `delta_pp` is an absolute percentage-point delta for ordinary rate/value KPIs.
- `cost` uses a relative percentage change for `delta_pp` (`reason.py:177`, `reason.py:234`) and must be rendered as `%`, not `pp`.
- A missing baseline or missing matching insight produces no invented delta and renders `—`.
- `avg_delay` has no corresponding reason KPI in the current insight builder, so its delta is `—` until a backend contract supplies one.
- `sev1` does not currently have an all-scope `vs_prior` insight in the fixture state, so its delta is also `—`.

`contribution_share` is calculated as `excess / total` and returned as a fraction between 0 and 1 (`reason.py:258`). A value of `0.31` is displayed as `31%`; null displays as `—`.

### 1.4 Existing frontend state

Before Story 10:

- `App.jsx` imports `kpis`, `alerts`, `recommendedActions`, and `initialIncidents` from `data.js`.
- `ChatPanel.jsx` imports `suggestionPills` from `data.js`.
- `TriggerBanner` always renders a hardcoded OTA trigger.
- `KpiPulse` contains hardcoded OTA drilldown values, a hardcoded CSAT delta, and a hardcoded safety timing value.
- `Header` contains a hardcoded cycle list and decorative Office, Vendor, and BU controls.
- `App.jsx` performs local-only action approval, incident acknowledgement, and hardcoded vendor-message generation.
- `AlertsSection` expects rich mock-only fields such as breakdown objects, copy metadata, unacknowledged counts, and review-alert flags.
- `RecommendedActions` expects mock-only `ownerTone`, `hasCopy`, `vendorName`, and `vendorOta` fields.

Story 10 removes mock-only data dependencies instead of fabricating API values for fields that do not exist in the frozen API.

### 1.5 Tooling constraints

- Tests use Vitest 4, jsdom, React Testing Library 16, and msw 2.
- The msw server must continue to reject unhandled requests.
- jsdom does not provide a usable clipboard implementation by default; clipboard tests must stub `navigator.clipboard.writeText`.
- The current ESLint flat config is ignores-only. Its default file selection does not lint the existing `.jsx` or `.ts` files. This known Story 09 gap is not expanded in Story 10.
- `npm run typecheck` checks TypeScript but JavaScript files use the existing `checkJs: false` convention.

## 2. Design Decisions

The following decisions are frozen for implementation.

### 2.1 Adapter-first UI wiring

`frontend/src/lib/adapters.js` contains pure mapping and formatting functions. It does not fetch data, own React state, or import components.

Adapters return the prop shapes needed by the existing components, reducing component churn while removing mock-only fields. All API values are formatted centrally so null handling is consistent.

### 2.2 Independent query hooks

Add:

- `frontend/src/lib/useInsights.js` for KPI prior-cycle data.
- `frontend/src/lib/useVendors.js` for the sort-dependent vendor query.

Both hooks follow the Story 09 effect pattern: one request per dependency change, a cancellation guard, `loading`, `error`, and `warning` state.

`useOpsData` remains unchanged so its established `{briefing, actions, overview}` result contract remains stable.

### 2.3 KPI cards remain six cards

The existing six slots remain:

1. OTA.
2. Avg Delay.
3. No-show.
4. Cost / Trip.
5. Safety Sev-1.
6. CSAT.

The safety value comes from `briefing.data.safety_open_sev1`, as required by the story mapping. The overview `sev1_count` may be used only as a defensive fallback when the briefing value is absent, not as a competing display value.

Values with no API source are removed or rendered as `—`; they are not retained as hardcoded numbers. This includes the mock safety `unacknowledged` count, `47m max`, and CSAT `↓ 0.08` text.

### 2.4 Delta selection and formatting

The adapter selects the first all-scope `vs_prior` insight for each KPI. If no matching insight exists, the card omits the delta row and displays a neutral `—` prior-cycle note.

Delta formats are:

- `ota_pct`, `no_show`, and `csat`: signed `pp` values.
- `cost`: signed relative `%` values.
- `avg_delay` and `sev1`: `—` when no matching insight exists.

Adverse movement determines the delta tone:

- Lower OTA is adverse.
- Higher delay is adverse.
- Higher no-show is adverse.
- Higher cost is adverse.
- Higher Sev-1 count is adverse.
- Lower CSAT is adverse.

### 2.5 User decision: live drilldown, unchanged decorative filters

The OTA drilldown in `KpiPulse` is wired to live current value, SLA, and prior-cycle delta. Missing values display `—`.

The Header's Office, Vendor, and BU selects remain untouched in this story. They are decorative controls from the prototype and are flagged for the Story 08 documentation pass rather than being given partially implemented behavior.

### 2.6 URL state

The URL persists:

- `cycle`: global cycle selected by the Header.
- `vendor`: selected vendor row for visual selection restoration.

`?vendor=` is deliberately row selection only. It does not filter or refetch `/overview` or `/vendors`, because `/vendors` has no vendor filter contract and Story 10 forbids backend changes.

The selected vendor is highlighted when the URL is loaded. Clicking the selected row again clears the parameter. `history.replaceState` is used to avoid adding a browser-history entry for every filter change.

Vendor sort is local component state and is not persisted because the Story 10 acceptance criterion only requires `cycle` and `vendor` URL round-tripping.

### 2.7 Ack state machine

Ack state is kept in `App.jsx` because both the recommended-action cards and exception cards need the same optimistic state.

State consists of:

- `ackOverrides`: action id to optimistic status, currently only `acked`.
- `ackPending`: action ids currently awaiting the POST response.
- Base statuses from the `/actions` payload.

Displayed status precedence is:

```text
ackOverrides[id] ?? actionsStatusById[id] ?? action.status ?? "proposed"
```

Approval sequence:

1. Ignore the click if the action is already acked or pending.
2. Set the optimistic override to `acked`.
3. Add the id to `ackPending`.
4. Call `ackAction(id, "Transport Manager")`.
5. On success, retain the optimistic status and show a success toast.
6. On 404, 422, or any other failure, remove the override and show an error toast.
7. Always remove the id from `ackPending`.

No immediate refetch occurs after a successful ack. The server state is retrieved during the next cycle refresh or explicit refetch, while the local optimistic state prevents a visual reversal during the current session.

### 2.8 Copy-for-vendor

The only copy source is the API's exact `action.copy_for_vendor` string. The old `App.jsx` template is deleted.

The clipboard call is guarded so unsupported or denied clipboard access does not crash the UI. The success toast may display the copied string, but the clipboard assertion must verify the exact API value.

Alert cards do not render a copy button because insights do not contain `copy_for_vendor`. Recommended-action cards retain the copy button.

### 2.9 Trigger forward compatibility

The trigger adapter accepts the optional, currently unknown `BriefingData.triggers` field defensively:

```text
Array.isArray(briefing.triggers)
  ? briefing.triggers.filter((trigger) => trigger?.fired === true)
  : []
```

The banner renders nothing when the result is empty. For the first fired trigger, it displays:

- `name`, with `insight_id` or `Operational trigger` as a fallback.
- `scope`, supporting string, vendor, office, or a safe `all` fallback.

The existing dismiss, restore, and review interactions remain. Hardcoded cycle and refresh text is replaced by the active cycle; the fabricated `Refresh 14m ago` value is removed.

### 2.10 Surface states

The brief surface owns the combined `useOpsData` state:

- Loading: skeleton blocks.
- Error: error banner with the API error message.
- Empty marts: verbatim warning banner; no blank page and no attempt to render null data as zero.
- Success: render mapped sections.

The `/insights` query degrades independently. If it fails, current values still render and deltas become `—`.

The vendor table owns its own loading, error, warning, and empty states. A vendor query failure must not blank the brief.

### 2.11 Static modal state

The safety modal remains static until Story 08, except for its total open count. Its static incident fixtures and local incident acknowledgement state move into `Modals.jsx` so deleting `data.js` does not delete the static modal prototype.

`SafetyModal.totalOpen` receives the live `safety_open_sev1` count. The modal's incident queue is explicitly not an API integration in Story 10.

### 2.12 ChatPanel deferral

The ChatPanel shell remains, but the mock conversation, suggestion pills, fake classifications, and mock response bodies are removed. The content area displays a disabled `Ask lands in Story 07` state, and the input/send control is disabled.

After this removal, `data.js` has no remaining consumer and is deleted.

## 3. Static Contracts

### 3.1 Module layout

```text
frontend/src/lib/adapters.js
  fmtKpiValue(kpi, value)
  fmtShare(value)
  fmtDelta(kpi, deltaPp)
  findPriorInsight(insights, kpi)
  getFiredTriggers(briefing)
  buildKpis(overview, insights, safetyOpenSev1)
  buildAlerts(insightsTop5)
  buildActions(actionsTop3, actionsList, statusById, ackOverrides)

frontend/src/lib/useInsights.js
  useInsights(cycle) -> {data, warning, loading, error, refetch}

frontend/src/lib/useVendors.js
  useVendors(cycle, sort) -> {data, warning, loading, error, refetch}

frontend/src/components/VendorTable.jsx
  VendorTable({cycle, selectedVendor, onSelectVendor})
```

The adapter functions accept API data objects, not full fetch promises. The hooks own request state and pass `Envelope.data` to the adapters or table.

### 3.2 KPI card mapping

| Card id | API value | Unit/display | Delta insight | Notes |
|---|---|---|---|---|
| `ota` | `overview.ota_pct` | `%` | `kpi: ota_pct`, `reason: vs_prior` | Compare against `benchmarks.ota_sla`; below SLA is an error badge. |
| `avg-delay` | `overview.avg_delay_min` | `min` | None in current insight contract | Missing delta is `—`; do not derive one from unrelated insights. |
| `no-show` | `overview.no_show_rate` | `%` | `kpi: no_show`, `reason: vs_prior` | Higher delta is adverse. |
| `cost` | `overview.cost_per_trip` | INR, two decimals | `kpi: cost`, `reason: vs_prior` | Delta is relative `%`, not `pp`. |
| `safety` | `safety_open_sev1` | `Open` | None unless a matching prior insight exists | Positive open count uses the error treatment. |
| `csat` | `overview.csat_avg` | `/5` | `kpi: csat`, `reason: vs_prior` | `low_rating_share` may be displayed as a supporting note. |

Formatting rules:

- Null, undefined, non-finite, and unavailable values render `—`.
- Numeric API zero is a valid zero and must not be converted to `—`.
- `cost` values use two decimal places and Indian grouping where the existing visual style uses INR.
- `contribution_share` values are multiplied by 100 before adding `%`.
- Delta rows are omitted when no baseline exists; the card may show a neutral prior-cycle `—` note.

The OTA drilldown receives the live OTA value, SLA, prior-cycle delta, and contribution share when available. It does not display hardcoded peer or vendor values.

### 3.3 Alert mapping

`buildAlerts` maps each `briefing.data.insights_top5` item to one exception card:

| Alert field | Source/format |
|---|---|
| React key | `${insight.id}:${index}` to tolerate duplicate backend ids in a ranked list. |
| Ack id | `insight.id`; shared with `/actions`. |
| Severity | `insight.severity`, expected `high`, `medium`, or `low`. |
| Title | `ALERT {index + 1}: {KPI label}` with the reason label when available. |
| Scope | `scope.vendor`, then `scope.office`, then `All`. |
| Current vs baseline | `current`, `baseline`, and signed `delta_pp`, formatted by KPI. |
| Operational impact | `reach_trips` followed by `trips affected`. |
| Contribution | `contribution_share * 100` followed by `%`, or `—`. |
| Reason | A stable presentation label for `vs_sla`, `vs_prior`, `anomaly`, peer, and z-score reasons; unknown values fall back to the raw reason. |
| Recommended action | `recommended_action`. |
| Owner | `owner`. |

Mock-only alert properties are removed: `breakdown`, `breakdownSimple`, `hasCopyForVendor`, `hasReviewAlerts`, `unackText`, hardcoded metric prose, and mock badge ids.

The severity filter contains `all`, `high`, `medium`, and `low`. The mock `critical` filter is removed because the backend contract does not emit a `critical` severity.

Duplicate insight ids are possible in the current fixture. The rendered React key must therefore include the array index, while the ack target remains the backend id. If two cards share an id, acknowledging that backend action is intentionally reflected on both cards.

### 3.4 Recommended-action mapping

The displayed list is selected in this order:

1. Use `briefing.data.actions_top3` when it is a non-empty array.
2. Otherwise use the first three records from `GET /actions`.

Each card maps:

| Card field | API source |
|---|---|
| id | `action.id` |
| title | `action.action` |
| owner | `action.owner` |
| reason/due text | `Due: {action.due_hint}` |
| copy value | `action.copy_for_vendor` |
| status | `ackOverrides[id]`, then full-actions status, then item status, then `proposed` |

The pending badge equals displayed action count minus displayed actions whose resolved status is `acked`. An acked action changes its primary button to the existing audit action; the audit modal remains static.

### 3.5 Vendor table contract

`VendorTable` renders server-provided rows and never client-reorders or recalculates peer ranks.

| Column | Source | Missing value |
|---|---|---|
| Vendor | `vendor` | `—` |
| Peer rank | `peer_rank` | `—` |
| Trips | `trips` | `—` |
| OTA | `ota_pct` | `—` |
| Cost / trip | `cost_per_trip` | `—` |
| Alerts / 1k | `alert_rate_per_1k` | `—` |
| CSAT | `csat_avg` | `—` |
| Contribution | `contribution_share * 100` | `—` |

Vendor sub-text always exposes the data-quality counts when present:

```text
Zero-km: {zero_km_count} | Unslabbed: {unslabbed_count}
```

Sortable keys are exactly `ota`, `cost`, `alerts`, and `csat`. A sort change calls `getVendors(cycle, sort)` through `useVendors`; the table does not sort the previous rows locally.

The selected row is controlled by `selectedVendor`. Clicking an unselected row selects it; clicking the selected row clears it. The selected row is highlighted without changing the API query.

### 3.6 URL contract

| Parameter | Read | Written | Behavior |
|---|---|---|---|
| `cycle` | App mount | Header cycle change | Initializes `useCycle`; changing it refetches all cycle-dependent surfaces. |
| `vendor` | App mount | Vendor row selection | Highlights the matching row only; no API refetch. |

The URL writer preserves unrelated parameters, URL-encodes values, removes empty parameters, and uses `history.replaceState`.

`useCycle` gains an optional `initialCycle` argument with the existing default when omitted. This permits the App to provide the URL cycle without changing existing callers or Story 09 default behavior.

### 3.7 Component prop contracts

| Component | New/changed contract |
|---|---|
| `App` | Owns cycle URL state, API hooks, adapter calls, ack state, toast state, and selected vendor state. |
| `Header` | Receives `cycle`, `cycles`, and `onCycleChange`; decorative Office/Vendor/BU controls remain unchanged. |
| `TriggerBanner` | Receives filtered fired triggers, cycle, dismiss/restore/review handlers; returns null for no fired trigger. |
| `KpiPulse` | Receives mapped `kpis` and `onOpenSafety`; all displayed values and OTA drilldown values come from props. |
| `AlertsSection` | Receives mapped alerts and ack/status handlers; mock incident and copy props are removed. |
| `RecommendedActions` | Receives mapped actions, resolved status, pending count, ack handler, copy handler, and audit handler. |
| `ChatPanel` | No mock data props; renders disabled Story 07 state. |
| `SafetyModal` | Receives `open`, `onClose`, and live `totalOpen`; static incident state is internal. |
| `VendorTable` | Receives `cycle`, `selectedVendor`, and `onSelectVendor`; owns sort and vendor request state. |

### 3.8 Error and edge-case contract

| Case | API result | UI behavior |
|---|---|---|
| Empty marts | 200, `data: null`, warning `marts empty — run ingest` | Verbatim warning banner; do not render a blank page or zero-filled cards. |
| Unknown cycle | 404 with top-level `valid_cycles` | `useCycle` selects the first valid cycle; dependent queries refetch. |
| Invalid sort | 422 with top-level `allowed` | Vendor table shows an inline error including allowed keys. |
| Ack unknown id | 404 | Optimistic status rolls back and failure toast appears. |
| Ack validation error | 422 | Same rollback and failure toast behavior. |
| Network failure | Fetch rejection | Surface an error state for the affected surface. |
| Null numeric | Valid envelope with null field | Render `—`, never `0`. |
| Missing triggers | No `triggers` key | No trigger banner and no exception. |
| Empty triggers | `triggers: []` | No trigger banner. |
| Non-fired triggers | Array with no `fired: true` item | No trigger banner. |
| Duplicate insight id | Repeated id in ranked list | Unique React key; shared backend ack identity retained. |

## 4. Functional Contracts

### 4.1 Initial load

1. App reads `cycle` and `vendor` from `window.location.search`.
2. App initializes `useCycle` with the URL cycle or the existing default.
3. `useOpsData`, `useInsights`, and the vendor query begin for the resolved cycle.
4. Loading skeletons render while requests are pending.
5. A stale response from a previous cycle must not replace the current cycle's data.

### 4.2 Cycle changes

1. Header's cycle selector calls `useCycle.setCycle` through the App handler.
2. App updates `?cycle=` with `replaceState`.
3. Briefing, actions, overview, insights, and vendors refetch for the new cycle.
4. A prior cycle's data is not displayed as current data after the new request settles.
5. If the API returns an unknown cycle, `useCycle` applies the existing `valid_cycles` fallback contract.

### 4.3 Brief surface

On successful data, the App renders, in the existing single-page order:

1. Fired trigger banner when applicable.
2. Live KPI pulse.
3. Live exception feed from `insights_top5`.
4. Live recommended actions.
5. Existing ChatPanel in disabled Story 07 state.

The dashboard/vendor table is rendered on the same scrollable page. No `?page=` routing or separate dashboard route is introduced.

### 4.4 Ack flow

Every approve control passes the backend action id to the shared App ack handler. The action button changes to its acked state before the network response resolves and is disabled while pending.

On a successful POST, the acked state and success toast remain. On failure, the previous status is restored and the toast contains the failure message. The request body must be exactly:

```json
{"actor":"Transport Manager"}
```

### 4.5 Copy flow

The recommended-action copy button passes the exact API string to the clipboard helper. No string reconstruction, trimming, or template replacement is permitted before the clipboard call.

### 4.6 Trigger flow

The banner is driven exclusively by fired trigger entries. A missing optional field must not produce a banner, warning, or render exception. Review continues to use the existing scroll-to-alert behavior.

### 4.7 Vendor flow

The table initially requests `sort=ota`. Sort controls request each supported key and render the order returned by the server. Counts for zero-km and unslabbed records remain visible below the vendor name.

Selecting a row updates `?vendor=` and applies a visual highlight. Reloading with the same URL restores that highlight without filtering the data.

### 4.8 Modal and Chat behavior

The safety modal displays the live total open Sev-1 count but retains static incident detail until Story 08. Chat is visibly disabled and does not perform mock classification, delayed responses, clipboard generation, or API calls.

## 5. Test Plan

Tests follow the repository's required red-first workflow: add each feature test, confirm a failing terminal result, implement the minimum change, then confirm green.

### 5.1 Adapter tests

File: `frontend/src/lib/__tests__/adapters.test.js`

Cases:

- OTA value formats from `overview.ota_pct` and receives the correct SLA badge from `benchmarks.ota_sla`.
- Avg Delay maps from `avg_delay_min` with `min` unit and no invented delta.
- No-show maps from `no_show_rate` and uses the all-scope `no_show` prior insight.
- Cost maps from `cost_per_trip` and formats its delta as relative `%`, not `pp`.
- CSAT maps from `csat_avg` and formats `low_rating_share` as a supporting percentage.
- Safety maps from `safety_open_sev1` and does not use a fabricated unacknowledged count.
- All-scope `vs_prior` is selected over peer, SLA, anomaly, or vendor-scoped insights.
- Missing prior insight and null baseline produce `—` with no delta row.
- Null, undefined, and non-finite numeric values produce `—`; numeric zero remains `0`.
- Contribution share `0.31` becomes `31%`; null contribution becomes `—`.
- Alert mapping preserves severity, scope, reach, recommendation, owner, and ack id.
- Duplicate alert ids receive distinct list keys.
- Action mapping uses `actions_top3` first and falls back to the full actions list when needed.
- Ack overrides take precedence over server status.
- Fired-trigger filtering ignores missing, empty, non-array, and `fired: false` values.

### 5.2 Live brief integration tests

File: `frontend/src/__tests__/BriefLive.test.jsx`

Handlers load the committed fixture JSON and return it through msw. The test may override individual fixture payloads for trigger and warning cases.

Cases:

- Real fixture response renders the live OTA value, live Sev-1 count, exception cards, and recommended actions.
- The fixture's `96.9%` OTA, `252` Sev-1 count, and `4.8` CSAT are visible in the mapped UI.
- Briefing trigger fixture with `triggers: [{fired: true, name, scope}]` renders the trigger name and scope.
- Briefing fixture with `triggers: []` renders no trigger banner.
- Briefing fixture without a `triggers` key renders no trigger banner.
- A warning envelope with `data: null` renders `marts empty — run ingest` as a banner and does not crash.
- A GET failure renders an error state rather than an empty or zero-filled brief.
- All expected GET requests include the active cycle query parameter.

### 5.3 Ack and clipboard tests

File: `frontend/src/__tests__/AckFlow.test.jsx`

Cases:

- Clicking an action's approve button immediately displays the acked state before the delayed POST resolves.
- The captured POST body deep-equals `{actor: 'Transport Manager'}` with no extra keys.
- A successful 200 response leaves the action acked and displays a success toast.
- A delayed request disables the clicked button while pending.
- A 404 response restores the proposed state and displays the failure toast.
- A 422 response follows the same rollback path.
- `navigator.clipboard.writeText` is stubbed in jsdom and receives the exact fixture `copy_for_vendor` value.

Clipboard setup must define a configurable `navigator.clipboard` object with a mocked `writeText` promise. The test must not rely on a system clipboard.

### 5.4 Vendor table tests

File: `frontend/src/__tests__/VendorTable.test.jsx`

The default render uses the real vendor fixture for data-quality count assertions. Sort tests use a small deterministic three-row handler dataset with distinct ordering for every supported sort, so the test proves query selection and server-order consumption without relying on the large snapshot's only default ordering.

Cases:

- Initial request uses `cycle=2026-06-H1&sort=ota`.
- `cost`, `alerts`, and `csat` controls issue the matching sort query and render the server-returned first row.
- Zero-km and unslabbed counts are visible beneath the vendor name.
- Null vendor fields render `—` instead of `0` or blank text.
- A 422 response displays the backend `allowed` sort values inline.
- Clicking a row writes the URL-encoded `vendor` parameter and highlights the row.
- Clicking the selected row removes `vendor` from the URL.
- Rendering with `?cycle=2026-06-H1&vendor=<name>` restores the selected-row highlight.

Each URL test resets history with `history.replaceState` before rendering so tests do not leak query state.

### 5.5 Existing regression tests

The Story 09 client, hook, fixture, and harness tests must remain green. Backend tests are not modified and must be rerun as a regression check.

## 6. Acceptance Mapping

| Acceptance criterion | Verification |
|---|---|
| Brief uses live fixture values and has no `data.js` imports | `BriefLive.test.jsx`; repository search for `data`; build succeeds after deleting `data.js`. |
| Trigger banner fire/no-fire/missing behavior | Trigger cases in `BriefLive.test.jsx`; `getFiredTriggers` adapter tests. |
| Exact copy-for-vendor value | Clipboard assertion in `AckFlow.test.jsx`. |
| Empty-marts warning is a banner | Warning case in `BriefLive.test.jsx`. |
| Optimistic ack, rollback, actor body | Ack cases in `AckFlow.test.jsx`; msw request capture. |
| Four vendor sorts and count sub-text | `VendorTable.test.jsx`; server-order assertions. |
| `?cycle=&vendor=` round-trip | Vendor URL tests with `history.replaceState`. |
| `data.js` deleted | Filesystem check and `npm run build`. |
| Frontend test/lint/build gates | `npx vitest run`, `npm run lint`, `npm run build`, and `npm run typecheck`. |
| Backend remains green and untouched | `uv run pytest` and `ruff`; `git diff -- backend` must be empty. |
| Compose smoke renders live surfaces | `docker compose up --build`, then browser check at `127.0.0.1:3000`. |

## 7. Files to Touch

### 7.1 Edit

- `frontend/src/App.jsx`
- `frontend/src/components/TriggerBanner.jsx`
- `frontend/src/components/KpiPulse.jsx`
- `frontend/src/components/AlertsSection.jsx`
- `frontend/src/components/RecommendedActions.jsx`
- `frontend/src/components/ChatPanel.jsx`
- `frontend/src/components/Header.jsx`
- `frontend/src/components/Modals.jsx`
- `frontend/src/lib/useCycle.js` for the optional URL-provided initial cycle argument.

### 7.2 New

- `frontend/src/lib/adapters.js`
- `frontend/src/lib/useInsights.js`
- `frontend/src/lib/useVendors.js`
- `frontend/src/components/VendorTable.jsx`
- `frontend/src/lib/__tests__/adapters.test.js`
- `frontend/src/__tests__/BriefLive.test.jsx`
- `frontend/src/__tests__/AckFlow.test.jsx`
- `frontend/src/__tests__/VendorTable.test.jsx`

The two hooks and table are additional files because the story explicitly adds independent `/insights` and sortable `/vendors` reads. Keeping their request state isolated prevents vendor sort failures from blanking the brief and avoids changing the frozen Story 09 hook contract.

### 7.3 Delete

- `frontend/src/data.js`

### 7.4 Documentation

- Update the status line in `stories/05-brief-ui/SPEC.md` to record that wiring is delivered by Story 10.
- Update the status line in `stories/06-dashboard-ui/SPEC.md` to record that live overview/vendor wiring is delivered by Story 10.
- Update this story's status in `stories/10-api-integration/SPEC.md` after implementation and verification.
- Update the Story 10 row in `stories/README.md` when the acceptance gates are complete.

### 7.5 Do not modify

- `backend/**`
- `frontend/src/lib/ops.ts`
- Story 09 fixture contracts
- Story 07 `/ask` or narration behavior

## 8. TDD Execution Order

1. Add adapter tests and confirm red output.
2. Implement `adapters.js` and confirm adapter tests green.
3. Add `BriefLive.test.jsx` and confirm red output for live rendering, warning, and trigger cases.
4. Add the independent hooks and wire App/components; confirm the brief tests green.
5. Add `AckFlow.test.jsx` and confirm red output for optimistic state, rollback, actor body, and clipboard.
6. Implement the App ack state machine and exact copy path; confirm ack tests green.
7. Add `VendorTable.test.jsx` and confirm red output for sorts, counts, and URL state.
8. Implement `useVendors`, `VendorTable`, and cycle/vendor URL synchronization; confirm vendor tests green.
9. Remove all `data.js` imports, move static modal fixture state into `Modals.jsx`, and delete `data.js`.
10. Apply documentation updates only after the implementation and tests reflect the final behavior.
11. Run the complete frontend and backend verification commands.
12. Run the compose smoke check against `127.0.0.1:3000`.

Required commands from `frontend/`:

```bash
npx vitest run
npm run lint
npm run typecheck
npm run build
```

Required backend regression commands from `backend/`:

```bash
uv run pytest
uv run ruff check .
```

## 9. Risks and Follow-ups

- **Known lint coverage gap:** the existing flat ESLint config does not lint `.jsx` or `.ts` files. Story 10 does not introduce a parser/config migration; the gap remains a separate follow-up.
- **Duplicate briefing request:** `useCycle` probes briefing while `useOpsData` also requests it. Story 09 documents this as an accepted cost because the backend cache makes the request cheap. Deduplication is deferred.
- **Session-local ack overlay:** optimistic overrides are local to the current App session. A different actor's ack appears after a refetch, which is acceptable for this mock-execution write-path.
- **Duplicate insight ids:** the current fixture contains repeated action/insight ids. React keys include the list index, but backend ack identity remains id-based. A backend identity correction belongs outside Story 10.
- **Static safety modal:** the total open count is live while incident details remain static. Story 08 owns full safety data integration.
- **Forward-compatible trigger shape:** `triggers` remains optional and unknown in the Story 09 client type. Story 08 may formalize the type; Story 10 must continue to guard missing or unexpected shapes.
- **Fixture staleness:** fixture-based UI tests assert the committed snapshot values. If backend contracts or snapshots change, refresh fixtures through the Story 09 snapshot procedure rather than hand-editing values.
- **Clipboard permissions:** unit tests stub clipboard behavior. Browser permission failures are not treated as API failures and should not crash the page.
- **Missing prior insights:** Avg Delay and any KPI without an all-scope `vs_prior` record intentionally display `—`. The frontend must not infer a prior value from a peer or SLA insight.
- **Header filter controls:** Office, Vendor, and BU controls remain decorative and should be reconciled during the Story 08 documentation pass.

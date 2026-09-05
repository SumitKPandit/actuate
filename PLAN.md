# Actuate — Solution Plan (Ops Brief for Transport Manager)

Locked scope: persona = **transport manager**; surface = **brief + dashboard + Q&A**;
narration = **deterministic templates + Sarvam LLM fallback**; data = **Postgres + precomputed marts**.
Proactive = **pull-proactive** (triggers fire on mart refresh, surface in `/briefing` without prompt;
push via Email/Slack out of scope, contract left push-ready). Act = **recommend + human-ack**
(`GET /actions` proposes, `POST /actions/{id}/ack` records approval/mock-execution + audit).

## 1. Goal

Transport manager opens one page and knows: what slipped, which vendors/offices
drive it, which safety items need acknowledgement, and what to do next.
No manual report assembly.

## 2. Evidence (dataset, sampled)

- 189k (May) + 211k (Jun) + 216k (Jul) trips; 1.6M legs; 621k bills; 51.7k alerts; 513k feedback.
- Delayed share ~2.4% May, ~7% Jun, ~3.9% Jul; mean delay < 1.1 min. OTA ~93–97%.
- Cost median ~1236, mean ~1394, max ~16k; zero-km rows common.
- Alerts top: geofence (10.8k), woman-travelling-alone (10.7k), device-unreachable (9.9k);
  Sev-1 = 656, Sev-2 = 572. `severity` contains 15k `"False"` + 16k nulls.
- Feedback avg ~4.85; `marshal_rating` ~0.85 (mostly unrated, not bad).

## 3. Agentic loop (deterministic-first, LLM at edge)

1. **Sense** — ETL CSVs to Postgres (idempotent batch; rerun-safe, satisfies
   sample-only constraint — no live stream expected); precompute daily/vendor/office marts;
   anomaly checks (threshold, MoM delta, z-score). Refresh cadence = ingest rerun;
   `insight_cache` max age 6h so reads never scan raw tables.
2. **Reason** — rules attach context: vs SLA, vs prior cycle, vs peer vendor/office,
   plus contribution analysis (e.g. "2 vendors = X% of delay gap"). Rank by severity × reach.
3. **Act** — ranked exception feed with recommended action + owner; copy-for-vendor text;
   NL Q&A grounded on marts (allowlisted `SELECT`, `LIMIT 50`, 422 + `supported_intents`
   otherwise — never invents numbers); proactive triggers (Sev-1 spike, OTA drop, cost outlier)
   evaluated on mart refresh and surfaced as `triggers[]` in `/briefing` + server log
   (no push infra — `{fired, scope, insight_id}` shape is the push-ready contract);
   human approval via `POST /actions/{id}/ack {actor}` → recorded status + audit (mock
   execution only, no real vendor integration per Constraints).

No LLM-per-row. LLM narrates precomputed facts only (1 call per briefing/Q&A),
template fallback when key is missing.

## 4. KPIs + benchmarks (MVP)

Each KPI was picked because the transport manager can act on it with a clear owner.
If it has no owner/action it is out for MVP.

| KPI | Definition | Benchmarks | Decision → owner |
|---|---|---|---|
| OTA % | delay > 15 min = late | SLA 95%, trend, vendor/office peer rank | vendor penalty review → vendor |
| Delay min + reason mix | traffic / driver / employee | trend + vendor attribution | re-route / buffer → vendor |
| No-show % | legs `is_no_show` | shift/office peer, reason split | shift reminder + standby cab → office |
| Cost/trip, cost/km, outliers | bills incl. zero-km flag | cycle trend, vendor/contract peer | hold bill + verify slab → ops |
| Alert rate/1k trips, Sev-1, ack time | ack SLA e.g. < 30 min | SLA + trend | ack Sev-1s + escort audit → ops |
| CSAT + low-rating clusters | route/driver/cab/safety excl. 0s; < 3 = low | trend + vendor peer | driver/cab review → vendor |

Out for MVP (no actionable sample data): sustainability, GPS-trace replay.

## 5. Architecture

```text
CSVs → backend/scripts/ingest.py → Postgres (trips, legs, bills, alerts, feedback)
→ marts (daily_kpi, vendor_kpi, office_kpi, shift_kpi, insight_cache)
→ FastAPI (/overview /insights /briefing[?narrate][+triggers[]] /vendors /actions[+POST /actions/{id}/ack] /ask)
→ TanStack Start (/ brief, /dashboard, chat drawer)
→ Sarvam sarvam-105b, reasoning_effort=None (narration only)
```

- **DB:** 5 raw tables (normalized keys) +
  `daily_kpi, vendor_kpi, office_kpi, shift_kpi, insight_cache`.
- **Backend:** `core/analytics.py` (pure KPI fns), `core/reason.py` (benchmark + rank),
  `core/triggers.py` (thin wrapper over `reason.py` — no duplicated thresholds),
  `core/ask.py` (deterministic intent parser + mart query plans),
  `core/narrate.py` (template + official asynchronous Sarvam client via
  `https://api.sarvam.ai/v1`), `api/ask.py` and `api/ops.py` routes.
  Existing `health/ready/examples` untouched.
- **Frontend:** `/` brief feed (trigger banner + headline facts + safety strip + actions + copy button),
  `/dashboard` KPIs + benchmark badges + vendor table,
  chat drawer → `POST /ask` (allowlisted mart `SELECT` only; returns generated SQL + rows + narrative + `grounded_from`; 422 + `supported_intents` otherwise).
- **Leadership-shareable:** `GET /briefing` (+ optional `?narrate=true`) returns
  `{generated_at, headline_facts[3-5], insights_top5, safety_open_sev1, actions_top3, triggers[], narrative?}` —
  template by default, Sarvam-105B-narrated 2–3 sentence version on request;
  forwardable without rework.
  Samples committed under `stories/08-triggers-docs/samples/` (or `docs/samples/`).
- **Cost/latency:** marts keep p95 low (no raw-table scans at request time);
  ~1–2 sarvam-105b calls per session; briefings cached.

## 6. Messy-data handling

- `trip_id`: strip commas → int on every join (`bill_data` already plain digits).
- `stwid = 0 / "0"`: placeholder, excluded from rider stats.
- Dates parsed per file (ISO vs `"May 1, 2026"` vs `"June 3, 2026, 11:00 AM"`).
- `severity = "False"` → null + data-quality flag; nulls kept as "unclassified".
- Negative `planned_km/traveled_km` → null + flag. `marshal_rating = 0` → unrated.
- Zero-km bills and null `slab_name` kept as explicit categories with counts in UI.

## 7. Build order (test-first)

1. Ingest + normalization (pytest quirk fixtures).
2. `analytics.py` / `reason.py` unit tests (OTA, cost/km, ranking).
3. API tests: `/overview /insights /briefing` + `GET /actions` + `POST /actions/{id}/ack`.
4. Brief UI (`/`) with trigger banner + safety strip + copy-for-vendor.
5. Dashboard + vendors (`/dashboard`).
6. Frontend↔API integration: typed `lib/ops.ts` client + vitest/msw harness (Story 09), live brief/dashboard wiring + ack write-path + delete `data.js` (Story 10).
7. `/ask` + narration with offline fallback (allowlist + 422).
8. Triggers (`triggers[]` in briefing, no push infra) + ack audit + README + architecture diagram + sample inputs/outputs.

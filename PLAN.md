# Actuate — Solution Plan (Ops Brief for Transport Manager)

Locked scope: persona = **transport manager**; surface = **brief + dashboard + Q&A**;
narration = **deterministic templates + Sarvam LLM fallback**; data = **Postgres + precomputed marts**.

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

1. **Sense** — ETL CSVs to Postgres; precompute daily/vendor/office marts;
   anomaly checks (threshold, MoM delta, z-score).
2. **Reason** — rules attach context: vs SLA, vs prior cycle, vs peer vendor/office,
   plus contribution analysis (e.g. "2 vendors = X% of delay gap"). Rank by severity × reach.
3. **Act** — ranked exception feed with recommended action + owner; copy-for-vendor text;
   NL Q&A grounded on marts; proactive triggers (Sev-1 spike, OTA drop, cost outlier).

No LLM-per-row. LLM narrates precomputed facts only (1 call per briefing/Q&A),
template fallback when key is missing.

## 4. KPIs + benchmarks (MVP)

| KPI | Definition | Benchmarks |
|---|---|---|
| OTA % | delay > 15 min = late | SLA 95%, trend, vendor/office peer rank |
| Delay min + reason mix | traffic / driver / employee | trend + vendor attribution |
| No-show % | legs `is_no_show` | shift/office peer, reason split |
| Cost/trip, cost/km, outliers | bills incl. zero-km flag | cycle trend, vendor/contract peer |
| Alert rate/1k trips, Sev-1, ack time | ack SLA e.g. < 30 min | SLA + trend |
| CSAT + low-rating clusters | route/driver/cab/safety excl. 0s; < 3 = low | trend + vendor peer |

## 5. Architecture

```text
CSVs → backend/scripts/ingest.py → Postgres (trips, legs, bills, alerts, feedback)
→ marts (daily_kpi, vendor_kpi, office_kpi, insight_cache)
→ FastAPI (/overview /insights /briefing /ask /vendors /actions)
→ TanStack Start (/ brief, /dashboard, chat drawer)
→ Sarvam sarvam-30b, reasoning_effort=None (narration only)
```

- **DB:** 5 raw tables (normalized keys) + `daily_kpi, vendor_kpi, office_kpi, insight_cache`.
- **Backend:** `core/analytics.py` (pure KPI fns), `core/reason.py` (benchmark + rank),
  `core/narrate.py` (template + Sarvam via OpenAI-compatible `base_url=https://api.sarvam.ai/v1`),
  `api/ops.py` routes. Existing `health/ready/examples` untouched.
- **Frontend:** `/` brief feed, `/dashboard` KPIs + benchmark badges + vendor table,
  chat drawer → `/ask` (returns generated SQL + rows + narrative).
- **Cost/latency:** marts keep p95 low; ~1–2 sarvam-30b calls per session; briefings cached.

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
3. API tests: `/overview /insights /briefing`.
4. Brief UI (`/`).
5. Dashboard + vendors (`/dashboard`).
6. `/ask` + narration with offline fallback.
7. Triggers + README + architecture diagram + sample inputs/outputs.

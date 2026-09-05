# Stories — Actuate (Transport Manager)

Pickup order is numeric. Each `NN-name/` folder is one independently testable story with its own `SPEC.md`. Do not skip order: each story depends on the previous one's contracts.

| # | Folder | What it delivers | Depends on |
|---|---|---|---|
| 01 | `01-ingest-marts/` | CSV → Postgres/SQLite: 5 raw tables + 4 marts, all messy-data rules applied | nothing (repo scaffolding only) |
| 02 | `02-analytics-kpis/` | `core/analytics.py`: pure KPI functions for all 6 MVP KPI families | 01 (real row shapes + quirk fixtures) |
| 03 | `03-reason-rank/` | `core/reason.py`: benchmarks, anomaly checks, contribution, severity×reach ranking | 02 |
| 04 | `04-ops-api/` | FastAPI `api/ops.py`: `GET /overview /insights /briefing /vendors /actions` + `POST /actions/{id}/ack` on marts | 01–03 |
| 05 | `05-brief-ui/` | Frontend `/` brief feed + foundation: typed API client (`lib/ops.ts`), vitest harness, conditional routing, Header nav | 04 (API contracts), 01–03 (mart data) |
| 06 | `06-dashboard-ui/` | Frontend `/dashboard`: 6 KPI cards + benchmark badges + sortable vendor table + URL filters | 05 (foundation), 04 (`/overview`, `/vendors`) |
| 07 | `07-ask-narrate/` | `core/narrate.py` (template + Sarvam fallback) + `POST /ask` (marts-only, 422 otherwise) + chat drawer + `?narrate=true` briefing | 02–04 |
| 08 | `08-triggers-docs/` | Proactive triggers (`triggers[]` in briefing, log only — no push), ack audit, README, architecture diagram, sample inputs/outputs | 01–07 |

## Global constraints (apply to every story)

- Persona: **transport manager** only (briefing is forwardable to head without rework). Surface: **brief + dashboard + Q&A**.
- Proactive = **pull-proactive**: triggers fire on mart refresh, surface in `/briefing` without prompt. No Email/Slack push — `{fired, scope, insight_id}` stays push-ready.
- Act = **recommend + human-ack**: `GET /actions` proposes (`proposed`), `POST /actions/{id}/ack` records approval/mock-execution. No real vendor integration.
- Q&A = **marts-only**: allowlisted `SELECT` over `daily_kpi/vendor_kpi/office_kpi/insight_cache`, `LIMIT 50`; anything else → 422 + `supported_intents`. New questions land as new marts, never raw-table access.

- Persona: **transport manager** only. Surface: **brief + dashboard + Q&A**.
- Narration: **deterministic templates first, Sarvam LLM at edge only** (1 call per briefing/Q&A, never per row).
- Data: **Postgres in compose, SQLite locally** via `backend/src/backend/core/database.py` (`Base`, `get_db`, `init_db`). Existing `health/ready/examples` routes stay untouched.
- Messy-data rules live in `PLAN.md §6` + `problem-statement/dataset/dictionary/` — every story must respect them, Story 01 implements them.
- Per `AGENTS.md`: failing test first (red terminal output) before any behavior change; run `uv run pytest` + `ruff` after every change; keep changes minimal and modular.
- KPI definitions are frozen in `PLAN.md §4`. Do not redefine: OTA late = `delay > 15 min`; SLA OTA 95%, ack SLA 30 min; CSAT excludes 0s, `< 3` = low; `marshal_rating = 0` = unrated.

## How to pick up a story

1. Read its `SPEC.md` fully (Goal → Acceptance criteria → Test plan).
2. Confirm predecessor stories are done (contracts in their SPECs hold).
3. Write the failing tests listed in the SPEC, confirm red, then implement minimum code.
4. Place follow-up artifacts (fixtures, samples, notes) inside the same story subfolder.

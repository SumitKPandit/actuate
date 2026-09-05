# Story 08 — Proactive Triggers + Docs + Samples (ship-ready)

**Status:** not started. **Depends on:** 01–07 (needs real insights, API, UI, narration to document).

## 1. Goal

System nudges before the manager asks, and a new reader can run, trust, and demo the whole loop in 15 minutes from README alone.

## 2. Scope

**In:** trigger evaluation + ack-audit surfacing + docs/diagram/samples. Code surface minimal by design.
**Out:** new KPIs, new endpoints (reuse `/insights` + Story 04 `POST /actions/{id}/ack`), push infra (email/Slack — log + API flag only).

## 3. Functional requirements

1. **Triggers (reuse Story 03, no new math):** evaluate on mart refresh / `/insights` read; minimum three rules with defaults in `BENCHMARKS`:
   - Sev-1 spike: `sev1_count` today/this-cycle > mean + 2σ (or > 2× prior cycle if < 14 points).
   - OTA drop: cycle OTA < 95% SLA **and** Δ ≤ −2pp vs prior.
   - Cost outlier: vendor `cost_per_trip` > mean + 3σ within cycle, or any trip `> ₹16k` sanity flag (PLAN max observed).
   Output: `{ trigger, fired: bool, scope, current, baseline, insight_id }` surfaced as `triggers[]` in `/briefing` (extend, don't break Story 04 shape) + server log line. Unfired → empty array (never null). `insight_id` links to the ranked insight; action ack (Story 04) is the approval half — triggers are the firing half.
2. **README (root + backend + frontend touch-up):** quickstart via `docker compose up --build` (ports 3000/8000, `/docs`, `/health`, `/ready`); local dev (`uv sync`, `npm install`); ingest command; env table (`DATABASE_URL`, `VITE_API_URL`, `SARVAM_API_KEY`); endpoint table with example curl (incl. `POST /actions/{id}/ack` + `POST /ask` 422 case); KPI/benchmark/decision-owner table (PLAN §4); messy-data handling summary (PLAN §6); agentic loop (Sense→Reason→Act) in 5 lines: batch-sense, deterministic-reason, pull-proactive + ack-act, LLM-narrates-facts-only.
3. **Architecture diagram:** one file `docs/architecture.(mmd|png)` (mermaid source committed): CSVs → ingest → Postgres (5 raw + 4 marts) → FastAPI (`/overview /insights /briefing[+triggers[]] /vendors /actions[+ack] /ask`) → Vite React SPA → Sarvam edge; annotate "LLM narrates precomputed facts only" + "marts-only reads, no raw scans at request time" + "push out, `{fired,scope,insight_id}` push-ready".
4. **Sample inputs/outputs:** `stories/08-triggers-docs/samples/` (or `docs/samples/` with pointer): mini CSV input (20 rows quirks-covered) + `overview.json` + `insights.json` + `briefing.json` (incl. `triggers[]` fire + no-fire variants + `?narrate=true` leadership paragraph) + `ask.json` (one Q&A + one 422 case) + `actions-ack.json` (POST ack request/response) captured from test DB — must match live schemas.
5. **Cleanup:** remove/replace starter placeholders (`StackStatus` demo decision, About page pointer); `.gitignore` covers `.env`, `*.db`, `pgdata`, `node_modules`, `.venv`; no secrets committed (`git status` check in PR).

## 4. Acceptance criteria

- [ ] Trigger fixtures: each of the 3 rules has a fire + no-fire test.
- [ ] Fresh clone → `docker compose up --build` → `/`, `/dashboard`, `/docs` all work; README steps reproduce without extra questions.
- [ ] Samples validate: pasting sample Q through `/ask` returns structurally identical response (keys match); sample `briefing.json` validates against Story 04 shape + `triggers[]`; sample `actions-ack.json` replays against live API.
- [ ] `uv run pytest` + `ruff` + `npm run build` all green; `git status --short` shows no `.env`/DB/build artifacts.

## 5. Test plan

- `backend/tests/test_triggers.py`: 6 tests (fire/no-fire × 3 rules) on mini-marts.
- Docs check: follow README on clean checkout (or CI-less manual checklist filed in this folder as `verify.md`).
- Confirm red → implement → green per AGENTS.md (docs-only edits exempt from red requirement, trigger code is not).

## 6. Files to touch

- New: trigger hook (prefer `core/triggers.py` thin wrapper over `reason.py` — no duplicated thresholds), `docs/architecture.mmd`, samples + `verify.md` in this story folder.
- Edit: `api/ops.py` (`triggers[]` in briefing), root/backend/frontend READMEs, `.gitignore` if gaps, remove starter cruft.
- Do not: retune KPI definitions or ranking weights without updating Stories 02/03 SPECs + tests.

## 7. Notes

- This story closes PLAN §7 item 7 and the "Act" step's proactive half (PLAN §3: "Sev-1 spike, OTA drop, cost outlier"). The approval half closed in Story 04 (`POST /actions/{id}/ack`).
- If push delivery is later wanted, triggers' `{fired, scope, insight_id}` shape is the contract to build on — note it here, don't implement it.

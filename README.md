# actuate
Agentic Intelligence & Reporting Layer for Enterprise Mobility

> Scope (frozen in `PLAN.md`): persona = transport manager; surface = brief + dashboard + Q&A.
> Loop: Sense (batch ingest → marts) → Reason (deterministic SLA/prior/peer + rank) → Act
> (pull-proactive `triggers[]` + recommend + human-ack). LLM narrates precomputed facts only.
> Status: Story 01 (ingest + marts) complete; Stories 02–08 build API → UI → Q&A → triggers.
> Full endpoint/KPI/diagram/samples land in Story 08 — see `PLAN.md` + `stories/README.md` meanwhile.

## Full-stack quickstart

```bash
# All services (db + api + web):
docker compose up --build
# Web http://127.0.0.1:3000 · API http://127.0.0.1:8000/docs · DB readiness /ready
```

Local dev (two terminals):

```bash
cd backend && uv sync --group dev && uv run uvicorn backend.app:app --reload --port 8000
cd frontend && npm install && npm run dev   # http://localhost:3000
```

The home page proves browser → API → DB (`/health`, `/ready`,
`/examples` + write form). Ops routes (`GET /overview /insights /briefing /vendors /actions`,
`POST /actions/{id}/ack`, `POST /ask`)
land in Stories 04+07 — see `stories/04-ops-api/SPEC.md` + `stories/07-ask-narrate/SPEC.md`.
See `backend/README.md` for endpoints,
`CORS_ORIGINS`, and the placeholder `examples` pattern to copy once the
dataset lands.

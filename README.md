# actuate
Agentic Intelligence & Reporting Layer for Enterprise Mobility

> Scope (frozen in `PLAN.md`): persona = transport manager; surface = brief + dashboard + Q&A.
> Loop: Sense (batch ingest → marts) → Reason (deterministic SLA/prior/peer + rank) → Act
> (pull-proactive `triggers[]` + recommend + human-ack). LLM narrates precomputed facts only.
> Status: Stories 01–07 and 09–10 are complete in code; Story 08 (triggers, docs, and samples) is not started.
> See `PLAN.md` + `stories/README.md` for the implementation order and the remaining Story 08 scope.

## Full-stack quickstart

```bash
# All services (db + api + web):
docker compose up --build
# Web http://127.0.0.1:5173 · API http://127.0.0.1:8000/docs · DB readiness /ready
```

Local dev (two terminals):

```bash
cd backend && uv sync --group dev && uv run uvicorn backend.app:app --reload --port 8000
cd frontend && npm install && npm run dev   # http://localhost:5173
```

The home page proves browser → API → DB (`/health`, `/ready`,
`/examples` + write form). Ops routes (`GET /overview /insights /briefing /vendors /actions`,
`POST /actions/{id}/ack`, `POST /ask`)
land in Stories 04+07 — see `stories/04-ops-api/SPEC.md` + `stories/07-ask-narrate/SPEC.md`.
See `backend/README.md` for endpoints,
`CORS_ORIGINS`, and the placeholder `examples` pattern to copy once the
dataset lands.

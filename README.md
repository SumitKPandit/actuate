# actuate
Agentic Intelligence & Reporting Layer for Enterprise Mobility

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
`/examples` + write form). See `backend/README.md` for endpoints,
`CORS_ORIGINS`, and the placeholder `examples` pattern to copy once the
dataset lands.

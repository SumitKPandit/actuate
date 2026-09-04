# Backend — Actuate API (FastAPI)

## Quickstart

```bash
cd backend
uv sync --group dev   # install deps (incl. pytest/httpx for tests)
uv run pytest         # run tests

# Dev server with auto-reload:
uv run uvicorn backend.app:app --reload --port 8000
# or via script entrypoint:
uv run backend
```

Open:

- API root: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health: http://127.0.0.1:8000/health and http://127.0.0.1:8000/api/v1/health

## Layout

```
src/backend/
  app.py          # create_app() factory + `app` ASGI entrypoint
  core/config.py  # pydantic-settings (env / .env)
  api/
    health.py     # /health, /ready, /live probes
    router.py     # versioned v1 router — mount new domains here
tests/
  test_health.py
```

## Config

Copy `.env.example` to `.env` to override `APP_NAME`, `ENVIRONMENT`,
`API_V1_PREFIX`, or `CORS_ORIGINS`.

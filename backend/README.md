# Backend — Actuate API (FastAPI)

## Quickstart

```bash
cd backend
uv sync --group dev   # install deps (incl. pytest/httpx for tests)
uv run pytest         # run tests

# Dev server with auto-reload:
uv run uvicorn backend.app:app --reload --port 8000
```

Open:

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Readiness (DB round-trip): http://127.0.0.1:8000/ready
- Example rows: `GET/POST http://127.0.0.1:8000/examples`

## Layout

```
src/backend/
  app.py            # create_app() factory + `app` ASGI entrypoint (CORS enabled)
  core/config.py    # pydantic-settings (env / .env)
  core/database.py  # SQLite/PostgreSQL engine, Base, get_db, init_db, ping_db
  models/           # ORM models — subclass Base (see example.py placeholder)
  api/
    health.py       # /health + /ready probes
    examples.py     # placeholder GET/POST proving the get_db pattern
tests/
  test_health.py
  test_readiness.py
  test_examples.py
```

## Config

Copy `.env.example` to `.env` to override `APP_NAME`, `DATABASE_URL`,
or `CORS_ORIGINS` (JSON array, defaults cover `localhost:3000`).

## Database

SQLite locally (zero setup), PostgreSQL when deployed. Picked by `DATABASE_URL`:

```bash
# Local (default) — file DB, no setup:
DATABASE_URL="sqlite+aiosqlite:///./actuate.db"

# Deployed — set this env var (e.g. on Render/Railway/AWS):
DATABASE_URL="postgresql+asyncpg://actuate:actuate@localhost:5432/actuate"
```

Use in routes:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db

@router.get("/widgets")
async def list_widgets(db: AsyncSession = Depends(get_db)):
    ...
```

Models subclass `backend.models.Base`; tables are created on app startup
via `lifespan` (`await init_db()`), so a fresh Postgres volume works.

## Frontend wiring

CORS allows the Vite dev server (`http://localhost:3000`,
`http://127.0.0.1:3000`) by default. The frontend reads the API base
from `frontend/.env` (`VITE_API_URL`, see `frontend/.env.example`) and
the home page shows `/health`, `/ready`, and `/examples` status plus a
small write form — proving browser → API → DB end to end.

## Docker

From the repo root (requires Docker Desktop running):

```bash
docker compose up --build
```

Open:

- Web: http://127.0.0.1:3000
- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Readiness: http://127.0.0.1:8000/ready

Notes:

- `api` builds `backend/Dockerfile` and defaults to
  `DATABASE_URL="postgresql+asyncpg://actuate:actuate@db:5432/actuate"`.
- `web` builds `frontend/Dockerfile`; `VITE_API_URL` is baked at build
  time (defaults to `http://127.0.0.1:8000` for local browsers).
- `db` is `postgres:16-alpine` with data in the `pgdata` volume.
- Override without a `.env` file, e.g.
  `DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/actuate" docker compose up --build`.
- Postgres shell: `docker compose exec db psql -U actuate -d actuate`.

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
  app.py            # create_app() factory + `app` ASGI entrypoint (lifespan closes DB)
  core/config.py    # pydantic-settings (env / .env, incl. DATABASE_URL)
  core/database.py  # async engine, AsyncSession, Base, get_db, init/close/check helpers
  models/           # ORM models — subclass Base; imported for metadata
  api/
    health.py       # /health, /ready (DB SELECT 1), /live probes
    router.py       # versioned v1 router — mount new domains here
tests/
  test_health.py
  test_db.py        # SQLite in-memory DB tests (no Postgres needed)
```

## Config

Copy `.env.example` to `.env` to override `APP_NAME`, `ENVIRONMENT`,
`API_V1_PREFIX`, `CORS_ORIGINS`, or `DATABASE_URL`.

## Postgres + SQLAlchemy

Async SQLAlchemy 2.0 + `asyncpg`. Configure via `DATABASE_URL`:

```bash
# Start local Postgres:
docker run -d --name actuate-pg \
  -e POSTGRES_USER=actuate -e POSTGRES_PASSWORD=actuate \
  -e POSTGRES_DB=actuate -p 5432:5432 postgres:17

# .env:
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

Models subclass `backend.models.Base`; `await init_db()` creates tables
for dev/tests (use Alembic migrations in prod). `/ready` returns
`{"ready": ..., "database": "connected"|"disconnected"}` via `SELECT 1`.
Tests run on `sqlite+aiosqlite:///:memory:`, so no live Postgres required.

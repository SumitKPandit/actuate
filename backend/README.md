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

## Layout

```
src/backend/
  app.py            # create_app() factory + `app` ASGI entrypoint
  core/config.py    # pydantic-settings (env / .env)
  core/database.py  # SQLite/PostgreSQL engine, Base, get_db, init_db, build_engine
  models/           # ORM models — subclass Base
  api/
    health.py       # /health probe
tests/
  test_health.py
```

## Config

Copy `.env.example` to `.env` to override `APP_NAME` or `DATABASE_URL`.

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

Models subclass `backend.models.Base`; `await init_db()` creates tables.

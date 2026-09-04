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
  core/database.py  # SQLite engine, AsyncSession, Base, get_db, init_db
  models/           # ORM models — subclass Base
  api/
    health.py       # /health probe
tests/
  test_health.py
```

## Config

Copy `.env.example` to `.env` to override `APP_NAME` or `DATABASE_URL`.

## Database

SQLite via SQLAlchemy 2.0 async (`aiosqlite`). Configure via `DATABASE_URL`.

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

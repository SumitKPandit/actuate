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

## Ingest (Story 01)

```bash
cd backend
PYTHONPATH=src uv run python -m backend.scripts.ingest --data ../problem-statement/dataset/data
# Subset for dev iteration:
PYTHONPATH=src uv run python -m backend.scripts.ingest --data ../problem-statement/dataset/data --tables trips,alerts
# Postgres:
PYTHONPATH=src DATABASE_URL="postgresql+asyncpg://actuate:actuate@localhost:5432/actuate" \
  uv run python -m backend.scripts.ingest --data ../problem-statement/dataset/data
```

`--database-url` overrides `DATABASE_URL` (`settings.database_url`,
default `sqlite+aiosqlite:///./actuate.db`). Reruns are idempotent
(`DELETE` + reload per table). Exit `2` on schema mismatch (missing
file/column); count deviation past ±0.5% is a warning, not a failure.
`daily_kpi` / `vendor_kpi` / `office_kpi` / `insight_cache` schemas are
created empty here; Story 02 fills rows.

Null markers (all → `NULL`, row kept, flag where listed):

| File | Marker | Meaning |
|---|---|---|
| `alerts_data.csv` | literal `NA` | missing (`severity`, `source`) |
| `alerts_data.csv` | literal `False` in `severity` | bad data → `NULL` + `severity_raw='False'`, `dq_flag='severity_false'` |
| `bill_data.csv` | literal `null` / `NA` | missing `slab_name`/`contract` (stored `NULL`; `'UNSLABBED'` is a Story-02 display rule) |
| `Ride_data _trip-*.csv` | literal `NA` in `trip_nodal` | non-nodal trip (expected) |
| `Ride_data _trip-*.csv` | empty `is_driver_nc`/`is_cab_nc` | May nulls (4 rows) → `NULL` |
| `emp_Data.csv` | empty strings | `not_boarding_reason`, `signintype`, epoch nulls → `NULL` |

Other rules: `trip_id`/`stwid` strip commas → `BIGINT`;
`stwid = 0` kept with `is_placeholder=true`; negative leg km → `NULL` +
`dq_flag='negative_km'`; `bills.total_trip_km = 0` kept with
`is_zero_km=true`; feedback ratings stored raw incl. `0`.

## Roadmap (Stories 02–08, not yet implemented)

- Story 02 `core/analytics.py`: pure KPI math per `PLAN.md §4` (OTA >15min, cost/km excl. zero-km, CSAT excl. 0s).
- Story 03 `core/reason.py`: SLA/prior/peer benchmarks + contribution + severity×reach rank.
- Story 07 `core/narrate.py` + `POST /ask`: marts-only allowlisted `SELECT` (`LIMIT 50`), 422 + `supported_intents` otherwise; `GET /briefing?narrate=true` leadership paragraph (template fallback, Sarvam `sarvam-30b` when `SARVAM_API_KEY` set).
- Story 08 `core/triggers.py`: Sev-1 spike / OTA drop / cost outlier → `triggers[]` in `/briefing` + log (no push infra; `{fired,scope,insight_id}` push-ready).

## Ops API (Story 04)

All routes read marts only (`daily_kpi`, `vendor_kpi`, `office_kpi`, `insight_cache`) — never raw tables. All five GETs return `{data, warning}`; empty marts → `200 {"data": null, "warning": "marts empty — run ingest"}`. `cycle` is required (`YYYY-MM-H1/H2`; `H1` = 1st–15th, `H2` = 16th–month-end); unknown/malformed → `404 {"detail": "unknown cycle", "cycle", "valid_cycles"}`.

```bash
curl "http://127.0.0.1:8000/overview?cycle=2026-06-H1"
# {"data": {"trips": 12000, "ota_pct": 92.7, ..., "benchmarks": {"ota_sla": 95, "ack_sla_min": 30}}, "warning": null}
```

| Method | Path | Params | Shape |
|---|---|---|---|
| GET | `/overview` | `cycle*, office, vendor, business_unit` | KPI snapshot + `benchmarks` (from `reason.BENCHMARKS`); vendor rows default, `office=` switches to office grain, `vendor=` wins; `business_unit` accepted no-op |
| GET | `/insights` | `cycle*` | ranked `reason.build_insights` output verbatim (computed on every read) |
| GET | `/briefing` | `cycle*` | `{generated_at, headline_facts[3-5], insights_top5, safety_open_sev1, actions_top3}` cached as `briefing:{cycle}` for 6h; `?narrate=true` → `422` (Story 07) |
| GET | `/vendors` | `cycle*, sort=ota\|cost\|alerts\|csat, business_unit` | peer table with `peer_rank` (competition `1,2,2,4`) + `contribution_share` (top-2 map, else null) + `zero_km_count`/`unslabbed_count`; keys `ota_pct`, `alert_rate_per_1k`, `csat_avg` |
| GET | `/actions` | `cycle*` | flattened insights `{id, action, owner, due_hint, copy_for_vendor≤500, status}`; `status` is `acked` iff `action:{id}` cached |
| POST | `/actions/{id}/ack` | body `{actor*}` | `{id, status: "acked", actor, acked_at}` persisted to `insight_cache`; same-actor re-ack idempotent, different-actor transfers + log line; unknown id → 404 |
| POST | `/ask` | any | `501 {"detail": "reserved for Story 07 (NL-to-SQL over marts)"}` |

Local dev: after pulling, recreate mart tables in `actuate.db` (new nullable columns; `init_db` only creates missing tables).

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

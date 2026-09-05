# Story 07 - PostgreSQL Q&A + Sarvam-105B Narration

**Status:** complete (implementation delivered, local unit gates are green, PostgreSQL migrations and Compose live-data paths are verified; the expanded acceptance matrix remains pending). **Depends on:** 02 (KPIs), 03
(insights), 04 (mart-backed API and reserved `/ask`), 05 (mart population),
and 09 (typed frontend API client). Story 10 supplies the live frontend
surface that this story completes.

## 1. Goal

A transport manager can ask a supported operational question in plain
language and receive a grounded answer backed by PostgreSQL marts. The answer
contains the executed read-only SQL, at most 50 mart rows, a short narrative,
and the marts/cycle used as sources.

The system must work without a Sarvam key. Deterministic templates are the
source of truth; Sarvam-105B improves the narrative only when it is configured
and reachable.

## 2. Scope

**In:**

- A PostgreSQL-backed `/ask` service using the existing SQLAlchemy async
  session and mart models.
- An allowlisted query planner for supported operational intents.
- Deterministic intent matching. Sarvam must never generate executable SQL.
- `backend/src/backend/core/narrate.py` with template narration and optional
  Sarvam-105B narration.
- `GET /briefing?narrate=true` using the same facts-only narration service.
- A functional frontend chat drawer available from the existing application
  surface.
- Offline fallback when the Sarvam key is missing or the provider fails.
- PostgreSQL integration verification and explicit mart schema prerequisites.

**Out:**

- Generic SQL agents or arbitrary model-generated SQL.
- Reads from raw tables at request time.
- SQL, CSV, or database access from the browser.
- Per-row LLM calls.
- Chat-history persistence or a new chat-history table.
- Streaming responses.
- Email, Slack, or other push delivery.
- Qwen, DuckDB, local model loading, or the detached root-level prototype
  execution path.

## 3. Functional Requirements

### 3.1 Query safety and grounding

1. `/ask` accepts `{ question, cycle?, scope? }` and returns
   `{ sql, rows, narrative, grounded_from }`.
2. The query planner may read only the allowlisted marts:
   `daily_kpi`, `vendor_kpi`, `office_kpi`, and any explicitly approved
   aggregate mart required for shift-level results.
3. Query statements are constructed by trusted application code using
   SQLAlchemy. The question and any provider output must never be interpolated
   into SQL.
4. Every executed statement is one read-only `SELECT` with `LIMIT <= 50`.
5. The returned `sql` is compiled from the same statement that was executed.
   It must contain no semicolon, write operation, raw-table reference, or
   unbounded result set.
6. Unsupported or ambiguous questions return HTTP 422 with a stable
   `supported_intents` list. No database query is executed in this case.
7. The response includes the resolved cycle and mart names in
   `grounded_from`.
8. PostgreSQL is the runtime database for Docker and deployment. SQLite may
   remain the isolated unit-test backend unless the deployment contract is
   explicitly changed.

### 3.2 Supported intents

The frozen intent IDs are defined in `TECH_SPEC.md` and are returned in this
order in every unsupported-question response:

```text
ota_by_vendor
ota_by_office
cost_outliers_by_vendor
open_sev1_by_vendor
open_sev1_by_office
low_csat_by_vendor
low_csat_by_office
no_show_by_shift
no_show_by_office
```

The parser supports deterministic synonyms such as `on-time`, `late`,
`expensive`, `severity one`, `ratings`, `feedback`, `no show`, and `missed
rides`. It rejects questions with no metric, no dimension, multiple metric or
dimension families, or a dimension that is not valid for the matched intent.
The complete token, scope, ordering, and response-row contract is in
`TECH_SPEC.md` §2 and §4.

### 3.3 Mart prerequisites

The current marts do not contain all fields required by the intent contract.
Before the endpoint is considered complete, the mart contract must provide:

- `open_sev1_count` at each supported aggregate grain.
- `unclassified_severity_count` where the response or narrative includes a
  data-quality footnote.
- A persisted `cost_outlier` flag on `vendor_kpi`, using the existing
  three-population-standard-deviation rule from `reason.py`.
- A shift-level aggregate mart, or an equivalent approved grain, containing
  `legs`, `no_show_count`, and `no_show_rate`.

These changes must be populated by `core/marts.py`, covered by fixtures, and
applied through an explicit PostgreSQL migration. `Base.metadata.create_all`
is not sufficient for upgrading an existing PostgreSQL volume.

These prerequisites are not deferred for Story 07. Their exact columns,
population rules, migration file, and migration command are frozen in
`TECH_SPEC.md` §3.

### 3.4 Narration

1. `render_template(facts)` handles every supported intent without a network
   call.
2. `narrate_with_sarvam(facts)` calls model `sarvam-105b` through the official
   asynchronous Sarvam client.
3. Sarvam receives only a small facts dictionary containing precomputed mart
   values. It never receives raw CSV rows or unrestricted database records.
4. The prompt instructs the model to produce two or three sentences for a
   transport manager and not invent, alter, or extrapolate numeric values.
5. Use `reasoning_effort=None` for this short operational response.
6. Missing key, timeout, network failure, non-success response, empty choices,
   or `message.content is None` must use the deterministic template and must
   not produce HTTP 500.
7. Fallbacks log `narrate_fallback=true` and a non-secret reason. API keys,
   prompts, raw rows, and provider response bodies must not be logged.
8. Sarvam output is never allowed to modify `rows`, `sql`, or
   `grounded_from`.

### 3.5 Briefing hook

`GET /briefing?cycle=&narrate=true` reuses `narrate.py` with headline facts.
The existing default behavior remains unchanged when `narrate` is absent or
false. The narrated response adds a `narrative` field and must not replace the
cached deterministic briefing payload.

### 3.6 Frontend drawer

The chat UI must:

- Open from a floating Ask Actuate control.
- Submit the active cycle with the question.
- Show loading, success, network-error, and unsupported-intent states.
- Render the narrative and a mini-table of no more than 50 rows.
- Provide a collapsible SQL and sources section.
- Keep a short in-memory session list only; no persistence is required.

## 4. Configuration and Secrets

Add backend settings for:

- `SARVAM_API_KEY`, optional.
- `SARVAM_MODEL`, default `sarvam-105b`.
- `SARVAM_TIMEOUT_SECONDS`, with a bounded default.
- `SARVAM_MAX_RETRIES`, default `0`, bounded to `0..2`.

The key is injected only into the backend process. It must be added to
`backend/.env.example` and the API service environment in Compose. It must
never be exposed through `VITE_*` variables or sent to the browser.

## 5. Acceptance Criteria

- [ ] Each supported intent returns the expected mart rows from seeded data.
- [ ] The nine intent IDs and their response row keys match `TECH_SPEC.md`.
- [ ] Returned SQL is a single read-only `SELECT` with `LIMIT <= 50` and only
      approved mart tables.
- [ ] Unsupported questions return 422 with `supported_intents` and execute
      no SQL.
- [ ] A question containing SQL-like text cannot cause SQL execution.
- [ ] Missing Sarvam key returns a correct template narrative.
- [ ] A fake Sarvam provider receives facts only and its narrative does not
      change returned numbers or sources.
- [ ] Provider timeout, non-success response, empty content, and
      `content=None` all fall back to the template without a 500.
- [ ] `/briefing?narrate=true` uses the same fallback behavior and default
      `/briefing` caching remains unchanged; the narrated field is returned as
      `data.narrative` and is never cached.
- [ ] PostgreSQL integration verification passes against the Compose database.
- [ ] No `/ask` query references `trips`, `legs`, `bills`, `alerts`, or
      `feedback`.
- [ ] The frontend drawer renders success, loading, error, and 422 states.
- [ ] No Sarvam key or chat history is persisted in the database.
- [ ] Existing PostgreSQL volumes can be upgraded with the explicit Story 07
      migration; `create_all()` is used only for fresh test databases.

## 6. Test Plan

Write the failing tests before implementation:

- `backend/tests/test_ask_query.py`: intent plans, SQL allowlist, limits,
  cycle/scope behavior, and PostgreSQL SQL compilation.
- `backend/tests/test_ask_api.py`: one API test per supported intent, empty
  marts, unknown cycle, unsupported question, and no-query-on-422 behavior.
- `backend/tests/test_narrate.py`: templates, fake provider success, missing
  key, provider errors, timeout, and `content=None` fallback.
- `backend/tests/test_briefing_narrate.py`: cached deterministic payload,
  `data.narrative`, and no narrative cache mutation.
- `backend/tests/test_migrations.py`: PostgreSQL migration and idempotent
  reapplication.
- Existing raw-table prohibition test extended to `/ask`.
- PostgreSQL smoke/integration test using a configured test database or the
  Compose PostgreSQL service.
- Frontend tests for drawer open, submit, render, loading, errors, 422, and
  SQL/source disclosure.

Required commands:

```bash
cd backend
uv run pytest
uv run ruff check .
```

```bash
cd frontend
npm test -- --run
npm run typecheck
npm run build
```

## 7. Files to Touch

**New:**

- `backend/src/backend/core/ask.py`
- `backend/src/backend/core/narrate.py`
- `backend/src/backend/api/ask.py`
- `backend/tests/test_ask_query.py`
- `backend/tests/test_ask_api.py`
- `backend/tests/test_narrate.py`
- `backend/migrations/001_story07_ask_marts.sql`
- `backend/src/backend/scripts/migrate.py`
- Frontend chat component tests

**Edit:**

- `backend/src/backend/app.py`
- `backend/src/backend/core/config.py`
- `backend/src/backend/models/marts.py` for required Story 07 mart fields
- `backend/src/backend/core/marts.py` for required aggregate population
- `backend/src/backend/core/analytics.py` for open/unclassified alert counts
- `backend/src/backend/models/__init__.py` for `ShiftKpi`
- `backend/src/backend/scripts/ingest.py` for shift mart population
- `backend/pyproject.toml` and `backend/uv.lock`
- `backend/.env.example`
- `backend/README.md`
- `docker-compose.yml`
- `frontend/src/lib/ops.ts`
- `frontend/src/components/ChatPanel.jsx` or a new chat component folder
- `frontend/src/App.jsx`

**Retire:**

- `agent_end_to_end.py` after the backend path is implemented and verified;
  it must not remain as a second Qwen/DuckDB execution path.

## 8. Operational Notes

- The existing PostgreSQL Compose service is not populated automatically.
  Document or implement the ingest/bootstrap step before declaring the full
  chat flow demo-ready.
- The query service must use the existing async SQLAlchemy session and must
  not create a second database connection strategy.
- No chat-specific ORM table is needed for this story.
- Sarvam is an edge narration provider, not the source of truth. PostgreSQL
  mart rows and deterministic facts remain authoritative.

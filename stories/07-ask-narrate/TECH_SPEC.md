# Story 07 - Technical Specification

**Status:** complete (implementation delivered; PostgreSQL migrations and Compose live-data paths are verified; the expanded acceptance matrix remains pending). This document freezes the contracts needed
by the backend, database, provider adapter, and frontend. `SPEC.md` describes
the product requirements; this document is the implementation contract.

## 1. Scope And Decisions

The request path is deterministic and mart-backed:

```text
POST /ask
  -> Pydantic validation
  -> deterministic intent matching
  -> scope validation and bounded cycle lookup
  -> trusted QueryPlan over approved marts
  -> one bounded AsyncSession plan SELECT with LIMIT 50
  -> bounded JSON rows and facts
  -> deterministic template
  -> optional Sarvam-105B narration
  -> response
```

Sarvam never receives a schema, SQL tool, raw operational rows, or the user
question. It only receives the bounded facts dictionary produced after the
mart query. The root-level `agent_end_to_end.py` path is not used and is
removed after the backend and frontend paths pass their acceptance tests.

The following decisions are frozen:

- `/ask` supports the nine intent IDs in Section 2.
- The active cycle is the lexicographically greatest cycle available in the
  intent's target mart when `cycle` is omitted.
- A requested cycle must use `YYYY-MM-H1` or `YYYY-MM-H2` and must exist in the
  intent's target mart.
- A scope value is an exact, case-sensitive mart dimension value after leading
  and trailing whitespace is removed.
- An empty result is HTTP 200 with `rows: []` and a deterministic no-data
  narrative. It is not an unsupported question.
- Empty target marts are HTTP 503 because no cycle can be resolved.
- Explicitly unknown cycles are HTTP 404 and include `valid_cycles`.
- Unsupported or ambiguous questions are HTTP 422 and execute no SQL.
- `rows` contains exactly the mappings returned by the executed statement;
  facts are derived from those mappings and never used to alter them.
- A request executes at most two read-only SELECTs: one bounded cycle lookup
  when needed and one bounded plan SELECT. Both use only approved marts and
  `LIMIT <= 50`.

## 2. Supported Intent Contract

`SUPPORTED_INTENTS` is an ordered tuple. The order is part of the 422 API
contract and must not be changed without a frontend contract update:

```python
SUPPORTED_INTENTS = (
    "ota_by_vendor",
    "ota_by_office",
    "cost_outliers_by_vendor",
    "open_sev1_by_vendor",
    "open_sev1_by_office",
    "low_csat_by_vendor",
    "low_csat_by_office",
    "no_show_by_shift",
    "no_show_by_office",
)
```

The parser requires one metric family and one dimension family. A question
with zero or multiple metric families, or with a missing or conflicting
dimension, is ambiguous and returns 422.

| Intent | Required metric terms | Required dimension | Target mart | Scope allowed |
|---|---|---|---|---|
| `ota_by_vendor` | `ota`, `on time`, `on-time`, or `late` | vendor | `vendor_kpi` | `vendor` |
| `ota_by_office` | `ota`, `on time`, `on-time`, or `late` | office | `office_kpi` | `office` |
| `cost_outliers_by_vendor` | `cost`, `cost per trip`, `expensive`, or `billing` | vendor | `vendor_kpi` | `vendor` |
| `open_sev1_by_vendor` | `sev 1`, `sev-1`, `severity 1`, or `severity one` | vendor | `vendor_kpi` | `vendor` |
| `open_sev1_by_office` | `sev 1`, `sev-1`, `severity 1`, or `severity one` | office | `office_kpi` | `office` |
| `low_csat_by_vendor` | `csat`, `rating`, `ratings`, `feedback`, or `satisfaction` | vendor | `vendor_kpi` | `vendor` |
| `low_csat_by_office` | `csat`, `rating`, `ratings`, `feedback`, or `satisfaction` | office | `office_kpi` | `office` |
| `no_show_by_shift` | `no show`, `no-show`, `noshow`, `missed ride`, or `missed rides` | shift | `shift_kpi` | none |
| `no_show_by_office` | `no show`, `no-show`, `noshow`, `missed ride`, or `missed rides` | office | `office_kpi` | `office` |

Dimension terms are `vendor`, `supplier`, or `operator` for vendor; `office`,
`hub`, or `site` for office; and `shift` for shift. A scope cannot supply a
missing question dimension. For example, `question="show OTA"` with
`scope.vendor="VendorX"` remains unsupported.

Questions containing SQL-like text are rejected before metric matching. The
parser returns the normal unsupported-question 422 for any question containing
the tokens `select`, `insert`, `update`, `delete`, `drop`, `alter`, `create`,
`truncate`, `union`, `--`, `/*`, `*/`, or `;`. No question text is ever placed
in a SQL expression.

## 3. Existing Mart Changes

### 3.1 Aggregate columns

Add the following nullable columns to `daily_kpi`, `vendor_kpi`, and
`office_kpi`:

| Column | Type | Population rule |
|---|---|---|
| `open_sev1_count` | integer | Count alerts where normalized severity is `Sev-1` and normalized `state_text` is `OPEN`. |
| `unclassified_severity_count` | integer | Count alerts whose normalized severity is not `Sev-1`, `Sev-2`, or `Sev-3`, including null. |

Add the following nullable column to `vendor_kpi`:

| Column | Type | Population rule |
|---|---|---|
| `cost_outlier` | boolean | True when `cost_per_trip` is greater than the cycle vendor population mean plus three population standard deviations. False when valid cost data exists and the row is not an outlier. Null when fewer than two valid vendor costs exist. |

`cost_outlier` uses the existing `reason.BENCHMARKS["cost_outlier_sigma"]`
value. The mart population code and reason code must not define separate
thresholds.

Zero is a valid value for both alert count columns. Null is used only when the
aggregate cannot be calculated because its source KPI is unavailable. An
aggregate row with no alerts has zero open and zero unclassified alerts.

### 3.2 Shift mart

Add `shift_kpi` with this schema:

```python
class ShiftKpi(Base):
    __tablename__ = "shift_kpi"

    shift_type: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_or_month: Mapped[str] = mapped_column(String(32), primary_key=True)
    legs: Mapped[int | None] = mapped_column(Integer)
    no_show_count: Mapped[int | None] = mapped_column(Integer)
    no_show_rate: Mapped[float | None] = mapped_column(Float)
```

Rows are grouped from `legs` by non-null `shift_type` and the cycle derived
from `legs.trip_date`. `legs` is the denominator because the existing
`no_show_stats` contract measures no-shows per rider leg. `no_show_rate` is a
percentage on the 0-100 scale, matching `office_kpi.no_show_rate`.

`populate_marts()` must delete and rebuild `shift_kpi` together with the other
marts. The returned mart count dictionary must include `shift_kpi`.

### 3.3 Migration and fresh databases

The implementation must add:

- `backend/migrations/001_story07_ask_marts.sql`
- `backend/src/backend/scripts/migrate.py`
- Migration coverage in `backend/tests/test_migrations.py`

The migration runner imports `backend.models`, creates only missing base
tables with `Base.metadata.create_all()`, creates a small
`schema_migrations` table, applies each numbered SQL file once, and commits
each migration. The Story 07 migration must use PostgreSQL-compatible
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`
statements. It must add all columns in Sections 3.1 and 3.2. `create_all()` is
therefore a fresh-database bootstrap inside the migration command; it still
does not upgrade existing tables.

The deployment command is:

```bash
cd backend
PYTHONPATH=src uv run python -m backend.scripts.migrate
```

The Compose API command must run this command before Uvicorn. `init_db()` and
`Base.metadata.create_all()` remain valid for fresh SQLite unit databases and
fresh test schemas, but are not the PostgreSQL upgrade mechanism. The Docker
image must copy the migration directory. Existing local SQLite files should
be recreated after the model changes; test databases are always fresh.

## 4. Query Plans

### 4.1 Common rules

Every plan uses one of these ORM models and no others:

```python
ALLOWED_MARTS = {
    "daily_kpi",
    "vendor_kpi",
    "office_kpi",
    "shift_kpi",
}
```

`insight_cache` is not needed by the supported `/ask` intents and is not
allowed in an `/ask` plan. Raw operational models and tables are never
imported by `core/ask.py`.

Every plan statement has:

- A cycle equality predicate on `cycle_or_month`.
- Any allowed scope predicate.
- A deterministic `ORDER BY` with null values last.
- `.limit(50)`.
- Only selected columns listed in Section 4.2.

Ordering is worst-first for the requested operational metric. Ties are broken
by the dimension name ascending. The exact row limit is 50, including when
fewer than 50 rows match.

### 4.2 Result row shapes

The selected labels and response keys are frozen:

| Intent | Response row keys | Ordering |
|---|---|---|
| `ota_by_vendor` | `vendor`, `cycle`, `trips`, `ota_pct`, `delayed_trips`, `avg_delay_min` | `ota_pct ASC NULLS LAST`, `vendor ASC` |
| `ota_by_office` | `office`, `cycle`, `trips`, `ota_pct`, `delayed_trips`, `avg_delay_min` | `ota_pct ASC NULLS LAST`, `office ASC` |
| `cost_outliers_by_vendor` | `vendor`, `cycle`, `trips`, `cost_per_trip`, `cost_per_km`, `cost_outlier` | `cost_per_trip DESC NULLS LAST`, `vendor ASC` |
| `open_sev1_by_vendor` | `vendor`, `cycle`, `trips`, `open_sev1_count`, `unclassified_severity_count` | `open_sev1_count DESC NULLS LAST`, `vendor ASC` |
| `open_sev1_by_office` | `office`, `cycle`, `trips`, `open_sev1_count`, `unclassified_severity_count` | `open_sev1_count DESC NULLS LAST`, `office ASC` |
| `low_csat_by_vendor` | `vendor`, `cycle`, `trips`, `csat_avg`, `low_rating_share` | `low_rating_share DESC NULLS LAST`, `csat_avg ASC NULLS LAST`, `vendor ASC` |
| `low_csat_by_office` | `office`, `cycle`, `trips`, `csat_avg`, `low_rating_share` | `low_rating_share DESC NULLS LAST`, `csat_avg ASC NULLS LAST`, `office ASC` |
| `no_show_by_shift` | `shift_type`, `cycle`, `legs`, `no_show_count`, `no_show_rate` | `no_show_rate DESC NULLS LAST`, `shift_type ASC` |
| `no_show_by_office` | `office`, `cycle`, `trips`, `no_show_rate` | `no_show_rate DESC NULLS LAST`, `office ASC` |

`cycle` is a response label for the mart's `cycle_or_month` column. The SQL
must label it as `cycle` so the same mapping shape is returned on SQLite and
PostgreSQL.

The cost query filters `cost_outlier IS TRUE`, so every returned cost row is a
persisted outlier. A cycle with no outliers returns an empty row list and a
no-data narrative.

### 4.3 `QueryPlan`

`core/ask.py` owns this dataclass:

```python
@dataclass(frozen=True)
class QueryPlan:
    intent: str
    statement: Select
    marts: tuple[str, ...]
    cycle: str
    scope: dict[str, str | None]
```

The builders are pure trusted functions. They receive only the validated
cycle, validated scope, and no raw question text. The question can influence
only the intent selected by the parser.

Before execution, `execute_plan()` asserts:

1. `statement` is a SQLAlchemy `Select`.
2. A limit exists and is an integer no greater than 50.
3. `plan.marts` is a non-empty subset of `ALLOWED_MARTS`.
4. The statement's final FROMs are approved mart tables.
5. Compiled SQL contains no semicolon and no write keyword.
6. Compiled SQL contains none of the raw table names `trips`, `legs`, `bills`,
   `alerts`, or `feedback` as table references.

The same `statement` object is passed to `AsyncSession.execute()` and to the
compiler. The returned SQL is compiled against the active connection dialect
with `literal_binds=True` for display. SQLAlchemy still receives the original
bound statement for execution; request values are never string-interpolated.

## 5. Parser, Cycle, And Scope Rules

### 5.1 Normalization and matching

`normalize_question()` lowercases the question, replaces punctuation with
spaces, normalizes `on-time` and `no-show` to their spaced forms, and collapses
whitespace. It does not remove words or use fuzzy matching.

The parser checks metric families in the table in Section 2 and dimension
families independently. It returns exactly one intent only when one supported
metric and one supported dimension are present. These are 422 cases:

- SQL-like token detected.
- No supported metric.
- No supported dimension.
- More than one metric family.
- More than one dimension family.
- A dimension not valid for the matched metric.
- A shift question containing vendor or office scope.

The parser does not query the database.

### 5.2 Cycle resolution

The target mart is known after parsing. `resolve_cycle()` queries only distinct
`cycle_or_month` values from that target mart, sorts them ascending, and limits
the metadata query to 50 values. The cycle lookup is a trusted read-only
SELECT and is subject to the same mart allowlist and no-semicolon checks as a
plan statement.

- Explicit `cycle`: validate the exact `YYYY-MM-H1/H2` grammar and look it up.
- Omitted `cycle`: choose the greatest valid cycle.
- No valid cycles: return HTTP 503 with `{"detail": "marts empty - run ingest"}`.
- Valid cycles exist but the requested cycle is absent: return HTTP 404 with
  `{"detail": "unknown cycle", "cycle": ..., "valid_cycles": [...]}`.

Cycle resolution runs after parsing and scope validation and before building
the plan. It is the only database work allowed before the plan statement
executes. Unsupported questions and invalid scopes therefore execute no SQL;
valid questions may execute the bounded cycle lookup followed by the plan
statement.

### 5.3 Scope resolution

`AskScope` values are stripped and must be non-blank when supplied. Scope is
validated against the intent's allowed scope:

- Vendor intents accept `scope.vendor`; `scope.office` is HTTP 422.
- Office intents accept `scope.office`; `scope.vendor` is HTTP 422.
- Shift intents accept neither scope field; either field is HTTP 422.
- An unknown dimension value is allowed and returns zero rows.

The scope is an equality predicate, not a substring or SQL pattern match.

## 6. HTTP API

### 6.1 Route ownership

`backend/src/backend/api/ask.py` owns `POST /ask`. The Story 04 reserved
`@router.post("/ask")` handler must be deleted from `backend/src/backend/api/ops.py`.
The new router is included exactly once by `backend/src/backend/app.py`.

The route contains no SQL text, query builder logic, parser logic, or Sarvam
provider construction. It calls `core.ask`, then `core.narrate`.

### 6.2 Pydantic models

```python
class AskScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor: str | None = Field(default=None, min_length=1, max_length=100)
    office: str | None = Field(default=None, min_length=1, max_length=100)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    cycle: str | None = Field(default=None, min_length=8, max_length=10)
    scope: AskScope | None = None


class GroundedFrom(BaseModel):
    marts: list[str]
    cycle: str


class AskResponse(BaseModel):
    sql: str
    rows: list[dict[str, object]]
    narrative: str
    grounded_from: GroundedFrom
```

Pydantic validation errors remain FastAPI's standard HTTP 422 response. The
application-level unsupported-question response is:

```json
{
  "detail": "unsupported question",
  "supported_intents": [
    "ota_by_vendor",
    "ota_by_office",
    "cost_outliers_by_vendor",
    "open_sev1_by_vendor",
    "open_sev1_by_office",
    "low_csat_by_vendor",
    "low_csat_by_office",
    "no_show_by_shift",
    "no_show_by_office"
  ]
}
```

The response never includes provider metadata, prompt text, reasoning content,
the original question, or an API key.

### 6.3 Error contract

| Condition | Status | Body |
|---|---:|---|
| Pydantic validation | 422 | FastAPI validation body |
| Unsupported or ambiguous question | 422 | `detail` plus ordered `supported_intents` |
| Invalid scope for intent | 422 | `detail: "invalid scope"`, `intent`, `allowed_scope` |
| Empty target mart | 503 | `detail: "marts empty - run ingest"` |
| Unknown explicit or resolved cycle | 404 | `detail`, `cycle`, and `valid_cycles` |
| Database/provider failure during query | 500 | Generic FastAPI error; provider failures must instead fall back to template |

Unsupported questions and invalid scopes execute no target query. Cycle
resolution is allowed only after an intent has been selected.

## 7. Narration Service

### 7.1 Facts contract

`core/narrate.py` accepts a typed dictionary with this shape:

```python
facts = {
    "intent": "ota_by_vendor",
    "cycle": "2026-06-H1",
    "scope": {"vendor": None, "office": None},
    "result_count": 2,
    "rows": [...],
    "quality": {
        "unclassified_severity_count": 0,
    },
}
```

The `rows` value sent to the provider is the first five response rows after
the deterministic database ordering. It never contains more than five rows,
and all values come from the selected mart columns in Section 4.2. The
provider facts payload is serialized with `json.dumps` and must be below
20,000 bytes. If it is not, truncate rows further before calling the
provider. The HTTP response still returns all database rows, up to 50.

`render_template(facts)` is the source of truth. It must produce a complete
string for every intent, including an explicit no-data sentence and a
data-quality footnote when `unclassified_severity_count > 0`.

### 7.2 Provider boundary

The module exposes an injectable protocol so tests use a fake provider:

```python
class NarrationProvider(Protocol):
    async def complete(self, facts: dict) -> object: ...
```

The production adapter uses the official asynchronous Python client:

```python
from sarvamai import AsyncSarvamAI

client = AsyncSarvamAI(
    api_subscription_key=settings.sarvam_api_key,
    timeout=settings.sarvam_timeout_seconds,
)
response = await client.chat.completions(
    model=settings.sarvam_model,
    messages=[
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": json.dumps(facts, sort_keys=True)},
    ],
    reasoning_effort=None,
    max_tokens=500,
    request_options={"max_retries": settings.sarvam_max_retries},
)
```

The configured timeout covers the complete await, including retries. The
implementation must also enforce it with `asyncio.timeout()` so a client or
transport regression cannot hold an API request open indefinitely.

Settings are:

```python
sarvam_api_key: str | None = None
sarvam_model: str = "sarvam-105b"
sarvam_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
sarvam_max_retries: int = Field(default=0, ge=0, le=2)
```

The API key is optional. When it is absent, no client is constructed and the
template is returned immediately.

### 7.3 Provider normalization and fallback

The adapter must:

1. Require at least one response choice.
2. Read `choices[0].message.content`.
3. Treat `None` and blank content as failure.
4. Return only non-blank content.
5. Return `render_template(facts)` for missing key, timeout, network error,
   provider error, empty choices, null content, or blank content.

Every fallback emits one structured log record containing
`narrate_fallback=true` and a fixed non-secret reason such as `missing_key`,
`timeout`, `provider_error`, `empty_choices`, or `empty_content`. Logs must
not contain API keys, prompts, facts, rows, questions, or provider bodies.

Sarvam output is assigned only to `narrative`. It cannot modify `sql`, `rows`,
or `grounded_from`.

## 8. Briefing Integration

`GET /briefing?cycle=&narrate=true` remains owned by `api/ops.py`.

The route must:

1. Load or calculate the normal deterministic `briefing:{cycle}` payload.
2. Never write `narrative` into that cache record.
3. Build facts from cycle, `headline_facts`, the first two insight values,
   `safety_open_sev1`, and any available quality count.
4. Call the same `narrate_with_sarvam()` service.
5. Return the normal response with `data.narrative` added only for this
   request.

The response models become:

```python
class BriefingData(BaseModel):
    generated_at: str
    headline_facts: list[str]
    insights_top5: list[dict]
    safety_open_sev1: int
    actions_top3: list[dict]
    narrative: str | None = None
```

Default `/briefing` reads and writes remain byte-for-byte compatible apart from
the optional model field being absent or null. A narrated request must narrate
even when the deterministic payload was loaded from cache.

## 9. Configuration And Secrets

Add the settings in Section 7.2 to `core/config.py`, document them in
`backend/.env.example` and `backend/README.md`, and pass these values only to
the API service in Compose:

```yaml
SARVAM_API_KEY: ${SARVAM_API_KEY:-}
SARVAM_MODEL: ${SARVAM_MODEL:-sarvam-105b}
SARVAM_TIMEOUT_SECONDS: ${SARVAM_TIMEOUT_SECONDS:-8}
SARVAM_MAX_RETRIES: ${SARVAM_MAX_RETRIES:-0}
```

The key must never be placed in `VITE_*` variables, frontend source, browser
requests, the database, or logs. Add `sarvamai>=0.1.29` to
`backend/pyproject.toml` and regenerate `backend/uv.lock`.

## 10. Frontend Drawer

Extend `frontend/src/lib/ops.ts` with:

```typescript
export interface AskScope {
  vendor?: string | null;
  office?: string | null;
}

export interface GroundedFrom {
  marts: string[];
  cycle: string;
}

export interface AskResponse {
  sql: string;
  rows: Record<string, unknown>[];
  narrative: string;
  grounded_from: GroundedFrom;
}

export function ask(
  question: string,
  cycle: string,
  scope?: AskScope,
): Promise<AskResponse>;
```

`ask()` sends `POST /ask` with JSON and raises the existing `ApiError` for all
non-2xx responses. The 422 body is passed through so the UI can render the
stable supported-intents list.

`ChatPanel` becomes a floating `Ask Actuate` control that opens a right-side
drawer on desktop and a full-width bottom sheet on small screens. It submits
the active cycle from `App`, renders the narrative and no more than 50 rows,
and exposes SQL plus sources in a native disclosure element. It must render
loading, success, network-error, unsupported-intent, and empty-result states.

The drawer keeps at most ten question/response entries in React state. It does
not use localStorage, IndexedDB, cookies, or a database table. The Sarvam key
is never present in frontend configuration.

## 11. Test Vectors And Required Tests

### 11.1 Seed data

Extend the existing SQLite mini-marts with:

- At least 51 vendor rows for one cycle to prove the query limit.
- At least 51 office rows for one cycle to prove the query limit.
- Two vendors and two offices with different OTA, cost, CSAT, and no-show
  values.
- Open and closed Sev-1 alerts represented in mart rows.
- Rows with zero and null `open_sev1_count`, `unclassified_severity_count`,
  `cost_outlier`, and KPI values.
- At least two shift rows with different no-show rates.
- An empty target mart case.

### 11.2 Backend tests

Add these tests before implementation and confirm each fails first:

- `test_ask_query.py`
  - One parser test for every supported intent.
  - Ambiguous metric/dimension rejection.
  - All query row shapes, ordering, scope predicates, and 50-row limits.
  - SQLite execution for every plan.
  - PostgreSQL dialect compilation for every plan.
  - Plan safety rejection for a missing limit, non-Select, disallowed mart,
    semicolon, and raw table reference.
  - Cycle default and explicit cycle behavior.
- `test_ask_api.py`
  - One successful API test for every supported intent.
  - Empty result, empty marts, unknown cycle, invalid scope, unsupported
    question, SQL-like question, and no-query-on-422 cases.
  - Assert response rows, SQL, narrative, and grounded sources.
- `test_narrate.py`
  - Exact template facts for every intent and no-data case.
  - Fake provider success receives only bounded facts.
  - Missing key, timeout, provider error, empty choices, blank content, and
    `content=None` fallback.
  - `reasoning_effort=None`, model, timeout, and retry settings are passed.
  - Fallback log contains the required flag but no secrets or facts.
- `test_briefing_narrate.py`
  - Cached deterministic payload is reused.
  - Narrated output adds `data.narrative` without changing the cache.
  - Default `/briefing` response has no provider call and no narrative cache.
- `test_migrations.py`
  - Migration creates the new columns and `shift_kpi` on PostgreSQL.
  - Applying the migration twice is safe.

Extend the raw-table prohibition test to inspect every `/ask` statement. The
following strings must not occur as table references:

```text
trips
legs
bills
alerts
feedback
```

### 11.3 Frontend tests

Add tests for drawer open/close, active-cycle submission, loading, success,
empty result, network error, 422 supported intents, row rendering capped at
50, and SQL/source disclosure. Verify that the key is absent from the built
frontend environment and source tree.

## 12. Files To Touch

New files:

- `backend/src/backend/core/ask.py`
- `backend/src/backend/core/narrate.py`
- `backend/src/backend/api/ask.py`
- `backend/src/backend/scripts/migrate.py`
- `backend/migrations/001_story07_ask_marts.sql`
- `backend/tests/test_ask_query.py`
- `backend/tests/test_ask_api.py`
- `backend/tests/test_narrate.py`
- `backend/tests/test_briefing_narrate.py`
- `backend/tests/test_migrations.py`
- Frontend chat component tests

Edited files:

- `backend/src/backend/app.py`
- `backend/src/backend/api/ops.py`
- `backend/src/backend/core/config.py`
- `backend/src/backend/core/analytics.py`
- `backend/src/backend/core/marts.py`
- `backend/src/backend/models/marts.py`
- `backend/src/backend/models/__init__.py`
- `backend/src/backend/scripts/ingest.py`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/.env.example`
- `backend/README.md`
- `backend/Dockerfile`
- `docker-compose.yml`
- `frontend/src/lib/ops.ts`
- `frontend/src/components/ChatPanel.jsx`
- `frontend/src/App.jsx`
- Frontend briefing types and tests as needed

Removed after verification:

- `agent_end_to_end.py`

## 13. Verification Commands

Backend:

```bash
cd backend
uv run pytest
uv run ruff check .
```

Frontend:

```bash
cd frontend
npm test -- --run
npm run typecheck
npm run build
```

PostgreSQL integration:

```bash
docker compose up --build -d db
cd backend
PYTHONPATH=src DATABASE_URL="postgresql+asyncpg://actuate:actuate@localhost:5432/actuate" uv run python -m backend.scripts.migrate
PYTHONPATH=src DATABASE_URL="postgresql+asyncpg://actuate:actuate@localhost:5432/actuate" uv run python -m backend.scripts.ingest --data ../problem-statement/dataset/data
```

The story is complete only when all unit tests, lint/type/build checks, the
PostgreSQL migration test, and the Compose PostgreSQL smoke test pass.

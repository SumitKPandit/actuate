# Story 07 — Q&A `/ask` + Narration `core/narrate.py` (LLM at edge only)

**Status:** pick up after Stories 02–04. **Depends on:** 02 (KPIs), 03 (insights), 04 (API patterns + reserved `/ask`).

## 1. Goal

Transport manager asks in plain language ("Which vendor drove June OTA drop?") and gets a grounded answer: generated SQL + mart rows + short narrative. Works offline (template) and better online (Sarvam) — never hallucinates row-level facts.

## 2. Scope

**In:**
- `backend/src/backend/core/narrate.py`: `render_template(facts) -> str` + `narrate_with_sarvam(facts) -> str` with offline fallback.
- `POST /ask` in `api/ops.py` (or new `api/ask.py`): `{ question, cycle?, scope? }` → `{ sql, rows, narrative, grounded_from }`.
- Frontend chat drawer (available from `/` and `/dashboard`) calling `/ask`.
**Out:** generic SQL agent / unguarded querying (allowlist only), per-row LLM calls (forbidden).

## 3. Functional requirements

1. **NL→SQL guardrails:** allowlisted query builder over marts only (`daily_kpi`, `vendor_kpi`, `office_kpi` + insight_cache). Supported intents (minimum): OTA by vendor/office, cost outlier vendor, Sev-1/open alerts, CSAT low cluster, no-show by shift/office. Anything else → 422 with `supported_intents` list. Returned `sql` is the actual executed statement (read-only `SELECT`, 1 statement, `LIMIT ≤ 50`); response includes `rows` + `grounded_from` (mart names + cycle).
2. **Narration:** `render_template` covers all supported intents deterministically (e.g. "OTA {cycle} was {v}% vs SLA 95%. {vendor} drove {share}% of the gap ({n}/{m} late trips)."), including data-quality footnotes (unclassified severity count, zero-km share) when relevant. `narrate_with_sarvam` takes the **same facts dict only** (never raw CSV rows), calls Sarvam `sarvam-30b` via OpenAI-compatible `base_url=https://api.sarvam.ai/v1`, `reasoning_effort=None`, ~1 call per Q&A/briefing; any missing key / timeout / non-200 → template fallback (log `narrate_fallback=true`, never 500).
3. **Briefing hook (optional, cheap):** `GET /briefing?cycle=&narrate=true` reuses `narrate.py` on headline facts; default `false` keeps Story 04 behavior (cached template).
4. **Chat drawer UX:** floating button → side drawer; shows question, narrative, mini table (≤ 50 rows), collapsible "SQL + sources" details; loading/error/422 states; no chat history persistence (single-session list ok).
5. **Secrets:** Sarvam key from env (`SARVAM_API_KEY`), never in repo/logs; add to `backend/.env.example` + README.

## 4. Acceptance criteria

- [ ] Offline (no key / blocked network): all 5 minimum intents return correct `sql` + `rows` + template narrative; tests force fallback via monkeypatched client error.
- [ ] Online (key present): narrative comes from Sarvam but numbers match `rows` (test with recorded/fake client asserting facts-dict passed, not live call in CI).
- [ ] Disallowed question ("drop tables…", non-mart intent) → 422, no SQL executed.
- [ ] `sql` with `;` injection / non-SELECT → rejected before execution.

## 5. Test plan (test-first)

- `backend/tests/test_narrate.py`: template per intent + fallback on client error + missing-key fallback.
- `backend/tests/test_ask_api.py`: one test per minimum intent (assert `sql` allowlist + row values from mini-marts), `test_ask_rejects_non_select`, `test_ask_422_unknown_intent`, `test_ask_offline_fallback`.
- Frontend: drawer open/ask/render/422 states (mock fetch).
- Commands: `uv run pytest backend/tests/test_narrate.py backend/tests/test_ask_api.py` green; `ruff` clean.

## 6. Files to touch

- New: `backend/src/backend/core/narrate.py`, `backend/tests/test_narrate.py`, `backend/tests/test_ask_api.py`, `frontend/src/components/chat/*`.
- Edit: `api/ops.py` (add `POST /ask`), `backend/.env.example`, `backend/README.md`, `frontend/.env.example` if drawer needs flag.
- Do not: add LLM per-row calls, new ORM tables (use `insight_cache` for optional caching).

## 7. Notes

- Cost/latency budget (PLAN §5): ~1–2 sarvam-30b calls per session; marts keep p95 low; briefings cached. Enforce by construction (single `narrate()` call site per request).
- Keep prompts tiny: facts JSON + "narrate in 2–3 sentences for a transport manager, do not invent numbers."

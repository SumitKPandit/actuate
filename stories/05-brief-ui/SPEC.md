# Story 05 — Brief UI `/` (transport manager's one page)

**Status:** pick up after Story 04. **Depends on:** 04 (`/briefing`, `/insights`, `/actions` contracts frozen).

## 1. Goal

Transport manager opens `/` and in < 30 seconds knows: what slipped, which vendors/offices drive it, which safety items need acknowledgement, and what to do next. No manual report assembly.

## 2. Scope

**In:** rewrite `frontend/src/routes/index.tsx` (+ small components under `frontend/src/components/brief/`) reading `VITE_API_URL` (see `frontend/.env.example`). Chat drawer is Story 07 — leave a placeholder entry point only.
**Out:** dashboard charts (Story 06), NL Q&A (Story 07), any direct DB/CSV access.

## 3. Functional requirements

1. **Data:** on load, `GET /briefing?cycle=` + `GET /actions?cycle=` (cycle selector defaults to latest; options from API 404 payload or `/overview` cycles). Loading / error / empty-marts-warning states required (surface API `warning` verbatim).
2. **Layout (top→bottom):**
   - Cycle selector + `generated_at` stamp + benchmark chips (OTA SLA 95% · Ack 30 min).
   - Headline facts (3–5 template strings from `/briefing`).
   - Ranked exception feed (top 5): each card shows KPI, scope (vendor/office/cycle), current vs baseline Δ, severity badge, reach (trips), contribution ("2 vendors = X% of gap"), recommended action + owner.
   - Safety strip: open Sev-1 count + unacknowledged count + oldest unacked age; links to dashboard vendor filter (Story 06 hook — keep as query param `?vendor=` even if dashboard lands later).
   - Actions: top 3 with owner chip + **Copy-for-vendor button** (clipboard, ≤ 500 chars, toast confirm).
3. **Performance/robustness:** no per-row rendering (aggregate cards only); API base missing → inline error naming `VITE_API_URL`; brief cached server-side so page needs ≤ 2 fetches.
4. **Style:** reuse existing tokens in `src/styles.css` (`island-shell`, etc.); no new design system; mobile-readable single column.

## 4. Acceptance criteria

- [ ] With API stubbed (msw or fixture JSON in `stories/05-brief-ui/sample-briefing.json`), page shows all §3.2 sections with correct numbers/badges.
- [ ] Copy-for-vendor copies exact `copy_for_vendor` string (test asserts clipboard content).
- [ ] Empty-marts warning from API renders as banner, not blank page.
- [ ] `npm run build` + `eslint` clean; existing `/about` route unaffected.

## 5. Test plan

- Component/integration test (Vitest + Testing Library — add if missing, minimal): `brief renders feed`, `copy button`, `empty warning`, `loading state`.
- Manual check: `docker compose up --build` → `http://127.0.0.1:3000` shows live `/briefing` data; note result in story folder.
- No backend changes in this story (mock at fetch boundary).

## 6. Files to touch

- Edit: `frontend/src/routes/index.tsx`; new: `frontend/src/components/brief/*`, `frontend/src/lib/ops.ts` (typed fetch client for Story 04 schemas — reuse in Story 06).
- Sample fixture to add here: `stories/05-brief-ui/sample-briefing.json` (captured real or hand-built to API schema).

## 7. Notes

- Current `index.tsx` is the TanStack starter placeholder ("Start simple…") + `StackStatus` demo — replace hero content but keep `StackStatus` until Story 08 cleanup decides.
- Keep `routeTree.gen.ts` generated (do not hand-edit).

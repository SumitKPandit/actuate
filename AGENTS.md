# AGENTS.md — Working Agreement (Non-Negotiable)

1. **EVIDENCE BEFORE ACTION:** Never guess. Read the existing code, docs, and requirements first until you understand the workflow and intent. If evidence for an implementation decision is missing, ask the user before implementing it. Use judgment for trivial calls (naming, wording) — don't stall on those.
2. **SIMPLICITY (KISS, YAGNI, DRY):** Implement the absolute minimum code required. Code must be simple, clean, maintainable, testable, and debuggable. Every line changed must have a clear justification. Prefer fewer lines.
3. **TEST DISCIPLINE:** Bug fixes and behavior changes REQUIRE a failing test first, confirmed red in terminal output before writing the fix. Exempt: pure deletions, refactors already covered by a green suite, and docs/config-only edits. New features must include tests covering the new behavior before the work is considered done.
4. **VERIFY SUCCESS:** Run the relevant tests and linters after every change and loop until green. Report the command and result; never declare success from intent.
5. **MODULARITY:** Write modular code. Avoid monolithic functions and classes. Each function does one thing and does it well.
6. **DOCUMENT + GIT HYGIENE:** After any behavior change, update all affected docs to match the current code. Before committing, check `git status` for files that must never be tracked (secrets, `.env`, local DBs, caches, build output, dependencies) and ensure `.gitignore` covers them. Never commit secrets.

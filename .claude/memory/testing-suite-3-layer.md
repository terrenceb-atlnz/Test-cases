---
name: testing-suite-3-layer
description: Ask-CK has a 3-layer test suite + one gate — pytest (backend) + Vitest/jsdom (frontend) run by run_tests.sh; Playwright E2E is sparingly-run separately
metadata: 
  node_type: memory
  type: project
  originSessionId: 5da34e66-6995-49af-8d5e-491007959772
  modified: 2026-07-27T00:32:32.933Z
---

Built 2026-07-27f (commits `4f990ea`→`e871caa`, pushed to `main`). Ask-CK now has three
automated-test layers:

- **Backend units** — `tests/` (pytest, in-process TestClient, no network/LLM/testbox; **190 tests** as of 2026-07-27g).
- **Frontend units** — `js-tests/` at repo root (Vitest + jsdom, no browser/server/LLM; **72 tests** as of 2026-07-27g).
  Covers DOM/button helpers, table renderers, chosen-list, and `db-search.js` `merge*` (exported
  for testability). DOM fixtures are lifted from the REAL `index.html` and throw on a renamed id
  (drift-detection).
- **E2E** — `e2e/` at repo root (Playwright, one Chromium golden-path). **Sparingly-run, NOT in the
  gate.** Asserts the export validation gate BLOCKS an un-synthesized case (a green export needs
  LLM synthesis, so the deterministic assertion is the blocked outcome).

**How to run:**
- `./tool/run_tests.sh` = THE regular gate: guards + pytest + `npm test` (Vitest). Fails loudly if
  Node deps aren't installed.
- `npm test` / `npm run test:watch` — frontend units only.
- `npm run e2e` — Playwright E2E (sparingly; starts/reuses the server via run.sh).

**Why:** the user wanted regression protection after big changes; chose Vitest over Jasmine for
readable failure output, and E2E-first as a known-good reference the unit layer derives from.

**2026-07-27g:** the adversarial-review batches grew the suite (48→190 pytest, 47→72 Vitest) and
introduced **structural** tests alongside example-based ones — e.g. an AST sweep asserting no async
handler calls a blocking function without `run_in_threadpool`, and source assertions that a guard
precedes a state write. These catch the NEXT regression, not only the filed one; prefer that shape
where a defect has a machine-checkable form. Test fixtures must clear BOTH the in-memory session and
the persisted `ck.db` row — an in-memory-only pop leaks throwaway keys into the permanent DB and
masks failures across tests.

**How to apply:** run `./tool/run_tests.sh` before committing frontend/backend changes; run the
E2E on demand (pre-release), not every commit. JS tooling (`package.json`, configs, `e2e/`,
`js-tests/`) lives at repo root, separate from `static/js`; `node_modules` + PW artifacts are
gitignored. No CI runner yet (`.github/workflows`). See [[user-prefers-manual-ui-testing]] — the
E2E/manual layer still owns the visual checks jsdom can't see (spinner animation, flash colors).
Plans: `ask-ck/ck-facelift/PLAN-playwright-e2e.md`, `PLAN-frontend-unit-tests.md`.

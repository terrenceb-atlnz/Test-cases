---
name: svelte-app-served-at-root
description: Since 2026-10-30 "/" is Trent's Svelte app served from the COMMITTED svelte/dist; rebuild with ask-ck/tools/build_svelte_app.sh and commit dist/; Classic at /classic; the restyle is unserved; the app reads no ?panel= deep links yet
metadata:
  type: project
  verified: 2026-10-30
---

**Since 2026-10-30 (`ask-ck/plans/PLAN-svelte-cutover.md`) the UI at `/` is Trent Morgan's Svelte app**
(`ask-ck/frontend/ck-main/svelte/`, Vite + Svelte 5, merged from `origin/userinterface`). The server
serves its **committed** `dist/`: `/assets` (content-hashed, immutable), one route per `public/` file,
and `dist/index.html` for every route in `svelte/src/routes.js` (`main.SPA_ROUTES`, an explicit tuple
— no catch-all). **Classic** (`current/`) stays at `/classic` with its files at `/static`; the ATUI
restyle is **unserved** (files kept).

**Why:** the hosted server serves files only and the working tree is production, so the build cannot
happen on the server — `dist/` ships in git, like the islands. A missing `svelte/dist/assets` fails
the server at import on purpose.

**How to apply:**
- After ANY edit under `svelte/src`, `public/`, `index.html`, the configs or `package*.json`: run
  `ask-ck/tools/build_svelte_app.sh` (needs `npm install --legacy-peer-deps` in `svelte/` once per
  clone), then `git add ask-ck/frontend/ck-main/svelte/dist` and commit. `tests/test_svelte_app_built.py`
  recomputes the `dist/.source-sha256` stamp and fails the gate when stale.
- A new route in `routes.js` needs the same path in `main.SPA_ROUTES` (test enforces it) — one
  `main.py` reload. A new file in `svelte/public/` likewise gets its root route only after a reload.
- The gate runs the app's own Vitest as a fourth layer (`run_tests.sh`), so `svelte/node_modules`
  must exist or the gate exits 2.
- Known at cutover (checklist in the plan §2): the app reads NO query parameters, so the Finalize
  link written into Zephyr (`/?panel=composer&script=…`) and run e-mails (`/?panel=tc-runs&run=…`)
  land on its home page — prefix `/classic` by hand until ported; it does not poll `/api/version`;
  `navigator.clipboard` is used (undefined on http seats); no session restore on refresh.
- Related: [[editing-backend-restarts-production]] (the `main.py` edit reloaded production once),
  [[askck-lan-hosting]], [[gate-does-not-start-the-server]].

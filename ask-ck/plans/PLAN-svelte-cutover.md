# PLAN — Svelte cutover: Trent's app at `/`, Classic at `/classic`, the restyle unserved

> ## Status (read first)
>
> **LIVE on main since 2026-10-30 10:01 (`41f0c44`, Terrence: "Land it now"); the manual browser
> checklist (§4) is NEXT, against production.** Approved by Terrence the same day from a read-only
> survey of `main`, `origin/userinterface` and the server; built on branch `svelte-cutover` in a
> scratch worktree, verified there, then landed as two fast-forwards.
>
> **Step 6 record:** no seat had touched the server in the 10 min before. FF 1 to `3b3a761` (merge +
> dist, no `.py` → no reload), `npm install --legacy-peer-deps` in `svelte/` on main, FF 2 to `41f0c44`
> → StatReload at 10:01:12, new worker up at 10:01:14 (2 s, no wedge), `/health` ok with the
> permanent db, `/` = the Svelte app on localhost and on `http://10.33.22.13:8000/`, `/classic`,
> `/assets` immutable, `/restyle` 404. **Gate on main: ALL GREEN** — pytest 2114 / 6 skipped, root
> vitest 409, Svelte vitest 121 (18 todo). One snag on the way: the Vite scaffold's untracked
> `svelte/src/lib/Counter.svelte` had sat on main's disk hidden by the old `lib/` ignore rule; Trent's
> `/lib/` rule unhid it and the freshness guard hashed it (first gate red on that one test) — removed
> (never tracked, referenced by nothing). Scratch server stopped, worktree removed; the merged local
> branch `svelte-cutover` is left in place (not asked). **Terrence pushes** (main is 36 ahead of
> origin). Trent should rebase `userinterface` onto main and finish `ToolPage` (see step 1).
>
> **Sync 2, same day (`af658b9` + `366b6e9`):** Trent's `8434747` ("implemented Terrence feedback",
> 9 Svelte source files + T44333 PyTest history + two run records) merged clean on branch
> `svelte-sync`, dist rebuilt (new hashed assets), guard green, Svelte vitest 121, fast-forwarded —
> no `.py`, so no reload; production picked the new bundle up on the next load. Gate on main ALL
> GREEN (pytest 2114 / 6 skipped, vitest 409, Svelte 121). Merge-base is now his tip, so the three
> excluded data sets stay excluded. His tip still imports `ToolPage.svelte` (the restored file
> keeps it building).
>
> **What happened at each step (the record):**
> - **Step 1 merge** (`49164c5`): the two predicted conflicts, both to Terrence. `.families.json` →
>   Trent's (adds 9003). `library_9002.py` was NOT a superset case: main's 19 helpers (T33241) and
>   Trent's 37 (T33247, ARP/GARP/MAC-table) were disjoint, so the resolution is the **union** —
>   main's text byte for byte, his 5 extra imports and 37 helpers appended (56 top-level names, no
>   clash; both scripts keep what they `import *`). `ZtPage.svelte` restored from main (#25).
> - **Trent's tip did not build**: `App.svelte` imports `./pages/ToolPage.svelte`, which his `87ddf78`
>   deleted; the `{:else}` branch that renders it is unreachable. Terrence: restore the 18-line file
>   byte-for-byte from `87ddf78^` (done in `3b3a761`). **Closed the same day (sync 3, `7e987bf`):**
>   Terrence — *"if we don't need it, delete it again"* — so the import, the `toolPages` data block,
>   the unreachable `{:else}` branch and the file are gone.
> - **Step 2** (`3b3a761`): `dist/` committed (1.8 MB, 20 files), `build_svelte_app.sh`,
>   `test_svelte_app_built.py` (red on a one-byte source edit, proven), both `.gitignore`s.
> - **Step 3** (`b8aa39c`): `main.py` as planned; `test_svelte_app_served.py` 12 checks (the
>   `SPA_ROUTES == routes.js` check goes red when a route is dropped, proven); the parity test's
>   four served-route asserts dropped; Classic's ATUI toggle removed.
> - **First full gate was RED (4)**: the known worktree false red, plus three of Trent's data sets —
>   `9001_Port` regenerated with framework imports (test G8 cannot exec it), the pre-numbering
>   `generated/IPv6/` (bench-safety lint: `no privilege level`), and the T44333 bundle (empty Zephyr
>   section). Terrence chose to **exclude all three** rather than touch a test (`203c7d9`); D4 now
>   reads "kept, minus those three". Family 9003 stays registered.
> - **Step 4**: Trent's Vitest in the gate: 4 files / 121 tests pass, 18 todo, 27 files skipped.
> - **Step 5**: records below updated; memory `svelte-app-served-at-root`.
>
> **What it supersedes.** Two settled decisions are overtaken by this plan and carry a ⚠ line at
> their source, not a rewrite: **S9** in [`archive/plans/PLAN-atui-restyle.md`](../../archive/plans/PLAN-atui-restyle.md)
> (*"DO NOT REPLACE CURRENT… both UIs are permanent"*, 2026-09-30) and **C-D1** in
> [`PLAN-test-composer.md`](PLAN-test-composer.md) (new UI = Svelte islands in `current/`, *"not
> Trent's app"*, 2026-10-09). The islands keep working, on `/classic`.
>
> **Decisions (Terrence, 2026-10-30):**
> - **D1** Trent's app is served at `/`. Classic (`current/`) stays served at **`/classic`**.
> - **D2** `restyle/` is **unserved only**: its routes and Classic's ATUI link go; files and tests
>   stay (tests rewritten so they pass unserved). Deletion is a later decision.
> - **D3** `origin/userinterface` is **merged into main** (`--no-ff`). **Conflicts are shown to
>   Terrence**, never resolved silently.
> - **D4** The branch touches no `ck.db`. Its data files under `ask-ck/functions/` are **kept** —
>   minus three sets excluded on 2026-10-30 after the first gate (see the record above).
> - **D5** **No gap-fixing before cutover** (checklist §A). Recorded as follow-ups.
> - **D6** **ATUI not required** for the Svelte app (S6 still holds).
> - **D7** Server-written deep links (`/?panel=composer&script=…` Finalize link in Zephyr,
>   `/?panel=tc-runs&run=…` run e-mails) were left as-is at cutover. **Ported the same day at
>   Terrence's ask:** `testComposerModel.deepLink` (pure, Classic's contract + a `/composer?script=`
>   path form) read once in `App.svelte` on mount → `TestComposerPage` gains `initialTab` + `openRun`
>   and hands `preselect`/`openRun` only to the tab it opened on. Spec: his
>   `tests/components/testcomposer/testComposerModel.spec.js` (7). The server still writes the
>   same links, so nothing already in Zephyr or e-mails changes. Not yet: a Run Scripts share link
>   opens the tab but does not fill it (`TcRun` has no `link` prop). **Browser check pending** (§2 #6).
> - **D8** Trent's Vitest suite is **added to the gate**, plus a dist-freshness pytest guard.
> - **D9** Built `dist/` is **committed** and hash-guarded like the islands, **without editing
>   Trent's `vite.config.js`** (a wrapper script writes `dist/.source-sha256`).
>
> **Step status:** 0 worktree ☑ · 1 merge ☑ · 2 dist + guard ☑ · 3 server + tests ☑ · 4 gate ☑ ·
> 5 records ☑ · 6 landed on main ☑ · manual checklist ☐ (against production, §4) · sync 3 ☑ (deep links, stale-tab guard, ToolPage gone).

## 1. Context

Terrence: *"I want to cutover to using the Svelte interface instead of current/restyle."* Found
read-only on 2026-10-30:

- `ask-ck/frontend/ck-main/svelte/` on `main` is the untouched create-vite scaffold (one commit,
  `60aafcc`, 2026-09-11). **The real app is Trent Morgan's, on `origin/userinterface`**: 30 commits,
  2026-10-20 → 2026-10-29, merge-base `3e5ac76`, unmerged. Vite + Svelte 5; routes in
  `src/routes.js` (`/`, `/help`, `/llm`, `/settings`, `/generator`, `/pytest`, `/composer`,
  `/zephyr`); history-API routing by pathname only; CodeMirror; its own Vitest suite (34 spec
  files, most `describe.todo`). Its README says the backend does not serve its `dist/` yet; it runs
  only via the Vite dev server on :5173 proxying `/api`.
- The server (`ask-ck/CK-main/CK_server/main.py`) serves `current/index.html` at `/` (:260-265),
  `current/` at `/static` (:186), `restyle/index.html` at `/restyle` (:267-271), `restyle/` at
  `/restyle/static` (:193). Classic has no per-page routes; it switches panels by `?panel=`.
  `FRONTEND_DIR` is `paths.py:51`. `/api/version` (:390-420) hashes `current/` only.
- Backend Python imports from `current/` are not UI and must keep working: `routers/pytest_create.py`
  (:2474, :3702) adds `current/pytest-creator` to `sys.path` for `cli_lookup`;
  `routers/wizard/export.py:492` runs `current/generator/upload_refined.py`.

## 2. Known-issue checklist (the test record)

Legend: [README] = Trent's README claim · [CONF] = confirmed by reading the branch · [SUSP] = verify.
Record each outcome here as it is tested.

### A. Carried in from Trent's app (ship as-is, D5)
1. No session restore on refresh [README]. Test: F5 mid-Generator.
2. Admin "Reset current case session" not ported [README]; two `resetSession` refs exist — check for a stub.
3. Not responsive [README].
4. ~~`navigator.clipboard.writeText` ×4~~ **REPLACED 2026-10-30** (Terrence: `execCommand('copy')` fails on every seat too, so no clipboard write anywhere): `lib/utils/select.js` `selectForCopy` — the share-link buttons in Compose and Run Scripts reveal the link in a readonly box, selected; the log viewer's button selects the pane; Help's buttons select the command box; every label says "Selected — press Ctrl+C". Spec: `tests/utils/select.spec.js`. To verify in a browser: each of the four, then Ctrl+C and paste.
5. ~~No `/api/version` poll~~ **PORTED 2026-10-30**: `lib/services/versionService.js` (from Classic's `shared/version.js`) polls every 60 s, prompts once per tab via his ConfirmModal, never reloads by itself. Spec: `tests/services/versionService.spec.js`. To verify in a browser: leave a tab open across a `build_svelte_app.sh` + commit; the prompt appears within a minute.
6. ~~No query-parameter reads~~ **PORTED 2026-10-30** (D7): `?panel=composer|validation|tc-runs|run-scripts` and `/composer?script=|run=` open Test Composer on the right tab with the script/run. To verify in a browser: a Finalize link from Zephyr, a run e-mail link, and `/composer?script=9002_IPv4/test-9002.33241.py`. His TcCompose share link (`?panel=composer&project=…`) opens Compose but its `project`/`wiki`/`template` fields are not read; a Run Scripts link opens the tab unfilled.
7. Admin mode is client-side only [README]; verify `/api/admin` calls and URL reachability.
8. PyTest→Composer "Validate Test" preselect is in-memory via `selectPage`; refresh loses it [CONF].
9. Vitest: 2 real spec files, rest `describe.todo`, e2e empty [README].
10. PageCard placeholders on Llm/Settings/Tool pages [his memory note]; `/llm` is in `routes.js` but not App.svelte's `routeMap`, so it renders Home [CONF].
11. TcValidate.svelte direct `fetch` bypasses services [README]; headers still patched globally — verify X-CK-Session on validate.
12. Theme does not carry between `/` and `/classic` (different storage keys) [SUSP, cosmetic].

### B. Created by the cutover (solved by steps 3–4)
13. SPA refresh on every route in `routes.js` must serve `dist/index.html`.
14. Root assets `/assets/*`, `/askck-logo.png`, `/icons.svg` (Trent's page icon is `/askck-logo.png`; `/favicon.svg` stays Classic's — the two favicon files differ [CONF]).
15. StaticFiles raises at startup if `dist/` is missing ⇒ `dist/` lands on main before `main.py` points at it.
16. `/api/version` must hash `dist/` + `current/`.
17. `dist/index.html` no-cache; hashed `/assets/*` immutable.
18. The `main.py` edit reloads production; wedge risk on agent long-polls ⇒ `ck restart`.
19. `test_restyle_parity.py`: drop asserts for `/restyle` served, `/` not ATUI, Classic→`/restyle` link; keep id-parity asserts.
20. Classic at `/classic`: no path navigation or `href="/"` in `current/` [CONF]; share links now carry `/classic?…`.
21. Locks across both UIs (his `lockService.js` exists [CONF]): same case from `/` and `/classic` on two seats.
22. Per-seat LLM header on each page; claude_agent call from a tool page without visiting Settings.
23. ~~Help page one-liner shows the real origin~~ It was **typed in** (`http://10.33.22.13:8000`), not derived — fixed 2026-10-30: `agentService.seatSetupCommands(window.location.origin)` (ported from Classic), spec in `tests/services/agentService.spec.js` incl. a no-literal-address check on HelpPage.svelte.
24. Backend imports from `current/` (`cli_lookup`, `upload_refined.py`) unaffected; deleting `current/` later would break them.

### C. Merge-time
25. ZtPage.svelte silently deleted by the merge (Trent's `20a3039` git mv; main's blob = base blob) ⇒ restore from main before committing the merge; islands guard stays green.
26. `.claude/memory/MEMORY.md` both sides, different hunks (should auto-merge; show the result).
27. `generated/.families.json` both sides, same lines ⇒ real conflict; Trent's is the superset (adds 9003).
28. **`generated/9002_IPv4/library_9002.py` add/add conflict [CONF]**: main 656 lines (`114aa3f`, the tool's T33241 library), Trent 851 lines (`109f709`), absent at the base. Terrence decides.
29. `.meta/IPv6/ssh_ipv6/` sits outside the numbered-family layout — check server tolerance.
30. Trent's `.gitignore` `lib/`→`/lib/` is load-bearing (main's `lib/` would ignore `svelte/src/lib/`); merges cleanly.
31. Three 2026-10-29 Validation run records arrive; the untracked 2026-10-19 one is still undecided.

### D. Toolchain / gate
32. `dist/` ignored twice (root `.gitignore:11`, nested `svelte/.gitignore:11`; nested wins today).
33. His deps not installed here (`svelte/node_modules` = scaffold's 32 entries); `npm install --legacy-peer-deps`; README says Node 22, host has 24.15 (Vite 8 accepts it).
34. Gate needs two `npm install`s; the no-stray-py hook blocks an install command that also names a `.py`.
35. If any of his real specs is red today, the gate goes red on main — run in the worktree first and report; never fix his specs silently.

### E. Records
SERVER-README :51-54/:118/:147-151/:1606 · ARCHITECTURE :46-48 · README :272-275/:308 ·
current/README :9 + convention 6 (:110-127) · CLAUDE.md :8 · paths.py :8/:47-50 comments ·
⚠ on S9 and C-D1 · `tests/e2e/pages/generator.page.js:63` (`goto('/')`, not run).

## 3. Implementation steps

All work happens in a **scratch worktree** on branch `svelte-cutover` and is trialled on the scratch
server (:8123) before landing on main. Rules in force: write only inside this repo; commit, never
push; ck.db never touched; conflicts to Terrence.

### Step 0 — worktree
`GIT_LFS_SKIP_SMUDGE=1 git worktree add -b svelte-cutover <scratchpad>/wt main`; symlink `.venv`,
`node_modules`, `ask-ck/db` in and mark the db paths skip-worktree (method: memory
`editing-backend-restarts-production`; expect the one known false red
`test_the_audit_log_is_not_committed` in a worktree).

### Step 1 — merge `origin/userinterface` (D3, D4)
1. `git merge --no-ff origin/userinterface`. Expected stops: `.families.json` (#27) and
   `library_9002.py` (#28). **Stop and show both to Terrence** with the three versions; apply his
   choice. Show the auto-merged `MEMORY.md` too (#26).
2. Before committing: `git checkout main -- ask-ck/frontend/ck-main/current/svelte-src/src/zt/ZtPage.svelte` (#25).
3. Commit the merge. Verify: no deletion under `current/` in `git show --stat HEAD`;
   `pytest -q tests/test_svelte_islands_built.py` green; `git status` clean.

### Step 2 — build, un-ignore, guard, commit `dist/` (D9) — no `.py` under `CK-main`, so no reload when landed
- **2a** `cd ask-ck/frontend/ck-main/svelte && npm install --legacy-peer-deps` (no `.py` token on the line, #34).
- **2b** `.gitignore`: root — keep line 11 `dist/`, add `!ask-ck/frontend/ck-main/svelte/dist/` with a
  one-line comment. Nested `svelte/.gitignore` — replace line 11 `dist` with a comment saying `dist/`
  is committed. Verify `git check-ignore -v …/svelte/dist/index.html` prints nothing.
- **2c** New `ask-ck/tools/build_svelte_app.sh`: `set -euo pipefail`; refuse if npm or
  `node_modules/vite` missing; `npm run build --silent`; then hash
  `src/** public/** index.html vite.config.js svelte.config.js package.json package-lock.json` as
  sha256 over sorted `(relpath + "\n" + bytes + "\n")` (`LC_ALL=C sort -z`, the islands'
  `vite.config.js` algorithm) and write it to `dist/.source-sha256` **after** a successful build
  (Vite empties `dist/` first, so a failed build leaves no stamp).
- **2d** New `tests/test_svelte_app_built.py`, modelled on `tests/test_svelte_islands_built.py`:
  recompute the hash in Python (`sorted(relative_to(APP).as_posix())`), fail with "run
  ask-ck/tools/build_svelte_app.sh and commit dist/" when stale; assert every `/assets/*` and root
  file referenced by `dist/index.html` exists; assert `package-lock.json` is committed. Mutation check
  before claiming: touch one source byte → red, revert → green.
- **2e** Commit: both `.gitignore`s, `svelte/dist/` (index.html, assets/*, askck-logo.png,
  favicon.svg, icons.svg, .source-sha256), the script, the test.

### Step 3 — server + tests (one commit; one production reload when landed)
**`ask-ck/CK-main/CK_server/main.py`** (anchor lines as of 2026-10-30):
- :179 no-cache condition → `/static/` only; add an `elif path.startswith("/assets/")` branch
  setting `public, max-age=31536000, immutable`.
- :183-193 → keep the `/static` mount; **delete** `RESTYLE_DIR` and the `/restyle/static` mount; add
  `DIST_DIR = FRONTEND_DIR.parent / "svelte" / "dist"` and
  `app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="app_assets")`
  (fail-fast at import if `dist/assets` is missing, deliberately — #15).
- :260-271 → replace `root()` and `restyle_root()` with:
  - `SPA_ROUTES = ("/", "/help", "/llm", "/settings", "/generator", "/pytest", "/composer", "/zephyr")`
    — an **explicit tuple mirrored from `routes.js`, not a catch-all**, so `/api/…`, `/static/…`,
    `/setup/…` typos keep 404-ing; one handler `spa_index()` returning `dist/index.html` with
    `Cache-Control: no-cache`, registered for each route.
  - Root public files: for each regular file in `DIST_DIR` except `index.html`, dotfiles and
    `favicon.*`, register `GET /<name>` → `FileResponse` no-cache (`/askck-logo.png`, `/icons.svg`).
    `/favicon.ico|.svg` (:250-257) keeps serving `current/favicon.svg` (#14).
  - `GET /classic` → `current/index.html`, no-cache (D1). `?panel=` deep links keep working there.
- `_static_build_id()` (:390-409): walk both `static_dir` and `DIST_DIR`, keyed `current/…` and
  `dist/…` (#16); fix its comment.
- **`paths.py`** :8 and :47-50 comments only.

**`ask-ck/frontend/ck-main/current/index.html`** :36-40 — delete the `#ui-toggle` block (the ATUI
link). Nothing in JS or tests references `#ui-toggle` [CONF]; `.ui-toggle` CSS stays.

**`tests/test_restyle_parity.py`** — delete `test_restyle_route_serves_the_restyle_page`,
`test_root_still_serves_current`, `test_restyle_static_serves_its_own_files`,
`test_swap_control_points_each_way` (and the `links` collection they used); keep id/data-action
parity, `sidebar-logo`, same `main.js` tag, `data-ui` flag, own stylesheet, sidebar sections,
pre-paint theme; docstring: "unserved since the Svelte cutover, kept mountable".

**New `tests/test_svelte_app_served.py`** (session `client` fixture, `tests/conftest.py:333`):
`SPA_ROUTES` == the set parsed from `src/routes.js`; every SPA route returns `dist/index.html` with
`no-cache`; `/classic` == `current/index.html` and `/` != it; `/restyle` and
`/restyle/static/styles.css` → 404; every `src=`/`href=` in `dist/index.html` resolves (assets carry
`immutable`); `/icons.svg` 200; `/api/nope`, `/static/nope.js`, `/setup/nope`, `/not-a-route` → 404;
`/favicon.svg` bytes == `current/favicon.svg`; `/api/version` stamp changes after touching
`dist/index.html` (mtime only; reset the cache dict between calls).

### Step 4 — gate (D8)
`ask-ck/tools/run_tests.sh`: after the frontend-units block (:56-66), add a fourth layer "Svelte app
units": SKIP if npm missing, `exit 2` with the install hint if `svelte/node_modules/vitest` is absent,
else `(cd ask-ck/frontend/ck-main/svelte && npm test --silent)`. Update the header comment. Record his
pass/todo counts here; a red spec of his is **reported, not fixed** (#35).

### Step 5 — records (§2 E)
- This file's Status block: step ticks, the merge choices (#25–#28), his spec counts, checklist outcomes.
- One `> ⚠ 2026-10-30` line each under C-D1 (`PLAN-test-composer.md:45-49`) and §6 (:267), and in
  `archive/plans/PLAN-atui-restyle.md`'s status block (S9 superseded; files kept).
- `CLAUDE.md:8`; `SERVER-README.md` :51-54, :118, :147-151, :1606; `ARCHITECTURE.md:46-48` (the
  "no bundler by design" paragraph is now false for `/`); `README.md` :272-275, :308;
  `current/README.md` :9-11 and convention 6; a dated paragraph in Trent's `svelte/README.md` ("the
  backend now serves `dist/` at `/`; build via `ask-ck/tools/build_svelte_app.sh`"); a
  `// cutover: Classic is at /classic` comment at `tests/e2e/pages/generator.page.js:63`.
- Memory: new `.claude/memory/svelte-app-served-at-root.md` + index line (`/` = Trent's app from
  committed `svelte/dist`; rebuild with the script and commit `dist/`; Classic at `/classic`;
  restyle unserved). CHANGELOG / SESSION_STATE / PROGRESS via `/wrap-ck`.

### Step 6 — land on main (two fast-forwards, in order; Terrence pushes)
1. `git merge --ff-only <step-2 commit>` → merge + dist + script + guard on main; **no reload** (no
   `CK-main/*.py`). Confirm `dist/assets` exists on main's disk.
2. `(cd ask-ck/frontend/ck-main/svelte && npm install --legacy-peer-deps)` on main (replaces the
   scaffold `node_modules`; needed by the gate).
3. `git merge --ff-only svelte-cutover` → main.py + tests + gate + docs: **one reload**. Watch
   `/health` ~45 s; if the journal ends in "Waiting for connections to close", hand Terrence
   `ck restart` (memory `editing-backend-restarts-production`). Seats mid-call lose case locks.
4. Gate on main → report the hash → Terrence pushes. Remove the worktree (symlinks by literal path,
   then `git worktree remove --force`).

## 4. Verification

**Scratch server from the worktree** (`ask-ck/tools/run_scratch_server.sh --bg`, :8123), curl:
- `/` and each of `/help /llm /settings /generator /pytest /composer /zephyr` → 200,
  `cache-control: no-cache`, body has `<div id="app">` and `/assets/index-`; `/generator/` → 307 to `/generator`.
- `/classic` → 200 Classic HTML with no `/restyle` string; `/classic?panel=composer` → 200.
- `/assets/<name from index.html>` → 200 + `immutable`; `/askck-logo.png`, `/icons.svg` → 200;
  `/favicon.svg` bytes == `current/favicon.svg`.
- `/restyle`, `/restyle/static/styles.css`, `/api/nope`, `/not-a-route` → 404;
  `/static/shared/main.js` → 200 `no-cache`; `/health` ok; `/api/version` changes after `touch dist/index.html`.
- `./ask-ck/tools/run_tests.sh` → ALL GREEN (now four layers) in the worktree, then again on main after landing.

**Manual browser checklist for Terrence on :8123** (manual UI testing, no Playwright): open `/`,
every sidebar page, F5 on `/generator`, back/forward; load a case in Generator and PyTest and run
one LLM step; Settings LLM status; admin panel; Zephyr analysis; Composer list; theme toggle; then
`/classic`: no ATUI link, `/classic?panel=composer` opens the Composer, a Classic tab shows the
stale-tab prompt after a dist rebuild. Then walk §2 items 1–12 and 21–23 and record each outcome in §2.

## 5. Risks accepted
- Deep links written by the server land on Trent's home page until ported (D7).
- Trent's tabs never get a stale-tab prompt (#5); Classic tabs do.
- `library_9002.py`: whichever version loses stays in history; the Run Scripts / Validation pickers show what lands.
- Any new file in Trent's `public/` needs a `main.py` reload to get its root route (dist is committed, so enumeration at import is deterministic).
- Playwright e2e stays broken at `goto('/')` until repointed; not in the gate, not run.

## 6. Follow-ups recorded, not in scope
- Port `?panel=` / `?script=` / `?run=` into Trent's router (D7); add an `/api/version` poll to his app (#5); his README gaps (#1–#4, #7–#9).
- Decide deletion of `restyle/` (D2) and, later, of `current/` once `/classic` is unused (mind #24).
- The T33241 head-to-head (the 2026-10-27 session's "next") is untouched by this plan.

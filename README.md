# Test-cases
=D
<p align="center">
  <img src="ask-ck/ck-facelift/ckc.jpg" alt="Ask CK" width="140" style="border-radius:50%;" />
</p>

<h3 align="center">Ask CK — Test Tooling Workbench</h3>

**Proprietary and Confidential — All Rights Reserved**

Copyright (c) 2026 terrenceb-atlnz. All rights reserved.

**No license is granted.** This repository and all contents (source code, data files, documentation, and tools) are the exclusive proprietary property of the copyright holder.

You may **not** copy, use, modify, distribute, sublicense, or create derivative works from any part of this work without prior express written permission.

Unauthorized access, use, or distribution is strictly prohibited.

---

Tools, data, and workflows for enriching and mapping **AWPTCM manual test cases** (Zephyr) using historical TestLink cases and enriched ATPyLib automated test suites — delivered through **Ask CK**, a server-backed multi-tool test-engineering workbench.

## Getting Started

**Quick start (recommended):** run the bootstrap script — it is the supported way to set up a new machine. On a fresh clone it does everything below in order and is safe to re-run:

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases
./setup.sh          # idempotent; safe to re-run
```

`setup.sh` runs a **preflight** before doing any work and, when run interactively, prompts before each fix (needs `sudo` for installs):

1. **Base toolchain** — verifies `git`, `git-lfs`, `curl` are present; offers to install any that are missing via your package manager (`apt`/`dnf`/`pacman`).
2. **Python ≥ 3.10** — required by the dependencies (`fastapi>=0.139` drops 3.9). It selects the newest suitable `python3.x` on `PATH`, or offers to install a newer one; if none can be found it stops early with clear guidance instead of failing deep inside `pip`.
3. **Git LFS ≥ 3.3** — installs/upgrades if needed (older LFS fails `git lfs pull` on a fresh clone), then pulls the large source files.
4. **Virtual environment + dependencies** — creates `.venv` with the **newest** available interpreter (recreating a stale one), installs the CPU PyTorch wheel then `requirements.txt`. It prefers **Python 3.13** to match the testbox — see *Python version: match the testbox* below.
5. **Database** — verifies `ask-ck/var/ck.db` (shipped via Git LFS — the permanent source of truth, not rebuilt).
6. Finally, **offers to launch the server** (delegates to `run.sh`, which asks foreground/background).

Useful flags: `./setup.sh --stop` stops a backgrounded server; any other arguments are forwarded to `run.sh` (e.g. `./setup.sh --port 9000`). Non-interactive runs (piped/CI) skip every prompt and never launch the server.

Run it non-interactively without any prompts:

```bash
./setup.sh < /dev/null   # fails fast if a prerequisite is missing; prints the exact install command
```

### `setup.sh` vs. `run.sh` — which do I need?

**Short answer: after the first successful `setup.sh`, you almost always just use `run.sh`.**

| Use `setup.sh` when… | Use `run.sh` when… |
|---|---|
| First-time setup on a new machine | Day-to-day: starting/stopping/restarting the server |
| First-time environment setup, or `ask-ck/var/ck.db` hasn't been materialized yet (it runs `git lfs pull` + a quick DB sanity-check — the DB itself is shipped, never rebuilt) | The DB is already present (it starts in seconds against the existing `ck.db`) |
| Toolchain/deps changed (Python, Git LFS, `requirements.txt`) | Nothing about the environment changed |

`setup.sh` is a superset — it does prerequisite checks + LFS pull + venv + **DB build**, *then* delegates to `run.sh` to launch. `run.sh` on its own does **none** of the setup; it only starts the server (auto-activating `.venv` if present). So a plain "bring the server back up" is `run.sh`, not `setup.sh`.

Both scripts live at the repo root:

```bash
./run.sh            # foreground (asks fg/bg first time)
./run.sh --bg       # background, no prompts (fast restart)
./run.sh --restart  # stop + background start
./run.sh --stop     # stop the background server
```

(Root `./run.sh` is a thin wrapper that forwards to the real launcher at `ask-ck/CK-main/run.sh`, which anchors its own paths — you can call either; the root one is just shorter.)

> The server runs with `--reload`, so **code edits hot-reload — no restart needed**. You generally only restart for env/dependency changes or to pick up a new `secrets.local.json`. (Template `.jinja` and static JS/CSS changes are also picked up on the next request / hard-reload; bump the `?v=N` on `main.js` when shipping JS so browsers refetch.)

<details>
<summary>Or do it manually</summary>

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases

# Required: materialize large source files
git lfs install
git lfs pull

# Recommended: isolate the Python dependencies in a virtual environment
# (use a Python >= 3.10 interpreter, e.g. python3.12 if your default python3 is older)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Required: install the Ask CK server dependencies
pip install -r ask-ck/CK-main/requirements.txt
```

</details>

### Python version: match the testbox

**Minimum 3.10; use 3.13 if you can.** The server runs fine on anything ≥ 3.10, but the
PyTest Creator lints every **generated** test script with `py_compile` using the venv's
interpreter — while those scripts actually execute under the **testbox's** `python3`
(tb470 is on **3.13.5**). When the two differ the lint checks the wrong language version:
it accepts imports the target has removed, and rejects syntax the target accepts.

That is not hypothetical. The script skeleton shipped `from distutils.util import
strtobool`, which is valid on 3.10, compiles clean on 3.10, and is a hard `ImportError` on
any 3.12+ target — so every generated script with a manual step would have died on import
before running a single test. `py_compile` cannot catch a missing module; only an import
can. The lint now also rejects stdlib modules removed in 3.12/3.13 (`distutils`, `imp`,
`telnetlib`, `cgi`, `pipes`, `crypt`, `asyncore`/`asynchat`/`smtpd`).

`setup.sh` picks the newest `python3.1x` on PATH. It **reuses** an existing venv that meets
the 3.10 floor rather than upgrading it, so if you install a newer Python later it will tell
you and print the upgrade steps. To upgrade by hand (with no server running):

```bash
python3.13 -m venv .venv313
PYTHONNOUSERSITE=1 .venv313/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch
PYTHONNOUSERSITE=1 .venv313/bin/pip install -r ask-ck/CK-main/requirements-dev.txt
PYTHONNOUSERSITE=1 .venv313/bin/pytest -q tests        # must be green BEFORE cutting over
mv .venv .venv-old && mv .venv313 .venv
# a venv is not relocatable: its console scripts hardcode the path they were built at
grep -rl '\.venv313' .venv/bin .venv/pyvenv.cfg | xargs sed -i 's|\.venv313|.venv|g'
./tool/run_tests.sh                                    # confirm, then rm -rf .venv-old
```

> `sentence-transformers` is **required** (it is in `requirements.txt`) — the semantic /
> hybrid search and the offline embedding model need it. A venv built by hand without a full
> `-r requirements.txt` install boots but silently degrades to keyword-only search. Verify
> with `PYTHONNOUSERSITE=1 .venv/bin/python -c "import sentence_transformers"` and check
> `/health` reports `sqlite_vec_loaded: true` with a non-zero `embeddings` count.

**Requirements:** **Python ≥ 3.10** + [Git LFS](https://git-lfs.com/) **≥ 3.3** + `curl` (used by the LFS installer) + the Python packages in [`ask-ck/CK-main/requirements.txt`](ask-ck/CK-main/requirements.txt) (FastAPI, uvicorn, Jinja2, requests, python-multipart, pydantic). Installing these is mandatory — the server will not start without them (you'll get `ModuleNotFoundError: No module named 'fastapi'`). On Debian/Ubuntu, `python3 -m venv` also needs the `python3-venv` package. `setup.sh` checks all of this for you; if you set up manually, note that installing `requirements.txt` on Python 3.9 or older fails with `No matching distribution found for fastapi`.

> **Git LFS version matters on Ubuntu.** Older Git LFS (e.g. 3.0.2, the version in Ubuntu's apt repos) is incompatible with modern Git (2.38+) and fails `git lfs pull` on a fresh clone with `cannot add to the index - missing --add option?`. If you hit this, install a current Git LFS from its own repo rather than apt:
> ```bash
> curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
> sudo apt-get install git-lfs      # now installs 3.3+
> git lfs install
> ```

> **On the virtual environment:** the `venv` is recommended but optional — it only isolates *where* these packages are installed, it does not change how the project runs. If you skip it, install into your user site-packages instead with `pip install --user -r ask-ck/CK-main/requirements.txt`. `run.sh` **auto-activates a repo-local `.venv` if present**, so you don't need to activate it first to start the server. You still need to activate it yourself (`source .venv/bin/activate`) before running `tool/*.py` scripts directly.

Large Zephyr sources (full XML export, `zephyr_cases.jsonl`, related indexes) live in the repo via Git LFS under `ask-ck/objective-drafting/data/zephyr_full/`. The original Zephyr XML export remains the immutable source of truth.

**Data layer:** all corpora and sessions live in a SQLite database, **`ask-ck/var/ck.db`**, which is the **permanent single source of truth** — built **once** from the provided data and **committed to the repo via Git LFS** (together with its ~84k semantic vectors and the bundled offline embedding model). A fresh clone gets a complete, populated, semantically-searchable database with **no build step**. It provides FTS5 keyword search + sqlite-vec semantic/hybrid search, including literal script-code chunks. **The running server reads corpora *only* from `ck.db` — zero runtime JSON** (strict DB-only), enforced by `tool/guard_db_only.py`; startup fails fast if `ck.db` is absent. The DB is **not rebuildable** — the intermediate source/courier files it was built from have been retired, and `tool/build_db.py` is kept only as provenance of how it was constructed (it refuses to run). The embedding model loads **fully offline** — the tool depends on nothing external but its own LLM endpoint. See [`ask-ck/ck-facelift/PLAN-db-only-search.md`](ask-ck/ck-facelift/PLAN-db-only-search.md).

## Project Goal

Manual cases (`AWPTCM-Txxxx` under New Platform Test (MASTER)) often lack clear **Objectives** (and sometimes preconditions). The project uses two other silos to define what those cases should verify and how they map to automation:

| Source | Role |
|--------|------|
| **TestLink (historical)** | Detailed human-authored cases (AWP-*) for artefact context and overlap |
| **ATPyLib (automated)** | Enriched suites describing what automation actually tests *for* |

Primary outcomes:

1. **Objectives** — declarative artefact lists (`<ul><li>…</li></ul>`) for each manual case  
2. **testScript steps** — Zephyr-ready verification steps (first step is usually a traceability note)  
3. **Traceability** — TestLink / Zephyr / ART mappings and gaps recorded per case  
4. **Many-to-one suite → case mappings** where automation is more granular than the manual case  

Authoritative process: **`ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`**.

## Current Status

| Area | Status |
|------|--------|
| ATPyLib suite enrichment | Largely complete (~116+ suites, ~10k tests) |
| Candidate generation + decisions | ~410 AWPTCM cases; decisions across review batches |
| Refined case outputs | **~42** cases with `traceability.md` + `zephyr_payload.json` under `ask-ck/objective-drafting/refined-cases/<Group>/` |
| Objective drafting process | Stable, documented, used in production workflow |
| **Ask CK workbench** | Multi-tool facelift complete (2026-07-13): Objective/Test Case Generator (full), sidebar LLM Configure panel, plus Test Composer and Zephyr Templating Tool (scaffolded) — see `ask-ck/objective-drafting/PROGRESS.md`. **Frontend refactored to browser-native ES modules (2026-07-16)** — `static/app.js` → `static/js/` (see `static/js/README.md`). |
| **Generator review UX** | **Two-table "chosen shortlist" (2026-07-16)** on the TestLink/Zephyr/ATPyLib steps (candidates ↑ / chosen ↓, insertion-ordered; confirm reads the chosen table only), plus **relevance-ranked keyword search** (title-weighted scoring; each new search re-ranks the whole candidate pool) |
| **Generator → Zephyr push** | **2026-07-22c:** "Push to Zephyr" button in the Generator's step-6 export actions (with a dry-run "Preview"). On the live Zephyr Scale (Server/DC) case it strips a leading `(N)` title group, ensures **version 2.0** (idempotent — bumps 1.0→2.0, never beyond), and uploads objective + steps + `traceability.md` + ART web-links. Shells out to `tool/upload_refined.py` (server never holds the JIRA token); attachments use replace-semantics (no dupes). All 43 Complete cases pushed + audited to v2.0. Loading a Complete case now rehydrates objective/steps from the on-disk bundle (`_backfill_from_refined`). |
| **PyTest Creator** | **Fully implemented:** 7-step gated flow (was 8; **Fit Decision removed 2026-07-23**) turning refined cases into runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test scripts, with a script-database index, testbox SSH execution, and an LLM fix loop to Final Validation — see `ask-ck/pytest-create/PLAN-pytest-creator.md`. **Standardized generation (2026-07-21):** Generate fills a fixed skeleton template (`templates/pt_script_template.py.jinja`) — one `TestCase` per verification step with a mandatory per-step logging contract, suite + per-case `tear_down`, data-driven topology; lint enforces template conformance. All reused script **source comes only from `ck.db`** (the retired mount is gone), and the testbox framework dir is **read-only** (guarded). **UX + correctness revision (2026-07-23):** Script Search + Fragments became per-step carousels (one step/screen, step-pill nav); Cases split into Open/Partial + Complete; the step sequence is classified **setup/verify/physical/manual** so **physical plug/unplug/hot-swap steps generate an operator-prompt + wait-for-state-change pattern** (SVT 3009) and manual checks generate a `yesNo()` — physical steps are in scope, not skipped. Also fixed: device-name reconciliation (bind the names fragments actually use), a **provenance mis-attribution bug** (setup-step renumbering stamped the wrong fragment on the wrong TestCase), fragment `maps_to` validation, and a positive **NO REUSE** gap marker. **Fragment-resolver hardening (2026-07-27):** the resolver now bounds every symbol by exact index `loc` — else next-unit-start−1, else `loc_total` — replacing a blind `loc[0]+60` fallback that over/under-captured ~18% of `test_case` entries (all legacy); helpers resolve by their real `loc` too. **Py2→Py3 fragments:** legacy Python-2 fragment code is deterministically modernized at resolve time via stdlib `lib2to3` (`status="translated"` guarantees valid Py3 — tab/space normalized + `ast`-verified; untranslatable code ships as-is with a ⚠ preview banner + a conditional Generate-prompt steer), and translated blocks carry a `(py2→py3)` provenance suffix. **CLI grounding (2026-07-27):** both the sequence-extraction and generate prompts are now grounded in the **real AlliedWare Plus command reference**, harvested from `docs.atlnz.lc` into `ck.db` (`cli_commands` / `cli_command_products`, 4,652 commands, 993 with sample output; re-runnable via `tool/harvest_cli_docs.py`, read via `tool/cli_lookup.py`). Root cause it fixes: the prompts demanded "exact CLI fields" while showing zero examples, so **every** model — Opus included — invented a `speed=1000`/`state=up` schema the switch never prints (real output is `current duplex full, current speed 1000, current polarity mdix`). Fabricated tokens went **13→0** in sequences and **57→0** in scripts. **Objective-coverage gate:** every Zephyr step must map to ≥1 sequence step, enforced on the **Confirm** button for *2. Sequence* and *5. Generate* with an error quoting each untested step (override: `acknowledge_coverage_gap`). **Objective in Generate (2026-07-29):** the refined objective is now baked into the generated script as a `# ==== OBJECTIVE ====` header AND carried into the Generate prompt (single source — it rides in via the embedded skeleton), so the model grounds each verdict in the declarative outcome instead of per-step action/verify text alone (generate-prompt rule 1a). A 5-model comparison (vllm-fast/thinking + claude haiku/sonnet/opus) judged by opus + vllm-fast (`tool/pt_matrix_judge.py`) confirmed the fix — T33233/T33235 now grade "good" — and isolated the next bottleneck as sequence-step **`kind` misclassification** (T33234 MDI/MDI-X: per-case reconfig collapsed into one-time setup, physical cable-swaps faked as CLI), captured in `ask-ck/ck-facelift/PLAN-permutation-expander.md`. See `ask-ck/pytest-create/{PLAN-pytest-testing,TEMPLATE-SPEC,LOGGING-CONTRACT}.md`. |
| **LLM: Local LLM + observability + provenance** | **2026-07-20:** third login mode **Local LLM** (org vLLM, OpenAI-compatible; Fast/Thinking toggle; server-stored key in gitignored `secrets.local.json`) — now the default radio, with a **Health check** button on the Configure page. Per-request **observability** (dev scaffolding): per-panel debug footer + `N in / M out` token badges + per-session log in `CK_server/debug-log/` (gitignored). **LLM Provenance** (permanent): every LLM panel can show/copy the exact prompt and **Refresh** it live via a no-send `dry_run` render (1-for-1 with a real send, zero tokens) — for pasting into a competing LLM. See `ask-ck/ck-facelift/PLAN-llm-observability.md`. **vLLM reasoning-model hardening (2026-07-21):** the OpenAI-compatible path now handles the org models' chain-of-thought — 16k `max_tokens`, null/truncated-`content` guards with clear errors, and the documented **system+user** message shape with a JSON-only steer (−35% tokens on real prompts). See `ask-ck/pytest-create/PART2A-WALKTHROUGH.md`. **Streaming transport (2026-07-22b):** the vLLM path now streams (`stream:true` + `stream_options.include_usage`), so the HTTP read timeout bounds the gap *between* chunks, not the whole response — the structural fix for `vllm-thinking` read-timing-out on the largest-output step (a 30s-read-timeout call ran 21+ min without timing out). Also: a session with a stale headless-CLI `llm_config` now **re-syncs to the active workspace default** instead of silently hitting the wrong backend. See `ask-ck/pytest-create/PLAN-pytest-testing.md` §8–§9. |
| **LLM: Claude agent tokens + model** | **2026-07-22d:** the per-user Claude agent (`claude_agent`) now **reports token usage + cost** — the ck-agent lifts `usage`/`total_cost_usd` from the `claude -p --output-format json` envelope and the browser forwards it through `/api/agent/result` (`deliver()` → `normalize_usage`), so the badge shows real `N in / M out` instead of "— tok" (a transport that reports nothing still shows "— tok" honestly). Added a **Haiku / Sonnet / Opus** model selector for that mode (radio row, live-persist, default Sonnet) that runs as `claude --model <name>` on your own seat. **Restart your ck-agent** to pick up token reporting. Also this session: the Generator's **Objective synthesis no longer makes the Traceability-gaps LLM call** — gaps belong to `traceability.md` and are generated at export time, so Step 4 is now a single self-contained call. |
| **Admin + fast restart** | **2026-07-20:** hidden **admin panel** (double-click CK's face) — reset sessions + restart server. (DB rebuild was removed once `ck.db` became the permanent, committed source of truth.) Fast restart via `run.sh --bg` / `--restart`. Localhost/single-user. |
| **Security posture** | **Hardened 2026-07-27 (full adversarial review):** server-side objective-HTML sanitizer (stored-XSS), `llm_config` secret redaction from all browser/disk serializations, `shlex`-quoted + metachar-validated SSH run command, extended framework-read-only guard (redirection/interpreter/`rsync`/`install`/`cp -t`), path-traversal guards on export `case_key` + generated filenames, session-bound agent-bridge, CORS lockdown. **Network defaults corrected 2026-07-27g:** binds `127.0.0.1` (LAN exposure is now an explicit `HOST=0.0.0.0`), `push_to_zephyr` no longer hardcodes `--force` (it was disabling the CLI's own "already refined — skip" guard on every push), and SSH host keys are pinned trust-on-first-use. Designed for **localhost/single-user** — there is still **no authentication**. Multi-user identity + per-case session locking is planned in [`ask-ck/ck-facelift/PLAN-auth-and-case-locking.md`](ask-ck/ck-facelift/PLAN-auth-and-case-locking.md); its Phase 1 also closes a concurrency bug that is live today (two tabs on one case silently overwrite each other). See SERVER-README → *Security Posture*; the review is closed and recorded in `ask-ck/pytest-create/ADVERSARIAL-REVIEW-BACKLOG.md`. |
| **Testing** | **Three-layer suite + one gate (2026-07-27).** **Backend:** `tests/` — **559** pytest in-process tests (no mocks/network/testbox) covering the validator, export gate, JSON extractor, framework guard, sanitizer, secret redaction, traversal guards, agent-bridge, CORS, `/process`, plus the 2026-07-27g batches (export authority, event-loop blocking, silent content loss, error signals, network hardening) — several **structural** (an AST sweep proving no async handler calls a blocking function unwrapped), so they catch the next regression rather than only the one filed. **Frontend units:** `js-tests/` — 85 Vitest + jsdom tests (no browser/server/LLM) covering the DOM/button-feedback helpers, table renderers, chosen-list machinery, and candidate-merge logic; DOM fixtures are lifted from the real `index.html` (drift-detecting). **E2E:** `e2e/` — one Playwright golden-path test driving the real app (boot → load → search → choose → export-gate), **run sparingly** via `npm run e2e` — NOT in the regular gate. **E2E and manual smoke checks run against a THROWAWAY ck.db copy on port 8123 (2026-07-28)** via `tool/run_scratch_server.sh`: `ck.db` going dirty is correct when a *person* operates the app (a case load persists a session row), but test traffic writing the permanent LFS-committed database is worthless data — the old `webServer: './run.sh --bg'` + `reuseExistingServer: true` attached to the real dev server on 8000 and did exactly that. `/health` now reports `db.db_path` + `db.is_permanent_db` so you can tell which database a server is on. **Prompt correctness (2026-07-28):** `tests/test_prompt_examples.py` EXECUTES the LLM prompts' own code examples against real harvested CLI output in `ck.db`, because where prose and an example disagree the model implements the example — several generated-script defects were traced to wrong examples in our own files, and these catch them pre-flight for zero tokens. `tests/_prose.py` keeps such checks from firing on their own advice text (it happened 4x). **Regular gate:** `./tool/run_tests.sh` runs guards + pytest + `npm test` (Vitest) in one command. Dev deps: `ask-ck/CK-main/requirements-dev.txt` (Python) + `package.json` (Node). No CI runner yet. |
| **Backend module split** | **2026-07-29: COMPLETE — all 11 commits done** (`PLAN-backend-module-split.md`; commit 6 dropped by decision). `routers/wizard.py` (was 2515 lines) is now the `routers/wizard/` **package** — four route modules (`reviews` / `config` / `synthesis` / `export`) plus `_shared.py` and `__init__.py`, function bodies moved byte-identical — with every shared concern already extracted to leaf modules at `CK_server/`: `llm_config.py` (the workspace LLM login), `case_registry.py` (which cases exist / are Complete / are hidden), `session_store.py` (the sessions dict + its ck.db row), and the `generator/` package (`descriptions.py`, `gates.py`, `backfill.py`) holding the Generator's logic with no FastAPI surface. **The coupling fix that motivated it:** `pytest_create.py` used to import **six underscore-private helpers out of `routers/wizard.py`**, so renaming any one silently broke a different tool — it now imports nothing from there, and its hand-copied `_apply_workspace_llm` (docstring: "Mirrors wizard…") collapsed into the shared one. `export()` decomposed from a 351-line handler into six named steps, verified byte-identical through the write path. Also from this effort: a failed session write now returns **500** instead of 200-with-work-lost (matching `pytest_create`), and case ids sort numerically. |
| **Data layer (SQLite `ck.db`)** | **Migration complete (2026-07-16), committed A–D:** corpora + sessions served from `ask-ck/var/ck.db` (FTS5 keyword + sqlite-vec hybrid/semantic). See `ask-ck/ck-facelift/PLAN-db-migration.md`. |
| **Strict DB-only search** | **2026-07-20:** literal script-code + all semantic vectors ingested (~84k embeddings incl. code chunks); embedding model bundled + loads offline. Runtime is now strictly DB-only — server reads **zero** corpus JSON, enforced by `tool/guard_db_only.py`, startup fails fast without `ck.db`. Fixed 3 latent bugs (embed guard never ran; sqlite-vec KNN silently returned nothing; huggingface load-time ping). See `ask-ck/ck-facelift/PLAN-db-only-search.md`. |

**Refined-case groups present** (examples): Port, IPv4, Switching, QoS, Sanity Check, Authentication & Security, Management, Bootloader.

**Session history / working notes:** `SESSION_STATE.md` (long-form). Prefer `ask-ck/objective-drafting/PROGRESS.md` when continuing Ask CK work.

## Ask CK Workbench

Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. This same welcome + per-tool guide is the **Main** splash page inside the app (sidebar → **Help → Main**).

```bash
# One-time: install the server dependencies (see Getting Started, or run ./setup.sh)
pip install -r ask-ck/CK-main/requirements.txt

./ask-ck/CK-main/run.sh        # auto-uses .venv; asks foreground or background
# then open http://localhost:8000/   (opens on the Main splash page)

./ask-ck/CK-main/run.sh --stop # stop a backgrounded server
```

`run.sh` automatically uses the repo-local `.venv` (if present) and, when run interactively, asks whether to run in the **foreground** (Ctrl-C to stop) or the **background**. Background mode prints the PID + log path and is stopped with `./ask-ck/CK-main/run.sh --stop` (or `./setup.sh --stop`). Background logs append to `.ck-server.log`.

> **Use `http://`, not `https://`.** Ask CK serves plain HTTP. If your browser forces HTTPS (Firefox HTTPS-Only mode, HSTS) you'll get a blank "Secure Connection Failed" / `SSL_ERROR_RX_RECORD_TOO_LONG` page. Browse to `http://localhost:8000/` explicitly and, if needed, exempt localhost from HTTPS-Only mode. (The server now binds `127.0.0.1` by default; if you start it with `HOST=0.0.0.0` the banner prints that bind address — still browse via `localhost`.)

- FastAPI backend (`ask-ck/CK-main/CK_server/`) + multi-tool sidebar UI; **server-side confirm gates** at every step.
- LLM via the sidebar **LLM → Configure** panel: **Local LLM** (organization vLLM, default — Fast/Thinking toggle, server-stored key, **Health check** button), **Claude Code CLI** (per-user local agent — **Haiku/Sonnet/Opus** model selector; reports token usage + cost), or **Grok CLI**. The workspace login persists across cases. Set this up first — most tools need it. (MOCK/demo paths removed — real login required.) Every LLM request is logged for observability (per-panel debug footer + `N in / M out` token badges; per-session log in `CK_server/debug-log/`), and every LLM panel exposes an **LLM Provenance** block that can copy the exact prompt or **Refresh** it live without sending (dry-run) for use in a competing LLM.

The tool guides below are in **inverse order of the sidebar list** (i.e. oldest/most-complete first), matching the Main splash page.

### Objective / Test Case Generator

The original Ask CK tool. Turns a sparse AWPTCM manual case into a refined case with declarative objectives, Zephyr-ready test steps, and traceability — with a review gate at every step. Authoritative process: `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`.

1. **Cases** — pick a case from the Open/partial or Complete dropdown and Load it.
2. **TestLink** — review the primary decision and candidate historical cases; Search or Suggest with the LLM, then Confirm your selections.
3. **Zephyr** — review related external Zephyr cross-references (not the managed Cases list); Confirm.
4. **ATPyLib (scored)** — review the scored automation-coverage candidates and Confirm which ART suites apply.
5. **Objectives (LLM)** — synthesize the declarative objective artefacts from the confirmed reviews; edit, then Confirm.
6. **Test Steps (LLM)** — synthesize the Zephyr test steps from the finalized objective, then **Export the Repeatable Bundle** — this writes `traceability.md` + `zephyr_payload.json` into `ask-ck/objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/`. A case becomes **Complete** once this exists.
7. **Push to Zephyr** (in the same step-6 export actions) — pushes the exported bundle to the live Zephyr case: **Preview Push (dry-run)** shows exactly what will change with no writes; **Push to Zephyr** then, on the case, strips a leading `(N)` title group, ensures the case is at **version 2.0** (bumps 1.0→2.0; never beyond), and uploads the objective + steps + `traceability.md` + ART web-links onto it. It operates on the **last exported bundle on disk** (Export first if you've edited), and shells out to `tool/upload_refined.py` — the server never handles the JIRA token.

**Review steps 2–4 use a two-table "chosen shortlist" (2026-07-16):** the top **candidates** table holds Search / Suggest results (keyword Search is relevance-ranked — title matches outrank body-only hits, and each new search re-ranks the whole pool against the new terms); tick rows and click **↓ Choose selected** to move them into the bottom **chosen** table, which stays in the order you added them. **Clear selected contents** moves chosen rows back up. **Mark Reviewed + Confirmed reads only the chosen table.** LLM **Suggest** drops its picks straight into the chosen table. Loading a previously-confirmed case pre-populates the chosen tables.

Gaps for Traceability are synthesized by the LLM at the synthesize/export step (not user-edited mid-wizard). Optional final step: push a refined case to Zephyr with `tool/upload_refined.py` (see below).

### PyTest Creator

Turns a **Complete** case (one exported by the Generator above) into a runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test script, then runs it on real hardware and iterates until it passes. Each step has a Confirm gate.

1. **Cases** — pick a case from the **Open/Partial** or **Complete** dropdown (split by PyTest work state; partials sort to the top) and Load it (use **↻ Refresh list** after exporting new cases in the Generator).
2. **Sequence** — the LLM extracts a prescriptive sequence of automatable steps from the refined case and classifies each as **setup / verify / physical / manual**; drag to reorder, edit the rows, Save, then Confirm.
3. **Script Search** — a per-step carousel (one sequence step per screen, Prev/Next + a step-pill row): for each step, search the script database for scripts that cover it and Choose what to reuse into that step's Chosen table, then Confirm.
4. **Fragments** — per-step, no cap: the LLM proposes reusable symbols per step, resolved to real source by line range (invented symbols and phantom step-mappings dropped); chosen/redundant accounting shows duplicates nested under the fragment they duplicate. An assembled-artefact preview slots the selected fragments per step; a verify step with no fragment gets a **NO REUSE** marker. Untick what you don't want, then Confirm. *(The former **Fit Decision** step was removed — the fixed skeleton made it moot.)*
5. **Generate** — the LLM **fills a standardized skeleton template** (fixed frame: header, `TestSet` with data-driven `init`/`configure`/`tear_down`, one `TestCase` per verification step with the logging contract + per-case `tear_down`, `__main__` footer). Step kind drives the body: **physical** steps prompt the operator then poll for the port state change (SVT 3009 pattern), **manual** steps ask a `yesNo()`, **verify** steps drive the CLI. Provenance is re-stamped authoritatively server-side (correct even when setup steps shift the TestCase numbering). Edit the Group/name, Lint (checks template + logging-contract conformance, rejects leftover placeholders), Save to `ask-ck/pytest-create/generated/<Group>/<Name>.py`, then Confirm.
6. **Run** — pick a stored testbox (or add one under **Testboxes**), choose the `.setup`, and run it over SSH; results are parsed into per-TestCase PASS/FAIL.
7. **Validate** — Final Validation passes when every TestCase is PASS with zero failures. On failures, **Fix with LLM** loops back to Generate; promotion into `testsuites_art/` is manual.

Add a testbox under the **Testboxes** sidebar item. No index build is needed.

> ⚠ **Historical — the script-index build is no longer a setup step.** The script index, literal
> source code, code chunks and framework surface all live in **`ask-ck/var/ck.db`** (the permanent
> single source of truth, shipped via Git LFS), and the PyTest Creator reads only the DB via
> `db.py`. The scripts below remain in `tool/` as **provenance of how the index was built**; their
> JSON outputs have been deleted and running them is not part of setting up or using the tool.
> See `ask-ck/pytest-create/PLAN-pytest-creator.md` (data-layer note).
>
> ```bash
> cd tool
> ./build_script_index.py --mechanical-only    # historical: AST scan of the 3 script DBs
> ./enrich_script_index.py --limit 100         # historical: resumable LLM tagging
> ./build_script_index.py                      # historical: merge enrichment
> ```

Stored testboxes live in the gitignored `secrets.testboxes.json` (passwords write-only; passwordless sudo on the box required).

### Test Composer

**TBD — scaffolded, not yet implemented.**

### Zephyr Templating Tool

**TBD — scaffolded, not yet implemented.**

### Documentation map

| Doc | Use for |
|-----|---------|
| [`ask-ck/objective-drafting/PROGRESS.md`](ask-ck/objective-drafting/PROGRESS.md) | **Start here** — status, backlog, handoff |
| [`ask-ck/CK-main/SERVER-README.md`](ask-ck/CK-main/SERVER-README.md) | Run, architecture, LLM modes, PyTest Creator, nginx |
| [`ask-ck/pytest-create/PLAN-pytest-creator.md`](ask-ck/pytest-create/PLAN-pytest-creator.md) | **PyTest Creator** plan + progress tracker |
| [`ask-ck/pytest-create/SETUP-FILE-REFERENCE.md`](ask-ck/pytest-create/SETUP-FILE-REFERENCE.md) | `.setup` topology schema + a real worked example (stack membership, stackports, testbox cabling) |
| [`ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`](ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md) | Generator process source of truth |
| [`ask-ck/objective-drafting/PLAN-server-backed.md`](ask-ck/objective-drafting/PLAN-server-backed.md) | Approved design rationale (historical paths) |
| [`ask-ck/objective-drafting/LESSONS_LEARNED.md`](ask-ck/objective-drafting/LESSONS_LEARNED.md) | Prior decisions and pitfalls |
| [`ask-ck/ck-facelift/PLAN-facelift.md`](ask-ck/ck-facelift/PLAN-facelift.md) | 2026-07-13 multi-tool facelift plan (as executed) |

**Session workflow:** run **`/orient`** at the start of a working session and **`/wrap`** at the
end — project skills in [`.claude/skills/`](.claude/skills/). `/orient` ground-truths the live
repo (git, guards, gate), reads the newest handoff entry, and confirms the invariants before any
work begins; `/wrap` reconciles the docs above against what actually shipped, sweeps for stale
claims, and commits. Both are plain Markdown with no tool-specific syntax — paste a `SKILL.md`
body into any other assistant if you are not using Claude Code.

### Upload refined cases to Zephyr

```bash
JIRA_KEY=... python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235
JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --verify
JIRA_KEY=... python3 tool/upload_refined.py --execute --groups "Port (7)" "IPv4 (44)"
# Full push as done by the Generator's "Push to Zephyr" button (title cleanup + v2.0):
JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --fix-title --new-version --force --verify
```

`--fix-title` strips a leading `(N)`/`(…)` group from the case Name; `--new-version`
ensures the case is at **version 2.0** (bumps 1.0→2.0, idempotent — never 3.0+), applied
**before** the payload so objective/steps land on v2.0. Attachments use replace-semantics
(no duplicate `traceability.md` on re-runs); web-links are parsed from the ATPyLib Cases
section (backticked or prose IDs) and de-duplicated. Always dry-run first. Auth matches the extract tools (JIRA_KEY + Bearer). Details: `tool/upload_refined.py --help` and Step 4 in `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`. (If the script has not yet been repathed for the 2026-07-13 restructure, run it with paths pointed at `ask-ck/objective-drafting/refined-cases/`.)

## Repository Layout

```
Test-cases/
├── SESSION_STATE.md                # Broader session history
├── ask-ck/                         # Ask CK workbench (all tool code, data, docs)
│   ├── CK-main/                    # App: run.sh, requirements.txt, SERVER-README.md, design assets
│   │   └── CK_server/              # FastAPI server (main.py, paths.py, routers/, static/, templates/, sessions/)
│   ├── objective-drafting/         # Generator data + docs + outputs
│   │   ├── OBJECTIVE_DRAFTING_PROCESS.md   # Process source of truth
│   │   ├── PROGRESS.md             # Primary handoff document
│   │   ├── data/                   # zephyr_master, candidates, decisions, suites, zephyr_full (LFS)
│   │   └── refined-cases/          # Per-case outputs (drop-in for upload)
│   │       └── <Group>/AWPTCM-Txxxx/{traceability.md, zephyr_payload.json}
│   ├── ck-facelift/                # Facelift plan (2026-07-13)
│   ├── pytest-create/              # PyTest Creator: PLAN-pytest-creator.md, data/ (index), generated/<Group>/<Name>.py
│   ├── test-composer/              # (future) Test Composer assets
│   └── zephyr-tool/                # (future) Zephyr Templating Tool assets
└── tool/                           # Extract, candidates, review, upload + build_script_index.py / enrich_script_index.py
```

### Key data & tools

**The runtime data all lives in `ask-ck/var/ck.db`** (the permanent LFS-committed single
source of truth — see **Data layer** above). The former on-disk courier corpora
(`zephyr_master.json`, `candidates.json`, `data/decisions/`, `test_id_description.*`,
`suite_*_enriched.json`, `zephyr_api_updates.json`, the script index/sidecars) were
**retired into `ck.db` and deleted (2026-07-20)** — do not look for them on disk.

What still exists under `ask-ck/objective-drafting/`:

- **`data/zephyr_full/`** — the full Zephyr XML export (LFS) — the immutable provenance root `ck.db` was built from.  
- **`data/suites/`** — enrichment *docs* only now (`ENRICHMENT_STATE.md`, `suite_index.md`, spec); the enriched-suite JSON corpora are in `ck.db`.  
- **`data/review/`** — review HTML/scratch.  
- **`refined-cases/<Group>/AWPTCM-Txxxx/`** — per-case exports (`traceability.md` + `zephyr_payload.json`); a case is **Complete** once this exists.  
- **`tool/`** — extraction, candidate build, review HTML, `upload_refined.py`, etc. (`build_db.py` is provenance-only and refuses to run).  

## Related Documentation

| File | Description |
|------|-------------|
| [ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md](ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md) | Repeatable drafting process + output shapes |
| [SESSION_STATE.md](SESSION_STATE.md) | Chronological work history |
| [resources.md](resources.md) | Links to TestLink, Zephyr, ART |
| [ask-ck/objective-drafting/ENRICHMENT_QUALITY_ANALYSIS.md](ask-ck/objective-drafting/ENRICHMENT_QUALITY_ANALYSIS.md) | Enrichment quality / schema |
| [ask-ck/objective-drafting/VALIDATION_RESULTS.md](ask-ck/objective-drafting/VALIDATION_RESULTS.md) | Suite validation vs ART |
| [ask-ck/objective-drafting/data/suites/ENRICHMENT_STATE.md](ask-ck/objective-drafting/data/suites/ENRICHMENT_STATE.md) | Enrichment phase resume notes |
| [ask-ck/objective-drafting/data/suites/_enrichment_agent_spec.md](ask-ck/objective-drafting/data/suites/_enrichment_agent_spec.md) | Log-enrichment agent spec |
| External [AGENTS.md](../AGENTS.md) | Environment, access patterns, CLI install (if present) |

`secrets.md` (API keys) is local/gitignored where configured — do not commit credentials.

> **Note:** Primary development is on an internal machine; this GitHub tree is a published copy. Some internal paths may appear in older notes. On 2026-07-13 the repo was restructured: `drafting-tool/` → `ask-ck/CK-main/` (+ `CK_server/`), and root `data/`, `refined-cases/`, and process docs → `ask-ck/objective-drafting/`. Historical docs (SESSION_STATE entries, PLAN-server-backed.md, old traceability artefacts) may still reference the pre-move paths.

## Copyright

See the notice at the top of this file and the `COPYRIGHT` file in the repository root.

All rights reserved. No permissions are granted to use, copy, or distribute this work.

---

## Setup & Maintenance Fix Log — 2026-07-15

This section records the setup/install fixes made on 2026-07-15 while walking the
Getting Started flow on a fresh Ubuntu machine, and *why* each was needed.

| # | Fix | Why it was needed |
|---|-----|-------------------|
| 1 | **Added `ask-ck/CK-main/requirements.txt`** and documented it as a mandatory install step. | The server crashed on startup with `ModuleNotFoundError: No module named 'fastapi'`. The app's Python dependencies (FastAPI, Jinja2, requests, …) were never listed anywhere, so a fresh clone had no way to know what to install. `uvicorn` starting but then failing to import the app was the confusing symptom. |
| 2 | **Added a virtual-environment step** (`python3 -m venv .venv` + activate) to Getting Started. | Isolates the dependencies from the user's global/site packages so versions can't collide with other projects. Optional but recommended — it does not change how the project runs, only *where* the packages live. |
| 3 | **Documented Git LFS ≥ 3.3** and how to install it from the git-lfs repo instead of apt. | On Ubuntu, apt ships Git LFS 3.0.2, which is incompatible with modern Git (2.38+). A fresh `git lfs pull` fails with `cannot add to the index - missing --add option?`. It only "worked" on the dev machine because the large files were already materialized, so the smudge step never ran. |
| 4 | **Documented HTTP-only access** (`http://`, not `https://`) and the `0.0.0.0` bind-address gotcha. | Browsers with HTTPS-Only mode (e.g. Firefox) auto-upgrade to `https://`, and the plain-HTTP server can't answer a TLS handshake — producing a blank `SSL_ERROR_RX_RECORD_TOO_LONG` page and a `WARNING: Invalid HTTP request` in the server log. A same-port https→http redirect is not possible (the failure is at the TLS layer, before any HTTP is exchanged). |
| 5 | **Added `setup.sh`** — an idempotent one-shot bootstrap (git-lfs check → LFS pull → venv → deps → offer to launch). | `run.sh` assumes everything is already set up and gives cryptic errors otherwise. `setup.sh` performs the full first-time setup in order and can be safely re-run. It also **detects a missing or too-old git-lfs (< 3.3) and offers to install/upgrade it** (via the packagecloud apt repo, with `sudo`, after asking) so fix #3 is handled automatically rather than left to the reader. To start the server it **delegates to `run.sh`** (which asks foreground/background — see #8); `./setup.sh --stop` also delegates to `run.sh --stop`. |
| 5a | **git-lfs upgrade installs an explicit version.** | On this machine the Ubuntu **ESM** repo pins git-lfs 3.0.2 at a *higher* apt priority (510) than packagecloud (500), so a plain `apt-get install git-lfs` kept the old version. `setup.sh` now installs the newest available version explicitly (`git-lfs=<latest>`) to bypass the pin. |
| 6 | **Corrected stale Git LFS paths in `.gitattributes`.** | After the 2026-07-13 restructure, `data/` moved under `ask-ck/objective-drafting/`, but the LFS rules still pointed at the old `data/zephyr_full/…` paths and so matched nothing. `zephyr_cases.jsonl` (53 MB), `index.json` (17 MB), and `suites/testlink_awp.json` (28 MB) were therefore committed as plain Git blobs instead of LFS objects. Rules were repathed to the real locations; the `Zephyr-Database-*.xml` rule was unaffected because it is a path-independent filename glob. |
| 7 | **Renormalized the three files into LFS** (`git add --renormalize`). | With the rules corrected, the already-committed plain blobs were re-run through the LFS filter so their tracked representation becomes ~130-byte LFS pointers instead of full content. This makes fix #6 actually take effect on the existing files (not just future edits). Working-tree contents are unchanged; this does **not** rewrite history, so old blobs remain in past commits. |
| 8 | **`run.sh` now auto-activates the venv and offers foreground/background, with `--stop`.** | Previously you had to `source .venv/bin/activate` before `run.sh`, and it only ran in the foreground (Ctrl-C). Now `run.sh` auto-uses the repo-local `.venv` if present; when interactive it asks **[F]oreground / [b]ackground**; background mode detaches the process (own session/process group), records the PID in `.ck-server.pid`, appends to `.ck-server.log`, and is stopped cleanly with `./ask-ck/CK-main/run.sh --stop`. Non-interactive/CI runs default to foreground with no prompt. The background/stop mechanics live only in `run.sh`; `setup.sh` delegates to it (see #5). |

> **Note on fixes #6–#7:** the renormalize was **staged locally, not committed or pushed** — commit it when ready. It does not rewrite history (old blobs stay in past commits; use `git lfs migrate import` + a force-push for that, which is best avoided on a published repo). After this lands, fresh clones must `git lfs pull` (or run `setup.sh`) to materialize these files — the same as the XML already requires. None of these files exceed GitHub's 100 MB limit today, so this is preventative, not urgent.

## Repo Hygiene — 2026-07-16

A narrow scrub of vestigial files. Removed the stray root `zephyr-auto_negotiation.xml` (an unreferenced single-suite export left over from the 2026-07-13 restructure) and the completed-phase enrichment scratch files (`data/suites/_gather_suite.py`, `_remaining_suites.txt`, `_todo_suites.json`), plus some gitignored debug-log test scratch.

> **What was deliberately kept** (looks redundant now that `ck.db` exists, but is not): the `data/suites/suite_*_enriched.json` corpora and the other `data/` JSON/JSONL remain the rebuildable **build input** for `ck.db` — `build_db.py` still consumes them (the *runtime* server, by contrast, reads only `ck.db` as of the 2026-07-20 strict DB-only Phase 1; see `ask-ck/ck-facelift/PLAN-db-only-search.md`). `CK_server/sessions/*.json` are intentional frozen pre-migration backups. These build inputs retire only in the later phases of the DB-only plan, not in an ad-hoc scrub.
>
> **Superseded (2026-07-20b):** those build-input couriers ARE now retired — `ck.db` became the permanent, committed source of truth, so the courier/intermediate files (incl. `suite_*_enriched.json`, `all_test_suites.json`, `zephyr_cases.jsonl`, the script index/sidecar) were deleted and the rebuild paths removed. Only the raw Zephyr XML original is kept as a provenance root. See the "Permanent DB / single source of truth" entry below.

# SERVER-README.md — Ask CK (Server-Backed Test Tooling Workbench)

This document contains **all instructions for use, setup, configuration, architecture, and details** for **Ask CK** — the server-backed workbench whose first (and mature) tool is the **Objective/Test Case Generator** (formerly "Objective Drafting Tool").

> **Want the shape rather than the detail?** [`ask-ck/ARCHITECTURE.md`](../ARCHITECTURE.md) is a
> one-page executive summary — the stack and languages, the four tools and their real state, the
> data layer, the four invariants, and where the risk actually sits. Read it first; this file is
> the deep reference behind it.

> **Layout note (2026-07-13):** the repo was restructured. Server code: `ask-ck/CK-main/CK_server/` (was `drafting-tool/drafting_server/`). Generator data, process docs, and `refined-cases/`: `ask-ck/objective-drafting/`. Filesystem anchors live in `CK_server/paths.py`. Historical session summaries at the bottom of this file keep their original (pre-move) paths.

## Overview and Goals

The server-backed workbench fulfills the two main functions:

1. **Present the OBJECTIVE_DRAFTING_PROCESS as a web-based page**  
   Interactive reference with deep links into the wizard steps, principles, checklist, and examples.

2. **Standardize the output of the process in a repeatable process**  
   - Enforced step-by-step workflow (user review at the forefront).  
   - Objectives and testScript Steps are created **last**, only after the user has reviewed and confirmed the three databases.  
   - Repeatable outputs are achieved via **prompt templating + structured parsing** of LLM responses.

**Key priorities (from approved plan):**
- Repeatable *process* (strict step-by-step with confirmation gates).
- Repeatable *outputs* (templated LLM prompts + post-processing for consistent `<ul>` objectives and steps).
- LLM integration is **necessary** for synthesis.
- Server-hosted (local IP, typically behind nginx).
- Never offline.
- Data will only grow — server handles indexing and loading.
- Future extensibility is expected — Ask CK now hosts multiple tools in one sidebar.

This version replaces the original single-file static `index.html` approach.

**Project state reference**: ~42 cases already processed using the overall workflow. The server version uses the same data sources and output formats (`ask-ck/objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/{traceability.md, zephyr_payload.json}`).

## Architecture

**Backend**: FastAPI (Python) — `CK_server/`
- Persistent process (run with uvicorn).
- Loads and manages all data on the server side (paths anchored in `CK_server/paths.py`).
- Enforces the repeatable process state machine.
- Direct LLM calls using templated prompts.
- Post-processing of LLM output using templates/parsers for guaranteed repeatable structure.
- REST API consumed by the frontend: `/api/wizard` (Generator) + stub routers `/api/zephyr-tool`, `/api/test-composer`, `/api/pytest-create`.
- Serves the process documentation as interactive web pages.

**Frontend**: Static web UI (vanilla JS + HTML, served by the backend) — `CK_server/static/index.html`
- **Ask CK multi-tool sidebar** (always-expanded sections, top→bottom):
  - **LLM** — live status + **Configure** entry (opens the LLM Provider Login as a main-area panel)
  - **Zephyr Templating Tool** — 1. Info / 2. Test Plan / Cycle / Cases / 3. Link Test Scripts / 4. TBD (placeholder panels)
  - **Test Composer** — 1. TBD (placeholder panel)
  - **PyTest Creator** — full 7-step flow (2026-07-23): **1. Cases** (Open/Partial + Complete dropdowns, split by PyTest work state; partials auto-sorted to top; independent of the Generator) / **2. Sequence** / **3. Script Search** / **4. Fragments** / **5. Generate** / **6. Run** / **7. Validate**. (Former **4. Fit Decision** removed; internal `stepN` keys unchanged.) See the detailed **PyTest Creator** section below.
  - **Objective/Test Case Generator** — **1. Cases**, **2. TestLink**, **3. Zephyr**, **4. ATPyLib (scored)**, **5. Objectives (LLM)**, **6. Test Steps (LLM)**
- Navigation: `goToPanel(panelId)` shows exactly one `.tool-panel` card; `goToStep()` wraps it for the Generator. **Visible step numbers (1–6) are display-only** — the internal scheme (`data-step` 0–5, panel ids `step-0..5`, session keys `step1..step5`, `confirm_step` domain ids 1–3) is unchanged and load-bearing.
- Generator Cases panel: dual dropdowns — **Open / partial** (in-progress first) vs **Complete** (has `refined-cases/.../zephyr_payload.json`). Review steps 2–4 each have Search + Suggest with LLM toolbars.
- Tables use explicit column classes (`cols-5`, `cols-6-zephyr`, `cols-6-atp`) for compact layout.
- Multi-step with gates; synthesize only after confirms; human-readable objective/steps + editors; post-synthesis teal **Export Repeatable Bundle** button.
- Process Reference at `/process` (basic). Favicon at `/favicon.ico` / `/favicon.svg`.

**LLM Layer** (core of repeatability):
- Prompt templates in `CK_server/templates/prompts/` including `generate_objectives.jinja`, `generate_steps.jinja`, **`generate_gaps.jinja`**, `suggest_*.jinja`, `analyze_atp_coverage.jinja` (rank only).
- **Gaps analysis is LLM-generated at synthesize/export** for Traceability — not an editable review-step field.
- UI login modes (radios, top→bottom): **Local LLM** (`local_llm`, default — the org vLLM, see below), **Claude Code CLI** (`claude_agent`, per-user local agent), **Grok CLI** (`grok_cli`). Legacy `api_key`/`claude_code` server-side only. See the **Local LLM** and **LLM request observability** subsections under *Running the Server*.
- **Workspace LLM default**: Apply/Login (sidebar **LLM → Configure**) persists the workspace default to the sessions table (`id='_workspace_llm'`, migrated off `sessions/_workspace_llm.json` in the 2026-07-16 DB migration); load_case applies it to cases without an active config so switching cases does not reset login. **No case is required** — keyless `POST /api/wizard/set_llm_config` saves the workspace default; when a case is selected, the config is also stored on that case's session. `GET /api/wizard/llm_config` returns the persisted default (no secrets) so a cold page load shows the real status instead of "No credential". **The active workspace default is authoritative (2026-07-22b):** a case session re-syncs to it whenever the session's config is inactive **or** diverges from it on the backend-selecting fields (`_same_backend`: auth_method/provider/model). This fixes the bug where a session with a *stale* headless-CLI config (`claude_agent`/`claude_code`/`grok_cli` — which `_llm_is_active` reports active unconditionally, since there is no server-side key to check) could never re-sync and kept silently hitting the wrong backend. It is safe because `set_llm_config` is the only writer of a case's config and always writes it identical to the workspace default (no legitimate per-case divergence exists); when the workspace default is inactive/absent the re-sync is a no-op, so the login still persists. Applies to both the Generator (`wizard._apply_workspace_llm_if_needed`) and PyTest Creator (`pytest_create._apply_workspace_llm`).
- Full provenance (prompts/responses/provider/auth) captured per session, plus a per-request debug log — see **LLM request observability**.

**Data** (SQLite `ck.db` — the permanent single source of truth):
- All corpora + sessions live in **`ask-ck/var/ck.db`**, **committed to the repo via Git LFS**
  (with its ~84k vectors + the bundled offline embedding model). Built **once** from the provided
  data; **NOT rebuildable** — a fresh clone gets the populated DB with no build step. `db.py` is
  the single access layer:
  - Zephyr (45k XML cases + 410 API targets), TestLink historical, enriched ATPyLib, the script index
  - FTS5 keyword search (`db.search_*`) + sqlite-vec **hybrid/semantic** (`mode=keyword|hybrid|semantic`; degrades to keyword if the extension can't load)
  - Sessions (per-case + workspace LLM) with `llm_config` isolated in its own column
  - Literal script **source code** + code chunks (`script_chunks` / `chunks_fts`) — `db.search_code` / `search_code_hybrid`
  - ~84k semantic vectors across all corpora incl. code chunks; embedding model bundled under
    `ask-ck/var/models/`, loads **fully offline** (`HF_HUB_OFFLINE`) — no external dependency
- **Strict DB-only runtime:** the server reads corpora **only** from `ck.db` — **zero runtime
  JSON**. `data.py` sources every reference (zephyr_master, candidates, decisions,
  framework_surface, scripts_index_meta) from `db.*` getters; startup **fails fast** if `ck.db`
  is missing. Enforced by **`tool/guard_db_only.py`**.
- **No rebuild / no source docs.** The intermediate courier/source files the DB was built from
  (`zephyr_cases.jsonl`, `testlink_awp.json`, `test_id_description.*`, `candidates.json`,
  `decisions/*`, the enriched-suite corpus, `scripts_index*.json` / `scripts_sources.jsonl`,
  `framework_surface.json`) have been **deleted** — the DB is the only copy. `tool/build_db.py`
  remains only as provenance of how the DB was constructed and **refuses to run** (it would
  delete the committed DB and cannot repopulate it). The one raw original kept is the Zephyr XML
  export, as an immutable provenance root. There are no corpus APIs and no re-fetch — the corpus
  data is a fixed snapshot. See **`ask-ck/ck-facelift/PLAN-db-only-search.md`**.

**Hosting**:
- Intended to run behind nginx on a local IP.
- Never offline.
- Example nginx config provided.

**Repeatability Guarantees**:
- Process: Backend state machine enforces explicit user confirmation of TestLink/Zephyr/ATPyLib **selections** before synthesis. Gates are server-side.
- LLM: Templated prompts + structured parsing + provenance; gaps for Traceability authored at completion (not mid-wizard free text).
- Outputs: Fixed Jinja + post-processing; export auto-persists to `objective-drafting/refined-cases/<Group>/`.
- UI: Dual case lists, Search/Suggest on the review steps, CLI login radios, design-system components.

## Directory Structure

```
ask-ck/
├── CK-main/
│   ├── SERVER-README.md             ← This file (all instructions)
│   ├── run.sh                       ← Start script (PYTHONPATH=CK-main, CK_server.main:app)
│   ├── nginx-drafting-server.conf.example
│   ├── (design assets + legacy single-file index.html, reference only)
│   └── CK_server/                   ← The actual server application
│       ├── main.py                  ← FastAPI entry point ("Ask CK"); includes all routers
│       ├── paths.py                 ← Filesystem anchors (DATA_DIR / REFINED_DIR / PROCESS_MD)
│       ├── data.py                  ← Data loading (three DBs + indices)
│       ├── llm.py                   ← Prompt templating + LLM call + parser
│       ├── models.py                ← Pydantic models
│       ├── llm_config.py            ← workspace LLM login: active? same backend? apply  (shared)
│       ├── case_registry.py         ← which cases exist / are Complete / are hidden      (shared)
│       ├── session_store.py         ← the `sessions` dict + its ck.db row                (shared)
│       ├── generator/               ← the Generator's LOGIC, no FastAPI surface
│       │   ├── descriptions.py      ← review-table text shaping + ATP retrieval
│       │   ├── gates.py             ← the step state machine (can_synthesize, invalidation)
│       │   └── backfill.py          ← rehydrate a session from its Complete on-disk bundle
│       ├── routers/
│       │   ├── wizard/              ← Generator API (/api/wizard) — endpoints, split by concern
│       │   │   ├── __init__.py      ← mounts the four sub-routers; re-exports the public surface
│       │   │   ├── _shared.py       ← get_data dependency + export template env (no routes)
│       │   │   ├── reviews.py       ← step 1/2/3 gates, search/suggest, confirm_step
│       │   │   ├── config.py        ← session clear, CLI status, LLM config, health
│       │   │   ├── synthesis.py     ← objectives + steps
│       │   │   └── export.py        ← drop-in refined-cases bundle + push_to_zephyr
│       │   ├── zephyr_tool.py       ← Zephyr Templating Tool stub (/api/zephyr-tool)
│       │   ├── test_composer.py     ← Test Composer stub (/api/test-composer)
│       │   └── pytest_create.py     ← PyTest Creator (/api/pytest-create) — fully implemented
│       ├── static/index.html        ← Ask CK frontend (all tools + process links)
│       ├── templates/
│       │   ├── prompts/             ← generate_objectives/steps/gaps, suggest_*, analyze_atp_coverage
│       │   └── outputs/traceability.md.jinja
│       └── sessions/                ← _workspace_llm.json + per-case AWPTCM-*.json
├── objective-drafting/              ← Generator data + docs + outputs
│   ├── PROGRESS.md / LESSONS_LEARNED.md / PLAN-server-backed.md / OBJECTIVE_DRAFTING_PROCESS.md
│   ├── data/ ...
│   └── refined-cases/<Group>/AWPTCM-Txxxx/
├── ck-facelift/PLAN-facelift.md     ← 2026-07-13 facelift plan (as executed)
├── pytest-create/  test-composer/  zephyr-tool/   ← future per-tool assets
```

All new server code lives under `ask-ck/CK-main/CK_server/`.

## Installation / Dependencies

Install the pinned dependency set (FastAPI, uvicorn, Jinja2, requests, python-multipart,
pydantic, …) from `requirements.txt` — this is the supported way; the old ad-hoc
`pip install fastapi uvicorn jinja2 requests` line understated what the server needs:

```bash
pip install -r ask-ck/CK-main/requirements.txt
```

**Python 3.13 is preferred** (the testbox runs 3.13.5): the PyTest Creator `py_compile`s generated scripts with the venv's interpreter while they execute on the testbox, so a version mismatch lints the wrong language version — see root `README.md` → *Requirements, manual setup, and the Python-version rule*.

`setup.sh` does this for you inside a repo-local `.venv` (see root `README.md` → *Quick
start*). If using a real LLM provider you may need additional packages such as `litellm`
or the official SDK.

**Two runtime deps exist because their absence FAILS POLITELY** — the feature switches off and
the symptom points somewhere else, so neither had a failing test until 2026-08-03:

- **`paramiko`** — `pt_exec.py`'s SSH/SFTP runner, used since the testbox-execution feature
  landed but declared in no requirements file. `import paramiko` sits inside `_connect()`, so
  the server boots, every other tool works, and the profile probe answers
  `{"ok": false, "detail": "SSH connection failed: No module named 'paramiko'"}` — which reads
  as a testbox/network fault. On a fresh venv the entire **6. Run** step was dead.
- **`fissix`** — the maintained fork of `lib2to3`, which Python **3.13 removed from the
  stdlib**, i.e. the version this project asks you to prefer. Without it the D3 py2→py3 fragment
  translation returns `status: "unavailable"` and legacy fragments ship untranslated behind a
  soft-warn, silently. `pytest_create._py2_refactor_backend()` prefers stdlib `lib2to3` where it
  still exists and falls back to `fissix`.

`tests/test_dependencies_declared.py` now asserts every third-party import in `CK_server/` is
declared, so the next one cannot hide the same way.

## Running the Server

The easiest way is the root `run.sh` (a thin wrapper that forwards to the real
launcher at `ask-ck/CK-main/run.sh`; either path works):

```bash
# The LLM backend is chosen in the UI (Configure page) — there is no key to pass here
./run.sh

# Fast restart — prompt-free background start / stop+start
./run.sh --bg          # background, no prompts
./run.sh --restart     # --stop then --bg
./run.sh --stop        # stop the background server

# Different port
PORT=9000 ./run.sh

# Extra uvicorn options (e.g. debug logging)
./run.sh --log-level debug

# Expose on the LAN — DELIBERATE OPT-IN (see Security Posture: there is no auth)
HOST=0.0.0.0 ./run.sh
```

> **The server binds `127.0.0.1` by default (changed 2026-07-27g).** It has no
> authentication and `push_to_zephyr` can spend the shared `JIRA_KEY` against live
> cases, so loopback is the safe default and matches the documented single-user
> model. `HOST=0.0.0.0` still works but is now an explicit choice — and is not by
> itself a safe configuration. Browse via `localhost`, not the bind address.

> **Hosted deployment (2026-08-26): the server of record now runs LAN-exposed on
> Terrence's workstation, `http://10.33.22.17:8000/`,** as the systemd **user** unit
> `ask-ck.service` (`~/.config/systemd/user/`, `HOST=0.0.0.0`, `Restart=always`,
> linger enabled, so it starts at boot and survives logout). The unit runs `run.sh`
> itself — with a non-TTY stdin `run.sh` exec's uvicorn in the foreground, so all
> venv/PYTHONPATH/offline-model logic stays in one place. The one front door is the
> **`ck` command** (`~/.local/bin/ck`, local disk on purpose — the repo's NFS share
> may be the very thing that is missing): `ck on|off|restart|reload|status|logs|setup|health`.
> Three host-local artifacts, deliberately **not** in this repo: the unit, the `ck`
> script, and an `/etc/fstab` automount for the NFS share
> (`nofail,x-systemd.automount,_netdev`; backup at `/etc/fstab.bak-2026-08-26`) so
> boot → mount-on-first-access → server up with nobody logged in.
> **Manage it with `ck` / `systemctl --user`, never `run.sh --stop`** — that pkills
> uvicorn behind systemd's back (the unit self-heals via `Restart=always`, which is
> precisely why it is `always`: the pkill's clean SIGTERM would end an `on-failure`
> unit permanently). The admin panel's Restart button is service-safe by design: it
> touches a watched `.py` and `--reload` cycles the app **in-process**, so the
> service MainPID never exits (verified 2026-08-26). Caveats: 10.33.22.17 is a DHCP
> lease, and the exposure below is accepted and real — no auth, no firewall on this
> host, and any LAN seat can switch the workspace onto this box's Claude seat.

> **A plain restart needs only `run.sh`, not `setup.sh`.** `run.sh` starts the
> server against the existing `ask-ck/var/ck.db` in seconds. `setup.sh` is for
> first-time environment setup — venv/deps + `git lfs pull` to materialize the
> committed DB, then a quick sanity-check (it does **not** rebuild the DB; the DB
> is shipped). Day-to-day, use `run.sh --bg` / `--restart`. The server also runs
> with `--reload`, so **code edits hot-reload without any restart** — you usually
> only need to restart for env/dependency changes.

### Admin panel (in-page maintenance)

**Double-click CK's face** (top-left sidebar logo — single-click still goes Home)
to open a hidden **Admin** panel. Local single-user convenience so you don't
drop to a terminal. Actions (`/api/admin/*`, all confirmation-gated):
- **Reset current case session** / **workspace LLM config** / **ALL sessions** —
  clears working session state only; corpora are never touched.
- **Restart server** — touches a watched `.py` file so uvicorn's `--reload`
  reloads the app; the page reconnects after ~2s.

> **No DB rebuild here.** `ck.db` is the permanent, committed source of truth
> (built once; source couriers retired), so the panel intentionally has no
> rebuild/re-ingest action — nothing in the product can wipe or refill corpora.
> **Localhost/single-user only** — do not expose `/api/admin/*` on a shared
> deployment without adding auth.

The script automatically:
- Uses `python3`
- Sets the correct `PYTHONPATH` for the `CK-main/CK_server` layout (data paths are absolute via `paths.py`, so working directory does not matter)
- (No MOCK default; real LLM required)

### Manual equivalent

```bash
PYTHONPATH=ask-ck/CK-main python3 -m uvicorn CK_server.main:app --host 127.0.0.1 --port 8000 --reload
```

Alternative (cd into the server dir):

```bash
cd ask-ck/CK-main/CK_server
PYTHONPATH=.. python3 -m uvicorn CK_server.main:app --host 127.0.0.1 --port 8000
```

**Choosing the LLM backend**: on the Configure page, not in the environment.

The permitted backends are an allowlist — `models.SUPPORTED_AUTH_METHODS`: `local_llm`
(the org vLLM, the default), `claude_agent`, `claude_code`, `grok_cli`. The set is a
**governance control**, closed at two layers: `set_llm_config` 400s on anything else, and
`_call_llm_raw` refuses to dispatch even if a stored session names a retired backend.

`LLM_API_KEY` and `LLM_BASE_URL` **were removed on 2026-08-04** along with the `api_key` /
`account` auth methods. They let a caller supply their own key and endpoint, so the tool
could be pointed at an arbitrary third-party model provider — a capability we do not want
and do not want to imply we have. There is no environment-key fallback and no configurable
endpoint; the vLLM address is fixed in code. Pinned by `tests/test_llm_backend_allowlist.py`
(including a structural check that the env channel has not been reintroduced).

Real LLM (org vLLM or a local CLI login) is required. MOCK/demo mode has been removed.

### Claude — per-user local agent (shared-server safe; the UI Claude mode)

`auth_method: "claude_agent"`. This is how a **shared** Ask CK webpage uses Claude
while keeping each user on **their own** Claude seat — never a shared one.

**Why:** a Claude subscription seat is per-person; the Claude Code CLI login lives on
a user's own machine and can't be handed to a remote server. So on a shared server the
server must **not** run `claude` itself. Instead:

```
 user's laptop:  ck-agent (127.0.0.1:8765) ── runs ──▶ claude -p  (user's OWN seat)
                       ▲ localhost
                 browser tab ──────────────── brokers ───────────────▶ shared Ask CK server
                                                                        (UI/data; NO claude)
```

The shared server queues a prompt job keyed to the browser's session id
(`X-CK-Session` header, minted per tab). That user's tab long-polls
`GET /api/agent/next`, POSTs the prompt to its own `ck-agent` at
`http://127.0.0.1:8765/run`, and returns the completion via `POST /api/agent/result`.
`claude` only ever runs on the user's machine; the server sees prompts/completions
(as always) but never a credential or seat.

**Per-user setup:**
1. On your own machine, install Claude Code (anthropic.com/claude-code); run `claude` → `/login`.
2. Start the agent: `cd ask-ck/agent && ./run-agent.sh` (leave it running). See `ask-ck/agent/README.md`. To pin CORS to your server: `CK_AGENT_ORIGIN=http://ck-box.lan:8000 ./run-agent.sh`.
3. In the UI (**LLM → Configure**): select **Claude Code CLI (my local machine)** → pick a model (**Haiku / Sonnet / Opus**, default Sonnet) → **Check my local agent** → **Apply / Login**.

Notes:
- The agent binds `127.0.0.1` only and restricts CORS to the Ask CK origin; no token (it can only spend that user's own seat).
- Server-side, blocking LLM calls run in a threadpool so the agent long-poll stays serviceable (no event-loop deadlock). One job at a time per session; a job whose browser/agent never answers times out cleanly.
- **Model selection (2026-07-22d):** the Haiku/Sonnet/Opus radio row sets `llm_config.model`, which flows `job.model` → ck-agent → `claude --model <name>`. It's a live toggle (persists immediately, like the vLLM Fast/Thinking one); a model typed in the free-text field still overrides. Values are CLI aliases (`haiku`/`sonnet`/`opus`).
- **Per-task model routing (2026-09-07, token-efficiency decision 6):** two selects under the toggle route the fan-out call classes to a cheaper alias — *unit fills* (`unit_model`: per-unit generation and per-unit Fix) and *step matching* (`match_model`); blank = same as the toggle. Review, whole-script Fix and the single-call generate always follow the toggle. Stored on the workspace `_workspace_llm` row and applied at dispatch from it (`llm_config.cfg_for_task`), never from a per-case copy; a toggle POST that omits the fields preserves them. Claude aliases only — this is not a new backend. Evidence: `TOKEN-EFFICIENCY-REPORT-2026-09-04.md` §5 (Sonnet 5 matched Opus on 4 of 5 sampled units at ~59% of the cost; same step-match shortlist at under half). The toggle handler also now posts the *checked* auth method — it used to post a literal `claude_agent`, so changing the model under "Claude Code CLI (this server)" silently moved the workspace to the browser agent.
- **Token usage + cost (2026-07-22d):** the ck-agent lifts `usage` + `total_cost_usd` from the `claude -p --output-format json` envelope and returns them from `/run`; the browser broker forwards them in the `/api/agent/result` POST; `registry.deliver()` stores them on the job result in the exact shape `llm_debug.normalize_usage` expects (usage sub-dict + top-level `total_cost_usd`), so token badges + the debug-log populate for this transport too. **Restart the ck-agent** after upgrading to enable this. When a transport reports nothing, the badge honestly shows "— tok" (never estimated).
- Usage counts against each user's own Claude seat's limits. Keep the agent running and the tab open while working.
- Endpoints: `GET /api/agent/next?session=…`, `POST /api/agent/result` (accepts `usage` + `total_cost_usd`), `GET /api/agent/status?session=…`.

### Claude on the server host (single-user hosting only)

`auth_method: "claude_code"` runs `claude -p` on the **server** machine against its own
login. Correct only when **one person** hosts Ask CK for themselves (e.g. on their
laptop). It is **not** offered in the UI anymore — a shared instance would pool every
user through one seat (a subscription-terms problem). Legacy `claude_code` configs still
deserialize and are mapped to `claude_agent` when restored in the UI. For a genuine
multi-user *server* that isn't per-user, use the Anthropic **API** (`api_key`), which is
licensed for that; the code path exists though it isn't surfaced in the UI.

It **is** the only headless Opus path — `claude_agent` needs a browser session and 502s from a
script — so it is what batch/scripted runs use. That made it the first mode to be exercised on
large artefacts, which exposed four things about the transport (all fixed 2026-08-03, see
`llm._call_claude_code_headless`):

- **`claude -p` is an agentic coding CLI, not a completion endpoint.** Invoked bare it has tools
  and loops. A 65k-token generate prompt consumed **2,670,565 input tokens over 23 minutes for
  $4.65 and returned an empty result** with `is_error: false` — surfaced as the misleading
  `502 "LLM returned no python code block."` Now always `--tools ""`.
- **`--output-format stream-json`, and every `assistant` text block is concatenated.** The
  `json` format's `result` field carries only the FINAL assistant message, so a long answer
  loses its *head* and what arrives is a mid-class tail that lints as an `IndentationError`.
- **The caller's `system` message REPLACES the CLI's harness prompt** (`--system-prompt`; a
  one-line neutral steer when the caller has none). It used to be dropped entirely, then
  appended (`--append-system-prompt`) on the theory that the harness prompt carried context
  the CLI needed. Measured 2026-09-04: with `--tools ""` there is nothing for that context to
  drive, and the harness prompt carries per-invocation content, so every call was a prompt-cache
  **miss** — the same 39.7k-char unit prompt sent twice cost $0.37 both times; replaced, the
  second call read all 29,674 tokens from cache and cost $0.14.
- **The CLI starts in a neutral directory, not the repo.** `claude -p` folds every CLAUDE.md
  above its cwd *and the project's memory index* into every call: from this repo that was
  16,104 tokens for a trivial prompt against 2,602 from a bare directory — ~13.5k tokens of
  project files per call, at the 1-hour cache-write premium, 38 times per per-unit generate.
  `llm._cli_neutral_cwd()` (under the system temp dir) has nothing to discover.
- **`--no-session-persistence`.** A completion is not a session; without it each unit of a
  fan-out left a transcript in `~/.claude/projects` (66 in one day).
- **The prompt cache matches only at content-block boundaries (2026-09-07).** With the harness
  gone the 38 unit prompts of T44297 shared their first 19,456 chars and the cache still read
  **zero** tokens on every call: the CLI's breakpoints sit on the system prompt and on the user
  message, and a shared prefix inside ONE user block whose tail differs can never hit. Probe:
  the shared half in the user block → 0 read on the second call; the same half as
  `--system-prompt` → 7,879 of 8,059 read at one twelfth of the price. So the per-unit prompt
  carries a visible split marker (`routers.pytest_create._PT_PROMPT_SPLIT`) and everything above
  it travels as the system prompt (behind `_CODE_SYSTEM_PROMPT`), everything below as the user
  turn — see "Per-unit generation — token-efficiency changes" under PyTest Creator. The debug
  log now records `system` and keeps `cache_read_input_tokens` / `cache_creation_input_tokens`
  as fields (still folded into `input_tokens` for every existing consumer).
- **The per-user agent (`ask-ck/agent/ck_agent.py`) now mirrors all of the above**, and the
  server's steer rides with each job (`system`) so the agent can pass it. Before 2026-09-04 the
  agent path ran with tools, under the harness prompt, unsteered, from the user's shell cwd and
  in `json` format — one unit call went agentic for 20 turns and 528k input tokens.
- **Thinking is capped, on long calls only.** Thinking shares the output budget with the answer
  and can consume nearly all of it. But passing `--max-thinking-tokens` at all *enables*
  extended thinking (2,242ms → 16,426ms on a trivial prompt), so applying it unconditionally
  timed out the health ping. `llm._is_long_call()` is the single predicate deciding this and the
  whole-response timeout floor, so the two cannot disagree.

- **A long answer arrives in SEVERAL messages, and is reassembled.** `32,000` bounds one
  message, not the answer: measured `output_tokens` on the stored multi-message generations are
  **67,326 / 66,334 / 57,188 / 34,966**, and every one is a complete script.
  `_parse_cli_stream` concatenates the assistant text blocks and `CK_server/gen_assembly.py`
  stitches the continuation seams back together, resolving classes a continuation re-emits.
  A reply that does **not** reassemble cleanly is refused (502) rather than persisted.
- **Truncation is detected on the `result` envelope, not on `stop_reason`.** Captured against
  CLI 2.1.207, `stop_reason` is `null` on every genuine assistant message *including ones that
  hit the cap*; the only truthy value sits on a message the CLI synthesizes to carry its error,
  and that message's text is filtered out so it cannot land inside the generated script.

> **Previously documented here as "a hard output ceiling of roughly 9–20 `TestCase` classes",
> gated by `_size_overflow()`. That was refuted on 2026-08-03 and both are gone.** The ceiling
> was a defect in `_parse_generated_blocks`, which stopped at the first *continuation* fence and
> discarded the rest of the reply — usually mid-token, which read as model truncation. The
> gate's three "measured" constants were fitted to that parser's output. The real protection is
> now applied on arrival (reassembly + the completeness lint) instead of predicted before the
> call. See `ask-ck/ck-facelift/PLAN-pipeline-end-to-end.md` Phase 7 and the ⚠-bannered
> `ask-ck/pytest-create/FINDINGS-generation-size-ceiling.md`.

### Grok CLI Subscription Mode (SuperGrok / X Premium+)

`auth_method: "grok_cli"` (Grok provider only) calls a locally installed + logged-in Grok CLI (`grok login --oauth`) instead of the HTTP API. **Same seat-sharing caveat as server-local Claude**: it runs on the server host, so it's for single-user hosting (a per-user Grok agent could be added later, mirroring `claude_agent`).

### Grok CLI Subscription Mode (SuperGrok / X Premium+)

`auth_method: "grok_cli"` (Grok provider only) calls a locally installed + logged-in Grok CLI (`grok login --oauth`) instead of the HTTP API. 

- `GET /api/wizard/grok_cli_status` reports availability.
- In the UI (sidebar **LLM → Configure**): select the **Grok CLI (SuperGrok / X Premium+ subscription)** radio, use the "Check Grok CLI" button, then "Apply / Login". Model optional (CLI default used if blank).
- Prompt passed safely via temp file; output captured cleanly.
- Fully integrated into synthesis and ATP paths. Real calls were tested on a machine with an active subscription login.
- Usage counts against the subscription (no separate API billing).

### Local LLM (organization vLLM)

`auth_method: "local_llm"` calls the org's self-hosted vLLM endpoint (`http://vllm.ai.atlnz.lc/v1`, OpenAI-compatible). Two modes via the **Fast / Thinking** toggle on the Configure page (models `vllm-fast` / `vllm-thinking`).

- **Key**: set it once on the Configure page (stored gitignored in `CK_server/secrets.local.json`; survives restarts and new sessions). Re-enter to update when it expires; leave blank to keep the stored key. For headless runs, `export LOCAL_LLM_KEY=...` works as a fallback. The key never leaves the server (not in sessions, responses, or the debug log).
- This transport reports real token usage (`usage.prompt_tokens/completion_tokens`), so the LLM debug footer/badges show actual in / out counts.
- **Reasoning-model handling (2026-07-21).** *Both* org models are reasoning models: they spend completion tokens on hidden chain-of-thought (returned in `message.reasoning_content`) **before** emitting the answer in `message.content`. The OpenAI-compatible call path in `llm.py` accounts for this in three ways: (1) `max_tokens` is raised to **16000** for `local_llm` (the legacy 2000 was exhausted mid-reasoning, leaving `content` null); (2) the response parser guards a null/empty/`finish_reason=length`-truncated `content` and raises a *clear* error (falling back to `reasoning_content` for a reasoning-only reply) instead of a cryptic `NoneType` crash; (3) requests are sent as a **system + user** message pair (the shape documented in `resources.md`) — `run_prompt` prepends a default JSON-only steer (`_JSON_SYSTEM_PROMPT`) that skips the model's scratchpad and cuts completion tokens sharply (measured ~35% on `extract_sequence`, ~22× on a trivial JSON ask). Callers can override the system message per call; the health-ping sends none. Anthropic's native path uses the top-level `system` field instead of a message role.
- **Streaming transport (2026-07-22).** The OpenAI-compatible (vLLM) call path **streams** the response (`stream: true` + `stream_options.include_usage`), consuming the SSE body and accumulating `content`/`reasoning_content` deltas into the same result the non-streamed path produced (all guards + token badges unchanged). This is the structural fix for the read-timeout failure the reasoning models hit on the largest-output step (`generate_script`): with a streamed body the HTTP `read` timeout bounds the gap **between chunks**, not the whole response, so a reasoning phase of *any* length completes as long as chunks keep flowing — a static timeout ceiling (even 600s) could still be exceeded and was (see `ask-ck/pytest-create/PLAN-pytest-testing.md` §7.7/§8). Verified live: a `vllm-thinking` call with a 30s read timeout ran 21+ minutes without timing out. `max_tokens` is also now overridable per call (`generate_script`/`fix_script` request 32000; default stays 16000 for `local_llm`). The Anthropic native path stays non-streaming (it had no such failure).
- **Health check** (next to the "key stored ✓" note): pings the *currently-selected* model with a minimal completion via the same real-call path (`POST /api/wizard/llm_health` → `_health_ping`), and reports `✓ up — <model> (<ms>) · N in / M out (total)` or a clean error. Distinguishes "my config is wrong" from "the backend is down" without spending a real synthesize. Provider-agnostic (works for any auth_method). Note: `vllm-thinking` reasons before replying, so even a trivial ping shows a large *output* count — that's the model's reasoning, and it's exactly the cost signal for comparing Fast vs. Thinking.

### LLM request observability

Every LLM request (success or failure) is recorded to `CK_server/debug-log/<session>.jsonl` (gitignored; full prompts/responses — can grow to a few MB per heavy session, no rotation) and to an in-memory ring served at `GET /api/llm/recent` / `GET /api/llm/log` (keyed by the browser's `X-CK-Session`). In the UI: a per-panel **"Last LLM request (this page)"** footer plus a token badge (`N in / M out (total)`) next to the pressed LLM button (`— tok` where the transport reports no usage, e.g. Grok CLI / agent bridge). Credentials are whitelisted out of records. **The debug-log is development scaffolding**; the durable/portable equivalent is the Provenance block below.

**Live progress + true Stop (2026-08-26).** Every LLM button in the app is a live one while
busy: `⟳ Generating… 37s / ~45s · 12.3k streamed` with a 2px fill bar. The browser stamps
each call with an `X-CK-LLM-Call` id (middleware → ContextVar → `llm_inflight.py`, an
in-memory single-process registry — same authority caveat as `locks.py`); the button polls
`GET /api/llm/inflight/{id}` for elapsed / streamed chars / `typical_ms` (median of this
session's recent successful calls to the same template — that is what the bar fills
against). Streamed counts are real server-side observation: vLLM SSE chunks, and the
claude/grok CLI's stream-json lines — the CLI always streamed; `subprocess.run` was
buffering it. **Clicking the busy button is a TRUE cancel** (`POST /api/llm/cancel/{id}`):
the CLI process group is killed (SIGTERM, SIGKILL after 5s), the vLLM stream is closed
mid-generation, an agent job is woken abandoned. The endpoint then errors with
"cancelled by user", so nothing persists, and the UI reports "⏹ stopped — nothing was
kept" rather than a failure. A UI-only abort (server finishes and spends anyway) was
explicitly rejected. Transport note: the CLI paths run via `llm._run_cli`
(Popen + pump threads), which preserves `subprocess.run` semantics exactly — the
transport-contract tests pin the boundary and pass unchanged; dry-runs never register.

### LLM Provenance (portable prompts) + dry-run preview

Every LLM panel (Generator: objectives, steps, the 3 *Suggest* panels; PyTest Creator: sequence, script-search, fragments, generate) carries a collapsible **LLM Provenance** block (`static/js/provenance.js`, shared) with **↻ Refresh (no send)** and **Copy prompt / Copy response** buttons. Purpose: grab the exact prompt to paste into a competing LLM (comparative analysis / free-LLM fallback).

- **Refresh** re-invokes the panel's own endpoint with `dry_run: true`. The backend renders the prompt through the *real* context path and returns it **without sending** to the LLM — no tokens, not recorded to the debug-log. Because it reuses the real call path with one flag flipped, the previewed/copied prompt is **1-for-1** (byte-identical) with what a real send transmits — verified in-repo.
- **The preview uses the panel's LIVE inputs, and targets the endpoint the panel actually drives (2026-08-31).** `registerProvenance` takes a `bodyFn` evaluated at click time — that is what makes the preview 1-for-1 with a real send — but every PyTest Creator panel passed a hard-coded empty body, so Refresh rendered against the endpoint's server-side *defaults* rather than what the page showed. On **Generate** that surfaced as a 400: the default group for a case in `Authentication & Security` failed `_validate_naming`, so Refresh answered "Invalid group name" for a group the reviewer had already edited away, while the Generate button (which does post its inputs) worked. On **Script Search** the mount still pointed at the retired whole-case `/suggest_scripts` — its last reference anywhere in the frontend — so Refresh rendered a mega-prompt this flow never sends. Both fixed: Generate passes its live naming, Script Search resolves `/suggest_scripts_step/{key}/{n}` at click time so the preview follows the step pager.
- Mechanism: `dry_run` flag on `llm._call_llm_with_meta` (short-circuits before the send) + `run_prompt`; every Generator function (`synthesize_objectives/steps`, `suggest_relevant_*`, `analyze_atp_coverage`) and every PyTest endpoint accepts it and returns `{provenance: {prompt, provider, model, auth_method}}`. `SynthesisRequest` gained a `dry_run` field. The normal (non-dry) PyTest paths now also store the sent `prompt` + `response` in their step provenance.

## Accessing the Tool

- Main Ask CK UI: `http://your-local-ip:8000/`
- Process as web-based page: `http://your-local-ip:8000/process`
- Interactive API docs (Swagger): `http://your-local-ip:8000/docs`
- Health: `http://your-local-ip:8000/health`
- Tool stubs: `GET /api/zephyr-tool/status`, `GET /api/test-composer/status`, `GET /api/pytest-create/status` (and `POST /api/pytest-create/generate/{key}` → 501 until implemented)

## Typical Workflow (Repeatable Process — Generator)

UI step numbers below are the visible 1–6 Generator labels.

1. **Step 1 – Cases**: select an AWPTCM case (dual dropdowns populated with real project cases) and click **Load**.
2. Sidebar **LLM → Configure**: choose a login radio (**Local LLM** is default — pick Fast/Thinking and, first time, paste the key; or select Claude Code CLI / Grok CLI). Optionally check CLI status. **Apply / Login** — no case required; the workspace default persists across cases (and is also stored on the selected case, if any). Steps 1 and 2 can be done in either order.
3. **Step 2 – TestLink**  
   Review primary + candidates. Use **Search TestLink** / **Suggest with LLM** to expand or re-rank, then confirm selections.
4. **Step 3 – Zephyr**  
   Review relevance-ranked external Zephyr cases (current Cases list omitted). Use **Search Zephyr** / **Suggest with LLM** as needed, then confirm.
5. **Step 4 – ATPyLib (scored)**  
   Search and select ART cases (pre-scored via LLM). Use **Search ATP** / **Suggest with LLM** if needed. Confirm selections only — **no gaps form** in this step.
6. Only after all three confirms are done → **Step 5 – Objectives (LLM)** becomes active. Click **Synthesize Objectives (LLM)**.
   - Backend builds templated prompts from your selections + process principles.
   - LLM generates: **Gaps analysis** (for Traceability) and objectives.
   - Review/edit, then **Confirm Objectives → Step 6**.
7. **Step 6 – Test Steps (LLM)**: **Synthesize Test Steps** (first testScript step is always the server-built traceability note); edit/revise as needed.
8. Click the teal **Export Repeatable Bundle** (appears after steps exist).
   - Produces: `traceability.md` (templated; **Gaps Noted** from LLM at synthesis/export), `AWPTCM-Txxxx-zephyr_payload.json` (exact Zephyr Scale shape), and session JSON (full provenance).
   - Auto-persists server-side to `ask-ck/objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/`.
9. **Push to Zephyr** (2026-07-22c; buttons next to Export) — publishes the exported bundle to the live Zephyr case.
   - **Preview Push (dry-run)** shows the exact plan with zero writes; **Push to Zephyr** performs it (with a confirm dialog).
   - On the case, in order: strip a leading `(N)`/`(…)` group from the **Name** → ensure **version 2.0** (`POST /rest/tests/1.0/testcase/{id}/newversion`; idempotent — bumps 1.0→2.0, skips if already ≥2.0) → PUT objective+testScript (lands on the new latest version) → replace `traceability.md` attachment (no duplicates) → post ART web-links.
   - `POST /api/wizard/push_to_zephyr/{key}?dry_run=…` **shells out to `tool/upload_refined.py`** (flags `--fix-title --new-version --verify`; `--force` is opt-in per request since 2026-07-27g and the UI does not send it). The server never holds the JIRA token (the CLI reads it from `secrets.md`). It operates on the **on-disk bundle**, NOT a re-export — re-exporting from an incomplete/backfilled session would degrade `traceability.md`, so Export explicitly first if you edited.
   - **A real push requires a confirmation token** (2026-08-03): `dry_run=false` is rejected with 400 unless the request body carries `{"confirm": "<case key>"}` matching the key in the path. `dry_run` is a query parameter, so without this a production write was one character from a preview for any non-browser client, and the browser-side `confirm()` is not executed by curl. It is not authentication — it is the second fact that has to be supplied deliberately.
   - **Nothing unvalidated reaches a live case** (2026-08-03). `upload_refined.py` imports `validate_zephyr_payload` from `llm.py` — the shape rules have one owner. The import is lazy and **fails closed**: if it cannot be loaded the case is refused, never passed. Validation also runs under `--dry-run`, so the preview reports what would be refused. `--skip-validation` is the deliberate override. A blocked case makes the process exit non-zero, so a refused push cannot read as success in the UI. **(2026-08-05: the added `expectedResult` content rule was removed — a Zephyr manual step is *designed* to leave `expectedResult` empty, so the field is forced empty at generation and never blocks a push. See memory `expected-results-deliberately-absent`.)**
   - **Every `--execute` is audited** to `ask-ck/var/zephyr-push-audit.jsonl` (gitignored; the server never reads it). A `push.intent` record is written **before the first network call** — who, when, key, argv, flags, the pre-push state including the full prior objective/testScript, and what it intends to change — then `push.version` and `push.outcome`. **A case whose audit record cannot be written is refused.** Zephyr keeps no version trail for these pushes (the process is capped at v2.0), so this log is the only local record of replaced content.
   - **Loading a Complete case** rehydrates step4/step5 (objective+steps) from the on-disk `zephyr_payload.json` when the runtime session lacks them (`wizard._backfill_from_refined`), so previously-refined cases reflect correctly and can be pushed. The Zephyr instance is Jira Server / Adaptavist ATM; the internal `tests/1.0` API accepts the Bearer PAT.

Tables are compact to fit on one page with no side-scroll. The Zephyr review contains only external cases (current Cases list entries, including the primary, are omitted).

The process and output formats are identical to what is documented in `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`.

## LLM Templating & Repeatability

Prompt templates live in `CK_server/templates/prompts/`:
- `generate_objectives.jinja` / `generate_steps.jinja` — synthesis. **(2026-07-22d)** `generate_objectives.jinja` no longer contains the gaps block, and `synthesize_objectives` no longer makes the gaps LLM call — Step 4 is a single self-contained objective call. Traceability gaps are decoupled to export time (below).
- `generate_gaps.jinja` — Traceability gaps for `traceability.md`, generated **at export time only** (`generate_coverage_gaps`, called from `/api/wizard/export` when the session has no gaps yet). No longer part of objective synthesis.
- `suggest_testlink.jinja` / `suggest_zephyr.jinja` / `suggest_atp.jinja` — pre-select assists
- `analyze_atp_coverage.jinja` — ATP ranking only (no gaps paragraph)

They inject confirmed selections + process principles ("artefacts, not procedures", first step notes + traceability, positive/negative/special cases, etc.).

After the LLM returns text, `llm.py` parses/normalizes and export uses `templates/outputs/traceability.md.jinja` so files match the documented standard.

**Note**: MOCK/demo mode has been removed. Real LLM (CLI login preferred) is required. Edit templates to refine style without code changes.

## Hosting Behind nginx

> ⚠ **The shipped examples are plain `listen 80` reverse proxies with NO TLS and NO auth,
> and Ask-CK itself has no authentication.** Following this section as-is publishes an
> unauthenticated tool that can spend the shared `JIRA_KEY` against live Zephyr cases to
> anyone who can reach the host. Do not use it for a shared deployment until
> `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` lands (that plan replaces these
> examples with TLS + auth in Phase 3). For local single-user use, you do not need nginx
> at all — `run.sh` on loopback is the supported path.

Copy the example:

```bash
cp ask-ck/CK-main/nginx-drafting-server.conf.example /etc/nginx/sites-available/ask-ck
# edit and enable, then nginx -t && systemctl reload nginx
```

Typical snippet (adjust path as needed):

```
location /ask-ck/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Access via your local IP / hostname that nginx serves.

## Data Source

**There is exactly one data source: `ask-ck/var/ck.db`** (shipped via Git LFS). The server reads
all corpora from it via `db.py` — no JSON, ever (enforced by `tool/guard_db_only.py`). It holds:
Zephyr (45,427 XML cases + 410 API targets), TestLink historical (21,620), ATPyLib/ATP (10,157),
the script index + literal source code / chunks (830 scripts / 5,782 chunks), candidates,
decisions, the framework-surface vocabulary, per-case + workspace sessions, and ~84k semantic
vectors — everything.

`ck.db` is the **permanent single source of truth**, built once and committed. The intermediate
source/courier files it was originally built from have been **retired and deleted** — there are no
JSON/JSONL corpora on disk and **no rebuild step**. `tool/build_db.py` remains only as provenance
of how the DB was constructed and refuses to run. The one raw original kept, purely as a provenance
root (not read by anything), is the Zephyr XML export at
`ask-ck/objective-drafting/data/zephyr_full/Zephyr-Database-*.xml`.

### CLI command reference (`cli_commands`, added 2026-07-27)

A **renewable** reference table — deliberately unlike the corpora above, which are permanent
and never rebuilt. It holds the real AlliedWare Plus CLI: command syntax and the switch's
actual sample output, harvested from the internal docs site `https://docs.atlnz.lc/preview/`.

- `cli_commands` — one row per **unique content hash** (4,652 rows; 993 carry sample output):
  `command`, `page`, `cmd_group`, `syntax` (JSON), `examples` (JSON), `sample_output`,
  `pre_blocks`. Content is byte-identical across product families ~96% of the time, so it is
  content-addressed and stored once.
- `cli_command_products` — the thin support matrix (61,240 rows): which product family ships
  which variant. This is how per-family differences are represented, e.g. `duplex` is
  `{auto|full|half}` on x530/x220/x550 but `{auto|full}` on x930/x950 (half duplex is
  impossible at ≥1 Gig, so platforms that never go below it cannot offer it).
- `cli_commands_fts` — FTS5 over command/group/syntax/sample output.

**Re-run any time:** `python3 tool/harvest_cli_docs.py --all` (73,006 fetches, ~59 min,
idempotent — rows are replaced per (product, command), and `meta.cli_docs_harvest` records
when it last ran and what it saw). Read it with `python3 tool/cli_lookup.py <command>` or
`--prompt-block`. This does **not** violate the no-rebuild invariant: it adds a new,
externally-sourced reference table and never touches the Zephyr/TestLink/ATP/script corpora.

**Why it exists:** the PyTest Creator prompts demanded "exact CLI fields" while showing zero
examples of real output, so every model in the Part 2B matrix — Claude Opus included —
invented a `speed=1000` / `state=up` schema the switch never prints. Real output is
`current duplex full, current speed 1000, current polarity mdix`. Both the sequence-extraction
and generate prompts now inject the relevant commands' syntax + sample output.

**Caveat — not a validity oracle.** Cross-command physical constraints are absent from the
source (the x530 `duplex` page lists `half` unconditionally; nothing says it is impossible at
≥1 Gig). Those rules must come from the ART corpus, which encodes them implicitly, or be
written by hand. The site is also a *preview* under active construction and serves occasional
soft-404 placeholders (HTTP 200 with a "may have moved in the latest rebuild" body) — the
harvester detects and counts those separately rather than recording them as empty commands.

## PyTest Creator (2026-07-14)

Turns a **Complete** case (one with a refined `zephyr_payload.json`) into a runnable
Allied Telesis framework test script. Full plan + progress tracker:
`ask-ck/pytest-create/PLAN-pytest-creator.md`.

**Objective-coverage gate (2026-07-27).** *Every objective links to a Zephyr step, and
every Zephyr step needs at least one PyTest step — otherwise that part of the objective is
not being tested.* Enforced on the **Confirm** button (Generate still completes, so the
script is available to inspect and regenerate) for **2. Sequence** and **5. Generate**:
`confirm_step` returns **409** with a message that QUOTES each untested Zephyr step, since a
bare index is not actionable. Generate is gated too because a case can arrive there with
zero reusable fragments (a `decision: new` case), so the fragment gates prove nothing about
coverage; there it additionally checks TestCase count against non-setup sequence steps.
Coverage is recomputed and stored (`step2.coverage`) on both `extract_sequence` and
`save_sequence` — a deleted UI row drops coverage as easily as the LLM can. Override with
`{"acknowledge_coverage_gap": true}` when a source step is genuinely untestable: a recorded
decision, not a silent pass. Built after a re-extraction silently dropped T33234's entire
MDI/MDI-X forced-polarity negative path (14 steps → 9).

**Lint gate on Confirm, split by AUTHORITY (2026-08-04).** `confirm_step` also refuses
**5. Generate** while the lint reports errors — it previously never looked at the lint at all,
so a script with hard errors could be signed off and carried into the run and export stages.
The 19 lint errors are two different kinds of thing, so they have two different authorities:

- **blocking (14)** — the artefact provably cannot work: a syntax error, missing structure, a
  surviving `>>> FILL` marker, `self.` used before the assignment block, a device or port the
  fixed `init()` frame never bound (an `AttributeError` on the testbox), a bad framework
  import, a duplicate portlink binding, fewer TestCase classes than the approved sequence, or
  a completeness check that could not run. **No override — regenerate.**
- **policy (5)** — the script runs but breaks a house rule: the four logging-contract checks,
  and calling `setup.init_portlink()` directly instead of through the frame's
  `_ck_bind_link()`. Overridable with `{"acknowledge_lint_policy": "<why>"}`; the reason is
  recorded on the session in `step6.policy_acknowledgements`.

Anything unrecognised is treated as blocking, so a newly-added check is strict until someone
classifies it. *Why the split exists:* the only lint error ever to fire on a real generation
was the `init_portlink` one, on the best script we have produced — and the generate prompt was
telling the model to bind devices in `TestSet.init` while never mentioning `_ck_bind_link`.
A blanket no-override rule made that script permanently unconfirmable because of a prompt bug.
The prompt was fixed in the same pass, and `tests/test_prompt_agrees_with_lint.py` now asserts
that every rule the lint enforces is actually conveyed by the prompt.

**Run results: consistent, readable, no gaps (2026-08-04).** `parse_framework_log` reports one
outcome per case — `PASS` / `FAIL` / `UNSUPPORTED`, plus `ERROR` for a case that never reached
a verdict — as a `counts` dict beside the log's verbatim `numPassed`/`numFailed`, and a single
readable line with **both tallies labelled**, because "N passed" is ambiguous between cases and
assertions and the log reports both:

```
cases: 1 passed, 10 failed, 4 unsupported, 1 no verdict (of 16); assertions: 60 passed, 43 failed
  — 1 case(s) did not reach a verdict (5700.2002.90).
```

`results_complete` means the **results are trustworthy** — the run produced results, every
registered case reported a verdict, and no failure line is unattributed. It deliberately does
*not* mean the test passed; that is `counts["FAIL"] == 0`, asked separately. Conflating the two
is the original defect: a run that never started parsed to `0 passed, 0 failed`, which read as
a clean sweep to every count-based check. Expected-case count comes from the script's own
`ts.add_testCase(...)` registrations, read from the AST.

> Note an UNSUPPORTED case reports its own inapplicability **as a failure line**
> (`!!FAIL: DUT does not support USB Media`), so it contributes to `numFailed` while being
> classified UNSUPPORTED. That is why the verdict reads case results rather than counters.
> Judging whether a case *should* have been unsupported, and tracking that across runs, is
> **Test Composer's** job, not this layer's.

**Gated flow (sidebar steps, each with an explicit Confirm):**
1. **Cases** — pick a Complete case, Load Case & Continue.
2. **Sequence** — LLM extracts a prescriptive sequence of automatable steps from the
   refined payload (traceability note skipped); edit rows, Save, Confirm.
   **Per-step carousel (2026-07-23):** Script Search and Fragments are now
   page-within-a-page — one sequence step per screen, Prev/Next + a clickable step-pill
   row (green ✓ = covered, yellow ✗ = gap). Each step has its own candidate/chosen tables.
3. **Script Search** — per-step: mechanical scoring over the script index + LLM
   coverage verdicts (full/partial) for the current step; free-text search box for
   manual digging; Choose moves a candidate down into the step's Chosen table. Selections
   are stored **per step** (`{stepN: [ids]}`) and flattened downstream. `view` shows real
   source. Confirm. *(The former standalone whole-sequence LLM field was removed.)*
   **Suggest all steps (2026-08-26):** a button in the coverage bar runs the per-step
   suggest for EVERY sequence step, sequentially in order — one LLM call per step, not the
   retired whole-case mega-prompt. Clicking it again stops after the in-flight step
   (a true cancel — see LLM observability below). **Everything the page shows persists**
   (same date): per-step suggestions land in `step3.step_matches[step]` (merged by id,
   newest verdict wins) and chosen rows carry whitelisted record snapshots
   (`step3.records`, sent by Save Selections) — so a hard reload or a fresh browser
   restores candidates AND chosen rows with their coverage/why intact. Previously only
   the whole-case suggest persisted, and once its button left the UI nothing did: a
   reload lost all candidates and degraded chosen rows to `other`/`?`. Suggestion
   fetches deliberately do NOT unconfirm step 3 or invalidate fragments — candidates
   are not selections. A per-step LLM failure is now a loud **502**, not a silent
   `matches: []`. **The coverage/why verdicts feed Fragments** — each script in the
   gather prompt carries "chosen for sequence step N — <coverage> — <why>" lines
   (per-step verdicts outrank whole-case ones), so fragment choice is no longer blind
   to why the scripts were selected; fragment `why` was already flowing into Generate
   as "Reviewer note".
   **Confirmable through the flow that drives it (2026-08-31).** `confirm_step` required
   `step3.provenance` or `step3.matches`, and after the per-step move neither is written:
   step 3 has never written `provenance` (only steps 2, 5, 6 and 8 do) and `matches` came
   only from the whole-case suggest that left the UI on 2026-08-20. A visibly complete step
   3 was therefore rejected however finished it was, and step 4 was unreachable behind
   `_require_confirmed`. It now also accepts the per-step flow's own evidence that the step
   ran — `step_matches` (written even when a step matched nothing, so an empty list stays a
   legitimate answer) or `selections` (keyword picks made without ever invoking Suggest).
   Scoped to `matches`: step 5 writes real provenance, so `fragments` keeps the original
   predicate. Pre-2026-08-26 sessions still pass on `matches` unchanged.
   **Step 3 records what it sent (2026-08-31).** It was the one LLM step storing no
   provenance at all, so its panel — which seeds from `step3.provenance` — was permanently
   blank for any session driven through the per-step picker. `suggest_scripts_step` now
   writes `{llm, prompt, response, step_n}`. **One slot, not one per sequence step:** the
   session payload is a row in the permanent `ck.db` and a 32-step case would otherwise
   carry 32 full prompts; `step_n` records which step it belongs to, and any other step's
   prompt is a Refresh away at zero cost. A dry run records nothing.
4. **Fragments** — per-step, no cap: LLM proposes symbols per step and the server
   resolves them to real code by indexed line ranges (invented symbols are dropped;
   `maps_to` numbers that aren't real sequence steps are dropped too — 2026-07-23). Each
   step shows a chosen/redundant accounting (green-outlined chosen, nested faint-red
   redundant alternatives). An **assembled-artefact preview** (skeleton + selected
   fragments slotted per step) sits above Save Selections; a verify step with **no**
   fragment carries a positive `# ===== NO REUSE … =====` marker so gaps are visible by
   presence, not silence (finding #7). `selections_fingerprint` stamps the gather so a
   Step-3 change surfaces a stale-warning + re-gather prompt. Untick unwanted, Confirm.
   **Fragment source code comes from `ck.db`** (`scripts.source_text` via
   `db.get_script_source`) — the old script mount (`testsuites_art/` etc.) is retired
   and no longer read (2026-07-21; guarded by `tool/guard_db_only.py`).
   **Resolver boundaries (2026-07-27, D1):** `_resolve_symbol_code` bounds every symbol
   (TestSet / TestCase class / helper fn) by its exact index `loc` — `_resolve_end`
   falls back to *next-unit-start − 1*, then `loc_total`, replacing a blind `loc[0]+60`
   that over/under-captured ~18% of `test_case` entries (all in the `legacy` DB, whose
   index carries a null `loc[1]`). Helper symbols resolve by their real `loc` too (the
   former stop-at-next-`def` regex mis-sliced nested defs). One resolver, not per-DB —
   `db.py` already normalizes all three script DBs to one schema. No `ck.db` rebuild.
   **Py2→Py3 fragment translation (2026-07-27, D3):** a reused fragment from a Python-2
   legacy script is deterministically modernized at resolve time via stdlib `lib2to3`
   (`_translate_py2`). A `status="translated"` result **is guaranteed valid Py3** —
   `expandtabs(8)` fixes Py2 tab/space mixing and an `ast.parse` self-check degrades a
   still-invalid result to `parse_error` (ship the original, never a broken half-fix).
   Untranslatable Py2 code ships as-is with a ⚠ PYTHON 2 preview banner **and** a
   *conditional* modernize rule injected into `pt_generate_script.jinja` (present only
   when a `py2_flagged` fragment is selected — zero prompt weight otherwise). Translated
   blocks carry a `(py2→py3)` provenance-tag suffix so a reviewer knows the code is not
   byte-identical to the cited source lines. (Old-framework/pre-`framework` idioms are a
   separate, fuzzier set left to the reviewer — `lib2to3` addresses Py2 syntax only.)
   *(Former step 4 **Fit Decision** was **removed** 2026-07-23 — with the fixed skeleton
   template the reuse/extend/new call no longer changes how the script is framed. Internal
   `stepN` keys are unchanged, step5=fragments etc.; only the visible sidebar numbers shifted.)*
5. **Generate** — the LLM **fills a standardized skeleton** rendered from the reviewed
   sequence (`templates/pt_script_template.py.jinja`), not a free-form compose
   **Naming survives the page and the call (2026-08-31).** `step6.naming` had exactly two
   writers — the SUCCESS tail of `generate_script`, and `save_script`, which 409s until a
   generated file exists. So before a first successful generation nothing would store the
   Group / script-name fields at all: an edit lived only in the DOM, and
   `renderPtGenPanel`'s `naming.group || group_display` re-seed silently restored the
   default whenever the panel was navigated away from and back. Two changes: a new
   **`POST /api/pytest-create/save_naming/{key}`** persists the two fields alone with no
   file required (autosaved on blur; it refuses once a script exists, because the rename
   then has to move the file on disk and re-lint it — `save_script`'s job, and half-doing
   it would strand the old file), and `generate_script` now persists the naming **before**
   the LLM call so a timeout or a failed reassembly no longer discards it. The pre-persist
   is skipped on `dry_run`, so Refresh stays a pure preview.
   **`_group_display` sanitises to the charset the validator accepts (2026-08-31).** It is
   both the value the browser seeds the Group field with and `generate_script`'s own default
   when the body carries no group — and it previously stripped only the `(42)` count, so a
   group whose label contains a character outside `_GROUP_RX` produced a default the
   server's own validator then rejected with 400. `Authentication & Security (42)` →
   `Authentication_Security`; that was the default for all 42 cases in the group, not one.
   A group that already validates is returned byte-for-byte unchanged, so existing
   `generated/` directories are untouched.
   (2026-07-21). Fixed frame: header, `TestSet(ATTestSet.TestSet)` with **data-driven
   `init`** (switches/stacks/portlink detected from the sequence + fragments),
   `configure()`/`tear_down()` (suite setup/cleanup — **no** pass/fail), one
   `TestCase_<n>` **per verification step** (each with the three `testCase*` attrs, a
   `main()` carrying the mandatory **logging contract**, and a per-case `tear_down()`),
   and the `__main__` footer.
   **Topology contract + minimality (2026-07-30).** `init` no longer names devices or leaves
   the port link to a FILL slot. It resolves the DUT from the bench's own role contract
   (`misc.get('ck_role_dut', 'swi_a')`, read from the `.setup`'s `[misc]` at run time) and
   binds its single link through the fixed-frame `self._ck_bind_link(setup, dut, misc,
   '<role>')`, which resolves `ck_link_<role>` on that bench, refuses a `(None, None)`
   portlink, and **asserts the bound port's media** via a shipped `ck_media.py`. Generation
   itself still reads **no** bench file — it targets the contract, because a bench-reading
   generator would silently weaken a test to fit the hardware present. Spec:
   `ask-ck/pytest-create/TOPOLOGY-PROFILES.md`; checker `tool/pt_profiles.py`; script-level
   check `tool/pt_preflight.py`. **`tests/test_pt_preflight.py` asserts over the real
   `generated/` tree, so what counts as a generated TEST SCRIPT matters (2026-08-31):** it
   globbed every `*.py` under `generated/`, which swept in both the `library` companion the
   generator writes beside a script (a helper module binds no devices, so it read as "no
   devices detected") and the `.meta/**/history/iter-N/` snapshots of superseded iterations
   (a draft regenerated *because* it was wrong would redden the gate forever). It now
   excludes `.meta/` and selects on the skeleton's own shape — a `class X(ATTestSet |
   ATTestCase)` — rather than on the filename, because the library's name comes from the
   MODEL (`_persist_generated_files` validates it for safety, not for a prefix). That rule
   also keeps the hand-made `.REVIEW.py` in scope, which a sidecar-meta rule would drop. An
   assertion fails loudly if the filter ever matches nothing, since a silently empty set
   would turn every assertion in the file into a vacuous pass.
   **Minimality:** the bound device set is now a *consequence* of the topology — one link ⇒
   exactly one partner, and the partner **is** that link's far end, so there is no second
   `init_swi()` to over-declare with. Names inferred from the selected fragments' vocabulary
   beyond that are dropped with a `# NOT BOUND:` comment. Previously the device set was fixed
   at render time, before any body existed, so it could only over-bind (T33235 bound 4 devices
   and 2 links while referencing 1 of each, which made the script demand cabling for nothing).
   Two lints enforce it: a direct `setup.init_portlink()` outside the helper is an **error**
   (it skips the media assertion), and using a device `init()` never bound is an **error**
   (`self.linkP.cmd(...)` compiles, then dies with `AttributeError` mid-bench-slot).
   **Objective header (2026-07-29):** the refined case objective is rendered into the skeleton
   as a `# ==== OBJECTIVE ====` comment block (`_objective_comment_lines` in `pytest_create.py`),
   so it rides into **both** the generated `.py` artifact and — because the Generate prompt
   embeds the skeleton — into the prompt itself (single source, no duplication). Generate-prompt
   **rule 1a** then directs the model to ground each `passed()`/`failed()` in the slice of the
   objective its step covers, not the per-step action/verify text alone. Port-literal lint skips
   comments so the header is safe; `>>>` is sanitised out of the objective text.
   **Step-kind taxonomy (2026-07-23):** the Sequence extractor classifies every step as
   one of **setup / verify / physical / manual** (`_step_kind` is the single classifier;
   `_split_sequence` is non-mutating). The skeleton branches on kind: `setup` →
   `TestSet.configure()` (no pass/fail); `verify` → normal CLI-driven TestCase; `physical`
   → a TestCase that **prompts the operator then polls `show interface … status` for the
   port state change** (SVT 3009 `waitForReplugEvent` pattern — plug/unplug/hot-swap steps
   are **in scope**, not skipped); `manual` → a TestCase with a `yesNo()` operator
   confirmation (LED/seating checks the device can't self-report). `import time` /
   `strtobool` / the `yesNo` helper are emitted only when a physical/manual step is present.
   *(Physical classification only appears after re-running Sequence on a case with such
   steps; legacy sequences with no `kind` default every step to `verify`.)*
   **Known limitation — `kind` misclassification (2026-07-29):** because the skeleton routes
   deterministically on `kind`, a mis-classified step is unrecoverable at Generate. A 5-model
   matrix graded T33234 (MDI/MDI-X) **10/10 "bad"** across every model: the extractor put the
   *per-case* partner-polarity reconfigs in `setup` (so they collapse into one-time `configure()`
   and the forced-polarity matrix never varies) and marked the *physical* cable-swaps `verify`
   (so the models faked them with DUT-side CLI = false green). Fix belongs in Sequence
   extraction, not Generate — tracked in `ask-ck/ck-facelift/PLAN-permutation-expander.md`.
   The prompt (`pt_generate_script.jinja`) instructs the LLM
   to fill the FILL slots with the reused fragments + gap-fill and to keep the three
   logging-contract calls. The prompt also mandates **deleting** each `# >>> FILL … <<<`
   scaffolding comment once its slot is filled; because model compliance is
   non-deterministic, `_parse_generated_blocks` **also strips** any residual
   `>>> FILL/replace/remove` pure-comment lines server-side (`_strip_fill_markers`) so a
   marker can never survive into a saved/linted/run script (2026-07-21).
   **Provenance re-stamp is now authoritative AND correct (2026-07-23):**
   `_restamp_provenance` strips whatever the model self-reported and stamps each `main()`
   from the server-known step→fragment mapping (`# ART/SVT/legacy <id> <lines>` for reused,
   `# AI <model> <date>` for gap-fill). It now takes the `sequence` and remaps
   original-step-number → `TestCase_<n>` class number before stamping — fixing a divergence
   bug where a dropped setup step shifted the class numbers and the wrong fragment's tag was
   stamped on the wrong TestCase. Edit the **Group / Script name**
   (`generated/<Group>/<Name>.py`), review/edit, **Lint** (py_compile + structure +
   framework-import + **template/logging-contract conformance**: each `main()` needs a
   `self.log()` and ≥1 non-empty `passed()`/`failed()`, no empty verdicts, no leftover
   FILL placeholders), **Save**, Confirm.
   **Stack + management-port hazards (2026-07-28, added after a live 8-member x950 run):**
   two further warnings. (1) `interface eth0` under config — eth0 is the out-of-band
   MANAGEMENT port (`show interface eth0 status` reports `Vlan: none`; it belongs to no
   VLAN and sits outside the switching fabric), yet it still appears in
   `show interface status`/`brief` as an ordinary connected row, which is how it gets swept
   into a port test. (2) A loop that enumerates interface rows from device output and then
   DRIVES the device with no `stackport` exclusion — on a stack, `show interface status`
   lists the stack links themselves with `stackport` in the Vlan column, so such a loop can
   shut one and **split the stack mid-run**, which then reads as a product failure rather
   than a test bug. Both key off the code shape, not the case text, so they fire whether or
   not the case is "about" stacking; both are silenced by the correct fix. See
   `ask-ck/pytest-create/{TEMPLATE-SPEC,LOGGING-CONTRACT,PART2A-WALKTHROUGH}.md`.
6. **Run** — pick a stored testbox from the dropdown (or ➕ Add new testbox…), pick
   the `.setup` (schema + a real worked example:
   **`ask-ck/pytest-create/SETUP-FILE-REFERENCE.md`** — it declares stack membership
   `[stack]`, the ports a test must never touch `[configured_stackport]`, and the testbox
   NIC ↔ switch port cabling `[portlink] tb-swi_X = ethN-portA.B.C`; these are DECLARED
   there and must never be inferred from case text), **Check Connection**,
   **Run on Testbox**. The script + setup go over
   SSH/SFTP, run as `sudo python3 <script> -s <setup> -v`, and the framework `.log`
   comes back and is parsed into per-TestCase PASS/FAIL. **The testbox framework dir
   (`framework_path`, default `/home/st-art/framework`) is READ-ONLY** — `pt_exec.py`
   refuses any SFTP write or remote command that would mutate it (guarded by
   `tool/guard_framework_readonly.py`); copy a framework file into the run workdir to
   edit it. See the run-chain reference `ask-ck/test-composer/ART-EXECUTION-CHAIN.md`.
7. **Validate** — Final Validation = run done + every case PASS + zero failures +
   exit 0. On failures, **Fix with LLM** revises the script (previous iteration is
   archived), which un-confirms steps 5-6 (Generate/Run) so the revision is re-reviewed
   and re-run — the fix path also re-stamps provenance with the corrected sequence remap.
   On all-PASS, Confirm step 7; promotion into `testsuites_art/` stays manual.

**Testboxes** (sidebar) — stored connection profiles kept in the gitignored
`secrets.testboxes.json` (0600). Passwords are write-only; the API returns `has_password`
only. Passwordless sudo on the box is required (probed by check).

*Required* is `name`, `tb_number`, `host` and **`user`** (`PROFILE_REQUIRED` in `pt_exec.py`).
`user` deliberately has **no default**: it used to default to `st-art`, which is wrong on at
least one live bench, and because a bad username fails at the SSH layer it presents as a
network or testbox fault rather than a profile mistake (2026-09-01; TESTBOX-ACCESS §3a).
Everything else — port, auth method, key path, password, framework path, remote workdir —
has a working server default and lives under **Advanced** in the panel; a field left blank
is omitted from the request rather than sent, so a profile never freezes today's default.

`setups` is a **named map**, `{name: remote_path}`, with as many entries as you like and
**no "default" key**: the panel writes the name its author typed and reproduces it verbatim
on edit. Before 2026-09-01 the form wrote every setup under the literal key `default`, which
silently renamed whatever was stored — on a LAN-shared server that let the last person to
save name everyone else's setup. Setups are **optional**: the Run panel lists every entry and
also takes a free-text remote path, so requiring one would only make the profile creator's
file everyone's de-facto default under another name.

**Building the script index** — ⚠ **Historical / provenance only.** The script index,
literal source code, code chunks, and framework surface now live in **`ask-ck/var/ck.db`**
(the permanent single source of truth); the runtime reads only the DB (`db.search_scripts`,
`db.get_script_source`, `db.get_json_doc("framework_surface")`). The AST-pass builder below
describes how the index was originally constructed from the script mounts — those mounts are
retired and the courier files (`scripts_index*.json`, `scripts_sources.jsonl`,
`framework_surface.json`) deleted. Kept only to document provenance; not part of the running
system.
```bash
cd tool
./build_script_index.py --mechanical-only   # (historical) AST pass over the script mounts + framework surface
./enrich_script_index.py --limit 100        # (historical) resumable LLM tagging/summaries
./build_script_index.py                     # (historical) rebuild with enrichment merged
```
`GET /api/pytest-create/status` reports the DB-backed script count + enrichment %.

**Generated artifacts:** `ask-ck/pytest-create/generated/<Group>/<Name>.py`, with
per-test provenance, sequence, iteration history, and run logs under
`generated/.meta/<Group>/<Name>/`. Generated scripts carry **inline source-provenance
tags** on reused blocks (`# ART/SVT/legacy <id> <lines>`) and gap-fill (`# AI <model>
<date>`), so a reviewer can trace any block back to its origin script + lines or to the
model that synthesised it.

**Session persistence:** `CK_server/sessions/pt-<KEY>.json` (separate from wizard
sessions). Confirming step N invalidates all later confirmations. Runs interrupted
by a server restart are marked `stale` on the next load_case.

### Per-unit generation — token-efficiency changes (2026-09-07)

Seven of the eight decisions in `TOKEN-EFFICIENCY-REPORT-2026-09-04.md` §6 were built on
2026-09-07 (Terrence: "change everything possible now, test it once"). All of them live in
`routers/pytest_create.py`, `templates/prompts/pt_generate_step.jinja` and the new
`pt_fix_unit.jinja`; each has its own test module (`tests/test_pt_prompt_split.py`,
`test_pt_fanout_prime.py`, `test_pt_shared_appendix.py`, `test_pt_fix_units.py`,
`test_pt_lint_integration.py`, `test_llm_task_routing.py`).

- **The unit prompt is two blocks (decision 8).** Everything identical across a case's units —
  intro, Case, framework surface, device handles, fill rules, the self-contained-unit rule,
  the shared fragments/CLI entries — renders above a visible split marker and is sent as the
  **system prompt**; the unit's own half is the user turn. The reviewer still sees and edits
  one prompt; an edit that drops the marker is sent whole (correct, uncached). The two flags
  the fill rules branch on (`py2_flagged`, `cli_reference`) are answered once per CASE for
  this template so the shared half is byte-identical across units. Why: see the transport
  bullet above — the cache matches only at block boundaries.
- **Primed fan-out (decision 4).** `generate_units` runs the FIRST unit alone to completion,
  then fans the rest out under the existing 8-wide semaphore (`_dispatch_primed`). A cache
  entry is readable only after the request that wrote it has been processed, so eight units
  fired at once all write and none reads. Costs one unit's wall clock (40–120 s) before the
  pills move; the status line says so and names the primed unit.
- **Self-contained units (decision 3).** The shared half tells every unit that nothing another
  TestCase configured is still in effect when its `main()` starts, so it establishes its own
  precondition and undoes it in its own `tear_down()`. 6 of 38 T44297 units failed for this
  reason alone. Per-unit template only — whole-script generation may legitimately chain cases.
- **Shared appendix (decision 5).** `_shared_plan` (once per generation context) hoists every
  fragment and CLI-reference command used by at least half the units (`_PT_SHARED_MIN_SHARE`)
  into the shared half; each unit names by tag which shared items apply to it and carries only
  its own remainder. On T44297 fragments were 27% of prompt text and the four used by ≥ 23/38
  units were 63% of fragment bytes. Single-unit cases share nothing.
- **Per-unit Fix (decision 7).** `POST /fix_units/{key}` sorts every current reason to fix —
  lint errors, review findings, the last run's failing cases with log excerpts — onto units by
  class name, line range or sequence step (`_fix_reasons`), re-syncs the chunks from the
  on-screen script so hand edits survive, re-generates ONLY those units (each prompt = the
  generation prompt + a `pt_fix_unit.jinja` addendum, so the same cached system half is read),
  primed and concurrent, then re-assembles through the one assembly implementation
  (`_assemble_and_store`, extracted from `assemble_script`) and records the outcome in
  `step6.fix_units`. Findings that name no unit are returned as `unmapped`; the whole-script
  Fix stays for those. UI: "⤺ Fix units (LLM)" on the Summary and "Fix units (LLM, from
  failures)" on step 7; the pills carry progress and the Summary refreshes when the last
  unit lands.
- **Two-tier Review (decision 7).** `review_script` refuses (409) while lint has BLOCKING
  errors: the deterministic pass goes to green first. Policy errors (`_POLICY_LINT_MARKERS`)
  and style warnings do not gate.
- **Bench-integration lint (decision 2).** `_lint_bench_integration`, inside
  `_lint_generated`: (1) a port attribute `init()` never assigned (`dut.portA` when it bound
  `dut.portB` only — reported once per class so the per-unit Fix reaches every affected unit;
  it follows local aliases such as `dutA = self.testSet.dutA`, which is how nearly every unit
  is written — chain-only it saw 12 of ~26 reads; on the real T44297 scripts it finds the
  unbound `tb.ethA` read in almost every capture unit, because the frame binds the far port
  as `self.ck_far_port`, not as `tb.ethA` the way the corpus scripts' `init_portlink` did);
  (2) a method the framework class does not
  define, or a keyword its signature rejects, judged against the `framework_surface` document
  in `ck.db` by handle kind (`init_swi` → Switch, `init_stk` → Stack, `init_tb` → TestBox, a
  `_ck_bind_link` partner → either); (3) a capture started and stopped with nothing between.
  1 and 2 are errors, 3 a warning.

### ART suite shape — frame, prompt, verdicts, library (2026-09-07)

Six ART scripts read whole plus a census over all 188 (2,085 TestCase classes) showed eight
places where the generated frame and prompt diverged from how ART suites are actually written,
and Terrence asked for all eight closed in one pass. What changed, and why each:

1. **The frame binds the TESTBOX link** `(dutA.portA, tb.ethA)` (profile `tblink`) whenever the
   case captures, injects or measures traffic (`_detect_links`). 111 of 188 ART tests bind
   exactly that and both models wrote `tb.ethA` in every capture unit while the frame had
   bound nothing on the testbox — the 60-error unbound-port flood on T44297 was frame-caused.
   `_ck_bind_link` takes the testbox end without `init_swi`; media role `tb` has no media
   requirement (`tool/pt_media.py`).
2. **The neighbour switch is `peer`, ports `dutA.portPeer` / `peer.portDut`.** ART reserves
   `dut` for the DUT's own stack handle; a partner called `dut` made every model read
   `dut.portA` as the DUT port. Any habitual `portB` / `ck_far_port` read is now a lint error
   instead of a silent wrong port.
3. **Every TestCase renders `configure()` / `main()` / `tear_down()`** (172 / 148 of 188 ART
   tests). The precondition a step presumes goes in `configure()`, its mirror in `tear_down()`;
   a verdict in either is a (policy) lint error. This makes the self-contained-unit rule the
   natural shape rather than a paragraph of prose.
4. **Every method opens with the ART shortcut block** (`tb = self.testSet.tb`, `dutA = ...`,
   `ethA = tb.ethA`, `portA = dutA.portA`, ...), emitted by the frame; the prompt's handle
   section now lists the bound LINKS (`_skeleton_bound_ports`, read back off the frame) and
   says the shortcut names are the complete list of what exists. The per-unit prompt also
   passes `bound_devices` into the included fill rules, which it had not been doing.
5. **Checkpoint verdicts are allowed.** LOGGING-CONTRACT §3 and TEMPLATE-SPEC C6 said
   "exactly one determination"; the corpus emits several per `main()` (3,372 passed / 4,947
   failed over 1,794 mains) and the parser always accepted ≥ 1. Rule 1 now says at least one
   per path, checkpoints named for what was observed, `return` after a fatal `failed()`.
6. **Class attributes:** `testCaseMethod` is the ART `=` / `+=` multi-line form; no
   `testCaseExcl` / `testCaseIncl` are generated (platform lists are hardware-verified, never
   inferred — rule 3d), and the run-time gate is the ART idiom `self.supported = False`.
7. **A suite library** `library_<case>.py` (`_build_library`) holds every selected fragment
   that is a stand-alone function, class or constant, verbatim under its provenance tag, with
   its source's imports; the frame imports it with `*`; it is stored as `files.library`, so
   `_persist_generated_files` writes it and the run ships it, and the lint compiles it. Units
   are told to CALL these, and they leave the per-unit and hoisted fragment sections. Two
   exclusions, both found on the real T44297 selection: a fragment that DEFINES a class the
   framework surface already has (the legacy `lldp_class.py` copies of the ATPackets layers)
   is not shipped — it would shadow the real layer and every `haslayer()` would fail silently
   — and the prompt names it as "already imported"; a member whose default argument or
   module-level value names something the library cannot resolve (`csvName = defaultCsvName`)
   is skipped, because that is evaluated at import and would kill the suite before case 1.
8. **`framework.ATPackets` is rendered as scapy LAYERS with FIELDS** mined from the corpus
   (`db.script_layer_fields`: `pkt[lldp_cap_tlv].lldp_med_cap` ...), and the frame imports the
   module whenever the testbox link is bound. Both models had hand-parsed TLV bytes; ART
   decodes with `pkt.haslayer(lldp_cap_tlv)`. Method args are shown for TestBox / Eth /
   SwitchPort / TestCase.

Tests: `tests/test_pt_art_shape.py` (32). The whole-script prompt snapshot was regenerated
knowingly (design docs read and revised first).

## Migration from Original Single-File Tool

- The original single-file `index.html` and `build_drafting_tool.py` logic (wizard UI, session model, selection tables, confirm buttons, export generation) has been migrated/adapted.
- Old static files remain in `CK-main/` for reference.
- The server version adds LLM synthesis, backend enforcement of the process, templated repeatability — and (2026-07-13) the Ask CK multi-tool shell.
- Output artifacts are drop-in compatible with the existing `refined-cases/` layout and `tool/upload_refined.py`.

## Adding a New Tool (Ask CK pattern)

1. **Frontend** (`CK_server/static/index.html`): add a `.card.tool-panel` div with a unique panel id, a `PANEL_META` entry (title/desc), and a sidebar nav item with `data-panel="<panel-id>"` + `onclick="goToPanel('<panel-id>')"`.
2. **Backend**: add `CK_server/routers/<tool>.py` (plain `APIRouter`), then `include_router(..., prefix="/api/<tool>")` in `main.py`.
3. **Assets/data**: use the matching `ask-ck/<tool>/` directory (mirrors how `objective-drafting/` backs the Generator).
4. Do not touch the Generator's numeric step scheme (`data-step`, `step-N` ids, `stepN` session keys, `confirm_step` 1–3).

## Development Notes

- Most logic is in `CK_server/`.
- To iterate on prompts: edit the `.jinja` files and restart (or use `--reload`).
- To iterate on the UI: edit `static/index.html` (no rebuild step).
- The wizard still supports manual editing of objectives/steps after LLM synthesis.
- Session state is file-persisted under `CK_server/sessions/`.
- Full prompt + LLM response is captured in the exported session JSON for auditability.

## Security Posture (hardened 2026-07-27c–g)

Ask CK is designed for **localhost / single-user** use (a shared multi-tenant deployment is
explicitly out of contract — see *Known Issues*, and the multi-user plan at
`ask-ck/ck-facelift/PLAN-auth-and-case-locking.md`). A full adversarial review (2026-07-27)
hardened the boundaries so untrusted/LLM-derived input can't escape its lane even so.

> **Review closed 2026-07-27g.** All 62 candidate findings are resolved: 31 fixed, 31 dismissed
> as not-real after tracing them against live code. The full record — including *why* each
> dismissal is not a bug, so they are not re-raised — is
> `ask-ck/pytest-create/ADVERSARIAL-REVIEW-BACKLOG.md`.

### Concurrency + case locking (Phase 1, 2026-07-29)

Two people — or one person in two browser tabs — could open the same case and silently
overwrite each other: every persist was an unconditional whole-blob write, so the second save
won and the first person's work vanished with no error. Phase 1 of
`ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` closes this for **both** tools.

- **A per-(tool, case) lock** (`CK_server/locks.py`) is acquired on `load_case`, heartbeated
  every 5 min, released on tab close (`navigator.sendBeacon` on `pagehide`), and idles out after
  15 min so an abandoned lock can be taken over. Held by the per-tab `X-CK-Session` id (Phase 2
  will make that a real user). Endpoints: `POST /api/locks/{kind}/{case_key}/acquire|heartbeat|release`.
- **Enforced at the two write choke points only** — `session_store.persist_session` and
  `pytest_create._pt_persist` — which raise a 409 if another holder owns a live lock. A
  `tests/test_no_unguarded_session_write.py` AST sweep proves no other code path writes a session.
- **Read-only while locked (not refused):** loading a case someone else is editing shows a
  banner ("held by … since HH:MM") and disables the step inputs; the case content still displays.
- **Optimistic `rev` backstop:** a monotonic `rev` in the session payload JSON is compared-and-
  swapped on every write, so even a stale copy after a restart — or a second server process (the
  window `pytest_create._pt_get` documents) — cannot clobber newer work.
- **This is NOT authentication.** `X-CK-Session` is a correlation id, not a credential; the lock
  is a data-loss guard. Identity (D1/D2) is Phase 2.

> ⚠ **Single-process assumption.** The lock registry is an in-memory dict, authoritative because
> the server runs as ONE process (`uvicorn … --reload`, no `--workers`; the nginx example proxies a
> single upstream). ck.db is immutable by design (`tool/build_db.py` refuses to rebuild; no
> migration path), so a durable lock table was deliberately not added. **If the server is ever run
> multi-worker/multi-process, promote the registry to a shared store** or the overwrite bug returns
> silently — the `rev` backstop is then the only remaining guard. See `locks.py`'s module docstring.

- **No secrets to the browser or disk.** `llm_config.api_key`/`token` are redacted from every
  session serialized to the client and from the exported `*-session.json` (`models.redact_llm_config`
  / `safe_session_dict`). The real key lives only in the server-side session store; the vLLM key
  stays in gitignored `secrets.local.json` (never in a session at all). `GET /…/session/{key}` and
  all wizard step responses return redacted configs.
- **Objective HTML is sanitized server-side.** The Generator objective is rendered raw via
  `innerHTML`, so `html_sanitize.sanitize_objective_html` (stdlib allowlist — tags only, no
  attributes, drops `script`/`style`) runs at **every** objective store point (synthesize / save /
  confirm / backfill / export). Defends against stored XSS from prompt-injected or garbage corpus text.
- **PyTest run command is injection-safe.** The `-s <setup>` remote path is metachar-validated at the
  `/run` endpoint and every interpolated component of the SSH exec string is `shlex.quote`d
  (`pt_exec.py`). The **framework-read-only guard** (`_assert_command_allowed`) refuses redirection
  (`>`), inline interpreters (`python -c`), command substitution, `rsync`/`install`, and
  `cp --target-directory` whenever the framework dir is referenced — not just a verb denylist.
- **No path traversal on writes.** The export `case_key` is validated against `^AWPTCM-T\d+$` at the
  top of the handler (before any write), and generated library filenames are validated as a bare
  basename — so neither can escape `refined-cases/` or `generated/`.
- **Agent-bridge is session-bound.** Broker jobs carry their owning `X-CK-Session`; `/api/agent/result`
  rejects a `job_id` that belongs to a different session, and `/next` binds to the header (query param
  is a legacy fallback). **CORS** is locked to a localhost allowlist (`CK_ALLOWED_ORIGINS` to widen).

### Data-integrity + correctness hardening (2026-07-27g, batches A–D)

The completion pass fixed 19 further findings. The ones that change observable behaviour:

- **Export writes only authoritative, confirmed, consistent state.** `/export` resolves the session
  server-side ONLY (404 if absent — it no longer falls back to the client's copy, which let a stale
  tab resurrect a deleted session), requires all three DB reviews confirmed (400 otherwise, matching
  every sibling synthesis endpoint), and writes the bundle atomically — staged to `.tmp` then
  `os.replace`d, with `zephyr_payload.json` **last** so the Complete marker is the final commit point.
- **Changing an upstream review invalidates downstream work.** `confirm_step` on steps 1–3 with
  *different* selections now un-confirms the objective and marks the test steps stale (amber
  "⚠ Stale — selections changed" badges); re-confirming the same shortlist does not. Previously both
  stayed green and export produced a bundle whose payload contradicted its own traceability.md.
  Backfilled Complete cases are marked confirmed from the on-disk bundle so legacy re-exports still work.
- **No blocking work on the event loop.** All seven search/LLM call sites now use `run_in_threadpool`.
  The sharpest was `export`'s coverage-gaps call: in `claude_agent` mode it was a *guaranteed* 180s
  self-deadlock (the blocked loop cannot serve the `/api/agent/result` POST that would release it).
  The embedding model is warmed on a daemon thread at startup (~7s in the background) so the first
  hybrid search no longer pays a ~16s cold load. Opt out with `CK_NO_EMBED_WARMUP=1`.
- **Generated content is no longer silently dropped or corrupted.** The traceability-note strip is
  anchored (an unanchored `"Traceability" in …` was deleting legitimate first steps, and the payload
  validator passed it, so cases exported a step short with no warning); the skeleton renderer escapes
  step text via a `pyliteral` filter (typed newlines/backslashes used to produce an **uncompilable**
  skeleton); provenance tags no longer mis-attribute setup-mapped fragments; and the provenance-echo
  strip matches the tag shape rather than any comment mentioning ART/SVT/legacy/AI.
- **Errors are reported as errors.** The Claude branch now guards empty and truncated responses like
  the OpenAI branch; the two frontend `fetch`es that lacked `res.ok` no longer render an HTTP error as
  a green success (or wipe the in-memory session); `keep_ids` are pinned through the hybrid RRF merge;
  restart-orphaned testbox runs are re-marked stale by the polling endpoint, not only on case load.
- **Streamed LLM output is UTF-8.** SSE is `text/event-stream`, and `requests` maps any `text` type to
  ISO-8859-1 — so every non-ASCII byte on the live vLLM streaming path was mojibaked (`port — 1 µs`
  → `port â 1 Âµs`), silently and as valid JSON, flowing into stored objectives and on to Zephyr.
  `resp.encoding` is now pinned before iterating.

**Network posture (revised 2026-07-27g).** The server still has **no authentication** — that part of
the single-user model is unchanged and remains the reason not to expose it. What changed is that the
defaults now *match* that model instead of quietly contradicting it:

- **Binds `127.0.0.1` by default** (`run.sh`, and the `__main__` entrypoint). Exposure is now a
  deliberate `HOST=0.0.0.0 ./ask-ck/CK-main/run.sh`. Previously the default was `0.0.0.0`, so a
  documented "localhost" tool was in fact LAN-reachable — verified live during the review: an
  unauthenticated `POST /api/wizard/push_to_zephyr/{key}` answered 200 from the box's LAN address.
  `dry_run` is a plain query param defaulting `true`, so flipping it is one character; CORS is not a
  mitigation (it constrains browsers, not `curl`) and the UI's `confirm()` is client-side only.
- **`push_to_zephyr` no longer hardcodes `--force`.** It did, which disabled `upload_refined.py`'s own
  last safety net (*"already appears refined in Zephyr — SKIP"*) on **every** push, so any push could
  overwrite an already-refined live case. Force is now opt-in per request (`?force=true`); the UI does
  not send it.
- **SSH host keys are pinned trust-on-first-use.** `load_system_host_keys()` runs before
  `AutoAddPolicy`, so a *known* testbox whose key changes — what a MITM looks like — now raises instead
  of being silently accepted. New hosts still connect with no prompt. Escape hatch for a legitimately
  reimaged box: `CK_SSH_TRUST_ANY=1`. This item never really fitted the "localhost" rationale anyway:
  the connection is **outbound** to a lab testbox, so its exposure is independent of the web UI being
  single-user.

Still accepted, unchanged: **no authentication on any endpoint.** `HOST=0.0.0.0` alone is not a
safe configuration. Note `X-CK-Session` is **not** a credential — the browser tab invents it and
the server never verifies it; it is a per-tab correlation id for the agent bridge only.

**This is tracked work, not just a caveat:** `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md`
(multi-user identity + per-case session locking).

**Phase 1 — locking — is DONE (2026-07-29).** It closed a concurrency bug that did not need a
second user: session writes are unconditional whole-blob overwrites keyed by case with no owner,
so two tabs editing one case silently destroyed each other's work. `CK_server/locks.py` now holds
a lock per `(tool, case)`; a tab that does not hold it gets a **read-only view** of the last saved
state rather than an error, and the handler mutates nothing on that path. An optimistic `rev`
compare-and-swap (`locks.next_rev`, applied at both persist choke points) backstops the window an
in-memory lock cannot cover — a restart, or a second process.

Two deliberate deviations from the plan's §4 design, both forced by the `ck.db` invariant: the
lock registry is an **in-process dict, not a table**, and `rev` rides **inside the session payload
JSON, not a column** — a durable `case_locks` table would have been the repo's first in-place
schema mutation of the permanent database. **The registry is authoritative only because the server
runs as one process** (`uvicorn … --reload`, no `--workers`; the nginx example proxies a single
upstream). Running multi-worker without promoting it to a shared store **silently reintroduces the
overwrite bug** — `locks.py`'s module docstring carries the same warning.

Phases 2 (identity) and 3 (attribution + TLS) remain **planned**, gated on the organisation's
identity decision.

## Testing

Three test layers, one regular gate (established 2026-07-27). Design: `ask-ck/ck-facelift/`
`PLAN-frontend-unit-tests.md` + `PLAN-playwright-e2e.md`.

**1. Backend units** — repo-root `tests/` (pytest, in-process `TestClient` — no mocks, network, or
testbox). Coverage centers on the security/correctness fixes (validator + export gate, the JSON
extractor, the framework guard, HTML sanitizer, secret redaction, path-traversal guards,
agent-bridge ownership, CORS) plus the `/process` page. The 2026-07-27g batches added suites for
export authority, event-loop blocking, silent content loss, error signals and the network hardening
— several are **structural** rather than example-based (an AST sweep asserting no async handler
calls a blocking function unwrapped; source assertions that a guard still precedes the state write),
so they catch the *next* regression, not only the one filed. `PYTHONNOUSERSITE=1` is required so an older
fastapi/starlette in `~/.local` can't shadow the venv's. Dev deps (`pytest`, `httpx`) in
`ask-ck/CK-main/requirements-dev.txt` (runtime `requirements.txt` stays lean).

**2. Frontend units** — repo-root `js-tests/` (Vitest + jsdom — no browser, server, or LLM; 85
tests). Covers the pure-logic ~80% of the frontend: the DOM/button-feedback helpers
(`setButtonBusy`/`flashButtonDone`/`showStatus`), the table renderers (`tables.js`), the
chosen-list machinery (`chosen.js`), and the candidate-merge logic (`db-search.js` `merge*`, made
`export` for this), plus the 2026-07-27g guards: the Step 4/5 "Stale" badge precedence and the
`res.ok` error guards. DOM fixtures are lifted from the **real `index.html`** and the helper throws if
a container id is missing — drift-detection, the same "ground selectors in the real DOM" discipline as
the E2E. Node dev deps in `package.json`.

**3. E2E (sparingly-run, NOT in the regular gate)** — repo-root `e2e/` (Playwright, one Chromium
project driving the real running app: boot → load a case → keyword-search TestLink/Zephyr/ATP →
tick + choose → Export → assert the validation gate blocks it). Deterministic (no LLM on the asserted
path — a green export needs synthesized objective+steps, so the honest assertion is the blocked
outcome). Run on demand, e.g. pre-release.

> **E2E runs against a THROWAWAY copy of ck.db, on port 8123** (`tool/run_scratch_server.sh`).
> `ask-ck/var/ck.db` going dirty is *correct* when a person operates the app — a case load persists
> a session row, and that is the tool working. A test doing it is worthless data landing in the
> permanent, LFS-committed source of truth. Until 2026-07-28 the Playwright `webServer` was
> `./run.sh --bg` with `reuseExistingServer: true`, so on a seat with the dev server already up it
> attached to *that* and wrote real session rows; the same thing happened via curl smoke checks, and
> three rows had to be discarded by restoring ck.db from git. Use the scratch launcher for anything
> that DRIVES the app as a test would:
>
> ```bash
> tool/run_scratch_server.sh --bg      # port 8123, throwaway ck.db copy, own pid/log files
> tool/run_scratch_server.sh --stop    # stops only the scratch server
> ```
>
> `/health` now reports `db.db_path` and `db.is_permanent_db`, so you can tell at a glance which
> database a running server is on. Guarded by
> `tests/test_test_traffic_never_writes_the_real_db.py`.

```bash
./tool/run_tests.sh        # THE GATE: guards + pytest (559) + Vitest (85), one command
PYTHONNOUSERSITE=1 .venv/bin/pytest -q     # backend only (559 tests, Python 3.13)
npm test                                    # frontend units only (vitest run)
npm run e2e                                 # Playwright E2E — sparingly, not the gate
```

`./tool/run_tests.sh` runs the two invariant guards (`tool/guard_db_only.py`,
`tool/guard_framework_readonly.py`), then pytest, then `npm test`; it **fails loudly** if npm is
present but `node_modules` isn't installed (a partial gate that silently drops a layer would falsely
read "all green"). There is **no CI runner yet** (`.github/workflows`) — running the gate before a
commit is the current discipline.

## Relation to the Approved Plan

See `ask-ck/objective-drafting/PLAN-server-backed.md` for the complete approved plan that this implementation follows (its paths are pre-restructure), and `ask-ck/ck-facelift/PLAN-facelift.md` for the 2026-07-13 multi-tool facelift plan.

The plan explicitly chose server-backed because:
- LLM is required for creation.
- Data will grow.
- Repeatable outputs via templating.
- Hosted behind nginx.
- Future extension is planned (now realized as Ask CK).

## Quick Reference Commands

```bash
# Start server (easiest)
./ask-ck/CK-main/run.sh

# With real key or different port
LLM_API_KEY=sk-... ./ask-ck/CK-main/run.sh
PORT=9000 ./ask-ck/CK-main/run.sh

# Manual start (project root)
LLM_API_KEY=sk-... PYTHONPATH=ask-ck/CK-main python3 -m uvicorn CK_server.main:app --host 127.0.0.1 --port 8000 --reload

# Test synthesis directly (Python)
cd ask-ck/CK-main/CK_server
PYTHONPATH=. python3 -c '
from llm import synthesize_objectives_and_steps
sess = {"key":"AWPTCM-Txxxx", "step1":{"selections":[...]},"step2":{...},"step3":{...},"gaps":"..."}
print(synthesize_objectives_and_steps(sess))
'
```

For the full approved plan, usage philosophy, and trade-off history, read `ask-ck/objective-drafting/PLAN-server-backed.md`.

This SERVER-README.md is the single source of operational instructions.

**For future sessions**: Start with `ask-ck/objective-drafting/PROGRESS.md`. It contains current status, completed work, open tasks, technical debt, prioritized backlog with effort estimates, and a handoff checklist.

Cross-reference higher-level project docs every session:
- Root `README.md` (project framing, quick start, the four invariants, the documentation map —
  navigational, **not** a status document)
- Root `CHANGELOG.md` (what changed, when, and why)
- Root `SESSION_STATE.md` (broader session history)
- Root `TESTBOX-ACCESS.md` (read in full before touching lab hardware)
- `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md` (the authoritative process this tool supports)

---

## Session Summary (2026-07-27g — adversarial review CLOSED: 19 fixes in 4 batches + network hardening)

Finished the verification that was paused at ~50% in 27c. Re-fired it over the 35 unadjudicated
rows (`wf_f4fcd274-366`, 40 agents: one verifier per file-cluster against live code, then a
refuting skeptic per confirmed finding). **21 survived, 14 dismissed**; 19 survivors fixed across
four themed batches, the two accepted-risk security rows taken to Terrence and actioned.

- **A `6b50f80` — export authority.** `/export` no longer accepts a client-supplied session (404),
  gates on the three DB reviews (400), invalidates stale downstream work on a changed selection,
  and writes the bundle atomically with the Complete marker last. Migration guard so the 43
  existing bundles stay re-exportable.
- **B `40ec299` — event-loop blocking.** Seven sites wrapped (the review named three; an AST sweep
  found four more, incl. `load_case`). Killed a *guaranteed* 180s `claude_agent` self-deadlock;
  added a background model warmup (cold load measured 16.2s, not the estimated 8.5s).
- **C `ba69e22` — silent content loss.** Anchored the traceability-note strip (it was deleting real
  verification steps that then exported as "valid"), replaced 13 fragile jinja slots with a
  `pyliteral` filter, fixed setup-step provenance mis-attribution, tightened the provenance-echo regex.
- **D `be9149d` — error signals.** Claude empty/truncated guards, two missing `res.ok` checks,
  `keep_ids` pinning through the RRF merge, stale run-status sweep, the never-called `gc()`.
- **Security `6eaa43e`.** Loopback by default, `--force` no longer hardcoded on `push_to_zephyr`
  (it was disabling the CLI's own "already refined — SKIP" guard on every push), SSH host keys
  pinned trust-on-first-use. Verified live: LAN address now refused, localhost serves 200.
- **Data `e54fdd2`.** `AWPTCM-T37861` shipped invalid JSON (a `\'` escape) since its first commit —
  the only one of 43. One backslash removed; all 43 now pass the export gate.

Two defects were found by skeptics **while refuting** other claims: the SSE latin-1 mojibake (the
most consequential correctness bug of the pass) and the inert Py2 prompt marker. Tests 48 → 190
pytest / 47 → 72 Vitest. Backlog closed as a historical record; multi-user auth + per-case locking
captured in `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md`.

## Session Summary (2026-07-27c–e — full adversarial review + 15 security/correctness fixes + test suite)

A full 14-domain adversarial review (workflow `wf_f53aa173-a88`; 62 candidate findings) drove three
fix batches, all committed + pushed (`1340d9b`, `a1608d5`) with in-process regression tests (no live
Zephyr / no testbox exercised):

- **Batch 1 (security/integrity):** SSH command injection, framework-guard bypass, stored XSS
  (new `html_sanitize.py`), secret leak (new `redact_llm_config`/`safe_session_dict` in `models.py`),
  admin-reset wrong session-kind, export step-0 overwrite.
- **Batch 2 (path-traversal + auth):** library-filename traversal, export `case_key` traversal,
  agent-bridge job-ownership (session-bound `deliver`), CORS lockdown.
- **Batch 3 (correctness):** unified 5 `llm.py` JSON-parse sites behind one string-aware
  `extract_json_block` (fixes silent result-dropping from greedy regexes / braces-in-strings).

Also this session (earlier): reconciled the stale backlog + cleared 4 quality items (in-page error
banners, export refuse-to-write hardening, `/process` anchor fix), and stood up the **first backend
test suite** (`tests/`, now 48 tests). See the **Security Posture** and **Testing** sections above,
`ask-ck/pytest-create/ADVERSARIAL-REVIEW-BACKLOG.md` (remaining ~40 candidate findings, verify before
fixing), and `PROGRESS.md` for the per-batch detail.

## Session Summary (2026-07-20, later — LLM-config bug, prompt trims, health check, provenance/dry-run)

Four pieces of work (all **uncommitted** at session end — Terrence commits himself):

1. **LLM-config bug (dangerous — fixed).** PyTest Creator LLM endpoints resolved `_llm_cfg` raw and only `load_case` applied the workspace login, so a stale/inactive session silently fell back to the default backend (`claude_agent`/`model=default`) instead of the configured `local_llm` — surfaced by the debug-log (a real T33233 `extract_sequence` recorded `auth=claude_agent`). Fixed by folding the workspace-apply into `_llm_cfg` (pytest_create.py) so every endpoint gets the right backend at dispatch. Audit found the **same latent bug in the wizard** (`_session_llm_cfg` + inline reads in suggest_atp/synthesize/coverage) — hardened `_session_llm_cfg` and routed all wizard LLM endpoints through it. `load_case`→analyze_atp was already safe.
2. **Prompt trims.** `pt_extract_sequence.jinja` −46% (dropped the traceability dump), `generate_steps.jinja` −51% (dropped selections — the finalized objective already carries them), `generate_objectives.jinja` −16% (dropped duplicate `process_principles`, raw `primary` dict, blank-line padding). Removed a **`(typically 4-10)` bullet-count anchor** that contradicted `OBJECTIVE_DRAFTING_PROCESS.md` ("not uniform"), plus the matching silent code caps (`bullets[:10]`, `ranked[:10]`, fallback `[:6]`) and the suggest/analyze selection caps — ranking now covers all relevant candidates; input-pool caps (`candidates[:20]`) kept as legit token bounds.
3. **Health check** (Configure page): `POST /api/wizard/llm_health` + `_health_ping` — minimal completion via the real path, reports `✓ up — <model> (ms) · N in / M out`. Both vLLM models confirmed healthy; earlier 500s were transient. Token badges relabelled from `17→179 tok` (ambiguous) to `N in / M out (total)` via a single shared `fmtTokens`.
4. **LLM Provenance + dry-run** (see the section above): every LLM panel gets a copy-able, live-refreshable prompt preview via a `dry_run` flag that renders 1-for-1 without sending. New file `static/js/provenance.js`; `main.js?v=…` bumped to 7.

Files touched: `llm.py`, `models.py`, `routers/{wizard,pytest_create}.py`, `static/index.html`, `static/js/{provenance(new),generator,pytest,db-search,llm,llm-debug,main}.js`, `static/styles.css`, 4 prompt templates. Memory: `pytest-creator-llm-config-bug`, `llm-health-check-button`, `llm-provenance-portability`.

## Session Summary (2026-07-13, later session — Ask CK facelift)

Repo restructure support + multi-tool facelift (see `ask-ck/ck-facelift/PLAN-facelift.md`):

- **Repathing** after the `drafting-tool/` → `ask-ck/` restructure: new `CK_server/paths.py` anchors (DATA_DIR / REFINED_DIR / PROCESS_MD); fixed `data.py` (was CWD-relative), `wizard.py` refined-cases roots, `main.py` process page path, and `run.sh` (now `CK_server.main:app`). Boot-verified with full data (410 cases).
- **Ask CK rename**: page title, sidebar logo, FastAPI title.
- **Multi-tool sidebar**: LLM (+ **Configure** main-area panel — the relocated LLM Provider Login, all element ids preserved), Zephyr Templating Tool (4 stub steps), Test Composer (1 stub), PyTest Creator (Cases wired / Creator stub), Objective/Test Case Generator (visible steps renumbered 1–6, display-only).
- **Navigation**: `goToPanel(panelId)` primitive + `goToStep()` wrapper + `PANEL_META` page-header registry; ✓ nav-badges scoped to the Generator section.
- **PyTest Creator Cases**: independent dropdown fed by the same `/api/wizard/cases` fetch (later restricted to **Complete cases only**); selection isolated from the Generator (`ptCase` global).
- **Backend stubs**: `routers/zephyr_tool.py`, `test_composer.py`, `pytest_create.py` with `/status` endpoints (+ pytest `generate/{key}` → 501).
- Dead code removed: `showLLMConfig()`, `#llm-config-card`, phantom `#llmCredential` handling.
- Docs repathed across the repo (root README, PROGRESS, this file, LESSONS, BoS/EoS prompts, READMEs, SESSION_STATE entry).

See `PROGRESS.md` for the updated backlog (manual browser smoke of the facelift is the top item).

---

## Session Summary (2026-07-13)

Major usability and process refinements for the live wizard:

- **Verified** load_case zrefs folder fix; **relevance-ranked** external Zephyr cross-refs.
- **Dual case dropdowns** (Open/partial with in-progress first vs Complete via refined-cases payload).
- **Search + Suggest with LLM** on Steps 1, 2, and 3 (TestLink / Zephyr / ATP).
- **Gaps removed from Step 3 UI**; generated by LLM at synthesize/export for Traceability (`generate_gaps.jinja`).
- **Workspace LLM persistence** (`sessions/_workspace_llm.json`) so case switches do not reset CLI login.
- Fixed **stack overflow** (auth UI recursion) and **table layout** (6-column width collapse).
- Favicon; root/drafting-tool README cleanup; handoff docs refreshed.
- GitHub: history LFS migrate for Zephyr XML/jsonl so push succeeds under 100 MB blob rules.

See `PROGRESS.md` and `LESSONS_LEARNED.md` for backlog and detailed lessons.

---

## Session Summary (2026-07-03)

This session replaced a non-functional Claude auth flow and added real subscription-based auth options:

- Removed the "Subscription Account" login (it pasted a claude.ai "session token" as an `x-api-key`, which cannot authenticate `api.anthropic.com` — no such token exists for third-party use).
- Added **Claude Code headless CLI mode** (`auth_method: "claude_code"`): calls the locally installed + logged-in `claude` CLI (`claude -p --output-format json`) so Claude Team subscription seats work with no key/token stored server-side. Full frontend UI (Step 0 radio, "Check CLI Status" button, setup instructions).
- Added the equivalent **Grok CLI mode** (`auth_method: "grok_cli"`) on the backend (SuperGrok/X Premium+ via `grok login --oauth`) — no frontend UI yet.
- Fixed a bug where `suggest_relevant_atp`/`analyze_atp_coverage` would silently fall back under headless auth modes (which have no stored credential by design).
- Tested end-to-end with real CLI paths where possible.

This session: MOCK/demo removed (real-only); export now auto-persists to refined-cases; frontend polish (styles, summary, editor, generalization).

All changes stay under `drafting-tool/`. Use real LLM setup (CLI preferred).

See updated `PROGRESS.md` and `LESSONS_LEARNED.md`.


## Session State & Lessons Learned (2026-07-01, extended session; see later entries for MOCK removal + polish)

**Current State Saved:**
- Gating + file-based persistence implemented (routers, models with LLMConfig, sessions/*.json)
- Real multi-provider LLM (llm.py: Grok/Claude, api_key+account auth_method, provenance capture, improved parsing)
- UI fully restructured + design system integrated (sidebar+main from showcase, full tokens, .btn/.card/.section/.page-header/.badge/.form-*/.table, SVG icons no emojis, custom scrollbar+border, title in sidebar-logo, no top header bar, dynamic page updates, in-page login flow)
- Light/dark toggle integrated in sidebar
- Spacing fixes + reduced inline styles per design scale
- Full session state (incl. LLM config/creds/auth, selections, provenance) persisted to disk
- `drafting-tool/PROGRESS.md` + `LESSONS_LEARNED.md` updated with new status/backlog/lessons

**Implementation Snapshot:**
- State machine + file persistence (confirms+selections+LLM+step4+provenance)
- Multi-provider LLM + in-page account login (prepare/actuallyOpen no popup race)
- Design-aligned frontend (sidebar full-top, main with page-header/sections; components from showcase)
- Theme support, badges, form/table polish, SVG icons
- Backend APIs with enforcement + set_llm_config

**Lessons Learned (to carry forward):**
See extended `drafting-tool/LESSONS_LEARNED.md` (new entries on browser flows, exact design matching, persisted state value).

**Next Steps (from current):**
- Complete output generation (full zephyr_payload + validation)
- Frontend remaining polish (dynamic cases, previews, editor, full components)
- requirements.txt + setup, tests, error handling
- See updated `drafting-tool/PROGRESS.md` for priorities + handoff.

**Memory Commit:**
This extended session delivered gating+persistence, real LLM (multi-provider + auth modes + provenance), and major UI restructure + design system integration (tokens, layout, components, icons, structure per showcase). All drafting-tool work consolidated. Ready for output gen + polish.

(End of session summary – 2026-07-01)

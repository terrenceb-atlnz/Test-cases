# SERVER-README.md — Ask CK (Server-Backed Test Tooling Workbench)

This document contains **all instructions for use, setup, configuration, architecture, and details** for **Ask CK** — the server-backed workbench whose first (and mature) tool is the **Objective/Test Case Generator** (formerly "Objective Drafting Tool").

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
│       ├── routers/
│       │   ├── wizard.py            ← Generator API (/api/wizard)
│       │   ├── zephyr_tool.py       ← Zephyr Templating Tool stub (/api/zephyr-tool)
│       │   ├── test_composer.py     ← Test Composer stub (/api/test-composer)
│       │   └── pytest_create.py     ← PyTest Creator stub (/api/pytest-create)
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

`setup.sh` does this for you inside a repo-local `.venv` (see root `README.md` → Getting
Started). If using a real LLM provider you may need additional packages such as `litellm`
or the official SDK.

## Running the Server

The easiest way is the root `run.sh` (a thin wrapper that forwards to the real
launcher at `ask-ck/CK-main/run.sh`; either path works):

```bash
# With a real API key
LLM_API_KEY=sk-... ./run.sh

# Fast restart — prompt-free background start / stop+start
./run.sh --bg          # background, no prompts
./run.sh --restart     # --stop then --bg
./run.sh --stop        # stop the background server

# Different port
PORT=9000 ./run.sh

# Extra uvicorn options (e.g. debug logging)
./run.sh --log-level debug
```

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
LLM_API_KEY=sk-... PYTHONPATH=ask-ck/CK-main python3 -m uvicorn CK_server.main:app --host 0.0.0.0 --port 8000 --reload
```

Alternative (cd into the server dir):

```bash
cd ask-ck/CK-main/CK_server
LLM_API_KEY=sk-... PYTHONPATH=.. python3 -m uvicorn CK_server.main:app --host 0.0.0.0 --port 8000
```

**Environment variables for LLM**:

```bash
export LLM_API_KEY=sk-...
export LLM_BASE_URL=https://api.openai.com/v1   # or your Grok/Claude-compatible endpoint
```

Real LLM (API key or local CLI login) is required. MOCK/demo mode has been removed.

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

### LLM Provenance (portable prompts) + dry-run preview

Every LLM panel (Generator: objectives, steps, the 3 *Suggest* panels; PyTest Creator: sequence, script-search, fragments, generate) carries a collapsible **LLM Provenance** block (`static/js/provenance.js`, shared) with **↻ Refresh (no send)** and **Copy prompt / Copy response** buttons. Purpose: grab the exact prompt to paste into a competing LLM (comparative analysis / free-LLM fallback).

- **Refresh** re-invokes the panel's own endpoint with `dry_run: true`. The backend renders the prompt through the *real* context path and returns it **without sending** to the LLM — no tokens, not recorded to the debug-log. Because it reuses the real call path with one flag flipped, the previewed/copied prompt is **1-for-1** (byte-identical) with what a real send transmits — verified in-repo.
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
   - `POST /api/wizard/push_to_zephyr/{key}?dry_run=…` **shells out to `tool/upload_refined.py`** (flags `--fix-title --new-version --force`); the server never holds the JIRA token (the CLI reads it from `secrets.md`). It operates on the **on-disk bundle**, NOT a re-export — re-exporting from an incomplete/backfilled session would degrade `traceability.md`, so Export explicitly first if you edited.
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

## PyTest Creator (2026-07-14)

Turns a **Complete** case (one with a refined `zephyr_payload.json`) into a runnable
Allied Telesis framework test script. Full plan + progress tracker:
`ask-ck/pytest-create/PLAN-pytest-creator.md`.

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
   (2026-07-21). Fixed frame: header, `TestSet(ATTestSet.TestSet)` with **data-driven
   `init`** (switches/stacks/portlink detected from the sequence + fragments),
   `configure()`/`tear_down()` (suite setup/cleanup — **no** pass/fail), one
   `TestCase_<n>` **per verification step** (each with the three `testCase*` attrs, a
   `main()` carrying the mandatory **logging contract**, and a per-case `tear_down()`),
   and the `__main__` footer.
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
   FILL placeholders), **Save**, Confirm. See
   `ask-ck/pytest-create/{TEMPLATE-SPEC,LOGGING-CONTRACT,PART2A-WALKTHROUGH}.md`.
6. **Run** — pick a stored testbox from the dropdown (or ➕ Add new testbox…), pick
   the `.setup`, **Check Connection**, **Run on Testbox**. The script + setup go over
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

**Testboxes** (sidebar) — stored connection profiles (`tb_number` + IP minimum) kept
in the gitignored `secrets.testboxes.json` (0600). Passwords are write-only; the API
returns `has_password` only. Passwordless sudo on the box is required (probed by check).

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

## Security Posture (hardened 2026-07-27c–e)

Ask CK is designed for **localhost / single-user** use (a shared multi-tenant deployment is
explicitly out of contract — see *Known Issues*). A full adversarial review (2026-07-27) hardened
the boundaries so untrusted/LLM-derived input can't escape its lane even so:

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

Still deliberately *accepted* for the single-user model (documented, not bugs): the server binds
`0.0.0.0` with no auth, and paramiko uses `AutoAddPolicy` (no SSH host-key verification). Harden these
before any shared/exposed deployment.

## Testing

A backend test suite lives at the repo-root `tests/` (pytest, in-process `TestClient` — no mocks,
no network, no testbox). Run it with the venv interpreter:

```bash
PYTHONNOUSERSITE=1 .venv/bin/pytest -q        # 48 tests
./tool/run_tests.sh                            # guards + pytest, one command (CI-shaped)
```

`PYTHONNOUSERSITE=1` is required so an older fastapi/starlette in `~/.local` can't shadow the venv's.
Coverage centers on the security/correctness fixes (validator + export gate, the JSON extractor, the
framework guard, HTML sanitizer, secret redaction, path-traversal guards, agent-bridge ownership,
CORS) plus the `/process` page. Dev-only deps (`pytest`, `httpx`) are in
`ask-ck/CK-main/requirements-dev.txt` (the runtime `requirements.txt` stays lean). There is **no CI
runner yet** (`.github/workflows`) — running `./tool/run_tests.sh` before a commit is the current gate.
The two invariant guards (`tool/guard_db_only.py`, `tool/guard_framework_readonly.py`) run as part of it.

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
LLM_API_KEY=sk-... PYTHONPATH=ask-ck/CK-main python3 -m uvicorn CK_server.main:app --host 0.0.0.0 --port 8000 --reload

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
- Root `README.md` (overall project framing, status, and links to AGENTS.md)
- Root `SESSION_STATE.md` (broader session history)
- `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md` (the authoritative process this tool supports)
- External `AGENTS.md` (access patterns and environment details, as referenced from root README)

---

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

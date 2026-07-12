# SERVER-README.md — Objective Drafting Tool (Server-Backed)

This document contains **all instructions for use, setup, configuration, architecture, and details** for the server-backed edition of the Objective Drafting Tool.

## Overview and Goals

The server-backed drafting tool fulfills the two main functions:

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
- Future extensibility is expected (tool can be complex to build).

This version replaces the original single-file static `index.html` approach.

**Project state reference**: ~41 cases already processed using the overall workflow. The server version uses the same data sources and output formats (`refined-cases/<Group>/AWPTCM-Txxxx/{traceability.md, zephyr_payload.json}`).

## Architecture

**Backend**: FastAPI (Python)
- Persistent process (run with uvicorn).
- Loads and manages all data on the server side.
- Enforces the repeatable process state machine.
- Direct LLM calls using templated prompts.
- Post-processing of LLM output using templates/parsers for guaranteed repeatable structure.
- REST API consumed by the frontend.
- Serves the process documentation as interactive web pages.

**Frontend**: Static web UI (vanilla JS + HTML, served by the backend)
- Restructured per design guidelines (sidebar+main layout from showcase, full tokens, components).
- Sidebar (full to top, 240px): LLM status, vertical steps nav (gray SVGs), theme toggle, custom thin scrollbar.
- Step 0 dual case dropdowns: **Open / partial** (in-progress first) vs **Complete** (has `refined-cases/.../zephyr_payload.json`).
- Steps: **1. TestLink**, **2. Zephyr**, **3. ATPyLib (scored)**, **4. Synthesize** — each of 1–3 has Search + Suggest with LLM toolbars.
- Tables use explicit column classes (`cols-5`, `cols-6-zephyr`, `cols-6-atp`) for compact layout.
- Multi-step with gates; synthesize only after confirms; human-readable Step 4 + editor; export.
- Process Reference at `/process` (basic). Favicon at `/favicon.ico` / `/favicon.svg`.

**LLM Layer** (core of repeatability):
- Prompt templates in `drafting_server/templates/prompts/` including `generate_objectives.jinja`, `generate_steps.jinja`, **`generate_gaps.jinja`**, `suggest_*.jinja`, `analyze_atp_coverage.jinja` (rank only).
- **Gaps analysis is LLM-generated at synthesize/export** for Traceability — not an editable Step 3 field.
- CLI subscription modes only in UI: `grok_cli` (default) and `claude_code`. Legacy `api_key` server-side only.
- **Workspace LLM default**: Apply/Login writes `drafting_server/sessions/_workspace_llm.json`; load_case applies it to cases without an active config so switching cases does not reset login.
- Full provenance (prompts/responses/provider/auth) captured per session.

**Data**:
- The three databases:
  - TestLink historical + candidates/decisions
  - Zephyr (slim_index + zephyr_cases.jsonl)
  - Enriched ATPyLib (test_id_description + suite files)
- Loaded on server startup (or lazily). Server-side indexes enable fast search and cross-referencing.

**Hosting**:
- Intended to run behind nginx on a local IP.
- Never offline.
- Example nginx config provided.

**Repeatability Guarantees**:
- Process: Backend state machine enforces explicit user confirmation of TestLink/Zephyr/ATPyLib **selections** before synthesis. Gates are server-side.
- LLM: Templated prompts + structured parsing + provenance; gaps for Traceability authored at completion (not mid-wizard free text).
- Outputs: Fixed Jinja + post-processing; export auto-persists to `refined-cases/<Group>/`.
- UI: Dual case lists, Search/Suggest on steps 1–3, CLI login radios, design-system components.

## Directory Structure (inside drafting-tool/)

```
drafting-tool/
├── SERVER-README.md                 ← This file (all instructions)
├── PLAN-server-backed.md            ← Full approved plan copy
├── README.md                        ← Original (points here)
├── nginx-drafting-server.conf.example
├── drafting_server/                 ← The actual server application
│   ├── main.py                      ← FastAPI entry point
│   ├── data.py                      ← Data loading (three DBs + indices)
│   ├── llm.py                       ← Prompt templating + LLM call + parser
│   ├── models.py                    ← Pydantic models
│   ├── routers/
│   │   └── wizard.py                ← API endpoints for the step workflow
│   ├── static/
│   │   └── index.html               ← Frontend UI (wizard + process links)
│   ├── templates/
│   │   ├── prompts/
│   │   │   ├── generate_objectives.jinja
│   │   │   └── generate_steps.jinja
│   │   └── outputs/
│   │       └── traceability.md.jinja
│   ├── nginx.conf.example
│   └── README.md                    ← Shorter version (see SERVER-README.md for full details)
├── ... (original static files for reference)
└── data/ ...                        ← Existing project data (used by server)
```

All new server code and related files live under `drafting-tool/drafting_server/`.

## Installation / Dependencies

From the project root:

```bash
python3 -m pip install --user fastapi uvicorn jinja2 requests
```

(If using a real LLM provider you may need additional packages such as `litellm` or the official SDK.)

## Running the Server

The easiest way is to use the included helper script from the project root:

```bash
# With a real API key
LLM_API_KEY=sk-... ./drafting-tool/run.sh

# Different port
PORT=9000 ./drafting-tool/run.sh

# Extra uvicorn options (e.g. debug logging)
./drafting-tool/run.sh --log-level debug
```

The script automatically:
- Uses `python3`
- Sets the correct `PYTHONPATH` for the `drafting-tool/` layout
- (No MOCK default; real LLM required)

### Manual equivalent

```bash
LLM_API_KEY=sk-... PYTHONPATH=drafting-tool python3 -m uvicorn drafting_server.main:app --host 0.0.0.0 --port 8000 --reload
```

Alternative (cd into the server dir):

```bash
cd drafting-tool/drafting_server
LLM_API_KEY=sk-... PYTHONPATH=. python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Environment variables for LLM**:

```bash
export LLM_API_KEY=sk-...
export LLM_BASE_URL=https://api.openai.com/v1   # or your Grok/Claude-compatible endpoint
```

Real LLM (API key or local CLI login) is required. MOCK/demo mode has been removed.

### Claude Team Subscription (Headless Mode)

If your users have **Claude Team subscriptions** (not developer API keys), the tool can call Claude through the **Claude Code CLI** in headless print mode instead of the HTTP API. Auth lives entirely with the CLI's own login; the server never sees or stores a key or token.

**Intended deployment**: each user hosts the tool locally (or the server runs as their own user), so calls bill against *their own* Team seat. Do **not** run one shared server instance under a single login for many users — that pools everyone's usage through one subscription seat.

Per-machine setup:

1. Install Claude Code on the machine running this server (see anthropic.com/claude-code).
2. In a terminal, run `claude` and log in (`/login`) with your Claude Team account.
3. In the tool UI (Step 0 → LLM Provider Login): select **Claude (Anthropic)** → **Claude Code CLI (Team subscription)** → "Check CLI Status" → "Apply / Login".
4. Leave Model blank to use the CLI's default (or pass e.g. `sonnet`).

Notes / limitations:

- Server-side check: `GET /api/wizard/claude_cli_status` reports whether the CLI binary is found (login state surfaces on the first real call — a login error message is returned in the synthesis output if the CLI isn't logged in).
- Team seats have rolling session-based usage limits shared with the user's interactive Claude Code use. The tool's calls are minimal (Step 3 assist + Step 4 synthesis), but an exhausted window surfaces as a CLI error until it resets.
- Latency is higher than a direct HTTP call (CLI process startup per request) — acceptable for the tool's occasional synthesis calls.
- Old "account" / token-paste flows were removed from the UI long ago. Current UI only exposes the two subscription CLI radios. Legacy `api_key` and old `account` values are mapped gracefully on restore but not presented to new users.

### Grok CLI Subscription Mode (SuperGrok / X Premium+)

`auth_method: "grok_cli"` (Grok provider only) calls a locally installed + logged-in Grok CLI (`grok login --oauth`) instead of the HTTP API. 

- `GET /api/wizard/grok_cli_status` reports availability.
- In the UI (Step 0): select the **Grok CLI (SuperGrok / X Premium+ subscription)** radio, use the "Check Grok CLI" button, then "Apply / Login". Model optional (CLI default used if blank).
- Prompt passed safely via temp file; output captured cleanly.
- Fully integrated into synthesis and ATP paths. Real calls were tested on a machine with an active subscription login.
- Usage counts against the subscription (no separate API billing).

## Accessing the Tool

- Main wizard UI: `http://your-local-ip:8000/`
- Process as web-based page: `http://your-local-ip:8000/process`
- Interactive API docs (Swagger): `http://your-local-ip:8000/docs`
- Health: `http://your-local-ip:8000/health`

## Typical Workflow (Repeatable Process)

1. Open the UI and select an AWPTCM case (dropdown populated with real project cases; neutral selection).
2. In Step 0 LLM section: choose the desired subscription CLI radio (Grok CLI is default). Optionally check status for the selected CLI. Apply. (No provider dropdown or API Key path is shown; real login/key required.)
3. **Step 1 – TestLink**  
   Review primary + candidates. Use **Search TestLink** / **Suggest with LLM** to expand or re-rank, then confirm selections.
4. **Step 2 – Zephyr**  
   Review relevance-ranked external Zephyr cases (current Cases list omitted). Use **Search Zephyr** / **Suggest with LLM** as needed, then confirm.
5. **Step 3 – ATPyLib (scored)**  
   Search and select ART cases (pre-scored via LLM). Use **Search ATP** / **Suggest with LLM** if needed. Confirm selections only — **no gaps form** in this step.
6. Only after all three confirms are done → **Step 4 – Synthesize (LLM)** becomes active.
7. Click **"Synthesize with LLM (templated prompt)"**.
   - Backend builds templated prompts from your selections + process principles.
   - LLM generates: **Gaps analysis** (for Traceability), objectives, and verification steps.
   - First testScript step is always the server-built traceability note.
   - Response is parsed + normalized for a repeatable shape.
8. Review the result; use the editor as needed.
9. Click **Export Repeatable Bundle**.
   - Produces (for download):
     - `traceability.md` (templated; **Gaps Noted** from LLM at synthesis/export)
     - `AWPTCM-Txxxx-zephyr_payload.json` (exact Zephyr Scale shape)
     - Session JSON (full provenance, including prompts sent to the LLM)
   - Also auto-persists core artifacts server-side to `refined-cases/<Group>/AWPTCM-Txxxx/`.
10. Use the persisted or dropped files in the correct `refined-cases/<Group>/AWPTCM-Txxxx/` directory.

Tables are compact to fit on one page with no side-scroll. Step 2 Zephyr cross-refs contain only external cases (current Cases list entries, including the primary, are omitted).

The process and output formats are identical to what is documented in `OBJECTIVE_DRAFTING_PROCESS.md`.

## LLM Templating & Repeatability

Prompt templates live here:
- `generate_objectives.jinja` / `generate_steps.jinja` — synthesis
- `generate_gaps.jinja` — Traceability gaps (synthesize/export only)
- `suggest_testlink.jinja` / `suggest_zephyr.jinja` / `suggest_atp.jinja` — pre-select assists
- `analyze_atp_coverage.jinja` — Step 3 ranking only (no gaps paragraph)

They inject confirmed selections + process principles ("artefacts, not procedures", first step notes + traceability, positive/negative/special cases, etc.).

After the LLM returns text, `llm.py` parses/normalizes and export uses `templates/outputs/traceability.md.jinja` so files match the documented standard.

**Note**: MOCK/demo mode has been removed. Real LLM (CLI login preferred) is required. Edit templates to refine style without code changes.

## Hosting Behind nginx

Copy the example:

```bash
cp drafting-tool/nginx-drafting-server.conf.example /etc/nginx/sites-available/drafting-tool
# edit and enable, then nginx -t && systemctl reload nginx
```

Typical snippet (adjust path as needed):

```
location /drafting-tool/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Access via your local IP / hostname that nginx serves.

## Data Sources Used

The server reads from the existing project `data/` directory (same as the original workflow):
- `data/zephyr_master.json`
- `data/candidates.json`
- `data/decisions/*.json`
- `data/zephyr_full/slim_index.json` + `zephyr_cases.jsonl`
- `data/suites/test_id_description.json` (and enriched suites)
- `data/suites/testlink_awp.json`

Data is loaded on the server, so large files and growth are no longer a browser problem.

## Migration from Original Single-File Tool

- The original `drafting-tool/index.html` and `build_drafting_tool.py` logic (wizard UI, session model, selection tables, confirm buttons, export generation) has been migrated/adapted.
- Old static files remain in `drafting-tool/` for reference.
- The new server version adds LLM synthesis, backend enforcement of the process, and templated repeatability.
- Output artifacts are drop-in compatible with the existing `refined-cases/` layout and `upload_refined.py`.

## Development Notes

- Most logic is in `drafting_server/`.
- To iterate on prompts: edit the `.jinja` files and restart (or use `--reload`).
- To iterate on the UI: edit `static/index.html` (no rebuild step).
- The wizard still supports manual editing of objectives/steps after LLM synthesis (or you can bypass LLM entirely).
- Session state is currently in-memory (easy to extend with SQLite or file persistence for restarts).
- Full prompt + LLM response is captured in the exported session JSON for auditability.

## Relation to the Approved Plan

See `drafting-tool/PLAN-server-backed.md` for the complete approved plan that this implementation follows.

The plan explicitly chose server-backed because:
- LLM is required for creation.
- Data will grow.
- Repeatable outputs via templating.
- Hosted behind nginx.
- Future extension is planned.

## Quick Reference Commands

```bash
# Start server (easiest)
./drafting-tool/run.sh

# With real key or different port
LLM_API_KEY=sk-... ./drafting-tool/run.sh
PORT=9000 ./drafting-tool/run.sh

# Manual start (project root)
LLM_API_KEY=sk-... PYTHONPATH=drafting-tool python3 -m uvicorn drafting_server.main:app --host 0.0.0.0 --port 8000 --reload

# Test synthesis directly (Python)
cd drafting-tool/drafting_server
PYTHONPATH=. python3 -c '
from llm import synthesize_objectives_and_steps
sess = {"key":"AWPTCM-Txxxx", "step1":{"selections":[...]},"step2":{...},"step3":{...},"gaps":"..."}
print(synthesize_objectives_and_steps(sess))
'
```

For the full approved plan, usage philosophy, and trade-off history, read `PLAN-server-backed.md` in this directory.

This SERVER-README.md is the single source of operational instructions.

**For future sessions**: Start with `PROGRESS.md` in this directory. It contains current status, completed work, open tasks, technical debt, prioritized backlog with effort estimates, and a handoff checklist.

Cross-reference higher-level project docs every session:
- Root `README.md` (overall project framing, status, and links to AGENTS.md)
- Root `SESSION_STATE.md` (broader session history)
- `OBJECTIVE_DRAFTING_PROCESS.md` (the authoritative process this tool supports)
- External `../AGENTS.md` (access patterns and environment details, as referenced from root README)

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
- GitHub: history LFS migrate for Zephyr XML/jsonl so push succeeds under 100 MB blob rules.

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
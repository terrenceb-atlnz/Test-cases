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
- Sidebar (full to top, 240px): case selector, LLM status+configure, vertical steps nav with small gray SVG icons (no emojis), custom thin scrollbar with border effect.
- Main: .page-header (dynamic title/desc per view), LLM config card (toggled; supports key/account with in-page instructions + explicit "Open tab now"), step content using .card + .section/.section-heading/.section-description.
- Buttons use .btn/.btn-primary/.btn-secondary etc.; tables .table-container/.table; forms .form-*; badges for status.
- Theme toggle (light/dark via .light class) integrated in sidebar.
- Multi-step with gates; "Synthesize with LLM" only after confirms; live preview + export.
- Process Reference page/tab.
- Title/logo incorporated into sidebar (no persistent top header bar per template).

**LLM Layer** (core of repeatability):
- Prompt templates live in `drafting_server/templates/prompts/` (`generate_objectives.jinja`, `generate_steps.jinja`).
- Templates inject: case data + user selections from the three databases + excerpts from `OBJECTIVE_DRAFTING_PROCESS.md` (principles, rules for artefacts vs. procedures, first-step notes requirement, etc.).
- LLM response is parsed + normalized using output templates (`drafting_server/templates/outputs/`) so the final `objective` (`<ul><li>...</li></ul>`) and `testScript` always follow the exact documented shape.
- Supports multiple providers (Grok via OpenAI-compatible; Claude native) with per-session config: `provider`, `auth_method` ("api_key" or "account"), credentials.
- Full prompt + response + provider/model details captured as `provenance` in the persisted session for audit/repeatability.
- Login flows (API key direct or account via instructions + explicit open) handled in frontend with in-page panel (no popup focus race).

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
- Process: Backend state machine enforces explicit user confirmation of TestLink/Zephyr/ATPyLib reviews (selections + flags persisted) before synthesis allowed. Gates are server-side.
- LLM: Multi-provider (Grok/Claude) with templated prompts + structured parsing + full provenance (prompts/responses/provider/auth) captured in session.
- Outputs: Fixed Jinja + post-processing for consistent shape; persistence of LLM config + provenance supports audit across restarts.
- UI: In-page account login flow + design system components ensure predictable, repeatable user experience.

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

From the project root (recommended):

```bash
# Recommended invocation
python -m uvicorn drafting_tool.drafting_server.main:app --host 0.0.0.0 --port 8000 --reload
```

Alternative (cd into the server dir):

```bash
cd drafting-tool/drafting_server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Environment variables for LLM**:

```bash
export LLM_API_KEY=MOCK                    # Use built-in mock for testing (recommended for first run)
# or
export LLM_API_KEY=sk-...
export LLM_BASE_URL=https://api.openai.com/v1   # or your Grok/Claude-compatible endpoint
```

When `LLM_API_KEY=MOCK`, the system uses a deterministic mock response so you can test the full flow and templating without an external call.

## Accessing the Tool

- Main wizard UI: `http://your-local-ip:8000/`
- Process as web-based page: `http://your-local-ip:8000/process`
- Interactive API docs (Swagger): `http://your-local-ip:8000/docs`
- Health: `http://your-local-ip:8000/health`

## Typical Workflow (Repeatable Process)

1. Open the UI and select an AWPTCM case (dropdown now populated with real project cases; T33234 prioritized for demo).
2. **Step 1 – TestLink + Decisions**  
   Review candidates and primary (real data from candidates.json). Make selections + justifications (checkboxes + editable fields). Click **"Mark TestLink List Reviewed + Confirmed"**.
3. **Step 2 – Zephyr Cross-Reference**  
   Review relevant Zephyr cases (real refs from zephyr_master + slim_index). Confirm.
4. **Step 3 – ATPyLib + Gaps**  
   Search and select ART cases (real data from test_id_desc). Use **"Suggest with LLM (pre-select)"** button for LLM-assisted pre-selection based on prior steps. Note gaps. Confirm.
   - On MOCK + demo case (T33234), steps 1-3 are auto pre-filled with realistic selections.
5. Only after all three confirms are done → **Step 4 – Synthesize (LLM)** becomes active.
6. Click **"Synthesize with LLM (templated prompt)"**.
   - Backend builds a rich prompt from templates + your selections + process principles.
   - LLM is called.
   - Response is parsed + normalized using output templates.
   - You get a clean, declarative objective + readable test steps list (human-readable format; provenance available in details).
7. Review the result (raw JSON view no longer default).
8. Click **Export Repeatable Bundle**.
   - Produces:
     - `traceability.md` (templated, includes all your reviewed items + links)
     - `AWPTCM-Txxxx-zephyr_payload.json` (exact Zephyr Scale shape)
     - Session JSON (full provenance, including the exact prompt sent to the LLM)
9. Drop the files into the correct `refined-cases/<Group>/AWPTCM-Txxxx/` directory (same layout as before).

Tables are now compact to fit on one page with no side-scroll.

The process and output formats are identical to what is documented in `OBJECTIVE_DRAFTING_PROCESS.md`.

## LLM Templating & Repeatability

Prompt templates live here:
- `drafting_server/templates/prompts/generate_objectives.jinja`
- `drafting_server/templates/prompts/generate_steps.jinja`
- `drafting_server/templates/prompts/suggest_atp.jinja` (new: LLM pre-selection for Step 3 ATPyLib)

They always include:
- The three databases selections you confirmed
- Excerpts of the process principles ("artefacts, not procedures", first step is notes + traceability, positive/negative/special cases, etc.)

After the LLM returns text, `llm.py` runs structured parsing + the output template in `templates/outputs/traceability.md.jinja` (and equivalent logic for the payload) so the final files are consistent and match the documented standard.

This is how repeatable outputs are achieved even when using stochastic LLMs.

**Note on MOCK mode (demo)**: Provides rich pre-filled selections for T33234 across steps 1-3 and deterministic synthesis for quick end-to-end testing.

You can edit the templates to refine style or add more rules without changing code.

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
# Start server (project root)
python -m uvicorn drafting_tool.drafting_server.main:app --host 0.0.0.0 --port 8000 --reload

# With mock LLM
LLM_API_KEY=MOCK python -m uvicorn ...

# Test a synthesis directly (Python)
cd drafting-tool/drafting_server
PYTHONPATH=. python -c '
from llm import synthesize_objectives_and_steps
sess = {"key":"AWPTCM-T33234", "step1":{"selections":[...]},"step2":{...},"step3":{...},"gaps":"..."}
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

## Session Summary (2026-07-02)

This session completed data-driven review for Steps 1-3 with LLM support and made the tool demo-ready:

- Real selectable data + UI for TestLink (Step 1) and Zephyr (Step 2).
- LLM "Suggest with LLM (pre-select)" for Step 3 (new prompt + backend).
- Dynamic cases + auto pre-filled demo selections for T33234 (all steps 1-3) when using MOCK.
- Compact tables (reduced padding, narrow inputs) so everything fits on one page with no side-scroll.
- Human-readable formatted output in Step 4 (Objective as list + clean steps; removed "Action:"; provenance details).

All changes stay under `drafting-tool/`. Test primarily with `LLM_API_KEY=MOCK` for instant rich pre-fills.

See updated `PROGRESS.md` and `LESSONS_LEARNED.md`.


## Session State & Lessons Learned (2026-07-01, extended session)

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
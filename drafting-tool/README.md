# Drafting Tool for Objective Drafting Process

This directory contains both the legacy single-file static version and the current **server-backed edition** of the tool.

## Current Focus: Server-Backed Edition

The primary implementation is now in `drafting_server/` (FastAPI backend + frontend).

**All instructions, setup, usage, architecture, LLM templating, nginx hosting, and details are in:**
- `SERVER-README.md` (comprehensive guide)
- `PLAN-server-backed.md` (full approved plan)
- `drafting_server/README.md` (quick pointer)

**Recent progress (see PROGRESS.md):** real data + selectable tables for Steps 1-3 (TestLink/Zephyr/ATPyLib), LLM pre-selection for Step 3 ATPyLib, dynamic case list with T33234 demo pre-fills, UI compaction for one-page fit, human-readable formatted synthesis in Step 4.

### Why Server-Backed?
- LLM integration is necessary to generate Objectives and Steps from selections.
- Data will continue to grow.
- Tool will be hosted locally (nginx on local IP) and never offline.
- Enables strong templating for **repeatable process** and **repeatable outputs**.
- Better positioned for future extensions.

See `SERVER-README.md` for full details.

## Legacy: Single-File Static Version

The original self-contained static version remains for reference:
- `index.html`
- `design-tokens.css`, `STYLE-GUIDELINES.md`, design guidelines assets
- `sample-session-T33234.json`

**Key Features (original focus on repeatable outputs)**
- Multi-step wizard matching the documented process
- Searchable cross-reference for Zephyr cases (Step 3)
- Session capture for full provenance
- One-click export of:
  - `traceability.md` (structured with links)
  - `zephyr_payload.json` (correct API shape)
  - `*-draft-session.json` (for replay and audit)

**Usage (legacy)**
1. Open `index.html` in a browser
2. Select an AWPTCM case
3. Work through the steps (search, select, edit objective/steps)
4. Click "Export Repeatable Bundle"
5. Drop the generated files into the appropriate `refined-cases/<Group>/AWPTCM-Txxxx/` directory

See the main `OBJECTIVE_DRAFTING_PROCESS.md` for the process this tool supports.

## Related Files
- `PROGRESS.md` — **Start here for future sessions** (current status, open tasks, handoff notes)
- `SERVER-README.md` — Complete instructions for the server version
- `PLAN-server-backed.md` — The approved implementation plan
- `LESSONS_LEARNED.md` — Captured insights from development
- `drafting_server/` — Server code (FastAPI)
- `nginx-drafting-server.conf.example` — Hosting example

→ **All instructions, setup, configuration, usage, LLM templating, nginx hosting, and architecture details are in `SERVER-README.md`** (in this directory).

Also see:
- `PLAN-server-backed.md` (full approved plan)
- `drafting_server/` for the actual code
- `nginx-drafting-server.conf.example`

The original single-file files remain for reference.

## Design System Integration

This folder also contains the OML Design Guidelines Showcase (recreated without password protection) and extracted style tokens.

### Unprotected Design Guidelines
- Open `design-guidelines-showcase.html` directly in a browser.
- Assets are in `design-guidelines-files/`.

### Style Guidelines File
- See `STYLE-GUIDELINES.md` for documented design philosophy, tokens, and components.
- `design-tokens.css` contains the CSS custom properties for light and dark themes.

### Design Tokens (Summary)
Use the CSS variables defined in `design-tokens.css` for consistent styling across the drafting tool and related UIs.

Key categories:
- Backgrounds (`--bg-*`)
- Text (`--text-*`)
- Borders, Accent, Status colors
- Shadows, Typography (`--font-sans`, `--font-mono`)

Toggle dark mode by adding the `.dark` class to the `<html>` element.

## Design Guidelines (Unprotected)

- `design-guidelines-showcase.html` — Full OML Design Guidelines Showcase page (recreated without password protection).
- Asset folder: `design-guidelines-files/`

Open `design-guidelines-showcase.html` directly in any browser — no password required.

## Style Guidelines File

- `STYLE-GUIDELINES.md` — Structured documentation extracted from the showcase.
- `design-tokens.css` — Reusable CSS custom properties (light + dark themes).

Use these as the source of truth for styling the drafting tool and any related UIs.

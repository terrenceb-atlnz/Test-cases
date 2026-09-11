# Objective Drafting (Objective/Test Case Generator)

Data, process docs, and exported artefacts for the **Objective/Test Case Generator** — the first tool in the **Ask CK** workbench (`ask-ck/CK-main/`). The generator implements **`OBJECTIVE_DRAFTING_PROCESS.md`**: review TestLink → Zephyr → ATPyLib, then synthesize Objectives + testScript with a real LLM, and export drop-in `refined-cases/` artifacts.

> **Layout note (2026-07-13):** the former `drafting-tool/` directory was split — server code now lives in `ask-ck/CK-main/CK_server/`, while this directory (`ask-ck/functions/generator/`) holds the generator's data, process docs, and outputs.

## Start here

| Doc | Purpose |
|-----|---------|
| **[PROGRESS.md](PROGRESS.md)** | Current status, backlog, technical debt, session handoff |
| **[../CK-main/SERVER-README.md](../../CK-main/SERVER-README.md)** | Run, architecture, LLM CLI modes, nginx, workflow |
| [PLAN-server-backed.md](../../../archive/records/PLAN-server-backed.md) | Approved design and rationale (historical paths; archived 2026-09-11) |
| [LESSONS_LEARNED.md](LESSONS_LEARNED.md) | Decisions and pitfalls from prior sessions |

## Quick start

From the **repository root**:

```bash
./ask-ck/CK-main/run.sh
# open http://localhost:8000/
# API docs: http://localhost:8000/docs
# Process page: http://localhost:8000/process
```

**LLM (required):** configure via the sidebar **LLM → Configure** panel — **Grok CLI** (default; SuperGrok / X Premium+ via `grok login --oauth`) or **Claude Code CLI** (Team via `claude /login`). MOCK/demo mode is removed.

Dependencies (typical):

```bash
python3 -m pip install --user fastapi uvicorn jinja2 requests
```

## What it does (Generator steps, as shown in the UI)

1. **Step 1 – Cases** — load an AWPTCM case (real candidates / decisions / suite data)
2. **Step 2 – TestLink** — Search / Suggest with LLM, then confirm selections
3. **Step 3 – Zephyr** — Search / Suggest external cross-refs, then confirm
4. **Step 4 – ATPyLib (scored)** — Search / Suggest ATP, then confirm (no gaps form)
5. **Step 5 – Objectives (LLM)** — synthesize only after all three confirms; LLM also writes **Gaps** for Traceability
6. **Step 6 – Test Steps (LLM)** — synthesize steps, then **Export**: auto-write to `refined-cases/<Group>/AWPTCM-Txxxx/`

Repeatability comes from **Jinja prompt templates** + structured parsing + process gates — not from MOCK data.

## Layout

```
ask-ck/
├── CK-main/                        # Ask CK app (server + UI)
│   ├── SERVER-README.md            # Full operational docs
│   ├── run.sh
│   └── CK_server/                  # FastAPI app
│       ├── main.py / paths.py
│       ├── data.py / llm.py / models.py
│       ├── routers/                # wizard.py + tool stubs
│       ├── frontend/ck-main/current/index.html       # Ask CK UI (all tools)
│       ├── templates/prompts/      # LLM prompts
│       ├── templates/outputs/      # Export templates
│       └── sessions/               # Persisted wizard sessions
├── objective-drafting/             # THIS DIRECTORY (generator data + docs)
│   ├── PROGRESS.md                 # Handoff / backlog (read first)
│   ├── OBJECTIVE_DRAFTING_PROCESS.md
│   ├── data/                       # zephyr_master, candidates, decisions, suites, zephyr_full
│   └── refined-cases/              # Exported artefacts
├── pytest-create/                  # (future) PyTest Creator assets
├── test-composer/                  # (future) Test Composer assets
└── zephyr-tool/                    # (future) Zephyr Templating Tool assets
```

## Legacy single-file UI

The old single-file `index.html` and its design assets were archived to `archive/CK-main/` on 2026-09-11 (reference only). **New work belongs in `../../CK-main/CK_server/`.**

Design tokens / showcase (the 2026-07-13 design system; archived 2026-09-11, superseded by the Svelte front-end work): `../../../archive/CK-main/design-tokens.css`, `design-guidelines-showcase.html`, `STYLE-GUIDELINES.md`.

## Project context

Root docs:

- `../../../README.md` — project overview
- `OBJECTIVE_DRAFTING_PROCESS.md` — process source of truth (lives here)
- `../../../SESSION_STATE.md` — broader history
- `refined-cases/` — exported artefacts (lives here)

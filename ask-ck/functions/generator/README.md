---
verified: 2026-09-23
---
# Objective Drafting (Objective/Test Case Generator)

Data, process docs, and exported artefacts for the **Objective/Test Case Generator** — the first tool in the **Ask CK** workbench (`ask-ck/CK-main/`). The generator implements **`OBJECTIVE_DRAFTING_PROCESS.md`**: review TestLink → Zephyr → ATPyLib, then synthesize Objectives + testScript with a real LLM, and export drop-in `refined-cases/` artifacts.

> **Layout note (2026-07-13):** the former `drafting-tool/` directory was split — server code now lives in `ask-ck/CK-main/CK_server/`, while this directory (`ask-ck/functions/generator/`) holds the generator's data, process docs, and outputs.

## Start here

| Doc | Purpose |
|-----|---------|
| **[PROGRESS.md](PROGRESS.md)** | Current status, backlog, technical debt, session handoff |
| **[../../CK-main/SERVER-README.md](../../CK-main/SERVER-README.md)** | Run, architecture, LLM configuration, nginx, workflow |
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

**LLM (required):** configure via the sidebar **LLM → Configure** panel. There are two
backends: the **org vLLM** and **Claude Code CLI (my local machine)** — your own Claude seat,
reached through the `ck-agent` on your PC (run the one-line seat setup on the home page first).
The choice is per seat. Grok and server-side Claude were removed on 2026-09-11 and 2026-09-10;
MOCK/demo mode is long gone.

Dependencies: a venv with `ask-ck/CK-main/requirements.txt` — see the root
[`README.md`](../../../README.md) quick start (`setup.sh` does all of it).

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
├── CK-main/                        # Ask CK server
│   ├── SERVER-README.md            # Full operational docs
│   ├── run.sh, requirements*.txt
│   └── CK_server/                  # FastAPI app — main.py, paths.py, db.py, llm.py, models.py …
│       ├── routers/                # wizard/ (this Generator), pytest_create.py, + tool stubs
│       ├── generator/              # the Generator's logic with no FastAPI surface
│       └── templates/              # prompts/ (LLM prompts), outputs/ (export templates)
├── frontend/ck-main/current/       # the UI — index.html + ES modules by page
├── db/ck.db                        # permanent single source of truth (corpora AND sessions)
├── functions/
│   ├── generator/                  # THIS DIRECTORY — PROGRESS.md, OBJECTIVE_DRAFTING_PROCESS.md,
│   │                               #   refined-cases/ (exported artefacts, recreated on export)
│   ├── pytest-creator/             # PyTest Creator docs + generated/ scripts
│   ├── test-composer/              # Test Composer docs + bench scripts
│   └── zephyr-tool/                # Zephyr Templating Tool (stub)
├── plans/                          # live PLAN-*.md (completed ones: archive/plans/)
└── tools/                          # the gate, guards, scratch server, CLI tools
```

(The corpora that used to sit in a `data/` directory here live in `ck.db` since 2026-07-20.)

## Legacy single-file UI

The old single-file `index.html` and its design assets were archived to `archive/CK-main/` on 2026-09-11 (reference only). **New work belongs in `../../CK-main/CK_server/`.**

Design tokens / showcase (the 2026-07-13 design system; archived 2026-09-11, superseded by the Svelte front-end work): `../../../archive/CK-main/design-tokens.css`, `design-guidelines-showcase.html`, `STYLE-GUIDELINES.md`.

## Project context

Root docs:

- `../../../README.md` — project overview
- `OBJECTIVE_DRAFTING_PROCESS.md` — process source of truth (lives here)
- `../../../SESSION_STATE.md` — broader history
- `refined-cases/` — exported artefacts (lives here)

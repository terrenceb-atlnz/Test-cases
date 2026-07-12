# Objective Drafting Tool

Server-backed wizard that implements **`OBJECTIVE_DRAFTING_PROCESS.md`**: review TestLink → Zephyr → ATPyLib, then synthesize Objectives + testScript with a real LLM, and export drop-in `refined-cases/` artifacts.

## Start here

| Doc | Purpose |
|-----|---------|
| **[PROGRESS.md](PROGRESS.md)** | Current status, backlog, technical debt, session handoff |
| **[SERVER-README.md](SERVER-README.md)** | Run, architecture, LLM CLI modes, nginx, workflow |
| [PLAN-server-backed.md](PLAN-server-backed.md) | Approved design and rationale |
| [LESSONS_LEARNED.md](LESSONS_LEARNED.md) | Decisions and pitfalls from prior sessions |

## Quick start

From the **repository root**:

```bash
./drafting-tool/run.sh
# open http://localhost:8000/
# API docs: http://localhost:8000/docs
# Process page: http://localhost:8000/process
```

**LLM (required):** configure in Step 0 of the UI — **Grok CLI** (default; SuperGrok / X Premium+ via `grok login --oauth`) or **Claude Code CLI** (Team via `claude /login`). MOCK/demo mode is removed.

Dependencies (typical):

```bash
python3 -m pip install --user fastapi uvicorn jinja2 requests
```

## What it does

1. Load an AWPTCM case (real candidates / decisions / suite data)  
2. **Step 1 – TestLink** — Search / Suggest with LLM, then confirm selections  
3. **Step 2 – Zephyr** — Search / Suggest external cross-refs, then confirm  
4. **Step 3 – ATPyLib (scored)** — Search / Suggest ATP, then confirm (no gaps form)  
5. **Step 4** — Synthesize only after all three confirms; LLM also writes **Gaps** for Traceability  
6. **Export** — downloads + auto-write to `refined-cases/<Group>/AWPTCM-Txxxx/` (gaps generated if not yet synthesized)  

Repeatability comes from **Jinja prompt templates** + structured parsing + process gates — not from MOCK data.

## Layout

```
drafting-tool/
├── PROGRESS.md                 # Handoff / backlog (read first)
├── SERVER-README.md            # Full operational docs
├── PLAN-server-backed.md
├── LESSONS_LEARNED.md
├── run.sh
├── drafting_server/            # FastAPI app
│   ├── main.py
│   ├── data.py / llm.py / models.py
│   ├── routers/wizard.py
│   ├── static/index.html
│   ├── templates/prompts/      # LLM prompts
│   ├── templates/outputs/      # Export templates
│   └── sessions/               # Persisted wizard sessions
└── (legacy static assets)      # Original single-file UI + design system reference
```

## Legacy single-file UI

`index.html` and related design assets remain for reference only. **New work belongs in `drafting_server/`.**

Design tokens / showcase (for UI consistency): `design-tokens.css`, `design-guidelines-showcase.html`, `STYLE-GUIDELINES.md`.

## Project context

This tool is one component of the larger **Test-cases** repo. Root docs:

- `../README.md` — project overview  
- `../OBJECTIVE_DRAFTING_PROCESS.md` — process source of truth  
- `../SESSION_STATE.md` — broader history  
- `../refined-cases/` — exported artefacts  

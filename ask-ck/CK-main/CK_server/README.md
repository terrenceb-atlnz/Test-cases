# CK_server — Ask CK Server (short reference)

**All detailed instructions, architecture, usage, configuration, and repeatability details are in the parent directory:**

→ **[../SERVER-README.md](../SERVER-README.md)**

**For next sessions / handoff**: See **[../../objective-drafting/PROGRESS.md](../../objective-drafting/PROGRESS.md)** (current status, open tasks, technical debt, backlog with estimates, and handoff checklist).

Also cross-reference higher-level:
- Root `../../../SESSION_STATE.md` and `../../../README.md`
- `../../objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`
- External `AGENTS.md` (via root README references, if present)

This file is intentionally minimal. Please refer to `SERVER-README.md` for:
- How to run the server (`../run.sh`)
- LLM configuration (Grok CLI / Claude Code CLI subscription modes — no MOCK)
- Prompt & output templating
- nginx hosting
- Workflow (repeatable process + LLM synthesis)
- Full directory layout
- Links to the approved plan (`../../objective-drafting/PLAN-server-backed.md`)

The server code lives in this directory (`CK_server/`). Filesystem anchors (data, refined-cases, process md) are defined in `paths.py` and point into `../../objective-drafting/`. Sibling tool routers (`routers/zephyr_tool.py`, `routers/test_composer.py`, `routers/pytest_create.py`) are stubs for the other Ask CK tools.

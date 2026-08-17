# CK_server — Ask CK Server (short reference)

**All detailed instructions, architecture, usage, configuration, and repeatability details are in the parent directory:**

→ **[../SERVER-README.md](../SERVER-README.md)**

**For next sessions / handoff**: See **[../../objective-drafting/PROGRESS.md](../../objective-drafting/PROGRESS.md)** (current status, open tasks, technical debt, backlog with estimates, and handoff checklist).

Also cross-reference higher-level:
- Root [`README.md`](../../../README.md) — framing, quick start, the four invariants, doc map
- Root [`CHANGELOG.md`](../../../CHANGELOG.md) — what changed, when, and why
- Root [`SESSION_STATE.md`](../../../SESSION_STATE.md) — broader session history
- [`../../objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`](../../objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md)

This file is intentionally minimal. Please refer to `SERVER-README.md` for:
- How to run the server (`../run.sh`)
- LLM configuration (Grok CLI / Claude Code CLI subscription modes — no MOCK)
- Prompt & output templating
- nginx hosting
- Workflow (repeatable process + LLM synthesis)
- Full directory layout
- Links to the approved plan (`../../objective-drafting/PLAN-server-backed.md`)

The server code lives in this directory (`CK_server/`). Filesystem anchors (data, refined-cases, process md) are defined in `paths.py` and point into `../../objective-drafting/`.

**Sibling tool routers:** `routers/pytest_create.py` is the **fully implemented** PyTest Creator (7-step flow, testbox execution, LLM fix loop) — it stopped being a stub long ago. `routers/zephyr_tool.py` and `routers/test_composer.py` *are* still stubs.

**Shared modules (2026-07-28, `PLAN-backend-module-split.md` Part B)** — leaves that both routers import, so neither reaches into the other's internals:
- `llm_config.py` — the workspace LLM login (active? same backend? apply to a session)
- `case_registry.py` — which cases exist, which are Complete, which are hidden, how they group
- `session_store.py` — the in-memory `sessions` dict and its `ck.db` row
- `generator/` — the Generator's own logic with no FastAPI surface (`descriptions.py`, `gates.py`, `backfill.py`)

None of these may import `routers.*`, and none may import fastapi; `tests/test_shared_modules_decoupling.py` enforces both.

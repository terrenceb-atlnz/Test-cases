---
name: ask-ck-admin-restart
description: "Ask CK fast-restart flags + hidden in-page admin panel (double-click CK's face)"
metadata: 
  node_type: memory
  type: project
  originSessionId: b69a0140-ff36-4d22-bc3a-819e30838064
  modified: 2026-07-20T01:01:57.863Z
  verified: 2026-08-31
---

**SUPERSEDED FOR THE HOSTED SERVER (2026-08-26): manage it with `ck`, never `run.sh --stop`.**
The dev server this memory describes became a LAN-hosted systemd user service
(`ask-ck.service`, see [[askck-lan-hosting]]). `run.sh --stop/--restart` now pkills uvicorn
behind systemd's back — the unit self-heals via `Restart=always`, but the right commands are
`ck on|off|restart|reload|status|logs` (or `systemctl --user … ask-ck`). Everything below about
the ADMIN PANEL still holds and was re-verified 2026-08-26: its Restart button touches a
watched `.py` so `--reload` cycles the app **in-process** — the service MainPID does not exit,
so the button is safe against the hosted service by construction (measured: MainPID unchanged
across a reload). `run.sh` flags remain correct for a NON-hosted context (another checkout, a
scratch copy).

Ask CK server restart/admin was streamlined 2026-07-20 (uncommitted working tree; Terrence commits himself). See [[pending-approved-plans]].

**Fast restart — `run.sh` only, NOT `setup.sh`.** A plain restart starts against the existing `ask-ck/var/ck.db` in seconds. Flags: `run.sh --bg` (prompt-free background start), `run.sh --restart` (stop+start), `run.sh --stop`. `setup.sh` is ONLY for first-time setup (toolchain/venv/LFS pull + a DB sanity-check). **It does NOT rebuild the DB** — verified 2026-07-30, `setup.sh` contains no `build_db` call at all; `ck.db` is shipped, see [[db-is-permanent-source]]. The server runs with `--reload`, so code edits hot-reload without any restart. **2026-07-20: a root `./run.sh` wrapper now exists** (forwards to `ask-ck/CK-main/run.sh`, which self-anchors) — so `./run.sh --bg` from the repo root is the shortest path; either location works. README has a `setup.sh` vs `run.sh` decision table.

**Hidden admin panel:** **double-click CK's face** (`.sidebar-logo`, top-left) opens `#panel-admin` (single-click still goes Home). Module `static/js/admin.js`, backend `routers/admin.py` mounted at `/api/admin`. Actions (all confirm-gated): reset current-case / workspace-LLM / ALL sessions (session state only — corpora untouched); restart server (touches a watched `.py` so `--reload` fires, page reconnects ~2s). **Localhost/single-user only — no auth on `/api/admin/*`.**

**Why:** Terrence was running full `setup.sh` on every restart and wanted the vector-build + launch prompts gone, plus an in-page reset. **How to apply:** for a restart tell Terrence `run.sh --restart`; the admin panel covers session resets without a terminal.

**Corrected 2026-07-30:** this file used to list "rebuild embeddings" + "rebuild DB" as admin actions and called `setup.sh` a DB rebuild. Both were retired when `ck.db` became the permanent committed source — `routers/admin.py` and `static/js/admin.js` now carry explicit "DB REBUILD IS DELIBERATELY ABSENT" comments. Never restore a rebuild button; see [[db-is-permanent-source]].

**Caveat noted:** during testing the `reset-session scope=workspace` endpoint was curl'd against the REAL `ck.db`, clearing Terrence's workspace LLM default — he re-applied it. Future admin-endpoint testing should target a throwaway DB copy, not the live one.

**VERIFIED BY TERRENCE 2026-07-20:** admin panel works and "massively speeds the process"; radio reorder (Local LLM first + default, Grok de-parenthesized) confirmed; LLM config re-applied; live Fast/Thinking toggle confirmed working. All changes still uncommitted in the working tree — Terrence commits himself.

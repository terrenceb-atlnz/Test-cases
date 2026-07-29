---
name: ask-ck-admin-restart
description: "Ask CK fast-restart flags + hidden in-page admin panel (double-click CK's face)"
metadata: 
  node_type: memory
  type: project
  originSessionId: b69a0140-ff36-4d22-bc3a-819e30838064
  modified: 2026-07-20T01:01:57.863Z
---

Ask CK server restart/admin was streamlined 2026-07-20 (uncommitted working tree; Terrence commits himself). See [[pending-approved-plans]].

**Fast restart — `run.sh` only, NOT `setup.sh`.** A plain restart starts against the existing `ask-ck/var/ck.db` in seconds. Flags: `run.sh --bg` (prompt-free background start), `run.sh --restart` (stop+start), `run.sh --stop`. `setup.sh` is ONLY for first-time setup / DB rebuilds (it re-ingests every corpus, slow, prompts about embeddings). The server runs with `--reload`, so code edits hot-reload without any restart. **2026-07-20: a root `./run.sh` wrapper now exists** (forwards to `ask-ck/CK-main/run.sh`, which self-anchors) — so `./run.sh --bg` from the repo root is the shortest path; either location works. README has a `setup.sh` vs `run.sh` decision table.

**Hidden admin panel:** **double-click CK's face** (`.sidebar-logo`, top-left) opens `#panel-admin` (single-click still goes Home). Module `static/js/admin.js`, backend `routers/admin.py` mounted at `/api/admin`. Actions (all confirm-gated): reset current-case / workspace-LLM / ALL sessions (session state only — corpora untouched); rebuild embeddings (`build_db.py --embed`) + rebuild DB (`--fresh --verify --sessions`) as background jobs polled via `/api/admin/job`; restart server (touches a watched `.py` so `--reload` fires, page reconnects ~2s). **Localhost/single-user only — no auth on `/api/admin/*`.**

**Why:** Terrence was running full `setup.sh` (which rebuilds the DB) on every restart and wanted the vector-build + launch prompts gone, plus an in-page reset. **How to apply:** for a restart tell Terrence `run.sh --restart`; the admin panel covers resets/rebuilds without a terminal.

**Caveat noted:** during testing the `reset-session scope=workspace` endpoint was curl'd against the REAL `ck.db`, clearing Terrence's workspace LLM default — he re-applied it. Future admin-endpoint testing should target a throwaway DB copy, not the live one.

**VERIFIED BY TERRENCE 2026-07-20:** admin panel works and "massively speeds the process"; radio reorder (Local LLM first + default, Grok de-parenthesized) confirmed; LLM config re-applied; live Fast/Thinking toggle confirmed working. All changes still uncommitted in the working tree — Terrence commits himself.

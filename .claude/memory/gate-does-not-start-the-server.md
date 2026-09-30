---
name: gate-does-not-start-the-server
description: The gate (guards + pytest + Vitest) never starts the server, so a broken launch path, static mount or shell tool stays green — after any layout/anchor change, smoke-test on the SCRATCH server (ask-ck/tools/run_scratch_server.sh --bg, port 8123, throwaway DB copy) and probe /health, /, the modules and the routers; never the real one
metadata:
  type: feedback
  verified: 2026-09-30
---

**What happened (2026-09-11, the restructure):** nine batches of moves, gate green after every
sweep — and `run_scratch_server.sh` still called `$ROOT/tool/ckdb_scratch.py`, a path deleted
six commits earlier. The gate could not see it: nothing in it launches a server or runs the
shell tools, and the sweep regex had skipped `tool/` tokens preceded by a slash (`$ROOT/tool/`,
`./tool/`), so nine more pointers survived the same way.

**Why it matters:** "gate green" is a statement about the code the tests import, not about the
process Terrence starts with `ck on`. A launch-path, static-mount, template-path or shell-tool
break reaches the hosted server untested.

**How to apply:**
- After any change to paths, anchors, mounts, launch scripts or the layout: `./ask-ck/tools/run_scratch_server.sh --bg`
  (a WAL-consistent throwaway copy of ck.db on port 8123 — the sanctioned way; it never touches
  the permanent DB), wait for `/health`, then probe `/`, every served module, `/process`,
  `/setup/setup.sh`, the `/api/*/status` routes and `/health` (`is_permanent_db` must be false);
  stop it afterwards and confirm no uvicorn is left. Check `.ck-server-scratch.log` for tracebacks.
- **Stop it by its own PID group** (`kill -- -$(cat .ck-server-scratch.pid)`), not `--stop`, when
  there is any doubt about the pid file: `run.sh`'s `_stop_server` falls back to
  `pkill -f 'uvicorn CK_server.main'` when the pid file is missing or stale — and that matches
  PRODUCTION's uvicorn too (read 2026-09-30). Check the PID's args first (`ps -o pgid,args -g`).
- When sweeping a moved path mechanically, grep for the SLASH-PREFIXED forms too (`/old/`,
  `./old/`, `$VAR/old/`) — a lookbehind that excludes `/` to avoid double-prefixing silently
  skips exactly those.
- The stray-script hook matches the word `install` like `cp`/`mv`: a command that runs
  `npm install` and also names a `.py` file is refused. Split such commands.

Related: [[ckdb-wal-and-test-isolation]], [[askck-lan-hosting]], [[testing-suite-3-layer]].

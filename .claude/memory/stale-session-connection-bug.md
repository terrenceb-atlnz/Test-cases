---
name: stale-session-connection-bug
description: "Server returns HTTP 200 with new data that never reaches ck.db — thread-local SQLite connections go stale after external writes, and _pt_persist swallows failures"
metadata: 
  node_type: memory
  type: project
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-27T04:08:16.561Z
---

Hit repeatedly on 2026-07-27 while re-extracting sequences. **The server can return
HTTP 200 from `extract_sequence`/`save_sequence`/`generate_script` with correct new data
that NEVER reaches `ck.db`.** `updated_at` does not move; a later read returns the old
row; the in-memory session and the DB silently diverge.

**Cause:** `db.get_connection()` caches one SQLite connection per thread
(`threading.local()`, created once). If anything writes to `ck.db` from another process
while the server is up (a tool run, a manual fix), the server's long-lived connections
keep a stale WAL snapshot. `_pt_persist` then wraps `save_session` in
`try/except` that only `print`s — so the failure never surfaces as an error, and the
endpoint still returns 200 with the good data.

**Symptoms:** endpoint returns N steps, DB has the old count; `pt_grade` grades a stale
script; `updated_at` unchanged. Verified `save_session` works fine from a standalone
process, so it is the server's connection state, not the DB.

**Workaround:** `./run.sh --restart` before and after any external write to `ck.db`, then
redo the operation. Always verify a write landed by reading `updated_at` from a FRESH
connection — never trust the 200.

**Fix candidates (not done):** drop the thread-local cache or add a staleness check;
make `_pt_persist` raise (or return a status the handler surfaces) instead of printing.
Related pre-existing debt: PLAN-pytest-testing §9.4 dual-instance sessions.

See [[part3-grading-session]].

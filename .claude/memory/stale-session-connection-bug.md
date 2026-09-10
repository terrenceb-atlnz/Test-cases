---
name: stale-session-connection-bug
description: "Server returns HTTP 200 for a write that outside readers never see — ROOT CAUSE FOUND 2026-09-10: two SQLite libraries in one process (db.py pysqlite3 vs tool/cli_lookup.py stdlib) stripped the server's POSIX locks, so the WAL got deleted/corrupted under it; fixed in cli_lookup + guard test. Symptom + runbook here"
metadata: 
  node_type: memory
  type: project
  verified: 2026-09-10
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

**Workaround:** restart the server before and after any external write to `ck.db`, then redo
the operation. **For the LAN-hosted server that means `ck`/`systemctl --user restart
ask-ck.service` or the admin face-button — NOT `./run.sh --restart`.** (Correction 2026-09-09:
this memory used to say `./run.sh --restart`; on the hosted box a manual run.sh squats port 8000
and crash-loops the unit while localhost `/health` stays green — see [[askck-lan-hosting]]. The
old advice was load-bearing and wrong for the current deployment.) Always verify a write landed
by reading `updated_at`/`rev` from a FRESH connection — never trust the 200.

**ROOT CAUSE — found and fixed 2026-09-10.** The 2026-09-09 reading ("the same pattern escalates
to WAL corruption on NFS") had the mechanism wrong. `db.py` binds **pysqlite3** (SQLite 3.51);
`tool/cli_lookup.py`, imported by `routers/pytest_create.py` during every unit-prompt render,
opened `ck.db` with the **stdlib sqlite3** (3.37) — read-only, per call, GC-closed. POSIX
advisory locks belong to the *process* and each SQLite library keeps its own per-inode lock
accounting, so each stdlib close issued a real `F_UNLCK` that **removed every lock the server's
pysqlite3 connections held on `ck.db` and `ck.db-shm`**. Lockless: (1) any *read-write*
open+close of `ck.db` from another process unlinked `-wal`/`-shm` from under the server (NFS:
silly-rename → `.nfs*` orphans held by the server pid) — the server kept committing into a WAL
only it could read, outside readers went stale, new in-process connections split-brained
("disk I/O error" / "malformed" / "not a database"), and a restart dropped the orphan with every
un-checkpointed row (2026-09-09: three fixes, rev 446→444; 2026-09-10: one save, rev 467);
(2) the shm locks are the WAL write lock + reader marks, so concurrent fix-fan-out writers
could corrupt the WAL with **no outside process at all** (2026-09-09 ~13:47, and 2026-09-03).
Same bug on local disk; NFS only added the `.nfs*` signature.

**How it was found — reusable.** The live worker pid had **zero** `/proc/locks` entries on
`ck.db` while a throwaway WAL holder on the same NFSv4 mount showed both READ locks (db file +
shm) — so NFS locks *are* visible there and the server had lost its; its `-wal`/`-shm` fds pointed
at `.nfs*` orphans (`ls -l /proc/<pid>/fd`); base vs base+orphan copied to the scratchpad
differed in exactly one row. Five probes on throwaway dbs in `ask-ck/var/` pinned each step:
a plain `open()/close()` in the holder's process drops its db-file lock; a **read-only** peer
*cannot* delete the WAL (`F_WRLCK` on an `O_RDONLY` fd fails → the test gate and read-only
diagnostics are innocent); a **read-write** peer can; pysqlite3 holder + stdlib RO close → all
locks gone; same library both sides → locks kept.

**Fix + rules.** `cli_lookup` now binds `try: import pysqlite3 as sqlite3 / except ImportError:
import sqlite3` exactly as `db.py` and honours `CK_DB_PATH`; `tests/test_sqlite_single_library.py`
guards identity, statically scans every module that runs in the server process, replays the
incident on a tmp WAL db via `/proc/locks`, and has a negative control. Standing rules: **one
SQLite library per server process**; **never open the live `ck.db` read-write from another
process while the server runs** (`sqlite3` CLI, inline `sqlite3.connect`, corpus loaders — stop
the service first or use a copy; read-only URI opens are safe); verify a write from a *copy* of
base+`-wal`+`-shm`, never a live open. Runbook: `.nfs*` orphans in `ask-ck/var/` + zero server
locks = find the second opener, snapshot the cache-held session via
`GET /api/pytest-create/session/<key>` if you need its rows, then `ck reload`/restart. Plan record:
`ask-ck/pytest-create/PLAN-t44297-pass-followups.md` #5; WAL triage: [[ckdb-corrupt-wal-recovery]];
the isolation authority: [[ckdb-wal-and-test-isolation]].

**Still open (the original symptom's other half):** the thread-local connection cache with no
staleness check, and `_pt_persist` — it now raises (2026-07-28) but the reload-on-newer-DB path
still prints. Related debt: PLAN-pytest-testing §9.4 dual-instance sessions.

See [[part3-grading-session]].

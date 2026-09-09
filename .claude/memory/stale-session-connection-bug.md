---
name: stale-session-connection-bug
description: "Server returns HTTP 200 with new data that never reaches ck.db — thread-local SQLite connections go stale after external writes, and _pt_persist swallows failures; on the NFS share the same pattern ESCALATES to WAL corruption (2026-09-09)"
metadata: 
  node_type: memory
  type: project
  verified: 2026-09-09
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

**Escalation seen 2026-09-09 — the same pattern corrupts the WAL on NFS.** `ck.db` lives on the
NFS share in WAL mode. During a review-driven Fix on T44297 (three rapid CAS re-writes of a
~1.2 MB session row while a second browser session held the DB open for reads) the `-wal`/`-shm`
were unlinked while open → NFS silly-rename (`.nfs*` orphans held by the server pid) → every
disk-backed op returned *"file is not a database"*. The base survived; recovery was a restart;
**the un-checkpointed fixes were lost** (cache rev 446 vs disk 444) and had to be re-run. So the
"200 that never persists" is not only stale-snapshot silence — under concurrent load it is data
loss. Until the root fix lands, avoid concurrent sessions during a fix/generate and treat a 200
as provisional until a disk read shows the rev advanced. Recovery runbook + root-fix options
(move `ck.db` off NFS is the recommendation): `ask-ck/pytest-create/PLAN-t44297-pass-followups.md`
item #5; WAL triage method: [[ckdb-corrupt-wal-recovery]].

**Fix candidates (still not done):** drop the thread-local cache or add a staleness check; make
`_pt_persist` raise (or return a status the handler surfaces) instead of printing; and the
structural one — get the WAL-mode DB off the network filesystem. Related pre-existing debt:
PLAN-pytest-testing §9.4 dual-instance sessions.

See [[part3-grading-session]].

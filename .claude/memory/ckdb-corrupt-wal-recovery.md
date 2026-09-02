---
name: ckdb-corrupt-wal-recovery
description: If the gate aborts with "database disk image is malformed", the ck.db BASE is likely fine and only its WAL is corrupt — recover with tool/db_wal_recover.sh, never a bare sqlite3
metadata:
  node_type: memory
  type: reference
  verified: 2026-09-03
---

Symptom (seen 2026-09-03): the gate aborts before pytest with `ckdb_signature.py …
sqlite3.DatabaseError: database disk image is malformed`, and `PRAGMA integrity_check` on
`ask-ck/var/ck.db` shows structural damage.

**First check the base ALONE**, by copying only the main file (no `-wal`/`-shm` beside it):
`T=$(mktemp); cp ask-ck/var/ck.db "$T"; sqlite3 "$T" 'PRAGMA integrity_check;'; rm -f "$T"`.
`integrity_check` on the live file reads base+WAL together, so it can report malformed when
only the uncommitted WAL is bad and the committed base is intact (which is what happened).

**Recover with the tool, not by hand:** `tool/db_wal_recover.sh` (runbook
`tool/DB-WAL-RECOVERY.md`). It is fail-closed — refuses unless the base alone is `ok`, backs
up base+wal+shm first, stops the systemd unit with a transient `KillSignal=SIGKILL` drop-in
(no checkpoint) that also marks it inactive (`Restart=always` would otherwise respawn onto the
corrupt WAL), discards the WAL, verifies, restarts; restores + leaves the server stopped if
verification fails. Same script rehearses on a throwaway unit via `CK_RECOVER_SERVICE=` /
`CK_RECOVER_DB=`.

Two non-obvious facts:
- **A corrupt WAL fails to checkpoint**, so the base survives even a graceful stop — that is
  why the live server held the corrupt WAL for 19 h without damage. SIGKILL is conservative
  defense-in-depth (covers a partially-valid WAL), not the sole thing preventing catastrophe.
- **Never run a bare `sqlite3 ask-ck/var/ck.db` when you'd be the LAST connection to close.**
  A read-write open checkpoints on close and folds the corrupt WAL into the base. It destroyed
  a throwaway copy exactly this way. Probe on copies only. A live server holding the DB open
  incidentally protects it, but do not rely on that.

Relates to the DB-only invariant and the WAL-safe isolation authority `tests/test_db_isolation.py`.

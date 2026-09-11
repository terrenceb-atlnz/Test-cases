# Recovering ck.db from a corrupt WAL — runbook

**Tool:** [`tool/db_wal_recover.sh`](db_wal_recover.sh). **First used:** 2026-09-03.

## Symptom

The gate aborts before pytest with:

```
ckdb_signature.py ... sqlite3.DatabaseError: database disk image is malformed
```

and `PRAGMA integrity_check` on `ask-ck/var/ck.db` reports structural damage
(e.g. `On tree page 91 cell 0: 2nd reference to page 103657`, plus many `never used` pages).

## First: is the *base* actually damaged, or only the WAL?

`ck.db` runs in WAL mode ([db.py](../ask-ck/CK-main/CK_server/db.py) — `PRAGMA journal_mode=WAL`).
`integrity_check` on `ck.db` reads **base + WAL together**. Check the base **alone** by copying
only the main file (no `-wal`/`-shm` beside it) and checking the copy:

```bash
T=$(mktemp); cp ask-ck/var/ck.db "$T"; sqlite3 "$T" 'PRAGMA integrity_check;'; rm -f "$T"
```

- **base-only `ok`** → the corruption is in the uncommitted WAL overlay. The committed
  source of truth is intact; use this runbook to discard the WAL.
- **base-only NOT ok** → the base itself is damaged. STOP. This runbook does not apply;
  the tool refuses to run. Restore `ck.db` from Git LFS (`git checkout ask-ck/var/ck.db`)
  or from a backup, and treat any WAL data as lost.

> ⚠️ **Never run a bare `sqlite3 ask-ck/var/ck.db` on a corrupt-WAL DB that will be the
> LAST connection to close.** A read-write connection checkpoints on close, and if that is
> the last connection SQLite deletes the WAL. On 2026-09-03 a throwaway *copy* was
> destroyed exactly this way. The live server incidentally protects the real file by
> keeping a connection open, but do not rely on that — always probe on a **copy**. The
> tool does all its pre-stop probes on copies for this reason.

## The two traps a naive fix hits

The server is a **systemd user unit** (`ask-ck.service`, `Restart=always`,
`RestartSec=15`). Two things bite a "just kill it and delete the WAL":

1. **`Restart=always` → respawn.** A bare `kill -9` leaves the unit *active*; systemd
   respawns a new server within `RestartSec` and it reopens the DB. The stop must mark the
   unit **inactive** (an explicit `systemctl --user stop` does; `systemctl kill` does not).
2. **A checkpoint could apply valid leading WAL frames.** A *fully* corrupt WAL fails to
   checkpoint and leaves the base untouched — measured 2026-09-03: base-only stayed `ok`
   even after a naive graceful `systemctl stop`. But a WAL whose *leading* frames are valid
   could be partially applied by a checkpoint-on-close. So the stop is made a **SIGKILL**
   (no checkpoint attempted at all). Zero downside — the WAL is being discarded anyway.

The tool combines both: a transient drop-in makes `systemctl --user stop` deliver SIGKILL
to the whole control group (no checkpoint), and the explicit stop marks the unit inactive
(no respawn), opening a window with nothing holding the DB in which the WAL is removed.

## Run it

```bash
./tool/db_wal_recover.sh                 # real: ask-ck.service + ask-ck/var/ck.db
```

Fail-closed contract:
- Refuses unless **base-only** integrity is `ok` (never discards the WAL when the base is bad).
- Backs up `ck.db{,-wal,-shm}` to `ask-ck/var/wal-recover-backup-<stamp>/` before stopping.
- If post-discard integrity is not `ok`, **restores** base+wal+shm from that backup, re-arms
  normal service config, leaves the server **stopped**, and exits non-zero.
- On success: removes the drop-in, restarts the service, re-verifies `ok`.

After it finishes, confirm and re-baseline:

```bash
curl -s http://127.0.0.1:8000/health | grep is_permanent_db   # true
git status --porcelain ask-ck/var/ck.db                       # empty = base unchanged
./tool/run_tests.sh                                           # gate green again
```

Delete the backup dir once satisfied.

## Rehearse against a scratch unit (recommended before a real run)

The same script drives a throwaway unit, so the procedure can be proven end to end without
touching the real DB. Point a copy of the corrupt artifacts at a localhost unit and run the
tool with the two override env vars:

```bash
CK_RECOVER_SERVICE=ask-ck-scratchrec.service \
CK_RECOVER_DB=/path/to/scratch/ck.db \
CK_RECOVER_BACKUP_DIR=/path/to/scratch-backup \
  tool/db_wal_recover.sh
```

On 2026-09-03 this rehearsal (a `Restart=always` unit on `:8124` against a copy of the real
corrupt WAL) proved the base stayed `ok` through stop→discard→restart, and a negative
control confirmed the respawn/checkpoint reasoning above.

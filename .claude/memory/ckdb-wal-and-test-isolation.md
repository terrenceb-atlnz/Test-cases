---
name: ckdb-wal-and-test-isolation
description: ck.db is WAL-mode so md5/mtime of the main file CANNOT detect writes — use tool/ckdb_signature.py; real user traffic SHOULD dirty ck.db but test/smoke/E2E traffic must not (tool/run_scratch_server.sh)
metadata: 
  node_type: memory
  type: project
  originSessionId: 5eff94ba-b305-4e2c-8e60-efda5ba8e420
  modified: 2026-07-28T04:16:43.800Z
  verified: 2026-08-26
---

`ask-ck/var/ck.db` is **WAL-mode**. A committed write lands in `ask-ck/var/ck.db-wal` and
can leave the main file's bytes AND mtime untouched for a long time. So:

**`md5sum ask-ck/var/ck.db` cannot detect a write. Neither can `stat -c %Y`.** Use
`tool/ckdb_signature.py` (added 2026-07-28) — it asks SQLite, which reads main+WAL
together. Default mode is ~0.4s and covers schema + a full row hash of `sessions`, the only
table the running app writes. `--tables` adds row counts (~15s, NFS-bound); `--full` adds
per-table content hashes.

**Why:** on 2026-07-28 I "verified" that a test run had not touched ck.db by comparing
md5 of the main file before/after, and reported it byte-identical. It was worthless. In the
same session a mutated test **deleted the real session `AWPTCM-T30649`** from the permanent
DB; main-file mtime never changed and md5 still matched. Recovered from a `backup()` snapshot
in the scratchpad, verified by full-row hash (`30185cd466774462`, 39 sessions).

**Test isolation is now in place.** `tests/conftest.py` sets `CK_DB_PATH` to a per-run copy
at **import time** — it must be import time, because `db.get_connection()` caches one
connection per thread and resolves the path only on first use, so the first connection
opened wins. Two levels: a pristine snapshot cached in `/tmp/ck-test-db/` keyed on the real
file's `(size, mtime_ns)` and built with `Connection.backup()` (4.8s, only when ck.db
changes), then a plain `cp` per run (~0.3s, safe because backup() emits a single
checkpointed file with no -wal). `./tool/run_tests.sh` now fails if the signature changes.
Escape hatches: `CK_TEST_USE_REAL_DB=1`, or set `CK_DB_PATH` yourself.
Side effect: the suite got ~2-3x faster (12-19s → ~6s) because the corpus is now read from
local ext4 instead of over NFS.

**Two fail-closed layers now back the redirect** (commit `7e80289`), because one layer is
what failed:
1. `connect()` is wrapped to REFUSE any writable open of the real ck.db, independent of
   `CK_DB_PATH`. Read-only URI opens still pass.
2. `db.save_session`/`delete_session` refuse a key that could be real. Reserved namespace:
   `AWPTCM-T99980..T99999`, or a non-numeric suffix (`AWPTCM-TSTALE1`) — a real key is
   `AWPTCM-T` + digits ONLY. Runtime, not a lint: 11 of 12 destructive call sites in tests
   pass a variable.

**`db.py` does NOT use the stdlib sqlite3.** It does `try: import pysqlite3 as sqlite3`
(db.py:34-38 — pysqlite3 bundles a modern SQLite with `enable_load_extension` for
sqlite-vec), and pysqlite3 IS installed, so **`db.sqlite3 is not sqlite3`**. Patching or
monkeypatching stdlib `sqlite3` alone does not affect db.py at all. My first version of
layer 1 did exactly that and would have been a safeguard that looked right and did nothing.

**The governing distinction (Terrence, 2026-07-28):** *"ck.db is designed to go dirty when
users actually operate in it. When tests are run for smoke checks or E2E or whatever, that
data is useless and shouldn't be propagated."* So a dirty ck.db is **not** automatically a
problem — do not "fix" it by making real case loads stop persisting. What matters is the
SOURCE of the write. Two paths ran outside conftest's isolation and wrote the real DB:
Playwright (`webServer: './run.sh --bg'` + `reuseExistingServer: true` → attaches to the
dev server on :8000) and my own curl smoke checks. Both now use
**`tool/run_scratch_server.sh`** (CK_DB_PATH → a `backup()` copy, PORT 8123, CK_RUN_TAG for
its own pid/log). **Use it for anything that drives the app as a test would.**
`/health` reports `db.db_path` + `db.is_permanent_db` so you can tell which DB a server is
on. Guarded by `tests/test_test_traffic_never_writes_the_real_db.py`.

If test rows do land in ck.db: stop the server, `rm ck.db-wal ck.db-shm` **before**
`git checkout -- ask-ck/var/ck.db` (a stale WAL must not replay onto the restored file),
then verify with `tool/ckdb_signature.py`. Do not "just delete the WAL" — while
un-checkpointed it holds the NEWEST commits, not stale leftovers.

**How to apply:** never assert "ck.db untouched" from a file hash or mtime — use
`tool/ckdb_signature.py`. Never write a test that names a real session id; the incident test
picked `sorted(real_ids)[0]` and called `_clear_persisted` on it, reasoning isolation made
it safe. A test whose failure mode is destroying the source of truth is wrong at any
confidence level. When testing a safeguard, write the test as the **incident path** (break
the isolation, assert it raises), not as "does the guard work" — that framing is what
exposed the pysqlite3 bug. And do not mutation-test safety infrastructure while pointed at
live data; raise the plan first. See [[db-is-permanent-source]],
[[stale-session-connection-bug]], and [[mutate-before-you-claim]].

#!/usr/bin/env python3
"""Print a content signature for ask-ck/var/ck.db. Use this to check it is untouched.

WHY THIS EXISTS — a real incident, 2026-07-28.

To verify that a test run had not written to ck.db, `md5sum ask-ck/var/ck.db` was compared
before and after. It matched, and that was reported as "ck.db byte-identical". The check
was worthless: **ck.db runs in WAL mode**, so a committed write lands in `ck.db-wal` and
may not touch the main file for a long time. During that same session a mutated test
DELETED a real session row, `ck.db` main-file mtime never changed, and the md5 check
happily reported no change. The row was recovered from a snapshot.

Hashing the main file cannot detect a write to a WAL-mode database. Ask SQLite instead:
opening the DB reads main + WAL together, so a row-level signature sees everything.

    tool/ckdb_signature.py            # FAST (<1s): schema + full hash of the sessions table
    tool/ckdb_signature.py --tables   # add every table's row count (~15s, NFS-bound)
    tool/ckdb_signature.py --full     # add a content hash over every table (slow, ~440MB)

The default covers `sessions` only, because that is the ONLY table the running app
writes — the corpus tables are built once by tool/build_db.py and never mutated at
runtime. So the cheap signature is also the complete one for "did a test dirty the DB".

Exit code is always 0; compare the printed lines yourself, e.g.

    tool/ckdb_signature.py > /tmp/before.txt
    ./tool/run_tests.sh
    tool/ckdb_signature.py > /tmp/after.txt
    diff /tmp/before.txt /tmp/after.txt && echo "ck.db untouched"

Read-only by construction (`mode=ro`), so this can never be the thing that dirties the file.
"""
import hashlib
import pathlib
import sqlite3
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = REPO_ROOT / "ask-ck" / "var" / "ck.db"


def _connect() -> sqlite3.Connection:
    if not DB.exists():
        sys.exit(f"not found: {DB}")
    # mode=ro still reads the -wal, which is the whole point.
    return sqlite3.connect(f"file:{DB.resolve()}?mode=ro", uri=True)


def _hash_rows(con: sqlite3.Connection, sql: str) -> str:
    m = hashlib.sha256()
    for row in con.execute(sql):
        m.update(repr(row).encode())
    return m.hexdigest()[:16]


def main() -> None:
    args = sys.argv[1:]
    full = "--full" in args
    per_table = full or "--tables" in args
    con = _connect()
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    print(f"# ck.db signature — {len(tables)} tables"
          f"{' (full content hash)' if full else '' }"
          f"{'' if per_table else ' — sessions only; pass --tables for row counts'}")
    print(f"schema  {_hash_rows(con, 'SELECT name, sql FROM sqlite_master ORDER BY name')}")

    # The sessions table is the only one the app writes at runtime, so it always gets a
    # full row hash — that is what catches an inserted or deleted session.
    print(f"sessions_rows  {_hash_rows(con, 'SELECT id,kind,case_key,payload,llm_config,updated_at FROM sessions ORDER BY id')}")
    print(f"sessions_count  {con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]}")

    if not per_table:
        con.close()
        return

    for t in tables:
        try:
            n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except sqlite3.DatabaseError as e:      # FTS shadow tables can refuse COUNT
            print(f"{t}  <unreadable: {e}>")
            continue
        line = f"{t}  rows={n}"
        if full:
            try:
                line += f"  {_hash_rows(con, f'SELECT * FROM \"{t}\"')}"
            except sqlite3.DatabaseError as e:
                line += f"  <hash failed: {e}>"
        print(line)
    con.close()


if __name__ == "__main__":
    main()

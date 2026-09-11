#!/usr/bin/env python3
"""Make a THROWAWAY copy of ck.db and print its path, for a server that tests will drive.

    CK_DB_PATH="$(tool/ckdb_scratch.py)" ./run.sh --bg

Why this exists
---------------
`ask-ck/var/ck.db` going dirty is CORRECT when a person operates the app — a case load
writes a session row, and that is the tool doing its job. Data written by a TEST is the
opposite: worthless, and it must not propagate into the permanent, git-LFS-committed
source of truth.

The pytest suite has been isolated since `ac760fd`/`7e80289` (conftest redirects
CK_DB_PATH and a fail-closed connect() guard refuses any writable open of the real file).
Two paths were still writing it for real:

  * **Playwright E2E** — its webServer ran `./run.sh --bg` with `reuseExistingServer:
    true`, i.e. a normal server on the normal database, and it drives real case loads.
  * **Manual smoke checks** — curl against the dev server. On 2026-07-28 exactly that
    created a session row for AWPTCM-T45102 and bumped two more; the rows had to be
    discarded by restoring ck.db from git.

Both are fixed by pointing the server at a copy, which `db._resolve_db_path()` already
supports via CK_DB_PATH. This script makes that copy correctly.

Why `backup()` and not `cp`
---------------------------
ck.db runs in WAL mode. A copy of the main file alone is consistent only while the WAL
happens to be checkpointed, which is SQLite's schedule to decide, not ours —
`Connection.backup()` is consistent by construction and emits a single checkpointed file
with no `-wal` beside it. Same reasoning as `tests/conftest.py`, and the same reason
`tool/ckdb_signature.py` exists: any check or copy that looks at the main file alone
inherits a blind spot that has already cost this project a deleted session row.

The copy is cached under a key built from the (size, mtime_ns) of BOTH ck.db and
ck.db-wal, so a committed write that has not been checkpointed still invalidates it.
"""
import argparse
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
REAL_DB = REPO_ROOT / "ask-ck" / "var" / "ck.db"


def db_revision(real: pathlib.Path) -> str:
    """Cache key that can see a WAL write. See tests/conftest.py::_db_revision."""
    parts = []
    for p in (real, real.with_name(real.name + "-wal")):
        try:
            st = p.stat()
            parts.append(f"{st.st_size}-{st.st_mtime_ns}")
        except OSError:
            parts.append("0-0")
    return "-".join(parts)


def scratch_db(fresh: bool = False) -> pathlib.Path:
    if not REAL_DB.exists():
        sys.exit(f"ck.db not found at {REAL_DB} — run ./setup.sh (git lfs pull) first.")

    cache_dir = pathlib.Path(tempfile.gettempdir()) / "ck-scratch-db"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"pristine-{db_revision(REAL_DB)}.db"

    if cached.exists() and not fresh:
        target = cache_dir / "scratch.db"
        shutil.copyfile(cached, target)          # safe: backup() left no -wal beside it
        return target

    # Build under a temp name and rename, so a concurrent run never sees a half-written
    # snapshot under the final key.
    tmp = cached.with_suffix(f".partial-{os.getpid()}")
    src = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    os.replace(tmp, cached)
    for old in cache_dir.glob("pristine-*.db"):
        if old != cached:
            old.unlink(missing_ok=True)

    target = cache_dir / "scratch.db"
    shutil.copyfile(cached, target)
    return target


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fresh", action="store_true",
                    help="rebuild the cached snapshot even if one matches")
    args = ap.parse_args()
    print(scratch_db(fresh=args.fresh))


if __name__ == "__main__":
    main()

"""One SQLite library per server process — the lock-stripping bug of 2026-09-10.

db.py binds `sqlite3` to pysqlite3 when it is installed (it is, here), so every server
connection to ck.db comes from that library. tool/cli_lookup.py — imported by
routers/pytest_create.py while rendering unit prompts — used to open ck.db through the
STDLIB sqlite3, read-only, a fresh connection per call, a dozen call sites.

POSIX advisory locks belong to the PROCESS, not the descriptor, and each SQLite library keeps
its own per-inode lock bookkeeping. So when the stdlib connection closed, that library saw "my
last connection on this inode" and issued a real F_UNLCK — which released every lock the
pysqlite3 connections held on ck.db and ck.db-shm. Lockless, the live server's WAL could be
deleted from under it by any read-write open from another process (the orphaned-WAL data
loss of 2026-09-09/10: writes visible only to the server, lost on restart), and two writer
threads could corrupt it with no outside help ("database disk image is malformed" during the
2026-09-09 fan-out fix). Each step was reproduced with throwaway databases before the fix.

Three checks, from decisive to structural:

  * test_server_imported_modules_bind_the_same_sqlite_module — identity (`is`), not name:
    `cli_lookup.sqlite3 is db.sqlite3` is the whole fix.
  * test_second_connection_closing_keeps_the_holders_locks — the incident path on a throwaway
    WAL database, observed through /proc/locks. Its negative control proves the check can
    see the bug at all: with pysqlite3 installed, a STDLIB connection closing DOES strip the
    holder's locks (mutate-before-you-claim).
  * test_no_server_imported_module_imports_stdlib_sqlite3_directly — static, so a module the
    test process never happens to import is still caught, and a future tool module the server
    starts importing inherits the rule automatically.
"""
import os
import pathlib
import re
import sqlite3 as stdlib_sqlite3
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CK_SERVER = _REPO_ROOT / "ask-ck" / "CK-main" / "CK_server"
_TOOL_DIR = _REPO_ROOT / "tool"
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

# db.py's preference block, verbatim. Any server-process module that needs SQLite must use it.
_PREFERENCE_BLOCK = re.compile(
    r"try:\s*\n\s*import pysqlite3 as sqlite3.*\n\s*except ImportError:\s*\n\s*import sqlite3",
)
_IMPORT_RX = re.compile(r"^\s*(?:import\s+(\w+)|from\s+(\w+)\s+import)", re.MULTILINE)
_STDLIB_SQLITE_RX = re.compile(r"^\s*(?:import sqlite3\b|from sqlite3 import)", re.MULTILINE)


def _server_sources():
    return sorted(p for p in _CK_SERVER.rglob("*.py") if "__pycache__" not in p.parts)


def _tool_modules_the_server_imports():
    """tool/*.py module names imported anywhere under CK_server (today: cli_lookup)."""
    tool_stems = {p.stem for p in _TOOL_DIR.glob("*.py")}
    found = set()
    for src in _server_sources():
        for m in _IMPORT_RX.finditer(src.read_text(encoding="utf-8")):
            name = m.group(1) or m.group(2)
            if name in tool_stems:
                found.add(name)
    return sorted(found)


def _server_process_sources():
    """Every source file whose code runs inside the server process."""
    return _server_sources() + [_TOOL_DIR / f"{m}.py" for m in _tool_modules_the_server_imports()]


def test_the_server_still_imports_cli_lookup():
    # The hazard this file exists for. If the server stops importing cli_lookup on purpose,
    # delete this test — the other three keep guarding whatever replaces it.
    assert "cli_lookup" in _tool_modules_the_server_imports()


def test_server_imported_modules_bind_the_same_sqlite_module():
    import db
    import cli_lookup

    assert cli_lookup.sqlite3 is db.sqlite3, (
        "cli_lookup opens ck.db through a different SQLite library than db.py. Two libraries in "
        "one process keep separate lock bookkeeping; closing one strips the other's POSIX "
        "locks and the server's WAL becomes deletable/corruptible. Use db.py's preference block."
    )
    for name in _tool_modules_the_server_imports():
        mod = __import__(name)
        bound = getattr(mod, "sqlite3", None)
        if bound is not None:
            assert bound is db.sqlite3, f"{name}.sqlite3 is not db.sqlite3"


def test_no_server_imported_module_imports_stdlib_sqlite3_directly():
    offenders = []
    for src in _server_process_sources():
        text = src.read_text(encoding="utf-8")
        if not _STDLIB_SQLITE_RX.search(text):
            continue
        if not _PREFERENCE_BLOCK.search(text):
            offenders.append(str(src.relative_to(_REPO_ROOT)))
    assert not offenders, (
        "These modules run inside the server process and import the stdlib sqlite3 outside "
        "db.py's `try: import pysqlite3 as sqlite3 / except ImportError: import sqlite3` block: "
        f"{offenders}"
    )


# ---------------------------------------------------------------------------
# The incident path, on a throwaway database
# ---------------------------------------------------------------------------
def _locks_held_by_me_on(paths):
    """Set of inodes among `paths` that this process holds a POSIX lock on (Linux)."""
    inodes = set()
    for p in paths:
        try:
            inodes.add(os.stat(p).st_ino)
        except FileNotFoundError:
            pass
    held = set()
    with open("/proc/locks") as fh:
        for line in fh:
            parts = line.split()
            # "N: POSIX ADVISORY READ <pid> <maj>:<min>:<ino> <start> <end>"
            if len(parts) < 6 or parts[4] != str(os.getpid()):
                continue
            ino = int(parts[5].split(":")[-1])
            if ino in inodes:
                held.add(ino)
    return held


def _wal_holder(lib, path):
    """An idle WAL-mode connection: it holds SHARED on the db file for its whole life."""
    h = lib.connect(str(path), check_same_thread=False)
    h.execute("PRAGMA journal_mode=WAL")
    h.execute("CREATE TABLE t(x)")
    h.execute("INSERT INTO t VALUES (1)")
    h.commit()
    list(h.execute("SELECT * FROM t"))          # consume the cursor: no open read txn
    return h


@pytest.fixture
def proc_locks():
    if not os.path.exists("/proc/locks"):
        pytest.skip("/proc/locks is how this test observes POSIX locks (Linux only)")


def test_second_connection_closing_keeps_the_holders_locks(tmp_path, proc_locks, monkeypatch):
    """cli_lookup's read-only open+close must leave the server's locks exactly as they were."""
    import db
    import cli_lookup

    dbfile = tmp_path / "probe.db"
    holder = _wal_holder(db.sqlite3, dbfile)
    try:
        watched = [dbfile, tmp_path / "probe.db-shm"]
        before = _locks_held_by_me_on(watched)
        assert before, "holder took no lock — the probe setup is wrong, not the code"

        monkeypatch.setattr(cli_lookup, "DB", dbfile)
        c = cli_lookup._conn()                      # the real code path, read-only
        list(c.execute("SELECT count(*) FROM t"))
        c.close()

        after = _locks_held_by_me_on(watched)
        assert after == before, (
            f"closing cli_lookup's connection changed the holder's locks: {before} -> {after}"
        )
    finally:
        holder.close()


def test_negative_control_a_second_library_does_strip_the_locks(tmp_path, proc_locks):
    """Proves the check above can see the bug: with pysqlite3 installed, a STDLIB connection
    closing in the same process removes the pysqlite3 holder's locks. If this ever fails, the
    platform changed (a shared libsqlite3, or pysqlite3 gone) — re-examine, don't delete."""
    import db

    if db.sqlite3 is stdlib_sqlite3:
        pytest.skip("pysqlite3 not installed here — only one SQLite library exists")

    dbfile = tmp_path / "probe.db"
    holder = _wal_holder(db.sqlite3, dbfile)
    try:
        watched = [dbfile, tmp_path / "probe.db-shm"]
        before = _locks_held_by_me_on(watched)
        assert before
        c = stdlib_sqlite3.connect(f"file:{dbfile}?mode=ro", uri=True)
        list(c.execute("SELECT count(*) FROM t"))
        c.close()
        after = _locks_held_by_me_on(watched)
        assert after != before, "the second library did not strip the locks — control failed"
    finally:
        holder.close()

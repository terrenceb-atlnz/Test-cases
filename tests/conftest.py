"""Shared fixtures for the Ask CK backend tests.

Provides a FastAPI TestClient over the real app. Importing the app pulls in the DB
layer (ck.db is the committed source of truth and present in a normal checkout), so
these are in-process integration tests, not mocks.

Note on interpreter: run with `PYTHONNOUSERSITE=1 .venv/bin/pytest` so an older
fastapi/starlette in ~/.local can't shadow the venv's. pytest.ini sets pythonpath;
this file also prepends both dirs defensively for direct `python -m pytest` runs.
"""
import atexit
import functools
import os
import pathlib
import re
import shutil
import sqlite3
import sys
import tempfile
import urllib.parse

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CK_MAIN = _REPO_ROOT / "ask-ck" / "CK-main"
_CK_SERVER = _CK_MAIN / "CK_server"
for _p in (str(_CK_MAIN), str(_CK_SERVER)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# ck.db isolation — the test suite must never write to the source of truth.
#
# `ask-ck/var/ck.db` is built ONCE and committed via git-LFS; it is the permanent
# runtime source. Several suites legitimately exercise session persistence
# (test_confirm_step_validation, test_export_gate, test_export_authority_batch_a,
# test_pydantic_v2_and_logging, test_pt_session_staleness, test_tz_aware_timestamps),
# and before this fixture those writes landed in the real file. They cleaned up after
# themselves, so no row was lost — but every gate run left ck.db byte-dirty, which
# invites a 440 MB LFS blob into an unrelated commit, and a crashing test could strand
# a throwaway session in the permanent DB.
#
# THIS MUST RUN AT IMPORT TIME, not in a fixture. `db.get_connection()` caches one
# connection per thread in `threading.local()` and resolves the path only on first use
# (`db._resolve_db_path()`), so whichever file the first connection opens is the file
# that thread keeps for its lifetime. conftest is imported before any test module, so
# this is the last point at which the choice is still ours.
#
# WHY backup() AND NOT `cp`: ck.db runs in WAL mode with a live multi-MB `ck.db-wal`.
# A copy of `ck.db` alone is consistent only if the WAL happens to have been fully
# checkpointed. Measured honestly: right now it HAS been, so a plain `cp` currently
# produces an identical logical snapshot — the claim "cp loses data" does not reproduce
# on this seat today. But SQLite checkpoints on its own schedule (autocheckpoint at
# 1000 pages), so that is a coincidence of timing, not a property. `backup()` is
# consistent by construction and removes the question; it also emits a single
# checkpointed file with no -wal beside it, which is what makes the cheap per-run `cp`
# below safe. Costs measured here: backup() 4.8s / VACUUM INTO 11.5s / plain cp 1.2s.
#
# Two levels, so the cost is paid only when ck.db actually changes:
#   1. a PRISTINE cache keyed by _db_revision() — 4.8s, rebuilt only when ck.db changes;
#   2. a per-run copy from that cache — ~0.3s, and a plain `cp` is safe here precisely
#      because backup() emits a single checkpointed file with no -wal alongside it.
# The per-run file is pid-suffixed so a concurrent gate run (another stream on this
# seat does run pytest) cannot share or clobber it.
#
# Escape hatches: set CK_DB_PATH yourself to point somewhere specific, or
# CK_TEST_USE_REAL_DB=1 to deliberately run against ask-ck/var/ck.db.
# ---------------------------------------------------------------------------
_REAL_DB = _REPO_ROOT / "ask-ck" / "var" / "ck.db"


def _db_revision(real: pathlib.Path) -> str:
    """Cache key that can SEE a write. Must include the -wal file, and here is why.

    The key was (size, mtime_ns) of ck.db alone, and that CANNOT detect a committed
    write. ck.db is WAL-mode: a transaction lands in `ck.db-wal` and SQLite may not
    checkpoint it back for a long time, so the main file's bytes AND mtime stay exactly
    as they were. Measured on 2026-07-28 after three live case loads: ck.db mtime
    13:20:12 unchanged with 440578048 bytes, while ck.db-wal was 4.1 MB at 15:04 and the
    session count had gone 39 -> 40. The cache key was byte-identical, so the stale
    snapshot was served and the suite ran against superseded data.

    This is the SAME blind spot that hid the AWPTCM-T30649 deletion, where `md5sum
    ask-ck/var/ck.db` reported "byte-identical" throughout (see SESSION_STATE.md
    2026-07-28e, and tool/ckdb_signature.py, which exists because of it). Any check on
    the main file alone inherits it.

    Including the WAL's (size, mtime_ns) closes it: a commit appends to the WAL, so both
    move; a checkpoint rewrites the main file and resets the WAL, so both move again.
    Missing -wal is a legitimate state (fully checkpointed, or a fresh clone), keyed as
    0-0 rather than being an error.

    `tests/test_db_isolation.py::test_the_copy_reflects_the_current_real_db` is what
    caught this, and it is what stops it coming back.
    """
    parts = []
    for p in (real, real.with_name(real.name + "-wal")):
        try:
            st = p.stat()
            parts.append(f"{st.st_size}-{st.st_mtime_ns}")
        except OSError:
            parts.append("0-0")
    return "-".join(parts)


def _pristine_cache(real: pathlib.Path) -> pathlib.Path:
    """A WAL-consistent snapshot of `real`, reused until `real` changes."""
    cache_dir = pathlib.Path(tempfile.gettempdir()) / "ck-test-db"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"pristine-{_db_revision(real)}.db"
    if cached.exists():
        return cached
    # Build under a temp name and rename, so a concurrent run never observes a
    # half-written snapshot under the final key.
    tmp = cached.with_suffix(f".partial-{os.getpid()}")
    src = sqlite3.connect(f"file:{real}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    os.replace(tmp, cached)
    # Drop snapshots of older ck.db revisions; keep the current one.
    for old in cache_dir.glob("pristine-*.db"):
        if old != cached:
            old.unlink(missing_ok=True)
    return cached


def _isolate_db() -> None:
    if os.environ.get("CK_TEST_USE_REAL_DB") == "1":
        return
    if os.environ.get("CK_DB_PATH"):
        return                      # caller already chose a target; respect it
    if not _REAL_DB.exists():
        return                      # no DB to copy; tests degrade as they already do
    run_dir = pathlib.Path(tempfile.mkdtemp(prefix="ck-test-run-"))
    run_db = run_dir / "ck.db"
    shutil.copyfile(_pristine_cache(_REAL_DB), run_db)
    os.environ["CK_DB_PATH"] = str(run_db)
    atexit.register(shutil.rmtree, run_dir, ignore_errors=True)


_isolate_db()


# ---------------------------------------------------------------------------
# LAYER 1 — fail-closed guard: refuse any WRITABLE open of the real ck.db.
#
# `_isolate_db()` above redirects CK_DB_PATH, and that was the ONLY thing standing
# between the suite and the permanent DB. It is not enough, because it can be wrong:
# on 2026-07-28 the isolation was deliberately disabled to mutation-test the guards in
# tests/test_db_isolation.py, and a test that named a real session id then DELETED
# `AWPTCM-T30649` out of ask-ck/var/ck.db for real. (Recovered from a snapshot — luck,
# not design.)
#
# This layer does not depend on the isolation being correct. It hooks the single choke
# point — `sqlite3.connect`, which db.py's module docstring already documents as the only
# place a connection is opened — and refuses a writable open of the real file whatever the
# reason: isolation missing, mutated, or bypassed by some future code path. Read-only URI
# opens still pass, so tests can legitimately inspect the real DB.
#
# Fails LOUDLY rather than silently redirecting: a redirect would hide a broken isolation
# for as long as the tests happened to pass anyway.
#
# IT IS NOT ENOUGH TO PATCH THE STDLIB `sqlite3`. db.py opens its connections through
#     try: import pysqlite3 as sqlite3
#     except ImportError: import sqlite3
# (db.py:34-38 — pysqlite3 bundles a modern SQLite WITH enable_load_extension, which
# sqlite-vec needs). pysqlite3 IS installed here, so `db.sqlite3 is not sqlite3` and a
# guard on the stdlib module alone never sees db.py's connect at all. The first version of
# this guard did exactly that and would NOT have prevented the incident it was written for;
# test_broken_isolation_now_fails_loudly_instead_of_writing caught it. So patch every
# sqlite module that is actually reachable.
# ---------------------------------------------------------------------------
_REAL_DB_RESOLVED = str(_REAL_DB.resolve()) if _REAL_DB.exists() else None


def _connect_target(database, uri: bool):
    """(resolved path, sqlite open mode) for a connect() target, or None if not a file."""
    if not isinstance(database, (str, os.PathLike)):
        return None                      # an int fd or similar; nothing to resolve
    text = os.fspath(database)
    if text == ":memory:" or text.startswith("file::memory:"):
        return None
    if uri or text.startswith("file:"):
        parts = urllib.parse.urlparse(text)
        path = urllib.parse.unquote(parts.path)
        query = urllib.parse.parse_qs(parts.query)
        if not path:
            return None
        # No explicit mode means read-write-create, same as a bare path.
        mode = (query.get("mode") or ["rwc"])[0]
        return str(pathlib.Path(path).resolve()), mode
    return str(pathlib.Path(text).resolve()), "rwc"


def _make_guarded_connect(original):
    @functools.wraps(original)
    def guarded(database, *args, **kwargs):
        target = _connect_target(database, bool(kwargs.get("uri")))
        if (target and _REAL_DB_RESOLVED
                and target[0] == _REAL_DB_RESOLVED and target[1] != "ro"):
            raise RuntimeError(
                "REFUSED: writable connect() to the REAL ck.db during tests.\n"
                f"  target: {target[0]} (mode={target[1]})\n"
                "  ask-ck/var/ck.db is built once and committed via git-LFS; it is the\n"
                "  permanent source of truth and the suite must never write to it.\n"
                "  Tests run against the isolated copy that tests/conftest.py creates and\n"
                "  points CK_DB_PATH at. If you are seeing this, that isolation is broken:\n"
                "  check that _isolate_db() still runs at conftest IMPORT time, because\n"
                "  db.get_connection() caches one connection per thread and resolves the\n"
                "  path only on first use.\n"
                "  To read the real DB on purpose, open it read-only:\n"
                "      connect(f'file:{path}?mode=ro', uri=True)\n"
                "  To run the whole suite against the real DB on purpose: "
                "CK_TEST_USE_REAL_DB=1"
            )
        return original(database, *args, **kwargs)

    guarded._ck_guarded = True
    return guarded


def _sqlite_modules():
    """Every sqlite module whose connect() could reach ck.db.

    stdlib `sqlite3` plus whatever db.py actually bound as `sqlite3` — pysqlite3 when it
    is installed. Importing db here is safe and cheap: it opens no connection until
    get_connection() is first called, and CK_DB_PATH is already set by now.
    """
    mods = {sqlite3}
    try:
        import db as _db

        mods.add(_db.sqlite3)
    except Exception:                    # pragma: no cover - db import guarded elsewhere
        pass
    return mods


def _install_connect_guard() -> None:
    for mod in _sqlite_modules():
        if getattr(mod.connect, "_ck_guarded", False):
            continue
        mod.connect = _make_guarded_connect(mod.connect)


# ---------------------------------------------------------------------------
# LAYER 3 — refuse a destructive session write under a key that could be REAL.
#
# Layer 1 stops writes reaching the real FILE. This stops the mistake one step earlier:
# aiming a destructive call at a real session id at all. The incident test did
#
#     victim = next(i for i in sorted(real_ids) if i.startswith("AWPTCM-"))
#     wizard._clear_persisted(victim)
#
# which is fine right up until the isolation is not there. 11 of the suite's 12 destructive
# call sites pass a VARIABLE, so a static lint over literals would have covered one of
# twelve — this has to be a runtime check. It goes at db.py's own choke point so every
# caller (wizard's `db.save_session`, pytest_create's `dbx.save_session`) is covered once.
#
# Reserved namespace, matching the convention the suite already follows:
#   * AWPTCM-T99980..T99999  — reserved numeric block (T99989-T99995 in use today)
#   * AWPTCM-T<non-digits>   — TSTALE1, TTZ1, TSTAMP, TFAIL: a real case key is
#                              AWPTCM-T followed by digits ONLY, so these cannot collide
# Anything else — notably a real key like AWPTCM-T30649 — is refused.
# ---------------------------------------------------------------------------
_REAL_SHAPED_KEY = re.compile(r"^(?:pt-)?AWPTCM-T(\d+)$")
_RESERVED_BLOCK = range(99980, 100000)


def _is_throwaway_key(key) -> bool:
    if not isinstance(key, str):
        return False
    if key == "_workspace_llm":
        return True                      # the workspace row, not a case
    m = _REAL_SHAPED_KEY.match(key)
    if not m:
        return True                      # cannot be a real case key
    return int(m.group(1)) in _RESERVED_BLOCK


def _guard_session_writes() -> None:
    import db

    def wrap(fn, verb):
        @functools.wraps(fn)
        def inner(kind, key, *args, **kwargs):
            if not _is_throwaway_key(key):
                raise AssertionError(
                    f"REFUSED: a test tried to {verb} session {key!r}, which is shaped "
                    f"like a REAL case key.\n"
                    f"  Tests may only write or delete throwaway sessions. Use a key in "
                    f"the reserved block AWPTCM-T99980..T99999, or a non-numeric suffix "
                    f"(e.g. AWPTCM-TMYTEST) which can never be a real case.\n"
                    f"  A test that names a real session id destroys the source of truth "
                    f"the moment the ck.db isolation is not in place — that is exactly how "
                    f"AWPTCM-T30649 was deleted on 2026-07-28."
                )
            return fn(kind, key, *args, **kwargs)

        return inner

    db.save_session = wrap(db.save_session, "persist")
    db.delete_session = wrap(db.delete_session, "delete")


if os.environ.get("CK_TEST_USE_REAL_DB") == "1":
    # Say so, loudly. This one variable disables ALL THREE protections at once —
    # the CK_DB_PATH redirect, the fail-closed connect guard, and the reserved-key
    # check — so the suite writes straight to the permanent source of truth. Silence
    # here is how someone discovers it from a `git status` diff hours later.
    sys.stderr.write(
        "\n"
        "!! CK_TEST_USE_REAL_DB=1 — ck.db PROTECTIONS ARE OFF.\n"
        "!! The suite will read AND WRITE ask-ck/var/ck.db, the permanent git-LFS\n"
        "!! source of truth. Snapshot first:\n"
        "!!     tool/ckdb_signature.py > /tmp/before.txt\n"
        "!! and verify afterwards. Unset the variable to restore isolation.\n"
        "\n"
    )
else:
    _install_connect_guard()
    _guard_session_writes()


@pytest.fixture(scope="session")
def client():
    try:
        from fastapi.testclient import TestClient
    except Exception as e:  # pragma: no cover - env guard
        pytest.skip(f"TestClient unavailable ({e}); install requirements-dev.txt with the venv interpreter")
    import CK_server.main as main
    with TestClient(main.app) as c:
        yield c


def pytest_report_header(config):
    """Always state which ck.db the run is using, and shout if it is the real one.

    The stderr banner above is written at import time, which pytest CAPTURES — it only
    appears with `-s`, i.e. never during `./tool/run_tests.sh`. That made it useless
    exactly when it mattered. This hook is printed uncaptured at the top of every run.
    """
    if os.environ.get("CK_TEST_USE_REAL_DB") == "1":
        return [
            "ck.db: *** REAL DATABASE, PROTECTIONS OFF (CK_TEST_USE_REAL_DB=1) ***",
            "ck.db: writes go to ask-ck/var/ck.db — snapshot with tool/ckdb_signature.py",
        ]
    target = os.environ.get("CK_DB_PATH")
    if not target:
        return ["ck.db: *** NOT ISOLATED — CK_DB_PATH unset (real ck.db missing?) ***"]
    return [f"ck.db: isolated copy at {target}"]

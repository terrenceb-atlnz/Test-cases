"""Shared fixtures for the Ask CK backend tests.

Provides a FastAPI TestClient over the real app. Importing the app pulls in the DB
layer (ck.db is the committed source of truth and present in a normal checkout), so
these are in-process integration tests, not mocks.

Note on interpreter: run with `PYTHONNOUSERSITE=1 .venv/bin/pytest` so an older
fastapi/starlette in ~/.local can't shadow the venv's. pytest.ini sets pythonpath;
this file also prepends both dirs defensively for direct `python -m pytest` runs.
"""
import atexit
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile

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
#   1. a PRISTINE cache keyed by (size, mtime_ns) of the real file — 4.8s, rebuilt only
#      when ck.db is replaced;
#   2. a per-run copy from that cache — ~0.3s, and a plain `cp` is safe here precisely
#      because backup() emits a single checkpointed file with no -wal alongside it.
# The per-run file is pid-suffixed so a concurrent gate run (another stream on this
# seat does run pytest) cannot share or clobber it.
#
# Escape hatches: set CK_DB_PATH yourself to point somewhere specific, or
# CK_TEST_USE_REAL_DB=1 to deliberately run against ask-ck/var/ck.db.
# ---------------------------------------------------------------------------
_REAL_DB = _REPO_ROOT / "ask-ck" / "var" / "ck.db"


def _pristine_cache(real: pathlib.Path) -> pathlib.Path:
    """A WAL-consistent snapshot of `real`, reused until `real` changes."""
    st = real.stat()
    cache_dir = pathlib.Path(tempfile.gettempdir()) / "ck-test-db"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"pristine-{st.st_size}-{st.st_mtime_ns}.db"
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


@pytest.fixture(scope="session")
def client():
    try:
        from fastapi.testclient import TestClient
    except Exception as e:  # pragma: no cover - env guard
        pytest.skip(f"TestClient unavailable ({e}); install requirements-dev.txt with the venv interpreter")
    import CK_server.main as main
    with TestClient(main.app) as c:
        yield c

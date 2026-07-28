"""Test traffic must never reach `ask-ck/var/ck.db`. Real user traffic is meant to.

The distinction, stated by Terrence 2026-07-28: **ck.db is designed to go dirty when a
person actually operates the app** — a case load persists a session row, and that is the
tool working. Data written by a smoke check or an E2E run is worthless, and it must not
propagate into the permanent, git-LFS-committed source of truth.

The in-process suite has been isolated since `ac760fd`/`7e80289` (conftest redirects
CK_DB_PATH; a fail-closed connect() guard refuses any writable open of the real file;
db.save_session/delete_session refuse a real-shaped key). Those cover THIS process. Two
paths ran outside it and wrote the real database for real:

  * **Playwright E2E** — `webServer` was `./run.sh --bg` on port 8000 with
    `reuseExistingServer: true`, i.e. "attach to whatever is already on 8000", which on a
    developer's seat is the real-database dev server. E2E drives real case loads.
  * **Manual smoke checks** — curl against the dev server after a refactor. On 2026-07-28
    that created a session row for AWPTCM-T45102 and bumped two more stamps; they had to be
    discarded by restoring ck.db from git.

Both now go through `tool/run_scratch_server.sh`, which points CK_DB_PATH at a
WAL-consistent copy. These tests guard that wiring, because it lives in config and shell —
neither of which any other test reads, and a silent revert to port 8000 + reuse would look
exactly like a working E2E suite.
"""
import pathlib
import re
import subprocess
import sys

import pytest

from _prose import code_lines

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PW_CONFIG = _ROOT / "playwright.config.js"
_SCRATCH_SH = _ROOT / "tool" / "run_scratch_server.sh"
_SCRATCH_PY = _ROOT / "tool" / "ckdb_scratch.py"
_REAL_DB = _ROOT / "ask-ck" / "var" / "ck.db"


# --- the E2E wiring ----------------------------------------------------------

def test_e2e_launches_the_scratch_server_not_the_real_one():
    src = _PW_CONFIG.read_text(encoding="utf-8")
    assert "run_scratch_server.sh" in src, (
        "playwright.config.js no longer starts tool/run_scratch_server.sh, so E2E drives a "
        "server on the PERMANENT ck.db and every run writes session rows into it")
    assert "'./run.sh --bg'" not in src, "webServer is back to the real-database launcher"


def test_e2e_does_not_reuse_an_existing_server():
    """`reuseExistingServer: true` is the sharp edge, not the port.

    With it, Playwright attaches to whatever answers the URL — so a developer with the real
    dev server already up gets their permanent ck.db written to, and the scratch launcher is
    never even executed.
    """
    src = _PW_CONFIG.read_text(encoding="utf-8")
    assert re.search(r"reuseExistingServer:\s*false", src), (
        "reuseExistingServer must be false: true means 'attach to whatever is on this URL', "
        "which is how E2E ended up writing the real ck.db")


def test_e2e_runs_on_its_own_port():
    """Defence in depth behind reuseExistingServer:false — a distinct port means even a
    mistaken reuse cannot land on the dev server."""
    src = _PW_CONFIG.read_text(encoding="utf-8")
    assert "8123" in src, "the E2E port is no longer distinct from the dev server's 8000"
    assert not re.search(r"localhost:8000", src), (
        "playwright.config.js points at port 8000, the dev server's port")


# --- the scratch launcher ----------------------------------------------------

def test_the_scratch_launcher_redirects_the_db_and_isolates_its_pidfile():
    sh = _SCRATCH_SH.read_text(encoding="utf-8")
    assert "CK_DB_PATH" in sh and "ckdb_scratch.py" in sh, (
        "run_scratch_server.sh must point CK_DB_PATH at a throwaway copy")
    assert "CK_RUN_TAG" in sh, (
        "the scratch server needs its own pid/log files, or `run.sh --stop` on one will "
        "stop or orphan the other")


def test_run_sh_honours_the_pidfile_tag():
    """The launcher's isolation only works if run.sh actually reads CK_RUN_TAG."""
    sh = (_ROOT / "ask-ck" / "CK-main" / "run.sh").read_text(encoding="utf-8")
    assert "CK_RUN_TAG" in sh, "run.sh ignores CK_RUN_TAG, so both servers share one pidfile"


def test_the_scratch_launcher_is_executable():
    assert _SCRATCH_SH.stat().st_mode & 0o111, f"{_SCRATCH_SH.name} is not executable"
    assert _SCRATCH_PY.stat().st_mode & 0o111, f"{_SCRATCH_PY.name} is not executable"


# --- the copy itself ---------------------------------------------------------

def test_the_scratch_copy_is_wal_consistent_and_not_the_real_file():
    """`cp` of a WAL-mode main file is consistent only while the WAL is checkpointed —
    SQLite's schedule, not ours. backup() is consistent by construction.

    Reads CODE LINES ONLY, via tests/_prose.py. The first version of this grepped the whole
    file, and a mutation to `pass  # src.backup(dst)` left it GREEN — the docstring above
    and the commented-out call both contain the string it was looking for. That is the
    house failure mode this repo has already hit four times: a check that matches the text
    describing the thing it forbids.
    """
    code = "\n".join(code_lines(_SCRATCH_PY.read_text(encoding="utf-8"), jinja=False))
    assert ".backup(" in code, (
        "the scratch copy must use Connection.backup(), not a raw copy")
    assert "mode=ro" in code, "the real ck.db must be opened READ-ONLY to copy it"


def test_the_scratch_cache_key_sees_a_wal_write(tmp_path):
    """Same blind spot as tests/conftest.py had: a committed write can leave the main
    file's size AND mtime untouched, because it is sitting in ck.db-wal."""
    sys.path.insert(0, str(_ROOT / "tool"))
    try:
        import ckdb_scratch
    finally:
        sys.path.pop(0)

    db = tmp_path / "ck.db"
    db.write_bytes(b"x" * 64)
    before = ckdb_scratch.db_revision(db)
    (tmp_path / "ck.db-wal").write_bytes(b"y" * 32)
    assert ckdb_scratch.db_revision(db) != before, (
        "an appearing WAL did not change the cache key, so a stale scratch copy would be "
        "reused and tests would run against superseded data")


@pytest.mark.skipif(not _REAL_DB.exists(), reason="no real ck.db in this checkout")
def test_the_scratch_path_is_outside_the_repo_and_is_not_the_real_db():
    """Inside the tree it would show up in `git status` — the thing being prevented."""
    out = subprocess.run([sys.executable, str(_SCRATCH_PY)],
                         capture_output=True, text=True, cwd=str(_ROOT))
    assert out.returncode == 0, out.stderr
    path = pathlib.Path(out.stdout.strip()).resolve()
    assert path.exists() and path != _REAL_DB.resolve()
    assert _ROOT not in path.parents, f"{path} is inside the repo"


# --- being able to TELL which database a server is on ------------------------

def test_health_reports_which_database_it_is_serving(client):
    """Before this, the only way to know whether a running server was on the permanent
    ck.db or a scratch copy was to read its process environment."""
    body = client.get("/health").json()["db"]
    assert "db_path" in body and body["db_path"], "/health does not say which db it uses"
    assert "is_permanent_db" in body
    # The suite itself runs isolated, so this must report False — if it reports True the
    # conftest isolation is broken and every other guard is load-bearing.
    assert body["is_permanent_db"] is False, (
        f"the test app is serving the PERMANENT database ({body['db_path']}) — "
        f"conftest's CK_DB_PATH isolation is not in effect")

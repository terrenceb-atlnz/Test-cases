"""The test suite must never write to ask-ck/var/ck.db, the permanent source of truth.

ck.db is built ONCE and committed via git-LFS. Six suites legitimately exercise session
persistence, and before conftest's isolation those writes landed in the real file. They
cleaned up after themselves — measured: no throwaway key survived, no row carried the
run's date — so nothing was lost. The damage was subtler:

  * every gate run left ck.db byte-dirty, so a 440 MB LFS blob sat in `git status`
    inviting itself into an unrelated commit (this repo has more than one active stream);
  * a test that crashed between write and cleanup would strand a throwaway session in the
    permanent DB;
  * "is this diff mine or real?" had to be re-litigated by hand. It cost a full
    LFS-smudge + row-hash comparison to establish that two changed rows were another
    stream's genuine work and not test residue.

These tests pin the isolation itself, not the cleanup discipline that used to stand in
for it. The load-bearing one is test_writes_do_not_reach_the_real_db: it performs a real
persist and then proves the row is absent from ask-ck/var/ck.db.
"""
import os
import pathlib
import sqlite3

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_REAL_DB = _REPO_ROOT / "ask-ck" / "var" / "ck.db"

pytestmark = pytest.mark.skipif(
    os.environ.get("CK_TEST_USE_REAL_DB") == "1",
    reason="CK_TEST_USE_REAL_DB=1 deliberately opts out of isolation",
)


def _real_db_ids() -> set:
    """Session ids in the REAL ck.db, read strictly read-only.

    mode=ro so this assertion can never itself be the thing that dirties the file.
    """
    if not _REAL_DB.exists():
        pytest.skip("ask-ck/var/ck.db not present in this checkout")
    con = sqlite3.connect(f"file:{_REAL_DB.resolve()}?mode=ro", uri=True)
    try:
        return {r[0] for r in con.execute("SELECT id FROM sessions")}
    finally:
        con.close()


def test_ck_db_path_is_set_and_is_not_the_real_db():
    resolved = os.environ.get("CK_DB_PATH")
    assert resolved, "conftest did not set CK_DB_PATH — the suite is on the real ck.db"
    assert pathlib.Path(resolved).resolve() != _REAL_DB.resolve()


def test_the_db_layer_agrees_about_which_file_it_opened():
    """Belt and braces: the env var is only useful if db.py actually honours it, and it
    resolves the path lazily inside get_connection()."""
    import db

    assert pathlib.Path(db._resolve_db_path()).resolve() != _REAL_DB.resolve()


def test_the_isolated_copy_lives_outside_the_repo():
    """Inside the tree it would show up in `git status` — the problem we are fixing."""
    resolved = pathlib.Path(os.environ["CK_DB_PATH"]).resolve()
    assert _REPO_ROOT not in resolved.parents, f"{resolved} is inside the repo"


def test_the_copy_carries_the_real_corpus():
    """Isolation must not become "tests run against an empty DB" — these are in-process
    integration tests over the real corpus. A silently empty copy would turn most of the
    suite green-but-meaningless.
    """
    import db

    con = db.get_connection()
    for table, minimum in (("zephyr_cases", 40000), ("testlink_cases", 20000),
                           ("atp_tests", 10000)):
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert n >= minimum, f"{table} has {n} rows in the isolated copy (expected >={minimum})"


def test_the_copy_reflects_the_current_real_db():
    """Guards CACHE STALENESS, which is the realistic failure mode here.

    The pristine snapshot is cached under a key built from the real file's (size,
    mtime_ns). Get that key wrong — drop mtime, say — and a snapshot of a superseded
    ck.db gets reused forever, so tests quietly run against old data. Comparing a content
    signature catches that; a row COUNT alone would not, since a stale copy usually has
    the same number of sessions.

    Deliberately NOT advertised as a WAL-consistency check. A plain `cp ck.db` currently
    produces an identical signature on this seat because the WAL happens to be fully
    checkpointed, so no assertion here can discriminate cp from backup() today. The
    mechanism is pinned separately, by source, below.
    """
    import db

    if not _REAL_DB.exists():
        pytest.skip("no real ck.db to compare against")
    con = sqlite3.connect(f"file:{_REAL_DB.resolve()}?mode=ro", uri=True)
    try:
        expected = con.execute(
            "SELECT COUNT(*), MAX(updated_at) FROM sessions").fetchone()
    finally:
        con.close()
    got = db.get_connection().execute(
        "SELECT COUNT(*), MAX(updated_at) FROM sessions").fetchone()
    assert tuple(got) == tuple(expected), (
        f"isolated copy reports {tuple(got)}, real ck.db reports {tuple(expected)} — the "
        f"cached snapshot is stale (check the (size, mtime_ns) cache key)")


def test_the_snapshot_uses_the_wal_consistent_backup_api():
    """Pin the MECHANISM, since no data assertion can currently distinguish it.

    ck.db is WAL-mode. `cp` of the main file alone is consistent only while the WAL is
    checkpointed, which is SQLite's schedule to decide, not ours. Connection.backup() is
    consistent by construction. This is a source guard precisely because the behavioural
    difference is invisible whenever the WAL happens to be clean — i.e. exactly when a
    regression would slip through unnoticed.
    """
    src = (pathlib.Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    assert ".backup(" in src, (
        "the pristine ck.db snapshot no longer uses Connection.backup(). A plain copy of "
        "a WAL-mode database is only consistent when the WAL is checkpointed.")


def test_the_snapshot_cache_key_includes_the_source_mtime():
    """Source guard, because the data assertion above cannot catch this on a cold cache.

    Mutating the key from (size, mtime_ns) to (size,) leaves every test green on a fresh
    run — the wrong key still produces a fresh snapshot when no file sits under it. The
    bug only bites later, when a stale snapshot IS present under the reused key and tests
    silently run against a superseded ck.db. Verified: that mutation did not turn this
    file red, which is why the key is pinned by source instead.
    """
    src = (pathlib.Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    assert "st_mtime_ns" in src, (
        "the pristine snapshot cache key no longer includes the source mtime, so a "
        "snapshot of a superseded ck.db can be reused indefinitely")


def test_writes_do_not_reach_the_real_db():
    """The one that matters. Persist a session for real, then prove it is not in ck.db."""
    from models import WizardSession
    import routers.wizard as wizard

    key = "AWPTCM-T99990"          # throwaway; never a real case
    before = _real_db_ids()
    assert key not in before, "stale residue from an earlier run is already in the real DB"

    wizard._persist_session(WizardSession(key=key))
    try:
        # It must be in the isolated copy...
        import db
        got = {r[0] for r in db.get_connection().execute("SELECT id FROM sessions")}
        assert key in got, "the write did not land anywhere — the test proves nothing"
        # ...and absent from the real one.
        assert key not in _real_db_ids(), (
            f"{key} reached ask-ck/var/ck.db — the permanent source of truth was written")
    finally:
        wizard._clear_persisted(key)
        wizard.sessions.pop(key, None)

    assert _real_db_ids() == before, "the real DB's session set changed"


def test_deleting_a_session_also_stays_isolated():
    """A DELETE reaching the real DB is worse than an INSERT, so the delete path needs
    its own cover.

    NEVER name a real session id here. The first version of this test picked
    `sorted(real_ids)[0]` and called `_clear_persisted` on it, reasoning that isolation
    made it safe. Isolation was then deliberately mutated off to check this file could go
    red — and the test deleted AWPTCM-T30649 out of the permanent ck.db for real. It was
    recovered from a snapshot, but a test whose failure mode is destroying the source of
    truth is not an acceptable design at any level of confidence in the thing it tests.

    The property is provable without ever aiming at real data: write a throwaway key into
    the isolated copy, delete it there, and assert the real DB's id set is untouched
    throughout.
    """
    from models import WizardSession
    import routers.wizard as wizard
    import db

    key = "AWPTCM-T99989"          # throwaway; never a real case
    before = _real_db_ids()
    assert key not in before

    wizard._persist_session(WizardSession(key=key))
    ids = {r[0] for r in db.get_connection().execute("SELECT id FROM sessions")}
    assert key in ids, "setup failed — nothing to delete"

    wizard._clear_persisted(key)
    wizard.sessions.pop(key, None)

    ids = {r[0] for r in db.get_connection().execute("SELECT id FROM sessions")}
    assert key not in ids, "the delete did not take effect in the isolated copy"
    assert _real_db_ids() == before, (
        "the real ck.db's session set changed across an insert+delete cycle")

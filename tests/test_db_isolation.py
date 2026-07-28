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


def test_the_snapshot_cache_key_sees_a_wal_write(tmp_path):
    """The mtime of ck.db ALONE cannot detect a committed write. This is not theory.

    Measured 2026-07-28: after three live case loads the session count went 39 -> 40 while
    ck.db's size and mtime were unchanged, because every one of those commits sat in
    ck.db-wal. The cache key matched, the stale snapshot was served, and
    test_the_copy_reflects_the_current_real_db went red — the only reason it was noticed.
    Same blind spot that let `md5sum ck.db` report "byte-identical" while a real session
    row had been deleted.

    Behavioural, not a source grep: touch only the -wal and require a different key.
    """
    import conftest

    db = tmp_path / "ck.db"
    db.write_bytes(b"x" * 64)
    wal = tmp_path / "ck.db-wal"

    no_wal = conftest._db_revision(db)
    wal.write_bytes(b"y" * 32)
    with_wal = conftest._db_revision(db)
    assert with_wal != no_wal, (
        "appearing WAL did not change the cache key — a committed write would be invisible")

    wal.write_bytes(b"y" * 4096)          # a later commit appends to the WAL
    assert conftest._db_revision(db) != with_wal, "a growing WAL did not change the key"

    assert conftest._db_revision(db) == conftest._db_revision(db), "key must be stable"


def test_writes_do_not_reach_the_real_db():
    """The one that matters. Persist a session for real, then prove it is not in ck.db."""
    from models import WizardSession
    import session_store as store

    key = "AWPTCM-T99990"          # throwaway; never a real case
    before = _real_db_ids()
    assert key not in before, "stale residue from an earlier run is already in the real DB"

    store.persist_session(WizardSession(key=key))
    try:
        # It must be in the isolated copy...
        import db
        got = {r[0] for r in db.get_connection().execute("SELECT id FROM sessions")}
        assert key in got, "the write did not land anywhere — the test proves nothing"
        # ...and absent from the real one.
        assert key not in _real_db_ids(), (
            f"{key} reached ask-ck/var/ck.db — the permanent source of truth was written")
    finally:
        store.clear_persisted(key)
        store.sessions.pop(key, None)

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
    import session_store as store
    import db

    key = "AWPTCM-T99989"          # throwaway; never a real case
    before = _real_db_ids()
    assert key not in before

    store.persist_session(WizardSession(key=key))
    ids = {r[0] for r in db.get_connection().execute("SELECT id FROM sessions")}
    assert key in ids, "setup failed — nothing to delete"

    store.clear_persisted(key)
    store.sessions.pop(key, None)

    ids = {r[0] for r in db.get_connection().execute("SELECT id FROM sessions")}
    assert key not in ids, "the delete did not take effect in the isolated copy"
    assert _real_db_ids() == before, (
        "the real ck.db's session set changed across an insert+delete cycle")


# --- LAYER 1: fail-closed connect guard --------------------------------------
#
# Isolation alone was one layer, and it was removed on purpose during mutation testing.
# These pin the second layer, which holds even when the first is broken.

def test_a_writable_connect_to_the_real_db_is_refused():
    """The mechanism that would have prevented the AWPTCM-T30649 deletion."""
    with pytest.raises(RuntimeError, match="REFUSED"):
        sqlite3.connect(str(_REAL_DB))


def test_a_writable_connect_is_refused_however_the_path_is_spelled():
    """Path spelling must not be a way around it — the guard resolves before comparing."""
    weird = _REAL_DB.parent / ".." / "var" / _REAL_DB.name       # same file, silly route
    with pytest.raises(RuntimeError, match="REFUSED"):
        sqlite3.connect(str(weird))
    with pytest.raises(RuntimeError, match="REFUSED"):
        sqlite3.connect(_REAL_DB)                                # a Path, not a str


@pytest.mark.parametrize("uri", [
    "file:{p}",                    # no mode= at all defaults to read-write-create
    "file:{p}?mode=rw",
    "file:{p}?mode=rwc",
])
def test_writable_uri_forms_are_refused(uri):
    with pytest.raises(RuntimeError, match="REFUSED"):
        sqlite3.connect(uri.format(p=_REAL_DB.resolve()), uri=True)


def test_read_only_access_to_the_real_db_still_works():
    """The guard must not block legitimate inspection — tool/ckdb_signature.py and the
    _real_db_ids() helper in this file both depend on read-only access."""
    con = sqlite3.connect(f"file:{_REAL_DB.resolve()}?mode=ro", uri=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] >= 0
    finally:
        con.close()


def test_the_guard_does_not_interfere_with_other_databases(tmp_path):
    """Only the real ck.db is special; everything else opens normally."""
    other = tmp_path / "scratch.db"
    con = sqlite3.connect(str(other))
    try:
        con.execute("CREATE TABLE t (x)")
        con.commit()
    finally:
        con.close()
    assert other.exists()
    sqlite3.connect(":memory:").close()


def test_broken_isolation_now_fails_loudly_instead_of_writing():
    """The incident path, end to end, with no write performed.

    Simulate the isolation being absent by pointing CK_DB_PATH at the real file and
    forcing db.py to open a fresh connection. Before Layer 1 this handed back a writable
    handle to the permanent DB. Now it raises.
    """
    import db

    saved_env = os.environ.get("CK_DB_PATH")
    saved_conn = getattr(db._local, "conn", None)
    try:
        db._local.conn = None                      # force get_connection() to reopen
        os.environ["CK_DB_PATH"] = str(_REAL_DB)
        with pytest.raises(RuntimeError, match="REFUSED"):
            db.get_connection()
    finally:
        if saved_env is None:
            os.environ.pop("CK_DB_PATH", None)
        else:
            os.environ["CK_DB_PATH"] = saved_env
        db._local.conn = saved_conn


# --- LAYER 3: destructive writes may only name throwaway keys ----------------

def test_persisting_a_real_shaped_key_is_refused():
    """`victim = sorted(real_ids)[0]` was the incident. Refuse it at the db choke point,
    where every caller funnels through, rather than trusting each test."""
    import db

    for real_key in ("AWPTCM-T30649", "AWPTCM-T33233", "AWPTCM-T1"):
        with pytest.raises(AssertionError, match="REAL case key"):
            db.save_session("wizard", real_key, {"key": real_key})
        with pytest.raises(AssertionError, match="REAL case key"):
            db.delete_session("wizard", real_key)


def test_the_pt_prefixed_form_is_also_refused():
    import db

    with pytest.raises(AssertionError, match="REAL case key"):
        db.delete_session("pt", "pt-AWPTCM-T33235")


@pytest.mark.parametrize("key", [
    "AWPTCM-T99990",      # reserved numeric block
    "AWPTCM-T99999",      # top of the block
    "AWPTCM-TSTALE1",     # non-numeric suffix: a real key is AWPTCM-T + digits only
    "AWPTCM-TTZ1",
])
def test_throwaway_keys_are_allowed(key):
    """The guard must not obstruct the suites that legitimately test persistence."""
    from models import WizardSession
    import db
    import session_store as store

    db.save_session("wizard", key, WizardSession(key=key).model_dump())
    try:
        ids = {r[0] for r in db.get_connection().execute("SELECT id FROM sessions")}
        assert key in ids
    finally:
        db.delete_session("wizard", key)
        store.sessions.pop(key, None)


def test_the_reserved_block_boundaries_are_exact():
    """Off-by-one here would either block a real case or wave through a neighbour of one."""
    from conftest import _is_throwaway_key

    assert not _is_throwaway_key("AWPTCM-T99979")   # just below the block
    assert _is_throwaway_key("AWPTCM-T99980")       # first reserved
    assert _is_throwaway_key("AWPTCM-T99999")       # last reserved
    assert not _is_throwaway_key("AWPTCM-T100000")  # just above
    assert _is_throwaway_key("_workspace_llm")      # not a case row
    assert not _is_throwaway_key(None)              # not a str -> refuse, do not crash


def test_the_guard_covers_the_sqlite_module_db_actually_uses():
    """The bug the first version of Layer 1 had, pinned so it cannot return.

    db.py binds `sqlite3` as pysqlite3 when installed (db.py:34-38 — pysqlite3 bundles a
    modern SQLite with enable_load_extension, which sqlite-vec needs), so
    `db.sqlite3 is not sqlite3` on this seat. A guard patched onto the stdlib module alone
    never sees db.get_connection()'s call, which is precisely the path that deleted a real
    session row. Assert the guard is installed on EVERY reachable module, not just stdlib.
    """
    import db

    for mod in {sqlite3, db.sqlite3}:
        assert getattr(mod.connect, "_ck_guarded", False), (
            f"{mod.__name__}.connect is unguarded — a writable open of the real ck.db "
            f"through this module would not be refused")


def test_pysqlite3_is_the_module_in_use_here():
    """Documents WHY the multi-module patch is needed, and fails loudly if the situation
    changes (e.g. pysqlite3 uninstalled), so the comment above cannot silently rot."""
    import db

    if db.sqlite3 is sqlite3:
        pytest.skip("pysqlite3 not installed; db.py fell back to the stdlib sqlite3")
    assert db.sqlite3.__name__ == "pysqlite3"

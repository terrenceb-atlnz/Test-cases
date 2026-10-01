"""ask-ck/tools/ckdb_scratch.py — the throwaway ck.db copy the scratch server runs on.

2026-10-01: the copy was refreshed but a previous scratch server's `scratch.db-wal` / `-shm`
were left beside it, SQLite replayed that stale WAL onto the fresh copy, and the first write
failed with "database disk image is malformed". These tests pin that a copy never has a
leftover -wal / -shm beside it, on both paths (cached snapshot and --fresh rebuild).
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "ask-ck" / "tools" / "ckdb_scratch.py"
spec = importlib.util.spec_from_file_location("ckdb_scratch", TOOL)
cs = importlib.util.module_from_spec(spec)
sys.modules["ckdb_scratch"] = cs
spec.loader.exec_module(cs)  # type: ignore[union-attr]


@pytest.fixture
def world(tmp_path: Path, monkeypatch):
    real = tmp_path / "real" / "ck.db"
    real.parent.mkdir()
    con = sqlite3.connect(str(real))
    con.execute("create table t (x)")
    con.execute("insert into t values (1)")
    con.commit()
    con.close()
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr(cs, "REAL_DB", real)
    monkeypatch.setattr(cs.tempfile, "gettempdir", lambda: str(tmp))
    return tmp / "ck-scratch-db"


@pytest.mark.parametrize("fresh", [False, True])
def test_a_leftover_wal_and_shm_are_removed_before_the_copy(world, fresh):
    first = cs.scratch_db()
    for suffix in ("-wal", "-shm"):
        (world / ("scratch.db" + suffix)).write_bytes(b"stale from a previous scratch server")

    target = cs.scratch_db(fresh=fresh)

    assert target == first
    assert not (world / "scratch.db-wal").exists()
    assert not (world / "scratch.db-shm").exists()
    con = sqlite3.connect(str(target))
    try:
        assert con.execute("select x from t").fetchall() == [(1,)]
    finally:
        con.close()

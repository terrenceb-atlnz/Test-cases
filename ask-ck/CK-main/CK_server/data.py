"""
Data loading for server-backed drafting tool.

Migrates patterns from:
- tool/build_drafting_tool.py
- tool/build_review_html.py
- tool/common.py

Loads the three databases + indices on server startup.
"""

from typing import Dict, List, Any

import db


class _DbMap:
    """Lazy, read-only mapping backed by a db.get_* lookup (Commit B).

    Replaces a fully-materialized corpus dict so the ~44 MB of TestLink / ATP /
    script records stay in SQLite instead of RAM. Only `.get(id)` / `[id]` /
    `in` are used by callers — the single `.items()` iteration site lived inside
    a search function that now delegates to db directly.
    """
    def __init__(self, getter):
        self._get = getter

    def get(self, key, default=None):
        try:
            v = self._get(key)
        except Exception:
            v = None
        return v if v is not None else default

    def __getitem__(self, key):
        v = self._get(key)
        if v is None:
            raise KeyError(key)
        return v

    def __contains__(self, key):
        try:
            return self._get(key) is not None
        except Exception:
            return False

def load_all_data() -> Dict[str, Any]:
    """Load the SMALL, frequently-joined references into RAM; back the large
    corpora (TestLink, ATP, scripts) with lazy db-backed maps (Commit B).

    The big keyword corpora — full Zephyr text, TestLink, ATP descriptions, the
    script index — now live in ask-ck/var/ck.db and are read on demand via db.*
    (searches) or the _DbMap lazy lookups below (per-id enrichment). This removes
    ~50 MB of boot-time RAM and the per-request zephyr_cases.jsonl scan. Run
    `python3 tool/build_db.py --fresh` to (re)build the DB from source JSON.
    """
    print("  Loading lightweight references (corpora served from ck.db)...")
    data = {}

    # Small references kept in RAM (heavily joined; ~3 MB total). Strict DB-only:
    # these come from ck.db, NOT from the source JSON — the DB is the single
    # runtime source of truth (PLAN-db-only-search Phase 1). Rebuild via
    # `python3 tool/build_db.py --fresh`.
    data["zephyr_master"] = {c["key"]: c for c in db.get_target_cases()}
    raw_cands = db.all_candidates()
    data["candidates"] = raw_cands
    data["candidates_dict"] = {c["key"]: c for c in raw_cands if c.get("key")}

    # Decisions (primary matches) — from ck.db
    data["decisions"] = db.get_decisions()

    # Large corpora — lazy db-backed lookups (never fully materialized).
    #   testlink       : {id -> case}      -> db.get_testlink_case
    #   test_id_desc   : {tid -> info}     -> db.get_atp_test
    #   scripts_index_by_id: {id -> record} -> db.get_script
    # Search over these goes through db.search_* (see routers); slim_index and
    # scripts_slim are gone (iterated via db.iter_zephyr_slim / db.search_scripts).
    data["testlink"] = _DbMap(db.get_testlink_case)
    data["test_id_desc"] = _DbMap(db.get_atp_test)
    data["scripts_index_by_id"] = _DbMap(db.get_script)

    # PyTest Creator: framework surface + index meta — from ck.db json_docs.
    data["framework_surface"] = db.get_json_doc("framework_surface") or {}
    data["scripts_index_meta"] = db.get_json_doc("scripts_index_meta") or {}

    chk = db.startup_check()
    counts = chk.get("counts", {}) if chk.get("ok") else {}
    print(f"  zephyr_master: {len(data['zephyr_master'])}  candidates: {len(data['candidates'])}  "
          f"decisions: {len(data['decisions'])} entries")
    if chk.get("ok"):
        print(f"  ck.db: zephyr {counts.get('zephyr_cases')} / testlink {counts.get('testlink_cases')} / "
              f"atp {counts.get('atp_tests')} / scripts {counts.get('scripts')}  "
              f"(vector_search={chk.get('has_vec')})")
    else:
        print(f"  ck.db: NOT READY ({chk.get('error', 'empty')}) — run tool/build_db.py --fresh")

    return data

# In real impl: add functions for get_full_zephyr_case(key), search_test_id(q), etc.
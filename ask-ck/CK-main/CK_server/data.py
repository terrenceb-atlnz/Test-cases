"""
Data loading for server-backed drafting tool.

Migrates patterns from:
- tool/build_drafting_tool.py
- tool/build_review_html.py
- tool/common.py

Loads the three databases + indices on server startup.
"""

import json
import os
from typing import Dict, List, Any

import db
from paths import OBJECTIVE_DRAFTING_ROOT, PT_DATA_DIR

# All "data/..." paths below resolve inside ask-ck/objective-drafting/
BASE = str(OBJECTIVE_DRAFTING_ROOT)


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

def load_json_safe(path: str) -> Any:
    full = os.path.join(BASE, path)
    if os.path.exists(full):
        try:
            return json.load(open(full, encoding="utf-8"))
        except Exception as e:
            print(f"Warning loading {path}: {e}")
    return None

def load_json_abs(full: str) -> Any:
    """Like load_json_safe but takes an absolute path (for non-drafting silos)."""
    if os.path.exists(full):
        try:
            return json.load(open(full, encoding="utf-8"))
        except Exception as e:
            print(f"Warning loading {full}: {e}")
    return None

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

    # Small references kept in RAM (heavily joined; ~3 MB total)
    data["zephyr_master"] = {c["key"]: c for c in (load_json_safe("data/zephyr_master.json") or [])}
    raw_cands = load_json_safe("data/candidates.json") or []
    data["candidates"] = raw_cands
    data["candidates_dict"] = {c["key"]: c for c in raw_cands}

    # Decisions (primary matches)
    dec = {}
    dec_dir = os.path.join(BASE, "data/decisions")
    for f in sorted([f for f in os.listdir(dec_dir) if f.endswith(".json")]):
        dec.update(json.load(open(os.path.join(dec_dir, f), encoding="utf-8")))
    data["decisions"] = dec

    # Large corpora — lazy db-backed lookups (never fully materialized).
    #   testlink       : {id -> case}      -> db.get_testlink_case
    #   test_id_desc   : {tid -> info}     -> db.get_atp_test
    #   scripts_index_by_id: {id -> record} -> db.get_script
    # Search over these goes through db.search_* (see routers); slim_index and
    # scripts_slim are gone (iterated via db.iter_zephyr_slim / db.search_scripts).
    data["testlink"] = _DbMap(db.get_testlink_case)
    data["test_id_desc"] = _DbMap(db.get_atp_test)
    data["scripts_index_by_id"] = _DbMap(db.get_script)

    # PyTest Creator: framework surface + index meta stay small file-backed refs.
    data["framework_surface"] = load_json_abs(str(PT_DATA_DIR / "framework_surface.json")) or {}
    data["scripts_index_meta"] = load_json_abs(str(PT_DATA_DIR / "scripts_index.meta.json")) or {}

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
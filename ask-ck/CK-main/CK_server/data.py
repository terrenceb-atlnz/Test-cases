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

from paths import OBJECTIVE_DRAFTING_ROOT, PT_DATA_DIR

# All "data/..." paths below resolve inside ask-ck/objective-drafting/
BASE = str(OBJECTIVE_DRAFTING_ROOT)

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
    print("  Loading lightweight indices + references...")
    data = {}

    # Core indices
    data["zephyr_master"] = {c["key"]: c for c in (load_json_safe("data/zephyr_master.json") or [])}
    raw_cands = load_json_safe("data/candidates.json") or []
    data["candidates"] = raw_cands
    data["candidates_dict"] = {c["key"]: c for c in raw_cands}
    data["slim_index"] = load_json_safe("data/zephyr_full/slim_index.json") or []

    # Decisions (primary matches)
    dec = {}
    dec_dir = os.path.join(BASE, "data/decisions")
    for f in sorted([f for f in os.listdir(dec_dir) if f.endswith(".json")]):
        dec.update(json.load(open(os.path.join(dec_dir, f), encoding="utf-8")))
    data["decisions"] = dec

    # ATPyLib data for search
    data["test_id_desc"] = load_json_safe("data/suites/test_id_description.json") or {}

    # Full TestLink data for rich descriptions in Step 1
    tl_raw = load_json_safe("data/suites/testlink_awp.json") or []
    data["testlink"] = {item.get("id"): item for item in tl_raw if item.get("id")}

    # PyTest Creator: script-database index (built out-of-band by
    # tool/build_script_index.py — degrade gracefully when absent)
    data["scripts_index"] = load_json_abs(str(PT_DATA_DIR / "scripts_index.json")) or []
    data["scripts_slim"] = load_json_abs(str(PT_DATA_DIR / "scripts_slim_index.json")) or []
    data["scripts_index_by_id"] = {r["id"]: r for r in data["scripts_index"]}
    data["framework_surface"] = load_json_abs(str(PT_DATA_DIR / "framework_surface.json")) or {}
    data["scripts_index_meta"] = load_json_abs(str(PT_DATA_DIR / "scripts_index.meta.json")) or {}

    print(f"  zephyr_master: {len(data['zephyr_master'])}")
    print(f"  candidates: {len(data['candidates'])}")
    print(f"  decisions: {len(data['decisions'])} entries")
    print(f"  slim_index: {len(data['slim_index'])}")
    print(f"  test_id_desc: {len(data['test_id_desc'])}")
    print(f"  testlink: {len(data['testlink'])}")
    print(f"  scripts_index: {len(data['scripts_index'])} files "
          f"(enriched {data['scripts_index_meta'].get('enrichment_pct', 0)}%), "
          f"framework_surface: {len(data['framework_surface'])} modules")

    return data

# In real impl: add functions for get_full_zephyr_case(key), search_test_id(q), etc.
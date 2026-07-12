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

BASE = "."

def load_json_safe(path: str) -> Any:
    full = os.path.join(BASE, path)
    if os.path.exists(full):
        try:
            return json.load(open(full, encoding="utf-8"))
        except Exception as e:
            print(f"Warning loading {path}: {e}")
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

    print(f"  zephyr_master: {len(data['zephyr_master'])}")
    print(f"  candidates: {len(data['candidates'])}")
    print(f"  decisions: {len(data['decisions'])} entries")
    print(f"  slim_index: {len(data['slim_index'])}")
    print(f"  test_id_desc: {len(data['test_id_desc'])}")
    print(f"  testlink: {len(data['testlink'])}")

    return data

# In real impl: add functions for get_full_zephyr_case(key), search_test_id(q), etc.
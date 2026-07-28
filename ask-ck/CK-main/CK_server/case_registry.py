"""Which AWPTCM cases exist, which are Complete, which are hidden, and how they group.

Both tools ask the same four questions of the case population, and both answered them
through `routers.wizard` until commit 8 (PLAN-backend-module-split.md):

  * is this key even a case key?              -> CASE_KEY_RE
  * should the lists offer it?                -> is_hidden_case
  * is it Complete?                           -> refined_complete_keys / refined_payload_path
  * how do the dropdowns group it?            -> build_case_groups / get_refined_group

"Complete" is defined by the filesystem, not the database: a case is Complete once
`refined-cases/<Group>/AWPTCM-Txxxx/zephyr_payload.json` exists. That artefact is the
drop-in bundle the Generator exports and `tool/upload_refined.py` pushes to Zephyr, and
`guard_db_only.py` explicitly allows reading it — it is the one on-disk runtime read the
DB-only invariant permits.

Hiding is DISPLAY ONLY. `ck.db` is the permanent source of truth and is never edited to
hide anything; the entries below simply stop a case being offered for review.

A leaf: imports `db` and `paths` only. It must never import `routers.*`.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import db
from paths import REFINED_DIR

log = logging.getLogger(__name__)

# Case keys are AWPTCM-Txxxx. Validate before interpolating a key into a filesystem path
# or a subprocess argument.
CASE_KEY_RE = re.compile(r"^AWPTCM-T\d+$")

# Cases hidden from the Generator (and PyTest Creator) case lists — out of scope for
# this tool. This is a DISPLAY filter only: the data stays untouched in ck.db (the
# permanent source of truth), it just isn't offered for review. Remove an entry here
# to surface a case/folder again.
#   T44453  — "ART Limits Test"  (New Platform Template/ART Limits Test)
#   T41263-6 — 1335_pbr / 1336_acl / 1344_qos / 5000_mdi_mdix (ART Testsuites folder)
HIDDEN_CASE_KEYS = frozenset({
    "AWPTCM-T44453",
    "AWPTCM-T41263", "AWPTCM-T41264", "AWPTCM-T41265", "AWPTCM-T41266",
})

# Whole categories (Zephyr folders) hidden from the case lists — out of scope. Matched
# by exact folder path, so every case in the folder is hidden regardless of its (non-
# contiguous) test-id, and any future case added to the folder is hidden too.
#   Bootloader (17) + GRUB Bootloader (8) = 25 cases
HIDDEN_CASE_FOLDERS = frozenset({
    "/New Platform Test (MASTER)/Bootloader",
    "/New Platform Test (MASTER)/GRUB Bootloader",
})


def is_hidden_case(key: str, folder: str = "") -> bool:
    """A case is hidden from the lists if its key is explicitly hidden OR it lives in a
    hidden folder. Display-only; ck.db is untouched."""
    if key in HIDDEN_CASE_KEYS:
        return True
    f = (folder or "").rstrip("/")
    return f in HIDDEN_CASE_FOLDERS


def refined_payload_path(key: str) -> Optional[Path]:
    """Path to the on-disk drop-in zephyr_payload.json for a case, if it exists."""
    if not key or not REFINED_DIR.exists():
        return None
    for p in REFINED_DIR.glob(f"*/{key}/zephyr_payload.json"):
        return p
    # Fallback for any deeper nesting of the group dir.
    for p in REFINED_DIR.rglob("zephyr_payload.json"):
        if p.parent.name == key:
            return p
    return None


def refined_complete_keys() -> set:
    """Cases with drop-in refined-cases/**/AWPTCM-Txxxx/zephyr_payload.json are 'complete'."""
    refined_root = REFINED_DIR
    done = set()
    if not refined_root.exists():
        return done
    try:
        for path in refined_root.rglob("zephyr_payload.json"):
            parent = path.parent.name
            if parent.startswith("AWPTCM-"):
                done.add(parent)
    except Exception as e:
        log.warning("scanning refined-cases failed: %s", e)
    return done


def session_progress_map() -> Dict[str, dict]:
    """Per-case wizard progress (confirms + step4/5). Commit C: sourced from the
    sessions table via db.list_session_progress() (identical derivation)."""
    try:
        return db.list_session_progress()
    except Exception as e:
        log.warning("reading session progress failed: %s", e)
        return {}


def build_case_groups(keys, zephyr: dict) -> List[dict]:
    """Group case keys by Zephyr folder leaf for optgroups."""
    groups: Dict[str, List[str]] = {}
    for key in keys:
        folder = zephyr.get(key, {}).get("folder", "") or ""
        group = folder.rstrip("/").split("/")[-1] if folder else "Other"
        groups.setdefault(group, []).append(key)
    for g in groups:
        groups[g].sort(key=lambda k: (k.split("-T")[-1] if "-T" in k else k))
    grouped = []
    for g in sorted(groups.keys()):
        case_list = groups[g]
        enriched = []
        for k in case_list:
            title = zephyr.get(k, {}).get("title", k)
            enriched.append({"key": k, "title": title})
        grouped.append({"label": f"{g} ({len(case_list)})", "cases": enriched})
    return grouped


def get_refined_group(case_key: str, data: dict) -> str:
    """Determine the appropriate refined-cases group folder for a case.
    Uses the last segment of the zephyr folder (e.g. 'Port', 'IPv4').
    Tries to match an existing refined-cases directory for consistency
    (e.g. 'Port (7)', 'IPv4 (44)'), otherwise uses the base name and creates if needed.
    Cross-references PROGRESS.md (output generation to produce drop-in refined-cases artifacts)
    and SERVER-README.md (drop files into refined-cases/<Group>/...).
    """
    zephyr = data.get("zephyr_master", {})
    folder = zephyr.get(case_key, {}).get("folder", "") or ""
    base = folder.rstrip("/").split("/")[-1] if folder else "Other"

    refined_root = REFINED_DIR
    if refined_root.exists():
        for d in sorted(refined_root.iterdir()):
            if d.is_dir():
                name = d.name
                # Match if base appears in existing group name (case insensitive)
                if base.lower() in name.lower() or name.lower().startswith(base.lower()):
                    return name
    return base

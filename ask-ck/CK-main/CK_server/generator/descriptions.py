"""Text shaping for the Generator's three review steps, plus the ATP retrieval wrapper.

Everything here answers one question: *given rows out of `db`, what text does the review
UI show?* The three review tables (TestLink / Zephyr / ATPyLib) each get a full,
untruncated body built from a different source shape, and Step 2's rows additionally need
enriching with the full Zephyr case before they can be described at all.

Extracted verbatim from `routers/wizard.py` (PLAN-backend-module-split.md commit 7). The
functions are pure — the only dependency is `db` — so they are unit-testable without a
TestClient, which they were not while they sat inside a router module.

Two duplicates were retired into `db` rather than carried in here, because `db` is the
leaf and the dependency has to point that way:

  * `_ZREF_GENERIC_TOKENS` was a byte-identical copy of the set `db.search_*` actually
    scores with. `db.GENERIC_TOKENS` is now the single definition.
  * `_split_atp_title_description` existed in both files; `db.py`'s copy was labelled
    "Verbatim from wizard.py" and was proven structurally identical (same signature, same
    AST once docstrings are stripped). `db.split_atp_title_description` is now the single
    definition, and it is used by `db.search_atp` itself.

Naming: this module exports PUBLIC names. Cross-module imports of underscore-private
helpers are the structural defect Part B exists to remove, so a name that another module
imports does not get an underscore.
"""

import re
from typing import Any, Dict, List, Optional

import db


def normalize_zephyr_text(s: str) -> str:
    s = s or ""
    s = re.sub(r"^\(\d+\)\s*", "", s)
    s = s.replace("_", " ").replace("/", " ").replace("-", " ")
    return s.lower()


def zephyr_tokens(s: str) -> List[str]:
    s = normalize_zephyr_text(s)
    words = re.findall(r"[a-z0-9][a-z0-9+]{1,}", s)
    out: List[str] = []
    for w in words:
        if len(w) < 3:
            continue
        out.append(w)
        # Normalize MDI variants so MDI / MDIX / MDI-MDIX cluster together
        if w in ("mdi", "mdix"):
            out.extend(["mdi", "mdix"])
    return out


def build_testlink_description(item: dict, title: str = "") -> str:
    """Full TestLink step body for Step 1 UI — no mid-sentence character truncation.

    Includes all steps with complete action/expected text. Soft-caps only on
    pathological step counts (first 30) so payloads stay reasonable.
    """
    steps = (item or {}).get("steps") or []
    desc_parts: List[str] = []
    for s in steps[:30]:
        action = (s.get("action") or "").strip()
        expected = (s.get("expected") or "").strip()
        if action or expected:
            if action and expected:
                desc_parts.append(f"Step: {action}\nExpected: {expected}")
            elif action:
                desc_parts.append(f"Step: {action}")
            else:
                desc_parts.append(f"Expected: {expected}")
    if desc_parts:
        return "\n\n".join(desc_parts)
    # Fallbacks only when no structured steps exist
    snip = ((item or {}).get("snippet") or "").strip()
    if snip:
        return snip
    return (title or (item or {}).get("title") or "").strip()


def build_zephyr_case_description(
    slim_meta: dict,
    full: dict,
    title_fallback: str = "",
) -> str:
    """Full Zephyr case body for Step 2 UI — no mid-field character truncation.

    Soft-caps step count only (first 20) for pathological cases; each field is complete.
    """
    desc_parts: List[str] = []
    t = (
        (slim_meta or {}).get("title")
        or (full or {}).get("title")
        or title_fallback
        or ""
    ).strip()
    full = full or {}
    slim_meta = slim_meta or {}

    obj = str(full.get("objective") or "").strip()
    if obj:
        desc_parts.append("Objective: " + obj)
    pre = str(full.get("precondition") or "").strip()
    if pre:
        desc_parts.append("Precondition: " + pre)

    meta = []
    if slim_meta.get("status"):
        meta.append(f"Status: {slim_meta['status']}")
    if "has_objective" in slim_meta:
        meta.append(f"Has objective: {slim_meta['has_objective']}")
    if "num_steps" in slim_meta:
        meta.append(f"Num steps: {slim_meta['num_steps']}")
    if slim_meta.get("labels"):
        meta.append(f"Labels: {', '.join(slim_meta['labels'])}")
    if meta:
        desc_parts.append(" | ".join(meta))

    steps_source = full.get("steps", []) or []
    if steps_source:
        steps_list = []
        for i, s in enumerate(steps_source[:20], 1):
            d = (s.get("description") or "").strip()
            if d:
                steps_list.append(f"{i}. {d}")
        if steps_list:
            desc_parts.append("Steps:\n" + "\n".join(steps_list))

    if not desc_parts:
        desc_parts.append(t or "Related Zephyr case")
    return "\n\n".join(desc_parts)


def enrich_zephyr_rows(
    rows: List[Dict[str, Any]],
    data: dict,
) -> List[Dict[str, Any]]:
    """Fill description from zephyr_master / batch jsonl for UI rows that only have title."""
    zm = data.get("zephyr_master", {}) or {}
    # Commit B: slim fields (title/folder/status/labels/…) already ride on each
    # row from db.search_zephyr, so no slim_index dict is needed.
    slim_by_key = {}
    need = []
    for r in rows:
        k = r.get("key") or r.get("id")
        if not k:
            continue
        # Re-enrich when description is missing or is just the title
        desc = (r.get("description") or "").strip()
        title = (r.get("title") or "").strip()
        if not desc or desc == title:
            if k not in zm:
                need.append(k)
    # Was wizard._get_full_zephyr_cases_batch, a one-line wrapper whose only job was to
    # drop falsy keys — which db.get_zephyr_cases_batch already does itself (db.py:336).
    full_map = db.get_zephyr_cases_batch(need) if need else {}
    out = []
    for r in rows:
        k = r.get("key") or r.get("id")
        if not k:
            out.append(r)
            continue
        slim = slim_by_key.get(k) or {
            "key": k,
            "title": r.get("title"),
            "folder": r.get("folder"),
            "status": r.get("status"),
            "labels": r.get("labels"),
            "has_objective": r.get("has_objective"),
            "num_steps": r.get("num_steps"),
        }
        full = zm.get(k) or full_map.get(k) or {}
        desc = build_zephyr_case_description(slim, full, title_fallback=r.get("title") or "")
        enriched = {**r, "key": k, "description": desc}
        if not enriched.get("title"):
            enriched["title"] = slim.get("title") or full.get("title") or k
        if not enriched.get("folder"):
            enriched["folder"] = slim.get("folder") or full.get("folder") or ""
        out.append(enriched)
    return out


def build_atp_query(sess, case_title: str = "") -> str:
    """Build a keyword search query from case + previous selections for ATP retrieval."""
    parts = [sess.key or "", case_title or ""]
    if sess.primary:
        parts.append(str(sess.primary.get("w", "")))
        parts.append(str(sess.primary.get("m", "")))
    for sel in (sess.step1.selections or []):
        parts.append(sel.title or "")
        parts.append(sel.justification or "")
    for sel in (sess.step2.selections or []):
        parts.append(sel.title or "")
    # Prefer specific tokens for search quality
    raw = " ".join(parts)
    toks = [t for t in zephyr_tokens(raw) if t not in db.GENERIC_TOKENS]
    # Fall back to raw if everything was filtered
    return " ".join(toks[:24]) if toks else raw


def hybrid_on(mode: str) -> bool:
    """True → use semantic+keyword hybrid; False → keyword only. Default (mode
    empty/'hybrid'/'semantic') is hybrid when vectors are available, else keyword;
    'keyword' forces keyword. db.*_hybrid also degrades internally, so this is safe."""
    return (mode or "").lower() != "keyword" and db.HAS_VEC


def get_atp_candidates(q: str, data: dict, limit: int = 20,
                       keep_ids: Optional[set] = None, mode: str = "") -> List[Dict[str, Any]]:
    """Candidate ATP tests via keyword (or hybrid) search. Full descriptions,
    short title. keep_ids pool rows always returned, re-scored (Commit B/D)."""
    keep = keep_ids or set()
    if hybrid_on(mode):
        return db.search_atp_hybrid(q, keep_ids=keep, limit=limit)
    return db.search_atp(q, keep_ids=keep, limit=limit)

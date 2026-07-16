"""SQLite access layer for Ask-CK  (see ask-ck/ck-facelift/PLAN-db-migration.md).

Commit A: reads + search (keyword/FTS5) + session CRUD. No vector search yet
(Stage D adds sqlite-vec); the connection factory already best-effort-loads the
extension so Stage D is a drop-in.

Design notes:
- **Single connection factory.** `get_connection()` is the ONLY place
  `sqlite3.connect()` is called anywhere in the codebase — every router and every
  tool/ script goes through it, so PRAGMAs / WAL / extension-load are applied
  identically in one spot. SQLite is an embedded file, so we reuse one connection
  per thread via `threading.local()` (no per-call reopen).
- **Plain sync sqlite3** — queries are ms-scale; no async ceremony.
- **No FastAPI imports** — tool/ scripts (build_db.py) import this module directly.
- **Search parity:** the scoring helpers below are copied verbatim from the CURRENT
  wizard.py / pytest_create.py (`_relevance_score`, `_score_script_candidate`, the
  tokenizers and stopword sets). NOTE: the DB-migration plan's "Search parity"
  section cites older formulas (`0.4+0.1*hits` …) that were replaced by
  `_relevance_score` in the 2026-07-16 ES-split work — the live scorer is the
  parity target, not the plan's stale formulas. In Commit B the router wrappers
  delegate here and their private copies are removed, so the two cannot drift.
"""

import math
import os
import re
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from paths import DB_PATH

# ─────────────────────────────────────────────────────────────────────────────
# Connection factory
# ─────────────────────────────────────────────────────────────────────────────
_local = threading.local()
HAS_VEC = False   # set by get_connection(); drives keyword-only degrade in Stage D


def _resolve_db_path() -> str:
    """paths.py default, env-overridable — matches CK_EMBED_MODEL convention."""
    return os.getenv("CK_DB_PATH", str(DB_PATH))


def get_connection() -> sqlite3.Connection:
    """Return this thread's connection, creating + configuring it once."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn
    conn = sqlite3.connect(_resolve_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA mmap_size=268435456")   # 256 MB
    global HAS_VEC
    try:
        conn.enable_load_extension(True)
        import sqlite_vec               # Stage D dependency; absent in Commit A
        sqlite_vec.load(conn)
        HAS_VEC = True
    except Exception:
        HAS_VEC = False
    finally:
        try:
            conn.enable_load_extension(False)
        except Exception:
            pass
    _local.conn = conn
    return conn


def _rows(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    return get_connection().execute(sql, params).fetchall()


def _one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    return get_connection().execute(sql, params).fetchone()


def _json(s: Optional[str], default):
    if not s:
        return default
    try:
        import json
        return json.loads(s)
    except Exception:
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Scoring helpers — copied VERBATIM from the current wizard.py / pytest_create.py
# so DB-backed search reproduces live ordering & scores exactly.
# ─────────────────────────────────────────────────────────────────────────────
_ZREF_GENERIC_TOKENS = frozenset({
    "port", "ports", "ipv4", "ipv6", "ip", "switch", "switches", "interface",
    "interfaces", "test", "tests", "feature", "features", "basic", "function",
    "functionality", "command", "commands", "show", "config", "configuration",
    "platform", "new", "master", "template", "traffic", "link", "device",
    "devices", "support", "supported", "behaviour", "behavior", "check",
    "verify", "confirm", "using", "with", "from", "that", "this", "when",
    "case", "cases", "area", "manual", "auto", "server", "client", "mode",
    "type", "level", "status", "info", "data", "table", "entry", "entries",
    "packet", "packets", "network", "remote", "local", "enabled", "disabled",
    "enable", "disable", "set", "get", "add", "remove", "for", "via", "and",
    "the", "full", "half", "fixed", "copper", "fibre", "fiber", "gig", "cross",
    "straight", "awp", "cr", "proj", "project", "red", "api", "user", "defined",
    "default", "bridge", "eth", "vlan", "vlans", "tunnel", "queueing", "queuing",
    "priority", "source", "destination", "address", "static", "lag", "lacp",
    "interop", "exploratory", "testing", "platform-test", "functional",
    "field", "info", "error", "message", "generated", "whenever", "address",
})


def _relevance_score(rank_words: List[str], fields: List[Tuple[str, float]]):
    """(score, matched_token_count, total_hits). Verbatim from wizard.py."""
    if not rank_words:
        return 0.0, 0, 0
    matched = set()
    weighted = 0.0
    total_hits = 0
    for text, weight in fields:
        if not text:
            continue
        low = text.lower()
        for w in rank_words:
            occ = low.count(w)
            if occ <= 0:
                continue
            matched.add(w)
            total_hits += occ
            whole = re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low) is not None
            tf = 1.0 + math.log1p(occ - 1)
            weighted += weight * tf * (1.35 if whole else 1.0)
    if not matched:
        return 0.0, 0, 0
    coverage = len(matched) / len(set(rank_words))
    phrase_bonus = 0.0
    if len(rank_words) > 1:
        phrase = " ".join(rank_words)
        if any(phrase in (t or "").lower() for t, _ in fields):
            phrase_bonus = 0.15
    raw = 1.0 - math.exp(-weighted / 4.0)
    score = 0.35 + 0.5 * raw + 0.10 * coverage + phrase_bonus
    return min(0.95, round(score, 4)), len(matched), total_hits


def _split_atp_title_description(full_desc: str, fallback_id: str = "") -> Tuple[str, str]:
    """Verbatim from wizard.py: (short_title, full_body)."""
    full = (full_desc or "").strip()
    if not full:
        return (fallback_id or "", "")
    for marker in ("\n\n[", "\n["):
        idx = full.find(marker)
        if idx > 0:
            title = full[:idx].strip().split("\n")[0].strip()
            if title:
                return (title, full)
    for line in full.splitlines():
        line = line.strip()
        if line:
            return (line, full)
    return (fallback_id or full[:80], full)


# pytest script scorer (12/10/6 weights) — verbatim from pytest_create.py
_PT_GENERIC_TOKENS = {
    "test", "tests", "testing", "verify", "verifies", "check", "checks",
    "confirm", "confirms", "switch", "switches", "port", "ports", "device",
    "devices", "case", "cases", "script", "run", "running", "show", "output",
    "correct", "correctly", "ensure", "behaviour", "behavior", "default",
    "config", "configure", "configuration", "set", "and", "the", "with",
}
_PT_AREA_SUPPORT = {"ipv4", "ipv6", "poe", "vlan", "stp", "qos", "acl", "lldp",
                    "snmp", "dhcp", "igmp", "epsr", "ospf", "bgp", "reboot",
                    "stack", "stacking", "mirror", "sfp", "pluggable"}


def _pt_tokens(s: str) -> set:
    s = (s or "").replace("_", " ").replace("/", " ").replace("-", " ").lower()
    words = re.findall(r"[a-z0-9][a-z0-9+]{1,}", s)
    out = set()
    for w in words:
        if len(w) < 3:
            continue
        out.add(w)
        if w in ("mdi", "mdix"):
            out.update(("mdi", "mdix"))
    return out


def _score_script_candidate(query_toks: set, slim: dict) -> Tuple[float, str]:
    """Verbatim from pytest_create.py."""
    q_spec = {t for t in query_toks if t not in _PT_GENERIC_TOKENS}
    tag_toks = set()
    for t in slim.get("feature_tags") or []:
        tag_toks |= _pt_tokens(t)
    dir_toks = _pt_tokens(re.sub(r"^\d+_", "", slim.get("suite_dir") or ""))
    blob = ((slim.get("title") or "") + " " + (slim.get("summary") or "")).lower()
    blob_toks = _pt_tokens(blob)

    score, reasons = 0.0, []
    tag_hits = q_spec & tag_toks
    if tag_hits:
        score += 12.0 * len(tag_hits)
        reasons.append("tags: " + ", ".join(sorted(tag_hits)[:4]))
    dir_hits = q_spec & dir_toks
    if dir_hits:
        score += 10.0 * len(dir_hits)
        reasons.append("suite: " + ", ".join(sorted(dir_hits)[:3]))
    blob_hits = (q_spec & blob_toks) - tag_hits - dir_hits
    if blob_hits:
        score += 6.0 * len(blob_hits)
        reasons.append("text: " + ", ".join(sorted(blob_hits)[:4]))

    if score <= 0:
        return 0.0, ""
    all_hits = tag_hits | dir_hits | blob_hits
    if len(all_hits) == 1 and next(iter(all_hits)) in _PT_AREA_SUPPORT and score < 12:
        return 0.0, ""
    if slim.get("kind") == "test":
        score += 1.0
    if slim.get("db") == "art":
        score += 1.5
    return score, "; ".join(reasons[:3])


# ─────────────────────────────────────────────────────────────────────────────
# FTS query builder
# ─────────────────────────────────────────────────────────────────────────────
def _fts_match_expr(rank_words: List[str]) -> str:
    """OR-of-tokens with prefix variants: `"tok" OR "tok"*` per word.

    Retrieval is deliberately generous (FTS gives recall); the Python re-score
    below applies the exact live formula, so over-recalled rows that don't match
    the scored fields fall out at nmatch<=0.
    """
    parts = []
    for w in rank_words:
        esc = w.replace('"', '""')
        parts.append(f'"{esc}"')
        parts.append(f'"{esc}"*')
    return " OR ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Zephyr reads  (kills the per-request zephyr_cases.jsonl linear scan)
# ─────────────────────────────────────────────────────────────────────────────
def _zephyr_row_to_case(r: sqlite3.Row) -> dict:
    return {
        "src": "zephyr_xml" if r["src"] == "xml" else r["src"],
        "key": r["key"], "title": r["title"], "folder": r["folder"],
        "objective": r["objective"] or "", "precondition": r["precondition"] or "",
        "priority": r["priority"] or "", "status": r["status"] or "",
        "labels": _json(r["labels"], []),
        "script_type": r["script_type"] or "", "script_text": r["script_text"] or "",
        "steps": _json(r["steps"], []),
    }


def get_case(key: str) -> Optional[dict]:
    r = _one("SELECT * FROM zephyr_cases WHERE key=?", (key,))
    return _zephyr_row_to_case(r) if r else None


def get_zephyr_cases_batch(keys: List[str]) -> Dict[str, dict]:
    """Replacement for wizard._get_full_zephyr_cases_batch (no jsonl scan)."""
    out: Dict[str, dict] = {}
    wanted = [k for k in keys if k]
    for i in range(0, len(wanted), 500):
        chunk = wanted[i:i + 500]
        ph = ",".join("?" * len(chunk))
        for r in _rows(f"SELECT * FROM zephyr_cases WHERE key IN ({ph})", tuple(chunk)):
            out[r["key"]] = _zephyr_row_to_case(r)
    return out


def get_target_cases() -> List[dict]:
    return [_zephyr_row_to_case(r) for r in
            _rows("SELECT * FROM zephyr_cases WHERE is_target=1 ORDER BY key")]


# ─────────────────────────────────────────────────────────────────────────────
# Generator pipeline reads
# ─────────────────────────────────────────────────────────────────────────────
def get_candidates(key: str) -> Optional[dict]:
    r = _one("SELECT payload FROM candidates WHERE case_key=?", (key,))
    return _json(r["payload"], None) if r else None


def all_candidates() -> List[dict]:
    return [_json(r["payload"], {}) for r in _rows("SELECT payload FROM candidates")]


def get_current_case_keys() -> set:
    """Keys that own a candidate list — the Step-2 'current Cases' exclusion set."""
    keys = set()
    for c in all_candidates():
        if c.get("candidates"):
            keys.add(c.get("key"))
    keys.discard(None)
    return keys


def get_decisions() -> Dict[str, dict]:
    out = {}
    for r in _rows("SELECT key, matched_id, confidence, rationale FROM decisions"):
        out[r["key"]] = {"m": _json(r["matched_id"], None), "c": r["confidence"], "w": r["rationale"]}
    return out


def get_decision(key: str) -> Optional[dict]:
    r = _one("SELECT matched_id, confidence, rationale FROM decisions WHERE key=?", (key,))
    return {"m": _json(r["matched_id"], None), "c": r["confidence"], "w": r["rationale"]} if r else None


def get_testlink_case(cid: str) -> Optional[dict]:
    r = _one("SELECT * FROM testlink_cases WHERE id=?", (cid,))
    if not r:
        return None
    return {
        "src": "testlink", "id": r["id"], "internal_id": r["internal_id"],
        "title": r["title"], "suite_top": r["suite_top"], "suite": r["suite"],
        "summary": r["summary"] or "", "preconditions": r["preconditions"] or "",
        "steps": _json(r["steps"], []), "importance": r["importance"], "status": r["status"],
    }


def get_atp_test(tid: str) -> Optional[dict]:
    r = _one("SELECT * FROM atp_tests WHERE tid=?", (tid,))
    if not r:
        return None
    return {
        "suite_id": r["suite_id"], "suite_name": r["suite_name"], "testSet": r["test_set"],
        "caseId": r["case_id"], "description": r["description"], "reference": r["reference"],
        "past_crs": _json(r["past_crs"], []), "current_crs": _json(r["current_crs"], []),
        "log_analysis": _json(r["log_analysis"], None),
    }


def get_script(sid: str) -> Optional[dict]:
    r = _one("SELECT * FROM scripts WHERE id=?", (sid,))
    if not r:
        return None
    return {
        "id": r["id"], "db": r["db"], "path": r["path"], "suite_dir": r["suite_dir"],
        "kind": r["kind"], "sha1": r["sha1"], "mtime": r["mtime"], "loc_total": r["loc_total"],
        "parse_error": r["parse_error"], "title": r["title"], "summary": r["summary"],
        "docstring": r["docstring"], "feature_tags": _json(r["feature_tags"], []),
        "covered_actions": _json(r["covered_actions"], []), "imports": _json(r["imports"], None),
        "testset": _json(r["testset"], None), "test_cases": _json(r["test_cases"], None),
        "helpers": _json(r["helpers"], None),
    }


def iter_scripts_slim(db_filter: str = ""):
    """Yield slim script records (fields _score_script_candidate reads)."""
    sql = "SELECT id, db, suite_dir, kind, title, summary, feature_tags FROM scripts"
    params: tuple = ()
    if db_filter:
        sql += " WHERE db=?"
        params = (db_filter,)
    for r in _rows(sql, params):
        yield {
            "id": r["id"], "db": r["db"], "suite_dir": r["suite_dir"], "kind": r["kind"],
            "title": r["title"] or "", "summary": r["summary"] or "",
            "feature_tags": _json(r["feature_tags"], []),
        }


def get_json_doc(name: str):
    r = _one("SELECT payload FROM json_docs WHERE name=?", (name,))
    return _json(r["payload"], None) if r else None


# ─────────────────────────────────────────────────────────────────────────────
# Search  (FTS retrieve → Python re-score with the live formula)
# ─────────────────────────────────────────────────────────────────────────────
def search_testlink(q: str, keep_ids: Optional[set] = None, limit: int = 20) -> List[Dict[str, Any]]:
    keep_ids = keep_ids or set()
    qlow = (q or "").lower().strip()
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9._+-]{1,}", qlow) if len(w) > 1]
    if not words and not keep_ids:
        return []
    specific = [w for w in words if w not in _ZREF_GENERIC_TOKENS]
    rank_words = specific or words

    cand: Dict[str, sqlite3.Row] = {}
    if rank_words:
        sql = ("SELECT c.id, c.title, c.summary, c.steps_text FROM testlink_fts f "
               "JOIN testlink_cases c ON c.rowid=f.rowid WHERE testlink_fts MATCH ?")
        for r in _rows(sql, (_fts_match_expr(rank_words),)):
            cand[r["id"]] = r
    for cid in keep_ids:
        if cid not in cand:
            r = _one("SELECT id, title, summary, steps_text FROM testlink_cases WHERE id=?", (cid,))
            if r:
                cand[cid] = r

    scored = []
    for cid, r in cand.items():
        title = r["title"] or ""
        score, nmatch, nhits = _relevance_score(rank_words, [
            (f"{cid} {title}", 3.0),
            (r["steps_text"] or "", 1.0),
        ])
        if nmatch <= 0 and cid not in keep_ids:
            continue
        scored.append((score, {
            "id": cid, "title": title, "score": score,
            "description": r["summary"] or title,
            "snippet": title or "", "source": "search",
            "justification": f"Matched search ({nmatch}/{len(set(rank_words))} terms, {nhits} hits)",
        }))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    out, seen = [], set()
    for _, item in scored:
        if item["id"] in keep_ids:
            out.append(item); seen.add(item["id"])
    fresh = 0
    for _, item in scored:
        if item["id"] in seen:
            continue
        out.append(item); fresh += 1
        if fresh >= limit:
            break
    return out


def search_zephyr(q: str, case_key: str = "", exclude_keys: Optional[set] = None,
                  keep_ids: Optional[set] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """External Zephyr cross-ref search. Scores over key+title+folder only (parity
    with the slim_index-based live search — objective/steps never scored here)."""
    current_cases = set(exclude_keys) if exclude_keys is not None else get_current_case_keys()
    if case_key:
        current_cases.add(case_key)
    keep_ids = keep_ids or set()
    qlow = (q or "").lower().strip()
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9._+-]{1,}", qlow) if len(w) > 1]
    if not words and not keep_ids:
        return []
    specific = [w for w in words if w not in _ZREF_GENERIC_TOKENS]
    rank_words = specific or words

    cand: Dict[str, sqlite3.Row] = {}
    if rank_words:
        sql = ("SELECT c.key, c.title, c.folder, c.status, c.has_objective, c.num_steps, c.labels "
               "FROM zephyr_fts f JOIN zephyr_cases c ON c.id=f.rowid "
               "WHERE zephyr_fts MATCH ?")
        for r in _rows(sql, (_fts_match_expr(rank_words),)):
            cand[r["key"]] = r
    for k in keep_ids:
        if k not in cand:
            r = _one("SELECT key, title, folder, status, has_objective, num_steps, labels "
                     "FROM zephyr_cases WHERE key=?", (k,))
            if r:
                cand[k] = r

    scored = []
    for rel_key, r in cand.items():
        if rel_key in current_cases:
            continue
        title = r["title"] or ""
        folder = r["folder"] or ""
        score, nmatch, nhits = _relevance_score(rank_words, [
            (f"{rel_key} {title}", 3.0),
            (folder, 1.0),
        ])
        if nmatch <= 0 and rel_key not in keep_ids:
            continue
        scored.append((score, {
            "key": rel_key, "id": rel_key, "title": title, "folder": folder, "score": score,
            "description": title,
            "justification": f"Matched search ({nmatch}/{len(set(rank_words))} terms, {nhits} hits)",
            "source": "search", "status": r["status"],
            "has_objective": bool(r["has_objective"]), "num_steps": r["num_steps"],
            "labels": _json(r["labels"], []),
        }))
    scored.sort(key=lambda x: (-x[0], x[1].get("key") or ""))
    out, seen_keys = [], set()
    for _, item in scored:
        if item["key"] in keep_ids:
            out.append(item); seen_keys.add(item["key"])
    seen_stems = set()
    fresh = 0
    for _, item in scored:
        if item["key"] in seen_keys:
            continue
        stem = re.sub(r"\s+", " ", (item.get("title") or "").lower())[:40]
        if stem in seen_stems:
            continue
        seen_stems.add(stem)
        out.append(item); fresh += 1
        if fresh >= limit:
            break
    return out


def search_atp(q: str, keep_ids: Optional[set] = None, limit: int = 20) -> List[Dict[str, Any]]:
    keep_ids = keep_ids or set()
    qlow = (q or "").lower().strip()
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9.+_-]{1,}", qlow) if len(w) > 2]
    specific = [w for w in words if w not in _ZREF_GENERIC_TOKENS]
    rank_words = specific or words

    cand: Dict[str, sqlite3.Row] = {}
    if rank_words:
        sql = ("SELECT c.tid, c.description, c.suite_name FROM atp_fts f "
               "JOIN atp_tests c ON c.rowid=f.rowid WHERE atp_fts MATCH ?")
        for r in _rows(sql, (_fts_match_expr(rank_words),)):
            cand[r["tid"]] = r
    for tid in keep_ids:
        if tid not in cand:
            r = _one("SELECT tid, description, suite_name FROM atp_tests WHERE tid=?", (tid,))
            if r:
                cand[tid] = r

    scored = []
    for tid, r in cand.items():
        desc = r["description"] or ""
        suite = r["suite_name"] or ""
        if "(not a functional test)" in desc.lower() or "(not a functional test)" in tid.lower():
            continue
        short_title, full_desc = _split_atp_title_description(desc, tid)
        score, nmatch, nhits = _relevance_score(rank_words, [
            (f"{tid} {short_title}", 3.0),
            (suite, 1.5),
            (full_desc, 1.0),
        ])
        if nmatch <= 0 and words and tid not in keep_ids:
            continue
        scored.append((score, {
            "id": tid, "description": full_desc, "title": short_title,
            "suite": suite, "score": score,
        }))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    out, seen = [], set()
    for _, item in scored:
        if item["id"] in keep_ids:
            out.append(item); seen.add(item["id"])
    fresh = 0
    for _, item in scored:
        if item["id"] in seen:
            continue
        out.append(item); fresh += 1
        if fresh >= limit:
            break
    return out


def search_scripts(query_tokens: set, db_filter: str = "", limit: int = 40) -> List[dict]:
    """Mirror of pytest_create._search_slim — scores every slim record (the pytest
    path never FTS-prefiltered; 830 rows is trivial to scan in full)."""
    out = []
    for slim in iter_scripts_slim(db_filter):
        score, reason = _score_script_candidate(query_tokens, slim)
        if score > 0:
            out.append({**slim, "score": round(score, 1), "reason": reason})
    out.sort(key=lambda c: (-c["score"], c["id"]))
    return out[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# Session CRUD  (Commit C imports the JSON files + rewires the routers; the
# functions live here now so the read API is complete.)
# ─────────────────────────────────────────────────────────────────────────────
def _session_id(kind: str, key: str) -> str:
    if kind == "pt":
        return key if key.startswith("pt-") else f"pt-{key}"
    if kind == "workspace":
        return "_workspace_llm"
    return key


def save_session(kind: str, key: str, payload: dict, llm_config: Optional[dict] = None) -> None:
    import json
    from datetime import datetime
    sid = _session_id(kind, key)
    case_key = key if kind in ("wizard", "pt") else None
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (id, kind, case_key, payload, llm_config, updated_at) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
        "kind=excluded.kind, case_key=excluded.case_key, payload=excluded.payload, "
        "llm_config=excluded.llm_config, updated_at=excluded.updated_at",
        (sid, kind, case_key, json.dumps(payload, default=str),
         json.dumps(llm_config, default=str) if llm_config is not None else None,
         datetime.utcnow().isoformat()))
    conn.commit()


def load_session(kind: str, key: str) -> Optional[dict]:
    sid = _session_id(kind, key)
    r = _one("SELECT payload, llm_config FROM sessions WHERE id=?", (sid,))
    if not r:
        return None
    payload = _json(r["payload"], {})
    lc = _json(r["llm_config"], None)
    if lc is not None:
        payload["llm_config"] = lc
    return payload


def delete_session(kind: str, key: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE id=?", (_session_id(kind, key),))
    conn.commit()


def list_session_progress() -> Dict[str, dict]:
    """Per-wizard-case confirm flags (json_extract over payload). Commit C aligns
    the emitted shape with wizard._session_progress_map when it rewires the router."""
    out: Dict[str, dict] = {}
    sql = ("SELECT id, "
           "json_extract(payload,'$.step1_confirmed'), json_extract(payload,'$.step2_confirmed'), "
           "json_extract(payload,'$.step3_confirmed'), json_extract(payload,'$.objectives_confirmed') "
           "FROM sessions WHERE kind='wizard'")
    for r in _rows(sql):
        out[r[0]] = {
            "step1": bool(r[1]), "step2": bool(r[2]), "step3": bool(r[3]),
            "objectives_confirmed": bool(r[4]), "status": "in_progress",
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Startup / health
# ─────────────────────────────────────────────────────────────────────────────
def get_meta(k: str) -> Optional[str]:
    r = _one("SELECT v FROM meta WHERE k=?", (k,))
    return r["v"] if r else None


def counts() -> Dict[str, int]:
    c = {}
    for t in ("zephyr_cases", "testlink_cases", "atp_tests", "scripts",
              "candidates", "decisions", "sessions"):
        c[t] = _one(f"SELECT count(*) AS n FROM {t}")["n"]
    c["zephyr_target"] = _one("SELECT count(*) AS n FROM zephyr_cases WHERE is_target=1")["n"]
    return c


def startup_check() -> Dict[str, Any]:
    """Report DB presence, counts, HAS_VEC. Never raises; the server decides."""
    info: Dict[str, Any] = {"db_path": _resolve_db_path(), "has_vec": HAS_VEC}
    try:
        get_connection()
        info["has_vec"] = HAS_VEC
        info["counts"] = counts()
        info["schema_version"] = get_meta("schema_version")
        info["built_at"] = get_meta("built_at")
        info["ok"] = info["counts"].get("zephyr_cases", 0) > 0
    except Exception as e:
        info["ok"] = False
        info["error"] = str(e)
    return info

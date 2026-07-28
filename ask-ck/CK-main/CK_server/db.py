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
import threading
from typing import Any, Dict, List, Optional, Tuple

# Prefer pysqlite3 (bundles a modern SQLite WITH enable_load_extension — needed to
# load sqlite-vec) when installed; otherwise the stdlib sqlite3. On builds whose
# sqlite3 lacks enable_load_extension (e.g. macOS system Python), vector search
# simply degrades to keyword (HAS_VEC=False) — never a startup failure. This is a
# portable capability preference, not a platform branch.
try:
    import pysqlite3 as sqlite3            # type: ignore
except ImportError:
    import sqlite3                          # type: ignore

from paths import DB_PATH, EMBED_MODEL_DIR
from timeutil import utc_now

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


_warned_missing = False


def _warn_db(e: Exception) -> None:
    global _warned_missing
    if not _warned_missing:
        print(f"WARNING: ck.db read failed ({e}). Run `python3 tool/build_db.py --fresh`. "
              "Reads degrade to empty until then.")
        _warned_missing = True


def _rows(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    try:
        return get_connection().execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:   # e.g. DB not built yet (no such table)
        _warn_db(e)
        return []


def _one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    try:
        return get_connection().execute(sql, params).fetchone()
    except sqlite3.OperationalError as e:
        _warn_db(e)
        return None


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


# Words that _ZREF_GENERIC_TOKENS strips as too common to RANK on, but which still
# carry real "same area" affinity — a port case and an IPv6 case are not neighbours.
# A binary specific/stripped stoplist cannot express that third tier, which is why
# _relevance_score accepts area_words separately (see below).
_AREA_WORDS = frozenset({"ipv4", "ipv6", "port", "switch", "poe", "stp", "vlan"})


def _relevance_score(rank_words: List[str], fields: List[Tuple[str, float]],
                     area_words: Tuple[str, ...] = ()):
    """(score, matched_token_count, total_hits).

    `area_words` is an OPT-IN third vocabulary tier, ported from the Generator's
    retired bespoke Step-2 scorer. Words in it were dropped from `rank_words` by the
    generic-token filter, but still contribute — at a reduced weight, and only when
    the specific overlap is THIN (<=1 matched rank word), which is exactly when the
    result set degenerates into a big score tie broken arbitrarily by key.

    Why it exists: for the case "Port - Auto Negotiation", both "port" and "auto" are
    generic, so `rank_words` collapses to ["negotiation"] and all 12 matches scored an
    identical 0.7683 — ordering them by key alone. The genuinely best cross-ref
    ("interface: port status, speed, duplex and negotiation") landed 9th and fell out
    of the top 8. The old scorer surfaced it at rank 1 precisely because it gave "port"
    a weak area boost (+8 on a 12-point base) instead of discarding it.

    Defaults to empty, so every existing caller is bit-for-bit unchanged; only
    search_zephyr opts in.
    """
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
    # Thin-overlap area affinity. Never counts toward `coverage` (that measures how
    # much of the SPECIFIC query was hit) and never rescues a zero-match row — it only
    # separates rows that would otherwise be exactly tied.
    if area_words and len(matched) <= 1:
        for text, weight in fields:
            if not text:
                continue
            low = text.lower()
            for w in area_words:
                if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low):
                    weighted += weight * 0.35
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
        "issues": _json(r["issues"], []) if "issues" in r.keys() else [],
        "attachments": _json(r["attachments"], []) if "attachments" in r.keys() else [],
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


# iter_zephyr_slim() was removed here. Its sole caller was the Generator's Step-2
# related-ref ranking, which streamed all ~45k rows through a bespoke Python scorer
# on the event loop. That path now uses search_zephyr() below (FTS + the shared
# _relevance_score), so a full-corpus scan is no longer needed anywhere. Do not
# reintroduce a whole-table iterator without an index-backed reason.


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
        "source_text": r["source_text"] if "source_text" in r.keys() else None,
    }


def get_script_source(sid: str) -> Optional[str]:
    """The whole literal file body for a script id (None if code not captured)."""
    r = _one("SELECT source_text FROM scripts WHERE id=?", (sid,))
    return r["source_text"] if r else None


def get_script_chunks(sid: str) -> List[dict]:
    """Literal-code chunks for a script id, in source order."""
    rows = _rows(
        "SELECT unit, name, descr, start_line, end_line, code FROM script_chunks "
        "WHERE script_id=? ORDER BY start_line", (sid,))
    return [{"unit": r["unit"], "name": r["name"], "descr": r["descr"],
             "start_line": r["start_line"], "end_line": r["end_line"], "code": r["code"]}
            for r in rows]


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
    # Third tier: query words the generic filter dropped that still mark a feature
    # AREA. Only meaningful when `specific` carried the ranking (otherwise these words
    # are already in rank_words). See _relevance_score's area_words.
    area_words = tuple(sorted({w for w in words if w in _AREA_WORDS} - set(rank_words))) \
        if specific else ()

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
        ], area_words=area_words)
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


def _code_snippet(code: str, words: List[str], ctx: int = 3, max_lines: int = 14) -> str:
    """A few lines of `code` centred on the first line that contains any query
    word (falls back to the head of the chunk) — for a compact search preview."""
    lines = (code or "").splitlines()
    if not lines:
        return ""
    hit = 0
    for i, ln in enumerate(lines):
        low = ln.lower()
        if any(w in low for w in words):
            hit = i
            break
    a = max(0, hit - ctx)
    return "\n".join(lines[a:a + max_lines])


def search_code(q: str, db_filter: str = "", limit: int = 20) -> List[dict]:
    """Literal-code keyword search over script_chunks (function / test-case / file
    bodies). FTS recall over name+descr+code, then the shared re-score weighting
    the symbol name and description above the raw body. Each hit carries a snippet
    and loc so a caller can cite `path:start-end`. Empty when no code was captured
    (script_chunks is empty until build_script_index.py runs on the testbox)."""
    qlow = (q or "").lower().strip()
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9._+-]*", qlow) if len(w) > 1]
    if not words:
        return []
    sql = ("SELECT ch.id, ch.script_id, ch.unit, ch.name, ch.descr, ch.start_line, "
           "ch.end_line, ch.code, s.path, s.db AS sdb, s.kind "
           "FROM chunks_fts f JOIN script_chunks ch ON ch.id=f.rowid "
           "JOIN scripts s ON s.id=ch.script_id WHERE chunks_fts MATCH ?")
    params: list = [_fts_match_expr(words)]
    if db_filter:
        sql += " AND s.db=?"
        params.append(db_filter)
    scored = []
    for r in _rows(sql, tuple(params)):
        score, nmatch, _ = _relevance_score(words, [
            (r["name"] or "", 3.0), (r["descr"] or "", 2.0), (r["code"] or "", 1.0)])
        if nmatch <= 0:
            continue
        scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]["script_id"], x[1]["start_line"] or 0))
    out = []
    for score, r in scored[:limit]:
        out.append({
            "chunk_id": r["id"], "id": r["script_id"], "script_id": r["script_id"],
            "path": r["path"], "db": r["sdb"], "kind": r["kind"], "unit": r["unit"],
            "name": r["name"], "descr": r["descr"], "start_line": r["start_line"],
            "end_line": r["end_line"], "code": r["code"],
            "snippet": _code_snippet(r["code"], words), "score": round(score, 2),
        })
    return out


def search_code_hybrid(q: str, db_filter: str = "", limit: int = 20) -> List[dict]:
    """search_code fused (RRF) with semantic KNN over vec_chunks. Degrades to the
    pure keyword result when sqlite-vec/embeddings are unavailable."""
    kw = search_code(q, db_filter=db_filter, limit=limit)
    if not HAS_VEC or not (q or "").strip():
        return kw
    try:
        qvec = embed_texts([q])[0]
    except Exception as e:
        print(f"WARNING: embed failed ({e}); keyword-only for this code query.")
        return kw
    hits = _vector_hits("chunks", qvec, k=200)
    if not hits:
        return kw

    def hydrate(chunk_id, sim):
        r = _one("SELECT ch.id, ch.script_id, ch.unit, ch.name, ch.descr, ch.start_line, "
                 "ch.end_line, ch.code, s.path, s.db AS sdb, s.kind FROM script_chunks ch "
                 "JOIN scripts s ON s.id=ch.script_id WHERE ch.id=?", (chunk_id,))
        if not r:
            return None
        if db_filter and r["sdb"] != db_filter:
            return None
        return {"chunk_id": r["id"], "id": r["script_id"], "script_id": r["script_id"],
                "path": r["path"], "db": r["sdb"], "kind": r["kind"], "unit": r["unit"],
                "name": r["name"], "descr": r["descr"], "start_line": r["start_line"],
                "end_line": r["end_line"], "code": r["code"],
                "snippet": _code_snippet(r["code"], [w for w in re.split(r"\W+", q.lower()) if w])}
    return _rrf_merge(kw, hits, "chunk_id", hydrate, limit)


# ─────────────────────────────────────────────────────────────────────────────
# Embeddings + hybrid (Stage D). Semantic search rides sqlite-vec; when the
# extension can't load (HAS_VEC=False) every hybrid entry point returns the pure
# keyword result, so callers never need to branch.
# ─────────────────────────────────────────────────────────────────────────────
EMBED_DIM = 384
EMBED_MODEL = os.getenv("CK_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_model = None

# entity -> (vec table, base table, base-rowid column, id column)
_VEC_TABLES = {
    "zephyr":   ("vec_zephyr",   "zephyr_cases",   "id",    "key"),
    "testlink": ("vec_testlink", "testlink_cases", "rowid", "id"),
    "atp":      ("vec_atp",      "atp_tests",      "rowid", "tid"),
    "scripts":  ("vec_scripts",  "scripts",        "rowid", "id"),
    "chunks":   ("vec_chunks",   "script_chunks",  "id",    "id"),
}


def _get_model():
    """Lazy-load the sentence-transformers model (CK_EMBED_MODEL, cached under
    EMBED_MODEL_DIR / SENTENCE_TRANSFORMERS_HOME).

    Ask CK is a stand-alone product: the embedding model is BUNDLED locally under
    EMBED_MODEL_DIR and must load from disk with zero network access. We force
    HuggingFace offline mode so sentence-transformers never contacts huggingface.co
    — not to download, and not for the revision-check it otherwise does even when
    the files are already cached. (Refreshing the model is a deliberate, offline
    re-fetch step, never a runtime dependency.) Set these BEFORE the library is
    imported, since the flags are read at import time."""
    global _model
    if _model is None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer
        cache = os.getenv("SENTENCE_TRANSFORMERS_HOME", str(EMBED_MODEL_DIR))
        _model = SentenceTransformer(EMBED_MODEL, cache_folder=cache)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Encode texts to L2-normalized EMBED_DIM float vectors (cosine-ready)."""
    model = _get_model()
    vecs = model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True,
                        show_progress_bar=False)
    return [v.tolist() for v in vecs]


def _serialize_vec(vec: List[float]) -> bytes:
    import sqlite_vec
    return sqlite_vec.serialize_float32(vec)


def _vector_hits(entity: str, qvec: List[float], k: int = 200) -> List[Tuple[str, float]]:
    """KNN over an entity's vec table. Returns [(entity_id, cos_sim)] best-first.
    Vec tables use distance_metric=cosine, so cos_sim = 1 - distance. []
    when vectors are unavailable/empty."""
    if not HAS_VEC:
        return []
    vt, base, rowcol, idcol = _VEC_TABLES[entity]
    try:
        # sqlite-vec KNN requires the LIMIT/k constraint to sit on the vec0 table
        # in the SAME query level as MATCH — a JOIN with an outer ORDER BY/LIMIT is
        # rejected ("A LIMIT or 'k = ?' constraint is required on vec0 knn queries")
        # and would silently fall through the except below, disabling semantic
        # search entirely. So do the KNN first (subquery), then join to hydrate ids.
        rows = get_connection().execute(
            f"SELECT b.{idcol} AS id, knn.dist AS dist FROM "
            f"(SELECT rowid AS rid, distance AS dist FROM {vt} "
            f" WHERE embedding MATCH ? ORDER BY distance LIMIT ?) knn "
            f"JOIN {base} b ON b.{rowcol} = knn.rid ORDER BY knn.dist",
            (_serialize_vec(qvec), k)).fetchall()
    except sqlite3.OperationalError:
        return []   # vec table not built yet
    return [(r["id"], round(1.0 - r["dist"], 4)) for r in rows]


def _rrf_merge(keyword_rows: List[dict], vector_hits: List[Tuple[str, float]],
               id_key: str, hydrate, limit: int, k: int = 60,
               keep_ids: Optional[set] = None) -> List[dict]:
    """Reciprocal Rank Fusion of a keyword result list and a vector hit list.

    Keyword rows keep their formula scores; vector-only rows are hydrated via
    `hydrate(id, cos_sim)` and scored min(0.95, 0.35 + 0.5*cos_sim) with a
    'Semantic match (cos N.NN)' justification (source='search') so the app.js
    merge keeps working. Ordering is by fused RRF.

    `keep_ids` are pinned: always returned (re-scored) regardless of where they fuse,
    matching the keyword layer's contract."""
    rrf: Dict[str, float] = {}
    kw_by_id: Dict[str, dict] = {}
    for rank, row in enumerate(keyword_rows):
        rid = row.get(id_key)
        kw_by_id[rid] = row
        rrf[rid] = rrf.get(rid, 0.0) + 1.0 / (k + rank)
    sim_by_id: Dict[str, float] = {}
    for rank, (rid, sim) in enumerate(vector_hits):
        sim_by_id[rid] = sim
        rrf[rid] = rrf.get(rid, 0.0) + 1.0 / (k + rank)
    merged = []
    for rid, score in sorted(rrf.items(), key=lambda x: (-x[1], str(x[0]))):
        if rid in kw_by_id:
            row = dict(kw_by_id[rid])
        else:
            sim = sim_by_id.get(rid, 0.0)
            row = hydrate(rid, sim)
            if row is None:
                continue
            row["score"] = min(0.95, round(0.35 + 0.5 * sim, 2))
            row["justification"] = f"Semantic match (cos {sim:.2f})"
            row["source"] = "search"
        row["rrf"] = round(score, 6)
        merged.append(row)
    # Pinned rows (the client's current pool) must ALWAYS come back, re-scored — that is
    # the keep_ids contract the keyword layer implements with a two-pass emit
    # (search_testlink:476-485). This used to be a plain `merged[:limit]`, so a kept item
    # that fused low was silently dropped from the pool the moment the user re-searched.
    # Mirror the keyword layer: emit pinned first, then fill with the rest up to `limit`.
    keep_ids = keep_ids or set()
    if not keep_ids:
        return merged[:limit]
    out = [r for r in merged if r.get(id_key) in keep_ids]
    seen = {r.get(id_key) for r in out}
    fresh = 0
    for r in merged:
        if r.get(id_key) in seen:
            continue
        out.append(r)
        fresh += 1
        if fresh >= limit:
            break
    return out


def _hybrid(entity: str, q: str, keyword_rows: List[dict], id_key: str,
            hydrate, limit: int, keep_ids: Optional[set] = None) -> List[dict]:
    if not HAS_VEC or not (q or "").strip():
        return keyword_rows
    try:
        qvec = embed_texts([q])[0]
    except Exception as e:
        print(f"WARNING: embed failed ({e}); keyword-only for this query.")
        return keyword_rows
    hits = _vector_hits(entity, qvec, k=200)
    if not hits:
        return keyword_rows
    return _rrf_merge(keyword_rows, hits, id_key, hydrate, limit, keep_ids=keep_ids)


def search_zephyr_hybrid(q: str, case_key: str = "", exclude_keys: Optional[set] = None,
                         keep_ids: Optional[set] = None, limit: int = 20) -> List[dict]:
    kw = search_zephyr(q, case_key=case_key, exclude_keys=exclude_keys,
                       keep_ids=keep_ids, limit=limit)
    excl = set(exclude_keys) if exclude_keys is not None else get_current_case_keys()
    if case_key:
        excl.add(case_key)

    def hydrate(key, sim):
        if key in excl:
            return None
        r = _one("SELECT key, title, folder, status, has_objective, num_steps, labels "
                 "FROM zephyr_cases WHERE key=?", (key,))
        if not r:
            return None
        return {"key": r["key"], "id": r["key"], "title": r["title"], "folder": r["folder"],
                "description": r["title"], "status": r["status"],
                "has_objective": bool(r["has_objective"]), "num_steps": r["num_steps"],
                "labels": _json(r["labels"], [])}
    return _hybrid("zephyr", q, kw, "key", hydrate, limit, keep_ids=keep_ids)


def search_testlink_hybrid(q: str, keep_ids: Optional[set] = None, limit: int = 20) -> List[dict]:
    kw = search_testlink(q, keep_ids=keep_ids, limit=limit)

    def hydrate(cid, sim):
        r = _one("SELECT id, title, summary FROM testlink_cases WHERE id=?", (cid,))
        if not r:
            return None
        return {"id": r["id"], "title": r["title"] or "",
                "description": r["summary"] or r["title"] or "", "snippet": r["title"] or ""}
    return _hybrid("testlink", q, kw, "id", hydrate, limit, keep_ids=keep_ids)


def search_atp_hybrid(q: str, keep_ids: Optional[set] = None, limit: int = 20) -> List[dict]:
    kw = search_atp(q, keep_ids=keep_ids, limit=limit)

    def hydrate(tid, sim):
        r = _one("SELECT tid, description, suite_name FROM atp_tests WHERE tid=?", (tid,))
        if not r:
            return None
        short_title, full_desc = _split_atp_title_description(r["description"] or "", tid)
        return {"id": r["tid"], "description": full_desc, "title": short_title,
                "suite": r["suite_name"] or ""}
    return _hybrid("atp", q, kw, "id", hydrate, limit, keep_ids=keep_ids)


# ─────────────────────────────────────────────────────────────────────────────
# Session CRUD  (Commit C). The routers (wizard.py / pytest_create.py) delegate
# their persist/load/clear helpers here; session JSON files stay in place as a
# frozen pre-migration backup. `llm_config` (may hold a plaintext api_key) is
# stored in its OWN column, never in `payload`, so progress/log queries can't
# leak it — encryption-at-rest is noted debt.
# ─────────────────────────────────────────────────────────────────────────────
def _session_id(kind: str, key: str) -> str:
    if kind == "pt":
        return key if key.startswith("pt-") else f"pt-{key}"
    if kind == "workspace":
        return "_workspace_llm"
    return key


def _write_session(sid: str, kind: str, case_key: Optional[str],
                   payload_json: str, llm_config_json: Optional[str]) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (id, kind, case_key, payload, llm_config, updated_at) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
        "kind=excluded.kind, case_key=excluded.case_key, payload=excluded.payload, "
        "llm_config=excluded.llm_config, updated_at=excluded.updated_at",
        (sid, kind, case_key, payload_json, llm_config_json,
         utc_now().isoformat()))
    conn.commit()


def save_session(kind: str, key: str, model_dump: dict) -> None:
    """Persist a wizard/pt session from its full model dump. The `llm_config`
    field is split into its own column so `payload` never carries the credential."""
    import json
    d = dict(model_dump or {})
    llm_config = d.pop("llm_config", None)
    _write_session(
        _session_id(kind, key), kind, d.get("key"),
        json.dumps(d, default=str),
        json.dumps(llm_config, default=str) if llm_config is not None else None)


def load_session(kind: str, key: str) -> Optional[dict]:
    """Return the full model dump (llm_config merged back in) or None."""
    r = _one("SELECT payload, llm_config FROM sessions WHERE id=?", (_session_id(kind, key),))
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


def save_workspace_llm(cfg: dict) -> None:
    """Workspace-default LLM config (the old sessions/_workspace_llm.json). The
    whole record IS a credential, so it lives in the llm_config column; payload
    is empty."""
    import json
    _write_session("_workspace_llm", "workspace", None, "{}",
                   json.dumps(cfg, default=str) if cfg is not None else None)


def load_workspace_llm() -> Optional[dict]:
    r = _one("SELECT llm_config FROM sessions WHERE id='_workspace_llm'")
    return _json(r["llm_config"], None) if r else None


def list_session_progress() -> Dict[str, dict]:
    """Per-wizard-case progress map — exact replica of wizard._session_progress_map,
    now sourced from the sessions table instead of globbing sessions/*.json."""
    out: Dict[str, dict] = {}
    for r in _rows("SELECT id, payload FROM sessions WHERE kind='wizard'"):
        raw = _json(r["payload"], {})
        key = raw.get("key") or r["id"]
        s1 = bool((raw.get("step1") or {}).get("confirmed"))
        s2 = bool((raw.get("step2") or {}).get("confirmed"))
        s3 = bool((raw.get("step3") or {}).get("confirmed"))
        s4 = raw.get("step4") or {}
        s5 = raw.get("step5") or {}
        has_obj = bool(isinstance(s4, dict) and (s4.get("objective") or "").strip())
        has_steps = bool(
            (isinstance(s5, dict) and (s5.get("testScript") or {}).get("steps"))
            or (isinstance(s4, dict) and (s4.get("testScript") or {}).get("steps"))
        )
        has_step4 = bool(s4) or has_obj
        n_conf = sum([s1, s2, s3])
        if n_conf or has_step4 or has_steps or (raw.get("gaps") or "").strip():
            out[key] = {
                "step1": s1, "step2": s2, "step3": s3,
                "has_step4": has_step4, "has_objective": has_obj,
                "objectives_confirmed": bool(isinstance(s4, dict) and s4.get("confirmed")),
                "has_step5": has_steps, "confirms": n_conf, "status": "in_progress",
            }
    return out


def list_pt_progress() -> Dict[str, dict]:
    """Per-PyTest-Creator-case progress map (kind='pt'). Returns, per case key, how
    far the PyTest Creator flow has gotten — used to split the Complete cases into
    'in progress' vs 'complete' in the PyTest Creator Cases panel. A case is
    PyTest-'complete' only when step 8 (Final Validation) is both confirmed and
    validated (mirrors updatePtBadges' step-8 rule in pytest.js)."""
    out: Dict[str, dict] = {}
    for r in _rows("SELECT id, payload FROM sessions WHERE kind='pt'"):
        raw = _json(r["payload"], {})
        key = raw.get("key") or r["id"]
        s8 = raw.get("step8") or {}
        validated = bool(s8.get("confirmed") and s8.get("validated"))
        # confirms = how many of steps 2-8 are confirmed, as a lightweight hint
        confirms = sum(bool((raw.get(f"step{n}") or {}).get("confirmed")) for n in range(2, 9))
        out[key] = {"validated": validated, "confirms": confirms,
                    "status": "complete" if validated else "in_progress"}
    return out


def snapshot_sessions() -> List[tuple]:
    """Dump the sessions table (for --fresh session preservation in build_db)."""
    return [tuple(r) for r in _rows(
        "SELECT id, kind, case_key, payload, llm_config, updated_at FROM sessions")]


def restore_sessions(rows: List[tuple]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        "INSERT OR REPLACE INTO sessions (id, kind, case_key, payload, llm_config, updated_at) "
        "VALUES (?,?,?,?,?,?)", rows)
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Startup / health
# ─────────────────────────────────────────────────────────────────────────────
def get_meta(k: str) -> Optional[str]:
    r = _one("SELECT v FROM meta WHERE k=?", (k,))
    return r["v"] if r else None


def counts() -> Dict[str, int]:
    c = {}
    for t in ("zephyr_cases", "testlink_cases", "atp_tests", "scripts", "script_chunks",
              "candidates", "decisions", "sessions"):
        c[t] = _one(f"SELECT count(*) AS n FROM {t}")["n"]
    c["zephyr_target"] = _one("SELECT count(*) AS n FROM zephyr_cases WHERE is_target=1")["n"]
    return c


def embeddings_count() -> int:
    r = _one("SELECT count(*) AS n FROM embeddings_meta")
    return r["n"] if r else 0


def startup_check() -> Dict[str, Any]:
    """Report DB presence, counts, HAS_VEC + embedding state. Never raises."""
    info: Dict[str, Any] = {"db_path": _resolve_db_path(), "has_vec": HAS_VEC}
    try:
        get_connection()
        info["has_vec"] = HAS_VEC
        info["counts"] = counts()
        info["schema_version"] = get_meta("schema_version")
        info["built_at"] = get_meta("built_at")
        n_emb = embeddings_count()
        info["embeddings"] = n_emb
        info["embed_model"] = get_meta("embed_model")
        # Vector search is only live when the extension loaded AND vectors exist.
        info["vector_search"] = bool(HAS_VEC and n_emb > 0)
        info["ok"] = info["counts"].get("zephyr_cases", 0) > 0
    except Exception as e:
        info["ok"] = False
        info["error"] = str(e)
    return info

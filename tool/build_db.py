#!/usr/bin/env python3
"""ONE-SHOT constructor that built ask-ck/var/ck.db from the original source data.

>>> HISTORICAL / PROVENANCE ONLY — DO NOT RUN AGAINST THE LIVE REPO. <<<

`ck.db` is now the PERMANENT single source of truth: it was built ONCE from the
data provided, then committed to git (LFS). The courier/source files this script
ingested (zephyr_cases.jsonl, testlink_awp.json, candidates.json, the script
index/sidecar, …) have been RETIRED and deleted — so this script can no longer
rebuild anything, and a stray `--fresh` must never be allowed to wipe the
committed DB. This file is kept solely to document HOW the database was
constructed. `--require-sources` (default on) makes every build path abort with a
clear message when the sources are absent, which they now are.

To reconstruct from scratch you would first have to restore the original source
exports (Zephyr XML export + testbox scripts + the API snapshots) — that is a
deliberate, out-of-band act, not a routine operation and not part of the product.

Original source layout (now retired):
    objective-drafting/data/zephyr_full/zephyr_cases.jsonl   (45,427 xml cases)
    objective-drafting/data/zephyr_master.json               (410 api-target)
    objective-drafting/data/suites/testlink_awp.json         (21,624 testlink)
    objective-drafting/data/suites/test_id_description.json  (10,157 atp tests)
    pytest-create/data/scripts_index.json + scripts_sources.jsonl (830 scripts)
    objective-drafting/data/candidates.json                  (candidates)
    objective-drafting/data/decisions/*.json                 (14 files)
    pytest-create/data/framework_surface.json, scripts_index.meta.json
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

# tool/ scripts sys.path-insert CK_server (see enrich_script_index.py)
CK_SERVER = Path(__file__).resolve().parent.parent / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(CK_SERVER))

import db  # noqa: E402  (uses the single connection factory)
from paths import DATA_DIR, PT_DATA_DIR, VAR_DIR, DB_PATH  # noqa: E402

SCHEMA_SQL = CK_SERVER / "schema.sql"
SESSIONS_DIR = CK_SERVER / "sessions"
BATCH = 1000
SCHEMA_VERSION = "1"

# Expected counts (parity guard — --verify asserts against these).
# testlink: source has 21,624 records but AWP-17349 is duplicated → 21,620 unique
# ids. The live app dedupes identically ({id: item} dict in data.py), so 21,620
# IS the parity target, not the raw 21,624. decisions: 14 source files, 410 rows.
EXPECT = {"zephyr_cases": 45427, "zephyr_target": 410, "testlink_cases": 21620,
          "atp_tests": 10157, "scripts": 830, "decision_files": 14, "decision_rows": 410}


def _sha1(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _zephyr_steps_text(steps) -> str:
    return " ".join(f"{s.get('description','')} {s.get('testData','')} {s.get('expected','')}"
                    for s in (steps or [])).strip()


def _zephyr_refs_text(issues, attachments) -> str:
    """Flatten issue keys+summaries + attachment names into one FTS-recall blob."""
    parts = []
    for i in (issues or []):
        parts.append(f"{i.get('key','')} {i.get('summary','')}".strip())
    parts.extend(attachments or [])
    return " ".join(p for p in parts if p).strip()


def _tl_steps_text(steps) -> str:
    # First 20 steps, action+expected — matches wizard._search_testlink step_blob.
    return " ".join(f"{s.get('action','')} {s.get('expected','')}"
                    for s in (steps or [])[:20]).strip()


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
def apply_schema(conn):
    conn.executescript(SCHEMA_SQL.read_text())
    conn.commit()


def clear_corpora(conn):
    """Clear base tables so a full rebuild is idempotent without --fresh.
    (Sessions are intentionally preserved — Commit C manages those.)"""
    for t in ("zephyr_cases", "testlink_cases", "atp_tests", "scripts", "script_chunks",
              "candidates", "decisions", "json_docs"):
        conn.execute(f"DELETE FROM {t}")
    conn.commit()


def ingest_zephyr(conn):
    """Stream zephyr_cases.jsonl (src='xml'), then upsert zephyr_master (src='api',
    is_target=1; api wins on key conflict)."""
    jsonl = DATA_DIR / "zephyr_full" / "zephyr_cases.jsonl"
    ins = ("INSERT INTO zephyr_cases (key,src,is_target,title,folder,objective,precondition,"
           "priority,status,labels,script_type,script_text,steps,steps_text,num_steps,"
           "has_objective,issues,attachments,refs_text,content_sha1) "
           "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
    n = 0
    batch = []
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            steps = r.get("steps") or []
            obj = r.get("objective") or ""
            iss = r.get("issues") or []
            att = r.get("attachments") or []
            batch.append((
                r["key"], "xml", 0, r.get("title") or "", r.get("folder") or "",
                obj, r.get("precondition") or "", r.get("priority") or "", r.get("status") or "",
                json.dumps(r.get("labels") or []), r.get("script_type") or "",
                r.get("script_text") or "", json.dumps(steps), _zephyr_steps_text(steps),
                len(steps), 1 if obj.strip() else 0,
                json.dumps(iss) if iss else None, json.dumps(att) if att else None,
                _zephyr_refs_text(iss, att), _sha1(r)))
            if len(batch) >= BATCH:
                conn.executemany(ins, batch); n += len(batch); batch = []
    if batch:
        conn.executemany(ins, batch); n += len(batch)
    conn.commit()

    # zephyr_master upsert: api target cases win on key conflict.
    master = _load_json(DATA_DIR / "zephyr_master.json")
    ups = ("INSERT INTO zephyr_cases (key,src,is_target,title,folder,objective,precondition,"
           "priority,status,labels,script_type,script_text,steps,steps_text,num_steps,"
           "has_objective,issues,attachments,refs_text,content_sha1) "
           "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
           "ON CONFLICT(key) DO UPDATE SET src=excluded.src, is_target=1, title=excluded.title, "
           "folder=excluded.folder, objective=excluded.objective, precondition=excluded.precondition, "
           "priority=excluded.priority, status=excluded.status, labels=excluded.labels, "
           "script_type=excluded.script_type, script_text=excluded.script_text, steps=excluded.steps, "
           "steps_text=excluded.steps_text, num_steps=excluded.num_steps, "
           "has_objective=excluded.has_objective, issues=excluded.issues, "
           "attachments=excluded.attachments, refs_text=excluded.refs_text, "
           "content_sha1=excluded.content_sha1")
    m = 0
    for r in master:
        steps = r.get("steps") or []
        obj = r.get("objective") or ""
        iss = r.get("issues") or []
        att = r.get("attachments") or []
        conn.execute(ups, (
            r["key"], "api", 1, r.get("title") or "", r.get("folder") or "",
            obj, r.get("precondition") or "", r.get("priority") or "", r.get("status") or "",
            json.dumps(r.get("labels") or []), r.get("script_type") or "",
            r.get("script_text") or "", json.dumps(steps), _zephyr_steps_text(steps),
            len(steps), 1 if obj.strip() else 0,
            json.dumps(iss) if iss else None, json.dumps(att) if att else None,
            _zephyr_refs_text(iss, att), _sha1(r)))
        m += 1
    conn.commit()
    print(f"  zephyr_cases: {n} xml + {m} api-target upserts")
    return n, m


def ingest_testlink(conn):
    rows = _load_json(DATA_DIR / "suites" / "testlink_awp.json")
    ins = ("INSERT OR REPLACE INTO testlink_cases (id,internal_id,title,suite_top,suite,summary,"
           "preconditions,importance,status,steps,steps_text,content_sha1) "
           "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")
    batch, n, skipped = [], 0, 0
    for r in rows:
        cid = r.get("id")
        if not cid:
            skipped += 1
            continue
        steps = r.get("steps") or []
        batch.append((cid, r.get("internal_id"), r.get("title") or "", r.get("suite_top"),
                      r.get("suite"), r.get("summary") or "", r.get("preconditions") or "",
                      r.get("importance"), r.get("status"), json.dumps(steps),
                      _tl_steps_text(steps), _sha1(r)))
        if len(batch) >= BATCH:
            conn.executemany(ins, batch); n += len(batch); batch = []
    if batch:
        conn.executemany(ins, batch); n += len(batch)
    conn.commit()
    print(f"  testlink_cases: {n}" + (f" ({skipped} skipped: no id)" if skipped else ""))
    return n


def ingest_atp(conn):
    descs = _load_json(DATA_DIR / "suites" / "test_id_description.json")
    ins = ("INSERT OR REPLACE INTO atp_tests (tid,suite_id,suite_name,test_set,case_id,description,"
           "reference,past_crs,current_crs,log_analysis,is_functional,content_sha1) "
           "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")
    batch, n = [], 0
    for tid, info in descs.items():
        suite_id = info.get("suite_id")
        suite_name = info.get("suite_name")
        if not suite_id or not suite_name:
            # The historical silent-drop bug becomes a named, loud error.
            raise ValueError(f"ATP {tid}: missing suite_id/suite_name "
                             f"(suite_id={suite_id!r}, suite_name={suite_name!r}) — refusing to drop silently")
        desc = info.get("description") or ""
        is_func = 0 if ("(not a functional test)" in desc.lower()
                        or "(not a functional test)" in tid.lower()) else 1
        la = info.get("log_analysis")
        pc, cc = info.get("past_crs"), info.get("current_crs")
        batch.append((tid, suite_id, suite_name, info.get("testSet"), info.get("caseId"),
                      desc, info.get("reference"),
                      json.dumps(pc) if pc is not None else None,
                      json.dumps(cc) if cc is not None else None,
                      json.dumps(la) if la is not None else None, is_func, _sha1(info)))
        if len(batch) >= BATCH:
            conn.executemany(ins, batch); n += len(batch); batch = []
    if batch:
        conn.executemany(ins, batch); n += len(batch)
    conn.commit()
    print(f"  atp_tests: {n}")
    return n


def ingest_scripts(conn):
    idx = _load_json(PT_DATA_DIR / "scripts_index.json")
    # title lives in the slim index, keyed by id
    slim_by_id = {}
    slim_path = PT_DATA_DIR / "scripts_slim_index.json"
    if slim_path.exists():
        for s in _load_json(slim_path):
            slim_by_id[s.get("id")] = s
    ins = ("INSERT OR REPLACE INTO scripts (id,db,path,suite_dir,kind,sha1,mtime,loc_total,"
           "parse_error,title,summary,docstring,feature_tags,covered_actions,imports,testset,"
           "test_cases,helpers,tags_text,dir_text) "
           "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
    batch, n = [], 0
    for r in idx:
        ft = r.get("feature_tags") or []
        ca = r.get("covered_actions") or []
        suite_dir = r.get("suite_dir") or ""
        title = (slim_by_id.get(r.get("id"), {}) or {}).get("title") or ""
        tags_text = " ".join(list(ft) + list(ca))
        dir_text = re.sub(r"[_/-]", " ", re.sub(r"^\d+_", "", suite_dir))
        batch.append((
            r.get("id"), r.get("db"), r.get("path") or "", suite_dir, r.get("kind"),
            r.get("sha1") or "", r.get("mtime"), r.get("loc_total"), r.get("parse_error"),
            title, r.get("summary") or "", r.get("docstring") or "",
            json.dumps(ft), json.dumps(ca), json.dumps(r.get("imports")),
            json.dumps(r.get("testset")), json.dumps(r.get("test_cases")),
            json.dumps(r.get("helpers")), tags_text, dir_text))
        if len(batch) >= BATCH:
            conn.executemany(ins, batch); n += len(batch); batch = []
    if batch:
        conn.executemany(ins, batch); n += len(batch)
    conn.commit()
    print(f"  scripts: {n}")
    return n


def ingest_script_sources(conn):
    """Load the literal-code sidecar (scripts_sources.jsonl) written by
    build_script_index.py: fill scripts.source_text and populate script_chunks.
    The sidecar is OPTIONAL — when absent (e.g. the extractor has not been re-run
    on the testbox yet) scripts still ingest fully, just without code. Matched by
    (id, sha1): a stale sidecar entry whose sha1 no longer matches the freshly
    indexed script is skipped, so code never drifts out of sync with metadata."""
    sidecar = PT_DATA_DIR / "scripts_sources.jsonl"
    if not sidecar.exists():
        print("  script sources: (no scripts_sources.jsonl — code columns empty; "
              "run tool/build_script_index.py on the testbox to capture code)")
        return 0
    # Current id -> sha1 from the just-ingested scripts table (the parity anchor).
    cur = {r["id"]: r["sha1"] for r in conn.execute("SELECT id, sha1 FROM scripts")}
    ins = ("INSERT INTO script_chunks (script_id,unit,name,descr,start_line,end_line,"
           "code,content_sha1) VALUES (?,?,?,?,?,?,?,?)")
    n_src = n_chunk = n_stale = 0
    batch = []
    with open(sidecar, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            sid, sha = rec.get("id"), rec.get("sha1")
            if cur.get(sid) != sha:            # stale/orphan sidecar entry
                n_stale += 1
                continue
            conn.execute("UPDATE scripts SET source_text=? WHERE id=?",
                         (rec.get("source_text") or "", sid))
            n_src += 1
            for ch in rec.get("chunks") or []:
                loc = ch.get("loc") or [None, None]
                code = ch.get("code") or ""
                batch.append((sid, ch.get("unit") or "file", ch.get("name") or "",
                              ch.get("descr") or "", loc[0], loc[1], code, _sha1(code)))
                if len(batch) >= BATCH:
                    conn.executemany(ins, batch); n_chunk += len(batch); batch = []
    if batch:
        conn.executemany(ins, batch); n_chunk += len(batch)
    conn.commit()
    print(f"  script sources: {n_src} files with code, {n_chunk} chunks"
          + (f" ({n_stale} stale sidecar rows skipped)" if n_stale else ""))
    return n_chunk


def ingest_candidates(conn):
    cands = _load_json(DATA_DIR / "candidates.json")
    conn.executemany("INSERT OR REPLACE INTO candidates (case_key,payload) VALUES (?,?)",
                     [(c["key"], json.dumps(c)) for c in cands if c.get("key")])
    conn.commit()
    print(f"  candidates: {len(cands)}")
    return len(cands)


def ingest_decisions(conn):
    dec_dir = DATA_DIR / "decisions"
    files = sorted(p for p in dec_dir.glob("*.json"))
    rows = []
    for p in files:
        d = _load_json(p)
        for key, v in d.items():
            # 'm' (matched_id) is usually a string but 3/410 are lists — JSON-encode
            # so the original type round-trips (db.get_decision decodes it back).
            rows.append((key, json.dumps(v.get("m")), v.get("c"), v.get("w"), p.name))
    conn.executemany("INSERT OR REPLACE INTO decisions (key,matched_id,confidence,rationale,source_file) "
                     "VALUES (?,?,?,?,?)", rows)
    conn.commit()
    print(f"  decisions: {len(rows)} entries from {len(files)} files")
    return len(files)


def ingest_json_docs(conn):
    from datetime import datetime
    docs = {"framework_surface": PT_DATA_DIR / "framework_surface.json",
            "scripts_index_meta": PT_DATA_DIR / "scripts_index.meta.json"}
    n = 0
    for name, path in docs.items():
        if path.exists():
            conn.execute("INSERT OR REPLACE INTO json_docs (name,payload,updated_at) VALUES (?,?,?)",
                         (name, json.dumps(_load_json(path)), datetime.utcnow().isoformat()))
            n += 1
    conn.commit()
    print(f"  json_docs: {n}")
    return n


def fts_rebuild(conn):
    for t in ("zephyr_fts", "testlink_fts", "atp_fts", "scripts_fts", "chunks_fts"):
        conn.execute(f"INSERT INTO {t}({t}) VALUES('rebuild')")
    conn.commit()
    print("  FTS rebuilt (5 indexes)")


def _snapshot_sessions_file(path: str):
    """Read the sessions table straight from the existing DB file (before --fresh
    deletes it) so live sessions survive a corpora rebuild. Sessions are PRIMARY
    data now, not a derived cache."""
    import sqlite3
    if not os.path.exists(path):
        return []
    c = sqlite3.connect(path)
    try:
        return [tuple(r) for r in c.execute(
            "SELECT id, kind, case_key, payload, llm_config, updated_at FROM sessions")]
    except sqlite3.OperationalError:
        return []
    finally:
        c.close()


# ── Stage D: embeddings ──────────────────────────────────────────────────────
# vec0 tables are created HERE (not in schema.sql) because CREATE VIRTUAL TABLE
# USING vec0 needs the sqlite-vec extension loaded. Keyword-only builds / Pythons
# without enable_load_extension never touch this path.
def _ensure_vec_schema(conn):
    for vt in ("vec_zephyr", "vec_testlink", "vec_atp", "vec_scripts", "vec_chunks"):
        conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {vt} "
                     "USING vec0(embedding float[384] distance_metric=cosine)")
    conn.commit()


def _zephyr_embed_text(r):
    t = (r["title"] or "").strip()
    obj = (r["objective"] or "").strip()
    return f"{t} {obj}".strip() if obj else f"{t} {r['folder'] or ''}".strip()


# entity -> (vec table, SELECT of base rows with rid+content_sha1, text builder)
_EMBED_SPEC = {
    "zephyr": ("vec_zephyr",
               "SELECT id AS rid, title, objective, folder, content_sha1 AS sha FROM zephyr_cases",
               _zephyr_embed_text),
    "testlink": ("vec_testlink",
                 "SELECT rowid AS rid, title, summary, content_sha1 AS sha FROM testlink_cases",
                 lambda r: f"{r['title'] or ''} {r['summary'] or ''}".strip()),
    "atp": ("vec_atp",
            "SELECT rowid AS rid, description, content_sha1 AS sha FROM atp_tests",
            lambda r: (r["description"] or "").strip()),
    "scripts": ("vec_scripts",
                "SELECT rowid AS rid, title, summary, feature_tags, sha1 AS sha FROM scripts",
                lambda r: f"{r['title'] or ''} {r['summary'] or ''} "
                          f"{' '.join(json.loads(r['feature_tags'] or '[]'))}".strip()),
    # Literal-code chunks. Lead with name+descr (survives the model's ~256-token
    # truncation) then the code body. base_rowid = script_chunks.id.
    "chunks": ("vec_chunks",
               "SELECT id AS rid, name, descr, code, content_sha1 AS sha FROM script_chunks",
               lambda r: f"{r['name'] or ''} {r['descr'] or ''}\n{r['code'] or ''}".strip()),
}


def embed(batch: int = 64, limit=None):
    """Resumable, Ctrl-C-safe embedding pass. Skips rows whose content_sha1+model
    already match embeddings_meta, so re-runs are near-instant and a model switch
    (CK_EMBED_MODEL) auto-invalidates. Commits per batch."""
    import db
    from datetime import datetime
    # HAS_VEC is only resolved once a connection is opened (the extension probe
    # lives in get_connection()); open it FIRST, then gate on the result. Checking
    # db.HAS_VEC before this call always reads the import-time False and skips.
    conn = db.get_connection()
    if not db.HAS_VEC:
        print("  sqlite-vec unavailable on this Python (enable_load_extension missing or "
              "extension load failed) — skipping --embed. Keyword search is unaffected; run "
              "--embed on a host where sqlite-vec loads (e.g. Linux, or with pysqlite3).")
        return
    _ensure_vec_schema(conn)
    model = db.EMBED_MODEL
    print(f"Embedding with {model} (batch={batch}"
          + (f", limit={limit}/entity" if limit else "") + ")…")
    total = 0
    for entity, (vt, sql, text_fn) in _EMBED_SPEC.items():
        done = {r[0]: r[1] for r in conn.execute(
            "SELECT base_rowid, content_sha1 FROM embeddings_meta WHERE entity=? AND model=?",
            (entity, model))}
        pending = []
        for r in conn.execute(sql):
            if done.get(r["rid"]) == r["sha"]:
                continue
            pending.append((r["rid"], text_fn(r), r["sha"]))
            if limit and len(pending) >= limit:
                break
        if not pending:
            print(f"  {entity}: up to date ({len(done)} embedded)")
            continue
        n = 0
        for i in range(0, len(pending), batch):
            chunk = pending[i:i + batch]
            vecs = db.embed_texts([t for _, t, _ in chunk])
            ts = datetime.utcnow().isoformat()
            for (rid, _txt, sha), vec in zip(chunk, vecs):
                conn.execute(f"DELETE FROM {vt} WHERE rowid=?", (rid,))
                conn.execute(f"INSERT INTO {vt}(rowid, embedding) VALUES (?, ?)",
                             (rid, db._serialize_vec(vec)))
                conn.execute("INSERT OR REPLACE INTO embeddings_meta "
                             "(entity, base_rowid, content_sha1, model, embedded_at) "
                             "VALUES (?,?,?,?,?)", (entity, rid, sha, model, ts))
            conn.commit()          # per-batch → Ctrl-C keeps progress
            n += len(chunk)
            print(f"    {entity}: {n}/{len(pending)}", end="\r", flush=True)
        print(f"  {entity}: embedded {n}")
        total += n
    conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES ('embed_model', ?)", (model,))
    conn.commit()
    print(f"Embeddings done ({total} new/changed).")


def import_sessions() -> int:
    """One-shot import of the JSON session files into the sessions table. Files
    stay in place as a frozen pre-migration backup (never deleted)."""
    import db
    if not SESSIONS_DIR.exists():
        print("  no sessions/ directory — nothing to import")
        return 0
    n_w = n_p = n_ws = 0
    for p in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            raw = _load_json(p)
        except Exception as e:
            print(f"  skip {p.name}: {e}")
            continue
        stem = p.stem
        if stem == "_workspace_llm":
            db.save_workspace_llm(raw); n_ws += 1
        elif stem.startswith("pt-"):
            db.save_session("pt", raw.get("key") or stem[3:], raw); n_p += 1
        elif stem.startswith("AWPTCM-"):
            db.save_session("wizard", raw.get("key") or stem, raw); n_w += 1
    print(f"  imported sessions: {n_w} wizard, {n_p} pt, {n_ws} workspace")
    return n_w + n_p + n_ws


def write_meta(conn, counts):
    from datetime import datetime
    src_files = {
        "zephyr_cases.jsonl": DATA_DIR / "zephyr_full" / "zephyr_cases.jsonl",
        "zephyr_master.json": DATA_DIR / "zephyr_master.json",
        "testlink_awp.json": DATA_DIR / "suites" / "testlink_awp.json",
        "test_id_description.json": DATA_DIR / "suites" / "test_id_description.json",
        "scripts_index.json": PT_DATA_DIR / "scripts_index.json",
        "scripts_sources.jsonl": PT_DATA_DIR / "scripts_sources.jsonl",
        "candidates.json": DATA_DIR / "candidates.json",
    }
    meta = {"schema_version": SCHEMA_VERSION, "built_at": datetime.utcnow().isoformat()}
    for name, p in src_files.items():
        if p.exists():
            st = p.stat()
            meta[f"src_mtime:{name}"] = str(st.st_mtime)
            meta[f"src_size:{name}"] = str(st.st_size)
    for k, v in counts.items():
        meta[f"count:{k}"] = str(v)
    conn.executemany("INSERT OR REPLACE INTO meta (k,v) VALUES (?,?)", list(meta.items()))
    conn.commit()


def build(fresh: bool):
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    saved_sessions = []
    if fresh:
        # Sessions are primary data — preserve them across the file wipe.
        saved_sessions = _snapshot_sessions_file(str(DB_PATH))
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(DB_PATH) + suffix)
            if p.exists():
                p.unlink()
        print(f"  --fresh: removed {DB_PATH.name}(+wal/shm)"
              + (f"; preserving {len(saved_sessions)} sessions" if saved_sessions else ""))
    conn = db.get_connection()
    t0 = time.time()
    apply_schema(conn)
    clear_corpora(conn)
    if saved_sessions:
        db.restore_sessions(saved_sessions)
    print("Ingesting…")
    ingest_zephyr(conn)
    ingest_testlink(conn)
    ingest_atp(conn)
    ingest_scripts(conn)
    ingest_script_sources(conn)
    ingest_candidates(conn)
    ingest_decisions(conn)
    ingest_json_docs(conn)
    fts_rebuild(conn)
    c = db.counts()
    write_meta(conn, c)
    print(f"Done in {time.time()-t0:.1f}s → {DB_PATH}")
    print("Counts:", json.dumps(c, indent=None))
    return c


def verify():
    c = db.counts()
    conn = db.get_connection()
    dec_files = conn.execute("SELECT count(DISTINCT source_file) FROM decisions").fetchone()[0]
    ok = True
    print("Verify (counts vs expected):")
    checks = {"zephyr_cases": c["zephyr_cases"], "zephyr_target": c["zephyr_target"],
              "testlink_cases": c["testlink_cases"], "atp_tests": c["atp_tests"],
              "scripts": c["scripts"], "decision_rows": c["decisions"], "decision_files": dec_files}
    for k, got in checks.items():
        exp = EXPECT[k]
        status = "OK " if got == exp else "MISMATCH"
        if got != exp:
            ok = False
        print(f"  [{status}] {k}: got {got}, expect {exp}")
    # Spot lookups
    print("Spot lookups:")
    spots = []
    case = db.get_case("AWPTCM-T33234")
    spots.append(("get_case AWPTCM-T33234", bool(case and case.get("title"))))
    batch = db.get_zephyr_cases_batch(["AWPTCM-T33234", "AWPTCM-T33235"])
    spots.append(("get_zephyr_cases_batch x2", len(batch) == 2))
    spots.append(("get_target_cases == 410", len(db.get_target_cases()) == 410))
    tl = db.search_testlink("auto-negotiation")
    spots.append(("search_testlink('auto-negotiation') non-empty", len(tl) > 0))
    atp = db.search_atp("igmp snooping")
    spots.append(("search_atp('igmp snooping') non-empty", len(atp) > 0))
    zx = db.search_zephyr("auto negotiation")
    spots.append(("search_zephyr('auto negotiation') non-empty", len(zx) > 0))
    for name, good in spots:
        if not good:
            ok = False
        print(f"  [{'OK ' if good else 'FAIL'}] {name}")
    print("VERIFY:", "PASS" if ok else "FAIL")
    return ok


def _sources_present() -> bool:
    """True only if the retired source couriers still exist on disk. After the
    2026-07-20 teardown they do not, so a corpora (re)build cannot run."""
    return (DATA_DIR / "zephyr_full" / "zephyr_cases.jsonl").exists()


def main():
    ap = argparse.ArgumentParser(
        description="ONE-SHOT constructor of ask-ck/var/ck.db. Provenance only — "
                    "the source couriers are retired; corpora rebuild is disabled.")
    ap.add_argument("--fresh", action="store_true", help="delete ck.db first (sessions preserved)")
    ap.add_argument("--sessions", action="store_true",
                    help="one-shot import of sessions/*.json into the DB (no corpora rebuild)")
    ap.add_argument("--embed", action="store_true",
                    help="build/update semantic vectors (sqlite-vec; resumable, Ctrl-C-safe)")
    ap.add_argument("--batch", type=int, default=64, help="embedding batch size (--embed)")
    ap.add_argument("--limit", type=int, default=None, help="cap rows/entity (--embed; for testing)")
    ap.add_argument("--verify", action="store_true", help="assert counts + spot lookups after build")
    ap.add_argument("--i-know-sources-are-gone", action="store_true",
                    help="override the safety abort (ONLY after restoring the original source "
                         "exports out-of-band; corpora rebuild would otherwise wipe the committed DB)")
    args = ap.parse_args()

    # Corpora (re)build is a DELETE + re-ingest. ck.db is now the committed source
    # of truth and the ingest sources are gone — refuse, loudly, unless the operator
    # has explicitly restored sources and overrides. --embed/--sessions act on the
    # EXISTING DB (not a rebuild) and are left alone.
    if not (args.embed or args.sessions):
        if not _sources_present() and not args.i_know_sources_are_gone:
            sys.exit(
                "REFUSING to rebuild: the source courier files are retired (ck.db is the\n"
                "committed, permanent source of truth — see the module docstring). A rebuild\n"
                "would DELETE ck.db and cannot repopulate it. If you have deliberately restored\n"
                "the original source exports, re-run with --i-know-sources-are-gone.")

    if args.embed:
        # Embed into the existing DB; no corpora rebuild.
        embed(batch=args.batch, limit=args.limit)
    elif args.sessions:
        # Import into the existing DB; do NOT rebuild corpora.
        import_sessions()
    else:
        build(args.fresh)
    if args.verify:
        ok = verify()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

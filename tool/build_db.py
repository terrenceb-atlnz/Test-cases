#!/usr/bin/env python3
"""Build ask-ck/var/ck.db from the extractor JSON/JSONL source of truth.

Idempotent full rebuild (Commit A — no embeddings; Stage D adds --embed). Streams
the 54 MB zephyr_cases.jsonl line-by-line, executemany batches of 1000, one
transaction per source, prints counts. The DB is a DERIVED cache — re-run any
time after the extractors change: `python3 tool/build_db.py --fresh`.

Usage:
    python3 tool/build_db.py [--fresh] [--verify]

    --fresh    delete ck.db first (full clean rebuild)
    --verify   after building, assert row counts vs sources + spot lookups

Source of truth (unchanged this pass):
    objective-drafting/data/zephyr_full/zephyr_cases.jsonl   (45,427 xml cases)
    objective-drafting/data/zephyr_master.json               (410 api-target)
    objective-drafting/data/suites/testlink_awp.json         (21,624 testlink)
    objective-drafting/data/suites/test_id_description.json  (10,157 atp tests)
    pytest-create/data/scripts_index.json                    (830 scripts)
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
    return " ".join(f"{s.get('description','')} {s.get('expected','')}"
                    for s in (steps or [])).strip()


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
    for t in ("zephyr_cases", "testlink_cases", "atp_tests", "scripts",
              "candidates", "decisions", "json_docs"):
        conn.execute(f"DELETE FROM {t}")
    conn.commit()


def ingest_zephyr(conn):
    """Stream zephyr_cases.jsonl (src='xml'), then upsert zephyr_master (src='api',
    is_target=1; api wins on key conflict)."""
    jsonl = DATA_DIR / "zephyr_full" / "zephyr_cases.jsonl"
    ins = ("INSERT INTO zephyr_cases (key,src,is_target,title,folder,objective,precondition,"
           "priority,status,labels,script_type,script_text,steps,steps_text,num_steps,"
           "has_objective,content_sha1) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
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
            batch.append((
                r["key"], "xml", 0, r.get("title") or "", r.get("folder") or "",
                obj, r.get("precondition") or "", r.get("priority") or "", r.get("status") or "",
                json.dumps(r.get("labels") or []), r.get("script_type") or "",
                r.get("script_text") or "", json.dumps(steps), _zephyr_steps_text(steps),
                len(steps), 1 if obj.strip() else 0, _sha1(r)))
            if len(batch) >= BATCH:
                conn.executemany(ins, batch); n += len(batch); batch = []
    if batch:
        conn.executemany(ins, batch); n += len(batch)
    conn.commit()

    # zephyr_master upsert: api target cases win on key conflict.
    master = _load_json(DATA_DIR / "zephyr_master.json")
    ups = ("INSERT INTO zephyr_cases (key,src,is_target,title,folder,objective,precondition,"
           "priority,status,labels,script_type,script_text,steps,steps_text,num_steps,"
           "has_objective,content_sha1) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
           "ON CONFLICT(key) DO UPDATE SET src=excluded.src, is_target=1, title=excluded.title, "
           "folder=excluded.folder, objective=excluded.objective, precondition=excluded.precondition, "
           "priority=excluded.priority, status=excluded.status, labels=excluded.labels, "
           "script_type=excluded.script_type, script_text=excluded.script_text, steps=excluded.steps, "
           "steps_text=excluded.steps_text, num_steps=excluded.num_steps, "
           "has_objective=excluded.has_objective, content_sha1=excluded.content_sha1")
    m = 0
    for r in master:
        steps = r.get("steps") or []
        obj = r.get("objective") or ""
        conn.execute(ups, (
            r["key"], "api", 1, r.get("title") or "", r.get("folder") or "",
            obj, r.get("precondition") or "", r.get("priority") or "", r.get("status") or "",
            json.dumps(r.get("labels") or []), r.get("script_type") or "",
            r.get("script_text") or "", json.dumps(steps), _zephyr_steps_text(steps),
            len(steps), 1 if obj.strip() else 0, _sha1(r)))
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
    for t in ("zephyr_fts", "testlink_fts", "atp_fts", "scripts_fts"):
        conn.execute(f"INSERT INTO {t}({t}) VALUES('rebuild')")
    conn.commit()
    print("  FTS rebuilt (4 indexes)")


def write_meta(conn, counts):
    from datetime import datetime
    src_files = {
        "zephyr_cases.jsonl": DATA_DIR / "zephyr_full" / "zephyr_cases.jsonl",
        "zephyr_master.json": DATA_DIR / "zephyr_master.json",
        "testlink_awp.json": DATA_DIR / "suites" / "testlink_awp.json",
        "test_id_description.json": DATA_DIR / "suites" / "test_id_description.json",
        "scripts_index.json": PT_DATA_DIR / "scripts_index.json",
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
    if fresh:
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(DB_PATH) + suffix)
            if p.exists():
                p.unlink()
        print(f"  --fresh: removed {DB_PATH.name}(+wal/shm)")
    conn = db.get_connection()
    t0 = time.time()
    apply_schema(conn)
    clear_corpora(conn)
    print("Ingesting…")
    ingest_zephyr(conn)
    ingest_testlink(conn)
    ingest_atp(conn)
    ingest_scripts(conn)
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


def main():
    ap = argparse.ArgumentParser(description="Build ask-ck/var/ck.db from source JSON/JSONL.")
    ap.add_argument("--fresh", action="store_true", help="delete ck.db first")
    ap.add_argument("--verify", action="store_true", help="assert counts + spot lookups after build")
    args = ap.parse_args()
    build(args.fresh)
    if args.verify:
        ok = verify()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

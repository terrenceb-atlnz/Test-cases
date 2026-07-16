#!/usr/bin/env python3
"""Build the PyTest Creator script index (supporting the Test-cases project).

Scans the three test-script databases (testsuites_art, svt_scripts, test_scripts)
and the shared `framework` library, producing the indexes consumed by the
Ask CK PyTest Creator (`/api/pytest-create`):

    ask-ck/pytest-create/data/scripts_index.json       full mechanical records
    ask-ck/pytest-create/data/scripts_slim_index.json  search/scoring corpus
    ask-ck/pytest-create/data/framework_surface.json   framework vocabulary
    ask-ck/pytest-create/data/scripts_index.meta.json  build info

Pass 1 (mechanical) needs no LLM. Pass 2 (enrichment) is resumable and appends
to scripts_index_enrich.jsonl keyed by file sha1; merged results appear in both
index files on the next build.

Usage:
    ./build_script_index.py                    # mechanical + framework + merge enrichment
    ./build_script_index.py --mechanical-only  # skip enrichment merge warnings
    ./build_script_index.py --enrich [N]       # run LLM enrichment on N unenriched files
"""
import ast
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

TESTBOX_HOME = Path(os.environ.get("TESTBOX_HOME", "/media/terrenceb/mnt/testbox_home"))

ROOTS = {
    "art": TESTBOX_HOME / "testsuites_art",
    "svt": TESTBOX_HOME / "svt_scripts",
    "legacy": TESTBOX_HOME / "test_scripts",
}
FRAMEWORK_DIR = TESTBOX_HOME / "DeviceSkrips" / "framework"

EXCLUDES = (
    "1371_trex_traffic_tests",
    "trex_libs",
    "Python-3.9.19",
    "__pycache__",
    ".git",
    "ixnetwork_restpy_git",
    "node_modules",
    "a1c_playwright",   # web-UI Playwright automation (JS-oriented) — not AT framework scripts
    "sqlalchemy",       # vendored DB library bundled inside tools/memory_leak_tools — not a test script
)

# Legacy (test_scripts) suite directories are numeric-prefixed, e.g. 5003_feature_limits,
# 1364_vrf_limits. Index any .py inside such a suite dir (in-suite helpers/config often
# aren't named test-/library_ but are part of the suite).
_SUITE_DIR_RX = re.compile(r"^\d+_")

REPO_ROOT = Path(__file__).resolve().parent.parent
PT_DATA_DIR = REPO_ROOT / "ask-ck" / "pytest-create" / "data"

TESTCASE_META_ATTRS = ("testCaseDesc", "testCaseRef", "testCaseMethod")


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDES for part in path.parts)


def wanted_file(root_key: str, path: Path) -> bool:
    """Select indexable files: test scripts, per-suite libraries, shared libs, tools."""
    if root_key == "svt":
        # svt is small and its tests/helpers use varied names (ixNetworkTest_*, ATSifos...)
        return True
    name = path.name
    if name.startswith("test-") or name.startswith("test_"):
        return True
    if name.startswith("library_") or name.startswith("lib"):
        return True
    if name.startswith("ixNetworkTest"):
        return True
    if root_key == "legacy":
        if any(d in path.parts for d in ("tools", "misc_scripts", "platformTestScripts", "stre_scripts", "Validation")):
            return True
        # Any .py inside a numeric suite directory (in-suite helpers/config included).
        if any(_SUITE_DIR_RX.match(p) for p in path.parts):
            return True
    return False


def classify_svt(path: Path) -> str:
    name = path.name
    if name.startswith(("test-", "test_")) or name.startswith("ixNetworkTest_"):
        return "test"
    if name.startswith(("library_", "lib")) or "libSvt" in path.parts:
        return "library"
    return "tool"


def classify_kind(root_key: str, path: Path) -> str:
    if root_key == "svt":
        return classify_svt(path)
    name = path.name
    if name.startswith(("test-", "test_")) or name.startswith("ixNetworkTest_"):
        return "test"
    if name.startswith(("library_", "lib")) or "libSvt" in path.parts:
        return "library"
    return "tool"


def _const_str(node) -> str:
    """String value of a constant/str node ('' if not a plain string)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _join_binop_strings(node) -> str:
    """Best-effort flatten of 'a' + 'b' (+ formatted pieces) into text."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _join_binop_strings(node.left) + _join_binop_strings(node.right)
    return _const_str(node)


def extract_class_meta(cls: ast.ClassDef) -> dict:
    """Pull testCaseDesc/Ref/Method (including += accumulation) from a class body."""
    meta = {k: "" for k in TESTCASE_META_ATTRS}
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            tgt = stmt.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id in TESTCASE_META_ATTRS:
                meta[tgt.id] = _join_binop_strings(stmt.value)
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
            tgt = stmt.target
            if isinstance(tgt, ast.Name) and tgt.id in TESTCASE_META_ATTRS:
                meta[tgt.id] += _join_binop_strings(stmt.value)
    return meta


def base_names(cls: ast.ClassDef):
    out = []
    for b in cls.bases:
        if isinstance(b, ast.Name):
            out.append(b.id)
        elif isinstance(b, ast.Attribute):
            parts = []
            node = b
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            out.append(".".join(reversed(parts)))
    return out


def looks_like_testcase(cls: ast.ClassDef, meta: dict) -> bool:
    if meta.get("testCaseDesc"):
        return True
    return any("TestCase" in b for b in base_names(cls))


def looks_like_testset(cls: ast.ClassDef) -> bool:
    return cls.name == "TestSet" or any("TestSet" in b for b in base_names(cls))


def extract_testset_info(cls: ast.ClassDef) -> dict:
    info = {
        "init_devices": [],
        "portlinks": 0,
        "has_configure": False,
        "has_tear_down": False,
        "features": [],
    }
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            tgt = stmt.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id == "FEATURES" and isinstance(stmt.value, (ast.List, ast.Tuple)):
                info["features"] = [_const_str(e) for e in stmt.value.elts if _const_str(e)]
        if isinstance(stmt, ast.FunctionDef):
            if stmt.name == "configure":
                info["has_configure"] = True
            elif stmt.name == "tear_down":
                info["has_tear_down"] = True
            elif stmt.name == "init":
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        fn = node.func.attr
                        if fn in ("init_swi", "init_stk", "init_ixia", "init_trex"):
                            arg = _const_str(node.args[0]) if node.args else ""
                            info["init_devices"].append(arg or fn)
                        elif fn == "init_tb":
                            info["init_devices"].append("tb")
                        elif fn == "init_portlink":
                            info["portlinks"] += 1
    return info


def extract_imports(tree: ast.AST):
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module in ("framework", "ATPyLib"):
                # `from framework import ATTestSet, ATDrivers` -> framework.ATTestSet ...
                mods.update(f"{node.module}.{a.name}" for a in node.names)
            else:
                mods.add(node.module)
    return sorted(mods)


def extract_helpers(tree: ast.Module):
    helpers = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            doc = ast.get_docstring(node) or ""
            helpers.append({
                "name": node.name,
                "args": [a.arg for a in node.args.args],
                "doc": doc.strip().splitlines()[0] if doc.strip() else "",
                "loc": [node.lineno, getattr(node, "end_lineno", None)],
            })
    return helpers


_RX_CLASS = re.compile(r"^class\s+(\w+)", re.M)
_RX_DESC = re.compile(r"""testCaseDesc\s*\+?=\s*['"](.+?)['"]""")


def regex_fallback(src: str) -> dict:
    """Minimal extraction for files ast.parse cannot handle (py2 vintage)."""
    cases = []
    for m in _RX_CLASS.finditer(src):
        cases.append({"class": m.group(1), "desc": "", "ref": "", "method": "", "loc": [src[:m.start()].count("\n") + 1, None]})
    descs = _RX_DESC.findall(src)
    for i, d in enumerate(descs[: len(cases)]):
        cases[i]["desc"] = d
    return {"test_cases": cases, "imports": sorted(set(re.findall(r"^(?:from|import)\s+([\w.]+)", src, re.M))), "helpers": []}


def _slice_code(lines, loc):
    """lines: 0-indexed; loc: [start, end] 1-based inclusive. '' if unusable."""
    if not loc or not loc[0]:
        return ""
    a = loc[0]
    b = loc[1] or a
    return "\n".join(lines[a - 1:b])


def _build_chunks(rec, src):
    """Literal-code chunks for scripts_sources.jsonl — one per test_case / helper /
    testset (using the loc ranges already extracted), or a single whole-file 'file'
    chunk when none apply, so every captured script yields >=1 searchable unit."""
    lines = src.splitlines()
    basename = Path(rec["path"]).name
    whole = {"unit": "file", "name": basename, "descr": rec.get("docstring", ""),
             "loc": [1, rec["loc_total"]], "code": src}
    if rec.get("parse_error"):
        return [whole]
    chunks = []
    ts = rec.get("testset")
    if ts and ts.get("loc") and _slice_code(lines, ts["loc"]).strip():
        chunks.append({"unit": "testset", "name": ts.get("class") or basename,
                       "descr": rec.get("docstring", ""), "loc": ts["loc"],
                       "code": _slice_code(lines, ts["loc"])})
    for tc in rec.get("test_cases", []):
        code = _slice_code(lines, tc.get("loc"))
        if code.strip():
            chunks.append({"unit": "test_case", "name": tc.get("class", ""),
                           "descr": tc.get("desc", ""), "loc": tc["loc"], "code": code})
    for h in rec.get("helpers", []):
        code = _slice_code(lines, h.get("loc"))
        if code.strip():
            chunks.append({"unit": "helper", "name": h.get("name", ""),
                           "descr": h.get("doc", ""), "loc": h["loc"], "code": code})
    return chunks or [whole]


def index_file(root_key: str, root: Path, path: Path) -> dict:
    src = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(root)
    rec = {
        "id": f"{root_key}/{rel}",
        "db": root_key,
        "path": str(path),
        "suite_dir": rel.parts[0] if len(rel.parts) > 1 else "",
        "kind": classify_kind(root_key, path),
        "imports": [],
        "testset": None,
        "test_cases": [],
        "helpers": [],
        "docstring": "",
        "parse_error": False,
        "loc_total": src.count("\n") + 1,
        "sha1": hashlib.sha1(src.encode("utf-8", "replace")).hexdigest(),
        "mtime": int(path.stat().st_mtime),
    }
    try:
        tree = ast.parse(src)
    except SyntaxError:
        rec["parse_error"] = True
        rec.update(regex_fallback(src))
        rec["_source"] = src
        rec["_chunks"] = _build_chunks(rec, src)
        return rec

    doc = ast.get_docstring(tree) or ""
    rec["docstring"] = doc.strip().splitlines()[0] if doc.strip() else ""
    rec["imports"] = extract_imports(tree)
    rec["helpers"] = extract_helpers(tree)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        meta = extract_class_meta(node)
        end = getattr(node, "end_lineno", None)
        if looks_like_testset(node):
            rec["testset"] = extract_testset_info(node)
            rec["testset"]["loc"] = [node.lineno, end]
        elif looks_like_testcase(node, meta):
            rec["test_cases"].append({
                "class": node.name,
                "desc": meta["testCaseDesc"].strip(),
                "ref": meta["testCaseRef"].strip(),
                "method": meta["testCaseMethod"].strip(),
                "loc": [node.lineno, end],
            })
    rec["_source"] = src
    rec["_chunks"] = _build_chunks(rec, src)
    return rec


def build_mechanical():
    records = []
    for root_key, root in ROOTS.items():
        if not root.is_dir():
            print(f"WARNING: root missing, skipped: {root}", file=sys.stderr)
            continue
        n = 0
        for path in sorted(root.rglob("*.py")):
            if is_excluded(path.relative_to(root)) or not wanted_file(root_key, path):
                continue
            try:
                records.append(index_file(root_key, root, path))
                n += 1
            except Exception as e:  # never let one bad file kill the build
                print(f"ERROR indexing {path}: {e}", file=sys.stderr)
        print(f"{root_key}: indexed {n} files from {root}", file=sys.stderr)
    return records


def build_framework_surface():
    if not FRAMEWORK_DIR.is_dir():
        print(f"WARNING: framework dir missing: {FRAMEWORK_DIR}", file=sys.stderr)
        return {}
    surface = {}
    targets = list(FRAMEWORK_DIR.glob("*.py"))
    targets += list((FRAMEWORK_DIR / "ATDrivers").glob("*.py"))
    targets += list((FRAMEWORK_DIR / "ATLibrary").glob("**/*.py"))
    for path in sorted(targets):
        if is_excluded(path):
            continue
        mod = str(path.relative_to(FRAMEWORK_DIR).with_suffix("")).replace(os.sep, ".")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            surface[mod] = {"parse_error": True, "classes": {}, "functions": []}
            continue
        classes = {}
        functions = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = []
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and not sub.name.startswith("_"):
                        mdoc = ast.get_docstring(sub) or ""
                        methods.append({
                            "name": sub.name,
                            "args": [a.arg for a in sub.args.args if a.arg != "self"],
                            "doc": mdoc.strip().splitlines()[0] if mdoc.strip() else "",
                        })
                classes[node.name] = {"bases": base_names(node), "methods": methods}
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                fdoc = ast.get_docstring(node) or ""
                functions.append({
                    "name": node.name,
                    "args": [a.arg for a in node.args.args],
                    "doc": fdoc.strip().splitlines()[0] if fdoc.strip() else "",
                })
        surface[mod] = {"classes": classes, "functions": functions}
    print(f"framework surface: {len(surface)} modules from {FRAMEWORK_DIR}", file=sys.stderr)
    return surface


def load_enrichment():
    """sha1 -> {summary, feature_tags, covered_actions} from the resumable jsonl."""
    path = PT_DATA_DIR / "scripts_index_enrich.jsonl"
    out = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            out[row["sha1"]] = row
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def make_slim(records):
    slim = []
    for r in records:
        title = ""
        for tc in r["test_cases"]:
            if tc["desc"]:
                title = tc["desc"]
                break
        title = title or r["docstring"] or Path(r["path"]).name
        fw_imports = sorted({m for m in r["imports"] if m.startswith(("framework", "ATPyLib"))})
        slim.append({
            "id": r["id"],
            "db": r["db"],
            "suite_dir": r["suite_dir"],
            "kind": r["kind"],
            "title": title[:200],
            "n_cases": len(r["test_cases"]),
            "framework_imports": fw_imports,
            "feature_tags": r.get("feature_tags", []),
            "summary": r.get("summary", ""),
        })
    return slim


def write_outputs(records, surface, enrich_map):
    PT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    enriched = 0
    for r in records:
        e = enrich_map.get(r["sha1"])
        if e:
            r["summary"] = e.get("summary", "")
            r["feature_tags"] = e.get("feature_tags", [])
            r["covered_actions"] = e.get("covered_actions", [])
            enriched += 1

    # Split the heavy literal code out of the (committed, metadata-only) index
    # into a sidecar. build_db.py ingests it into scripts.source_text +
    # script_chunks; it is LFS-tracked like the other large corpora. Popping the
    # underscore keys keeps scripts_index.json lean and byte-stable.
    n_chunks = 0
    with (PT_DATA_DIR / "scripts_sources.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            source = r.pop("_source", None)
            chunks = r.pop("_chunks", []) or []
            if source is None:
                continue
            n_chunks += len(chunks)
            fh.write(json.dumps({"id": r["id"], "sha1": r["sha1"],
                                 "source_text": source, "chunks": chunks},
                                ensure_ascii=False) + "\n")
    print(f"scripts_sources.jsonl: {len(records)} files, {n_chunks} code chunks", file=sys.stderr)

    (PT_DATA_DIR / "scripts_index.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    (PT_DATA_DIR / "scripts_slim_index.json").write_text(
        json.dumps(make_slim(records), ensure_ascii=False, indent=1), encoding="utf-8")
    if surface:
        (PT_DATA_DIR / "framework_surface.json").write_text(
            json.dumps(surface, ensure_ascii=False, indent=1), encoding="utf-8")

    counts = {}
    for r in records:
        counts.setdefault(r["db"], {"test": 0, "library": 0, "tool": 0})
        counts[r["db"]][r["kind"]] += 1
    meta = {
        "built_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "roots": {k: str(v) for k, v in ROOTS.items()},
        "excludes": list(EXCLUDES),
        "counts": counts,
        "total_files": len(records),
        "parse_errors": sum(1 for r in records if r["parse_error"]),
        "enriched": enriched,
        "enrichment_pct": round(100.0 * enriched / len(records), 1) if records else 0.0,
        "framework_modules": len(surface),
    }
    (PT_DATA_DIR / "scripts_index.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=1), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mechanical-only", action="store_true",
                    help="build without merging/expecting LLM enrichment")
    ap.add_argument("--enrich", nargs="?", const=50, type=int, metavar="N",
                    help="run LLM enrichment on up to N unenriched files (default 50), then rebuild")
    args = ap.parse_args()

    if args.enrich is not None:
        from enrich_script_index import run_enrichment  # separate module, needs CK_server LLM config
        run_enrichment(limit=args.enrich)

    records = build_mechanical()
    surface = build_framework_surface()
    enrich_map = {} if args.mechanical_only else load_enrichment()
    write_outputs(records, surface, enrich_map)


if __name__ == "__main__":
    main()

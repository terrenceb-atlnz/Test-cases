"""PyTest Creator — turn completed (refined) test cases into runnable framework scripts.

Guided 8-step gated flow (see ask-ck/pytest-create/PLAN-pytest-creator.md):
  1 Cases (select a Complete case)        5 Fragments (reuse real code by symbol)
  2 Sequence (prescriptive steps, LLM)    6 Generate (LLM composite + naming + lint)
  3 Script Search (index + LLM re-rank)   7 Run (execute on a stored testbox)
  4 Fit Decision (reuse/extend/new)       8 Validate (all PASS + human confirm)

Patterns mirror routers/wizard.py: server-side confirmation gates, per-case JSON
session persistence (sessions/pt-{key}.json), workspace LLM config reuse.
"""

from fastapi import APIRouter, HTTPException, Body, Request
from starlette.concurrency import run_in_threadpool
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
from pathlib import Path
import html as html_mod
import json
import os
import py_compile
import re
import tempfile

from models import PtSession, LLMConfig
from paths import REFINED_DIR, PT_DATA_DIR, PT_GENERATED_DIR
from llm import run_prompt, extract_json_block
import db as dbx   # aliased: several functions here have a `db` filter parameter
from pt_exec import (
    load_profiles, save_profiles, redact_profile, normalize_profile,
    check_profile, parse_framework_log, failure_excerpts, run_manager,
)
from routers.wizard import _load_global_llm, _llm_is_active

router = APIRouter(tags=["pytest-creator"])

# In-memory sessions + file persistence, mirroring wizard.py
pt_sessions: Dict[str, PtSession] = {}
BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

TESTBOX_HOME = Path(os.environ.get("TESTBOX_HOME", "/media/terrenceb/mnt/testbox_home"))
FRAMEWORK_LINT_PARENT = TESTBOX_HOME / "DeviceSkrips"  # readable framework copy for lint

META_ROOT = PT_GENERATED_DIR / ".meta"

# Style anchor embedded in generation prompts: short, complete, has tear_down.
EXEMPLAR_ID = "art/6011_simul_fail/test-6011.1000.py"

STEP_KEYS = ["step2", "step3", "step4", "step5", "step6", "step7", "step8"]

_GROUP_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _()\-]{0,59}$")
_NAME_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,59}$")


# ---------------------------------------------------------------------------
# Session helpers (wizard.py:115-149 pattern, pt- prefix)
# ---------------------------------------------------------------------------

def _pt_session_path(key: str) -> Path:
    return SESSIONS_DIR / f"pt-{key}.json"


def _pt_persist(sess: PtSession) -> None:
    sess.updated_at = datetime.utcnow()
    try:
        data = sess.dict() if hasattr(sess, "dict") else sess.model_dump()
        with open(_pt_session_path(sess.key), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: failed to persist pt session {sess.key}: {e}")


def _pt_load(key: str) -> Optional[PtSession]:
    path = _pt_session_path(key)
    if path.exists():
        try:
            return PtSession(**json.load(open(path, encoding="utf-8")))
        except Exception as e:
            print(f"Warning: failed to load pt session {key}: {e}")
    return None


def _pt_get(key: str) -> PtSession:
    sess = pt_sessions.get(key) or _pt_load(key)
    if not sess:
        raise HTTPException(404, "PyTest Creator session not found. Call load_case first.")
    pt_sessions[key] = sess
    return sess


def _apply_workspace_llm(sess: PtSession) -> bool:
    """Copy the workspace LLM login into this session when it has none active."""
    if _llm_is_active(getattr(sess, "llm_config", None)):
        return False
    cfg = _load_global_llm()
    if not cfg:
        return False
    raw = cfg.dict() if hasattr(cfg, "dict") else cfg.model_dump()
    sess.llm_config = LLMConfig(**raw)
    return True


def _llm_cfg(sess: PtSession) -> dict:
    cfg = sess.llm_config
    return cfg.dict() if hasattr(cfg, "dict") else cfg.model_dump()


def _confirm(sess: PtSession, step_key: str) -> None:
    step = getattr(sess, step_key) or {}
    step["confirmed"] = True
    step["confirmed_at"] = datetime.utcnow().isoformat()
    setattr(sess, step_key, step)


def _invalidate_from(sess: PtSession, step_num: int) -> None:
    """Editing/confirming step N un-confirms every later step (gate integrity)."""
    for k in STEP_KEYS:
        if int(k[4:]) > step_num:
            step = getattr(sess, k) or {}
            if step.get("confirmed"):
                step["confirmed"] = False
                step["invalidated_at"] = datetime.utcnow().isoformat()
                setattr(sess, k, step)
    if step_num < 8 and (sess.step8 or {}).get("validated"):
        sess.step8 = {**sess.step8, "validated": False}


def _require_confirmed(sess: PtSession, step_key: str, what: str) -> None:
    if not (getattr(sess, step_key) or {}).get("confirmed"):
        raise HTTPException(409, f"{what} requires {step_key} to be confirmed first.")


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def _data(request: Request) -> dict:
    data = getattr(request.app.state, "app_data", None)
    if not data:
        raise HTTPException(503, "Server data not loaded yet.")
    return data


def _script_record(data: dict, script_id: str) -> dict:
    rec = (data.get("scripts_index_by_id") or {}).get(script_id)
    if not rec:
        raise HTTPException(404, f"Unknown script id: {script_id}")
    return rec


def _read_source(rec: dict, start: Optional[int] = None, end: Optional[int] = None) -> str:
    """Read a validated index record's source (optionally a 1-based line slice)."""
    path = Path(rec["path"])
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        raise HTTPException(500, f"Cannot read {rec['id']}: {e}")
    if start is None:
        return "\n".join(lines)
    end = end or len(lines)
    return "\n".join(lines[max(0, start - 1):min(len(lines), end)])


_TAG_RX = re.compile(r"<[^>]+>")


def _html_to_text(s: str) -> str:
    s = (s or "").replace("&nbsp;", " ").replace("<li>", "\n- ")
    return html_mod.unescape(_TAG_RX.sub(" ", s)).strip()


# ---------------------------------------------------------------------------
# Refined-case resolution (wizard._refined_complete_keys pattern, plus group)
# ---------------------------------------------------------------------------

def _find_refined_case(key: str) -> Tuple[str, dict, str]:
    """Return (group_dir_name, payload_dict, traceability_md) for a Complete case."""
    if not REFINED_DIR.exists():
        raise HTTPException(500, f"refined-cases dir missing: {REFINED_DIR}")
    for payload_path in REFINED_DIR.rglob("zephyr_payload.json"):
        if payload_path.parent.name == key:
            group = payload_path.parent.parent.name
            try:
                payload = json.load(open(payload_path, encoding="utf-8"))
            except Exception as e:
                raise HTTPException(500, f"Cannot parse {payload_path}: {e}")
            trace_path = payload_path.parent / "traceability.md"
            trace = trace_path.read_text(encoding="utf-8") if trace_path.exists() else ""
            return group, payload, trace
    raise HTTPException(404, f"{key} is not a Complete case (no refined zephyr_payload.json).")


def _case_payload_fields(sess: PtSession) -> dict:
    """objective + steps (minus the leading traceability note) from the snapshot."""
    payload = sess.payload or {}
    body = payload.get(sess.key) or (next(iter(payload.values())) if payload else {})
    objective = _html_to_text(body.get("objective", ""))
    steps = ((body.get("testScript") or {}).get("steps")) or []
    work_steps = []
    for i, s in enumerate(steps):
        desc = _html_to_text(s.get("description", ""))
        if i == 0 and ("wiki" in desc.lower() or "traceability" in desc.lower() or "covered by" in desc.lower()):
            continue  # step 0 traceability note
        work_steps.append({"description": desc,
                           "expectedResult": _html_to_text(s.get("expectedResult", ""))})
    return {"objective": objective, "steps": work_steps}


def _case_title(data: dict, key: str) -> str:
    zc = (data.get("zephyr_master") or {}).get(key) or {}
    return zc.get("title") or key


def _parsed_list(parsed: Any, key: str) -> list:
    """Pull a list out of an LLM JSON reply tolerant of shape.

    The prompts ask for {"<key>": [...]} but models sometimes return the bare
    [...] array (or {"<key>": {...single...}}). Normalize all of those to a list.
    """
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        val = parsed.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            return [val]
    return []


def _parsed_field(parsed: Any, key: str, default=""):
    """Fetch a scalar field from an LLM reply that may be a bare list."""
    return parsed.get(key, default) if isinstance(parsed, dict) else default


def _group_display(group_dir: str) -> str:
    """'Port (7)' -> 'Port' (refined-cases group dirs carry candidate counts)."""
    return re.sub(r"\s*\(\d+\)\s*$", "", group_dir).strip() or group_dir


def _propose_name(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title)
    stop = {"the", "a", "an", "of", "and", "or", "to", "for", "with", "test", "verify", "check"}
    core = [w for w in words if w.lower() not in stop][:4]
    return ("_".join(core) + "_test") if core else "generated_test"


# ---------------------------------------------------------------------------
# Query tokenization. The 12/10/6 script scorer + its stopword/area sets now live
# in db (db._score_script_candidate), applied inside dbx.search_scripts — single
# source of truth, no private copy here (Commit B).
# ---------------------------------------------------------------------------

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
    """Score a slim index record against the sequence/query tokens."""
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
    # Require one specific signal; single weak generic-area hit is noise
    all_hits = tag_hits | dir_hits | blob_hits
    if len(all_hits) == 1 and next(iter(all_hits)) in _PT_AREA_SUPPORT and score < 12:
        return 0.0, ""
    if slim.get("kind") == "test":
        score += 1.0  # prefer runnable tests over libs/tools at equal relevance
    if slim.get("db") == "art":
        score += 1.5  # canonical style
    return score, "; ".join(reasons[:3])


def _search_slim(data: dict, query_toks: set, db: str = "", limit: int = 40) -> List[dict]:
    """Commit B: mechanical script ranking delegates to dbx.search_scripts (same
    12/10/6 formula, applied over the scripts table). `db` = optional db filter
    ('art'/'svt'/'test'). `data` kept for signature compatibility."""
    return dbx.search_scripts(query_toks, db_filter=db, limit=limit)


# ---------------------------------------------------------------------------
# Generated-output helpers
# ---------------------------------------------------------------------------

def _validate_naming(group: str, name: str) -> Tuple[str, str]:
    group, name = (group or "").strip(), (name or "").strip()
    if not _GROUP_RX.match(group) or ".." in group:
        raise HTTPException(400, "Invalid group name (letters/digits/space/()-_ only).")
    if not _NAME_RX.match(name):
        raise HTTPException(400, "Invalid script name (letters/digits/-_ only, no extension).")
    return group, name


def _script_path(group: str, name: str) -> Path:
    return PT_GENERATED_DIR / group / f"{name}.py"


def _meta_dir(group: str, name: str) -> Path:
    return META_ROOT / group / name


def _parse_generated_blocks(content: str) -> Dict[str, Any]:
    """Extract test + optional 'LIBRARY: <name>' python blocks from LLM output."""
    blocks = re.findall(r"(?:^|\n)(LIBRARY:\s*(\S+)\s*\n)?```(?:python)?\s*\n(.*?)```",
                        content, re.DOTALL)
    test_code, library = None, None
    for _, lib_name, code in blocks:
        code = code.strip() + "\n"
        if lib_name:
            library = {"name": lib_name.strip(), "code": code}
        elif test_code is None:
            test_code = code
    return {"test_code": test_code, "library": library}


def _framework_surface_slice(data: dict, extra_modules: List[str]) -> dict:
    """Bounded framework vocabulary for the generation prompt."""
    surface = data.get("framework_surface") or {}
    core = ["ATTestSet", "ATTestCase", "Setup", "ATPackets",
            "ATDrivers.ATSwitch", "ATDrivers.ATTestBox", "ATDrivers.ATPower"]
    wanted = list(dict.fromkeys(core + [m.replace("framework.", "") for m in extra_modules]))
    return {m: surface[m] for m in wanted if m in surface}


def _lint_generated(sess: PtSession) -> dict:
    """Offline checks: py_compile + structural AST assertions + framework import check."""
    step6 = sess.step6 or {}
    files = step6.get("files") or {}
    test = files.get("test") or {}
    code = test.get("code") or ""
    if not code:
        raise HTTPException(409, "No generated script to lint. Run generate_script first.")
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Syntax
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        py_compile.compile(tmp, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"syntax: {e.msg}")
    finally:
        os.unlink(tmp)

    # 2. Structure
    import ast as ast_mod
    try:
        tree = ast_mod.parse(code)
    except SyntaxError:
        tree = None
    if tree:
        classes = [n for n in tree.body if isinstance(n, ast_mod.ClassDef)]
        testset = [c for c in classes if any("TestSet" in getattr(b, "attr", getattr(b, "id", ""))
                                             for b in c.bases)]
        cases = [c for c in classes if any("TestCase" in getattr(b, "attr", getattr(b, "id", ""))
                                           for b in c.bases)]
        if not testset:
            errors.append("structure: no TestSet(ATTestSet.TestSet) class")
        if not cases:
            errors.append("structure: no TestCase classes")
        for c in cases:
            attrs = {t.targets[0].id for t in c.body
                     if isinstance(t, ast_mod.Assign) and len(t.targets) == 1
                     and isinstance(t.targets[0], ast_mod.Name)}
            aug = {t.target.id for t in c.body
                   if isinstance(t, ast_mod.AugAssign) and isinstance(t.target, ast_mod.Name)}
            for req in ("testCaseDesc", "testCaseRef", "testCaseMethod"):
                if req not in attrs | aug:
                    errors.append(f"structure: {c.name} missing {req}")
            has_main = any(isinstance(n, ast_mod.FunctionDef) and n.name == "main" for n in c.body)
            inherits_local = any(isinstance(b, ast_mod.Name) and b.id not in ("object",)
                                 and "TestCase" not in b.id for b in c.bases)
            if not has_main and not inherits_local:
                warnings.append(f"{c.name} has no main() (ok only if a base class provides it)")
        src_tail = code[-600:]
        if "ts.run(sys.argv)" not in code and ".run(sys.argv)" not in src_tail:
            errors.append("structure: missing ts.run(sys.argv) __main__ entry")
        if "self.passed(" not in code and "self.failed(" not in code:
            warnings.append("no self.passed()/self.failed() calls found in this file "
                            "(ok only if inherited main() asserts)")

        # 3. Framework imports must exist in the surface index
        surface = {}
        surf_path = PT_DATA_DIR / "framework_surface.json"
        if surf_path.exists():
            try:
                surface = json.load(open(surf_path, encoding="utf-8"))
            except Exception:
                surface = {}
        if surface:
            for node in ast_mod.walk(tree):
                if isinstance(node, ast_mod.ImportFrom) and node.module:
                    mod = node.module
                    if mod.startswith("framework."):
                        short = mod[len("framework."):]
                        if short not in surface and short.replace(".", "/") not in surface:
                            errors.append(f"imports: framework module '{short}' not found in framework_surface")
                    elif mod == "framework":
                        for a in node.names:
                            if a.name not in ("ATTestSet", "ATTestCase", "ATDrivers", "ATPackets",
                                              "Setup", "ATTestTag", "ATTagFilter") \
                                    and a.name not in surface:
                                errors.append(f"imports: framework.{a.name} not found in framework_surface")

    lib = files.get("library")
    if lib and lib.get("name"):
        lib_name = Path(lib["name"]).stem
        if re.search(rf"\bimport\s+{re.escape(lib_name)}\b|\bfrom\s+{re.escape(lib_name)}\b", code) is None:
            warnings.append(f"library file {lib['name']} provided but never imported")

    result = {"ok": not errors, "errors": errors, "warnings": warnings,
              "checked_at": datetime.utcnow().isoformat()}
    step6["lint"] = result
    sess.step6 = step6
    return result


def _persist_generated_files(sess: PtSession) -> List[str]:
    """Write <Group>/<Name>.py (+library) and sidecar meta; returns written paths."""
    step6 = sess.step6 or {}
    naming = step6.get("naming") or {}
    group, name = _validate_naming(naming.get("group", ""), naming.get("name", ""))
    files = step6.get("files") or {}
    test = files.get("test") or {}
    if not test.get("code"):
        raise HTTPException(409, "No generated code to save.")

    script_path = _script_path(group, name)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    written = []
    script_path.write_text(test["code"], encoding="utf-8")
    written.append(str(script_path))
    lib = files.get("library")
    if lib and lib.get("code"):
        lib_path = script_path.parent / lib["name"]
        if not _NAME_RX.match(Path(lib["name"]).stem):
            raise HTTPException(400, "Invalid library file name.")
        lib_path.write_text(lib["code"], encoding="utf-8")
        written.append(str(lib_path))

    meta = _meta_dir(group, name)
    meta.mkdir(parents=True, exist_ok=True)
    seq_lines = [f"# Sequence — {sess.key}", ""]
    for s in (sess.step2 or {}).get("sequence") or []:
        seq_lines.append(f"{s.get('n')}. {s.get('action')}")
        seq_lines.append(f"   verify: {s.get('verify')}")
    (meta / "sequence.md").write_text("\n".join(seq_lines) + "\n", encoding="utf-8")
    provenance = {
        "case_key": sess.key,
        "group": group,
        "name": name,
        "saved_at": datetime.utcnow().isoformat(),
        "iterations": step6.get("iterations", 1),
        "fit_decision": {k: (sess.step4 or {}).get(k) for k in ("decision", "base_script")},
        "fragments": [{k: f.get(k) for k in ("source_id", "symbol", "maps_to")}
                      for f in (sess.step5 or {}).get("fragments") or []],
        "llm": (step6.get("provenance") or {}).get("llm", {}),
    }
    (meta / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    written.append(str(meta / "provenance.json"))
    return written


# ---------------------------------------------------------------------------
# Status + case/session lifecycle
# ---------------------------------------------------------------------------

@router.get("/status")
async def status(request: Request):
    data = getattr(request.app.state, "app_data", None) or {}
    meta = data.get("scripts_index_meta") or {}
    generated = []
    if PT_GENERATED_DIR.exists():
        generated = [str(p.relative_to(PT_GENERATED_DIR))
                     for p in PT_GENERATED_DIR.glob("*/*.py")]
    # Commit B: script count comes from ck.db (scripts table), not an in-RAM list.
    scripts_indexed = dbx.counts().get("scripts", 0)
    return {
        "tool": "pytest-create",
        "status": "ok" if scripts_indexed else "index-missing",
        "scripts_indexed": scripts_indexed,
        "index_counts": meta.get("counts", {}),
        "enrichment_pct": meta.get("enrichment_pct", 0.0),
        "index_built_at": meta.get("built_at"),
        "framework_modules": len(data.get("framework_surface") or {}),
        "profiles": len(load_profiles()),
        "generated_scripts": generated,
        "message": ("Run tool/build_db.py --fresh to build the script index."
                    if not scripts_indexed else None),
    }


@router.post("/load_case/{key}")
async def load_case(key: str, request: Request):
    data = _data(request)
    sess = pt_sessions.get(key) or _pt_load(key)
    if not sess:
        group, payload, trace = _find_refined_case(key)
        sess = PtSession(key=key, group=group, payload=payload, traceability=trace)
    # Mark runs orphaned by a restart
    runs = (sess.step7 or {}).get("runs") or []
    for r in runs:
        if r.get("status") in ("queued", "connecting", "uploading", "running") \
                and not run_manager.is_running(key):
            r["status"] = "stale"
    if runs:
        sess.step7 = {**sess.step7, "runs": runs}
    changed = _apply_workspace_llm(sess)
    pt_sessions[key] = sess
    _pt_persist(sess)
    fields = _case_payload_fields(sess)
    return {
        "session": sess.dict() if hasattr(sess, "dict") else sess.model_dump(),
        "case_title": _case_title(data, key),
        "group_display": _group_display(sess.group),
        "objective": fields["objective"],
        "steps": fields["steps"],
        "llm_applied_from_workspace": changed,
    }


@router.get("/session/{key}")
async def get_session(key: str):
    sess = _pt_get(key)
    return {"session": sess.dict() if hasattr(sess, "dict") else sess.model_dump()}


@router.post("/clear_session/{key}")
async def clear_session(key: str):
    pt_sessions.pop(key, None)
    path = _pt_session_path(key)
    if path.exists():
        path.unlink()
    return {"cleared": key}


@router.post("/confirm_step/{key}/{step}")
async def confirm_step(key: str, step: int, body: dict = Body(default={})):
    """Explicit human confirmation gate for steps 2-8 (wizard.confirm_step pattern)."""
    if step < 2 or step > 8:
        raise HTTPException(400, "Invalid step (2-8).")
    sess = _pt_get(key)
    step_key = f"step{step}"
    content = getattr(sess, step_key) or {}
    # Steps must have content before they can be confirmed
    required_field = {2: "sequence", 3: "matches", 4: "decision",
                      5: "fragments", 6: "files", 7: "runs", 8: "validated"}[step]
    if not content.get(required_field):
        raise HTTPException(409, f"Nothing to confirm yet for step {step} "
                                 f"(missing {required_field}).")
    _confirm(sess, step_key)
    _invalidate_from(sess, step)
    _pt_persist(sess)
    return {"session": sess.dict() if hasattr(sess, "dict") else sess.model_dump()}


# ---------------------------------------------------------------------------
# Step 2 — prescriptive sequence
# ---------------------------------------------------------------------------

@router.post("/extract_sequence/{key}")
async def extract_sequence(key: str, request: Request):
    data = _data(request)
    sess = _pt_get(key)
    fields = _case_payload_fields(sess)
    if not fields["steps"]:
        raise HTTPException(409, "Refined case has no test steps to work from.")
    meta = await run_in_threadpool(run_prompt, "pt_extract_sequence.jinja", {
        "case_key": key,
        "case_title": _case_title(data, key),
        "objective": fields["objective"],
        "steps": fields["steps"],
        "traceability": (sess.traceability or "")[:3000],
    }, llm_config=_llm_cfg(sess))
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    parsed = extract_json_block(meta.get("content", ""))
    sequence = _parsed_list(parsed, "sequence")
    if not sequence:
        raise HTTPException(502, "LLM returned no sequence. Raw response stored in provenance.")
    notes = _parsed_field(parsed, "notes", "")
    for i, s in enumerate(sequence):
        s["n"] = i + 1
    sess.step2 = {"sequence": sequence, "notes": notes,
                  "confirmed": False,
                  "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                                 "response": meta.get("content", "")[:20000]}}
    _invalidate_from(sess, 2)
    _pt_persist(sess)
    return {"sequence": sequence, "notes": notes}


@router.post("/save_sequence/{key}")
async def save_sequence(key: str, body: dict = Body(...)):
    """User edits to the sequence before confirming."""
    sess = _pt_get(key)
    sequence = body.get("sequence")
    if not isinstance(sequence, list) or not sequence:
        raise HTTPException(400, "Body must include a non-empty 'sequence' list.")
    for i, s in enumerate(sequence):
        s["n"] = i + 1
    sess.step2 = {**(sess.step2 or {}), "sequence": sequence, "confirmed": False}
    _invalidate_from(sess, 2)
    _pt_persist(sess)
    return {"sequence": sequence}


# ---------------------------------------------------------------------------
# Step 3 — script database search
# ---------------------------------------------------------------------------

@router.get("/search_scripts")
async def search_scripts(request: Request, q: str, db: str = "", limit: int = 25):
    """Mechanical index search (no LLM) — used for the free-text search box."""
    data = _data(request)
    toks = _pt_tokens(q)
    if not toks:
        return {"results": []}
    return {"results": _search_slim(data, toks, db=db, limit=min(limit, 100))}


@router.post("/suggest_scripts/{key}")
async def suggest_scripts(key: str, request: Request, body: dict = Body(default={})):
    """Two-stage match: mechanical top-40 -> LLM coverage verdicts."""
    data = _data(request)
    sess = _pt_get(key)
    _require_confirmed(sess, "step2", "Script search")
    sequence = (sess.step2 or {}).get("sequence") or []
    user_inputs = body.get("user_inputs", "") or (sess.step3 or {}).get("user_inputs", "")

    query_toks = set()
    for s in sequence:
        query_toks |= _pt_tokens(s.get("action", "")) | _pt_tokens(s.get("verify", ""))
    query_toks |= _pt_tokens(_case_title(data, key))
    query_toks |= _pt_tokens(user_inputs)

    mech = _search_slim(data, query_toks, limit=40)
    candidates = []
    for c in mech:
        rec = (data.get("scripts_index_by_id") or {}).get(c["id"]) or {}
        candidates.append({**c, "case_descs": [tc["desc"] for tc in rec.get("test_cases", [])
                                               if tc.get("desc")][:12]})

    llm_matches = []
    if candidates:
        meta = await run_in_threadpool(run_prompt, "pt_match_scripts.jinja", {
            "case_key": key, "sequence": sequence,
            "user_inputs": user_inputs, "candidates": candidates,
        }, llm_config=_llm_cfg(sess), timeout=300)
        if not meta.get("error"):
            parsed = extract_json_block(meta.get("content", ""))
            valid_ids = {c["id"] for c in candidates}
            llm_matches = [m for m in _parsed_list(parsed, "matches")
                           if isinstance(m, dict) and m.get("id") in valid_ids
                           and m.get("coverage") in ("full", "partial")]

    mech_by_id = {c["id"]: c for c in mech}
    matches = [{**mech_by_id.get(m["id"], {"id": m["id"]}), **m} for m in llm_matches]
    if not matches:  # LLM unavailable/empty -> mechanical fallback, marked as such
        matches = [{**c, "coverage": "unknown", "covers_steps": []} for c in mech]

    sess.step3 = {**(sess.step3 or {}),
                  "matches": matches, "user_inputs": user_inputs,
                  "mechanical_considered": len(mech), "confirmed": False}
    _invalidate_from(sess, 3)
    _pt_persist(sess)
    return {"matches": matches, "mechanical_considered": len(mech)}


@router.post("/save_matches/{key}")
async def save_matches(key: str, body: dict = Body(...)):
    """Store the reviewer's selected script ids + free-text inputs."""
    sess = _pt_get(key)
    sels = body.get("selections")
    if not isinstance(sels, list):
        raise HTTPException(400, "Body must include 'selections' (list of script ids).")
    sess.step3 = {**(sess.step3 or {}), "selections": sels,
                  "user_inputs": body.get("user_inputs", (sess.step3 or {}).get("user_inputs", "")),
                  "confirmed": False}
    _invalidate_from(sess, 3)
    _pt_persist(sess)
    return {"selections": sels}


@router.get("/script_source")
async def script_source(request: Request, id: str,
                        start: Optional[int] = None, end: Optional[int] = None):
    """Source (slice) of an indexed script — id validated against the index."""
    data = _data(request)
    rec = _script_record(data, id)
    return {"id": id, "path": rec["path"], "start": start, "end": end,
            "source": _read_source(rec, start, end)}


# ---------------------------------------------------------------------------
# Step 4 — fit decision
# ---------------------------------------------------------------------------

@router.post("/assess_fit/{key}")
async def assess_fit(key: str, request: Request):
    data = _data(request)
    sess = _pt_get(key)
    _require_confirmed(sess, "step3", "Fit assessment")
    sequence = (sess.step2 or {}).get("sequence") or []
    selections = (sess.step3 or {}).get("selections") or \
        [m["id"] for m in (sess.step3 or {}).get("matches", [])[:3]]
    if not selections:
        raise HTTPException(409, "No scripts selected in step 3.")

    scripts_ctx = []
    match_by_id = {m["id"]: m for m in (sess.step3 or {}).get("matches", [])}
    for sid in selections[:4]:
        rec = _script_record(data, sid)
        ts = rec.get("testset") or {}
        ts_loc = ts.get("loc") or [1, 60]
        testset_src = _read_source(rec, ts_loc[0], min(ts_loc[1] or ts_loc[0] + 60, ts_loc[0] + 90))
        cases = rec.get("test_cases") or []
        case_src = ""
        if cases:
            c0 = cases[0]
            loc = c0.get("loc") or [1, 40]
            case_src = _read_source(rec, loc[0], min(loc[1] or loc[0] + 40, loc[0] + 80))
        scripts_ctx.append({
            "id": sid,
            "coverage": (match_by_id.get(sid) or {}).get("coverage", "unknown"),
            "testset_src": testset_src,
            "cases": [{"class": c["class"], "desc": c["desc"]} for c in cases[:15]],
            "case_src": case_src,
        })

    meta = await run_in_threadpool(run_prompt, "pt_assess_fit.jinja", {
        "case_key": key, "sequence": sequence, "scripts": scripts_ctx,
    }, llm_config=_llm_cfg(sess), timeout=300)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    parsed = extract_json_block(meta.get("content", ""))
    if not isinstance(parsed, dict) or parsed.get("decision") not in ("reuse", "extend", "new"):
        raise HTTPException(502, "LLM fit decision unparseable.")
    sess.step4 = {"decision": parsed["decision"],
                  "base_script": parsed.get("base_script"),
                  "rationale": parsed.get("rationale", ""),
                  "per_step": parsed.get("per_step", []),
                  "confirmed": False,
                  "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model")}}}
    _invalidate_from(sess, 4)
    _pt_persist(sess)
    return {k: sess.step4[k] for k in ("decision", "base_script", "rationale", "per_step")}


@router.post("/save_fit/{key}")
async def save_fit(key: str, body: dict = Body(...)):
    sess = _pt_get(key)
    if body.get("decision") not in ("reuse", "extend", "new"):
        raise HTTPException(400, "decision must be reuse|extend|new")
    sess.step4 = {**(sess.step4 or {}),
                  "decision": body["decision"],
                  "base_script": body.get("base_script"),
                  "rationale": body.get("rationale", (sess.step4 or {}).get("rationale", "")),
                  "per_step": body.get("per_step", (sess.step4 or {}).get("per_step", [])),
                  "confirmed": False}
    _invalidate_from(sess, 4)
    _pt_persist(sess)
    return {"decision": body["decision"]}


# ---------------------------------------------------------------------------
# Step 5 — fragments
# ---------------------------------------------------------------------------

@router.post("/gather_fragments/{key}")
async def gather_fragments(key: str, request: Request):
    data = _data(request)
    sess = _pt_get(key)
    _require_confirmed(sess, "step4", "Fragment gathering")
    sequence = (sess.step2 or {}).get("sequence") or []
    step4 = sess.step4 or {}
    selections = (sess.step3 or {}).get("selections") or []
    if step4.get("base_script") and step4["base_script"] not in selections:
        selections = [step4["base_script"]] + selections

    scripts_ctx = []
    for sid in selections[:5]:
        rec = _script_record(data, sid)
        symbols = []
        ts = rec.get("testset")
        if ts:
            symbols.append({"kind": "class", "name": "TestSet",
                            "desc": f"topology init ({', '.join(ts.get('init_devices', []))}), "
                                    f"configure={ts.get('has_configure')}"})
        for c in rec.get("test_cases", []):
            symbols.append({"kind": "class", "name": c["class"], "desc": c["desc"] or c["method"][:120]})
        for h in rec.get("helpers", []):
            symbols.append({"kind": "function", "name": h["name"], "desc": h.get("doc", "")})
        scripts_ctx.append({"id": sid, "symbols": symbols})

    meta = await run_in_threadpool(run_prompt, "pt_gather_fragments.jinja", {
        "case_key": key, "sequence": sequence,
        "decision": step4.get("decision"), "base_script": step4.get("base_script"),
        "per_step": step4.get("per_step", []), "scripts": scripts_ctx,
    }, llm_config=_llm_cfg(sess), timeout=300)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    parsed = extract_json_block(meta.get("content", ""))

    fragments, dropped = [], []
    for f in _parsed_list(parsed, "fragments"):
        if not isinstance(f, dict):
            continue
        rec = (data.get("scripts_index_by_id") or {}).get(f.get("source_id"))
        if not rec:
            dropped.append(f)
            continue
        loc, code = None, ""
        if f.get("symbol") == "TestSet" and rec.get("testset"):
            loc = rec["testset"].get("loc")
        else:
            for c in rec.get("test_cases", []):
                if c["class"] == f.get("symbol"):
                    loc = c.get("loc")
                    break
        if loc and loc[0]:
            code = _read_source(rec, loc[0], loc[1] or loc[0] + 60)
        elif any(h["name"] == f.get("symbol") for h in rec.get("helpers", [])):
            # helper functions: locate by regex (helpers carry no loc in the index)
            src = _read_source(rec)
            m = re.search(rf"^def {re.escape(f['symbol'])}\b.*?(?=^def |^class |\Z)",
                          src, re.DOTALL | re.MULTILINE)
            code = m.group(0) if m else ""
        if not code:
            dropped.append(f)
            continue
        fragments.append({"source_id": f["source_id"], "symbol": f["symbol"],
                          "loc": loc, "code": code[:8000],
                          "maps_to": f.get("maps_to", []), "why": f.get("why", "")})

    sess.step5 = {"fragments": fragments, "dropped": dropped, "confirmed": False}
    _invalidate_from(sess, 5)
    _pt_persist(sess)
    return {"fragments": fragments, "dropped": len(dropped)}


@router.post("/save_fragments/{key}")
async def save_fragments(key: str, body: dict = Body(...)):
    """Reviewer keeps/removes fragments (list of {source_id, symbol} to keep)."""
    sess = _pt_get(key)
    keep = {(k.get("source_id"), k.get("symbol")) for k in body.get("keep", [])}
    frags = [f for f in (sess.step5 or {}).get("fragments", [])
             if (f["source_id"], f["symbol"]) in keep] if keep else \
        (sess.step5 or {}).get("fragments", [])
    sess.step5 = {**(sess.step5 or {}), "fragments": frags, "confirmed": False}
    _invalidate_from(sess, 5)
    _pt_persist(sess)
    return {"fragments": frags}


# ---------------------------------------------------------------------------
# Step 6 — generate + naming + lint
# ---------------------------------------------------------------------------

@router.post("/generate_script/{key}")
async def generate_script(key: str, request: Request, body: dict = Body(default={})):
    data = _data(request)
    sess = _pt_get(key)
    _require_confirmed(sess, "step2", "Generation")
    # steps 3-5 may legitimately be 'new script, no fragments'; require them
    # confirmed so the human explicitly reviewed the (possibly empty) reuse.
    _require_confirmed(sess, "step5", "Generation")

    naming = (sess.step6 or {}).get("naming") or {}
    group = body.get("group") or naming.get("group") or _group_display(sess.group)
    name = body.get("name") or naming.get("name") or _propose_name(_case_title(data, key))
    group, name = _validate_naming(group, name)
    file_name = f"{name}.py"

    fragments = (sess.step5 or {}).get("fragments", [])
    extra_mods = []
    for f in fragments:
        rec = (data.get("scripts_index_by_id") or {}).get(f["source_id"]) or {}
        extra_mods += [m.replace("framework.", "").replace("ATPyLib.", "")
                       for m in rec.get("imports", []) if m.startswith(("framework.", "ATPyLib."))]

    exemplar_rec = (data.get("scripts_index_by_id") or {}).get(EXEMPLAR_ID)
    exemplar = _read_source(exemplar_rec) if exemplar_rec else ""

    meta = await run_in_threadpool(run_prompt, "pt_generate_script.jinja", {
        "case_key": key,
        "case_title": _case_title(data, key),
        "file_name": file_name,
        "sequence": (sess.step2 or {}).get("sequence", []),
        "fragments": fragments,
        "exemplar": exemplar[:12000],
        "framework_surface": _framework_surface_slice(data, extra_mods),
    }, llm_config=_llm_cfg(sess), timeout=600)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    blocks = _parse_generated_blocks(meta.get("content", ""))
    if not blocks["test_code"]:
        raise HTTPException(502, "LLM returned no python code block.")

    prev = sess.step6 or {}
    sess.step6 = {
        "naming": {"group": group, "name": name},
        "files": {"test": {"name": file_name, "code": blocks["test_code"]},
                  "library": blocks["library"]},
        "iterations": prev.get("iterations", 0) + 1,
        "confirmed": False,
        "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")}},
    }
    _invalidate_from(sess, 6)
    lint = _lint_generated(sess)
    _pt_persist(sess)
    return {"naming": sess.step6["naming"], "files": sess.step6["files"],
            "iterations": sess.step6["iterations"], "lint": lint}


@router.post("/save_script/{key}")
async def save_script(key: str, body: dict = Body(...)):
    """Persist user edits (code and/or naming) and write files to generated/."""
    sess = _pt_get(key)
    step6 = sess.step6 or {}
    if not (step6.get("files") or {}).get("test"):
        raise HTTPException(409, "Generate a script first.")
    if "group" in body or "name" in body:
        naming = step6.get("naming") or {}
        group, name = _validate_naming(body.get("group", naming.get("group", "")),
                                       body.get("name", naming.get("name", "")))
        step6["naming"] = {"group": group, "name": name}
        step6["files"]["test"]["name"] = f"{name}.py"
    if "code" in body and body["code"]:
        step6["files"]["test"]["code"] = body["code"]
    if "library_code" in body and step6["files"].get("library"):
        step6["files"]["library"]["code"] = body["library_code"]
    step6["confirmed"] = False
    sess.step6 = step6
    _invalidate_from(sess, 6)
    lint = _lint_generated(sess)
    written = _persist_generated_files(sess)
    _pt_persist(sess)
    return {"written": written, "lint": lint, "naming": step6["naming"]}


@router.post("/lint_script/{key}")
async def lint_script(key: str):
    sess = _pt_get(key)
    lint = _lint_generated(sess)
    _pt_persist(sess)
    return lint


# ---------------------------------------------------------------------------
# Step 7 — testbox profiles + execution
# ---------------------------------------------------------------------------

@router.get("/profiles")
async def get_profiles():
    profiles = load_profiles()
    return {"profiles": {name: redact_profile(p) for name, p in profiles.items()}}


@router.post("/profiles")
async def upsert_profile(body: dict = Body(...)):
    name = (body.get("name") or "").strip()
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_\-\. ]{0,40}$", name):
        raise HTTPException(400, "Invalid profile name.")
    profiles = load_profiles()
    try:
        prof = normalize_profile(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not body.get("password") and name in profiles:
        prof["password"] = profiles[name].get("password")  # keep stored password on edit
    profiles[name] = prof
    save_profiles(profiles)
    return {"saved": name, "profile": redact_profile(prof)}


@router.delete("/profiles/{name}")
async def delete_profile(name: str):
    profiles = load_profiles()
    if name not in profiles:
        raise HTTPException(404, "Profile not found.")
    del profiles[name]
    save_profiles(profiles)
    return {"deleted": name}


@router.post("/profiles/{name}/check")
async def profile_check(name: str):
    profiles = load_profiles()
    if name not in profiles:
        raise HTTPException(404, "Profile not found.")
    return check_profile(profiles[name])


@router.post("/run/{key}")
async def run_script(key: str, body: dict = Body(...)):
    sess = _pt_get(key)
    _require_confirmed(sess, "step6", "Execution")
    if run_manager.is_running(key):
        raise HTTPException(409, "A run is already active for this case.")

    profiles = load_profiles()
    profile_name = body.get("profile") or (sess.step7 or {}).get("profile")
    if not profile_name or profile_name not in profiles:
        raise HTTPException(400, "Unknown or missing testbox profile.")
    profile = profiles[profile_name]

    setup = body.get("setup") or ""
    if setup in (profile.get("setups") or {}):
        setup_remote = profile["setups"][setup]
    elif setup:
        setup_remote = setup  # explicit remote path
    elif profile.get("setups"):
        setup_remote = next(iter(profile["setups"].values()))
    else:
        raise HTTPException(400, "No .setup file: add one to the profile or pass 'setup'.")

    step6 = sess.step6 or {}
    files = {step6["files"]["test"]["name"]: step6["files"]["test"]["code"]}
    lib = (step6.get("files") or {}).get("library")
    if lib and lib.get("code"):
        files[lib["name"]] = lib["code"]

    naming = step6.get("naming") or {}
    run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    run = {"run_id": run_id, "case_key": key, "status": "queued",
           "profile": profile_name, "setup": setup_remote,
           "test_file": step6["files"]["test"]["name"],
           "started_at": datetime.utcnow().isoformat(),
           "finished_at": None, "log_file": None, "parsed": None,
           "exit_code": None, "error": None}

    step7 = sess.step7 or {}
    step7["profile"] = profile_name
    step7.setdefault("runs", []).append(run)
    step7["confirmed"] = False
    sess.step7 = step7
    _invalidate_from(sess, 7)
    _pt_persist(sess)

    local_run_dir = _meta_dir(naming.get("group", "Ungrouped"),
                              naming.get("name", "unnamed")) / "runs" / run_id

    def on_update(updated_run: dict):
        cur = pt_sessions.get(key) or _pt_load(key)
        if not cur:
            return
        runs = (cur.step7 or {}).get("runs") or []
        for i, r in enumerate(runs):
            if r.get("run_id") == updated_run["run_id"]:
                runs[i] = updated_run
                break
        cur.step7 = {**cur.step7, "runs": runs}
        pt_sessions[key] = cur
        _pt_persist(cur)

    try:
        run_manager.start(key, run, profile, files, setup_remote, local_run_dir, on_update)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"run_id": run_id, "status": "queued"}


@router.get("/run_status/{key}/{run_id}")
async def run_status(key: str, run_id: str, tail: int = 40):
    sess = _pt_get(key)
    runs = (sess.step7 or {}).get("runs") or []
    run = next((r for r in runs if r.get("run_id") == run_id), None)
    if not run:
        raise HTTPException(404, "Run not found.")
    log_tail = ""
    if run.get("log_file") and Path(run["log_file"]).exists():
        lines = Path(run["log_file"]).read_text(encoding="utf-8", errors="replace").splitlines()
        log_tail = "\n".join(lines[-tail:])
    return {"run": run, "log_tail": log_tail, "active": run_manager.is_running(key)}


# ---------------------------------------------------------------------------
# Fix loop + Step 8 validation
# ---------------------------------------------------------------------------

@router.post("/fix_script/{key}")
async def fix_script(key: str, request: Request):
    """LLM revision from the latest failed run (or lint errors); archives history."""
    _data(request)  # ensure server ready
    sess = _pt_get(key)
    step6 = sess.step6 or {}
    if not (step6.get("files") or {}).get("test"):
        raise HTTPException(409, "No script to fix.")
    runs = (sess.step7 or {}).get("runs") or []
    last = runs[-1] if runs else None
    parsed = (last or {}).get("parsed") or {}
    lint = step6.get("lint") or {}
    lint_errors = "\n".join(lint.get("errors", []))
    if not parsed.get("cases") and not lint_errors:
        raise HTTPException(409, "Nothing to fix: no failed run results or lint errors.")

    excerpts = []
    if last and last.get("log_file") and Path(last["log_file"]).exists():
        excerpts = failure_excerpts(
            Path(last["log_file"]).read_text(encoding="utf-8", errors="replace"), parsed)

    naming = step6.get("naming") or {}
    meta = await run_in_threadpool(run_prompt, "pt_fix_script.jinja", {
        "case_key": key,
        "file_name": step6["files"]["test"]["name"],
        "iteration": step6.get("iterations", 1),
        "code": step6["files"]["test"]["code"],
        "lint_errors": lint_errors,
        "results": parsed.get("cases", []),
        "log_excerpts": excerpts,
    }, llm_config=_llm_cfg(sess), timeout=600)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    blocks = _parse_generated_blocks(meta.get("content", ""))
    if not blocks["test_code"]:
        raise HTTPException(502, "LLM fix returned no python code block.")

    # Archive current iteration before replacing
    iteration = step6.get("iterations", 1)
    hist_dir = _meta_dir(naming.get("group", "Ungrouped"),
                         naming.get("name", "unnamed")) / "history" / f"iter-{iteration}"
    hist_dir.mkdir(parents=True, exist_ok=True)
    (hist_dir / step6["files"]["test"]["name"]).write_text(
        step6["files"]["test"]["code"], encoding="utf-8")

    step6["files"]["test"]["code"] = blocks["test_code"]
    if blocks["library"]:
        step6["files"]["library"] = blocks["library"]
    step6["iterations"] = iteration + 1
    step6["confirmed"] = False
    sess.step6 = step6
    _invalidate_from(sess, 6)  # revised code must be re-reviewed and re-run
    new_lint = _lint_generated(sess)
    _pt_persist(sess)
    return {"files": step6["files"], "iterations": step6["iterations"],
            "lint": new_lint, "previous_archived": str(hist_dir)}


@router.post("/validate/{key}")
async def validate(key: str):
    """Machine half of Final Validation; human confirms via confirm_step/{key}/8."""
    sess = _pt_get(key)
    runs = (sess.step7 or {}).get("runs") or []
    last = runs[-1] if runs else None
    checks = {"has_run": bool(last), "run_done": False, "cases_parsed": False,
              "all_pass": False, "no_failures": False, "exit_code_zero": False}
    if last:
        parsed = last.get("parsed") or {}
        cases = parsed.get("cases") or []
        checks["run_done"] = last.get("status") == "done"
        checks["cases_parsed"] = len(cases) > 0
        checks["all_pass"] = bool(cases) and all(c.get("result") == "PASS" for c in cases)
        checks["no_failures"] = parsed.get("numFailed", 1) == 0 and parsed.get("unparsed_fails", 1) == 0
        checks["exit_code_zero"] = last.get("exit_code") == 0
    validated = all(checks.values())
    sess.step8 = {**(sess.step8 or {}),
                  "validated": validated,
                  "validated_at": datetime.utcnow().isoformat() if validated else None,
                  "run_id": (last or {}).get("run_id"),
                  "checks": checks}
    if validated:
        # Stamp provenance with the validation result (no credentials)
        naming = (sess.step6 or {}).get("naming") or {}
        meta_dir = _meta_dir(naming.get("group", "Ungrouped"), naming.get("name", "unnamed"))
        prov_path = meta_dir / "provenance.json"
        if prov_path.exists():
            try:
                prov = json.load(open(prov_path, encoding="utf-8"))
                prov.update({"validated_at": sess.step8["validated_at"],
                             "validated_run_id": sess.step8["run_id"],
                             "validated_profile": (sess.step7 or {}).get("profile")})
                prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"Warning: provenance stamp failed: {e}")
    _pt_persist(sess)
    promotion = None
    if validated:
        naming = (sess.step6 or {}).get("naming") or {}
        promotion = (f"Validated. To promote: copy generated/{naming.get('group')}/"
                     f"{naming.get('name')}.py into the appropriate testsuites_art suite "
                     f"(rename to the suite's test-<suite>.<set>.py convention), then "
                     f"confirm step 8 to close out this case.")
    return {"validated": validated, "checks": checks, "promotion": promotion}

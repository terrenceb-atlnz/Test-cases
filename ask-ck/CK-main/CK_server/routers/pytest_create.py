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

from models import PtSession, LLMConfig, safe_session_dict
from paths import REFINED_DIR, PT_GENERATED_DIR
from llm import run_prompt, extract_json_block
import db as dbx   # aliased: several functions here have a `db` filter parameter
from pt_exec import (
    load_profiles, save_profiles, redact_profile, normalize_profile,
    check_profile, parse_framework_log, failure_excerpts, run_manager,
)
from routers.wizard import (
    _load_global_llm, _llm_is_active, _same_backend,
    _refined_complete_keys, _build_case_groups, _is_hidden_case,
)

router = APIRouter(tags=["pytest-creator"])

# In-memory cache over ck.db-persisted sessions, mirroring wizard.py.
# Sessions live in ck.db (db.save_session/load_session, kind='pt'); the
# sessions/pt-*.json files on disk are frozen pre-migration backups, not read at
# runtime — there is no sessions/ path helper.
pt_sessions: Dict[str, PtSession] = {}

META_ROOT = PT_GENERATED_DIR / ".meta"

# Style anchor embedded in generation prompts: short, complete, has tear_down.
EXEMPLAR_ID = "art/6011_simul_fail/test-6011.1000.py"

STEP_KEYS = ["step2", "step3", "step4", "step5", "step6", "step7", "step8"]

# ---------------------------------------------------------------------------
# Py2 → Py3 fragment translation (D3, 2026-07-27)
# ---------------------------------------------------------------------------
# A reused fragment can come from a Python-2 / pre-`framework` legacy script (60
# scripts / 342 symbols in the corpus expose such fragments). If its code reaches
# the Generate prompt untouched, the model — steered by the prompt's "keep their
# proven CLI/parsing" rule — tends to PRESERVE the Py2 idioms. Lint only
# py_compile()s the RESULT (after a full re-generate) and cannot catch runtime-only
# tells (.iteritems()/.has_key()/basestring are valid Py3 syntax that fails at
# runtime on the testbox). So we translate the fragment code DETERMINISTICALLY, at
# resolve time, BEFORE it ever reaches Generate.
#
# stdlib `lib2to3` (not hand-rolled regex) because it is a real Py2 parser: it
# translates what it can and fails LOUDLY (ParseError) on what it can't, instead of
# silently mistranslating. On a ParseError we ship the ORIGINAL fragment + a
# soft-warn (banner in the preview, a modernize-when-adapting line in the prompt),
# never a broken half-translation.

# Py2 / old-idiom tells. Detection is cheap and only gates whether we ATTEMPT a
# translation — the authority on whether code is really Py2 is lib2to3's parser.
_PY2_TELLS = re.compile(
    r"(^[ \t]*print[ \t]+[^(=]"          # print statement (not print(), not print =)
    r"|^[ \t]*print[ \t]*$"              # bare `print`
    r"|except[ \t]+[\w.]+[ \t]*,[ \t]*\w+[ \t]*:"   # except X, e:
    r"|\.iteritems\(|\.iterkeys\(|\.itervalues\("
    r"|\.has_key\("
    r"|\bxrange\("
    r"|\bbasestring\b"
    r"|^[ \t]*raise[ \t]+\w+[ \t]*,)",   # raise X, msg
    re.MULTILINE,
)


def _has_py2_tells(code: str) -> bool:
    return bool(code) and bool(_PY2_TELLS.search(code))


def _translate_py2(code: str, name: str = "fragment") -> Tuple[str, str]:
    """Deterministically modernize a Py2 code fragment to Py3 via lib2to3.

    Returns (new_code, status) where status is one of:
      - "translated"  : lib2to3 parsed it and produced (possibly changed) Py3.
      - "clean"       : no Py2 tells to begin with (caller usually skips this path).
      - "parse_error" : lib2to3 could not parse it — ORIGINAL code returned unchanged
                        (caller must soft-warn, never ship a broken translation).
      - "unavailable" : lib2to3 import failed (very old/stripped runtime) — original
                        returned; caller soft-warns.

    Never raises: any failure degrades to returning the original code + a status the
    caller can act on. lib2to3 wants a trailing newline and a name for error messages.
    """
    if not _has_py2_tells(code):
        return code, "clean"
    try:
        from lib2to3 import refactor
    except Exception:
        return code, "unavailable"
    try:
        # Normalize indentation FIRST. Py2 legacy source frequently mixes tabs and
        # spaces (Py2 tolerated it; Py3's tokenizer rejects it as "inconsistent use of
        # tabs and spaces"). lib2to3 fixes SYNTAX but preserves the original mixed
        # indentation, so without this the translated code still fails ast.parse /
        # py_compile. expandtabs(8) applies Python's own tab-stop rule (found by the
        # adversarial test: 9/85 translations were invalid Py3 for exactly this reason).
        norm = "\n".join(ln.expandtabs(8) for ln in code.split("\n"))
        fixers = refactor.get_fixers_from_package("lib2to3.fixes")
        tool = refactor.RefactoringTool(fixers)
        out = str(tool.refactor_string(norm + "\n", name))
        # refactor_string re-emits the (added) trailing newline; strip the one we added
        # back off so we don't accrete blank lines across re-gathers.
        if out.endswith("\n") and not code.endswith("\n"):
            out = out[:-1]
        # Self-verify: the whole POINT is a valid-Py3 fragment. If lib2to3 "succeeded"
        # but the result still doesn't parse as Py3 (partial-grammar edge cases), do NOT
        # claim "translated" — degrade to parse_error so the caller ships the original +
        # soft-warns, never a fragment that lies about being modernized.
        try:
            import ast as _ast
            _ast.parse(out)
        except SyntaxError:
            return code, "parse_error"
        return out, "translated"
    except Exception:
        # ParseError (the ~5% lib2to3 can't handle) or any refactor failure: keep the
        # original, let the caller soft-warn. Fail-loud-here == degrade-safely-there.
        return code, "parse_error"

# NOTE: generation no longer embeds a free-form exemplar script — it renders the
# standardized skeleton (templates/pt_script_template.py.jinja) via _render_skeleton
# and asks the LLM to fill its slots. See TEMPLATE-SPEC.md.

_GROUP_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _()\-]{0,59}$")
_NAME_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,59}$")


# ---------------------------------------------------------------------------
# Session helpers (wizard.py pattern, pt- prefix; persisted in ck.db)
# ---------------------------------------------------------------------------

def _pt_persist(sess: PtSession) -> None:
    """Commit C: persist to ck.db (kind='pt'); llm_config split into its own
    column by db.save_session. The pt-{key}.json file stays as frozen backup."""
    sess.updated_at = datetime.utcnow()
    try:
        data = sess.dict() if hasattr(sess, "dict") else sess.model_dump()
        dbx.save_session("pt", sess.key, data)
    except Exception as e:
        print(f"Warning: failed to persist pt session {sess.key}: {e}")


def _pt_load(key: str) -> Optional[PtSession]:
    try:
        raw = dbx.load_session("pt", key)
        if raw is not None:
            return PtSession(**raw)
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
    """Re-sync this PyTest session's LLM config to the active workspace default.

    Mirrors wizard._apply_workspace_llm_if_needed (see its docstring for the full
    rationale): the active workspace default is the single source of truth, so we
    re-sync whenever the session has no active config OR its config diverges from
    the workspace default's backend — not only when it is inactive. This fixes the
    bug (§7.3) where a stale headless-CLI config (`_llm_is_active` reports it active
    unconditionally) could never re-sync and kept hitting the wrong backend."""
    global_cfg = _load_global_llm()
    if not global_cfg:
        return False
    cur = getattr(sess, "llm_config", None)
    if _llm_is_active(cur) and _same_backend(cur, global_cfg):
        return False
    raw = global_cfg.dict() if hasattr(global_cfg, "dict") else global_cfg.model_dump()
    sess.llm_config = LLMConfig(**raw)
    return True


def _llm_cfg(sess: PtSession) -> dict:
    # Apply the workspace LLM login at dispatch time if this session has no
    # active config of its own. Without this, an LLM endpoint would fall back to
    # run_prompt's default backend (claude_agent/model=default) instead of the
    # provider the user configured on the Configure page — silently sending the
    # prompt to the wrong LLM. load_case applies it once, but a stale/inactive
    # persisted config (or a session touched before the workspace login) would
    # otherwise slip through. Centralized here so no endpoint can forget it,
    # mirroring the wizard's per-call _apply_workspace_llm_if_needed.
    if _apply_workspace_llm(sess):
        _pt_persist(sess)
    cfg = sess.llm_config
    return cfg.dict() if hasattr(cfg, "dict") else cfg.model_dump()


async def _dry_run(request: Request) -> bool:
    """Read the optional dry_run flag from the request body (provenance preview).

    dry_run means: render the exact prompt this endpoint would send, and return
    it WITHOUT calling the LLM (no tokens). The Refresh button on a provenance
    block reuses the endpoint's own handler with this flag set, so the previewed
    prompt is 1-for-1 with what a real send transmits.
    """
    try:
        body = await request.json()
        return bool(body.get("dry_run"))
    except Exception:
        return False


def _provenance_preview(meta: dict) -> dict:
    """Shape a dry_run meta into the standard provenance-preview response."""
    return {"provenance": {
        "prompt": meta.get("prompt", ""),
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "auth_method": meta.get("auth_method"),
        "dry_run": True,
    }}


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


# The internal `stepN` keys and the numbers the UI shows DIVERGED when the old step 4
# (Fit Decision) was folded away: internal step5 is "4. Fragments" on screen and internal
# step6 is "5. Generate". Error messages must speak the UI's language — quoting the raw
# key told a user blocked on Fragments that "step5 must be confirmed", and step5 is the
# label the UI puts on Generate, i.e. the very thing they were trying to run.
_STEP_UI_LABEL = {
    "step2": "2. Sequence",
    "step3": "3. Script Search",
    # internal step4 (Fit Decision) has no panel of its own any more — it is folded into
    # Fragments. It stays reachable via confirm_step/{key}/4, so give it a name that
    # matches where a user would actually look for it rather than a bare number.
    "step4": "4. Fragments (fit decision)",
    "step5": "4. Fragments",
    "step6": "5. Generate",
    "step7": "6. Run",
    "step8": "7. Validate",
}


def _step_label(step: object) -> str:
    """UI-facing name for an internal step key or number ('step5' / 5 -> '4. Fragments').

    Falls back to the raw value so an unmapped step degrades to today's behaviour
    instead of raising inside an error path.
    """
    key = step if isinstance(step, str) and step.startswith("step") else f"step{step}"
    return _STEP_UI_LABEL.get(key, str(step))


_LIVE_RUN_STATUSES = ("queued", "connecting", "uploading", "running")


def _sweep_stale_runs(sess: PtSession) -> bool:
    """Re-mark runs orphaned by a server restart as 'stale'. Returns True if changed.

    A run row persists its last status, but the process that owned it does not survive
    a restart. This sweep used to live only inside load_case, so the polling endpoint
    (run_status) kept reporting the persisted 'running' forever — the UI spinner never
    resolved for anyone who did not reload the case first. Shared so every reader of
    step7.runs sees the same truth.
    """
    runs = (sess.step7 or {}).get("runs") or []
    if not runs:
        return False
    changed = False
    for r in runs:
        if r.get("status") in _LIVE_RUN_STATUSES and not run_manager.is_running(sess.key):
            r["status"] = "stale"
            changed = True
    if changed:
        sess.step7 = {**sess.step7, "runs": runs}
    return changed


def _collapse_step_text(step: dict) -> dict:
    """Collapse whitespace in a sequence step's action/verify text (in place).

    The skeleton renderer now emits these via `| pyliteral`, so a newline or backslash
    can no longer break the generated Python. This is the belt-and-braces half: step text is
    single-line prose by nature, and a stray newline from the Sequence <textarea> (or an
    LLM extraction) still renders as an awkward multi-line comment and inflates the
    generate prompt. Normalizing at the WRITE path keeps every downstream consumer —
    skeleton, prompt, traceability — working from clean single-line text.
    """
    for field in ("action", "verify"):
        val = step.get(field)
        if isinstance(val, str):
            step[field] = " ".join(val.split())
    return step


def _require_confirmed(sess: PtSession, step_key: str, what: str) -> None:
    if not (getattr(sess, step_key) or {}).get("confirmed"):
        raise HTTPException(
            409, f"{what} requires '{_step_label(step_key)}' to be confirmed first.")


def _selected_script_ids(sess: PtSession) -> List[str]:
    """Flattened, de-duped set of script ids chosen across all sequence steps in
    step 3. Selections are stored per-step as {stepN: [id,...]}; the legacy flat-list
    shape (pre per-step-picker sessions) is still accepted so old sessions don't break.
    Preserves first-seen order for stable downstream context."""
    sels = (sess.step3 or {}).get("selections")
    out, seen = [], set()
    if isinstance(sels, dict):
        for ids in sels.values():
            for sid in (ids or []):
                if isinstance(sid, str) and sid and sid not in seen:
                    seen.add(sid)
                    out.append(sid)
    elif isinstance(sels, list):  # legacy flat list
        for sid in sels:
            if isinstance(sid, str) and sid and sid not in seen:
                seen.add(sid)
                out.append(sid)
    return out


def _frag_key(f: dict) -> tuple:
    """Stable identity of a fragment: (source_id, symbol)."""
    return (f.get("source_id"), f.get("symbol"))


def _selections_fingerprint(sess: PtSession) -> str:
    """Order-independent fingerprint of the step-3 script selections. Fragments are
    stamped with this at gather time; when it no longer matches the current selections,
    the fragments are stale (Step 3 changed) and the UI prompts a re-gather."""
    ids = sorted(set(_selected_script_ids(sess)))
    return "|".join(ids)


def _unit_starts(rec: dict) -> List[int]:
    """Sorted 1-based start lines of every indexed unit (testset + test_cases +
    helpers) in a script record. Used to derive a symbol's END when the index only
    carries its start (loc[1] is null) — the next unit's start bounds it."""
    starts: List[int] = []
    ts = rec.get("testset") or {}
    if isinstance(ts, dict) and (ts.get("loc") or [None])[0]:
        starts.append(ts["loc"][0])
    for c in rec.get("test_cases") or []:
        loc = c.get("loc")
        if loc and loc[0]:
            starts.append(loc[0])
    for h in rec.get("helpers") or []:
        loc = h.get("loc")
        if loc and loc[0]:
            starts.append(loc[0])
    return sorted(set(starts))


def _resolve_end(rec: dict, start: int, declared_end: Optional[int]) -> int:
    """The authoritative END line for a unit starting at `start` (D1, 2026-07-27).

    Fallback chain (all derivable from the index alone; no ck.db rebuild):
      1. declared_end (loc[1]) when the index carries it   — ART/SVT common path.
      2. next unit's start - 1                              — 573/650 legacy null-end.
      3. loc_total (last unit in file)                      —  77/650 legacy null-end.
      4. clamped bound (start + 60)                         — defensive; 0 in corpus.

    Replaces the old blind `loc[0] + 60`, which over/under-captured 650 legacy
    test_case symbols (~18% of all test_case entries) and drove prompt bloat +
    context skew. Every branch here is exact structural data, not a guess.
    """
    if declared_end and declared_end >= start:
        return declared_end
    nxt = next((s for s in _unit_starts(rec) if s > start), None)
    if nxt:
        return nxt - 1
    loc_total = rec.get("loc_total")
    if isinstance(loc_total, int) and loc_total >= start:
        return loc_total
    return start + 60  # defensive only — unreachable on the current corpus


def _resolve_symbol_code(data: dict, source_id: str, symbol: str,
                         translate_py2: bool = True) -> Tuple[Optional[list], str, str]:
    """Resolve one LLM-named symbol (TestSet / TestCase class / helper fn) to its real
    source slice from ck.db.

    Returns (loc, code, py2_status):
      - loc        : [start, end] with the END resolved via `_resolve_end` (D1), so a
                     null index end is bounded exactly, not by a blind +60.
      - code       : '' if unresolvable (invented symbol / missing script) so the
                     caller can drop it; otherwise the real source, Py2→Py3-modernized
                     when `translate_py2` and the fragment carried Py2 idioms (D3).
      - py2_status : 'clean' | 'translated' | 'parse_error' | 'unavailable' — lets the
                     caller annotate provenance (`(py2→py3)`) or soft-warn on an
                     untranslatable Py2 fragment. Always 'clean' when code is ''.
    """
    rec = (data.get("scripts_index_by_id") or {}).get(source_id)
    if not rec:
        return None, "", "clean"
    loc: Optional[list] = None
    if symbol == "TestSet" and rec.get("testset"):
        loc = (rec["testset"] or {}).get("loc")
    else:
        for c in rec.get("test_cases", []):
            if c["class"] == symbol:
                loc = c.get("loc")
                break
        else:
            for h in rec.get("helpers", []):
                if h["name"] == symbol:
                    loc = h.get("loc")
                    break

    if not (loc and loc[0]):
        return loc, "", "clean"

    start = loc[0]
    end = _resolve_end(rec, start, loc[1] if len(loc) > 1 else None)
    loc = [start, end]
    code = _read_source(rec, start, end)

    py2_status = "clean"
    if translate_py2 and code:
        code, py2_status = _translate_py2(code, f"{source_id}::{symbol}")
    return loc, code, py2_status


def _selected_fragments(sess: PtSession) -> List[dict]:
    """The fragments the reviewer has SELECTED for generation. step5.fragments is the
    full gathered pool (retained so the UI can show a selected/not-selected split);
    step5.selected is the list of chosen {source_id, symbol} keys. Downstream Generate
    reads ONLY the selected subset. Back-compat: a session with no `selected` key (or
    an empty gather that legitimately has none) falls back to treating the whole pool
    as selected, matching the old delete-on-save behavior."""
    step5 = sess.step5 or {}
    pool = step5.get("fragments") or []
    if "selected" not in step5:
        return list(pool)
    sel = step5.get("selected") or []
    sel_keys = {tuple(s) if isinstance(s, (list, tuple))
                else (s.get("source_id"), s.get("symbol")) for s in sel}
    return [f for f in pool if _frag_key(f) in sel_keys]


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
    """Read a validated index record's source (optionally a 1-based line slice).

    Source comes from ck.db — the single runtime source of truth — never from the
    filesystem. The record's own `source_text` (loaded by db.get_script) is used
    when present; otherwise it is fetched by id via db.get_script_source. The old
    script mount (testsuites_art/ etc.) is gone and must never be referenced.
    """
    src = rec.get("source_text")
    if src is None:
        src = dbx.get_script_source(rec.get("id", ""))
    if src is None:
        raise HTTPException(404, f"No source in ck.db for {rec.get('id')}")
    lines = src.splitlines()
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


# A scaffolding-marker comment line: a pure comment (only whitespace before the
# '#') carrying one of the template's slot markers. The markers span one or two
# comment lines (opener + an indented continuation ending in '<<<'); both forms
# are pure comments, so dropping every comment line that mentions a marker OR
# closes one removes the guidance without touching filled-in code (real code is
# never a pure comment). See templates/pt_script_template.py.jinja for shapes.
_FILL_MARKER_RX = re.compile(r">>>\s*(FILL|replace|remove)\b", re.IGNORECASE)


def _strip_fill_markers(code: str) -> str:
    """Remove leftover '# >>> FILL/replace/remove ... <<<' scaffolding comments.

    The model is told to delete these after filling a slot, but compliance is
    non-deterministic; stripping them server-side guarantees no marker ever
    survives into a saved/linted/run script regardless of the model. Only PURE
    comment lines are removed — a line with real code before the '#' is kept.
    Continuation lines of a two-line marker (indented comment ending in '<<<')
    are removed while the marker is 'open'."""
    out, in_marker = [], False
    for line in code.splitlines():
        stripped = line.lstrip()
        is_comment = stripped.startswith("#")
        if is_comment and _FILL_MARKER_RX.search(line):
            in_marker = "<<<" not in line  # single-line marker closes immediately
            continue
        if in_marker and is_comment:
            # continuation comment line of an open two-line marker
            if "<<<" in line:
                in_marker = False
            continue
        in_marker = False
        out.append(line)
    result = "\n".join(out)
    return result if result.endswith("\n") else result + "\n"


def _parse_generated_blocks(content: str) -> Dict[str, Any]:
    """Extract test + optional 'LIBRARY: <name>' python blocks from LLM output."""
    blocks = re.findall(r"(?:^|\n)(LIBRARY:\s*(\S+)\s*\n)?```(?:python)?\s*\n(.*?)```",
                        content, re.DOTALL)
    test_code, library = None, None
    for _, lib_name, code in blocks:
        code = _strip_fill_markers(code.strip() + "\n")
        if lib_name:
            library = {"name": lib_name.strip(), "code": code}
        elif test_code is None:
            test_code = code
    return {"test_code": test_code, "library": library}


# PLAN §1.5 — inline source-provenance tags. `db` on the scripts table is one of
# art/svt/legacy and maps 1:1 to the tag family; `id` is "<db>/<suite_dir>/<file>".
_PROVENANCE_TAG_FAMILY = {"art": "ART", "svt": "SVT", "legacy": "legacy"}
_PROVENANCE_TAG_RX = re.compile(r"^\s*#\s*(ART|SVT|legacy|AI)\s+\S")
# Model-echoed provenance attempts are not always a bare tag on the first line —
# a reasoning model can restate the prompt's own instruction text first
# ("# Provenance tag for this fragment: # AI ...") on a LATER leading comment line.
# Both shapes are scaffolding to strip; only the server's own re-stamp is authoritative.
#
# This used to be `^\s*#.*\b(ART|SVT|legacy|AI)\b` — any leading comment MENTIONING a
# family word. Those words are ordinary domain vocabulary here, so a real rationale
# comment ("# SVT 3009 replug pattern: poll until the operator reseats the module",
# "# legacy CLI parsing retained: this firmware has no 'show pluggable detail'") was
# silently deleted from the saved and executed script. Now we match only the two shapes
# a provenance echo actually takes:
#   1. the bare tag itself           -> _PROVENANCE_TAG_RX  (# ART suite/file lines a-b)
#   2. the prompt's instruction text -> "provenance tag" / "provenance:" phrasing
_PROVENANCE_ECHO_PHRASE_RX = re.compile(r"^\s*#.*\bprovenance\b\s*(tag|:)", re.IGNORECASE)
# The tag SHAPE that _fragment_tag emits: `# <FAMILY> <path/file.py>[ lines a-b]`, or
# `# AI <model> <YYYY-MM-DD>`. Deliberately stricter than _PROVENANCE_TAG_RX (which is a
# loose lint check at :1164 and must keep its current meaning): it requires a
# file-like token or a lines/date suffix, so "# SVT 3009 replug pattern: poll until..."
# — prose that merely opens with a family word — is NOT treated as a tag.
_PROVENANCE_ECHO_TAG_RX = re.compile(
    r"^\s*#\s*(?:"
    r"(?:ART|SVT|legacy)\s+\S*\.py\b"          # # ART suite/file.py [lines a-b]
    r"|(?:ART|SVT|legacy|AI)\s+\S+\s+lines\s+\d+"   # ...explicit line range
    r"|AI\s+\S+\s+\d{4}-\d{2}-\d{2}\s*$"       # # AI <model> <date>
    r")",
    re.IGNORECASE,
)
# Cap the leading run we are willing to strip. A genuine echo is 1-2 lines; anything
# longer is the model's own documentation.
_PROVENANCE_ECHO_MAX_LINES = 2


def _is_provenance_echo(line: str) -> bool:
    """True for a model-emitted provenance tag/restatement, not for real commentary."""
    return bool(_PROVENANCE_ECHO_TAG_RX.match(line)
                or _PROVENANCE_ECHO_PHRASE_RX.match(line))


def _fragment_tag(source_id: str, loc: Optional[Tuple[int, int]],
                  py2_translated: bool = False) -> str:
    """Mechanical `# ART <suite/file> <lines a-b>`-style tag for a reused fragment.

    Derived entirely from indexed metadata (source_id + loc), never from LLM
    self-report, so it cannot be faked or drift (PLAN §1.5). When the fragment's
    code was mechanically modernized Py2→Py3 (D3), a `(py2→py3)` suffix marks it so a
    reviewer tracing the block back to its source lines knows it is NOT byte-identical
    to those lines — it was translated, not copied verbatim."""
    db_kind, _, rest = (source_id or "").partition("/")
    family = _PROVENANCE_TAG_FAMILY.get(db_kind, "legacy")
    lines = f" lines {loc[0]}-{loc[1]}" if loc and loc[0] and loc[1] else ""
    suffix = " (py2→py3)" if py2_translated else ""
    return f"# {family} {rest or source_id}{lines}{suffix}"


def _restamp_provenance(code: str, fragments: List[dict], model: str,
                        sequence: Optional[List[dict]] = None) -> str:
    """Authoritative post-generation provenance pass (PLAN §1.5).

    For each `TestCase_<n>` block, stamp the top of main() with the tag of
    whichever fragment's `maps_to` includes that step (mechanical — matched by the
    server-known step->fragment mapping, not by trusting anything the LLM
    wrote). A step with no mapped fragment is stamped `# AI <model> <date>`
    (gap-fill).

    CRITICAL MAPPING NOTE (finding #4): fragment `maps_to` uses ORIGINAL sequence
    numbers, but the `TestCase_<n>` class numbers are the CONTIGUOUS 1..N produced by
    `_split_sequence` after setup steps are dropped. When any setup step precedes a
    verify step, the two number spaces DIVERGE (orig step 3 becomes TestCase_2, etc.),
    so keying `maps_to` directly by the class number stamps the wrong fragment's tag.
    We therefore build the SAME orig_n -> new_n remap the preview uses and translate
    every fragment's `maps_to` into class-number space before stamping. When `sequence`
    is None (legacy callers / no setup steps) we fall back to identity — correct exactly
    when the numbers already coincide.

    The model is asked to attempt its own tag (prompt rule 8) but compliance is
    non-deterministic in both content AND shape — observed live: it can restate
    the prompt's own instruction text as a leading comment instead of emitting a
    bare tag ("Provenance tag for this fragment: # AI ... ") one or more lines
    into main(), which a first-line-only check would miss and leave duplicated
    alongside the real stamp. So the ENTIRE leading run of comment lines that
    mention a tag family is stripped first, then exactly one authoritative tag
    is inserted — trustworthy regardless of what shape the model produced."""
    # Build orig_n -> class_n (TestCase number) remap — the same one the preview uses,
    # so a fragment mapped to original step 3 stamps TestCase_2 when a setup step was
    # dropped ahead of it, instead of mis-stamping whatever class happens to be #3.
    orig_to_classn: Dict[int, int] = {}
    if sequence:
        tc_orig = [s for s in sequence if _step_kind(s) != "setup"] or list(sequence)
        for new_i, s in enumerate(tc_orig, 1):
            try:
                orig_to_classn[int(s.get("n"))] = new_i
            except (TypeError, ValueError):
                continue

    # tag_by_step is keyed by CLASS number (TestCase_<n>), which is what we match below.
    tag_by_step: Dict[int, str] = {}
    for f in fragments:
        tag = _fragment_tag(f.get("source_id", ""), f.get("loc"),
                            f.get("py2_translated", False))
        for n in f.get("maps_to") or []:
            try:
                orig_n = int(n)
            except (TypeError, ValueError):
                continue
            # Translate original step number -> class number.
            if orig_to_classn:
                # A step missing from the remap is a SETUP step — it has no TestCase of
                # its own (it folds into the suite's configure()). Falling back to
                # identity here mapped it onto whichever class happens to share its
                # number and OVERWROTE that class's correct tag (last write wins), so
                # the authoritative provenance line pointed a reviewer at the wrong
                # source script. Skip it instead — matching what the preview path does.
                class_n = orig_to_classn.get(orig_n)
                if class_n is None:
                    continue
            else:
                # Legacy callers pass no sequence; the two number spaces coincide.
                class_n = orig_n
            tag_by_step[class_n] = tag
    gen_date = datetime.utcnow().strftime("%Y-%m-%d")
    ai_tag = f"# AI {model or 'unknown'} {gen_date}"

    lines = code.split("\n")
    out: List[str] = []
    current_class_n: Optional[int] = None
    in_main = False
    stamped_this_main = False
    stripped_echoes = 0
    class_rx = re.compile(r"^class TestCase_(\d+)\b")
    main_rx = re.compile(r"^\s+def main\(self\):\s*$")

    for line in lines:
        m = class_rx.match(line)
        if m:
            current_class_n = int(m.group(1))
            in_main = False
            stamped_this_main = False
            stripped_echoes = 0   # the cap is per-TestCase, not per-file
            out.append(line)
            continue
        if in_main and not stamped_this_main:
            if stripped_echoes < _PROVENANCE_ECHO_MAX_LINES and _is_provenance_echo(line):
                # Part of the model's leftover provenance attempt — drop the
                # whole line, keep scanning (there may be more before real code).
                stripped_echoes += 1
                continue
            indent = line[:len(line) - len(line.lstrip())] or "        "
            tag = tag_by_step.get(current_class_n, ai_tag)
            out.append(f"{indent}{tag}")
            out.append(line)
            stamped_this_main = True
            continue
        if main_rx.match(line):
            in_main = True
        out.append(line)
    return "\n".join(out)


from jinja2 import Environment as _J2Env, FileSystemLoader as _J2Loader

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_skeleton_env = _J2Env(loader=_J2Loader(str(_TEMPLATES_DIR)))


def _pyliteral(value) -> str:
    """Render a value as a correctly-escaped Python string literal.

    The skeleton's step-text slots used to be hand-quoted and sanitized with
    replace("'",""), so a newline or trailing backslash in reviewer-typed text produced
    an UNCOMPILABLE skeleton (shown as-is on the preview path, and fed to the model as
    the structure to copy on the generate path).

    `repr` rather than `| tojson`: both escape correctly, but tojson HTML-escapes the
    apostrophe (`port\\u0027s`), and these files exist to be read by a human reviewer.
    repr gives `"the port's state"` — same runtime value, legible diff.
    """
    return repr("" if value is None else str(value))


_skeleton_env.filters["pyliteral"] = _pyliteral


# The four step kinds (extract_sequence classifies every step; see the prompt).
#   setup    -> suite configure(), no pass/fail
#   verify   -> a TestCase driven over CLI/traffic (default)
#   physical -> a TestCase with the operator-prompt + wait-for-state-change pattern
#   manual   -> a TestCase with a yesNo() operator confirmation
_STEP_KINDS = ("setup", "verify", "physical", "manual")


def _step_kind(s: dict) -> str:
    """The single source of truth for a step's kind (fixes the previously-triplicated
    is_setup logic). Uses the extractor's explicit `kind` when present + valid; else
    falls back for legacy sequences (no kind): a step with no verify text is `setup`,
    otherwise `verify`."""
    k = (s.get("kind") or s.get("type") or "").strip().lower()
    if k in _STEP_KINDS:
        return k
    if k in ("precondition", "config"):
        return "setup"
    if k in ("test",):
        return "verify"
    # legacy / unclassified: verify-empty => setup, else verify
    return "setup" if not (s.get("verify") or "").strip() else "verify"


def _split_sequence(sequence: List[dict]) -> Tuple[List[dict], List[dict]]:
    """Split into (setup_steps -> TestSet.configure, testcase_steps -> TestCase).
    setup = kind 'setup'; everything else (verify/physical/manual) becomes a TestCase.
    NON-MUTATING: returns fresh dicts with contiguous `n` on the TestCase steps; never
    assigns onto the caller's objects (so preview and Generate can't drift via aliasing)."""
    setup_steps, tc_steps = [], []
    for s in sequence:
        (setup_steps if _step_kind(s) == "setup" else tc_steps).append(dict(s))
    for i, s in enumerate(tc_steps, 1):
        s["n"] = i          # on the COPY, not the caller's dict
    return setup_steps, tc_steps


_SWI_RX = re.compile(r"\b(swi_[a-z])\b")
_STK_RX = re.compile(r"\b(stk_[a-z])\b")
_PORTLINK_RX = re.compile(r"port\s?link|init_portlink|\.port[A-Z]\b|portlink")

# Device references in reused fragment code. ART scripts don't share ONE naming
# convention (corpus: dutA×2571, dut×2199, swiSrc, swiDst, dutB, lp, swi, …), so the
# skeleton must bind whatever names the SELECTED fragments actually use — otherwise the
# reused code says `self.dut.cmd(...)` while init() only bound `swi_a` → AttributeError.
# Two reference shapes cover it: `self.<name>.cmd/mode/...` and `x = self.testSet.<name>`.
_FRAG_DEV_METHOD_RX = re.compile(r"self\.(\w+)\.(?:cmd|mode|reboot|portReset|configurePort|link|portA|portB)\b")
_FRAG_DEV_TESTSET_RX = re.compile(r"self\.testSet\.(\w+)\b")
# Names that match the shapes but are NOT devices (framework internals / common locals).
_FRAG_DEV_DENY = frozenset({
    "setup", "testSet", "stream", "log", "logFile", "result", "results",
    "supported", "cycles", "plugIndex", "pluggableInfo", "platformName",
})


def _detect_fragment_devices(fragments: List[dict]) -> List[str]:
    """The device names the reused fragment code references (so init() can bind them).
    Filters framework internals + obvious non-devices; preserves first-seen order."""
    seen: List[str] = []
    have = set()
    for f in (fragments or []):
        code = f.get("code", "") or ""
        for rx in (_FRAG_DEV_METHOD_RX, _FRAG_DEV_TESTSET_RX):
            for name in rx.findall(code):
                if (name in _FRAG_DEV_DENY or name in have
                        or not name.isidentifier() or name.startswith("_")):
                    continue
                # crude device heuristic: switch/dut/lp/link vocabulary, or swi_*/stk_*
                low = name.lower()
                if not (any(t in low for t in ("dut", "swi", "remote", "link", "lp", "switch", "stk"))
                        or _SWI_RX.match(name) or _STK_RX.match(name)):
                    continue
                have.add(name)
                seen.append(name)
    return seen


def _detect_topology(sequence: List[dict], fragments: List[dict]) -> Tuple[List[str], List[str], bool]:
    """Data-driven topology: the switch device names to bind in init(), stacks, and
    whether a port link is needed. Prefers the device names the SELECTED fragments
    actually reference (so the reused code resolves against init()); falls back to any
    swi_*/stk_* seen in the sequence text, then to a sane default. Names must match the
    .setup [switch]/[stack] sections — that reconciliation is surfaced to the reviewer/LLM
    (see _fragment_device_note), since the real .setup is only chosen later at Run."""
    blob = " ".join((s.get("action", "") + " " + s.get("verify", "")) for s in sequence)
    blob += " " + " ".join(f.get("code", "") for f in fragments)
    frag_devs = _detect_fragment_devices(fragments)
    swi_literal = sorted(set(_SWI_RX.findall(blob)))
    # Fragment device names first (they're what the reused code calls), then any literal
    # swi_* from the text, else the default pair (most cases are DUT + link partner).
    switches = frag_devs or swi_literal or ["dut", "lp"]
    stacks = sorted(set(_STK_RX.findall(blob)))
    needs_portlink = bool(_PORTLINK_RX.search(blob))
    return switches, stacks, needs_portlink


def _fragment_device_note(fragments: List[dict], bound: List[str]) -> str:
    """Reconciliation note for the artefact + Generate prompt: the device names the
    reused fragments use and what init() binds, so the reviewer/LLM reconciles them
    against the eventual .setup file (which defines the real [switch] names)."""
    frag_devs = _detect_fragment_devices(fragments)
    if not frag_devs:
        return ""
    return ("Reused fragments reference these device names: "
            + ", ".join(frag_devs) + ". init() binds: " + ", ".join(bound)
            + ". These MUST match the [switch]/[stack] sections of the .setup file used "
              "at Run — rename to your .setup's device names where they differ.")


def _render_skeleton(case_key: str, case_title: str, sequence: List[dict],
                     extra_imports: List[str], fragments: Optional[List[dict]] = None) -> str:
    """Render the standardized ART skeleton (fixed frame + FILL slots) for this case.
    Each TestCase step carries a resolved `kind` (verify/physical/manual) so the template
    renders the right main() pattern (CLI check vs operator-prompt-and-wait vs yesNo)."""
    setup_steps, verify_steps = _split_sequence(sequence)
    if not verify_steps:  # never emit a zero-TestCase script
        verify_steps = [dict(s, n=i + 1) for i, s in enumerate(sequence)]
        setup_steps = []
    # Stamp the resolved kind on each rendered step (default 'verify' for TestCase steps).
    for s in verify_steps:
        rk = _step_kind(s)
        s["kind"] = rk if rk in ("physical", "manual") else "verify"
    switches, stacks, needs_portlink = _detect_topology(sequence, fragments or [])
    tpl = _skeleton_env.get_template("pt_script_template.py.jinja")
    return tpl.render(case_key=case_key, case_title=case_title,
                      extra_imports=extra_imports or [],
                      setup_steps=setup_steps, steps=verify_steps,
                      switches=switches, stacks=stacks, needs_portlink=needs_portlink)


def _assemble_fragment_preview(case_key: str, case_title: str, sequence: List[dict],
                               extra_imports: List[str], fragments: List[dict]) -> str:
    """The per-step ARTEFACT this Fragments step produces: the real Generate skeleton
    with each verification step's SELECTED fragment code inserted as a reference block
    inside its TestCase, and FILL markers left where the Generate LLM will gap-fill.

    This is a pre-LLM preview — it shows how the reused pieces sit in the template
    frame that Generate starts from (Generate then fills the FILL slots + adapts).
    Fragment `maps_to` uses ORIGINAL sequence numbers, so we compute verify-step order
    the same way _split_sequence does and map original-n -> TestCase_<new n>.
    """
    # _split_sequence is now non-mutating; the TestCase steps carry the original `n`
    # too (we read it before the split's copy renumbered). Build the original-n list
    # from the SAME classifier the split uses — one source of truth, no drift.
    tc_orig = [s for s in sequence if _step_kind(s) != "setup"]
    orig_ns = [s.get("n") for s in tc_orig] or [s.get("n") for s in sequence]

    skeleton = _render_skeleton(case_key, case_title, sequence, extra_imports, fragments)

    # Device-name reconciliation banner: the reused fragments reference device names
    # (dut/remote/linkP/dutA/…) that must be reconciled against init()'s bindings and the
    # eventual .setup file. Surface it at the top so the reviewer/LLM sees it (finding #1).
    bound, _stk, _pl = _detect_topology(sequence, fragments)
    dev_note = _fragment_device_note(fragments, bound)
    banner = []
    if dev_note:
        banner = ["# ==== DEVICE NAMES — reconcile before running ====",
                  *[f"#   {ln}" for ln in _wrap_comment(dev_note, 92)],
                  "# =================================================", ""]

    # Build per-TestCase reused-code blocks keyed by the new TestCase number, plus a
    # class-number -> kind map so we can mark GENUINE gaps (finding #7): a verify step
    # with no reused fragment must be signalled by PRESENCE ("NO REUSE — write from
    # scratch"), not by the silent absence of a block. Physical/manual steps generate
    # their own interactive pattern, so a missing fragment there is expected, not a gap.
    by_newn: Dict[int, List[dict]] = {}
    kind_by_newn: Dict[int, str] = {}
    for new_i, orig_n in enumerate(orig_ns, 1):
        src = next((s for s in tc_orig if s.get("n") == orig_n), None)
        kind_by_newn[new_i] = _step_kind(src) if src else "verify"
        for f in fragments:
            if orig_n in (f.get("maps_to") or []):
                by_newn.setdefault(new_i, []).append(f)

    out_lines = list(banner)
    class_rx = re.compile(r"^class TestCase_(\d+)\(")
    for line in skeleton.split("\n"):
        out_lines.append(line)
        m = class_rx.match(line)
        if m:
            new_n = int(m.group(1))
            frags_here = by_newn.get(new_n, [])
            for f in frags_here:
                tag = _fragment_tag(f.get("source_id", ""), f.get("loc"),
                                    f.get("py2_translated", False))
                out_lines.append(f"    # ===== reused fragment for this step: {tag} =====")
                # D3 soft-warn: a Py2 fragment lib2to3 could NOT translate ships as-is;
                # surface it so the reviewer/LLM knows to modernize rather than copy.
                if f.get("py2_flagged"):
                    out_lines.append("    # ===== ⚠ PYTHON 2 — could not auto-modernize; "
                                     "translate idioms (print/except/iteritems) when adapting =====")
                for cl in (f.get("code") or "").split("\n"):
                    out_lines.append(("    # " + cl) if cl else "    #")
                out_lines.append("    # ===== end reused fragment =====")
            if not frags_here and kind_by_newn.get(new_n) == "verify":
                # Positive gap marker (finding #7) — the LLM will write this step from
                # scratch; make that explicit so a reviewer sees the gap, not silence.
                out_lines.append("    # ===== NO REUSE — no fragment covers this step; "
                                 "Generate writes it from scratch =====")
    return "\n".join(out_lines)


def _wrap_comment(text: str, width: int) -> List[str]:
    """Word-wrap a note into lines <= width for comment banners."""
    import textwrap
    return textwrap.wrap(text, width) or [text]


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
            main_fn = next((n for n in c.body if isinstance(n, ast_mod.FunctionDef)
                            and n.name == "main"), None)
            inherits_local = any(isinstance(b, ast_mod.Name) and b.id not in ("object",)
                                 and "TestCase" not in b.id for b in c.bases)
            if main_fn is None and not inherits_local:
                warnings.append(f"{c.name} has no main() (ok only if a base class provides it)")
            # Template logging-contract conformance (TEMPLATE-SPEC.md C6, offline half):
            # each TestCase.main() must log and end in exactly one NON-EMPTY pass/fail.
            if main_fn is not None:
                m_src = ast_mod.get_source_segment(code, main_fn) or ""
                calls = [n for n in ast_mod.walk(main_fn) if isinstance(n, ast_mod.Call)]
                def _is_self_call(n, meth):
                    return (isinstance(n.func, ast_mod.Attribute) and n.func.attr == meth
                            and isinstance(n.func.value, ast_mod.Name) and n.func.value.id == "self")
                n_log = sum(1 for n in calls if _is_self_call(n, "log"))
                verdicts = [n for n in calls if _is_self_call(n, "passed") or _is_self_call(n, "failed")]
                # An assertion with an empty reason emits no log marker (framework
                # guards on `if reason != ''`) — see LOGGING-CONTRACT.md.
                empty_verdicts = [n for n in verdicts
                                  if not n.args or (isinstance(n.args[0], ast_mod.Constant)
                                                    and str(n.args[0].value).strip() == "")]
                nonempty_verdicts = [n for n in verdicts if n not in empty_verdicts]
                if n_log < 1:
                    errors.append(f"contract: {c.name}.main() has no self.log() (needs step-start + observed)")
                # Need at least one real determination; the standard if/else idiom has a
                # passed() in one branch and failed() in the other (two textual verdicts,
                # one per path) — that is correct, so require >=1, not ==1.
                if not nonempty_verdicts:
                    errors.append(f"contract: {c.name}.main() has no non-empty "
                                  f"self.passed()/self.failed() determination")
                if empty_verdicts:
                    errors.append(f"contract: {c.name}.main() has {len(empty_verdicts)} empty "
                                  f"self.passed()/self.failed() (empty reason emits no log marker)")
                # PLAN §1.5 — inline source-provenance tag conformance: the FIRST
                # line inside main() must be a re-stamped `# ART/SVT/legacy/AI` tag.
                body_lines = [ln for ln in m_src.splitlines()[1:] if ln.strip()]
                if not body_lines or not _PROVENANCE_TAG_RX.match(body_lines[0]):
                    errors.append(f"contract: {c.name}.main() missing a leading "
                                  f"# ART/SVT/legacy/AI provenance tag (PLAN §1.5)")
        src_tail = code[-600:]
        if "ts.run(sys.argv)" not in code and ".run(sys.argv)" not in src_tail:
            errors.append("structure: missing ts.run(sys.argv) __main__ entry")
        if "self.passed(" not in code and "self.failed(" not in code:
            warnings.append("no self.passed()/self.failed() calls found in this file "
                            "(ok only if inherited main() asserts)")
        # Leftover template placeholders must not survive into a saved script.
        for marker in (">>> FILL", "output = ''  # >>> replace", "if False:  # >>> replace"):
            if marker in code:
                errors.append(f"contract: unfilled template placeholder present ({marker!r})")

        # 3. Framework imports must exist in the surface index (from ck.db — the
        #    single runtime source; no JSON read).
        surface = dbx.get_json_doc("framework_surface") or {}
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
        # Validate the FULL library filename before building any path. The old check
        # looked only at Path(name).stem — which strips directory + extension — so a name
        # like '../../evil.py' passed (stem 'evil') while the raw name was still used to
        # build the write path, escaping the generated dir (adversarial-review finding).
        raw_name = lib.get("name") or ""
        stem = Path(raw_name).name                      # drop any directory component
        if not stem.endswith(".py"):
            raise HTTPException(400, "Library file name must end with .py")
        if not _NAME_RX.match(stem[:-3]):               # base (sans .py) must be safe
            raise HTTPException(400, "Invalid library file name (letters/digits/-_ only).")
        lib_path = script_path.parent / stem            # basename only — never the raw name
        # Belt-and-suspenders: the resolved path must stay inside the script's own dir.
        if lib_path.parent.resolve() != script_path.parent.resolve():
            raise HTTPException(400, "Library file must be written alongside the script.")
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
        "fragments": [{k: f.get(k) for k in ("source_id", "symbol", "maps_to")}
                      for f in _selected_fragments(sess)],
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


@router.get("/pt_cases")
async def pt_cases(request: Request):
    """Complete (Generator-exported) cases, split by PyTest Creator work state for the
    two Cases dropdowns:
      - complete:    step 8 (Final Validation) confirmed + validated in PyTest Creator
      - in_progress: everything else (not yet fully validated here)
    Both lists only contain cases with a refined zephyr_payload.json — i.e. cases the
    PyTest Creator can actually load. Grouped by Zephyr folder leaf for optgroups.
    """
    data = _data(request)
    zephyr = data.get("zephyr_master", {})
    cands = data.get("candidates", []) or []
    all_keys = [c["key"] for c in cands
                if c.get("candidates") and c.get("key")
                and not _is_hidden_case(c["key"], zephyr.get(c["key"], {}).get("folder", ""))]

    complete_set = _refined_complete_keys()
    refined_keys = [k for k in all_keys if k in complete_set]

    try:
        pt_prog = dbx.list_pt_progress()
    except Exception as e:
        print(f"Warning: reading pt session progress failed: {e}")
        pt_prog = {}

    done_keys = [k for k in refined_keys if (pt_prog.get(k) or {}).get("validated")]
    open_keys = [k for k in refined_keys if k not in set(done_keys)]

    # Partials-first ordering for the Open/Partial dropdown: cases whose PyTest work has
    # actually started (a pt session with ≥1 confirmed step, but not yet validated) go in
    # a single "In progress" optgroup at the TOP; every other not-yet-started case follows,
    # grouped by Zephyr folder. Mirrors the Generator's Step-1 partials-on-top pattern.
    def _num(k: str):
        return k.split("-T")[-1] if "-T" in k else k

    partial_keys = sorted(
        [k for k in open_keys if (pt_prog.get(k) or {}).get("confirms", 0) > 0],
        key=lambda k: (-(pt_prog.get(k) or {}).get("confirms", 0), _num(k)),
    )
    partial_set = set(partial_keys)
    not_started_keys = [k for k in open_keys if k not in partial_set]

    open_grouped = []
    if partial_keys:
        partial_cases = []
        for k in partial_keys:
            title = zephyr.get(k, {}).get("title", k)
            conf = (pt_prog.get(k) or {}).get("confirms", 0)
            hint = f" [{conf}/7 steps]" if conf else ""
            partial_cases.append({"key": k, "title": f"{title}{hint}" if title else f"{k}{hint}"})
        open_grouped.append({"label": f"In progress ({len(partial_cases)})", "cases": partial_cases})
    open_grouped.extend(_build_case_groups(not_started_keys, zephyr))

    return {
        "in_progress": {"grouped": open_grouped},
        "complete": {"grouped": _build_case_groups(done_keys, zephyr)},
        "counts": {"in_progress": len(open_keys), "complete": len(done_keys),
                   "partials": len(partial_keys)},
    }


@router.post("/load_case/{key}")
async def load_case(key: str, request: Request):
    data = _data(request)
    sess = pt_sessions.get(key) or _pt_load(key)
    if not sess:
        group, payload, trace = _find_refined_case(key)
        sess = PtSession(key=key, group=group, payload=payload, traceability=trace)
    _sweep_stale_runs(sess)
    changed = _apply_workspace_llm(sess)
    pt_sessions[key] = sess
    _pt_persist(sess)
    fields = _case_payload_fields(sess)
    return {
        "session": safe_session_dict(sess),   # redacts llm_config secrets
        "case_title": _case_title(data, key),
        "group_display": _group_display(sess.group),
        "objective": fields["objective"],
        "steps": fields["steps"],
        "llm_applied_from_workspace": changed,
    }


@router.get("/session/{key}")
async def get_session(key: str):
    sess = _pt_get(key)
    return {"session": safe_session_dict(sess)}   # redacts llm_config secrets


@router.post("/clear_session/{key}")
async def clear_session(key: str):
    pt_sessions.pop(key, None)
    dbx.delete_session("pt", key)   # Commit C: sessions live in ck.db
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
    # Steps 3/5 (matches/fragments) are lists where an EMPTY list is a legitimate,
    # already-run answer -- e.g. a case with genuinely no reusable code correctly
    # returns `fragments: []` (verified live on AWPTCM-T33235, Part 2B). A truthiness
    # check on the list itself can't tell
    # that apart from "the step never ran", so for these two check the STEP
    # actually ran (the step's own LLM `provenance` is present) rather than
    # whether the list happens to be non-empty. Steps with non-list required
    # fields (sequence/decision/files/runs/validated) keep the truthiness check —
    # those are never legitimately empty-but-complete.
    if required_field in ("matches", "fragments"):
        ran = bool(content.get("provenance")) or content.get(required_field) is not None
        if not ran:
            raise HTTPException(409, f"Nothing to confirm yet for '{_step_label(step)}' "
                                     f"(missing {required_field}).")
    elif not content.get(required_field):
        raise HTTPException(409, f"Nothing to confirm yet for '{_step_label(step)}' "
                                 f"(missing {required_field}).")
    _confirm(sess, step_key)
    _invalidate_from(sess, step)
    _pt_persist(sess)
    return {"session": safe_session_dict(sess)}   # redacts llm_config secrets


# ---------------------------------------------------------------------------
# Step 2 — prescriptive sequence
# ---------------------------------------------------------------------------

@router.post("/extract_sequence/{key}")
async def extract_sequence(key: str, request: Request):
    data = _data(request)
    sess = _pt_get(key)
    dry_run = await _dry_run(request)
    fields = _case_payload_fields(sess)
    if not fields["steps"]:
        raise HTTPException(409, "Refined case has no test steps to work from.")
    # Sequence extraction runs off the authoritative inputs only (objective + Zephyr
    # steps). Traceability context was deliberately dropped: it added ~35% of the
    # prompt tokens as reviewer-facing prose (coverage-gap essays, empty section
    # placeholders, workflow status) with no bearing on converting steps into an
    # automatable sequence.
    meta = await run_in_threadpool(run_prompt, "pt_extract_sequence.jinja", {
        "case_key": key,
        "case_title": _case_title(data, key),
        "objective": fields["objective"],
        "steps": fields["steps"],
    }, llm_config=_llm_cfg(sess), dry_run=dry_run)
    if dry_run:
        return _provenance_preview(meta)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    parsed = extract_json_block(meta.get("content", ""))
    sequence = _parsed_list(parsed, "sequence")
    if not sequence:
        raise HTTPException(502, "LLM returned no sequence. Raw response stored in provenance.")
    notes = _parsed_field(parsed, "notes", "")
    for i, s in enumerate(sequence):
        s["n"] = i + 1
        _collapse_step_text(s)
    sess.step2 = {"sequence": sequence, "notes": notes,
                  "confirmed": False,
                  "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                                 "prompt": meta.get("prompt", ""),
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
        _collapse_step_text(s)
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
    dry_run = bool((body or {}).get("dry_run"))
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

    if dry_run:
        if not candidates:
            return {"provenance": {"prompt": "", "note": "no mechanical candidates to match", "dry_run": True}}
        meta = await run_in_threadpool(run_prompt, "pt_match_scripts.jinja", {
            "case_key": key, "sequence": sequence,
            "user_inputs": user_inputs, "candidates": candidates,
        }, llm_config=_llm_cfg(sess), timeout=300, dry_run=True)
        return _provenance_preview(meta)

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


@router.post("/suggest_scripts_step/{key}/{step_n}")
async def suggest_scripts_step(key: str, step_n: int, request: Request,
                               body: dict = Body(default={})):
    """Per-step LLM suggestion: rank scripts against ONE sequence step's action/verify.

    Unlike the global suggest (which fans matches out across the whole sequence), this
    scopes the LLM to a single step so a reviewer can fill a specific gap. Every returned
    match is linked to this step by construction (covers_steps forced to [step_n]); the
    frontend drops them into that step's candidate list. Not persisted to step3.matches —
    the reviewer chooses per step and saves the whole map via save_matches.
    """
    data = _data(request)
    sess = _pt_get(key)
    dry_run = bool((body or {}).get("dry_run"))
    _require_confirmed(sess, "step2", "Per-step script search")
    sequence = (sess.step2 or {}).get("sequence") or []
    step = next((s for s in sequence if s.get("n") == step_n), None)
    if not step:
        raise HTTPException(404, f"No sequence step {step_n}.")
    user_inputs = body.get("user_inputs", "") or ""

    query_toks = _pt_tokens(step.get("action", "")) | _pt_tokens(step.get("verify", ""))
    query_toks |= _pt_tokens(_case_title(data, key)) | _pt_tokens(user_inputs)
    mech = _search_slim(data, query_toks, limit=20)
    candidates = []
    for c in mech:
        rec = (data.get("scripts_index_by_id") or {}).get(c["id"]) or {}
        candidates.append({**c, "case_descs": [tc["desc"] for tc in rec.get("test_cases", [])
                                               if tc.get("desc")][:12]})
    # Present the single step as a 1-entry sequence so the match template ranks against it.
    one_seq = [{"n": step_n, "action": step.get("action", ""), "verify": step.get("verify", "")}]

    if dry_run:
        if not candidates:
            return {"provenance": {"prompt": "", "note": "no mechanical candidates for this step", "dry_run": True}}
        meta = await run_in_threadpool(run_prompt, "pt_match_scripts.jinja", {
            "case_key": key, "sequence": one_seq,
            "user_inputs": user_inputs, "candidates": candidates,
        }, llm_config=_llm_cfg(sess), timeout=300, dry_run=True)
        return _provenance_preview(meta)

    llm_matches = []
    if candidates:
        meta = await run_in_threadpool(run_prompt, "pt_match_scripts.jinja", {
            "case_key": key, "sequence": one_seq,
            "user_inputs": user_inputs, "candidates": candidates,
        }, llm_config=_llm_cfg(sess), timeout=300)
        if not meta.get("error"):
            parsed = extract_json_block(meta.get("content", ""))
            valid_ids = {c["id"] for c in candidates}
            llm_matches = [m for m in _parsed_list(parsed, "matches")
                           if isinstance(m, dict) and m.get("id") in valid_ids
                           and m.get("coverage") in ("full", "partial")]

    mech_by_id = {c["id"]: c for c in mech}
    # Force covers_steps to this step — every result is linked to it by construction.
    matches = [{**mech_by_id.get(m["id"], {"id": m["id"]}), **m, "covers_steps": [step_n]}
               for m in llm_matches]
    return {"matches": matches, "mechanical_considered": len(mech), "step_n": step_n}


@router.post("/save_matches/{key}")
async def save_matches(key: str, body: dict = Body(...)):
    """Store the reviewer's per-step script selections + free-text inputs.

    `selections` is a per-step map {stepN(str): [script_id, ...]}. The same script
    may appear under several steps (it covers several). Downstream (Fragments/Generate)
    read the flattened unique id set via _selected_script_ids(); the per-step map is
    the source of truth for the coverage view.
    """
    sess = _pt_get(key)
    sels = body.get("selections")
    if not isinstance(sels, dict):
        raise HTTPException(400, "Body must include 'selections' (a {step: [ids]} map).")
    # Normalize: string step keys, list-of-str ids, de-duped per step.
    clean: Dict[str, list] = {}
    for step_k, ids in sels.items():
        if not isinstance(ids, list):
            continue
        seen, out = set(), []
        for sid in ids:
            if isinstance(sid, str) and sid and sid not in seen:
                seen.add(sid)
                out.append(sid)
        clean[str(step_k)] = out
    sess.step3 = {**(sess.step3 or {}), "selections": clean,
                  "user_inputs": body.get("user_inputs", (sess.step3 or {}).get("user_inputs", "")),
                  "confirmed": False}
    _invalidate_from(sess, 3)
    _pt_persist(sess)
    return {"selections": clean}


@router.get("/script_source")
async def script_source(request: Request, id: str,
                        start: Optional[int] = None, end: Optional[int] = None):
    """Source (slice) of an indexed script — id validated against the index."""
    data = _data(request)
    rec = _script_record(data, id)
    # `source` comes from ck.db; `path` is provenance-only (original repo location),
    # not a live filesystem handle — nothing reads it off disk anymore.
    return {"id": id, "path": rec.get("path"), "start": start, "end": end,
            "source": _read_source(rec, start, end)}


# ---------------------------------------------------------------------------
# Step 4 (Fit Decision) — RETIRED. Once generation moved to the fixed skeleton
# template (templates/pt_script_template.py.jinja), the reuse/extend/new decision
# no longer changed how the script was framed, so the whole step was removed
# (assess_fit/save_fit endpoints + UI panel). The internal stepN keys are left
# unchanged (fragments still live on step5, generate on step6, etc.) to avoid
# churning the load-bearing numeric scheme; only the visible sidebar numbers
# shifted down. gather_fragments now gates on step3 (see below).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Step 5 — fragments
# ---------------------------------------------------------------------------

@router.post("/gather_fragments/{key}")
async def gather_fragments(key: str, request: Request):
    data = _data(request)
    sess = _pt_get(key)
    dry_run = await _dry_run(request)
    # Fit Decision (former step 4) was retired once generation moved to the fixed
    # skeleton template: reuse/extend/new no longer changes how the script is framed,
    # so fragments are gathered straight from the confirmed step-3 script selections.
    _require_confirmed(sess, "step3", "Fragment gathering")
    sequence = (sess.step2 or {}).get("sequence") or []
    selections = _selected_script_ids(sess)

    # Offer the LLM ALL scripts the reviewer chose in step 3 (no cap — per-step
    # selection can legitimately span many). scripts_ctx carries only symbol names +
    # one-line descriptions (not source), so this stays cheap even for large selections.
    scripts_ctx = []
    for sid in selections:
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
        "case_key": key, "sequence": sequence, "scripts": scripts_ctx,
    }, llm_config=_llm_cfg(sess), timeout=300, dry_run=dry_run)
    if dry_run:
        return _provenance_preview(meta)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    parsed = extract_json_block(meta.get("content", ""))

    # New per-step schema: {steps:[{n, chosen:[{source_id, symbol, maps_to, why,
    # redundant:[{source_id, symbol, why}]}]}]}. We resolve real code for EVERY symbol
    # (chosen + redundant) into a flat fragment pool, and build a per-step `accounting`
    # of chosen→[redundant] so the UI can nest the redundant alternatives under the
    # chosen one they duplicate. `chosen` fragments default to selected; `redundant`
    # ones live in the pool but start deselected.
    fragments_by_key: Dict[tuple, dict] = {}   # de-duped resolved fragments (pool)
    dropped = []
    accounting: Dict[str, list] = {}           # {stepN(str): [ {chosen_key, redundant_keys:[...]} ]}
    default_chosen: set = set()                # keys the LLM chose (auto-selected)

    # Valid step numbers for maps_to validation (finding #3): the LLM sometimes emits
    # maps_to entries that aren't real sequence steps, which would then mis-drive the
    # provenance remap and per-step preview slotting. Keep only numbers that exist.
    valid_steps = {int(s["n"]) for s in sequence if str(s.get("n") or "").strip().isdigit()}

    def _clean_maps(raw) -> list:
        """Keep only maps_to entries that are real sequence step numbers (drop phantoms)."""
        out = []
        for n in raw or []:
            try:
                ni = int(n)
            except (TypeError, ValueError):
                continue
            if (not valid_steps) or ni in valid_steps:
                if ni not in out:
                    out.append(ni)
        return out

    def _add_fragment(entry: dict, extra_steps: list) -> Optional[tuple]:
        """Resolve one {source_id, symbol, why, maps_to?} to code + register it in the
        pool. Returns its key, or None if unresolvable (dropped)."""
        sid = entry.get("source_id")
        sym = entry.get("symbol")
        if not sid or not sym:
            return None
        key = (sid, sym)
        # extra_steps come from the step loop (always a real n); merge with validated maps_to.
        want_steps = _clean_maps((entry.get("maps_to") or []) + list(extra_steps))
        if key in fragments_by_key:
            # already resolved; merge any newly-seen (validated) steps into maps_to
            existing = fragments_by_key[key]
            for n in want_steps:
                if n not in existing["maps_to"]:
                    existing["maps_to"].append(n)
            return key
        loc, code, py2_status = _resolve_symbol_code(data, sid, sym)
        if not code:
            dropped.append(entry)
            return None
        fragments_by_key[key] = {"source_id": sid, "symbol": sym, "loc": loc,
                                 "code": code[:8000], "maps_to": want_steps,
                                 "why": entry.get("why", ""),
                                 # D3 provenance/soft-warn signals:
                                 #  translated  → code is modernized Py3 (tag gets (py2→py3))
                                 #  py2_flagged → Py2 fragment lib2to3 could NOT translate;
                                 #                ship original + banner + prompt steer
                                 "py2_translated": py2_status == "translated",
                                 "py2_flagged": py2_status in ("parse_error", "unavailable")}
        return key

    for st in _parsed_list(parsed, "steps"):
        if not isinstance(st, dict):
            continue
        try:
            n = int(st.get("n"))
        except (TypeError, ValueError):
            continue
        step_entries = []
        for ch in st.get("chosen") or []:
            if not isinstance(ch, dict):
                continue
            ck = _add_fragment(ch, [n])
            if not ck:
                continue
            default_chosen.add(ck)
            red_keys = []
            for rd in ch.get("redundant") or []:
                if not isinstance(rd, dict):
                    continue
                rk = _add_fragment(rd, [n])   # redundant frags also resolve to real code
                if rk:
                    red_keys.append({"key": list(rk), "why": rd.get("why", "")})
            step_entries.append({"chosen": list(ck), "redundant": red_keys})
        if step_entries:
            accounting[str(n)] = step_entries

    fragments = list(fragments_by_key.values())

    # Merge into any existing pool (a re-Gather adds to what's there without wiping the
    # reviewer's selections). Freshly CHOSEN fragments default to selected; redundant
    # ones are added to the pool but not auto-selected. Previously-made selections win.
    prev = sess.step5 or {}
    pool = list(prev.get("fragments") or [])
    have = {_frag_key(f) for f in pool}
    selected = list(prev.get("selected") or [])
    sel_have = {tuple(s) if isinstance(s, (list, tuple)) else (s.get("source_id"), s.get("symbol"))
                for s in selected}
    added = 0
    for f in fragments:
        k = _frag_key(f)
        if k not in have:
            pool.append(f)
            have.add(k)
            added += 1
        # auto-select only fragments the LLM CHOSE (not the redundant alternatives)
        if k in default_chosen and k not in sel_have:
            selected.append({"source_id": f["source_id"], "symbol": f["symbol"]})
            sel_have.add(k)

    # Merge accounting (new steps overwrite; old steps for untouched sequence numbers kept)
    merged_acct = dict(prev.get("accounting") or {})
    merged_acct.update(accounting)

    sess.step5 = {"fragments": pool, "selected": selected, "dropped": dropped,
                  "accounting": merged_acct, "confirmed": False,
                  "selections_fingerprint": _selections_fingerprint(sess),
                  "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                                 "prompt": meta.get("prompt", ""),
                                 "response": meta.get("content", "")[:20000]}}
    _invalidate_from(sess, 5)
    _pt_persist(sess)
    return {"fragments": pool, "selected": selected, "accounting": merged_acct,
            "added": added, "dropped": len(dropped),
            "scripts_considered": len(selections)}


@router.post("/save_fragments/{key}")
async def save_fragments(key: str, body: dict = Body(...)):
    """Persist the reviewer's SELECTED fragments (list of {source_id, symbol}).

    The full gathered pool (step5.fragments) is retained so the UI keeps its
    selected / not-selected split; only step5.selected changes. Generation reads the
    selected subset via _selected_fragments. An empty `keep` means nothing selected
    (a legitimate 'new script from scratch' outcome)."""
    sess = _pt_get(key)
    step5 = sess.step5 or {}
    pool = step5.get("fragments") or []
    pool_keys = {_frag_key(f) for f in pool}
    selected = [{"source_id": k.get("source_id"), "symbol": k.get("symbol")}
                for k in body.get("keep", [])
                if (k.get("source_id"), k.get("symbol")) in pool_keys]
    sess.step5 = {**step5, "selected": selected, "confirmed": False}
    _invalidate_from(sess, 5)
    _pt_persist(sess)
    return {"selected": selected, "pool": len(pool)}


@router.post("/preview_fragments/{key}")
async def preview_fragments(key: str, request: Request, body: dict = Body(default={})):
    """The per-step ARTEFACT the Fragments step produces: the Generate skeleton with the
    currently-selected fragments' code slotted per verification step (as reference
    blocks), plus the FILL markers Generate will complete. A pre-LLM preview so the
    reviewer sees how the reused pieces assemble before submitting to Generate.

    Accepts an optional `keep` list ([{source_id, symbol}]) so the preview reflects LIVE
    (unsaved) toggles; falls back to the persisted selection when omitted.
    """
    data = _data(request)
    sess = _pt_get(key)
    pool = (sess.step5 or {}).get("fragments") or []
    keep = body.get("keep")
    if isinstance(keep, list) and keep:
        want = {(k.get("source_id"), k.get("symbol")) for k in keep}
        fragments = [f for f in pool if _frag_key(f) in want]
    elif isinstance(keep, list):        # explicit empty selection
        fragments = []
    else:
        fragments = _selected_fragments(sess)

    # Same import surfacing Generate does, so the header reflects reality.
    extra_import_lines: List[str] = []
    for f in fragments:
        rec = (data.get("scripts_index_by_id") or {}).get(f.get("source_id")) or {}
        for m in rec.get("imports", []):
            if m.startswith("framework.") and m not in ("framework.ATTestSet", "framework.ATTestCase"):
                line = "from {} import {}".format(*m.rsplit(".", 1)) if "." in m else "import " + m
                if line not in extra_import_lines:
                    extra_import_lines.append(line)

    sequence = (sess.step2 or {}).get("sequence") or []
    preview = _assemble_fragment_preview(key, _case_title(data, key), sequence,
                                         extra_import_lines, fragments)
    return {"preview": preview, "selected_count": len(fragments)}


# ---------------------------------------------------------------------------
# Step 6 — generate + naming + lint
# ---------------------------------------------------------------------------

@router.post("/generate_script/{key}")
async def generate_script(key: str, request: Request, body: dict = Body(default={})):
    data = _data(request)
    sess = _pt_get(key)
    dry_run = bool((body or {}).get("dry_run"))
    _require_confirmed(sess, "step2", "Generation")
    # steps 3-5 may legitimately be 'new script, no fragments'; require them
    # confirmed so the human explicitly reviewed the (possibly empty) reuse.
    _require_confirmed(sess, "step5", "Generation")

    naming = (sess.step6 or {}).get("naming") or {}
    group = body.get("group") or naming.get("group") or _group_display(sess.group)
    name = body.get("name") or naming.get("name") or _propose_name(_case_title(data, key))
    group, name = _validate_naming(group, name)
    file_name = f"{name}.py"

    fragments = _selected_fragments(sess)   # only the reviewer-selected subset
    extra_mods = []
    extra_import_lines: List[str] = []
    for f in fragments:
        rec = (data.get("scripts_index_by_id") or {}).get(f["source_id"]) or {}
        for m in rec.get("imports", []):
            if m.startswith(("framework.", "ATPyLib.")):
                extra_mods.append(m.replace("framework.", "").replace("ATPyLib.", ""))
            # surface real framework `from ... import` lines into the skeleton header
            if m.startswith("framework.") and m not in ("framework.ATTestSet", "framework.ATTestCase"):
                line = "from {} import {}".format(*m.rsplit(".", 1)) if "." in m else "import " + m
                if line not in extra_import_lines:
                    extra_import_lines.append(line)

    sequence = (sess.step2 or {}).get("sequence", [])
    # Topology (switches/stacks/portlinks) is detected from the sequence + fragments
    # inside _render_skeleton, so multi-device cases keep a fixed init() frame.
    skeleton = _render_skeleton(key, _case_title(data, key), sequence,
                                extra_import_lines, fragments)
    # Device-name reconciliation (finding #1): tell the LLM which names the reused
    # fragments use vs what init() binds, so it renames rather than emitting AttributeErrors.
    bound_devs, _stk, _pl = _detect_topology(sequence, fragments)
    device_note = _fragment_device_note(fragments, bound_devs)

    llm_cfg = _llm_cfg(sess)
    fragments_ctx = [{**f, "tag": _fragment_tag(f.get("source_id", ""), f.get("loc"),
                                                f.get("py2_translated", False))}
                     for f in fragments]
    # D3: Py2 fragments that lib2to3 could NOT auto-modernize ship as-is; steer the
    # model to translate their idioms (only present when such a fragment is selected,
    # so clean cases pay no extra prompt weight). Translated fragments are already Py3
    # and need no steer.
    py2_flagged = any(f.get("py2_flagged") for f in fragments)
    meta = await run_in_threadpool(run_prompt, "pt_generate_script.jinja", {
        "case_key": key,
        "case_title": _case_title(data, key),
        "file_name": file_name,
        "skeleton": skeleton,
        "fragments": fragments_ctx,
        "device_note": device_note,
        "bound_devices": bound_devs,
        "py2_flagged": py2_flagged,
        "framework_surface": _framework_surface_slice(data, extra_mods),
        "model_name": llm_cfg.get("model") or "unknown",
        "gen_date": datetime.utcnow().strftime("%Y-%m-%d"),
    }, llm_config=llm_cfg, timeout=600, dry_run=dry_run,
       # This step emits a whole standardized script (real runs have hit
       # ~35KB); the default 16000-token cap truncated a live generate on
       # T33234 (Part 2B, 2026-07-22) — give it more completion headroom.
       max_tokens=32000)
    if dry_run:
        return _provenance_preview(meta)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    blocks = _parse_generated_blocks(meta.get("content", ""))
    if not blocks["test_code"]:
        raise HTTPException(502, "LLM returned no python code block.")
    # PLAN §1.5 — authoritative re-stamp: server-known step->fragment mapping wins
    # over anything the model self-reported, so provenance is trustworthy either way.
    stamped_code = _restamp_provenance(blocks["test_code"], fragments,
                                       meta.get("model") or "", sequence)

    prev = sess.step6 or {}
    sess.step6 = {
        "naming": {"group": group, "name": name},
        "files": {"test": {"name": file_name, "code": stamped_code},
                  "library": blocks["library"]},
        "iterations": prev.get("iterations", 0) + 1,
        "confirmed": False,
        "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                       "prompt": meta.get("prompt", ""),
                       "response": meta.get("content", "")[:20000]},
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
        # Explicit remote path (not a named profile setup). This value is interpolated
        # into the remote SSH command, so reject anything that isn't a plausible path —
        # no shell metacharacters, whitespace, or quotes. `pt_exec` also shell-quotes it
        # (defense in depth), but rejecting here gives a clear 400 instead of a silently
        # mangled path. Allows POSIX path chars + dot/dash/underscore.
        if not re.fullmatch(r"[A-Za-z0-9_./\-]+", setup):
            raise HTTPException(400, "Invalid setup path: only letters, digits, '_', '.', '/', '-' allowed.")
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
    # Re-mark restart-orphaned runs here too, not just in load_case — otherwise this
    # endpoint reports the persisted 'running' forever and the UI polls indefinitely.
    if _sweep_stale_runs(sess):
        _pt_persist(sess)
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
    dry_run = await _dry_run(request)
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
    }, llm_config=_llm_cfg(sess), timeout=600, dry_run=dry_run,
       max_tokens=32000)  # emits a whole revised script — same size profile as generate
    if dry_run:
        return _provenance_preview(meta)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    blocks = _parse_generated_blocks(meta.get("content", ""))
    if not blocks["test_code"]:
        raise HTTPException(502, "LLM fix returned no python code block.")
    # Re-stamp (PLAN §1.5): a fix pass can shift step content, so re-derive tags
    # from the same fragment mapping rather than trust whatever survived the edit.
    fix_fragments = _selected_fragments(sess)
    fix_sequence = (sess.step2 or {}).get("sequence") or []
    stamped_code = _restamp_provenance(blocks["test_code"], fix_fragments,
                                       meta.get("model") or "", fix_sequence)

    # Archive current iteration before replacing
    iteration = step6.get("iterations", 1)
    hist_dir = _meta_dir(naming.get("group", "Ungrouped"),
                         naming.get("name", "unnamed")) / "history" / f"iter-{iteration}"
    hist_dir.mkdir(parents=True, exist_ok=True)
    (hist_dir / step6["files"]["test"]["name"]).write_text(
        step6["files"]["test"]["code"], encoding="utf-8")

    step6["files"]["test"]["code"] = stamped_code
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

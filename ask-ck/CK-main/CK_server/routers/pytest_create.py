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
from pathlib import Path
import html as html_mod
import json
import os
import py_compile
import re
import tempfile

from models import PtSession, safe_session_dict, model_to_dict
from paths import REFINED_DIR, PT_GENERATED_DIR
from timeutil import utc_now, as_utc
from llm import run_prompt, extract_json_block, _CODE_SYSTEM_PROMPT
import db as dbx   # aliased: several functions here have a `db` filter parameter
import gen_assembly
import locks
from pt_exec import (
    load_profiles, save_profiles, redact_profile, normalize_profile,
    check_profile, parse_framework_log, failure_excerpts, run_manager,
)
# Shared with the Generator. These were six underscore-PRIVATE imports out of
# routers/wizard.py until PLAN-backend-module-split.md commit 8 — a sibling router
# reaching into another router's internals, so renaming any one of them silently broke
# a different tool. They now live in leaf modules that both routers import.
from case_registry import build_case_groups, is_hidden_case, refined_complete_keys
from llm_config import apply_workspace_llm

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


# Stdlib modules REMOVED in the Python 3 versions a testbox actually runs. A generated
# script is executed by the TESTBOX's `python3`, not this server's — tb470 is on 3.13.5
# (2026-07-28) while this seat is on 3.10, so an import that resolves here can be a hard
# ImportError there. `py_compile` cannot catch it: compiling proves syntax, never that a
# module exists. That combination is how the skeleton shipped
# `from distutils.util import strtobool` — valid syntax, compiles clean on 3.10, and
# guaranteed to crash on import on any 3.12+ testbox before a single test ran.
#
# Keys are the removal version; values are (module, replacement) so the error can say what
# to do instead. Deliberately limited to real removals, not deprecations.
_REMOVED_STDLIB = {
    "3.12": [
        ("distutils", "packaging / hand-rolled (strtobool: parse 'y'/'n' yourself)"),
        ("imp", "importlib"),
        ("asynchat", "asyncio"),
        ("asyncore", "asyncio"),
        ("smtpd", "aiosmtpd"),
    ],
    "3.13": [
        ("telnetlib", "the framework's own console driver (ATDrivers)"),
        ("cgi", "urllib.parse / email"),
        ("cgitb", "traceback"),
        ("pipes", "shlex / subprocess"),
        ("crypt", "hashlib / passlib"),
        ("nntplib", "n/a"),
        ("sndhdr", "n/a"),
        ("spwd", "n/a"),
    ],
}


def _removed_stdlib_imports(tree) -> List[str]:
    """Errors for imports of stdlib modules removed in a Python the testbox may run."""
    import ast as _a
    flat = {mod: (ver, repl)
            for ver, mods in _REMOVED_STDLIB.items() for mod, repl in mods}
    out: List[str] = []
    for node in _a.walk(tree):
        names: List[str] = []
        if isinstance(node, _a.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, _a.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for name in names:
            root = name.split(".")[0]
            if root in flat:
                ver, repl = flat[root]
                out.append(
                    f"imports: `{name}` — the stdlib `{root}` module was REMOVED in "
                    f"Python {ver}, and the testbox runs the script with its own python3 "
                    f"(tb470 is on 3.13). This compiles here but is an ImportError there. "
                    f"Use {repl} instead.")
    return out


def _py2_refactor_backend():
    """The 2-to-3 refactoring engine, or (None, "") if neither is installed.

    Returns (refactor_module, fixers_package_name).

    Two backends because `lib2to3` was REMOVED FROM THE STDLIB IN PYTHON 3.13 — and 3.13 is
    the version this project deliberately targets, because the PyTest Creator lints
    generated scripts with the local interpreter and the testbox runs 3.13.5
    (requirements.txt: "PREFER PYTHON 3.13 — match the testbox"). So the recommended
    environment was precisely the one where this feature silently stopped working: the
    import failed, `_translate_py2` returned "unavailable", and every legacy Py2 fragment
    shipped untranslated behind a soft-warn. Nothing raised, so nothing said so. Measured
    on the 2026-07-30 Opus batch: 1 py2_flagged fragment, 0 translated.

    `fissix` is the maintained fork of lib2to3 with the same `refactor` API and its own
    `fissix.fixes` package, so it is a genuine drop-in rather than a reimplementation.
    Preference order is stdlib-first purely so nothing changes on an interpreter that still
    ships lib2to3.
    """
    try:
        from lib2to3 import refactor          # noqa: PLC0415
        return refactor, "lib2to3.fixes"
    except Exception:
        pass
    try:
        from fissix import refactor           # noqa: PLC0415
        return refactor, "fissix.fixes"
    except Exception:
        return None, ""


def _translate_py2(code: str, name: str = "fragment") -> Tuple[str, str]:
    """Deterministically modernize a Py2 code fragment to Py3 via lib2to3 (or fissix).

    Returns (new_code, status) where status is one of:
      - "translated"  : the refactorer parsed it and produced (possibly changed) Py3.
      - "clean"       : no Py2 tells to begin with (caller usually skips this path).
      - "parse_error" : could not parse it — ORIGINAL code returned unchanged
                        (caller must soft-warn, never ship a broken translation).
      - "unavailable" : NEITHER lib2to3 nor fissix is installed — original returned;
                        caller soft-warns. See _py2_refactor_backend for why there are two.

    Never raises: any failure degrades to returning the original code + a status the
    caller can act on. The refactorer wants a trailing newline and a name for errors.
    """
    if not _has_py2_tells(code):
        return code, "clean"
    refactor, fixers_pkg = _py2_refactor_backend()
    if refactor is None:
        return code, "unavailable"
    try:
        # Normalize indentation FIRST. Py2 legacy source frequently mixes tabs and
        # spaces (Py2 tolerated it; Py3's tokenizer rejects it as "inconsistent use of
        # tabs and spaces"). lib2to3 fixes SYNTAX but preserves the original mixed
        # indentation, so without this the translated code still fails ast.parse /
        # py_compile. expandtabs(8) applies Python's own tab-stop rule (found by the
        # adversarial test: 9/85 translations were invalid Py3 for exactly this reason).
        norm = "\n".join(ln.expandtabs(8) for ln in code.split("\n"))
        fixers = refactor.get_fixers_from_package(fixers_pkg)
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
    column by db.save_session. The pt-{key}.json file stays as frozen backup.

    Failures are RAISED, not printed (2026-07-28). Swallowing them into a `print` meant an
    endpoint returned 200 while the work never reached the DB — the caller then had no way
    to know, and the documented workaround was "never trust the 200". A lost generate costs
    a multi-minute LLM round trip, so it must fail loudly.

    Case-locking guards run FIRST (PLAN-auth-and-case-locking.md Phase 1), before the DB
    write and outside the try/except so their 409 is never rewrapped as a 500:
    `require_can_write` refuses if another tab/user holds a live lock on this case, and
    `next_rev` is the optimistic backstop against a stale copy — precisely the two-process
    window `_pt_get` documents. Both raise `locks.LockError` → HTTP 409 (app-wide handler).
    """
    locks.require_can_write("pt", sess.key)
    sess.updated_at = utc_now()
    sess.rev = locks.next_rev("pt", sess.key, int(sess.rev or 0))
    try:
        data = model_to_dict(sess)
        dbx.save_session("pt", sess.key, data)
    except Exception as e:
        print(f"ERROR: failed to persist pt session {sess.key}: {e}")
        raise HTTPException(
            500, f"Could not save PyTest session {sess.key} to the database: {e}. "
                 f"Your work was NOT saved — retry, and check the server log.")


def _pt_load(key: str) -> Optional[PtSession]:
    try:
        raw = dbx.load_session("pt", key)
        if raw is not None:
            return PtSession(**raw)
    except Exception as e:
        print(f"Warning: failed to load pt session {key}: {e}")
    return None


def _pt_session_updated_at(key: str) -> Optional[str]:
    """The DB's `updated_at` for this session, without loading the whole payload."""
    try:
        row = dbx.get_connection().execute(
            "SELECT updated_at FROM sessions WHERE id=?", (f"pt-{key}",)).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _pt_get(key: str) -> PtSession:
    """The live session, preferring whichever copy is NEWER — memory or the DB.

    The in-memory cache used to win unconditionally, which silently destroyed work
    (2026-07-28). `pt_sessions` is per-process, so a second server instance — a leftover
    `--reload` worker, or the 24-day-old process found running beside this one — holds its
    own copy from whenever it last served that case. A request routed there is answered
    from that stale copy AND re-persists it, overwriting a newer generate that had already
    committed. Symptom: an endpoint returns 200 with correct new data, and a later read
    shows the OLD script, which reads exactly like "the write never landed".

    Comparing `updated_at` against the DB costs one indexed lookup and makes the DB
    authoritative whenever it is ahead, so a stale instance can no longer clobber.

    The comparison PARSES both stamps rather than comparing their strings. This is
    defence-in-depth, not a bug fix: `models.UtcDatetime` keeps the cached stamp aware, and
    with that in place string comparison happens to agree with parsed comparison on all 8
    shapes the `updated_at` column can hold (verified by enumeration in
    tests/test_tz_aware_timestamps.py). The point is that the verdict no longer DEPENDS on
    that coincidence — a naive stamp is a strict prefix of its own aware form
    ("…T12:00:00" vs "…T12:00:00+00:00"), so string ordering is sensitive to formatting in
    a way this check must not be. `as_utc` reads a naive stamp as UTC, which is what the
    pre-cutover `utcnow()` always meant.
    """
    cached = pt_sessions.get(key)
    if cached is not None:
        db_stamp = as_utc(_pt_session_updated_at(key))
        mem_stamp = as_utc(cached.updated_at)
        if db_stamp and (mem_stamp is None or db_stamp > mem_stamp):
            fresh = _pt_load(key)
            if fresh is not None:
                print(f"[pt] {key}: DB copy is newer than this process's cache "
                      f"({db_stamp} > {mem_stamp}); reloading to avoid overwriting it")
                pt_sessions[key] = fresh
                return fresh
        return cached
    sess = _pt_load(key)
    if not sess:
        raise HTTPException(404, "PyTest Creator session not found. Call load_case first.")
    pt_sessions[key] = sess
    return sess


def _llm_cfg(sess: PtSession) -> dict:
    # Apply the workspace LLM login at dispatch time if this session has no
    # active config of its own. Without this, an LLM endpoint would fall back to
    # run_prompt's default backend (claude_agent/model=default) instead of the
    # provider the user configured on the Configure page — silently sending the
    # prompt to the wrong LLM. load_case applies it once, but a stale/inactive
    # persisted config (or a session touched before the workspace login) would
    # otherwise slip through. Centralized here so no endpoint can forget it,
    # via the shared llm_config.apply_workspace_llm the Generator also calls.
    if apply_workspace_llm(sess):
        _pt_persist(sess)
    return model_to_dict(sess.llm_config)


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
    step["confirmed_at"] = utc_now().isoformat()
    setattr(sess, step_key, step)


def _invalidate_from(sess: PtSession, step_num: int) -> None:
    """Editing/confirming step N un-confirms every later step (gate integrity)."""
    for k in STEP_KEYS:
        if int(k[4:]) > step_num:
            step = getattr(sess, k) or {}
            if step.get("confirmed"):
                step["confirmed"] = False
                step["invalidated_at"] = utc_now().isoformat()
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
# Refined-case resolution (case_registry.refined_complete_keys pattern, plus group)
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
    """'Port (7)' -> 'Port' (refined-cases group dirs carry candidate counts), sanitised
    to the charset `_validate_naming` will actually accept.

    This is BOTH the value the browser seeds the step-6 Group field with (load_case's
    `group_display`) and generate_script's server-side default when the body carries no
    group. Stripping only the count left the rest of the label verbatim, so a group whose
    name contains a character outside _GROUP_RX produced a default that the server's own
    validator then rejected with 400 "Invalid group name" — the API handing the UI a value
    it refuses to take back. Observed 2026-08-31 on AWPTCM-T33351, group
    'Authentication & Security (42)': the '&' is not in _GROUP_RX, so every dry-run
    provenance render 400'd before a single line of prompt was built, and the field reset
    to the invalid default on every re-render. It is the group of 42 cases, not one.

    A group that ALREADY validates is returned byte-for-byte unchanged, so existing groups
    (Management, Port) and the generated/ directories named after them are untouched — only
    a name that could not have worked at all is rewritten. Each run of disallowed characters
    collapses WITH the spaces hugging it into a single '_', which is what a human doing this
    by hand produced: 'Authentication & Security' -> 'Authentication_Security'.
    """
    g = re.sub(r"\s*\(\d+\)\s*$", "", group_dir).strip() or group_dir
    if _GROUP_RX.match(g):
        return g
    g = re.sub(r" *[^A-Za-z0-9 _()\-]+ *", "_", g)
    g = re.sub(r"_{2,}", "_", g).strip(" _")[:60]
    # Only reachable if the label held nothing usable at all (e.g. '***'); a valid
    # placeholder beats re-emitting the value we just proved the validator rejects.
    return g or "Ungrouped"


def _propose_name(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title)
    stop = {"the", "a", "an", "of", "and", "or", "to", "for", "with", "test", "verify", "check"}
    core = [w for w in words if w.lower() not in stop][:4]
    return ("_".join(core) + "_test") if core else "generated_test"


# ---------------------------------------------------------------------------
# Query tokenization. The 12/10/6 script scorer + its stopword/area sets live in db
# (db._score_script_candidate), applied inside dbx.search_scripts — single source of
# truth (Commit B).
#
# This comment used to claim "no private copy here" while a full copy of the scorer sat
# directly below it. That copy referenced _PT_GENERIC_TOKENS / _PT_AREA_SUPPORT, which
# only ever existed in db.py — so it raised NameError on any call and was reachable from
# nothing. Deleted. _pt_tokens stays: it is still used to build query token sets.
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
#
# MATCHES THE SHAPE, NOT A VERB LIST (Phase 7.8). This was
# `>>>\s*(FILL|replace|remove)\b`, while `_lint_generated` errors on ANY surviving
# `>>>` — so the template's `# >>> adjust operator timeout (s) <<<` was unstrippable
# AND a hard lint error, with no way for the model to win but to delete a comment it
# was never told about. The stripper must remove exactly what the lint punishes,
# wherever it can safely do so; any other split leaves a gap of exactly this kind.
_FILL_MARKER_RX = re.compile(r">>>")


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


# THE OUTPUT CEILING THIS GATE DEFENDED AGAINST DOES NOT EXIST (Phase 7.4, 2026-08-03).
#
# The gate was built on "the CLI's hard maxOutputTokens is 32,000, so an answer needing more
# than that will be truncated mid-token". Both halves are wrong.
#
# 32,000 bounds ONE MESSAGE, not the answer. The CLI continues a long answer across several
# assistant messages, and `_parse_cli_stream` concatenates them. Measured `output_tokens` on
# the four multi-message generations stored in debug-log/no-session.jsonl:
#
#     2026-07-30T06:47:37   67,326 output tokens   4 messages   40 TestCase classes
#     2026-07-30T07:25:59   66,334               2            11
#     2026-07-30T07:48:13   57,188               1             6
#     2026-07-30T07:00:16   34,966               2            17
#
# Every one exceeds 32,000, and every one is a COMPLETE script ending in ts.run(sys.argv).
# What actually truncated them was `_parse_generated_blocks`, which stopped at the first
# continuation fence (see gen_assembly). The three constants here were then fitted to that
# parser's output and called measurements of the model.
#
# So the block is gone. Predicting output size from skeleton size never worked — re-measured
# across every stored generation with the fixed recoverer, expansion runs 0.71 to 1.90
# (median 0.90), a 2.7x spread that no single constant can represent, and `_FILL_EXPANSION`
# was pinned at 1.95, above the top of the real range. `tool/pt_measure_expansion.py`
# reproduces the table.
#
# What replaces it: EVIDENCE INSTEAD OF PREDICTION. The reply is reassembled, checked
# against its own `ts.add_testCase(...)` manifest, and refused if it did not come back whole
# (`_recovery_failure`). That fires on what actually arrived rather than on a guess made
# before the call, so it cannot be wrong about a case it has never seen. `_size_estimate`
# below is advisory only — it tells the reviewer how big this generation is likely to be,
# and it never blocks.
_CHARS_PER_OUTPUT_TOKEN = 2.89       # 86,644 chars / 29,952 tokens, dense Python

# Re-measured 2026-08-03 across 36 recovered generations. Kept as a RANGE, because the
# single fitted constant it replaces was the error: one number cannot carry both
# marker-stripping (deterministic) and model verbosity (variable).
_FILL_EXPANSION_OBSERVED = (0.71, 1.90)


def _size_estimate(skeleton: str, sequence: list) -> Dict[str, Any]:
    """Advisory size projection for a generation. NEVER blocks — see the note above.

    Returned to the caller so a reviewer can see what to expect (notably: how many
    continuation messages a large script will arrive in), without a prediction standing
    between them and a generation that would have worked.
    """
    lo, hi = _FILL_EXPANSION_OBSERVED
    n_tc = max(skeleton.count("class TestCase"), 1)
    likely_chars = (int(len(skeleton) * lo), int(len(skeleton) * hi))
    likely_tokens = tuple(int(c / _CHARS_PER_OUTPUT_TOKEN) for c in likely_chars)
    # One message carries ~32,000 output tokens; more than that simply continues.
    messages = max(1, -(-likely_tokens[1] // 32000))
    return {
        "skeleton_chars": len(skeleton),
        "testcase_classes": n_tc,
        "sequence_steps": len(sequence),
        "projected_chars": likely_chars,
        "projected_output_tokens": likely_tokens,
        "likely_messages": messages,
        "note": (f"Projected {likely_chars[0]:,}-{likely_chars[1]:,} chars "
                 f"(~{likely_tokens[0]:,}-{likely_tokens[1]:,} output tokens). "
                 + (f"This will arrive across about {messages} assistant messages and be "
                    f"reassembled server-side." if messages > 1 else
                    "This fits in a single message.")),
    }


def _parse_generated_blocks(content: str) -> Dict[str, Any]:
    """Extract test + optional 'LIBRARY: <name>' python blocks from LLM output.

    This used to be one non-greedy regex, and THAT REGEX IS WHY THE "OUTPUT CEILING"
    APPEARED TO EXIST. The CLI splits a long answer across assistant messages that each
    re-open a ```python fence, so `(.*?)``` ` stopped at the *continuation's opening* fence
    and the rest was dropped — usually mid-token, which reads as model truncation. On the
    five stored replies it kept 21 of 40 classes, 16/17, 9/11, 6/6 and 0/6, and those exact
    figures were published as the model's budget. See gen_assembly for the full account.

    Assembly now lives in `gen_assembly.recover_script`, and the recovery report is returned
    alongside so callers can refuse a script that did not come back whole rather than stamp,
    lint and persist a known-broken one.
    """
    recovered = gen_assembly.recover_script(content or "")
    test_code = recovered["test_code"]
    if test_code:
        test_code = _strip_fill_markers(test_code.strip() + "\n")
    library = recovered["library"]
    if library:
        library = {"name": library["name"],
                   "code": _strip_fill_markers(library["code"].strip() + "\n")}
    report = dict(recovered["report"])
    # Cross-check against the script's own ts.add_testCase(...) manifest: the one
    # completeness signal that does not come from this parser.
    report["manifest"] = gen_assembly.manifest_check(test_code or "")
    # Say WHY an unrecoverable reply was unrecoverable (Phase 7.8). Diagnosis only — there is
    # deliberately no repair path for a fence inside a string literal; see the long note on
    # gen_assembly.diagnose_unrecoverable.
    if not report.get("parses"):
        report["diagnosis"] = gen_assembly.diagnose_unrecoverable(content or "", test_code or "")
    return {"test_code": test_code, "library": library, "report": report}


def _recovery_failure(report: Dict[str, Any]) -> str:
    """Human-readable reason a multi-part reply could not be reassembled, else "".

    Reviewed with Terrence 2026-08-04 — two reasons were added, both on the principle that
    the assembler acts on objective evidence and escalates real ambiguity:

      * `ambiguous_units` — two definitions of one name that are genuinely comparable, so
        neither is demonstrably the right one. Deciding by a margin is fine (see
        `_DUPLICATE_OBVIOUS_FACTOR`); deciding by a coin-flip is not.
      * `blocks_after_runner` — a fenced block after `ts.run(sys.argv)`. Never observed, so
        refusing is free, and it beats quietly discarding code the model meant to include.
    """
    manifest = report.get("manifest") or {}
    ambiguous = report.get("ambiguous_units") or []
    after_runner = report.get("blocks_after_runner") or 0
    if report.get("parses") and manifest.get("ok") and not ambiguous and not after_runner:
        return ""
    bits = [f"the reply arrived in {report.get('parts')} parts and reassembly did not "
            f"produce a complete script"]
    if ambiguous:
        bits.append(
            "these classes are defined twice with no clear winner, so the assembler will not "
            "choose between them: " + ", ".join(ambiguous[:10]))
    if after_runner:
        bits.append(
            f"{after_runner} fenced python block(s) appear AFTER ts.run(sys.argv), which is "
            f"the last statement a script can have — the reply's structure is not understood, "
            f"and guessing whether that code belongs in the file risks either dropping real "
            f"code or appending code that runs on import")
    if not report.get("parses"):
        bits.append(report.get("diagnosis") or "the assembled code does not parse as Python")
    if manifest.get("missing"):
        bits.append("these registered test cases are not defined: "
                    + ", ".join(manifest["missing"][:10]))
    if manifest.get("without_main"):
        bits.append("these test cases have no main(): "
                    + ", ".join(manifest["without_main"][:10]))
    if report.get("seam_lines_dropped"):
        bits.append(f"{len(report['seam_lines_dropped'])} partial line(s) were dropped at "
                    f"message seams")
    return "; ".join(bits) + "."


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
    gen_date = utc_now().strftime("%Y-%m-%d")
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


def _setup_keys_for(switches: List[str]) -> List[str]:
    """The .setup [switch] KEYS the bound variables look up, positionally.

    Two layers, and conflating them is what broke the first generated scripts
    (2026-07-28): the LOOKUP STRING must match the .setup file's `[switch]` key, while the
    local VARIABLE carries the role. Real ART code does exactly this:

        dutA   = setup.init_swi('swi_a')
        swiSrc = setup.init_swi('swi_c')

    The convention is swi_a/swi_b/... — 621 of ~650 corpus `init_swi()` calls, and what a
    real testbox declares (tb470's `[switch]` is swi_a/swi_b/swi_c/swi_d as of 2026-07-30).
    Generating `init_swi('dut')` from a role name instead means the lookup simply fails on
    any real .setup. A name that ALREADY looks like a .setup key is passed through unchanged.

    Binding a role successfully is NOT the same as being able to RUN: the bench also has to
    declare the [portlink]s the script asks for, and `init_portlink` returns (None, None)
    silently when it does not. `tool/pt_preflight.py` checks that offline before a run.
    """
    keys: List[str] = []
    letters = "abcdefghijklmnop"
    nxt = 0
    for name in switches:
        if _SWI_RX.match(name):                  # already a .setup-style key
            keys.append(name)
            continue
        while nxt < len(letters) and f"swi_{letters[nxt]}" in keys:
            nxt += 1
        keys.append(f"swi_{letters[nxt]}" if nxt < len(letters) else name)
        nxt += 1
    return keys


# Bound in init() but not a DEVICE the model reaches with `self.testSet.<name>.cmd(...)`.
# `ck_far_port` is the far end of the bound link — a SwitchPort, not a switch.
_NON_DEVICE_BOUND_ATTRS = frozenset({"ck_far_port"})


def _skeleton_bound_devices(skeleton: str, dut: str = "") -> List[str]:
    """The device names `TestSet.init()` ACTUALLY binds, read from the rendered skeleton.

    PHASE 7.8. Rule 3 of the generate prompt renders this as "init binds: ...", and it used
    to be handed `_detect_topology`'s raw switch list — which is NOT what gets bound. The
    skeleton caps the bound set at the DUT plus one partner (`switches[:2]`, with the
    remainder recorded as `dropped_switches`), so the prompt was wrong in BOTH directions:

        _detect_topology  -> ['swi_a', 'swi_b', 'swi_c']      what the prompt claimed
        skeleton binds    -> ['swi_a', 'swi_b', 'tb']         what init() really does

    Naming a dropped device invites `self.testSet.swi_c`, which earns the BLOCKING lint
    "uses device `swi_c` but init() never binds `self.swi_c`" — our own prompt producing an
    error the reviewer cannot override. In the other direction the testbox `tb` is bound and
    was never mentioned, so the model could not use it.

    Reading the rendered skeleton rather than re-deriving the cap keeps one authority: the
    frame that does the binding. A second copy of `switches[:2]` here would be free to drift
    from the template's.

    `dut` is placed first when given — the prompt uses `bound_devices[0]` as the device in
    its worked example, and source order puts `self.tb` (the testbox) first.
    """
    import ast as ast_mod
    try:
        tree = ast_mod.parse(skeleton)
    except SyntaxError:
        return []
    names: List[str] = []
    for node in ast_mod.walk(tree):
        if not (isinstance(node, ast_mod.FunctionDef) and node.name == "init"):
            continue
        for sub in ast_mod.walk(node):
            if not isinstance(sub, ast_mod.Assign):
                continue
            targets: List[Any] = []
            for t in sub.targets:
                # `(dut.portA, self.ck_far_port, lp) = self._ck_bind_link(...)`
                targets.extend(t.elts if isinstance(t, (ast_mod.Tuple, ast_mod.List)) else [t])
            for t in targets:
                if (isinstance(t, ast_mod.Attribute)
                        and isinstance(t.value, ast_mod.Name) and t.value.id == "self"
                        and t.attr not in _NON_DEVICE_BOUND_ATTRS
                        and t.attr not in names):
                    names.append(t.attr)
    if dut and dut in names:
        names.remove(dut)
        names.insert(0, dut)
    return names


# parents[2]=CK_server (cf. _TEMPLATES_DIR), [3]=CK-main, [4]=ask-ck, [5]=repo root.
_MEDIA_HELPER_SRC = Path(__file__).resolve().parents[4] / "tool" / "pt_media.py"
# The workdir filename the generated script imports. Must match the template's `import`.
MEDIA_HELPER_NAME = "ck_media.py"

_FIBRE_HINT_RX = re.compile(
    r"\b(fibre|fiber|optical|optic|single-?mode|multi-?mode|"
    r"\d+base-(?:sx|lx|lh|sr|lr|er|zx|bx|fx))\b", re.I)


def _detect_link_role(sequence: List[dict], objective: str = "") -> str:
    """Which MEDIA role this case's link must be — `'copper'` or `'fibre'`.

    Defaults to copper, and that default is SAFE rather than a guess: MDI/MDIX and the
    10/100 speed range exist only on twisted pair, which is what the great majority of port
    cases exercise. Crucially, a wrong choice cannot produce a wrong verdict — the run-time
    media assertion (`_ck_bind_link` -> `ck_media`) refuses to proceed when the bound port's
    pluggable disagrees, and says the BENCH is at fault. So the failure mode is a loud stop,
    never a silent false pass.
    """
    blob = " ".join([objective or ""] + [
        (s.get("action", "") or "") + " " + (s.get("verify", "") or "") for s in (sequence or [])])
    return "fibre" if _FIBRE_HINT_RX.search(blob) else "copper"


def _media_helper_source() -> str:
    """The `ck_media.py` shipped alongside a generated script into the run workdir.

    Read from `tool/pt_media.py` rather than duplicated, so the module the testbox executes
    is byte-identical to the one the in-repo tests cover. Not a corpus read (guard_db_only
    is about corpora), and the script imports it as a workdir sibling.

    Fails loudly if the path is wrong: shipping a run WITHOUT this helper would make every
    generated script die on `import ck_media`, so a silent miss is not acceptable.
    """
    if not _MEDIA_HELPER_SRC.is_file():
        raise RuntimeError(
            f"media helper not found at {_MEDIA_HELPER_SRC} — generated scripts import it as "
            f"`ck_media`, so a run cannot proceed without it")
    return _MEDIA_HELPER_SRC.read_text(encoding="utf-8")


def _detect_topology(sequence: List[dict], fragments: List[dict]) -> Tuple[List[str], List[str], bool]:
    """Data-driven topology: the switch device names to bind in init(), stacks, and
    whether a port link is needed. Prefers the device names the SELECTED fragments
    actually reference (so the reused code resolves against init()); falls back to any
    swi_*/stk_* seen in the sequence text, then to a sane default. The .setup
    [switch]/[stack] KEYS these look up come from `_setup_keys_for()` — the variable name
    and the lookup string are different layers."""
    blob = " ".join((s.get("action", "") + " " + s.get("verify", "")) for s in sequence)
    blob += " " + " ".join(f.get("code", "") for f in fragments)
    frag_devs = _detect_fragment_devices(fragments)
    swi_literal = sorted(set(_SWI_RX.findall(blob)))
    # Fragment device names first (they're what the reused code calls), then any literal
    # swi_* from the text, else the default pair (most cases are DUT + link partner).
    switches = frag_devs or swi_literal or ["dut", "lp"]
    stacks = sorted(set(_STK_RX.findall(blob)))
    # A PHYSICAL step always needs a port link, whatever its wording says. Its rendered
    # body does `port = dut.portA` and then polls `show interface <port> status`, so
    # without the init_portlink FILL slot `portA` is never bound and the script dies with
    # AttributeError on the first poll iteration (2026-07-28). The keyword scan misses this
    # whenever the step is phrased physically rather than topologically — e.g. "prompt
    # operator to power-cycle the unit" mentions no link at all.
    has_physical = any(_step_kind(s) == "physical" for s in sequence)
    needs_portlink = bool(_PORTLINK_RX.search(blob)) or has_physical
    return switches, stacks, needs_portlink


def _fragment_device_note(fragments: List[dict], bound: List[str]) -> str:
    """Reconciliation note for the artefact + Generate prompt: the device names the
    reused fragments use and what init() binds, so the reviewer/LLM reconciles them
    against the eventual .setup file (which defines the real [switch] names)."""
    frag_devs = _detect_fragment_devices(fragments)
    if not frag_devs:
        return ""
    keys = _setup_keys_for(bound)
    pairs = ", ".join(f"{v} = init_swi('{k}')" for v, k in zip(bound, keys))
    return ("Reused fragments reference these device names: "
            + ", ".join(frag_devs) + ". init() binds them as " + pairs
            + ". The VARIABLE carries the role; the STRING is the .setup [switch] key "
              "(swi_a/swi_b/... — a real testbox declares swi_a/swi_c/swi_d). Keep the "
              "variable names when adapting fragment code so it resolves; do NOT put a "
              "role name inside init_swi(), and never name a port — the .setup [portlink] "
              "lines supply those so the script stays hardware-agnostic.")


def _objective_comment_lines(objective: str, width: int = 88) -> List[str]:
    r"""The refined objective as comment-body lines for the skeleton header — the
    "expected results" this whole script must demonstrate, carried into the emitted .py
    so the generator (and any later reader) never loses the declarative context that the
    per-step action/verify text alone does not carry. Bullets (`<li>` -> `\n- ` in
    _html_to_text) are wrapped independently so the structure survives; blank lines are
    dropped; and `>>>` is neutralised because it is the one marker the generated-script
    linter scans inside comments (an unfilled-placeholder error, _lint_generated §"`>>>`")."""
    out: List[str] = []
    for raw in (objective or "").replace(">>>", ">").split("\n"):
        raw = raw.rstrip()
        if raw:
            out.extend(_wrap_comment(raw, width))
    return out


def _render_skeleton(case_key: str, case_title: str, sequence: List[dict],
                     extra_imports: List[str], fragments: Optional[List[dict]] = None,
                     objective: str = "") -> str:
    """Render the standardized ART skeleton (fixed frame + FILL slots) for this case.
    Each TestCase step carries a resolved `kind` (verify/physical/manual) so the template
    renders the right main() pattern (CLI check vs operator-prompt-and-wait vs yesNo).

    `objective` (the refined case's expected results) is emitted as a comment header so the
    context rides into the .py artifact AND into the Generate prompt (which embeds this
    skeleton) — the fix for verdicts drifting away from what the case actually asks."""
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
                      switches=switches, stacks=stacks, needs_portlink=needs_portlink,
                      setup_keys=_setup_keys_for(switches),
                      link_role=_detect_link_role(sequence, objective),
                      objective_lines=_objective_comment_lines(objective))


def _assemble_fragment_preview(case_key: str, case_title: str, sequence: List[dict],
                               extra_imports: List[str], fragments: List[dict],
                               objective: str = "") -> str:
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

    skeleton = _render_skeleton(case_key, case_title, sequence, extra_imports, fragments,
                                objective)

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


def _cli_reference_for_text(text: str, product: Optional[str] = None,
                            max_output_lines: int = 14) -> str:
    """Real AlliedWare Plus CLI syntax + sample output for the commands `text` mentions.

    Why this exists: both LLM steps were asked to name exact CLI fields while being shown
    ZERO examples of real switch output, so they invented a `speed=1000` / `state=up`
    key=value schema. The switch actually prints
    `current duplex full, current speed 1000, current polarity mdix`, so those assertions
    can never match real hardware. Grounding both prompts in the harvested reference is
    the fix; see PLAN-pytest-testing.md §11.

    Used at BOTH ends of the pipeline, because the fabrication originates at step 2 and
    step 6 merely propagates it (T33235: 13 key=value in the sequence -> 57 in the
    script). Grounding step 6 alone would leave the generator arguing with its own
    skeleton, which repeats the invented format 4x per TestCase.

    Scoped, not dumped: only commands the text actually references are injected. Returns
    "" when the harvest has not run or nothing matches — grounding is an enhancement and
    must never block the pipeline.
    """
    try:
        import sys as _sys
        # routers/ -> CK_server/ -> CK-main/ -> ask-ck/ -> repo root
        tool_dir = str(Path(__file__).resolve().parents[4] / "tool")
        if tool_dir not in _sys.path:
            _sys.path.insert(0, tool_dir)
        import cli_lookup
    except Exception:
        return ""
    try:
        cmds = cli_lookup.detect_commands(text)
        # Features named in PROSE have no lexical path to their command tree, so the
        # literal matcher misses them entirely (2026-07-28). Four steps across
        # T33233/T33234 said "Enable EcoMode on the port" / "lpi disable on <port>" and
        # got either nothing or — worse — a grounded `show interface` variant with no EEE
        # field at all, while being told to match the reference exactly and invent
        # nothing. That steered them into asserting link state only: a false green
        # whenever the disable silently fails, which is what criterion 4 flagged. The
        # `ecofriendly` tree was in ck.db the whole time.
        feat_cmds, feat_terms = cli_lookup.feature_commands(text)
        cmds = cmds + [c for c in feat_cmds if c not in cmds]
        if not cmds:
            return ""
        # feature_terms also steers VARIANT choice: `show interface` reports LPI on only
        # 3 of 8 families, so breadth alone shipped the variant that omits it.
        return cli_lookup.prompt_block(cmds, product,
                                       max_output_lines=max_output_lines,
                                       feature_terms=feat_terms)
    except Exception as e:                       # never fail the step over grounding
        print(f"[pt] CLI reference unavailable: {e}")
        return ""


def _cli_reference_block(sequence: List[dict], fragments: List[dict],
                         product: Optional[str] = None) -> str:
    """Step-6 grounding: commands named by the reviewed sequence + approved fragments."""
    text = " ".join(
        [(s.get("action") or "") + " " + (s.get("verify") or "") for s in sequence]
        + [(f.get("code") or "") for f in fragments])
    return _cli_reference_for_text(text, product)


def _cli_reference_for_case(fields: dict, product: Optional[str] = None) -> str:
    """Step-2 grounding: commands named by the REFINED objective + Zephyr steps.

    Reads the same `_case_payload_fields` dict the prompt itself renders, so the
    grounding can never see different text than the model does. (The raw `zephyr_cases`
    row is NOT usable here — T33235's is an empty Draft, 29 chars of title, while its
    refined objective is 698 chars with 6 real steps.) Output is capped shorter than
    step 6's: the extract prompt is only ~2-4k chars, and 300-800 is proportionate.
    """
    text = re.sub(r"<[^>]+>", " ", fields.get("objective") or "") + " " + " ".join(
        (s.get("description") or "") + " " + (s.get("expectedResult") or "")
        for s in (fields.get("steps") or []))
    return _cli_reference_for_text(text, product, max_output_lines=8)


def _coverage_report(sequence: List[dict], source_steps: List[dict]) -> dict:
    """Which source Zephyr steps does this sequence actually exercise?

    THE INVARIANT (Terrence, 2026-07-27): every objective links to a Zephyr step, and
    every Zephyr step needs at least one PyTest step — otherwise the objective is not
    being tested. A dropped source step is silent: the sequence just looks tidier.

    Real regression this catches: a re-extraction of T33234 went 14 -> 9 steps and
    dropped source step 4 entirely — "configure one side to Auto and the other to forced
    MDI/MDIX ... correct link-down behavior in incompatible combinations", i.e. the whole
    negative path of an MDI/MDI-X test, which the old sequence covered with 4 dedicated
    entries. Nothing absorbed it; it was simply gone.

    Advisory, not fatal: the reviewer must SEE the gap and decide. Blocking would strand
    a case whose source step is genuinely untestable, and step 2 is a human gate anyway.
    """
    total = len(source_steps or [])
    covered: Dict[int, int] = {}
    for s in sequence or []:
        try:
            idx = int(s.get("zephyr_step_idx"))
        except (TypeError, ValueError):
            continue
        if 1 <= idx <= total:
            covered[idx] = covered.get(idx, 0) + 1
    missing = [i for i in range(1, total + 1) if i not in covered]
    return {
        "source_steps": total,
        "covered": sorted(covered),
        "missing": missing,
        "multiplicity": {str(k): v for k, v in sorted(covered.items())},
        "ok": not missing,
        "warning": (
            f"{len(missing)} of {total} Zephyr step(s) have NO sequence entry: "
            f"{missing}. Those parts of the objective would go untested — review before "
            f"confirming."
        ) if missing else "",
    }


def _coverage_gate_error(sess: PtSession, step: int) -> str:
    """Detailed refusal message when confirming would sign off untested source steps.

    Returns "" when coverage is complete. The message QUOTES each uncovered Zephyr step
    rather than listing bare indices — "step 4 is missing" is not actionable, whereas
    the step's own text tells the reviewer exactly which behaviour goes untested. The
    real case this was built for: T33234 silently dropped the MDI/MDI-X forced-polarity
    matrix, i.e. the whole negative path of the feature under test.
    """
    try:
        source_steps = _case_payload_fields(sess)["steps"]
        sequence = (sess.step2 or {}).get("sequence") or []
    except Exception:
        return ""
    cov = _coverage_report(sequence, source_steps)

    lines: List[str] = []
    if not cov["ok"]:
        lines.append(
            f"Cannot confirm '{_step_label(step)}': "
            f"{len(cov['missing'])} of {cov['source_steps']} Zephyr step(s) are not "
            f"tested by any step in this sequence. Every Zephyr step needs at least one "
            f"PyTest step or that part of the objective is not being tested.")
        lines.append("")
        lines.append("UNTESTED source step(s):")
        for idx in cov["missing"]:
            try:
                desc = (source_steps[idx - 1].get("description") or "").strip()
            except (IndexError, AttributeError):
                desc = "(source text unavailable)"
            lines.append(f"  • Zephyr step {idx}: {desc[:300]}")

    # At Generate, also require the script to actually render a case per verify step —
    # the sequence can be complete while the model emitted fewer TestCase classes.
    if step == 6:
        code = (((sess.step6 or {}).get("files") or {}).get("test") or {}).get("code") or ""
        verify_steps = [s for s in sequence if _step_kind(s) != "setup"]
        n_cases = len(re.findall(r"^class TestCase_\d+\(", code, re.M))
        if verify_steps and n_cases < len(verify_steps):
            if lines:
                lines.append("")
            lines.append(
                f"Cannot confirm '{_step_label(step)}': the generated script has "
                f"{n_cases} TestCase class(es) for {len(verify_steps)} non-setup "
                f"sequence step(s) — {len(verify_steps) - n_cases} step(s) have no test "
                f"case, so they will never run.")
            missing_cases = [s for s in verify_steps[n_cases:]][:8]
            if missing_cases:
                lines.append("")
                lines.append("Sequence step(s) with no TestCase:")
                for s in missing_cases:
                    lines.append(f"  • step {s.get('n')}: "
                                 f"{(s.get('action') or '')[:200]}")

    if not lines:
        return ""
    lines.append("")
    lines.append("Fix the sequence (edit or re-extract) and regenerate, or re-confirm "
                 "with acknowledge_coverage_gap=true if the step is genuinely "
                 "untestable.")
    return "\n".join(lines)


# PHASE 7.8 — WHICH LINT ERRORS A HUMAN MAY OVERRIDE.
#
# The only lint error that has ever fired on a real generation was on T44297, the best script
# we have produced: "calls setup.init_portlink() directly, which skips the run-time MEDIA
# assertion". The script compiled and ran; it bypassed one of our checks. And the model was
# following the generate prompt, which told it to bind devices in TestSet.init and pointed it
# at init_portlink() (fixed in the same pass). Under a blanket no-override rule that script is
# permanently unconfirmable because of OUR prompt bug — which is the argument for splitting.
#
# The split is by AUTHORITY, not severity:
#   * the artefact provably cannot work  -> nobody's judgement helps. Regenerate.
#   * the script runs but breaks a house rule -> the reviewer is the right authority.
#
# Anything unrecognised is treated as BLOCKING. A new error is therefore strict until someone
# classifies it, rather than silently overridable — and
# tests/test_lint_error_classes.py fails until it is listed, so the choice is explicit.
_POLICY_LINT_MARKERS = (
    "has no self.log()",                       # logging contract
    "has no non-empty",                        # ...no textual verdict
    "self.passed()/self.failed() (empty reason",   # ...empty verdict reason
    "missing a leading",                       # ...provenance tag
    "calls setup.init_portlink() directly",    # house binding idiom; script still runs
)


def _split_lint_errors(errors: List[str]) -> Tuple[List[str], List[str]]:
    """(blocking, policy). Unrecognised errors are blocking — strict by default."""
    blocking, policy = [], []
    for err in errors:
        (policy if any(m in str(err) for m in _POLICY_LINT_MARKERS) else blocking).append(err)
    return blocking, policy


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
        #
        # Generic on purpose (2026-07-28). This used to test three special cases —
        # ">>> FILL" plus two EXACT lines — which let every other marker through:
        # `pass  # >>> remove once …`, `# >>> adjust operator timeout (s) <<<`, and a
        # `# >>> replace …` sitting on any line other than the two spelled out. Those are
        # instructions addressed to the MODEL, so shipping them into a saved, lint-green,
        # executable artefact leaves a human reading `# >>> replace with the real
        # verification condition` next to a verdict that may well be the placeholder.
        # `>>>` appears in no legitimate Python line the skeleton produces, so match it
        # directly and quote the offending line.
        for _i, _line in enumerate(code.splitlines(), 1):
            if ">>>" in _line:
                errors.append(
                    f"contract: unfilled template placeholder on line {_i} — every `>>>` "
                    f"marker is an instruction to you and must be deleted once the slot is "
                    f"filled: {_line.strip()[:80]}")

        # 2a. THE PLACEHOLDER CODE ITSELF, not the comment that used to sit beside it.
        #
        # PHASE 7.8. Until now the ONLY thing detecting an unfilled verification slot was
        # the trailing `# >>> replace with the real condition <<<` marker on the `if False:`
        # line — and that marker could not be stripped server-side precisely BECAUSE it
        # shared a line with code, which is what made it a hard lint error in the first
        # place. Moving the template's markers onto their own comment lines (so the stripper
        # can remove them) would therefore have deleted the detection along with the noise.
        # So detect the placeholder CODE, which is what actually matters: a marker is a
        # comment, but `if False:` is a test that can never pass and `output = ''` is a
        # verdict reached without ever looking at the device.
        #
        # ERRORS, not warnings: both are the "script runs green having tested nothing"
        # shape, and no reviewer judgement makes an unfilled slot into a test.
        for _c in cases:
            _main = next((n for n in _c.body if isinstance(n, ast_mod.FunctionDef)
                          and n.name == "main"), None)
            if _main is None:
                continue
            for _sub in ast_mod.walk(_main):
                # `if False:` / `if True:` — the skeleton's placeholder condition, left in.
                if (isinstance(_sub, ast_mod.If) and isinstance(_sub.test, ast_mod.Constant)
                        and isinstance(_sub.test.value, bool)):
                    errors.append(
                        f"contract: {_c.name}.main() line {_sub.lineno} still branches on "
                        f"`if {_sub.test.value}:` — the skeleton's placeholder verification "
                        f"condition was never replaced, so this step's verdict is fixed "
                        f"before the device is consulted and the test can never "
                        f"{'fail' if _sub.test.value else 'pass'}")
            # `output = ''` that is never reassigned: the observation slot was left empty,
            # so `self.log('OBSERVED: ...')` reports nothing and any verdict built on it is
            # vacuous. The PHYSICAL step shape legitimately seeds `output = ''` before its
            # poll loop and reassigns it inside, so requiring "never reassigned" is what
            # keeps this off a correct script rather than a blanket text match.
            _assigns: Dict[str, List[Any]] = {}
            for _sub in ast_mod.walk(_main):
                if isinstance(_sub, ast_mod.Assign) and len(_sub.targets) == 1 and \
                        isinstance(_sub.targets[0], ast_mod.Name):
                    _assigns.setdefault(_sub.targets[0].id, []).append(_sub)
            for _name, _nodes in _assigns.items():
                if len(_nodes) != 1:
                    continue                      # reassigned somewhere — really used
                _v = _nodes[0].value
                if (isinstance(_v, ast_mod.Constant) and _v.value == ""
                        and _name in ("output", "out", "result")):
                    errors.append(
                        f"contract: {_c.name}.main() line {_nodes[0].lineno} leaves "
                        f"`{_name} = ''` and never reassigns it — the observation slot was "
                        f"not filled, so OBSERVED logs an empty string and the verdict is "
                        f"reached without reading the device")

        # `self.<dev>` used in init() BEFORE the assignment block (2026-07-28). A real bug
        # in the first generated scripts: `init_portlink(self.dut, ...)` ran three lines
        # above `self.dut = dut`, an AttributeError the moment init() is called — so the
        # script cannot run at all. py_compile does not catch it (it is valid syntax) and
        # neither did any structural check. An ERROR, not a warning: it is a guaranteed
        # crash, not a judgement call.
        _init_m = re.search(r"\n    def init\(self.*?(?=\n    def )", code, re.S)
        if _init_m:
            _body = _init_m.group(0).splitlines()
            _first_assign = next(
                (i for i, l in enumerate(_body)
                 if re.match(r"\s*self\.\w+\s*=", l)), None)
            if _first_assign is not None:
                for _off, _line in enumerate(_body[:_first_assign]):
                    if "self." in _line.split("#", 1)[0]:
                        errors.append(
                            f"init(): uses `self.` before the self.<dev> assignment block "
                            f"(line {_off} of init) — AttributeError at runtime; use the "
                            f"local variables there: {_line.strip()[:70]!r}")
                        break

        # Hardcoded port names (2026-07-28; index semantics corrected the same day against a
        # live 8-member x950 stack, which reported port1.0.x-port8.1.x). In `portA.B.C`,
        # A is the STACK MEMBER (1 standalone, 1-8 across a stack), B is the BAY (0 = base
        # board, 1+ = a populated expansion slot), C the port. A literal `'port1.0.1'` is
        # therefore wrong on a chassis or a populated-slot x950 (`port1.1.x`) AND on every
        # stack member but the first (`port2.0.x` … `port8.0.x`).
        # It is a runtime property of the hardware, not something the case
        # text implies, so it must come from the .setup topology via the attribute
        # `init_portlink()` binds. The corpus agrees overwhelmingly: 10,578 bound-attribute
        # uses vs 125 literals (and those are mostly negative-test inputs).
        #
        # A WARNING, not an error: `invalidIfRangeList.append('port1.0.1')` is a legitimate
        # literal — a deliberately invalid name fed to a negative test. The reviewer
        # decides; the check exists so a hardcode is never silent.
        # Match the port name anywhere inside a string literal, not just when it fills the
        # whole literal — `dut.cmd('interface port1.1.3')` is just as hardcoded as
        # `port = 'port1.0.1'`, and anchoring on the quotes missed it.
        #
        # Comments are skipped: prose ABOUT port naming is not a hardcode, and the check
        # otherwise flags the skeleton's own guidance comment where it quotes an example
        # (it did exactly that on first run — a warning against its own advice).
        _port_literal_rx = re.compile(
            r"""['"][^'"\n]*\bport\d+\.\d+\.\d+\b[^'"\n]*['"]""")
        # Descriptive text is not a device reference. `testCaseDesc`/`testCaseMethod` are
        # echoed from the sequence step, and a passed()/failed() reason quotes the step's
        # own verify wording — if the reviewer wrote "show interface port1.0.1" there, the
        # port name is DOCUMENTATION. Flagging those buried the real signal under ~30 false
        # positives per script (measured 2026-07-28), and a warning nobody can trust gets
        # ignored. Only lines that actually drive the device or bind a port matter.
        _prose_rx = re.compile(
            r"^\s*(?:testCaseDesc|testCaseMethod|testCaseRef)\s*=|"
            r"^\s*self\.(?:log|passed|failed)\s*\(")
        for _i, _line in enumerate(code.splitlines(), 1):
            if _line.lstrip().startswith("#"):
                continue
            if _prose_rx.match(_line):
                continue
            # Find literals first, THEN drop trailing comments — splitting on '#' first
            # would corrupt a string that legitimately contains one.
            for m in _port_literal_rx.finditer(_line):
                if "#" in _line[:m.start()]:
                    continue                     # the match sits in a trailing comment
                warnings.append(
                    f"port name hardcoded as {m.group(0)} at line {_i} — take it from "
                    f"the .setup topology (e.g. `port = dut.portA` bound by "
                    f"init_portlink). The first index is the stack member and the second "
                    f"the bay, so a literal is wrong on every stack member but the first "
                    f"and on a chassis or populated-slot x950 (port1.1.x)")

        # 2b. Imports the TESTBOX's python3 will not have. The script runs there, not here.
        errors.extend(_removed_stdlib_imports(tree))

        # 2b-0. The MEDIA ASSERTION must be on the only path to a bound port.
        #
        # `_ck_bind_link()` (fixed frame) resolves the bench's `[misc] ck_link_<role>`,
        # binds it, and asserts the bound port's media before the test uses it. That last
        # part cannot be checked offline — media belongs to the pluggable, and the CLI
        # accepts `polarity`/`speed 100` on a fibre port where they are meaningless, so a
        # run bound to the wrong media reports a PRODUCT failure that is really a cabling
        # error (TOPOLOGY-PROFILES.md). A script that calls `init_portlink()` directly
        # therefore gets a port with no media guarantee, which defeats the whole mechanism.
        #
        # Two errors, both about the same invariant:
        #   (a) a direct init_portlink() OUTSIDE the helper — bypasses the assertion;
        #   (b) reading a bound port attribute while never calling the helper — the port is
        #       unbound, so this dies with AttributeError on first use (seen 2026-07-28).
        _helper = "_ck_bind_link"
        _helper_def = next((n for n in ast_mod.walk(tree)
                            if isinstance(n, ast_mod.FunctionDef) and n.name == _helper), None)
        _helper_lines = (set(range(_helper_def.lineno, (_helper_def.end_lineno or
                                                        _helper_def.lineno) + 1))
                         if _helper_def else set())
        _calls_helper = any(
            isinstance(n, ast_mod.Call) and (
                (isinstance(n.func, ast_mod.Attribute) and n.func.attr == _helper)
                or (isinstance(n.func, ast_mod.Name) and n.func.id == _helper))
            for n in ast_mod.walk(tree))
        for _n in ast_mod.walk(tree):
            if not (isinstance(_n, ast_mod.Call) and isinstance(_n.func, ast_mod.Attribute)
                    and _n.func.attr == "init_portlink"):
                continue
            if _n.lineno in _helper_lines:
                continue                      # the helper's own, sanctioned, call
            errors.append(
                f"line {_n.lineno}: calls setup.init_portlink() directly, which skips the "
                f"run-time MEDIA assertion. Bind through `self.{_helper}(setup, <dut>, misc, "
                f"'<role>')` instead — a port bound without that check can be the wrong media, "
                f"and the resulting failure reads as a product defect rather than a cabling "
                f"error. See ask-ck/pytest-create/TOPOLOGY-PROFILES.md")
        if not _calls_helper:
            _port_attr_rx = re.compile(r"\.port[A-Z]\w*\b")
            for _i, _line in enumerate(code.splitlines(), 1):
                if _i in _helper_lines or _line.lstrip().startswith("#"):
                    continue
                _m = _port_attr_rx.search(_line.split("#")[0])
                if _m:
                    errors.append(
                        f"line {_i}: reads `{_m.group(0).lstrip('.')}` but the script never "
                        f"calls `self.{_helper}(...)`, so no port link is ever bound — this "
                        f"dies with AttributeError the first time the attribute is read")
                    break

        # 2b-0b. A body referencing a device init() never bound.
        #
        # The counterpart to capping the bound device set at DUT + one partner (template,
        # 2026-07-30). Dropping a device that was only ever inferred from a fragment's
        # variable vocabulary is safe ONLY if using it fails at generation instead of on
        # hardware: `self.linkP.cmd(...)` is valid Python and compiles, so without this the
        # run dies with AttributeError halfway through a booked bench slot.
        _bound = {t.attr for n in ast_mod.walk(tree) if isinstance(n, ast_mod.Assign)
                  for t in n.targets
                  if isinstance(t, ast_mod.Attribute) and isinstance(t.value, ast_mod.Name)
                  and t.value.id == "self"}
        # Tuple-unpacked binds — `(dut.portA, self.ck_far_port, lp) = ...`
        for _n in ast_mod.walk(tree):
            if isinstance(_n, ast_mod.Assign):
                for _t in _n.targets:
                    if isinstance(_t, (ast_mod.Tuple, ast_mod.List)):
                        for _el in _t.elts:
                            if (isinstance(_el, ast_mod.Attribute)
                                    and isinstance(_el.value, ast_mod.Name)
                                    and _el.value.id == "self"):
                                _bound.add(_el.attr)
        _DEV_VERBS = {"cmd", "mode", "reboot", "portReset", "configurePort", "link",
                      "portA", "portB", "name"}
        _unbound_seen = set()
        for _n in ast_mod.walk(tree):
            if not isinstance(_n, ast_mod.Attribute):
                continue
            _v = _n.value
            # shape A: self.testSet.<dev>
            if (isinstance(_v, ast_mod.Attribute) and _v.attr == "testSet"
                    and isinstance(_v.value, ast_mod.Name) and _v.value.id == "self"):
                _dev = _n.attr
            # shape B: self.<dev>.<device verb>
            elif (_n.attr in _DEV_VERBS and isinstance(_v, ast_mod.Attribute)
                    and isinstance(_v.value, ast_mod.Name) and _v.value.id == "self"):
                _dev = _v.attr
            else:
                continue
            if _dev in _bound or _dev in _unbound_seen or _dev.startswith("_"):
                continue
            _unbound_seen.add(_dev)
            errors.append(
                f"line {_n.lineno}: uses device `{_dev}` but init() never binds "
                f"`self.{_dev}` — this compiles and then dies with AttributeError on the "
                f"testbox. A test binds the DUT plus ONE partner (the far end of its single "
                f"link); a second partner needs a second link role declared in "
                f"TOPOLOGY-PROFILES.md, not an extra init_swi()")

        # 2b-ii. The same port attribute bound by two init_portlink() calls. Each call
        # ASSIGNS the attribute, so the second silently discards the first link — the script
        # then drives one topology while believing it has two. Observed 2026-07-28: the model
        # emitted `(dut.portA, tb.ethA) = ...` followed by `(dut.portA, lp.portA) = ...`,
        # losing the testbox link entirely. An ERROR: the test cannot be measuring what it
        # claims, and nothing downstream would reveal it.
        _pl_binds: Dict[str, List[int]] = {}
        for _i, _line in enumerate(code.splitlines(), 1):
            if "init_portlink" not in _line or _line.lstrip().startswith("#"):
                continue
            lhs = _line.split("=")[0]
            for _m in re.finditer(r"\b(\w+\.port[A-Za-z]\w*)\b", lhs):
                _pl_binds.setdefault(_m.group(1), []).append(_i)
        for attr, lines in _pl_binds.items():
            if len(lines) > 1:
                errors.append(
                    f"init(): `{attr}` is bound by init_portlink() on lines "
                    f"{', '.join(map(str, lines))} — the later call DISCARDS the earlier "
                    f"link, so one of those topologies is silently missing. Use a distinct "
                    f"attribute per link (portA, portB, …).")

        # 2b-iii. `eth0` driven as if it were a switchport (2026-07-28, observed on a live
        # x950 stack). eth0 is the out-of-band MANAGEMENT interface: `show interface eth0
        # status` reports `Vlan: none` and it belongs to no VLAN, so it sits outside the
        # switching fabric entirely. It nonetheless appears in `show interface status`,
        # `show interface brief` and `show ip interface brief` as an ordinary connected
        # row — which is precisely how it gets swept into a port test by accident.
        # Switchport/VLAN/port-level config does not apply to it and asserting on it proves
        # nothing about the fabric.
        #
        # A WARNING, not an error: READING eth0 is a legitimate management-reachability
        # check (35 of 830 corpus scripts reference it). Only the reviewer can tell whether
        # a given `interface eth0` meant management or was a misplaced fabric test.
        _eth0_rx = re.compile(r"""['"][^'"\n]*\binterface\s+eth0\b[^'"\n]*['"]""")
        for _i, _line in enumerate(code.splitlines(), 1):
            if _line.lstrip().startswith("#"):
                continue
            for _m in _eth0_rx.finditer(_line):
                if "#" in _line[:_m.start()]:
                    continue
                warnings.append(
                    f"line {_i} enters interface config on `eth0` — that is the "
                    f"out-of-band management port (Vlan: none, outside the switching "
                    f"fabric), so switchport/VLAN/port-level commands do not apply and an "
                    f"assertion on it proves nothing about the fabric. Use a port bound "
                    f"from the .setup topology for fabric tests.")

        # 2b-iv. Enumerating interface rows from device output and then DRIVING the device,
        # with no stackport exclusion (2026-07-28, from a live 8-member x950 stack). On a
        # stack, `show interface status` lists the stack links themselves — they print
        # `stackport` in the Vlan column (port1.0.57 / port1.0.61 on that box). A loop that
        # reads those rows and configures whatever it finds can shut a stack link and SPLIT
        # THE STACK mid-run, which then reads as a product failure rather than a test bug.
        # The corpus already knows the hazard: 40 of 830 scripts mention `stackport`.
        #
        # A WARNING, not an error: the loop may be reading output already scoped to one
        # port, where no stack link can appear. It fires only when the script never mentions
        # `stackport` at all, so adding the guard silences it. A `show` inside the loop is a
        # read and does not count — the risk is config, not inspection.
        if "stackport" not in code:
            for _node in ast_mod.walk(tree):
                if not isinstance(_node, ast_mod.For):
                    continue
                _target = getattr(_node.target, "id", None)
                _iter_dump = ast_mod.dump(_node.iter)
                # Either `for line in out.splitlines():` or a pre-split list that the body
                # then row-parses with `line.split()` — both are the same enumeration idiom.
                _row_parses = any(
                    isinstance(_s, ast_mod.Call)
                    and isinstance(_s.func, ast_mod.Attribute)
                    and _s.func.attr == "split"
                    and getattr(_s.func.value, "id", None) == _target
                    for _s in ast_mod.walk(_node))
                if "splitlines" not in _iter_dump and not _row_parses:
                    continue
                def _cmd_text(_arg) -> str:
                    """The literal head of a command argument.

                    A generated command is rarely a bare constant — the port is interpolated
                    (`'show interface {}'.format(p)`, or an f-string). Reading only
                    ast.Constant classified every such call as config and warned on
                    read-only loops (caught by the guard test, not in review).
                    """
                    if isinstance(_arg, ast_mod.Constant) and isinstance(_arg.value, str):
                        return _arg.value
                    if (isinstance(_arg, ast_mod.Call)
                            and isinstance(_arg.func, ast_mod.Attribute)
                            and _arg.func.attr == "format"):
                        return _cmd_text(_arg.func.value)
                    if isinstance(_arg, ast_mod.JoinedStr):     # f-string: take its head
                        for _p in _arg.values:
                            if isinstance(_p, ast_mod.Constant) and isinstance(_p.value, str):
                                return _p.value
                    if isinstance(_arg, ast_mod.BinOp) and isinstance(_arg.op, ast_mod.Mod):
                        return _cmd_text(_arg.left)             # legacy `'...%s' % x`
                    return ""

                _drives = False
                for _sub in ast_mod.walk(_node):
                    if not (isinstance(_sub, ast_mod.Call)
                            and isinstance(_sub.func, ast_mod.Attribute)
                            and _sub.func.attr in ("cmd", "mode")):
                        continue
                    _arg = _sub.args[0] if _sub.args else None
                    if not _cmd_text(_arg).strip().lower().startswith("show"):
                        _drives = True
                        break
                if _drives:
                    warnings.append(
                        f"line {_node.lineno} iterates interface rows from device output "
                        f"and then drives the device, with no `stackport` exclusion — on a "
                        f"stack, `show interface status` lists the stack links themselves "
                        f"(their Vlan column reads `stackport`), so this can shut a stack "
                        f"link and split the stack mid-run. Skip rows whose Vlan is "
                        f"`stackport`, or drive only ports bound from the .setup topology.")
                    break

        # 2c. `startswith(port)` when selecting a port's row from a per-port table.
        # `'port1.0.1'` is a prefix of `'port1.0.10'`, so this silently reads the WRONG
        # row whenever the table lists both. The correct test is the first token
        # (`line.split()[:1] == [port]`).
        #
        # A WARNING, not an error: the generated code usually scopes the show command to a
        # single port, so today's output has one row and the prefix match happens to work.
        # It is a latent break that a reviewer widening the command would trigger.
        #
        # Mechanical because prose did not hold (2026-07-28): rule 4d names the antipattern
        # explicitly and the model still emitted `line.strip().startswith(port.name)` — its
        # example showed the `next()` generator form while the model was writing a `for`
        # loop, so the guidance did not transfer across code shapes. Both forms are now in
        # the prompt AND checked here.
        for _i, _line in enumerate(code.splitlines(), 1):
            if _line.lstrip().startswith("#"):
                continue
            if re.search(r"\.startswith\(\s*(?:self\.)?[\w.]*\bport\w*(?:\.name)?\s*[,)]",
                         _line):
                warnings.append(
                    f"line {_i}: `startswith(port…)` selects a port's row by PREFIX, so "
                    f"'port1.0.1' also matches 'port1.0.10' — compare the first token "
                    f"instead (`line.split()[:1] == [port]`): {_line.strip()[:60]}")

        # 3. Framework imports must exist in the surface index (from ck.db — the
        #    single runtime source; no JSON read).
        #
        #    The surface is keyed by MODULE path only ("ATLibrary.ATTools",
        #    "ATLibrary.__init__") — a package never appears as a bare key. So membership
        #    alone rejects every legitimate package import: `from framework import
        #    ATLibrary` and even `from framework.ATDrivers import ATSwitch` were both
        #    errors (2026-07-28). `ATDrivers` only ever passed because it sat in a
        #    hardcoded allowlist, though it is structurally identical to `ATLibrary`.
        #    That misdiagnosed a real import as "a hallucinated framework.ATLibrary" and
        #    held T33235's lint red. Resolve packages from the index instead of listing
        #    them by hand, so the check follows the data.
        surface = dbx.get_json_doc("framework_surface") or {}
        if surface:
            packages = {k.rsplit(".", 1)[0] for k in surface if "." in k}

            def _known(name: str) -> bool:
                """True if `name` names a module or a package inside the surface."""
                return (name in surface
                        or name.replace(".", "/") in surface
                        or name in packages
                        or f"{name}.__init__" in surface)

            for node in ast_mod.walk(tree):
                if isinstance(node, ast_mod.ImportFrom) and node.module:
                    mod = node.module
                    if mod.startswith("framework."):
                        short = mod[len("framework."):]
                        if not _known(short):
                            errors.append(f"imports: framework module '{short}' not found in framework_surface")
                    elif mod == "framework":
                        # Importing a submodule/package off the `framework` package: the
                        # imported name is itself the module path.
                        for a in node.names:
                            if not _known(a.name):
                                errors.append(f"imports: framework.{a.name} not found in framework_surface")

    lib = files.get("library")
    if lib and lib.get("name"):
        lib_name = Path(lib["name"]).stem
        if re.search(rf"\bimport\s+{re.escape(lib_name)}\b|\bfrom\s+{re.escape(lib_name)}\b", code) is None:
            warnings.append(f"library file {lib['name']} provided but never imported")

    # 4. OBJECTIVE COVERAGE (Terrence's invariant, 2026-07-27): every objective links to
    #    a Zephyr step, and every Zephyr step needs at least one PyTest step — otherwise
    #    that part of the objective is not being tested.
    #
    #    Checked HERE as well as at step 2 because a case can legitimately reach Generate
    #    with no reusable scripts at all (T33235: decision 'new', zero fragments), so the
    #    fragment gates prove nothing about coverage. Generate is the last point before a
    #    script exists, and coverage can still be lost after step 2 — a reviewer edits or
    #    deletes a sequence row, or a re-extraction drops a source step (T33234 silently
    #    lost the whole MDI/MDI-X negative path that way, 14 steps -> 9).
    #
    #    Measured against the SEQUENCE, then cross-checked against the TestCase classes
    #    the script actually emitted, so "the sequence covered it but the script skipped
    #    it" is caught too. A warning, not an error: the reviewer decides, and a genuinely
    #    untestable source step must not permanently block generation.
    try:
        cov = _coverage_report((sess.step2 or {}).get("sequence") or [],
                               _case_payload_fields(sess)["steps"])
        result_coverage = cov
        if not cov["ok"]:
            warnings.append(
                f"coverage: Zephyr step(s) {cov['missing']} have no sequence entry — "
                f"that part of the objective is NOT tested by this script")
        # The script must also render a TestCase per verify step; a shortfall means the
        # model dropped steps the sequence did cover.
        #
        # PHASE 7.7 — THIS IS AN ERROR, NOT A WARNING. It is the one check that detects a
        # CLEANLY-PARSING truncated script: a reply cut between classes compiles, passes
        # every structural assertion, and differs from a complete one only in how many
        # TestCases it contains. The plan calls this "the one to fear", and it was
        # advisory — so the artefact that most needs stopping was the one that sailed
        # through. A genuinely untestable SOURCE step is a different question and stays a
        # warning above; this is the script failing to cover a sequence the reviewer
        # already approved.
        verify_steps = [s for s in ((sess.step2 or {}).get("sequence") or [])
                        if _step_kind(s) != "setup"]
        n_cases = len(re.findall(r"^class TestCase_\d+\(", code, re.M))
        if verify_steps and n_cases < len(verify_steps):
            errors.append(
                f"incomplete: {n_cases} TestCase classes for {len(verify_steps)} "
                f"non-setup sequence steps — {len(verify_steps) - n_cases} step(s) have "
                f"no test case in the generated script. The script compiles, so this is "
                f"the only signal that it is short; regenerate rather than confirm it.")
    except Exception as e:
        # NARROWED (Phase 7.7). This used to swallow every exception, including one raised
        # by the completeness check itself — so the check could be dead and the lint would
        # still report ok. A failure to RUN the check is now itself an error: unknown is
        # not the same as clean.
        print(f"[pt] coverage check failed: {type(e).__name__}: {e}")
        errors.append(f"coverage/completeness check could not run ({type(e).__name__}: {e}) "
                      f"— the script has NOT been checked for completeness")
        result_coverage = None

    blocking, policy = _split_lint_errors(errors)
    result = {"ok": not errors, "errors": errors, "warnings": warnings,
              # PHASE 7.7/7.8 — two kinds of error, two different authorities.
              # `blocking` means the artefact provably cannot work (it will not compile, or
              # it dies with AttributeError on the testbox, or it is short). No override.
              # `policy` means the script runs but breaks a house rule — the reviewer is the
              # right authority, so it is overridable WITH A RECORDED REASON.
              "blocking_errors": blocking, "policy_errors": policy,
              "coverage": result_coverage,
              "checked_at": utc_now().isoformat()}
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
        "saved_at": utc_now().isoformat(),
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


def _pt_cases_index() -> Tuple[set, Dict[str, dict]]:
    """(complete_keys, per-case PyTest progress) — the two blocking reads pt_cases
    needs, paired for a single threadpool hop and named so the event-loop AST
    invariant can see what is dispatched (a lambda would hide them)."""
    try:
        pt_prog = dbx.list_pt_progress()
    except Exception as e:
        print(f"Warning: reading pt session progress failed: {e}")
        pt_prog = {}
    return refined_complete_keys(), pt_prog


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
                and not is_hidden_case(c["key"], zephyr.get(c["key"], {}).get("folder", ""))]

    # Off the event loop: refined_complete_keys rglob's the whole refined-cases tree
    # and list_pt_progress hits ck.db. Both were bare here — the same blocking-work-in-
    # an-async-handler bug batch B fixed for the LLM/search sites, missed because the
    # invariant's _BLOCKING list only covered LLM round-trips and embedding entry
    # points, not pure filesystem/DB reads. Widening that list surfaced this.
    complete_set, pt_prog = await run_in_threadpool(_pt_cases_index)
    refined_keys = [k for k in all_keys if k in complete_set]

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
    open_grouped.extend(build_case_groups(not_started_keys, zephyr))

    return {
        "in_progress": {"grouped": open_grouped},
        "complete": {"grouped": build_case_groups(done_keys, zephyr)},
        "counts": {"in_progress": len(open_keys), "complete": len(done_keys),
                   "partials": len(partial_keys)},
    }


@router.post("/load_case/{key}")
async def load_case(key: str, request: Request):
    data = _data(request)
    # Per-case lock (PLAN-auth-and-case-locking.md Phase 1). If another tab/user holds a
    # LIVE lock, serve a read-only snapshot and touch nothing — pt_sessions is shared
    # across tabs in this one process, so _sweep_stale_runs / apply_workspace_llm here
    # would mutate THEIR live object, and the hydration _pt_persist would 409.
    lock = locks.acquire("pt", key)
    if not lock["by_me"]:
        snap = _pt_load(key) or PtSession(key=key)
        fields = _case_payload_fields(snap)
        return {
            "session": safe_session_dict(snap),
            "case_title": _case_title(data, key),
            "group_display": _group_display(snap.group),
            "objective": fields["objective"],
            "steps": fields["steps"],
            "llm_applied_from_workspace": False,
            "lock": lock,
            "read_only": True,
        }

    sess = pt_sessions.get(key) or _pt_load(key)
    if not sess:
        group, payload, trace = _find_refined_case(key)
        sess = PtSession(key=key, group=group, payload=payload, traceability=trace)
    _sweep_stale_runs(sess)
    changed = apply_workspace_llm(sess)
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
        "lock": lock,
        "read_only": False,
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
        # Step 3 alone needs more than those two fields. It moved to a PER-SEQUENCE-STEP
        # picker on 2026-08-26 and BOTH of them stopped being written for new sessions:
        # `matches` comes only from the whole-case POST /suggest_scripts, which left the UI
        # at the same time (see _persist_step_matches), and step 3 has never written
        # `provenance` at all -- only steps 2, 5, 6 and 8 do. So a case driven through the
        # current UI could NOT be confirmed however complete it was (observed: 32/32 steps
        # covered, 34 scripts chosen, still 409), and step 4 was unreachable behind it,
        # since gather_fragments calls _require_confirmed(sess, "step3", ...).
        #
        # The per-step flow's evidence that the step actually RAN is either of:
        #   step_matches -- written per sequence step by _persist_step_matches, and written
        #                   even when that step matched nothing, so it preserves the
        #                   "empty list is a legitimate answer" property this check exists
        #                   for; and
        #   selections   -- scripts chosen by keyword search, which is reachable without
        #                   ever invoking Suggest.
        # Pre-2026-08-26 sessions still pass on `matches` exactly as before.
        if not ran and required_field == "matches":
            ran = bool(content.get("step_matches")) or bool(content.get("selections"))
        if not ran:
            raise HTTPException(409, f"Nothing to confirm yet for '{_step_label(step)}' "
                                     f"(missing {required_field}).")
    elif not content.get(required_field):
        raise HTTPException(409, f"Nothing to confirm yet for '{_step_label(step)}' "
                                 f"(missing {required_field}).")

    # OBJECTIVE-COVERAGE GATE (Terrence's invariant, 2026-07-27): every objective links
    # to a Zephyr step, and every Zephyr step needs at least one PyTest step — otherwise
    # that slice of the objective is not being tested.
    #
    # Enforced HERE rather than at Generate: generation should still produce the script
    # (it is useful to look at, and the reviewer may fix the sequence and regenerate),
    # but confirming is the human signing off that the step is CORRECT — and signing off
    # on a script that silently skips a source step is the thing to prevent.
    #
    # Checked at BOTH gates that can lock coverage in:
    #   '2. Sequence' — the sequence itself dropped a source step
    #   '5. Generate' — reachable with zero reusable fragments (T33235: decision 'new'),
    #                   so the fragment gates prove nothing about coverage; and a reviewer
    #                   can edit or delete a sequence row after step 2 was confirmed.
    # Override with {"acknowledge_coverage_gap": true} once the reviewer has decided the
    # uncovered step is genuinely untestable — a deliberate, recorded choice, not a
    # silent pass.
    if step in (2, 6) and not (body or {}).get("acknowledge_coverage_gap"):
        gap = _coverage_gate_error(sess, step)
        if gap:
            raise HTTPException(409, gap)

    # PHASE 7.7/7.8 — CONFIRMING A SCRIPT REQUIRES A CLEAN LINT, with two authorities.
    #
    # `confirm_step` never looked at the lint at all, so a script with hard errors —
    # including the completeness error that is the only way to spot a cleanly-parsing
    # truncated script — could be signed off and carried into the run and export stages.
    # Confirming is a human asserting the step is CORRECT; it must not be possible while
    # the machine checks say it is not.
    #
    # But not every error is the same kind of thing (see _POLICY_LINT_MARKERS). A script
    # that cannot compile, or that dies with AttributeError on the testbox, or that covers
    # fewer steps than the approved sequence, is broken and no judgement helps — regenerate.
    # A script that runs but breaks a house rule is the reviewer's call, so it is overridable
    # with a REASON that is recorded on the session, matching how the objective-coverage gap
    # beside this already works.
    if step == 6:
        lint = (getattr(sess, "step6", None) or {}).get("lint") or {}
        if not lint:
            raise HTTPException(409, "Lint the generated script before confirming it.")
        # Older sessions were linted before the split existed; fall back to treating every
        # recorded error as blocking rather than silently letting them all through.
        blocking = lint.get("blocking_errors")
        if blocking is None:
            blocking, _ = _split_lint_errors(lint.get("errors") or [])
        if blocking:
            raise HTTPException(
                409, "This script has errors that cannot be overridden — regenerate it:\n  - "
                     + "\n  - ".join(str(e) for e in blocking[:10]))
        policy = lint.get("policy_errors")
        if policy is None:
            _, policy = _split_lint_errors(lint.get("errors") or [])
        if policy:
            reason = str((body or {}).get("acknowledge_lint_policy") or "").strip()
            if not reason:
                raise HTTPException(
                    409, "This script breaks house rules that a reviewer may accept. To "
                         "confirm anyway, resend with {\"acknowledge_lint_policy\": "
                         "\"<why>\"} — the reason is recorded on the session:\n  - "
                         + "\n  - ".join(str(e) for e in policy[:10]))
            step6 = getattr(sess, "step6", None) or {}
            acks = list(step6.get("policy_acknowledgements") or [])
            acks.append({"at": utc_now().isoformat(), "reason": reason[:500],
                         "errors": [str(e) for e in policy]})
            step6["policy_acknowledgements"] = acks
            sess.step6 = step6

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
        # Real CLI output formats, so `verify` text quotes what the switch actually
        # prints instead of inventing `speed=1000` — which the skeleton would then
        # stamp into every TestCase 4x over.
        "cli_reference": _cli_reference_for_case(fields),
    }, llm_config=_llm_cfg(sess),
       # This was the ONE LLM step in this router with no explicit timeout, so it
       # silently inherited run_prompt's 180s default while every sibling asked for
       # 300s or 600s. Output here scales with the refined case: one sequence row
       # (action + verify + kind) per Zephyr step, so a rich case is an
       # emit-a-whole-artifact step like generation, not a short analysis step —
       # hence 600s, matching generate_script rather than the 300s of the analysis
       # steps. Found the hard way: a 42-step case timed out at exactly 180s on
       # every attempt (2026-07-30), which reads as an LLM fault rather than a
       # missing kwarg because the error text is the CLI's own timeout message.
       timeout=600, dry_run=dry_run)
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
    # Every Zephyr step must map to >=1 sequence step, or that slice of the objective is
    # untested. Surfaced to the reviewer rather than enforced silently.
    coverage = _coverage_report(sequence, fields["steps"])
    if not coverage["ok"]:
        print(f"[pt] {key} coverage gap — {coverage['warning']}")
    sess.step2 = {"sequence": sequence, "notes": notes,
                  "coverage": coverage,
                  "confirmed": False,
                  "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                                 "prompt": meta.get("prompt", ""),
                                 "response": meta.get("content", "")[:20000]}}
    _invalidate_from(sess, 2)
    _pt_persist(sess)
    return {"sequence": sequence, "notes": notes, "coverage": coverage}


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
    # Re-check coverage on manual edits too — deleting a row in the UI can drop the last
    # entry covering a Zephyr step just as easily as the LLM can.
    coverage = _coverage_report(sequence, _case_payload_fields(sess)["steps"])
    sess.step2 = {**(sess.step2 or {}), "sequence": sequence,
                  "coverage": coverage, "confirmed": False}
    _invalidate_from(sess, 2)
    _pt_persist(sess)
    return {"sequence": sequence, "coverage": coverage}


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


# Fields of a step-3 match record worth persisting on the session. A whitelist,
# not the whole record: mechanical-search rows drag scoring internals along, and
# the session payload is the permanent ck.db row — keep it to what the UI renders
# and downstream prompts consume.
_MATCH_PERSIST_FIELDS = ("id", "title", "db", "coverage", "reason", "covers_steps")


def _match_slim(m: dict) -> dict:
    return {k: m[k] for k in _MATCH_PERSIST_FIELDS if k in m}


def _persist_step_matches(sess: PtSession, step_n: int, matches: List[dict]) -> None:
    """Merge one step's LLM suggestions into step3.step_matches and persist.

    Why (2026-08-26, Terrence): per-step suggestions used to live only in browser
    JS — a hard reload lost the candidates AND degraded already-chosen rows to
    db='other' / coverage='?' because nothing server-side held their records. The
    whole-case suggest DID persist (step3.matches), but it left the UI on
    2026-08-20-ish, so nothing persisted at all. Merge is by id with the newest
    verdict winning, so a re-suggest refreshes coverage/why without dropping
    candidates the page already showed.

    Deliberately does NOT unconfirm step 3 and does NOT _invalidate_from(3):
    candidates are not selections — only save_matches changes what downstream
    consumes, and it keeps its invalidation.
    """
    step3 = sess.step3 or {}
    sm = dict(step3.get("step_matches") or {})
    merged = {m0.get("id"): _match_slim(m0) for m0 in (sm.get(str(step_n)) or [])
              if isinstance(m0, dict) and m0.get("id")}
    for m0 in matches or []:
        if isinstance(m0, dict) and m0.get("id"):
            merged[m0["id"]] = _match_slim(m0)
    sm[str(step_n)] = list(merged.values())
    sess.step3 = {**step3, "step_matches": sm}
    _pt_persist(sess)


@router.post("/suggest_scripts_step/{key}/{step_n}")
async def suggest_scripts_step(key: str, step_n: int, request: Request,
                               body: dict = Body(default={})):
    """Per-step LLM suggestion: rank scripts against ONE sequence step's action/verify.

    Unlike the global suggest (which fans matches out across the whole sequence), this
    scopes the LLM to a single step so a reviewer can fill a specific gap. Every returned
    match is linked to this step by construction (covers_steps forced to [step_n]); the
    frontend drops them into that step's candidate list. Persisted to
    step3.step_matches[step] (2026-08-26) so suggestions — and their coverage/why
    verdicts — survive a reload and a closed browser; the reviewer still chooses
    per step and saves the map via save_matches.
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
        # AN ERROR IS NOT "NO MATCHES" (2026-08-26). This used to swallow LLM
        # failures into a 200 with matches=[], so a backend outage — and now a
        # user's Stop — read as "the LLM found nothing for this step". Same
        # silent-degradation shape gather_fragments already fails loudly on.
        # The whole-case suggest keeps its documented mechanical fallback; this
        # per-step path has no fallback to offer, so say what happened.
        if meta.get("error"):
            raise HTTPException(502, meta.get("content", "LLM error"))
        parsed = extract_json_block(meta.get("content", ""))
        valid_ids = {c["id"] for c in candidates}
        llm_matches = [m for m in _parsed_list(parsed, "matches")
                       if isinstance(m, dict) and m.get("id") in valid_ids
                       and m.get("coverage") in ("full", "partial")]

    mech_by_id = {c["id"]: c for c in mech}
    # Force covers_steps to this step — every result is linked to it by construction.
    matches = [{**mech_by_id.get(m["id"], {"id": m["id"]}), **m, "covers_steps": [step_n]}
               for m in llm_matches]
    # Record what was actually sent. step3 was the ONE LLM step storing no provenance:
    # steps 2, 5 and 6 all write {llm, prompt, response}, and the step-3 panel seeded from
    # `step3.provenance` — a key only the retired whole-case suggest ever wrote. So for any
    # session driven through the per-step picker the panel was permanently blank, and there
    # was no way to see what a suggest had sent after the fact (2026-08-31).
    #
    # ONE slot, not one per sequence step: this payload is a row in the permanent ck.db,
    # and a 32-step case would otherwise carry 32 prompts. `step_n` records which step this
    # was; any OTHER step's prompt is a Refresh away and costs nothing to render.
    # Set before _persist_step_matches, which spreads the current step3 and persists.
    if candidates:
        sess.step3 = {**(sess.step3 or {}),
                      "provenance": {"llm": {k: meta.get(k) for k in
                                             ("provider", "model", "auth_method")},
                                     "prompt": meta.get("prompt", ""),
                                     "response": meta.get("content", "")[:20000],
                                     "step_n": step_n}}
    _persist_step_matches(sess, step_n, matches)
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
    # Record snapshots for the chosen ids (2026-08-26): keyword-search picks have
    # no LLM verdict persisted anywhere, so after a reload a chosen row degraded
    # to db='other' / coverage='?' / empty why. The client sends its cached record
    # per chosen id; whitelisted and kept on the session so the chosen tables
    # render with full fidelity forever after.
    recs_in = body.get("records") or {}
    stored = dict((sess.step3 or {}).get("records") or {})
    if isinstance(recs_in, dict):
        for sid, rec in recs_in.items():
            if isinstance(sid, str) and sid and isinstance(rec, dict):
                slim = _match_slim({**rec, "id": sid})
                stored[sid] = slim
    sess.step3 = {**(sess.step3 or {}), "selections": clean, "records": stored,
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
    # Step-3 review context (2026-08-26): which steps chose each script, with what
    # coverage verdict and WHY. Until now scripts reached the fragment prompt as
    # bare symbol lists, so the LLM chose fragments blind to the reasons the
    # scripts were selected at all — the coverage/why the reviewer (and the match
    # LLM) produced in step 3 went nowhere. Per-step verdicts (step_matches) win
    # over whole-case ones (matches), then chosen-record snapshots (records).
    sels_map = (sess.step3 or {}).get("selections") or {}
    step_matches = (sess.step3 or {}).get("step_matches") or {}
    flat_matches = {m.get("id"): m for m in ((sess.step3 or {}).get("matches") or [])
                    if isinstance(m, dict)}
    rec_snaps = (sess.step3 or {}).get("records") or {}
    chosen_steps: Dict[str, list] = {}
    if isinstance(sels_map, dict):
        for n, ids in sels_map.items():
            for sid in ids or []:
                chosen_steps.setdefault(sid, []).append(n)

    def _review_for(sid: str) -> List[dict]:
        out = []
        for n in chosen_steps.get(sid, []):
            m = next((x for x in (step_matches.get(str(n)) or [])
                      if isinstance(x, dict) and x.get("id") == sid), None)                 or flat_matches.get(sid) or rec_snaps.get(sid)
            entry = {"step": n}
            if isinstance(m, dict):
                if m.get("coverage"):
                    entry["coverage"] = m["coverage"]
                if m.get("reason"):
                    entry["why"] = m["reason"]
            out.append(entry)
        return out

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
        scripts_ctx.append({"id": sid, "symbols": symbols, "review": _review_for(sid)})

    # 600s, matching generate_script and fix_script. This prompt carries the whole
    # sequence PLUS every chosen script's symbols and review notes — the largest context
    # in the pipeline — and had half their budget. On claude_agent (the one transport
    # that gets the raw value rather than _cli_timeout's 1800s floor) that was a hard
    # 300s ceiling, hit on 2026-08-27 for AWPTCM-T44191.
    meta = await run_in_threadpool(run_prompt, "pt_gather_fragments.jinja", {
        "case_key": key, "sequence": sequence, "scripts": scripts_ctx,
    }, llm_config=_llm_cfg(sess), timeout=600, dry_run=dry_run)
    if dry_run:
        return _provenance_preview(meta)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    parsed = extract_json_block(meta.get("content", ""))
    # AN UNREADABLE ANSWER IS NOT AN EMPTY ANSWER. extract_json_block returns None when
    # nothing in the reply parses; without this guard that None flowed into _parsed_list,
    # which yields [], which produced `fragments: []` — indistinguishable from the
    # legitimate "this case has no reusable code" outcome, and confirm_step accepts an empty
    # fragment list precisely because that outcome is real. So a corrupted reply was being
    # recorded as a valid finding of no-reuse, and generation then ran with zero fragments
    # while step 3 had selected a dozen scripts.
    #
    # Observed twice on 2026-07-30 (T43869, T44297): the reply arrived truncated at the HEAD,
    # beginning mid-string ('test-1332.1001.py", "symbol": ...'), so it could never parse.
    # extract_sequence already fails loudly in this situation ("LLM returned no sequence");
    # this step just never did. A genuinely empty answer still parses — `{"steps": []}` or
    # per-step `chosen: []` — and still reaches the no-reuse path below, so the loud failure
    # is scoped to unparseable replies only.
    if parsed is None:
        raise HTTPException(502, "Could not parse the fragment reply as JSON (an unreadable "
                                 "answer is not 'no reusable code'). Raw response stored in "
                                 "provenance.")

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
                                         extra_import_lines, fragments,
                                         _case_payload_fields(sess)["objective"])
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

    # Persist the naming BEFORE the LLM call, not only on the success path below.
    # step6.naming had exactly two writers -- the successful tail of this function and
    # save_script (which 409s until a file exists) -- so a generation that timed out or
    # failed reassembly threw the reviewer's typed Group/name away with it, and the field
    # re-seeded from the default on the next render. The naming is the reviewer's input,
    # not an output of the call; it should survive the call failing. Written directly so a
    # later `sess.step6 = {...}` in this function still replaces the whole dict cleanly.
    # ...but never from a dry run: Refresh (no send) is a pure preview and must not write
    # to the session just because someone looked at the prompt.
    _pre = dict(sess.step6 or {})
    if not dry_run and (_pre.get("naming") or {}) != {"group": group, "name": name}:
        _pre["naming"] = {"group": group, "name": name}
        sess.step6 = _pre
        _pt_persist(sess)

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
                                extra_import_lines, fragments,
                                _case_payload_fields(sess)["objective"])

    # SIZE ADVICE, NOT A SIZE GATE (Phase 7.4). This used to raise 409 for any script whose
    # projected output exceeded "32,000 tokens minus thinking". That premise is refuted: the
    # four stored multi-message generations used 34,966 to 67,326 output tokens and every one
    # is a COMPLETE script. 32,000 bounds a single message; the answer simply continues into
    # the next one and is reassembled by gen_assembly.
    #
    # What the gate actually did was refuse large cases outright, and its remediation advice
    # ("about N TestCase classes is the most that fits") was derived from a constant fitted to
    # truncated parser output. The honest replacement is to say how big this is likely to be
    # and let it run — the artefact is checked on ARRIVAL by _recovery_failure, which reasons
    # about what was actually delivered instead of predicting it.
    size = _size_estimate(skeleton, sequence)

    # Device-name reconciliation (finding #1): tell the LLM which names the reused
    # fragments use vs what init() binds, so it renames rather than emitting AttributeErrors.
    bound_devs, _stk, _pl = _detect_topology(sequence, fragments)
    # PHASE 7.8 — what init() BINDS, not what the text mentions. The skeleton caps the set
    # at the DUT plus one partner, so `bound_devs` over-reports (and omits the testbox it
    # does bind); telling the model about a dropped device earns a BLOCKING lint. Read it
    # back off the frame that did the binding — see _skeleton_bound_devices.
    skeleton_devs = _skeleton_bound_devices(skeleton, bound_devs[0] if bound_devs else "")
    # The reconciliation note maps switch VARIABLES onto .setup [switch] KEYS positionally,
    # so it takes the switch names only (never `tb`), narrowed to the ones really bound.
    note_devs = [d for d in bound_devs if d in set(skeleton_devs)] or bound_devs
    device_note = _fragment_device_note(fragments, note_devs)

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
        "bound_devices": skeleton_devs or bound_devs,
        "py2_flagged": py2_flagged,
        "framework_surface": _framework_surface_slice(data, extra_mods),
        # Real CLI syntax + sample output for the commands this case uses, so the model
        # asserts on what the switch actually prints instead of inventing `speed=1000`.
        "cli_reference": _cli_reference_block(sequence, fragments),
        "model_name": llm_cfg.get("model") or "unknown",
        "gen_date": utc_now().strftime("%Y-%m-%d"),
    }, llm_config=llm_cfg, timeout=600, dry_run=dry_run,
       # This template asks for a FENCED python block and _parse_generated_blocks needs the
       # fence to find the code at all — but run_prompt's default system message is the
       # JSON steer, whose text forbids markdown fences. The request was arguing with
       # itself. Same reason on the fix pass below.
       system=_CODE_SYSTEM_PROMPT,
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
    # A reply that spanned several messages and did not reassemble cleanly must NOT be
    # stamped, linted and persisted — that is exactly how a partial script came to be
    # reported as a successful generation for months.
    #
    # BUT THE EVIDENCE MUST SURVIVE THE REFUSAL (found 2026-08-04). The first version raised
    # here, before `sess.step6` was written, so refusing DESTROYED the whole reply — which is
    # precisely the defect Phase 7.9 exists to fix, re-created one layer up: the record meant
    # to capture this class of failure was destroying it, and for the one case where it
    # matters most. So the attempt is recorded first, under its own key so a previously-good
    # script is left intact, and only then is the request refused. Retry is a deliberate,
    # recorded action rather than a hidden second call: the generations that fail this way are
    # the multi-message ones, measured at 326-778s, so an automatic retry would turn a slow
    # request into one of 10-26 minutes that the client abandons.
    failure = _recovery_failure(blocks["report"])
    if failure:
        step6 = dict(sess.step6 or {})
        attempts = list(step6.get("failed_generations") or [])
        attempts.append({
            "at": utc_now().isoformat(),
            "reason": failure,
            "llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
            "prompt": meta.get("prompt", ""),
            "response": meta.get("content", ""),
            "recovery": blocks["report"],
            "rejected_code": blocks["test_code"] or "",
        })
        # Keep the last few attempts, newest last; unbounded growth here would be a second
        # storage problem rather than a forensic record.
        step6["failed_generations"] = attempts[-3:]
        sess.step6 = step6
        _pt_persist(sess)
        raise HTTPException(
            502, f"Generation could not be reassembled: {failure} The full reply is saved "
                 f"under step6.failed_generations for inspection; generate again to retry.")
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
        # Phase 7.9 — the reply is stored WHOLE. It used to be cut at 20,000 chars with no
        # marker, so every stored generation was incomplete and the primary evidence for
        # transport defects was destroyed by the record meant to capture them; the
        # multi-part replies that exposed the fence bug are 37k-173k chars. `recovery` is
        # the assembly audit trail: how many messages the answer spanned, what was dropped
        # at each seam, and the model's own assembly notes.
        "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                       "prompt": meta.get("prompt", ""),
                       "response": meta.get("content", ""),
                       "recovery": blocks["report"]},
    }
    _invalidate_from(sess, 6)
    lint = _lint_generated(sess)
    _pt_persist(sess)
    return {"naming": sess.step6["naming"], "files": sess.step6["files"],
            "iterations": sess.step6["iterations"], "lint": lint,
            # Advisory only (Phase 7.4): what was projected, beside what arrived. Shown
            # together so a reviewer can see when a projection was wrong, rather than
            # having a wrong projection silently refuse the case before the call.
            "size": {**size, "recovery": blocks["report"]}}


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


@router.post("/save_naming/{key}")
async def save_naming(key: str, body: dict = Body(...)):
    """Persist step-6 Group/script-name on their own, with no generated file required.

    save_script -- the only other naming writer reachable from the UI -- opens with
    `if not step6.files.test: 409 "Generate a script first."`, and generate_script writes
    naming only once the model has answered. So until a generation SUCCEEDED there was no
    endpoint at all that would store these two fields: what the reviewer typed lived purely
    in the DOM, and renderPtGenPanel re-seeded from `naming.group || group_display` on
    every re-render, silently replacing an edited value with the default the moment the
    panel was navigated away from and back. Reported 2026-08-31 on AWPTCM-T33351.

    Naming-only by design. Once a script exists the rename has to move the file on disk and
    invalidate the confirmation with it, which is save_script's whole job -- so this refuses
    that case rather than half-doing it and leaving a stale file behind under the old name.
    """
    sess = _pt_get(key)
    step6 = dict(sess.step6 or {})
    if (step6.get("files") or {}).get("test"):
        raise HTTPException(409, "A script already exists for this case — use Save to "
                                 "generated/, which also moves the file and re-lints it.")
    naming = step6.get("naming") or {}
    group, name = _validate_naming(body.get("group", naming.get("group", "")),
                                   body.get("name", naming.get("name", "")))
    step6["naming"] = {"group": group, "name": name}
    sess.step6 = step6
    _pt_persist(sess)
    return {"naming": step6["naming"]}


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
    # Every generated script does `import ck_media` inside _ck_bind_link (fixed frame), so
    # the helper ships with EVERY run — not only when the reviewer supplied a library.
    files[MEDIA_HELPER_NAME] = _media_helper_source()

    naming = step6.get("naming") or {}
    run_id = utc_now().strftime("%Y%m%d-%H%M%S")
    run = {"run_id": run_id, "case_key": key, "status": "queued",
           "profile": profile_name, "setup": setup_remote,
           "test_file": step6["files"]["test"]["name"],
           "started_at": utc_now().isoformat(),
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
       system=_CODE_SYSTEM_PROMPT,   # fenced python out, not JSON — see generate_script
       max_tokens=32000)  # emits a whole revised script — same size profile as generate
    if dry_run:
        return _provenance_preview(meta)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))
    blocks = _parse_generated_blocks(meta.get("content", ""))
    if not blocks["test_code"]:
        raise HTTPException(502, "LLM fix returned no python code block.")
    # Same rule as generate: a fix pass that came back in pieces and did not reassemble
    # must not silently replace a working script with a partial one.
    fix_failure = _recovery_failure(blocks["report"])
    if fix_failure:
        # Same rule as generate: record the evidence, keep the working script, then refuse.
        step6_f = dict(sess.step6 or {})
        attempts_f = list(step6_f.get("failed_generations") or [])
        attempts_f.append({
            "at": utc_now().isoformat(), "phase": "fix", "reason": fix_failure,
            "llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
            "prompt": meta.get("prompt", ""), "response": meta.get("content", ""),
            "recovery": blocks["report"], "rejected_code": blocks["test_code"] or "",
        })
        step6_f["failed_generations"] = attempts_f[-3:]
        sess.step6 = step6_f
        _pt_persist(sess)
        raise HTTPException(
            502, f"LLM fix could not be reassembled: {fix_failure} The full reply is saved "
                 f"under step6.failed_generations; the existing script is unchanged.")
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
                  "validated_at": utc_now().isoformat() if validated else None,
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

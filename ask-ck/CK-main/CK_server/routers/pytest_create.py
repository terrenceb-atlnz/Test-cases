"""PyTest Creator — turn completed (refined) test cases into runnable framework scripts.

Guided 8-step gated flow (see ask-ck/plans/PLAN-pytest-creator.md):
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
import asyncio
import py_compile
import random
import functools
import re
import tempfile
import threading
import time

from models import PtSession, safe_session_dict, model_to_dict
from paths import REFINED_DIR, PT_GENERATED_DIR
from timeutil import utc_now, as_utc
from llm import (run_prompt, run_prompt_text, render_prompt,
                 extract_json_block, _CODE_SYSTEM_PROMPT)
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
from llm_config import cfg_for_task, effective_llm_config

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
# A dot is allowed so a generated script can carry the ART identity `test-<suite>.<set>`
# (2026-09-17). The framework derives EVERYTHING from that filename: ATTestSet.py:71 matches
# `test-(\d+).(\d+).*\.py` and, failing to match, silently keeps the defaults at :53
# (`testSuiteNum = testSetNum = '0'`) — so a dotless name produced `test-0.0.log` with cases
# named `0.0.<n>`, and pt_exec's basename lookup then missed it and fell back to an arbitrary
# `.log` in the workdir, which can be a DEVICE console log. Barring dots made that
# unavoidable. Callers must still reject `..` (see _validate_naming) — that is the only
# traversal this character class would otherwise open.
_NAME_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,59}$")


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


# How many times to re-apply a narrow field update onto a freshly reloaded session.
# Each attempt is one indexed read plus one write, so a small number is enough: the writes
# it races are human-paced clicks, not a hot loop.
_PT_FRESH_WRITE_ATTEMPTS = 3

# Per-unit generation dispatches N units at once and every reply writes the same session
# row, so a stale write is the NORM there rather than an accident. Contention is bounded by
# the browser's broker worker count (default 4, max 16), and each attempt re-reads before
# re-applying, so a budget comfortably above that clears the queue. A discarded chunk here
# costs a whole LLM call, which is why this is generous where the default is not.
_PT_CHUNK_WRITE_ATTEMPTS = 24

# Server-side cap on concurrent unit calls, so a 30-unit batch cannot eat the anyio
# threadpool (40 threads by default; `registry.submit` blocks one for the whole call).
# The real ceiling on throughput is the browser's broker worker count, which is smaller
# than this — so this exists to protect the server, not to pace the work.
_PT_UNIT_DISPATCH_MAX = 8
# How much of a REFUSED reply to keep for the reviewer. Enough to read the whole of a
# plausible unit (they run 3-5KB) without letting a runaway reply bloat the session row.
_PT_RAW_KEEP_CHARS = 24000
# R3 repair turns per unit at GENERATION (D1, 2026-09-15). Start at 1; R5's return rate
# (repaired replies that pass / repair turns taken) raises it to 2 below 50%, back to 1 if
# that does not move it. Admin-settable later; a module constant until then.
_PT_REPAIR_TURNS = 1
# R4 settle rounds after an Assemble (D3: 2, default on, rounds shown live). A round fixes
# the units whose lint errors are all LINT-CLASS and per-unit — never a held (review/run)
# unit, never a whole-file error — re-assembles and re-lints.
_PT_SETTLE_ROUNDS = 2

# Units dispatched and not yet settled, per case key. In memory only: a server restart
# loses the tracking, and the poll then reports whatever landed in step6.chunks, which is
# the truth that matters. Guarded because the batch endpoint and the poll race.
_pt_units_running: Dict[str, set] = {}
_pt_units_lock = threading.Lock()


def _pt_unit_mark(key: str, unit_ids, running: bool) -> None:
    with _pt_units_lock:
        cur = _pt_units_running.setdefault(key, set())
        for uid in unit_ids:
            cur.add(uid) if running else cur.discard(uid)
        if not cur:
            _pt_units_running.pop(key, None)


def _pt_units_inflight(key: str) -> set:
    with _pt_units_lock:
        return set(_pt_units_running.get(key) or ())


def _pt_persist_fresh(key: str, apply_fn, attempts: int = 0) -> PtSession:
    """Re-load the session, apply `apply_fn(sess)`, and persist. Retries a stale write.

    THE DEFECT THIS FIXES (2026-09-02, AWPTCM-T44297 -- 8 lost LLM calls, ~235k tokens)
    ------------------------------------------------------------------------------------
    Every long LLM endpoint here did: load the session, spend 30-600s in the model, then
    persist THE SNAPSHOT IT LOADED BEFORE THE CALL. `_pt_persist` CASes on `rev`, so any
    other write inside that window makes the snapshot stale and `locks.next_rev` refuses
    it -- discarding the entire round trip with an HTTP 409.

    The window is wide enough that ordinary use lands in it. Measured on a 31-step
    suggest-all: clicking "Save Selections" (the reviewer shortlisting the steps already
    done -- exactly what the panel is for) bumped the rev every 20-45s, and steps
    10 and 13-19 each completed their LLM call and were then thrown away. The coverage bar
    simply stopped advancing, which reads as "the LLM stopped suggesting".

    The fix is to stop writing a stale whole-session snapshot, NOT to weaken the CAS.
    `apply_fn` touches only the fields its endpoint owns, so a concurrent write to any
    OTHER field is no longer a conflict -- while a genuine same-field conflict still loses
    the race and still refuses, which is the protection `next_rev` exists to give.

    `_pt_load`, not `_pt_get`, deliberately: `_pt_get` prefers whichever of memory/DB is
    newer by `updated_at`, and a FAILED `_pt_persist` has already stamped `updated_at = now`
    on the in-memory copy before `next_rev` raised. So on a retry `_pt_get` would judge the
    poisoned cache newer than the DB and hand back the same stale-rev object forever. The
    authoritative copy for a CAS is the row the CAS compares against.

    A `LockConflictError` is NOT retried: another holder owns the case, and hammering it
    would neither succeed nor be polite.

    `attempts` overrides the default retry budget. Three is right for the one-call-at-a-time
    endpoints this was written for, where a conflict means a human clicked Save mid-call.
    Per-unit generation (2026-09-02) is different in kind: N units are dispatched at once and
    every reply writes the same session row, so conflicts are the NORM rather than an
    accident, and a unit whose result is discarded costs a whole LLM call. Contention is
    bounded by the browser's worker count, so a budget a few times that clears it.
    """
    budget = attempts if attempts > 0 else _PT_FRESH_WRITE_ATTEMPTS
    last: Optional[locks.StaleWriteError] = None
    for attempt in range(1, budget + 1):
        sess = _pt_load(key)
        if sess is None:
            raise HTTPException(404, "PyTest Creator session not found. Call load_case first.")
        pt_sessions[key] = sess
        apply_fn(sess)
        try:
            _pt_persist(sess)
            return sess
        except locks.StaleWriteError as e:
            last = e
            if attempt < budget:
                # Back off a little, and jitter it. Without the jitter N units that
                # collided once re-collide in lockstep on every retry.
                time.sleep(0.05 * attempt + random.random() * 0.05)
                print(f"[pt] {key}: stale write on attempt {attempt}/{budget}; reloading "
                      f"and re-applying (a concurrent save landed mid-LLM)")
    raise last if last else HTTPException(500, "unreachable")


def _llm_cfg(sess: PtSession) -> dict:
    # The dispatch config for THIS request: the requesting seat's X-CK-LLM choice, else
    # the site default, else the session's own stored config. Resolved at call time and
    # never written onto the session — the case is shared between seats, the choice is
    # not (PLAN-seat-setup-and-per-seat-llm.md §5). Centralized here so no endpoint can
    # resolve it differently; the Generator's _session_llm_cfg uses the same helper.
    return effective_llm_config(sess)


def _llm_cfg_for(sess: PtSession, task: str) -> dict:
    """`_llm_cfg` with the workspace's per-task model routing applied (decision 6).

    `task` is "unit_fill" (per-unit generation, per-unit Fix) or "step_match" (per-step
    script matching) — the two fan-out call classes that a cheaper Claude alias was judged
    good enough for (docs/TOKEN-EFFICIENCY-REPORT-2026-09-04.md §5). Review, whole-script Fix
    and the single-call generate keep `_llm_cfg` and therefore the toggle model. Routing is
    read inside cfg_for_task from the requesting SEAT's header, else the workspace (site
    default) row — never from this session's copy.
    """
    return cfg_for_task(_llm_cfg(sess), task)


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
        "system": meta.get("system") or "",
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


# Slice C (PLAN-generate-state-and-sequence-sanity, 2026-09-21): the extractor now checks its
# own sequence — every state-changing step carries a `claim` (cable / DUT / partner / expected
# link) and contradictions it could not resolve come back as `sanity` flags. Both are advisory:
# rendered on the Sequence page beside Confirm Step 2, never a gate (Terrence: warn, don't block).
_CLAIM_KEYS = ("cable", "dut", "partner", "expect")


def _normalize_claim(raw: Any) -> Optional[dict]:
    """A step's physical claim as short strings, or None when the model gave nothing usable."""
    if not isinstance(raw, dict):
        return None
    out = {k: " ".join(str(raw[k]).split()) for k in _CLAIM_KEYS
           if raw.get(k) is not None and str(raw[k]).strip()}
    return out or None


def _sanity_flags(raw: Any, n_steps: int) -> List[dict]:
    """[{steps: [ints within 1..n], issue: str}] — anything else is dropped, not stored."""
    out: List[dict] = []
    for f in (raw if isinstance(raw, list) else []):
        if not isinstance(f, dict):
            continue
        issue = " ".join(str(f.get("issue") or "").split())
        steps = f.get("steps")
        if not isinstance(steps, list):
            steps = [steps] if steps is not None else []
        nums = sorted({int(x) for x in steps
                       if str(x).strip().lstrip("-").isdigit() and 1 <= int(x) <= n_steps})
        if issue:
            out.append({"steps": nums, "issue": issue})
    return out


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


def _sequence_shape(sequence: list) -> str:
    """Identity of a sequence for the purpose of "is step-numbered data still valid?".

    Step numbers are the join key for everything downstream -- step3.selections is
    {stepN: [ids]} and step5 fragments carry `maps_to: [n]` -- so a re-extraction that
    renumbers the steps silently repoints all of it at different work. Keyed on the STEP
    TEXT, not just the count: 31 steps whose wording changed is the same hazard as 13
    becoming 31, and a count alone would miss it.
    """
    return "|".join(f"{s.get('n')}:{(s.get('action') or '')[:120]}"
                    for s in (sequence or []))


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


# Our assigned, previously-unused ART suite number. The family lives at 9000.<set>.<case>,
# modelled on the 1000-series convention (2026-09-17, Terrence).
PT_ART_SUITE = "9000"


def _art_script_name(case_key: str) -> str:
    """`AWPTCM-T33233` -> `test-9000.33233`: the script's ART identity, derived not typed.

    The filename is NOT cosmetic — it is the only input the framework has for its own
    identity. `ATTestSet.py:71` parses `test-(\\d+).(\\d+).*\\.py` out of it and
    `create_log_file()` writes `test-<suite>.<set>.log`; no match means the '0' defaults
    stand and every run lands in `test-0.0.log`. Putting the Zephyr case number in the SET
    position is what makes each case's log natively named and self-describing
    (`9000.33233.<step>` = suite · case · step), so the four Port cases produce four
    correctly-named logs with no post-processing.

    Derived from the key rather than the title, and authoritative over anything stored or
    posted: a typed name cannot satisfy a convention the framework parses.
    """
    digits = "".join(re.findall(r"\d+", case_key or ""))
    if digits:
        return f"test-{PT_ART_SUITE}.{digits}"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", case_key or "generated").strip("_") or "generated"
    return f"test-{PT_ART_SUITE}.0_{slug}"[:60]


# `_propose_name(title)` — which coined a name from the case TITLE ("MDIX_test") — was removed
# on 2026-09-17 along with the Generate panel's naming inputs. A title-derived name cannot
# satisfy the framework's `test-<suite>.<set>.py` pattern, so every script it named produced a
# `test-0.0.log`. `_art_script_name(case_key)` above replaced it as the only namer.


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
    # `..` is rejected explicitly now that _NAME_RX admits a dot: before that, no-dots made
    # traversal impossible by construction, exactly as it still is for _GROUP_RX above.
    if not _NAME_RX.match(name) or ".." in name:
        raise HTTPException(400, "Invalid script name (letters/digits/.-_ only, no '..', no extension).")
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
# was pinned at 1.95, above the top of the real range. `ask-ck/tools/pt_measure_expansion.py`
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
_skeleton_env = _J2Env(loader=_J2Loader(str(_TEMPLATES_DIR)),
                       keep_trailing_newline=True)   # pep8 W292: scripts end with a newline


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
        # `orig_n` keeps the SOURCE Test Step number so the `self.log('STEP n')` line traces to
        # the manual case's steps; `n` becomes the contiguous TestCase index (class name / unit
        # id). Because step 1 is the setup/disclaimer, orig_n on the cases starts at 2 — which is
        # exactly the alignment Terrence asked for (2026-09-16): STEP logs follow the source
        # steps, class numbering unchanged. Without this, the log said the case index (STEP 25 for
        # source step 26), off by one against every manual step (Review finding on T44297).
        s["orig_n"] = s.get("n")
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
    silently when it does not. `ask-ck/tools/pt_preflight.py` checks that offline before a run.
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


# Bound in init() but not a DEVICE the model reaches with `self.testSet.<name>.cmd(...)`:
# the pluggable-role flags and the frame's own discovery state (2026-09-21).
_NON_DEVICE_BOUND_ATTRS = frozenset({"ck_far_port", "fibre_supported", "cusfp_supported",
                                     "_ck_far", "_ck_topo"})


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
_MEDIA_HELPER_SRC = Path(__file__).resolve().parents[4] / "ask-ck" / "tools" / "pt_media.py"
# The workdir filename the generated script imports. Must match the template's `import`.
MEDIA_HELPER_NAME = "ck_media.py"

_FIBRE_HINT_RX = re.compile(
    r"\b(fibre|fiber|optical|optic|single-?mode|multi-?mode|"
    r"\d+base-(?:sx|lx|lh|sr|lr|er|zx|bx|fx))\b", re.I)


# Copper-specific vocabulary: when a case mentions fibre AND any of these, it needs BOTH links
# (T33234: crossover/straight-through polarity on copper, plus fibre and copper-SFP insertion).
_COPPER_HINT_RX = re.compile(
    r"\b(copper|twisted[- ]pair|rj-?45|polarity|mdi-?x?|crossover|straight-?through|"
    r"\d+base-t[a-z0-9]*)\b", re.I)
# A copper SFP: a 1000BASE-T (or similar) MODULE in an SFP cage — a pluggable the operator
# inserts, so it is its own role rather than the fixed RJ-45 copper link.
_CUSFP_HINT_RX = re.compile(
    r"\b(copper[- ]sfp|sfp[- ]?t\b|cu[- ]?sfp|"
    r"\d+base-t[a-z0-9]*\s+(?:sfp|module|pluggable|transceiver)|"
    r"copper\s+(?:sfp\s+)?(?:module|pluggable|transceiver)|"
    r"rj-?45\s+(?:sfp|module|pluggable|transceiver))\b", re.I)


# ---- ART shape (2026-09-07): which LINKS the frame binds, the suite LIBRARY, the bound ports ----
#
# The corpus's dominant topology is DUT <-> TESTBOX: `(dut.portA, tb.ethA) = setup.init_portlink(
# dutA, tb, type1='port')` in 111 of 188 ART tests, with captures, scapy sends and pings on
# `tb.ethA`. A second SWITCH appears only when the test needs a neighbour, and ART names it by
# role (swiSrc, swiDst, dutZ), never `dut` — `dut` is the DUT's own stack handle. Until this
# change the frame bound one partner switch and called it `dut`, gave the testbox no bound
# interface at all, and both Opus and Sonnet wrote `tb.ethA` in every capture unit and
# `dut.portA` for the DUT port: 59 and 63 unbound-port lint errors on T44297, all frame-caused.
_TBLINK_RX = re.compile(
    r"\b(tcpdump|pcap|scapy|sendp|sniff|capture[ds]?|inject(?:ed|s)?|"
    r"tb\.eth\w*|ethA|testbox|test box|traffic|ping|on the wire|wireshark|"
    r"frames? (?:transmitted|sent|received)|lldpdu|packets?)\b", re.I)
_PEER_RX = re.compile(
    r"\b(partner|neighbou?rs?|peer|link partner|remote (?:switch|end|device)|second switch|"
    r"other switch|far end|swi_[b-z]|polarity|mdi-?x?|speed|duplex|auto-?neg\w*|"
    r"negotiat\w*|show lldp neighbo\w*)\b", re.I)


LINK_ROLES = ("tb", "copper", "fibre", "cusfp")


def _detect_links(sequence: List[dict], fragments: List[dict], objective: str = "") -> dict:
    """Which of the frame's four link ROLES this case needs:
    `{"tb": bool, "copper": bool, "fibre": bool, "cusfp": bool, "peer": bool}` — `peer` is the
    derived alias "any neighbour switch" (copper or fibre or cusfp), for callers that only care
    whether a partner exists.

    The frame binds one link per role and finds each through the framework at run time
    (`get_all_port_links()` + the DUT's own show output — 2026-09-21, no `[misc]` declaration),
    so this function decides only HOW MANY partner links the case needs and of which media.

    Text-driven and deliberately over-inclusive: a role bound but unused costs one discovered
    link (or, for the optional pluggable roles, nothing at all), while a role needed but
    unbound costs a bench run that dies on `interface None`. A wrong choice can never produce
    a wrong VERDICT — a required role the bench cannot supply aborts at init() and says the
    bench is the cause.

      tb      the case captures / injects / measures traffic (the ART `tb.ethA` idiom), or
              has a PHYSICAL step (the testbox observes the event from its own end).
      copper  a neighbour switch on a fixed twisted-pair link: a partner to negotiate against,
              a polarity to force, an LLDP neighbour table to read, a remote port to act on.
              Suppressed only when the case is fibre-flavoured and mentions nothing
              copper-specific (then the neighbour is the fibre link).
      fibre   the case mentions fibre / optical / a fibre pluggable, or a step's slice-C
              `claim.cable` says so.
      cusfp   the case mentions a copper SFP / 1000BASE-T module — a pluggable the operator
              inserts, its own role so a bench without one reports UNSUPPORTED.
    Legacy fallback: a case that reads like it needs *a* port link but names neither side
    gets the copper link, which is what the frame bound before this function existed.
    """
    seq = sequence or []
    blob = " ".join([objective or ""] + [
        (s.get("action", "") or "") + " " + (s.get("verify", "") or "") for s in seq])
    code = " ".join((f.get("code") or "") for f in (fragments or []))
    has_physical = any(_step_kind(s) == "physical" for s in seq)
    claims = [str(((s.get("claim") or {}) if isinstance(s.get("claim"), dict) else {}).get("cable") or "").lower()
              for s in seq]
    tb = bool(_TBLINK_RX.search(blob)) or bool(re.search(r"\btb\.eth|start_tcpdump|sendp\(", code)) \
        or has_physical
    neighbour = bool(_PEER_RX.search(blob)) or bool(re.search(r"\b(lp|peer|remote|swi_[b-z])\.(cmd|mode|port)", code))
    fibre = bool(_FIBRE_HINT_RX.search(blob)) or any(c.startswith("fib") for c in claims)
    cusfp = bool(_CUSFP_HINT_RX.search(blob)) or any(c in ("cusfp", "copper-sfp", "copper sfp") for c in claims)
    copper_hint = bool(_COPPER_HINT_RX.search(blob)) or any(c in ("straight", "crossover", "copper") for c in claims)
    copper = neighbour and (not fibre or copper_hint)
    if not (tb or copper or fibre or cusfp) and _PORTLINK_RX.search(blob + " " + code):
        copper = True
    return {"tb": tb, "copper": copper, "fibre": fibre, "cusfp": cusfp,
            "peer": copper or fibre or cusfp}


def _group_library_stem(group: str) -> str:
    """`Port` -> `library_port`: ONE library per mother folder (R1(b), PLAN-group-libraries.md).

    Was `library_<case>` until 2026-09-22, which gave every case its own copy of a shared
    helper — the duplication R1(a)'s dependency closure makes MORE likely, since it now
    auto-ships a fragment's dependencies into whatever library the case happens to own.

    Deliberately NOT ART's `library_<suite>`: ART keys that on the numeric suite
    (`library_1332.py` for `1332_lldp_med`), but every script we generate sits on our one
    assigned suite 9000 (`PT_ART_SUITE`), so a faithful `library_<suite>` would be a single
    `library_9000.py` for the entire output. The mother folder is the grouping that carries
    meaning here. Recorded so nobody "corrects" it back.

    Group names are not module names — `_GROUP_RX` admits spaces, parens and hyphens — so the
    same fold `_library_stem` always used applies. KNOWN consequence: `Port A` and `Port-A`
    both become `library_port_a`. That collision class did not exist when the key was the case;
    it is left unguarded because two groups differing only in punctuation would be visible the
    moment it happened (both scripts import the same module).
    """
    return "library_" + re.sub(r"[^a-z0-9]+", "_", (group or "group").lower()).strip("_")


def _effective_group(sess) -> str:
    """The group BOTH generation paths must agree on.

    `_pt_generation_context` mirrors `generate_script`'s derivation so a per-unit run and a
    whole-script run start from a byte-identical frame; the library stem is now part of that
    frame (`from <stem> import *`), so a divergence here changes `assembled_hash` and makes
    slice A's gating 409 on every splice. One helper, both callers, no re-derivation inside
    `_build_library`.
    """
    naming = (getattr(sess, "step6", None) or {}).get("naming") or {}
    return naming.get("group") or _group_display(getattr(sess, "group", "") or "")


_LIB_SKIP_IMPORTS = {"sys", "framework.ATTestCase", "framework.ATTestSet"}


def _fragment_loaded_names(code: str) -> set:
    """The FREE names a fragment reads — names it Loads but does not itself bind (so not its
    own defs, assignments, params or comprehension targets). These are what it depends on."""
    import ast as ast_mod
    try:
        tree = ast_mod.parse(textwrap_dedent(code))
    except SyntaxError:
        return set()
    bound: set = set()
    for n in ast_mod.walk(tree):
        if isinstance(n, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef, ast_mod.ClassDef)):
            bound.add(n.name)
        elif isinstance(n, ast_mod.Name) and isinstance(n.ctx, (ast_mod.Store, ast_mod.Del)):
            bound.add(n.id)
        elif isinstance(n, ast_mod.arg):
            bound.add(n.arg)
        elif isinstance(n, (ast_mod.Import, ast_mod.ImportFrom)):
            bound.update((a.asname or a.name).split(".")[0] for a in n.names)
    loaded = {n.id for n in ast_mod.walk(tree)
              if isinstance(n, ast_mod.Name) and isinstance(n.ctx, ast_mod.Load)}
    return loaded - bound


def _find_top_level_def(name: str, source: str) -> Optional[str]:
    """The source text of a top-level `name = …` / `def name` / `class name` in `source`, or
    None. AST + get_source_segment, so the definition comes back verbatim."""
    import ast as ast_mod
    if not source:
        return None
    try:
        tree = ast_mod.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef, ast_mod.ClassDef)) \
                and node.name == name:
            return ast_mod.get_source_segment(source, node)
        if isinstance(node, ast_mod.Assign) and any(
                isinstance(tt, ast_mod.Name) and tt.id == name for tt in node.targets):
            return ast_mod.get_source_segment(source, node)
    return None


def _framework_star_imports_of(source: str) -> List[str]:
    """The `from framework… import *` (and `import scapy…`) lines a source uses — the imports a
    module-level dependency lifted from it needs to evaluate at import time."""
    import ast as ast_mod
    out: List[str] = []
    try:
        tree = ast_mod.parse(source or "")
    except SyntaxError:
        return out
    for node in tree.body:
        if isinstance(node, ast_mod.ImportFrom) and (node.module or "").startswith("framework") \
                and any(a.name == "*" for a in node.names):
            out.append(f"from {node.module} import *")
    return out


_PT_MAX_DEPS = 40


def _close_fragment_deps(fragments: List[dict], data: dict, already: set,
                         fw_classes: set) -> Tuple[List[dict], List[str]]:
    """R1 (2026-09-15): the module-level definitions the SHOWN fragments depend on but nothing
    ships. A fragment offered "to adapt" may call a name defined at its source suite's module
    level or in its `library_<suite>.py` (`LLDP_PHONE_PKT` in 1332_lldp_med/library_1332.py); the
    model adapts the fragment and keeps the name, and if nothing ships it, that is a NameError on
    the bench. Resolve each free name against the fragment's source script and sibling library,
    ship the definition in OUR library (marked auto-added), and recurse on its own free names.
    Returns (dep_members, import_lines). A class the framework already provides is never shipped
    (it would shadow the real layer). Bounded at `_PT_MAX_DEPS`."""
    def _sources(f: dict) -> Tuple[str, str]:
        sid = f.get("source_id", "")
        rec = (data.get("scripts_index_by_id") or {}).get(sid) or {}
        src = _fragment_source_text(sid)
        try:
            suite_lib = dbx.get_suite_library(rec.get("suite_dir") or "", rec.get("db")) or ""
        except Exception:
            suite_lib = ""
        return src, suite_lib

    seen = set(already)
    members: List[dict] = []
    import_lines: List[str] = []
    queue: List[tuple] = []
    for f in fragments or []:
        src, suite_lib = _sources(f)
        try:
            tag = _fragment_tag(f.get("source_id", ""), f.get("loc"), f.get("py2_translated", False))
        except Exception:
            tag = f.get("source_id", "") or "(fragment)"
        for nm in _fragment_loaded_names(f.get("code") or ""):
            queue.append((nm, src, suite_lib, tag))
    import ast as ast_mod
    while queue and len(members) < _PT_MAX_DEPS:
        name, src, suite_lib, tag = queue.pop(0)
        if name in seen:                               # builtins/scapy/framework are pre-seeded
            continue
        seen.add(name)
        definition = _find_top_level_def(name, src) or _find_top_level_def(name, suite_lib)
        if not definition:
            continue                                   # framework/scapy/unknown — not ours to ship
        try:
            deftree = ast_mod.parse(definition)
        except SyntaxError:
            continue
        if any(isinstance(n, ast_mod.ClassDef) and n.name in fw_classes for n in deftree.body):
            continue                                   # would shadow the framework's real layer
        members.append({"tag": f"# AI: dependency `{name}` of {tag}", "symbol": name,
                        "names": [name], "code": textwrap_dedent(definition), "why": "", "auto": True})
        for line in _framework_star_imports_of(src) + _framework_star_imports_of(suite_lib):
            if line not in import_lines:
                import_lines.append(line)
        for nm in _fragment_loaded_names(definition):
            queue.append((nm, src, suite_lib, tag))
    return members, import_lines


def _build_library(group: str, fragments: List[dict], data: dict,
                   surface: Optional[dict] = None) -> Optional[dict]:
    """The GROUP's own helper module — one per mother folder since 2026-09-22 (R1(b)); see
    `_group_library_stem`. Modelled on the way every ART suite ships one (`library_1332.py`
    holds the packets and the shared checks; 154 of 188 tests import theirs with `*`).

    Contents: every SELECTED fragment that is a stand-alone module-level definition — a
    function (INCLUDING ART's helpers that take the TestCase as a `self` first parameter,
    `def analyse_lldp_packets(self, recPktList)`), a class, or a constant — copied verbatim
    under its provenance tag, plus the import lines its source script used. Methods and
    class-body slices are NOT library material (they need their class) and stay as
    fragments to adapt. A `self`-first def is a helper when its SOURCE defines it at column
    0 and a method otherwise (2026-09-08: the old "first parameter is not `self`" rule left
    `analyse_lldp_packets` out, so it was offered as a fragment to adapt and the model
    CALLED it — a NameError in 7 of 37 T44297 units on a lint-clean script).

    Two exclusions found on the real T44297 selection (2026-09-07), both import-time
    hazards a compile check cannot see:
      * a fragment that DEFINES a class the framework already provides (the legacy
        `lldp_class.py` copies of the `framework.ATPackets` layers). Shipping it would
        shadow the real layer after `from framework.ATPackets import *`, so `haslayer()`
        compares against a different class object and every decode silently fails. These
        are recorded as `framework_dupes` — the prompt says "already imported, do not
        paste" — and dropped from the fragment sections too.
      * a member whose default argument or module-level value names something the
        library cannot resolve (`def checkPortCoErrors(csvName = defaultCsvName)`) —
        evaluated when the module is imported, so the whole suite dies before case 1.
        Allowed only when the source script star-imports a framework module, which is
        where such names legitimately come from (`LLDP_PHONE_PKT = Ether() / ...`).
    Returns None when nothing qualifies and nothing was excluded; a dict with empty
    `members` (and no `stem`) when only exclusions happened, so the frame emits no import.
    """
    import ast as ast_mod
    import builtins as _bi
    if surface is None:
        surface = _framework_surface_doc()
    fw_classes = {cn for mod in (surface or {}).values() if isinstance(mod, dict)
                  for cn in (mod.get("classes") or {})}
    stem = _group_library_stem(group)
    members: List[dict] = []
    imports: List[str] = []
    dupes: List[str] = []
    dupe_tags: set = set()
    skipped: List[str] = []
    for f in fragments or []:
        code = (f.get("code") or "").strip("\n")
        if not code:
            continue
        try:
            tree = ast_mod.parse(textwrap_dedent(code))
        except SyntaxError:
            continue
        if not tree.body:
            continue
        tag = _fragment_tag(f.get("source_id", ""), f.get("loc"), f.get("py2_translated", False))
        # Frame classes (a TestSet / TestCase_<n> slice) are never library material and are
        # not "framework duplicates" either — they merely share the framework's class names.
        if any(isinstance(n, ast_mod.ClassDef) and any(
                ("TestCase" in getattr(b, "attr", getattr(b, "id", "")) or
                 "TestSet" in getattr(b, "attr", getattr(b, "id", ""))) for b in n.bases)
               for n in tree.body):
            continue
        cls_names = [n.name for n in tree.body if isinstance(n, ast_mod.ClassDef)]
        if any(c in fw_classes for c in cls_names):
            dupes.extend(c for c in cls_names if c in fw_classes)
            dupe_tags.add(tag)
            continue
        rec = (data.get("scripts_index_by_id") or {}).get(f.get("source_id")) or {}
        src_imports = [m for m in (rec.get("imports", []) or []) if m not in _LIB_SKIP_IMPORTS
                       and not m.startswith("library_")]
        has_star = any(m.startswith("framework.") for m in src_imports)
        # names evaluated at IMPORT time: defaults and module-level values
        import_time: List[ast_mod.AST] = []
        for node in tree.body:
            if isinstance(node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef)):
                import_time += list(node.args.defaults) + [d for d in node.args.kw_defaults if d]
            elif isinstance(node, ast_mod.Assign):
                import_time.append(node.value)
        defined = {n.name for n in tree.body if isinstance(n, (ast_mod.FunctionDef, ast_mod.ClassDef))}
        defined |= {t.id for n in tree.body if isinstance(n, ast_mod.Assign)
                    for t in n.targets if isinstance(t, ast_mod.Name)}
        defined |= {m["symbol"] for m in members} | {nm for m in members for nm in m["names"]}
        defined |= {m.split(".")[0] for m in src_imports}
        unresolved = sorted({n.id for e in import_time for n in ast_mod.walk(e)
                             if isinstance(n, ast_mod.Name) and isinstance(n.ctx, ast_mod.Load)
                             and n.id not in defined and not hasattr(_bi, n.id)})
        if unresolved:
            # A name the SOURCE SCRIPT itself defines at module level is a local global the
            # library does not carry — a star import cannot supply it, whatever else the
            # source imports (`defaultCsvName` in svt/libSvt/portCoToCsv.py). Anything else
            # is allowed only when the source star-imports a framework module.
            src_text = _fragment_source_text(f.get("source_id", ""))
            local = [nm for nm in unresolved
                     if re.search(rf"^{re.escape(nm)}\s*=", src_text, re.M)]
            if local or not has_star:
                skipped.append(f"{f.get('symbol') or tag}: needs "
                               f"{', '.join(local or unresolved)} at import time")
                continue
        ok = True
        src_text_cached: Optional[str] = None
        for node in tree.body:
            if isinstance(node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef)):
                if node.name in ("main", "configure", "tear_down", "init"):
                    ok = False
                    continue
                first = node.args.args[0].arg if node.args.args else ""
                if first == "self":
                    # Module-level in the SOURCE (column 0) is what separates an ART helper
                    # from a method extracted out of its class; without the source text the
                    # conservative reading (a method) stands.
                    if src_text_cached is None:
                        src_text_cached = _fragment_source_text(f.get("source_id", ""))
                    if not re.search(rf"^(?:async\s+)?def\s+{re.escape(node.name)}\s*\(",
                                     src_text_cached, re.M):
                        ok = False
            elif isinstance(node, ast_mod.ClassDef):
                if any(("TestCase" in getattr(b, "attr", getattr(b, "id", "")) or
                        "TestSet" in getattr(b, "attr", getattr(b, "id", ""))) for b in node.bases):
                    ok = False
            elif not isinstance(node, (ast_mod.Assign, ast_mod.Import, ast_mod.ImportFrom)):
                ok = False
        if not ok:
            continue
        names = [n.name for n in tree.body if isinstance(n, (ast_mod.FunctionDef, ast_mod.ClassDef))]
        members.append({"tag": tag, "symbol": f.get("symbol") or (names[0] if names else ""),
                        "names": names, "code": textwrap_dedent(code), "why": f.get("why") or ""})
        for m in src_imports:
            line = f"from {m} import *" if m.startswith("framework.") else f"import {m}"
            if line not in imports:
                imports.append(line)
    # R1: close the shown fragments' module-level dependencies into the library (see
    # _close_fragment_deps). Runs on the FULL shown set, so a dep of a fragment offered only "to
    # adapt" is shipped too. Auto-added members are tagged `# AI: dependency …` so a review prune
    # can drop them without touching reviewer-selected members.
    _already = set(_bi.__dict__) | fw_classes | _SCAPY_STAR_NAMES | {c for c in dupes}
    _already |= {m["symbol"] for m in members} | {nm for m in members for nm in m["names"]}
    _dep_members, _dep_imports = _close_fragment_deps(fragments, data, _already, fw_classes)
    for _dm in _dep_members:
        members.append(_dm)
    for _line in _dep_imports:
        if _line not in imports:
            imports.append(_line)

    if not members and not dupes:
        return None
    if not members:
        return {"name": "", "stem": "", "code": "", "members": [], "tags": set(),
                "framework_dupes": sorted(set(dupes)), "framework_tags": dupe_tags,
                "skipped": skipped}
    body = [f'"""{stem} — helpers shared by the {group} group.',
            "",
            "Generated by Ask CK PyTest Creator alongside the test scripts, modelled on the way every",
            "ART suite ships a `library_<suite>.py`. EVERY script in this group imports this one module",
            "with `*`, so it is merged, never overwritten: each member is keyed by its provenance tag,",
            "which names the source. A member already here is left exactly as it is.",
            '"""']
    body += sorted(imports) if imports else ["import time"]
    for m in members:
        body += ["", "", m["tag"]]
        if m["why"]:
            body += ["# " + ln for ln in _wrap_comment(m["why"], 92)]
        body.append(m["code"])
    return {"name": stem + ".py", "stem": stem, "code": "\n".join(body).rstrip("\n") + "\n",
            "members": members, "tags": {m["tag"] for m in members},
            "framework_dupes": sorted(set(dupes)), "framework_tags": dupe_tags,
            "skipped": skipped}


def _fragment_source_text(source_id: str) -> str:
    """Whole source of a corpus script, "" when unavailable (a corpus read via db.py)."""
    try:
        return dbx.get_script_source(source_id) or ""
    except Exception:
        return ""


def textwrap_dedent(code: str) -> str:
    import textwrap
    return textwrap.dedent(code)


def _skeleton_bound_ports(skeleton: str) -> List[dict]:
    """The LINKS `TestSet.init()` binds, read off the rendered frame's `_ck_bind_link` calls:
    `[{"role": "tb", "near": "dutA.portA", "far": "tb.ethA"}, {"role": "copper",
    "near": "dutA.portPeer", "far": "peer.portDut"}, {"role": "fibre", "near": "dutA.portFibre",
    "far": "fibre_peer.portFibre"}]`. The prompt's handle section and rule 3 render from this,
    so the names the model is told are the names the frame really bound."""
    import ast as ast_mod
    try:
        tree = ast_mod.parse(skeleton)
    except SyntaxError:
        return []
    init_fn = next((n for n in ast_mod.walk(tree)
                    if isinstance(n, ast_mod.FunctionDef) and n.name == "init"), None)
    if init_fn is None:
        return []

    def _dotted(node) -> str:
        if isinstance(node, ast_mod.Attribute) and isinstance(node.value, ast_mod.Name):
            return f"{node.value.id}.{node.attr}"
        return node.id if isinstance(node, ast_mod.Name) else ""

    out: List[dict] = []
    # `X.portY = <local>` re-homes a tuple element onto its device (peer.portDut = peer_port)
    rehome: Dict[str, str] = {}
    for n in ast_mod.walk(init_fn):
        if (isinstance(n, ast_mod.Assign) and len(n.targets) == 1 and isinstance(n.value, ast_mod.Name)
                and isinstance(n.targets[0], ast_mod.Attribute)):
            rehome[n.value.id] = _dotted(n.targets[0])
    for n in ast_mod.walk(init_fn):
        if not (isinstance(n, ast_mod.Assign) and isinstance(n.value, ast_mod.Call)
                and isinstance(n.value.func, ast_mod.Attribute)
                and n.value.func.attr == "_ck_bind_link"):
            continue
        t = n.targets[0]
        elts = t.elts if isinstance(t, (ast_mod.Tuple, ast_mod.List)) else [t]
        if len(elts) < 2:
            continue
        role = next((a.value for a in n.value.args if isinstance(a, ast_mod.Constant)
                     and isinstance(a.value, str)), "")
        near, far = _dotted(elts[0]), _dotted(elts[1])
        far = rehome.get(far, far)
        out.append({"role": role, "near": near, "far": far})
    return out


def _media_helper_source() -> str:
    """The `ck_media.py` shipped alongside a generated script into the run workdir.

    Read from `ask-ck/tools/pt_media.py` rather than duplicated, so the module the testbox executes
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
                     objective: str = "", library: Optional[dict] = None) -> str:
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
                      links=_detect_links(sequence, fragments or [], objective),
                      lib_stem=(library or {}).get("stem") or "",
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
    """Bounded framework vocabulary for the generation prompt.

    `ATPackets` is special-cased (2026-09-07): the surface doc records its 28 scapy layers
    as classes with one `guess_payload_class` method each, which told the model nothing.
    ART decodes captures with them — `pkt.haslayer(lldp_cap_tlv)`, `pkt[lldp_cap_tlv]
    .lldp_med_cap` — and both models on T44297 hand-parsed TLV bytes instead. The prompt now
    lists the layers with their FIELDS.

    Since 2026-09-15 (D4, decision d — Terrence: option 1) a layer's list is its DECLARED
    fields from the surface doc (`classes[<layer>].fields`, harvested from `fields_desc`),
    ordered with the fields the corpus reads off it first (`db.script_layer_fields`), then the
    rest in declaration order. Until then only the corpus-read fields were shown — the only
    list that existed — and a 3-of-11 list on `lldp_basic` read as permission to extend it:
    fix run 5's tc6 invented `port_desc` / `sys_name`. The prompt and `_lint_layer_fields`
    now judge from the same list. A layer with no declared list falls back to corpus-read.
    """
    surface = data.get("framework_surface") or {}
    core = ["ATTestSet", "ATTestCase", "Setup", "ATPackets",
            "ATDrivers.ATSwitch", "ATDrivers.ATTestBox", "ATDrivers.ATPower"]
    wanted = list(dict.fromkeys(core + [m.replace("framework.", "") for m in extra_modules]))
    out = {m: surface[m] for m in wanted if m in surface}
    ap = out.get("ATPackets")
    if ap and ap.get("classes"):
        layers = sorted(ap["classes"])
        declared = _surface_layer_fields(surface)
        corpus = _atpackets_layer_fields(tuple(layers))
        out["ATPackets"] = {"classes": {}, "functions": ap.get("functions") or [],
                            "layers": {lay: _merge_layer_fields(corpus.get(lay) or [], declared.get(lay) or [])
                                       for lay in layers}}
    return out


def _merge_layer_fields(corpus_read: List[str], declared: List[str]) -> List[str]:
    """Declared fields, the corpus-read ones first (most-used order), then the rest in
    declaration order. A corpus-read name the layer does not declare is dropped — the lint would
    flag it. No declared list → the corpus-read list as before."""
    if not declared:
        return list(corpus_read)
    head = [f for f in corpus_read if f in declared]
    return head + [f for f in declared if f not in head]


@functools.lru_cache(maxsize=4)
def _atpackets_layer_fields(layers: tuple) -> Dict[str, List[str]]:
    """{layer: [fields the corpus reads]} — memoised, the corpus is permanent."""
    try:
        return dbx.script_layer_fields(list(layers))
    except Exception:
        return {lay: [] for lay in layers}


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
        # routers/ -> CK_server/ -> CK-main/ -> ask-ck/; cli_lookup is the PyTest Creator page's script
        tool_dir = str(Path(__file__).resolve().parents[3] / "frontend" / "ck-main" / "current" / "pytest-creator")
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
        # Resolve commands two features spell the same way in prose (`management address` is
        # both an LLDP TLV and an AWC wireless-controller command) using the whole text as
        # context — F2. The step-6 call site passes the entire sequence, so "LLDP named
        # elsewhere in the case" is visible here.
        cmds = cli_lookup.disambiguate_shared(cmds, text)
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
    "binding devices is the frame's job",      # a unit init_swi()/init_stk()-ing its own device (2026-09-21)
    "are config only; the verdict belongs in main()",   # a verdict in configure()/tear_down()
    "'s port, on ",                            # a port selected on the switch it does not belong to
    "the suite owns it",                       # G8(b): a case re-issues / undoes a TestSet.configure() command
)


def _split_lint_errors(errors: List[str]) -> Tuple[List[str], List[str]]:
    """(blocking, policy). Unrecognised errors are blocking — strict by default."""
    blocking, policy = [], []
    for err in errors:
        (policy if any(m in str(err) for m in _POLICY_LINT_MARKERS) else blocking).append(err)
    return blocking, policy


# --- PEP 8 style (2026-09-01) -------------------------------------------------
#
# Until now NOTHING in this pipeline checked style. `_lint_generated` ran py_compile
# (syntax) plus a long list of house-rule and contract assertions, all of which are about
# whether the script WORKS. A generated artefact is read by a human before it is promoted
# into `testsuites_art/`, so how it reads is part of the deliverable -- and the model has
# no incentive to keep lines short unless something says so.
#
# pycodestyle, not a hand-rolled subset. It IS the reference implementation of PEP 8, it is
# pure Python with zero dependencies, and it runs entirely offline -- the alternative was
# re-deriving a dozen rules here and getting the edge cases wrong while calling the result
# "PEP 8".
#
# 120, not pycodestyle's default 79. Measured over the 7 scripts in `generated/` (3,121
# lines): 732 lines exceed 79 and 171 exceed 120. At 79 the check emits ~120 findings on a
# single healthy script, which is a warning list nobody reads; at 120 the same script emits
# 21, and every one is a genuinely unreadable line -- the corpus tops out at 799 characters.
# The lower bound on usefulness here is "would a reviewer agree", and 79 fails it for code
# whose natural unit is a CLI string.
_PEP8_MAX_LINE = 120

# How many individual findings to name per code before collapsing to a count. A pathological
# generation can produce 200 E501s; listing them all buries the E741/W293 findings that are
# quick real fixes.
_PEP8_SAMPLE_PER_CODE = 4


def _pep8_findings(code: str) -> Tuple[List[str], Optional[str]]:
    """PEP 8 findings for `code`, as (warning strings, unavailable_reason).

    Returns `unavailable_reason` set and an EMPTY finding list when pycodestyle is not
    installed. The caller surfaces that as its own warning rather than silently reporting
    a clean style pass -- unknown is not the same as clean (the Phase 7.7 lesson from the
    coverage check, which used to be able to die and still lint green).

    Deliberately NOT an error, blocking or policy. A long line does not stop a script
    binding devices or reaching a verdict, and `blocking_errors` is reserved for "provably
    cannot work". Style that blocked Save would make the reviewer's only escape a recorded
    policy override, for whitespace.
    """
    try:
        import pycodestyle                       # runtime dep; see requirements.txt
    except Exception as e:                       # pragma: no cover - depends on the venv
        return [], f"{type(e).__name__}: {e}"

    collected: List[Tuple[int, str, str]] = []

    class _Collect(pycodestyle.BaseReport):
        """Collect findings instead of printing them. pycodestyle's default report writes
        to stdout, which on this server means the journal, not the reviewer's screen."""
        def error(self, line_number, offset, text, check):
            rv = super().error(line_number, offset, text, check)
            if rv:                               # None when the code is in the ignore list
                collected.append((line_number, rv, text[5:].strip()))
            return rv

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        style = pycodestyle.StyleGuide(max_line_length=_PEP8_MAX_LINE, reporter=_Collect,
                                       quiet=True)
        style.check_files([tmp])
    except Exception as e:                       # a checker crash must not kill the lint
        return [], f"pycodestyle failed to run ({type(e).__name__}: {e})"
    finally:
        os.unlink(tmp)

    by_code: Dict[str, List[Tuple[int, str]]] = {}
    for lineno, ccode, text in collected:
        by_code.setdefault(ccode, []).append((lineno, text))

    out: List[str] = []
    for ccode in sorted(by_code):
        hits = sorted(by_code[ccode])
        shown = ", ".join(f"line {ln}" for ln, _ in hits[:_PEP8_SAMPLE_PER_CODE])
        more = f" (+{len(hits) - _PEP8_SAMPLE_PER_CODE} more)" \
            if len(hits) > _PEP8_SAMPLE_PER_CODE else ""
        out.append(f"pep8 {ccode}: {hits[0][1]} — {len(hits)} occurrence"
                   f"{'s' if len(hits) != 1 else ''} at {shown}{more}")
    return out, None


# --- bench-integration lint (token-efficiency decision 2, 2026-09-07) ----------------------
#
# The three defect classes that made the T44297 per-unit script unrunnable until Review + Fix,
# each of which is DETERMINISTIC given the assembled script and the framework surface, so it
# belongs here and not in a $0.30 LLM review (about 40% of what Review found was this):
#
#   1. a port attribute init() never assigned — `self.testSet.dut.portA` when init() bound
#      `dut.portB` only (~30 of 38 units; renders as `interface None` on the bench);
#   2. a method call the framework class does not define, or a keyword it does not accept —
#      `start_tcpdump(..., filter=...)` copied from a library fragment's local helper;
#   3. a capture started and stopped with nothing in between — captures nothing.
#
# 1 and 2 are errors (they fail on the bench, deterministically). 3 is a warning: a capture
# of an already-flowing stream can legitimately be brief, so a human decides.

_PORTLIKE_RX = re.compile(r"^(port|eth)[A-Z]\w*$")
_CAPTURE_START = {"start_tcpdump", "start_capture", "startCapture"}
_CAPTURE_STOP = {"stop_tcpdump", "stop_capture", "stopCapture"}
_WAIT_NAMES = {"sleep", "wait", "waitFor", "wait_for", "poll", "mode", "settle"}
# init() binder -> the surface class whose methods a handle of that kind may call. A partner
# bound through _ck_bind_link (discovered, 2026-09-21) may be a switch OR the testbox, so it
# gets the union.
_BINDER_KINDS = {"init_swi": ("ATDrivers.ATSwitch", "Switch"),
                 "init_stk": ("ATDrivers.ATSwitch", "Stack"),
                 "init_tb": ("ATDrivers.ATTestBox", "TestBox")}


def _framework_surface_doc() -> dict:
    try:
        return dbx.get_json_doc("framework_surface") or {}
    except Exception:
        return {}


def _surface_methods(surface: dict, module: str, cls: str) -> Dict[str, Optional[list]]:
    """{method: args or None} for one surface class; None args = signature unknown."""
    out: Dict[str, Optional[list]] = {}
    for m in ((surface.get(module) or {}).get("classes") or {}).get(cls, {}).get("methods") or []:
        if m.get("name"):
            out[m["name"]] = m.get("args") if isinstance(m.get("args"), list) else None
    return out


def _lint_bench_integration(tree, code: str, surface: dict) -> Tuple[List[str], List[str]]:
    """The three checks above. Pure: (errors, warnings) from the AST + the surface."""
    import ast as ast_mod
    errors: List[str] = []
    warnings: List[str] = []

    testset = next((n for n in tree.body if isinstance(n, ast_mod.ClassDef)
                    and any("TestSet" in getattr(b, "attr", getattr(b, "id", "")) for b in n.bases)),
                   None)
    if testset is None:
        return errors, warnings
    init_fn = next((n for n in testset.body if isinstance(n, ast_mod.FunctionDef)
                    and n.name == "init"), None)

    # --- what init() binds: handle kinds, and (handle, port-attribute) pairs -----------------
    local_kind: Dict[str, str] = {}          # local name -> swi|stk|tb|partner
    self_kind: Dict[str, str] = {}           # self.<attr> -> kind
    bound_ports: set = set()                 # (handle-as-self-attr, portattr)
    local_to_self: Dict[str, str] = {}

    def _binder(call) -> Optional[str]:
        f = call.func
        name = f.attr if isinstance(f, ast_mod.Attribute) else getattr(f, "id", "")
        if name in _BINDER_KINDS:
            return {"init_swi": "swi", "init_stk": "stk", "init_tb": "tb"}[name]
        return None

    setup_scope = [n for n in testset.body if isinstance(n, ast_mod.FunctionDef)]
    for fn in setup_scope:
        for n in ast_mod.walk(fn):
            if not isinstance(n, ast_mod.Assign):
                continue
            val = n.value
            for t in n.targets:
                elts = t.elts if isinstance(t, (ast_mod.Tuple, ast_mod.List)) else [t]
                # X = setup.init_swi(...) ; self.X = setup.init_swi(...)
                if isinstance(val, ast_mod.Call) and _binder(val) and len(elts) == 1:
                    k = _binder(val)
                    if isinstance(t, ast_mod.Name):
                        local_kind[t.id] = k
                    elif (isinstance(t, ast_mod.Attribute) and isinstance(t.value, ast_mod.Name)
                          and t.value.id == "self"):
                        self_kind[t.attr] = k
                # (dut.portA, self.far, partner) = self._ck_bind_link(...)
                if (isinstance(val, ast_mod.Call) and isinstance(val.func, ast_mod.Attribute)
                        and val.func.attr == "_ck_bind_link" and len(elts) == 3):
                    if isinstance(elts[2], ast_mod.Name):
                        local_kind[elts[2].id] = "partner"
                    elif (isinstance(elts[2], ast_mod.Attribute)
                          and isinstance(elts[2].value, ast_mod.Name) and elts[2].value.id == "self"):
                        self_kind[elts[2].attr] = "partner"
                for el in elts:
                    # self.X = X  (a local handle published on the TestSet)
                    if (isinstance(el, ast_mod.Attribute) and isinstance(el.value, ast_mod.Name)
                            and el.value.id == "self" and isinstance(val, ast_mod.Name)
                            and len(elts) == 1):
                        local_to_self[val.id] = el.attr
                    # <handle>.portX = ... / self.<handle>.portX = ...  (a bound port)
                    if isinstance(el, ast_mod.Attribute) and _PORTLIKE_RX.match(el.attr):
                        base = el.value
                        if isinstance(base, ast_mod.Name):
                            bound_ports.add((base.id, el.attr))
                        elif (isinstance(base, ast_mod.Attribute)
                              and isinstance(base.value, ast_mod.Name) and base.value.id == "self"):
                            bound_ports.add((base.attr, el.attr))
    # Resolve locals to their self.* names (the name a TestCase reaches them by).
    for loc, k in local_kind.items():
        if loc in local_to_self:
            self_kind.setdefault(local_to_self[loc], k)
    bound_self_ports = set()
    for h, p in bound_ports:
        bound_self_ports.add((local_to_self.get(h, h), p))
    if not self_kind:
        return errors, warnings                    # not our frame; nothing to judge against

    def _direct_handle(node) -> Optional[str]:
        """`self.testSet.<h>` (in a TestCase) or `self.<h>` (in the TestSet) -> h."""
        if not isinstance(node, ast_mod.Attribute):
            return None
        v = node.value
        if (isinstance(v, ast_mod.Attribute) and v.attr == "testSet"
                and isinstance(v.value, ast_mod.Name) and v.value.id == "self"):
            return node.attr
        if isinstance(v, ast_mod.Name) and v.id == "self" and node.attr in self_kind:
            return node.attr
        return None

    # Local ALIASES. Nearly every generated unit starts `dutA = self.testSet.dutA` and then
    # reads `dutA.portA` / calls `dutA.cmd(...)` through the alias, so a checker that follows
    # only the full chain sees a fraction of the reads (measured 2026-09-07 on T44297: 12 of
    # ~26 unbound-port reads, and none of the keyword misuses). Resolve `name = <handle>`
    # per function; the alias is valid from its assignment to the end of that function.
    aliases: List[Tuple[int, int, str, str]] = []          # (lo, hi, local, handle)
    for fn in [n for n in ast_mod.walk(tree) if isinstance(n, ast_mod.FunctionDef)]:
        hi = fn.end_lineno or fn.lineno
        for n in ast_mod.walk(fn):
            if (isinstance(n, ast_mod.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast_mod.Name)):
                h = _direct_handle(n.value)
                if h:
                    aliases.append((n.lineno, hi, n.targets[0].id, h))

    def _handle_of(node) -> Optional[str]:
        h = _direct_handle(node)
        if h:
            return h
        if isinstance(node, ast_mod.Name):
            for lo, hi, local, handle in aliases:
                if local == node.id and lo <= node.lineno <= hi:
                    return handle
        return None

    # --- 1. port attributes that init() never assigned -----------------------------------
    # Reported once per (handle, attribute, ENCLOSING CLASS), not once per script: the
    # per-unit Fix maps a lint line to a unit by class name or line number, so a defect that
    # ~30 units share must name each of them or only one unit gets fixed.
    class_ranges = [(c.name, c.lineno, c.end_lineno or c.lineno)
                    for c in tree.body if isinstance(c, ast_mod.ClassDef)]

    def _class_at(ln: int) -> str:
        return next((nm for nm, lo, hi in class_ranges if lo <= ln <= hi), "")

    seen_ports = set()
    for n in ast_mod.walk(tree):
        if not (isinstance(n, ast_mod.Attribute) and _PORTLIKE_RX.match(n.attr)):
            continue
        h = _handle_of(n.value)
        if h is None or h not in self_kind:
            continue
        key = (h, n.attr, _class_at(n.lineno))
        if (h, n.attr) in bound_self_ports or key in seen_ports:
            continue
        # a read inside the TestSet's own binding code is the assignment itself
        if init_fn and init_fn.lineno <= n.lineno <= (init_fn.end_lineno or n.lineno):
            continue
        seen_ports.add(key)
        have = sorted(p for hh, p in bound_self_ports if hh == h)
        errors.append(
            f"{(_class_at(n.lineno) + ' ') if _class_at(n.lineno) else ''}"
            f"line {n.lineno}: reads `{h}.{n.attr}` but init() binds "
            f"{('`' + '`, `'.join(f'{h}.{p}' for p in have) + '` only') if have else f'no port on `{h}`'}"
            f" — on the bench this renders as `interface None`. Use a bound port, or declare "
            f"the extra link in the frame (TOPOLOGY-PROFILES.md), never in a TestCase")

    # --- 2. call shape against the framework surface ------------------------------------
    if surface:
        kind_methods: Dict[str, Dict[str, Optional[list]]] = {}
        for k, (mod, cls) in (("swi", _BINDER_KINDS["init_swi"]), ("stk", _BINDER_KINDS["init_stk"]),
                              ("tb", _BINDER_KINDS["init_tb"])):
            kind_methods[k] = _surface_methods(surface, mod, cls)
        partner = dict(kind_methods["swi"])
        partner.update(kind_methods["tb"])
        kind_methods["partner"] = partner
        seen_calls = set()
        for n in ast_mod.walk(tree):
            if not (isinstance(n, ast_mod.Call) and isinstance(n.func, ast_mod.Attribute)):
                continue
            h = _handle_of(n.func.value)
            if h is None or h not in self_kind:
                continue
            methods = kind_methods.get(self_kind[h]) or {}
            if not methods:
                continue                            # surface has nothing for this kind
            meth = n.func.attr
            if meth not in methods:
                if (h, meth) in seen_calls:
                    continue
                seen_calls.add((h, meth))
                cls = {"swi": "Switch", "stk": "Stack", "tb": "TestBox",
                       "partner": "Switch/TestBox"}[self_kind[h]]
                errors.append(
                    f"line {n.lineno}: calls `{h}.{meth}()` but the framework's {cls} class "
                    f"defines no `{meth}` — this is a fragment's local helper or an invented "
                    f"API; it dies with AttributeError on the testbox. Call a method from the "
                    f"framework surface, or inline the helper's body")
                continue
            args = methods[meth]
            if args is None:
                continue
            bad_kw = [kw.arg for kw in n.keywords if kw.arg and kw.arg not in args]
            if bad_kw and (h, meth, "kw") not in seen_calls:
                seen_calls.add((h, meth, "kw"))
                errors.append(
                    f"line {n.lineno}: `{h}.{meth}(...)` is called with keyword(s) "
                    f"{', '.join('`' + k + '`' for k in bad_kw)} that the framework signature "
                    f"`{meth}({', '.join(args)})` does not accept — TypeError on the testbox")
            npos = sum(1 for a in n.args if not isinstance(a, ast_mod.Starred))
            if npos > len(args) and (h, meth, "pos") not in seen_calls:
                seen_calls.add((h, meth, "pos"))
                warnings.append(
                    f"line {n.lineno}: `{h}.{meth}(...)` passes {npos} positional argument(s) "
                    f"but the framework signature `{meth}({', '.join(args)})` names {len(args)}")

    # --- 3. a capture with nothing between start and stop ---------------------------------
    for fn in [n for n in ast_mod.walk(tree) if isinstance(n, ast_mod.FunctionDef)]:
        calls = [n for n in ast_mod.walk(fn) if isinstance(n, ast_mod.Call)
                 and isinstance(n.func, (ast_mod.Attribute, ast_mod.Name))]
        calls.sort(key=lambda c: c.lineno)
        names = [(c.func.attr if isinstance(c.func, ast_mod.Attribute) else c.func.id, c.lineno)
                 for c in calls]
        for i, (nm, ln) in enumerate(names):
            if nm not in _CAPTURE_START:
                continue
            between = []
            for nm2, ln2 in names[i + 1:]:
                if nm2 in _CAPTURE_STOP:
                    break
                between.append(nm2)
            else:
                continue                            # never stopped in this function
            if not any(b in _WAIT_NAMES or b.startswith(("wait", "sleep")) for b in between):
                warnings.append(
                    f"line {ln}: the capture started here is stopped with no wait, sleep or "
                    f"wait-for-event between — it captures nothing. Settle first (time.sleep, "
                    f"or a wait on the event the step is about)")
    return errors, warnings


# --- names nothing defines / a port on the wrong switch / echoed verdicts (2026-09-08) --------
#
# The first pass on the ART frame (AWPTCM-T44297, 38 units, $6.47) linted CLEAN — 0 errors
# against 59 and 63 on the old frame — and would still have died on the bench three ways that
# no check looked for: `analyse_lldp_packets` called in 7 units and defined nowhere, `re` used
# in 4 units the frame never imported, and `LLDP_PHONE_PKT` lifted from an ART test script
# that was never offered. All three are the same defect class, a NameError on first use, and
# py_compile is blind to it. The fourth finding runs but tests the wrong thing: the suite setup
# configured `portPeer` (the DUT's end of the neighbour link) ON THE NEIGHBOUR. And six
# verdicts quoted the step's verify text verbatim as their reason, which says what was
# expected rather than what was observed.

# Names `from framework.ATPackets import *` brings in from scapy (ATPackets star-imports
# scapy.all). The surface doc records the AT layers, not scapy, so these are listed here.
_SCAPY_STAR_NAMES = frozenset("""
    sendp send sniff srp srp1 sr sr1 srloop srploop Ether IP IPv6 TCP UDP ICMP ICMPv6EchoRequest
    ICMPv6EchoReply ARP Raw Dot1Q Dot1AD Dot3 LLC SNAP STP Padding IGMP BOOTP DHCP DNS
    wrpcap rdpcap hexdump ls conf RandMAC RandIP RandShort RandString Packet bind_layers
    get_if_hwaddr get_if_addr get_if_list fuzz mac2str str2mac
""".split())


def _lint_unbound_names(tree, lib: Optional[dict]) -> List[str]:
    """Every name the script LOADS must be bound by the frame, the suite library, a
    star-imported framework module (per the surface doc), scapy via ATPackets, or builtins.

    Scoping is deliberately flat — a name bound anywhere in the file counts everywhere — so
    this under-reports rather than over-reports. It stays silent (returns []) when the script
    star-imports something it cannot see through: an unknown module could define anything,
    and a check that guesses would train reviewers to ignore it.
    """
    import ast as ast_mod
    import builtins as _bi
    defined = set(dir(_bi)) | {"__name__", "__file__", "__doc__", "__class__"}

    def _bind(t) -> List[str]:
        """Add every name `t` binds; return the modules it star-imports."""
        stars: List[str] = []
        for node in ast_mod.walk(t):
            if isinstance(node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef, ast_mod.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast_mod.Import):
                defined.update((a.asname or a.name).split(".")[0] for a in node.names)
            elif isinstance(node, ast_mod.ImportFrom):
                if any(a.name == "*" for a in node.names):
                    stars.append(node.module or "")
                defined.update(a.asname or a.name for a in node.names if a.name != "*")
            elif isinstance(node, ast_mod.Name) and isinstance(node.ctx, (ast_mod.Store, ast_mod.Del)):
                defined.add(node.id)
            elif isinstance(node, ast_mod.arg):
                defined.add(node.arg)
            elif isinstance(node, ast_mod.ExceptHandler) and node.name:
                defined.add(node.name)
            elif isinstance(node, (ast_mod.Global, ast_mod.Nonlocal)):
                defined.update(node.names)
        return stars

    surface = {k.replace("/", "."): v for k, v in (_framework_surface_doc() or {}).items()}
    packages = {k.rsplit(".", 1)[0] for k in surface if "." in k}

    def _add_module(rec: dict) -> None:
        defined.update(rec.get("classes") or {})
        defined.update(fn.get("name") if isinstance(fn, dict) else str(fn)
                       for fn in (rec.get("functions") or []))
        defined.update(rec.get("constants") or [])

    lib_stem = Path(lib["name"]).stem if lib and lib.get("name") else ""
    pending = _bind(tree)
    seen: set = set()
    while pending:
        mod = pending.pop()
        if mod in seen:
            continue
        seen.add(mod)
        if lib_stem and mod == lib_stem:
            try:
                pending += _bind(ast_mod.parse(lib.get("code") or ""))
            except SyntaxError:
                return []                     # reported by the library syntax check
            continue
        if mod.startswith("framework."):
            short = mod[len("framework."):]
            rec = surface.get(short)
            if isinstance(rec, dict):
                _add_module(rec)
            if short in packages or f"{short}.__init__" in surface:
                # A star import of a PACKAGE (`from framework.ATLibrary import *`, which the
                # corpus libraries do) exports whatever its __init__ chose; the surface cannot
                # say which, so take the union of every submodule's names plus the submodule
                # names themselves — a superset, so this under-reports rather than guesses.
                for k, r in surface.items():
                    if k.startswith(short + ".") and isinstance(r, dict):
                        _add_module(r)
                        defined.add(k[len(short) + 1:].split(".")[0])
            elif not isinstance(rec, dict):
                return []                     # a framework module the surface has never seen
            if short == "ATPackets":
                defined.update(_SCAPY_STAR_NAMES)
            continue
        return []                             # scapy.all, os.path, ... — cannot judge

    spans = [(c.name, c.lineno, c.end_lineno or c.lineno)
             for c in tree.body if isinstance(c, ast_mod.ClassDef)]

    def _where(line: int) -> str:
        return next((n for n, a, b in spans if a <= line <= b), "module level")

    loads: Dict[str, List[int]] = {}
    for node in ast_mod.walk(tree):
        if isinstance(node, ast_mod.Name) and isinstance(node.ctx, ast_mod.Load) \
                and node.id not in defined:
            loads.setdefault(node.id, []).append(node.lineno)
    out: List[str] = []
    for name, lines in sorted(loads.items(), key=lambda kv: min(kv[1]))[:12]:
        lines = sorted(set(lines))
        more = f" (+{len(lines) - 1} more)" if len(lines) > 1 else ""
        out.append(
            f"unbound name: `{name}` at line {lines[0]}{more} in {_where(lines[0])} — nothing "
            f"defines it: not the frame, not {lib['name'] if lib_stem else 'a suite library'}, "
            f"not any star-imported framework module. NameError the first time it runs")
    return out


def _lint_port_owner(tree, code: str) -> List[str]:
    """A port selected on a switch that does not own it: `peer.cmd('interface {}'.format(
    portPeer.name))` — `portPeer` is the DUT's end of the neighbour link (`dutA.portPeer`),
    the neighbour's own end is `peer.portDut`. Only the DUT/neighbour boundary is judged:
    a stack handle configuring a member's port (`stk_a` for `dutA.portA`) is legitimate,
    so mismatches between DUT-side handles are left alone."""
    import ast as ast_mod
    owners: Dict[str, str] = {}
    for m in re.finditer(r"^\s*(\w+)\s*=\s*(\w+)\.(port\w+)\s*$", code, re.M):
        owners[m.group(1)] = m.group(2)                  # portPeer = dutA.portPeer
    peer = next((m.group(1) for m in re.finditer(r"^\s*(\w+)\s*=\s*self(?:\.testSet)?\.peer\s*$",
                                                 code, re.M)), "peer")
    out: List[str] = []
    for node in ast_mod.walk(tree):
        if not (isinstance(node, ast_mod.Call) and isinstance(node.func, ast_mod.Attribute)
                and node.func.attr == "cmd" and isinstance(node.func.value, ast_mod.Name)
                and node.args):
            continue
        dev = node.func.value.id
        a0 = node.args[0]
        text, exprs = None, []
        if (isinstance(a0, ast_mod.Call) and isinstance(a0.func, ast_mod.Attribute)
                and a0.func.attr == "format" and isinstance(a0.func.value, ast_mod.Constant)
                and isinstance(a0.func.value.value, str)):
            text, exprs = a0.func.value.value, list(a0.args)
        elif isinstance(a0, ast_mod.JoinedStr):
            text = "".join(str(v.value) for v in a0.values if isinstance(v, ast_mod.Constant))
            exprs = [v.value for v in a0.values if isinstance(v, ast_mod.FormattedValue)]
        elif (isinstance(a0, ast_mod.BinOp) and isinstance(a0.op, ast_mod.Add)
                and isinstance(a0.left, ast_mod.Constant) and isinstance(a0.left.value, str)):
            text, exprs = a0.left.value, [a0.right]
        if not text or not text.lstrip().lower().startswith("interface"):
            continue
        for pe in exprs:
            if isinstance(pe, ast_mod.Attribute) and pe.attr == "name":
                pe = pe.value
            owner = label = None
            if isinstance(pe, ast_mod.Attribute) and isinstance(pe.value, ast_mod.Name) \
                    and pe.attr.startswith("port"):
                owner, label = pe.value.id, f"{pe.value.id}.{pe.attr}"
            elif isinstance(pe, ast_mod.Name) and pe.id in owners:
                owner, label = owners[pe.id], pe.id
            if owner and (dev == peer) != (owner == peer):
                out.append(
                    f"line {node.lineno}: `{dev}.cmd('interface ...')` selects `{label}`, which "
                    f"is {owner}'s port, on {dev} — the neighbour's own end of the link is "
                    f"`{peer}.portDut` and the DUT's end is `portPeer`; a port name only exists "
                    f"on the switch it belongs to")
    return out


# Mode-navigation and read-only commands are not "state the suite owns": every method
# re-enters `interface <port>` for itself, and a `show` changes nothing.
_SUITE_NAV_CMD_RX = re.compile(
    r"^(interface\b|exit\b|end\b|enable\b|conf(igure)?(\s+t(erminal)?)?\b|write\b|show\b|do\b)", re.I)


def _cmd_literals(fn_node) -> List[Tuple[str, str, int]]:
    """(device, command text, line) for every `<dev>.cmd(<literal>)` in a function — a
    string constant, a `'...'.format(...)` template or an f-string, placeholders kept as
    `{}` so `'interface {}'` compares as a template. Whitespace-normalised, lower-cased."""
    import ast as ast_mod
    out: List[Tuple[str, str, int]] = []
    for n in ast_mod.walk(fn_node):
        if not (isinstance(n, ast_mod.Call) and isinstance(n.func, ast_mod.Attribute)
                and n.func.attr == "cmd" and isinstance(n.func.value, ast_mod.Name) and n.args):
            continue
        a0 = n.args[0]
        text = None
        if isinstance(a0, ast_mod.Constant) and isinstance(a0.value, str):
            text = a0.value
        elif (isinstance(a0, ast_mod.Call) and isinstance(a0.func, ast_mod.Attribute)
                and a0.func.attr == "format" and isinstance(a0.func.value, ast_mod.Constant)
                and isinstance(a0.func.value.value, str)):
            text = a0.func.value.value
        elif isinstance(a0, ast_mod.JoinedStr):
            text = "".join(str(v.value) if isinstance(v, ast_mod.Constant) else "{}" for v in a0.values)
        if text and text.strip():
            out.append((n.func.value.id, " ".join(text.split()).lower(), n.lineno))
    return out


def _lint_suite_owned_commands(tree, code: str) -> List[str]:
    """G8(b) (RC6 of PLAN-fix-units-guardrails; reworked 2026-09-15 per Terrence's call on the
    T44297 proof run). The suite's `TestSet.configure()` owns a command for the whole run. A case
    is FREE to unset it (`no X`) when its own step needs to — a transmit-only negative test does
    exactly that (T44297 tc25: `no lldp receive`) — PROVIDED it re-sets it, so the suite baseline
    is whole for the cases behind it. What leaks, and all this flags, is an unset that is NEVER
    re-set later (fix run 5 put `no lldp run` in tc1's tear_down and never restored it — 36 cases
    behind it ran with LLDP off). A re-set is the cure, so a re-set is never flagged; a redundant
    re-issue is not state harm, so that is dropped too. Deterministic, cross-case, no model; a
    POLICY finding (the reviewer is the authority — a case may legitimately own the tail of a
    run). Mode navigation and `show` are not state. Because restoration is judged over the WHOLE
    script, this is an Assemble/Review check, not an arrival one: a later case that restores the
    unset may not be generated yet, so `_arrival_refusal` never refuses a unit on it."""
    import ast as ast_mod
    classes = [n for n in tree.body if isinstance(n, ast_mod.ClassDef)]

    def _base_has(c, word):
        return any(word in getattr(b, "attr", getattr(b, "id", "")) for b in c.bases)

    owned: Dict[Tuple[str, str], str] = {}                 # (dev, cmd) -> which suite method
    for c in classes:
        if not _base_has(c, "TestSet"):
            continue
        for m in c.body:
            if isinstance(m, ast_mod.FunctionDef) and m.name in ("configure", "tear_down"):
                for dev, cmd, _ln in _cmd_literals(m):
                    if not _SUITE_NAV_CMD_RX.match(cmd):
                        owned.setdefault((dev, cmd), m.name)
    if not owned:
        return []

    # Every unset and re-set of a suite-owned command a CASE issues, tagged with an execution
    # position (case order in the file, then configure < main < tear_down, then line) so
    # "re-set LATER" is a strict ordering. A re-set is a case re-issuing the suite's own `X`; an
    # unset is a case issuing `no X` against it. A re-set later than the unset (same case or a
    # later one) means the suite baseline is whole for the cases behind it — a well-formed
    # negative test (T44297 tc25: `no lldp receive` then `lldp receive`). An unset with no later
    # re-set leaks (fix run 5's tc1). A redundant re-issue is not state harm, so it is dropped.
    _PHASE = {"configure": 0, "main": 1, "tear_down": 2}
    unsets: List[tuple] = []
    resets: Dict[Tuple[str, str], List[tuple]] = {}
    cases = [c for c in classes if _base_has(c, "TestCase")]
    for ci, c in enumerate(cases):
        for m in c.body:
            if not isinstance(m, ast_mod.FunctionDef):
                continue
            phase = _PHASE.get(m.name, 1)
            for dev, cmd, ln in _cmd_literals(m):
                if _SUITE_NAV_CMD_RX.match(cmd):
                    continue
                pos = (ci, phase, ln)
                if cmd.startswith("no ") and (dev, cmd[3:]) in owned:
                    unsets.append((dev, cmd[3:], pos, c.name, m.name, ln))
                elif not cmd.startswith("no ") and (dev, cmd) in owned:
                    resets.setdefault((dev, cmd), []).append(pos)

    out: List[str] = []
    for dev, base, pos, cname, mname, ln in unsets:
        if any(rp > pos for rp in resets.get((dev, base), [])):
            continue                                       # re-set later — a well-formed override
        owner = owned.get((dev, base))
        out.append(
            f"suite-owned: {cname}.{mname}() line {ln} unsets `{base}` (`no {base}`) on {dev}, "
            f"which TestSet.{owner}() issues for the whole run — the suite owns it — and no "
            f"later case re-sets it, so it leaks to every case after this one")
    return out


# --- D4 (PLAN-fix-units-guardrails, 2026-09-15): a field must exist on the layer it is read from
#
# Fix run 5's tc6 read `getattr(basicLayer, 'port_desc', None)` off `lldp_basic`, whose real
# fields are chassis_id … ttl_val — no port_desc, sys_name or sys_desc. The default made every
# read silently None and the case passed on nothing. Syntax and structure checks cannot see it;
# only the layer's own field list can. `ask-ck/tools/harvest_framework_surface.py` stores that
# list as `classes[<layer>].fields` in the surface doc; without it this lint is silent.

# What every scapy `Packet` carries besides its own fields — methods and bookkeeping the script
# may legitimately reach through `pkt[<layer>]`. Not judged.
_SCAPY_PACKET_ATTRS = frozenset("""
    payload underlayer name fields fields_desc default_fields overloaded_fields time sent_time
    original direction sniffed_on wirelen explicit raw_packet_cache aliastypes packetfields
    show show2 summary mysummary haslayer getlayer firstlayer lastlayer layers build do_build
    command copy sprintf answers hashret getfieldval getfield_and_val setfieldval delfieldval
    get_field fieldtype add_payload remove_payload guess_payload_class dissect do_dissect
    extract_padding hide_defaults clone_with canvas_dump psdump pdfdump svgdump json route
    src dst decode_payload_as display fragment iterpayloads
""".split())


def _surface_layer_fields(surface: Optional[dict] = None) -> Dict[str, List[str]]:
    """{layer: [its real fields]} from the surface doc's ATPackets record. Only layers whose
    record carries a non-empty `fields` list are returned — the rest cannot be judged."""
    doc = surface if surface is not None else (_framework_surface_doc() or {})
    ap = doc.get("ATPackets") or doc.get("framework/ATPackets") or {}
    out: Dict[str, List[str]] = {}
    for name, rec in (ap.get("classes") or {}).items():
        fields = rec.get("fields") if isinstance(rec, dict) else None
        if isinstance(fields, list) and fields:
            out[name] = [str(f) for f in fields]
    return out


def _lint_layer_fields(tree, layer_fields: Optional[Dict[str, List[str]]] = None) -> List[str]:
    """Every attribute read off a `framework.ATPackets` layer — `pkt[<layer>].<f>`, a name bound
    from `pkt[<layer>]` / `pkt.getlayer(<layer>)` then `.<f>`, or `getattr`/`hasattr` on either
    with a literal name — must be a field the layer declares, or a scapy `Packet` attribute.

    Scoping is flat, like `_lint_unbound_names`: a name bound from a layer anywhere counts as
    that layer everywhere, and a name bound from two layers is judged against the union. A name
    that is ALSO bound from something that is not a layer is ambiguous and is not judged.
    Silent for a layer with no field list, and entirely when the surface has none.
    """
    import ast as ast_mod
    known = layer_fields if layer_fields is not None else _surface_layer_fields()
    if not known:
        return []

    def _layer_of(node) -> Optional[str]:
        if (isinstance(node, ast_mod.Subscript) and isinstance(node.slice, ast_mod.Name)
                and node.slice.id in known):
            return node.slice.id
        if (isinstance(node, ast_mod.Call) and isinstance(node.func, ast_mod.Attribute)
                and node.func.attr == "getlayer" and node.args
                and isinstance(node.args[0], ast_mod.Name) and node.args[0].id in known):
            return node.args[0].id
        if isinstance(node, ast_mod.IfExp):
            return _layer_of(node.body) or _layer_of(node.orelse)
        return None

    bound: Dict[str, set] = {}
    ambiguous: set = set()
    for node in ast_mod.walk(tree):
        if (isinstance(node, ast_mod.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast_mod.Name)):
            lay = _layer_of(node.value)
            if lay:
                bound.setdefault(node.targets[0].id, set()).add(lay)
                continue
            if isinstance(node.value, ast_mod.Constant) and node.value.value is None:
                continue                              # `x = None` before the real bind
            ambiguous.add(node.targets[0].id)
        elif isinstance(node, ast_mod.arg):
            ambiguous.add(node.arg)
    for node in ast_mod.walk(tree):                   # for-targets, with-as, comprehensions, walrus
        if isinstance(node, (ast_mod.For, ast_mod.AsyncFor, ast_mod.comprehension)):
            for t in ast_mod.walk(node.target):
                if isinstance(t, ast_mod.Name):
                    ambiguous.add(t.id)
        elif isinstance(node, ast_mod.withitem) and node.optional_vars is not None:
            for t in ast_mod.walk(node.optional_vars):
                if isinstance(t, ast_mod.Name):
                    ambiguous.add(t.id)
        elif isinstance(node, (ast_mod.NamedExpr, ast_mod.AugAssign, ast_mod.AnnAssign)):
            t = node.target
            if isinstance(t, ast_mod.Name):
                ambiguous.add(t.id)
        elif isinstance(node, ast_mod.Assign) and (len(node.targets) != 1
                                                   or not isinstance(node.targets[0], ast_mod.Name)):
            for tgt in node.targets:
                for t in ast_mod.walk(tgt):
                    if isinstance(t, ast_mod.Name):
                        ambiguous.add(t.id)
    bound = {v: lays for v, lays in bound.items() if v not in ambiguous}

    def _layers_of_target(node) -> set:
        lay = _layer_of(node)
        if lay:
            return {lay}
        if isinstance(node, ast_mod.Name) and node.id in bound:
            return bound[node.id]
        return set()

    spans = [(c.name, c.lineno, c.end_lineno or c.lineno)
             for c in tree.body if isinstance(c, ast_mod.ClassDef)]

    def _where(line: int) -> str:
        return next((n for n, a, b in spans if a <= line <= b), "module level")

    hits: Dict[tuple, List[int]] = {}
    for node in ast_mod.walk(tree):
        if isinstance(node, ast_mod.Attribute):
            lays, field = _layers_of_target(node.value), node.attr
        elif (isinstance(node, ast_mod.Call) and isinstance(node.func, ast_mod.Name)
              and node.func.id in ("getattr", "hasattr") and len(node.args) >= 2
              and isinstance(node.args[1], ast_mod.Constant) and isinstance(node.args[1].value, str)):
            lays, field = _layers_of_target(node.args[0]), node.args[1].value
        else:
            continue
        if not lays or field.startswith("_") or field in _SCAPY_PACKET_ATTRS:
            continue
        if any(field in known[lay] for lay in lays):
            continue
        hits.setdefault((tuple(sorted(lays)), field), []).append(node.lineno)

    out: List[str] = []
    for (lays, field), lines in sorted(hits.items(), key=lambda kv: min(kv[1]))[:12]:
        lines = sorted(set(lines))
        more = f" (+{len(lines) - 1} more)" if len(lines) > 1 else ""
        layer = "/".join(lays)
        declared = ", ".join(known[lays[0]]) if len(lays) == 1 else \
            "; ".join(f"{lay}: {', '.join(known[lay])}" for lay in lays)
        out.append(
            f"unknown field: `{field}` at line {lines[0]}{more} in {_where(lines[0])} — `{layer}` "
            f"has no such field (declared: {declared}). A read through getattr(..., None) is "
            f"silently None and a direct read is an AttributeError, so the check observes nothing")
    return out


def _lint_verdict_echo(tree, sequence: List[dict]) -> List[str]:
    """A passed()/failed() reason that IS the step's verify or action text, verbatim. Such a
    reason restates the expectation; the log then carries no evidence of what happened.
    A warning: the reviewer decides, and the message names the fix."""
    import ast as ast_mod

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "")).strip().rstrip(".").lower()

    texts = {_norm(s.get(k)): k for s in (sequence or []) for k in ("verify", "action")
             if _norm(s.get(k))}
    out: List[str] = []
    for c in tree.body:
        if not isinstance(c, ast_mod.ClassDef):
            continue
        main = next((n for n in c.body if isinstance(n, ast_mod.FunctionDef) and n.name == "main"), None)
        if main is None:
            continue
        for node in ast_mod.walk(main):
            if (isinstance(node, ast_mod.Call) and isinstance(node.func, ast_mod.Attribute)
                    and node.func.attr in ("passed", "failed") and node.args
                    and isinstance(node.args[0], ast_mod.Constant)
                    and isinstance(node.args[0].value, str)):
                field = texts.get(_norm(node.args[0].value))
                if field:
                    out.append(
                        f"{c.name}.main() line {node.lineno}: the {node.func.attr}() reason is the "
                        f"step's {field} text verbatim — a verdict should say what was OBSERVED "
                        f"(the value, count or line), not restate what was expected")
    return out


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
            # ART shape (2026-09-07): a TestCase's own configure()/tear_down() are the
            # precondition / mirror-undo pair — config only. A verdict there is counted by
            # the framework against the case but sits outside main()'s STEP/OBSERVED
            # evidence, so the log block no longer says what was checked.
            for _hook in c.body:
                if (isinstance(_hook, ast_mod.FunctionDef) and _hook.name in ("configure", "tear_down")):
                    for _n in ast_mod.walk(_hook):
                        if (isinstance(_n, ast_mod.Call) and isinstance(_n.func, ast_mod.Attribute)
                                and _n.func.attr in ("passed", "failed")
                                and isinstance(_n.func.value, ast_mod.Name) and _n.func.value.id == "self"):
                            errors.append(f"contract: {c.name}.{_hook.name}() line {_n.lineno} calls "
                                          f"self.{_n.func.attr}() — configure()/tear_down() are config "
                                          f"only; the verdict belongs in main()")
                            break
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

        # 2b-0. BINDING IS THE FRAME'S. `TestSet.init()` discovers the topology through the
        # framework (`get_all_port_links()`) and picks each link by the MEDIA the DUT reports
        # (`_ck_discover` / `_ck_bind_link`, 2026-09-21). That cannot be checked offline —
        # media belongs to the pluggable — so a port bound any other way carries no media
        # guarantee, and a run bound to the wrong media reports a PRODUCT failure that is
        # really a cabling error (TOPOLOGY-PROFILES.md).
        #
        # Three errors, all about the same invariant:
        #   (a) `setup.init_portlink()` anywhere but inside a legacy `_ck_bind_link` body —
        #       the frame never calls it (first-unused matching is exactly what cannot tell
        #       copper from fibre), so any call is a bypass;
        #   (b) `setup.init_swi()` / `init_stk()` outside `TestSet.init()` and the frame's
        #       helpers — a UNIT binding its own device (the T33234 setup-unit failure);
        #   (c) reading a bound port attribute while never calling the helper — the port is
        #       unbound, so this dies with AttributeError on first use (seen 2026-07-28).
        _helper = "_ck_bind_link"
        _frame_fns = {"init", _helper, "_ck_discover"}
        _fn_lines = {}
        for _fd in ast_mod.walk(tree):
            if isinstance(_fd, ast_mod.FunctionDef) and _fd.name in _frame_fns:
                _fn_lines.setdefault(_fd.name, set()).update(
                    range(_fd.lineno, (_fd.end_lineno or _fd.lineno) + 1))
        _helper_lines = _fn_lines.get(_helper, set())
        _frame_lines = set().union(*_fn_lines.values()) if _fn_lines else set()
        _calls_helper = any(
            isinstance(n, ast_mod.Call) and (
                (isinstance(n.func, ast_mod.Attribute) and n.func.attr == _helper)
                or (isinstance(n.func, ast_mod.Name) and n.func.id == _helper))
            for n in ast_mod.walk(tree))
        for _n in ast_mod.walk(tree):
            if not (isinstance(_n, ast_mod.Call) and isinstance(_n.func, ast_mod.Attribute)):
                continue
            if _n.func.attr == "init_portlink" and _n.lineno not in _helper_lines:
                errors.append(
                    f"line {_n.lineno}: calls setup.init_portlink() directly, which skips the "
                    f"run-time MEDIA assertion. The frame binds every link in `TestSet.init()` "
                    f"through `self.{_helper}(setup, <dut>, '<role>')`, choosing the link by "
                    f"the media the DUT reports — a port bound without that check can be the "
                    f"wrong media, and the resulting failure reads as a product defect rather "
                    f"than a cabling error. See ask-ck/functions/pytest-creator/TOPOLOGY-PROFILES.md")
            elif (_n.func.attr in ("init_swi", "init_stk") and _frame_lines
                  and _n.lineno not in _frame_lines):
                errors.append(
                    f"line {_n.lineno}: calls setup.{_n.func.attr}() outside `TestSet.init()` — "
                    f"binding devices is the frame's job. Units reach the devices init() bound "
                    f"through `self.testSet.<name>`; if the case needs another device, the "
                    f"sequence is wrong — say so in a comment rather than binding it here")
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
                      "portA", "portB", "portPeer", "portDut", "portFibre", "portCuSfp",
                      "ethA", "name"}
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

        # 2b-0c. Bench-integration checks (decision 2, 2026-09-07): unbound port attribute,
        # call shape against the framework surface, capture with no wait. See the function.
        _bi_errors, _bi_warnings = _lint_bench_integration(tree, code, _framework_surface_doc())
        errors.extend(_bi_errors)
        warnings.extend(_bi_warnings)

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
        # The library ships and is imported at module load, so a syntax error in it kills
        # the whole suite before the first case runs.
        try:
            compile(lib.get("code") or "", lib["name"], "exec")
        except SyntaxError as e:
            errors.append(f"syntax: {lib['name']} line {e.lineno}: {e.msg}")

    # 3b. Names nothing defines, a port on the wrong switch, echoed verdicts (2026-09-08) —
    #     see the three helpers above. Separate append sites on purpose: the error-class
    #     test counts them, and each has its own authority (blocking / policy / warning).
    if tree is not None:
        for _e in _lint_unbound_names(tree, lib):
            errors.append(_e)
        for _e in _lint_port_owner(tree, code):
            errors.append(_e)
        for _e in _lint_suite_owned_commands(tree, code):       # G8(b), 2026-09-14
            errors.append(_e)
        for _e in _lint_layer_fields(tree):                     # D4, 2026-09-15
            errors.append(_e)
        warnings.extend(_lint_verdict_echo(tree, (sess.step2 or {}).get("sequence") or []))

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

    # 5. PEP 8. Last, because it is the only check that is about how the script READS
    # rather than whether it works, and its findings should sit below the ones that matter.
    _pep8, _pep8_unavailable = _pep8_findings(code)
    if _pep8_unavailable:
        warnings.append(
            f"style NOT checked — pycodestyle unavailable ({_pep8_unavailable}). "
            f"Install it (`pip install -r ask-ck/CK-main/requirements.txt`) or treat this "
            f"script's style as unreviewed; a clean warning list below does not mean the "
            f"style is clean.")
    warnings.extend(_pep8)

    blocking, policy = _split_lint_errors(errors)
    result = {"ok": not errors, "errors": errors, "warnings": warnings,
              # Style findings are also surfaced on their own key so the UI (and any
              # future auto-fix pass) can address them without string-matching the
              # general warning list.
              "pep8": _pep8, "pep8_unavailable": _pep8_unavailable,
              "pep8_max_line": _PEP8_MAX_LINE,
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


# A library member's tag line, at column 0: `# ART <path> lines a-b`, `# SVT …`, `# legacy …`
# (`_fragment_tag`) or `# AI: dependency `name` of <tag>` for one R1(a)'s closure pulled in.
# NOT `_PROVENANCE_TAG_RX`, which is a different job (stripping model-echoed scaffolding) and
# would not match `AI:` at all — its `(AI)\s+` cannot cross the colon.
_LIB_MEMBER_TAG_RX = re.compile(r"^#\s*(?:ART|SVT|legacy|AI:?)\s+\S")
_LIB_IMPORT_RX = re.compile(r"^(?:import|from)\s+\S")


def _split_library(code: str):
    """(preamble_lines, [(tag, member_lines), …]) for a library file.

    A file with NO recognisable tag line is ALL preamble. That is the real case, not a
    hypothetical: the T33234 library that shipped in `3c680c9` is an LLM-authored helper module
    with zero provenance tags, and merging must not shred it.
    """
    lines = code.splitlines()
    idx = [i for i, ln in enumerate(lines) if _LIB_MEMBER_TAG_RX.match(ln)]
    if not idx:
        return lines, []
    members = []
    for a, b in zip(idx, idx[1:] + [len(lines)]):
        members.append((lines[a].strip(), lines[a:b]))
    return lines[:idx[0]], members


def _merge_library_code(existing: str, incoming: str) -> str:
    """Merge a freshly built library into the one already on disk, keyed by provenance tag.

    Every script in a group now imports ONE module, so two scripts saving in the same group
    would otherwise have the second silently destroy the first's members. Rules (R1(b) D3 —
    this pass is additive; PRUNE is a separate pass and nothing here removes anything):

    * a tag already present is left BYTE FOR BYTE, so a reviewer's hand edit to a merged
      member survives the next save;
    * a tag not present is appended, in `_build_library` order;
    * imports the incoming file needs are inserted after the last top-level import already
      there (always safe in Python), or after the header when the file has none.
    """
    if not (existing or "").strip():
        return incoming
    _pre, have = _split_library(existing)
    _, want = _split_library(incoming)
    seen = {tag for tag, _ in have}
    add = [m for tag, m in want if tag not in seen]

    lines = existing.splitlines()
    # imports the incoming library declares that the existing file does not
    inc_imports = [ln for ln in (incoming.splitlines()) if _LIB_IMPORT_RX.match(ln)]
    cur_imports = {ln.strip() for ln in lines if _LIB_IMPORT_RX.match(ln)}
    missing = [ln for ln in inc_imports if ln.strip() not in cur_imports]
    if missing:
        at = max((i for i, ln in enumerate(lines) if _LIB_IMPORT_RX.match(ln)), default=-1)
        if at < 0:
            # No import to anchor to. Sit them at the END OF THE LEADING HEADER — the run of
            # shebang / comment / blank lines at the top — never at the end of the preamble:
            # in an UNTAGGED file the preamble is the whole file, so that put the imports
            # after the code that needs them (caught by test_imports_land_after_the_header).
            at = -1
            for i, ln in enumerate(lines):
                if ln.strip() and not ln.lstrip().startswith("#"):
                    break
                at = i
        lines[at + 1:at + 1] = missing
    for m in add:
        lines += ["", ""] + [ln for ln in m if ln.strip() or True]
    return "\n".join(lines).rstrip("\n") + "\n"


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
        if not _NAME_RX.match(stem[:-3]) or ".." in stem:   # base (sans .py) must be safe
            raise HTTPException(400, "Invalid library file name (letters/digits/.-_ only, no '..').")
        lib_path = script_path.parent / stem            # basename only — never the raw name
        # Belt-and-suspenders: the resolved path must stay inside the script's own dir.
        if lib_path.parent.resolve() != script_path.parent.resolve():
            raise HTTPException(400, "Library file must be written alongside the script.")
        # MERGE, never overwrite (R1(b)): the library is per GROUP now, so every script in this
        # folder writes this same path. Overwriting would drop the other scripts' members.
        code = lib["code"]
        if lib_path.exists():
            code = _merge_library_code(lib_path.read_text(encoding="utf-8"), code)
        lib_path.write_text(code, encoding="utf-8")
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
        "message": ("Run ask-ck/tools/build_db.py --fresh to build the script index."
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
async def load_case(key: str, request: Request, fresh: bool = False):
    data = _data(request)
    # Per-case lock (PLAN-auth-and-case-locking.md Phase 1). If another tab/user holds a
    # LIVE lock, serve a read-only snapshot and touch nothing — pt_sessions is shared
    # across tabs in this one process, so _sweep_stale_runs here would mutate THEIR live
    # object, and the hydration _pt_persist would 409.
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

    if fresh:
        # "Load Case & New Session" (the sibling of "& Continue"). load_case REUSES an
        # existing session by design — that is what preserves the step2-step8 work across a
        # reload — so an upstream objective/steps edit + re-export is NOT picked up by a plain
        # load. This is the explicit opt-in to throw the stored session away and rebuild from
        # the on-disk refined bundle (the same bundle `push` reads). Only reachable holding the
        # lock: the not-by_me branch above already returned a read-only snapshot, so we never
        # overwrite a session another seat is actively editing.
        #
        # Resolve the disk bundle BEFORE deleting anything: _find_refined_case raises 404 for a
        # case with no drop-in, and we must not destroy the persisted session only to fail the
        # rebuild. If the read succeeds, discard the old session (cache + ck.db row) and build
        # fresh from disk.
        group, payload, trace = _find_refined_case(key)
        pt_sessions.pop(key, None)
        dbx.delete_session("pt", key)
        sess = PtSession(key=key, group=group, payload=payload, traceability=trace)
    else:
        sess = pt_sessions.get(key) or _pt_load(key)
        if not sess:
            group, payload, trace = _find_refined_case(key)
            sess = PtSession(key=key, group=group, payload=payload, traceability=trace)
    _sweep_stale_runs(sess)
    # The LLM choice is per seat since 2026-09-10 (X-CK-LLM, resolved at dispatch); nothing
    # is copied onto the case any more. The response field below stays for API compatibility.
    changed = False
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
        "gen_state": _gen_state(sess.step6 or {}),
    }


@router.get("/session/{key}")
async def get_session(key: str):
    sess = _pt_get(key)
    return {"session": safe_session_dict(sess),   # redacts llm_config secrets
            "gen_state": _gen_state(sess.step6 or {})}


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
        claim = _normalize_claim(s.get("claim"))
        if claim:
            s["claim"] = claim
        else:
            s.pop("claim", None)
    sanity = _sanity_flags(_parsed_list(parsed, "sanity"), len(sequence))
    # Every Zephyr step must map to >=1 sequence step, or that slice of the objective is
    # untested. Surfaced to the reviewer rather than enforced silently.
    coverage = _coverage_report(sequence, fields["steps"])
    if not coverage["ok"]:
        print(f"[pt] {key} coverage gap — {coverage['warning']}")
    # Applied to a FRESHLY reloaded session, not the snapshot loaded before a 600s LLM
    # call — see _pt_persist_fresh. This endpoint owns step2 (and the invalidation it
    # implies); anything a concurrent click changed elsewhere is preserved.
    _step2 = {"sequence": sequence, "notes": notes,
              "coverage": coverage, "sanity": sanity,
              "confirmed": False,
              "provenance": {"llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                             "prompt": meta.get("prompt", ""),
                             "response": meta.get("content", "")[:20000]}}

    def _apply(fresh: PtSession) -> None:
        # DROP STEP-NUMBERED DOWNSTREAM DATA WHEN THE SEQUENCE IS RENUMBERED
        # (2026-09-02, Terrence's call, after AWPTCM-T44297).
        #
        # `_invalidate_from` only un-CONFIRMS later steps; it leaves their payloads intact.
        # That is right for most edits and wrong for a re-extraction, because step 5's
        # fragments carry `maps_to: [n]` -- step numbers into the sequence that just
        # changed. T44297 went from 13 steps to 31 and the pool survived with its old
        # mapping, so six steps showed fragment cards while reporting no fragment selected,
        # and the fragments feeding Generate were attributed to steps they never served.
        #
        # Only step 5 is cleared, and only when the shape actually changed: a re-extract
        # that reproduces the same sequence must not throw away a Gather that costs minutes
        # and real money (measured: 334.8s / $1.13 on this case).
        #
        # step3.selections has the same {stepN: ...} exposure and is deliberately NOT
        # cleared here -- Terrence chose to keep that as a reported risk rather than
        # destroy a reviewer's script picks automatically. See the 2026-09-02 log entry.
        prev_shape = _sequence_shape((fresh.step2 or {}).get("sequence") or [])
        fresh.step2 = _step2
        _invalidate_from(fresh, 2)
        if prev_shape and prev_shape != _sequence_shape(sequence):
            if (fresh.step5 or {}).get("fragments"):
                print(f"[pt] {key}: sequence renumbered — dropping {len(fresh.step5['fragments'])} "
                      f"gathered fragment(s) whose maps_to referenced the old step numbers")
            fresh.step5 = {}

    _pt_persist_fresh(key, _apply)
    return {"sequence": sequence, "notes": notes, "coverage": coverage, "sanity": sanity}


@router.post("/save_sequence/{key}")
async def save_sequence(key: str, body: dict = Body(...)):
    """User edits to the sequence before confirming."""
    sess = _pt_get(key)
    sequence = body.get("sequence")
    if not isinstance(sequence, list) or not sequence:
        raise HTTPException(400, "Body must include a non-empty 'sequence' list.")
    prev_seq = (sess.step2 or {}).get("sequence") or []
    prev_by_n = {str(p.get("n")): p for p in prev_seq}
    for i, s in enumerate(sequence):
        s["n"] = i + 1
        _collapse_step_text(s)
        # The Sequence table round-trips only n/action/verify/from; `kind` and `claim` were
        # silently lost on every Save (a setup step came back as a TestCase). Carry them over
        # from the stored row at the same position — but only when its action text is the
        # same row, so a drag-reorder never pins another step's kind or claim onto this one.
        old = prev_by_n.get(str(s["n"]))
        if old and " ".join(str(old.get("action") or "").split()) == (s.get("action") or ""):
            for fld in ("kind", "claim", "zephyr_step_idx"):
                if s.get(fld) in (None, "") and old.get(fld) not in (None, ""):
                    s[fld] = old[fld]
        else:
            claim = _normalize_claim(s.get("claim"))
            if claim:
                s["claim"] = claim
            else:
                s.pop("claim", None)
    # Re-check coverage on manual edits too — deleting a row in the UI can drop the last
    # entry covering a Zephyr step just as easily as the LLM can.
    coverage = _coverage_report(sequence, _case_payload_fields(sess)["steps"])
    # The sanity flags name step NUMBERS; once the steps are re-shaped they point at the
    # wrong rows, so they are kept only while the shape is unchanged.
    sanity = (sess.step2 or {}).get("sanity") or []
    if _sequence_shape(prev_seq) != _sequence_shape(sequence):
        sanity = []
    sess.step2 = {**(sess.step2 or {}), "sequence": sequence,
                  "coverage": coverage, "sanity": sanity, "confirmed": False}
    _invalidate_from(sess, 2)
    _pt_persist(sess)
    return {"sequence": sequence, "coverage": coverage, "sanity": sanity}


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
        }, llm_config=_llm_cfg_for(sess, "step_match"), timeout=300, dry_run=True)
        return _provenance_preview(meta)

    llm_matches = []
    if candidates:
        meta = await run_in_threadpool(run_prompt, "pt_match_scripts.jinja", {
            "case_key": key, "sequence": sequence,
            "user_inputs": user_inputs, "candidates": candidates,
        }, llm_config=_llm_cfg_for(sess, "step_match"), timeout=300)
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


def _persist_step_matches(key: str, step_n: int, matches: List[dict],
                          provenance: Optional[dict] = None) -> None:
    """Merge one step's LLM suggestions into step3.step_matches and persist.

    Takes the case KEY, not a session object, and merges onto a freshly reloaded copy via
    `_pt_persist_fresh`. It used to take the caller's pre-LLM snapshot, which is how a
    31-step suggest-all lost 8 completed calls to HTTP 409 on 2026-09-02: the reviewer
    clicking "Save Selections" between the load and the write made every snapshot stale.
    The merge must read `step_matches` from the CURRENT row anyway, or a concurrent
    suggest's candidates would be dropped on the floor.

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
    def _apply(fresh: PtSession) -> None:
        step3 = fresh.step3 or {}
        if provenance is not None:
            step3 = {**step3, "provenance": provenance}
        sm = dict(step3.get("step_matches") or {})
        merged = {m0.get("id"): _match_slim(m0) for m0 in (sm.get(str(step_n)) or [])
                  if isinstance(m0, dict) and m0.get("id")}
        for m0 in matches or []:
            if isinstance(m0, dict) and m0.get("id"):
                merged[m0["id"]] = _match_slim(m0)
        sm[str(step_n)] = list(merged.values())
        fresh.step3 = {**step3, "step_matches": sm}

    _pt_persist_fresh(key, _apply)


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
        }, llm_config=_llm_cfg_for(sess, "step_match"), timeout=300, dry_run=True)
        return _provenance_preview(meta)

    llm_matches = []
    if candidates:
        meta = await run_in_threadpool(run_prompt, "pt_match_scripts.jinja", {
            "case_key": key, "sequence": one_seq,
            "user_inputs": user_inputs, "candidates": candidates,
        }, llm_config=_llm_cfg_for(sess, "step_match"), timeout=300)
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
    # Handed to _persist_step_matches rather than written onto `sess` here: that snapshot
    # predates a 30-50s LLM call and persisting it is what produced the 409s (see
    # _pt_persist_fresh). Both fields land in one write on one fresh copy.
    provenance = None
    if candidates:
        provenance = {"llm": {k: meta.get(k) for k in
                              ("provider", "model", "auth_method")},
                      "prompt": meta.get("prompt", ""),
                      "response": meta.get("content", "")[:20000],
                      "step_n": step_n}
    _persist_step_matches(key, step_n, matches, provenance=provenance)
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
    # THE MERGE ITSELF runs on the fresh copy, not just the write (2026-09-02).
    #
    # This is why _pt_persist_fresh takes a callback rather than a finished payload: the
    # step5 pool is merged INTO what is already stored, so reading `prev` from the
    # snapshot loaded before a 600s LLM call would silently discard any fragment
    # selection the reviewer made while waiting -- the same class of loss as the 409s,
    # but silent, which is worse. `_selections_fingerprint` reads step3 and must see the
    # current selections for the same reason.
    out: Dict[str, Any] = {}

    def _apply(fresh: PtSession) -> None:
        prev = fresh.step5 or {}
        pool = list(prev.get("fragments") or [])
        have = {_frag_key(f) for f in pool}
        by_key = {_frag_key(pf): pf for pf in pool}
        selected = list(prev.get("selected") or [])
        sel_have = {tuple(s) if isinstance(s, (list, tuple))
                    else (s.get("source_id"), s.get("symbol"))
                    for s in selected}
        added = 0
        for f in fragments:
            k = _frag_key(f)
            if k not in have:
                pool.append(f)
                by_key[k] = f
                have.add(k)
                added += 1
            else:
                # A RE-GATHER MUST BE ABLE TO CORRECT A MAPPING (2026-09-02, AWPTCM-T44297).
                #
                # This branch used to do nothing: an already-pooled fragment kept whatever
                # `maps_to` it was first gathered with, and THIS run's freshly-derived
                # mapping was dropped on the floor. `accounting` was refreshed regardless
                # (merged_acct.update below), so the two diverged -- and the UI reads the
                # cards from accounting but the coverage pill from maps_to, so a step could
                # display three ticked fragments while reporting "no fragment selected".
                #
                # Observed after the sequence was re-extracted from 13 steps to 31: the pool
                # survived with `maps_to` keyed on the OLD numbering, so steps 14-17, 20 and
                # 27 had accounting entries that no fragment claimed. `_add_fragment` had
                # computed the right mapping (it merges each step as the loop visits it);
                # only this merge threw it away.
                #
                # REPLACE, not union (Terrence's call). On a renumbered sequence the stored
                # mapping is WRONG rather than merely incomplete, and a union would preserve
                # step numbers that no longer mean anything. This run is the only one that
                # read the current sequence, so its mapping is the authoritative one.
                #
                # `why` is replaced for the same reason: it is this run's reviewer-facing
                # justification for THIS step's text, and a stale one describes the step the
                # fragment used to serve. The card renders it, so a wrong `why` is visible.
                stale = by_key[k]
                stale["maps_to"] = list(f.get("maps_to") or [])
                if f.get("why"):
                    stale["why"] = f["why"]
            # auto-select only fragments the LLM CHOSE (not the redundant alternatives)
            if k in default_chosen and k not in sel_have:
                selected.append({"source_id": f["source_id"], "symbol": f["symbol"]})
                sel_have.add(k)

        # Merge accounting (new steps overwrite; old steps for untouched sequence numbers kept)
        merged_acct = dict(prev.get("accounting") or {})
        merged_acct.update(accounting)

        fresh.step5 = {"fragments": pool, "selected": selected, "dropped": dropped,
                       "accounting": merged_acct, "confirmed": False,
                       "selections_fingerprint": _selections_fingerprint(fresh),
                       "provenance": {"llm": {k: meta.get(k) for k in
                                              ("provider", "model", "auth_method")},
                                      "prompt": meta.get("prompt", ""),
                                      "response": meta.get("content", "")[:20000]}}
        _invalidate_from(fresh, 5)
        # The response must describe what was actually committed, so it is built here and
        # rebuilt on a retry rather than captured from a superseded attempt.
        out.clear()
        out.update({"fragments": pool, "selected": selected, "accounting": merged_acct,
                    "added": added, "dropped": len(dropped),
                    "scripts_considered": len(selections)})

    _pt_persist_fresh(key, _apply)
    return out


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
    # The script name is DERIVED, never chosen (2026-09-17). The Generate panel's Group and
    # Script-name inputs were removed with this change: a name the reviewer types cannot
    # satisfy a convention the framework parses out of the filename, and a stored name from
    # before the convention would otherwise keep winning here.
    name = _art_script_name(key)
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
    # `group` is already resolved above, and equals `_effective_group(sess)` once the naming has
    # been persisted — pass it rather than re-deriving, so the two paths cannot drift (§1).
    library = _build_library(group, fragments, data)
    skeleton = _render_skeleton(key, _case_title(data, key), sequence,
                                extra_import_lines, fragments,
                                _case_payload_fields(sess)["objective"], library)

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
        "bound_ports": _skeleton_bound_ports(skeleton),
        "library": library,
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
        # On a fresh copy: the whole point of this branch is that the evidence SURVIVES the
        # refusal, and persisting a snapshot from before a 600s call is exactly how it
        # would not (a 409 here loses the failed reply as well as the generation).
        def _apply_failure(fresh: PtSession) -> None:
            step6 = dict(fresh.step6 or {})
            attempts = list(step6.get("failed_generations") or [])
            attempts.append(_attempt)
            # Keep the last few attempts, newest last; unbounded growth here would be a
            # second storage problem rather than a forensic record.
            step6["failed_generations"] = attempts[-3:]
            fresh.step6 = step6

        _attempt = {
            "at": utc_now().isoformat(),
            "reason": failure,
            "llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
            "prompt": meta.get("prompt", ""),
            "response": meta.get("content", ""),
            "recovery": blocks["report"],
            "rejected_code": blocks["test_code"] or "",
        }
        _pt_persist_fresh(key, _apply_failure)
        raise HTTPException(
            502, f"Generation could not be reassembled: {failure} The full reply is saved "
                 f"under step6.failed_generations for inspection; generate again to retry.")
    # PLAN §1.5 — authoritative re-stamp: server-known step->fragment mapping wins
    # over anything the model self-reported, so provenance is trustworthy either way.
    stamped_code = _restamp_provenance(blocks["test_code"], fragments,
                                       meta.get("model") or "", sequence)

    # `iterations` counts up from what is STORED, so it must read the fresh copy or a
    # concurrent write would make the generation appear not to have happened.
    _committed: Dict[str, Any] = {}

    def _apply_success(fresh: PtSession) -> None:
        prev = fresh.step6 or {}
        fresh.step6 = {
            "naming": {"group": group, "name": name},
            # The frame imports the suite library the server built, so it ships with the
            # script unless the model returned its own (which then wins, as before).
            "files": {"test": {"name": file_name, "code": stamped_code},
                      "library": blocks["library"] or (
                          {"name": library["name"], "code": library["code"]}
                          if (library or {}).get("members") else None)},
            "iterations": prev.get("iterations", 0) + 1,
            "confirmed": False,
            # Phase 7.9 — the reply is stored WHOLE. It used to be cut at 20,000 chars with
            # no marker, so every stored generation was incomplete and the primary evidence
            # for transport defects was destroyed by the record meant to capture them; the
            # multi-part replies that exposed the fence bug are 37k-173k chars. `recovery`
            # is the assembly audit trail: how many messages the answer spanned, what was
            # dropped at each seam, and the model's own assembly notes.
            "provenance": {"llm": {k: meta.get(k) for k in
                                   ("provider", "model", "auth_method")},
                           "prompt": meta.get("prompt", ""),
                           "response": meta.get("content", ""),
                           "recovery": blocks["report"]},
        }
        _invalidate_from(fresh, 6)
        # Lint the copy being committed, so the stored lint always describes the stored
        # code. Re-runs on a retry, which is correct: the code is the same either way.
        _committed["lint"] = _lint_generated(fresh)
        _committed["naming"] = fresh.step6["naming"]
        _committed["files"] = fresh.step6["files"]
        _committed["iterations"] = fresh.step6["iterations"]

    _pt_persist_fresh(key, _apply_success)
    lint = _committed["lint"]
    return {"naming": _committed["naming"], "files": _committed["files"],
            "iterations": _committed["iterations"], "lint": lint,
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
    return {"written": written, "lint": lint, "naming": step6["naming"],
            "gen_state": _gen_state(step6)}


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
    # Every generated script does `import ck_media` inside _ck_discover / _ck_bind_link (fixed
    # frame), so the helper ships with EVERY run — not only when the reviewer supplied a library.
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
# Per-unit generation (PLAN-pytest-creator.md §9.5, built 2026-09-02)
#
# One LLM call per UNIT of the script — a single TestCase class, or the TestSet's
# configure()/tear_down() pair — spliced into a frame the server renders itself.
#
# The frame is NOT a model's work. §9.5 proposed a "Pass A" that asked an LLM to write
# imports, TestSet and the runner; `_render_skeleton()` already produces all of that
# deterministically, so there is nothing for a model to add and a great deal for it to get
# inconsistently wrong across N calls. Dropping Pass A removes a call AND a failure mode.
#
# UNIT IDS are stable strings ("setup", "tc1" … "tcN"), not sequence step numbers, because
# `_split_sequence` RENUMBERS: setup-kind steps become TestSet.configure() and the rest are
# renumbered contiguously, so sequence step 31 can be TestCase_29. Keying chunks on the
# sequence number would mis-file every unit on any case with a setup step.
# ---------------------------------------------------------------------------

def _skeleton_units(skeleton: str) -> List[dict]:
    """Split a rendered skeleton into the fillable units, by AST.

    Returns [{id, kind, tc_n, label, block, lines:[start,end]}] in file order, where
    `block` is the exact source text the model is asked to return filled. Read off the
    AST rather than by regex so a `class TestCase_12` mentioned inside a docstring or a
    log string can never be mistaken for a unit boundary.
    """
    import ast as ast_mod
    try:
        tree = ast_mod.parse(skeleton)
    except SyntaxError:
        return []
    lines = skeleton.split("\n")

    def _text(node) -> str:
        return "\n".join(lines[node.lineno - 1:node.end_lineno])

    units: List[dict] = []
    for node in tree.body:
        if not isinstance(node, ast_mod.ClassDef):
            continue
        m = re.fullmatch(r"TestCase_(\d+)", node.name)
        if m:
            units.append({"id": f"tc{m.group(1)}", "kind": "testcase",
                          "tc_n": int(m.group(1)), "label": node.name,
                          "block": _text(node),
                          "lines": [node.lineno, node.end_lineno]})
            continue
        if node.name == "TestSet":
            # configure() and tear_down() are ONE unit: they are a matched pair (what
            # configure sets up, tear_down reverts) and splitting them across two calls
            # would let the halves disagree about what was configured.
            meths = [b for b in node.body
                     if isinstance(b, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef))
                     and b.name in ("configure", "tear_down")]
            if meths:
                lo = min(b.lineno for b in meths)
                hi = max(b.end_lineno for b in meths)
                units.insert(0, {"id": "setup", "kind": "setup", "tc_n": None,
                                 "label": "TestSet.configure / tear_down",
                                 "block": "\n".join(lines[lo - 1:hi]),
                                 "lines": [lo, hi]})
    units.sort(key=lambda u: u["lines"][0])
    return units


def _unit_source_step(unit: dict, tc_steps: List[dict]) -> Optional[dict]:
    """The sequence row a TestCase unit implements (post-renumbering)."""
    if unit["kind"] != "testcase":
        return None
    i = (unit.get("tc_n") or 0) - 1
    return tc_steps[i] if 0 <= i < len(tc_steps) else None


def _pt_generation_context(key: str, data: dict, sess: PtSession) -> dict:
    """Everything both the per-unit prompts and the assembly need, derived once.

    Deliberately mirrors generate_script's own derivation (same fragments, same import
    lines, same skeleton call) so a per-unit run and a whole-script run start from a
    byte-identical frame. If these two ever diverge, the units stop fitting the file.
    """
    fragments = _selected_fragments(sess)
    extra_mods: List[str] = []
    extra_import_lines: List[str] = []
    for f in fragments:
        rec = (data.get("scripts_index_by_id") or {}).get(f["source_id"]) or {}
        for m in rec.get("imports", []):
            if m.startswith(("framework.", "ATPyLib.")):
                extra_mods.append(m.replace("framework.", "").replace("ATPyLib.", ""))
            if m.startswith("framework.") and m not in ("framework.ATTestSet", "framework.ATTestCase"):
                line = "from {} import {}".format(*m.rsplit(".", 1)) if "." in m else "import " + m
                if line not in extra_import_lines:
                    extra_import_lines.append(line)
    sequence = (sess.step2 or {}).get("sequence") or []
    library = _build_library(_effective_group(sess), fragments, data)
    skeleton = _render_skeleton(key, _case_title(data, key), sequence,
                                extra_import_lines, fragments,
                                _case_payload_fields(sess)["objective"], library)
    # Slice A: once the units have been re-chunked from an assembled script, THAT script is the
    # frame — module-level helpers a whole-script Fix or a hand edit added are part of it, and
    # the server's fresh render would silently drop them. The snapshot is trusted only while
    # the sequence it was cut against is still the sequence (same shape); after a re-extract
    # or renumbering the rendered skeleton is the only frame that fits the new steps.
    frame = (sess.step6 or {}).get("frame") or {}
    if frame.get("code") and frame.get("sequence_shape") == _sequence_shape(sequence):
        skeleton = frame["code"]
    setup_steps, tc_steps = _split_sequence(sequence)
    bound_devs, _stk, _pl = _detect_topology(sequence, fragments)
    return {
        "fragments": fragments, "extra_mods": extra_mods, "sequence": sequence,
        "skeleton": skeleton, "setup_steps": setup_steps, "tc_steps": tc_steps,
        "units": _skeleton_units(skeleton),
        "devices": _skeleton_bound_devices(skeleton, bound_devs[0] if bound_devs else ""),
        # ART shape (2026-09-07): the links the frame bound, and the suite library the
        # frame imports — both read back off the rendered frame / built once per case.
        "bound_ports": _skeleton_bound_ports(skeleton),
        "library": library,
        # CASE-level, not unit-level, on purpose: the fill rules branch on these two flags,
        # and the rules live in the SHARED half of every unit prompt (decision 8). Derived
        # per unit they made the shared half differ between units that disagreed — a cache
        # miss for every such unit — so they are answered once for the whole case here.
        "case_py2_flagged": any(f.get("py2_flagged") for f in fragments),
        "case_cli_reference": bool(_cli_reference_block(sequence, fragments)),
        # G8(a): case-level too — the suite's configure() body is the same for every unit.
        "suite_setup_body": _suite_setup_body(sess),
    }


def _configure_method_of(setup_unit_text: str) -> str:
    """The `configure()` method of a setup unit, verbatim (D7 of the guardrails plan: the
    body itself, not a derived command list), dedented; '' when there is none."""
    import textwrap
    lines = (setup_unit_text or "").split("\n")
    start = next((i for i, ln in enumerate(lines) if re.match(r"\s*def configure\(", ln)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"\s*def tear_down\(", lines[i])), len(lines))
    body = "\n".join(lines[start:end]).rstrip()
    return textwrap.dedent(body)


def _suite_setup_body(sess: PtSession) -> str:
    """G8(a) (RC6): what `TestSet.configure()` currently issues, for the shared half of
    every unit prompt. The assembled script on screen wins (it carries hand-edits, and
    fix_units re-syncs the chunks from it); before any assembly the generated setup chunk
    is used; before the setup unit exists there is nothing to show and the block is
    omitted. So at first generation the case units do not see it (the setup unit is still
    being written) and every fix pass does — the shared half changes once, when the setup
    lands, which is the honest cache boundary."""
    step6 = sess.step6 or {}
    text = ""
    code = ((step6.get("files") or {}).get("test") or {}).get("code") or ""
    if code:
        setup = next((u for u in _skeleton_units(code) if u["id"] == "setup"), None)
        text = setup["block"] if setup else ""
    if not text:
        ch = (step6.get("chunks") or {}).get("setup") or {}
        if ch.get("status") == "ok":
            text = ch.get("code") or ""
    return _configure_method_of(text)


def _fragments_for_unit(unit: dict, ctx: dict) -> List[dict]:
    """Only the fragments whose maps_to covers this unit's ORIGINAL sequence step.

    This is the whole input saving: the whole-script prompt carried 106KB of fragment code
    because it carried every fragment for every step. A unit needs its own.
    """
    if unit["kind"] == "setup":
        want = {str(s.get("n")) for s in ctx["setup_steps"]}
    else:
        src = _unit_source_step(unit, ctx["tc_steps"])
        want = {str(src.get("zephyr_step_idx", src.get("n")))} if src else set()
        # tc_steps carry the RENUMBERED n; maps_to is keyed on the original sequence
        # numbering, so match on whichever the row still carries.
        if src:
            want |= {str(src.get("n"))}
    out = []
    for f in ctx["fragments"]:
        maps = {str(x) for x in (f.get("maps_to") or [])}
        if maps & want:
            out.append({**f, "tag": _fragment_tag(f.get("source_id", ""), f.get("loc"),
                                                  f.get("py2_translated", False))})
    return out


# Fragments / CLI-reference entries used by at least this share of a case's units are
# HOISTED into the shared (system, cached) half of every unit prompt instead of being
# re-sent inside each unit that uses them (token-efficiency decision 5, 2026-09-07).
# Measured on T44297: fragments were 27% of all prompt text; one 6,282-char fragment went
# to 32 of 38 units and the top four (all ≥ 23/38) were 63% of the fragment bytes sent.
# Hoisted, they are read from cache by every unit after the first instead of written 38
# times. Below the threshold a fragment stays per-unit — hoisting everything would hand
# every unit all 38 fragments, which the report flagged as a quality risk.
_PT_SHARED_MIN_SHARE = 0.5


def _split_cli_sections(block: str) -> Tuple[str, List[Tuple[str, str]]]:
    """(header, [(command, section)]) of a `_cli_reference_block`; sections start at '### '."""
    if not block:
        return "", []
    header: List[str] = []
    sections: List[List[str]] = []
    for ln in block.split("\n"):
        if ln.startswith("### "):
            sections.append([ln])
        elif not sections:
            header.append(ln)
        else:
            sections[-1].append(ln)
    return ("\n".join(header).rstrip(),
            [(sec[0][4:].strip(), "\n".join(sec).rstrip()) for sec in sections])


def _join_cli_sections(header: str, sections: List[Tuple[str, str]]) -> str:
    return (header + "\n" + "\n".join(t for _, t in sections)) if sections else ""


def _shared_plan(ctx: dict) -> dict:
    """Which fragments and CLI entries are common enough to live in the shared half.

    Computed ONCE per generation context (memoised on `ctx`) because it needs every unit's
    fragment list and CLI block, and a fan-out renders every unit from one context anyway.
    A single-unit case shares nothing — there is nobody to share with.
    """
    plan = ctx.get("_shared_plan")
    if plan is not None:
        return plan
    units = ctx["units"]
    per_frags: Dict[str, List[dict]] = {}
    per_cli: Dict[str, str] = {}
    for u in units:
        frags = _fragments_for_unit(u, ctx)
        src = _unit_source_step(u, ctx["tc_steps"])
        rows = ctx["setup_steps"] if u["kind"] == "setup" else ([src] if src else [])
        per_frags[u["id"]] = frags
        per_cli[u["id"]] = _cli_reference_block(rows, frags)
    n = len(units)

    def _common(counter: Dict[str, int]) -> List[str]:
        if n < 2:
            return []
        return [k for k, c in counter.items() if c / n >= _PT_SHARED_MIN_SHARE]

    frag_count: Dict[str, int] = {}
    first_seen: Dict[str, dict] = {}
    for frags in per_frags.values():
        for f in frags:
            frag_count[f["tag"]] = frag_count.get(f["tag"], 0) + 1
            first_seen.setdefault(f["tag"], f)
    shared_tags = _common(frag_count)

    cli_count: Dict[str, int] = {}
    cli_text: Dict[str, str] = {}
    header = ""
    for blk in per_cli.values():
        h, secs = _split_cli_sections(blk)
        header = header or h
        for cmd, txt in secs:
            cli_count[cmd] = cli_count.get(cmd, 0) + 1
            cli_text.setdefault(cmd, txt)
    shared_cmds = _common(cli_count)
    shared_header = header.replace("REAL CLI REFERENCE",
                                   "REAL CLI REFERENCE shared by most units of this case", 1)
    plan = {
        "per_frags": per_frags, "per_cli": per_cli,
        "shared_tags": set(shared_tags),
        "shared_fragments": [first_seen[t] for t in shared_tags],
        "shared_cmds": set(shared_cmds),
        "shared_cli": _join_cli_sections(shared_header, [(c, cli_text[c]) for c in shared_cmds]),
    }
    ctx["_shared_plan"] = plan
    return plan


def _render_unit_prompt(key: str, data: dict, sess: PtSession, ctx: dict, unit: dict) -> str:
    """The prompt for one unit, rendered but NOT sent."""
    plan = _shared_plan(ctx)
    lib = ctx.get("library") or {}
    lib_tags = set(lib.get("tags") or ()) | set(lib.get("framework_tags") or ())
    frags = plan["per_frags"][unit["id"]]                 # ALL of this unit's fragments
    # Fragments that ship in the suite library are CALLED, not pasted: they leave both the
    # per-unit and the hoisted sections and appear once, under the library header.
    own_frags = [f for f in frags if f["tag"] not in plan["shared_tags"] and f["tag"] not in lib_tags]
    shared_here = [f["tag"] for f in frags if f["tag"] in plan["shared_tags"] and f["tag"] not in lib_tags]
    lib_here = [f["tag"] for f in frags if f["tag"] in lib_tags]
    cli_header, cli_secs = _split_cli_sections(plan["per_cli"][unit["id"]])
    own_cli = _join_cli_sections(cli_header,
                                 [(c, t) for c, t in cli_secs if c not in plan["shared_cmds"]])
    src = _unit_source_step(unit, ctx["tc_steps"])
    return render_prompt("pt_generate_step.jinja", {
        "case_key": key,
        "case_title": _case_title(data, key),
        "mode": unit["kind"],
        "tc_n": unit.get("tc_n"),
        "source_n": (src or {}).get("orig_n") or (src or {}).get("n"),
        "step": src or {},
        "setup_steps": ctx["setup_steps"],
        "blank_block": unit["block"],
        "fragments": own_frags,
        "shared_fragments": [f for f in plan["shared_fragments"] if f["tag"] not in lib_tags],
        "shared_tags_for_unit": shared_here,
        "shared_cli_reference": plan["shared_cli"],
        "devices": ctx["devices"],
        "bound_devices": ctx["devices"],           # rule 3 of the included fill rules
        "bound_ports": ctx.get("bound_ports") or [],
        "library": lib or None,
        "library_tags_for_unit": lib_here,
        "framework_surface": _framework_surface_slice(data, ctx["extra_mods"]),
        "cli_reference": own_cli,
        "device_note": _fragment_device_note(frags, ctx["devices"]),
        "py2_flagged": ctx["case_py2_flagged"],
        "rules_cli_reference": ctx["case_cli_reference"],
        "suite_setup_body": ctx.get("suite_setup_body") or "",
        "split_marker": _PT_PROMPT_SPLIT,
        "model_name": (_llm_cfg_for(sess, "unit_fill").get("model") or "unknown"),
        "gen_date": utc_now().strftime("%Y-%m-%d"),
    })


def _unit_shape_ok(code: str, unit: dict) -> Tuple[bool, str]:
    """Is this reply the unit we asked for, and does it parse?

    Checked on ARRIVAL rather than at assembly, for the same reason `_recovery_failure`
    exists: a unit that is wrong is worth refusing while the reviewer is still looking at
    the button they pressed, not thirty units later when the file will not compile and
    nobody knows which call caused it.

    A TestCase block is dedented to column 0 and parsed here. The setup unit is a pair of
    bare METHODS, which can only be parsed by wrapping them in a synthetic class — and that
    wrapper's line numbers are unmappable to anything the reviewer sees ("line 38" of code
    nobody wrote). So the setup unit is NOT parsed on arrival: its only arrival check is the
    mappable, structural one — did both configure() and tear_down() come back (by regex).
    Its syntax and indentation are judged at the Summary step, where `_lint_generated`
    py_compiles the full assembled script and reports real line numbers.
    """
    import ast as ast_mod
    if unit["kind"] == "setup":
        # Syntax/indentation is validated at the Summary step (assemble_script ->
        # _lint_generated py_compiles the whole assembled script, real line numbers). Parsing
        # the pair here needed a synthetic `class _P:` wrapper whose line numbers the reviewer
        # cannot map to anything on screen, so the arrival check keeps only the mappable,
        # structural question: did BOTH methods come back? Read by regex so a merely-
        # misindented reply still reaches Summary instead of being refused against line 38.
        missing = [m for m in ("configure", "tear_down")
                   if not re.search(rf"(?m)^[ \t]*(?:async[ \t]+)?def[ \t]+{m}[ \t]*\(", code)]
        if missing:
            return False, ("the reply is missing " + ", ".join(missing)
                           + " — configure() and tear_down() are one unit and must both come back")
        return True, ""
    try:
        tree = ast_mod.parse(code)
    except SyntaxError as e:
        return False, f"the returned block is not valid Python ({e.msg} line {e.lineno})"
    classes = [n for n in tree.body if isinstance(n, ast_mod.ClassDef)]
    if len(classes) != 1:
        return False, (f"expected exactly one class, got {len(classes)} — a unit reply must "
                       f"contain only its own class")
    if classes[0].name != unit["label"]:
        return False, (f"the reply defines {classes[0].name}, not {unit['label']} — the class "
                       f"name is part of the fixed frame and the runner registers it by name")
    methods = {b.name for b in classes[0].body
               if isinstance(b, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef))}
    if "main" not in methods:
        return False, f"{unit['label']} came back without a main() — nothing would run"
    return True, ""


# G2 (RC2 of PLAN-fix-units-guardrails): the lines of a unit that are the FIXED FRAME, read
# off the frame's own blank block — the class line, the testCase* attribute lines (the `+=`
# continuation included), the three method signatures and each method's opening shortcut
# block (`name = dotted.name`, no call). The prompt asked for them "EXACTLY as they are" and
# nothing checked; tc6 came back re-implemented wholesale and was stored as ok.
_FROZEN_LINE_RX = re.compile(
    r"^class TestCase_\d+\(|^\s*testCase(Desc|Ref|Method)\s*\+?=|"
    r"^\s*(?:async\s+)?def\s+(configure|main|tear_down)\s*\(|^\s*\w+ = [\w.]+$")


def _unit_frozen_lines(unit: dict, current_code: str) -> List[str]:
    """The frozen lines this fix must return unchanged: frame lines of the unit's blank block
    that the CURRENT unit still carries (a reviewer who hand-edited one of them has decided
    otherwise, so only what is present now is enforced), plus the current main()'s leading
    provenance tag, which the frame reserves and the fill supplies."""
    setup = unit.get("kind") == "setup"
    cur = [(ln.strip() if setup else ln) for ln in (current_code or "").split("\n")]
    out: List[str] = []
    for ln in (unit.get("block") or "").split("\n"):
        if not ln.strip() or ln.strip().startswith("#") or not _FROZEN_LINE_RX.match(ln):
            continue
        key = ln.strip() if setup else ln
        if key in cur and key not in out:
            out.append(key)
    m = re.search(r"(?ms)^[ \t]*def main\(self\):[^\n]*\n((?:[ \t]*\n)*)([^\n]*)", current_code or "")
    if m and _PROVENANCE_TAG_RX.match(m.group(2)) and m.group(2) not in out:
        out.append(m.group(2))
    return out


def _unit_frozen_ok(current_code: str, new_code: str, unit: dict) -> Tuple[bool, str]:
    """G2: every frozen line of the current unit must come back byte-identical (the setup
    pair is compared stripped: its indentation is re-based at assembly anyway)."""
    setup = unit.get("kind") == "setup"
    new = {(ln.strip() if setup else ln) for ln in (new_code or "").split("\n")}
    for ln in _unit_frozen_lines(unit, current_code):
        if ln not in new:
            return False, (f"fix altered a frozen line of the fixed frame: `{ln.strip()[:90]}` "
                           f"is missing from the reply — the class name, testCase* lines, the "
                           f"three method signatures, the shortcut lines and the provenance tag "
                           f"must come back exactly as they are")
    return True, ""


# G6(c), scoped (Terrence, 2026-09-14): the kinds whose `evidence` quotes the DEFECT itself —
# a verdict, an observation, a symbol — so a correct fix must change that line. NOT
# `missing_precondition` / `cross_unit_inconsistency` / `other`: review #1 finding 3 quoted
# the `lldp management-address` line as evidence of a MISSING `tlv-select`, and the right fix
# adds a line and keeps that one; applied to those kinds this check refuses correct fixes.
_EVIDENCE_IS_DEFECT_KINDS = ("verdict_mismatch", "weak_observation", "wrong_symbol")


def _norm_ws(s: str) -> str:
    return " ".join((s or "").split())


def _unit_evidence_gone(guard: dict, new_code: str, unit: dict) -> Optional[str]:
    """For each finding of an evidence-is-defect kind mapped to this unit: every evidence
    line that is quoted verbatim from the current unit (whitespace-insensitive; elided lines
    with `...` and lines the current unit does not contain are not judged) must no longer
    appear in the reply. A line still there means the defect was not addressed."""
    cur = {_norm_ws(ln) for ln in (guard.get("current_code") or "").split("\n") if ln.strip()}
    new = {_norm_ws(ln) for ln in (new_code or "").split("\n") if ln.strip()}
    for f in guard.get("findings") or []:
        if (f.get("kind") or "") not in _EVIDENCE_IS_DEFECT_KINDS:
            continue
        for raw in str(f.get("evidence") or "").split("\n"):
            ln = _norm_ws(raw)
            if not ln or "..." in ln or "…" in ln or ln not in cur:
                continue
            if ln in new:
                return (f"finding evidence still present — the {f.get('kind')} finding at "
                        f"{f.get('where') or '(unit)'} quotes `{ln[:90]}` as the defect and the "
                        f"reply still contains that line; kept the current unit")
    return None


def _spliced_new_errors(guard: dict, new_code: str, unit: dict,
                        include_unmapped: bool = True) -> Optional[List[str]]:
    """Splice `new_code` into `guard['assembled_code']` at this unit's slot, lint the whole
    file, and return the errors it INTRODUCES (absent from `guard['baseline_errors']`) that map
    to this unit — and, when `include_unmapped`, to no unit at all (a file that stopped
    compiling). `None` only when the linter itself could not run (never refuse on that).

    The one splice-and-lint both the fix guard (G6(b), include_unmapped=True) and the
    generation arrival guard (R2, include_unmapped=False — whole-file classes are Assemble's
    job) share, so they cannot drift."""
    assembled = guard.get("assembled_code") or ""
    units = _skeleton_units(assembled)
    me = next((u for u in units if u["id"] == unit["id"]), None)
    if me is None:
        return []
    code = (new_code or "").strip("\n")
    if unit.get("kind") == "setup":
        d_ind, b_ind = _setup_slot_indents(unit.get("block") or "")
        code = _reindent_setup_pair(code, d_ind, b_ind)
    lines = assembled.split("\n")
    lo, hi = me["lines"]
    lines[lo - 1:hi] = code.split("\n")
    spliced = "\n".join(lines)
    tmp = guard["sess"].model_copy(deep=True)
    step6_t = dict(tmp.step6 or {})
    files_t = dict(step6_t.get("files") or {})
    files_t["test"] = {**(files_t.get("test") or {}), "code": spliced}
    step6_t["files"] = files_t
    tmp.step6 = step6_t
    try:
        lint = _lint_generated(tmp)
    except Exception as e:                       # the linter, not the unit, failed: do not refuse on it
        print(f"[pt] isolated lint could not run for {unit['id']}: {e}")
        return None
    baseline = set(guard.get("baseline_errors") or [])
    new_units = _skeleton_units(spliced)
    ok_ids = (unit["id"], None) if include_unmapped else (unit["id"],)
    return [e for e in (lint.get("errors") or []) if e not in baseline
            and _unit_id_for_text(str(e), new_units) in ok_ids]


def _unit_lint_regression(guard: dict, new_code: str, unit: dict) -> Optional[str]:
    """G6(b): a FIX reply must not add a lint error the current script does not already carry.
    Any such error mapping to this unit or to no unit (a file that stopped compiling) keeps the
    old chunk. `guard` = {current_code, assembled_code, sess, baseline_errors}."""
    mine = _spliced_new_errors(guard, new_code, unit, include_unmapped=True)
    if mine:
        return ("fix introduces lint error(s) the current unit does not have — kept the current "
                "unit: " + "; ".join(str(e)[:160] for e in mine[:3]))
    return None


def _arrival_refusal(key: str, unit: dict, code: str, ctx: dict, sess) -> Optional[str]:
    """R2 (arrival-time lint, 2026-09-15). A freshly GENERATED unit, spliced into the frame plus
    the units that have landed so far (the setup unit is primed first, so it is always present),
    must not introduce a PER-UNIT lint error — an unbound name, a command the suite owns, a port
    on the wrong switch, an unknown scapy field, a verdict in configure()/tear_down(). Whole-file
    classes (coverage, completeness, imports) stay for Assemble; only errors mapping to THIS unit
    are judged. Returns the reason, or None. Never refuses on a linter crash."""
    try:
        fresh = _pt_load(key) or sess
        if fresh is None:
            return None
        chunks = dict((fresh.step6 or {}).get("chunks") or {})
        base_chunks = {k: v for k, v in chunks.items() if k != unit["id"]}
        placeholder_partial, _missing = _assemble_units(ctx, base_chunks)
        tmp = fresh.model_copy(deep=True)
        step6_t = dict(tmp.step6 or {})
        files_t = dict(step6_t.get("files") or {})
        files_t["test"] = {**(files_t.get("test") or {}), "code": placeholder_partial}
        step6_t["files"] = files_t
        tmp.step6 = step6_t
        baseline = _lint_generated(tmp).get("errors") or []
    except Exception as e:
        print(f"[pt] R2 arrival baseline could not run for {unit['id']}: {e}")
        return None
    guard = {"assembled_code": placeholder_partial, "sess": fresh, "baseline_errors": baseline}
    mine = _spliced_new_errors(guard, code, unit, include_unmapped=False)
    if mine:
        # Suite-owned unset findings (D-2026-09-15) are a cross-case POLICY flag judged over the
        # WHOLE assembled script at Review — a later case may re-set the unset, and may not be
        # generated yet — so a unit is never arrival-refused (nor repair-thrashed) for one. A
        # negative test that unsets a suite command for its own step is legitimate; the Review
        # flag is what checks it is re-set. Every other per-unit class still refuses here.
        mine = [e for e in mine if not str(e).startswith("suite-owned:")]
    if mine:
        return "generated unit has lint error(s): " + "; ".join(str(e)[:160] for e in mine[:3])
    return None


_SETUP_DEF_RE = re.compile(r"[ \t]*(?:async[ \t]+)?def[ \t]+(?:configure|tear_down)\b")


def _setup_slot_indents(block: str) -> Tuple[int, int]:
    """(def_indent, body_indent) the frame reserves for the setup pair — read off the
    frame's own block (a `def` at method level, its first body line one step deeper).
    Defaults to the 4/8 the skeleton uses if the block can't be read."""
    lines = (block or "").split("\n")
    for idx, ln in enumerate(lines):
        if _SETUP_DEF_RE.match(ln):
            d = len(ln) - len(ln.lstrip())
            for nxt in lines[idx + 1:]:
                if nxt.strip():
                    return d, len(nxt) - len(nxt.lstrip())
            return d, d + 4
    return 4, 8


def _reindent_setup_pair(code: str, def_indent: int, body_indent: int) -> str:
    """Re-indent a returned configure()/tear_down() pair so each method's `def` sits at
    `def_indent` and its body base at `body_indent`, preserving the body's internal nesting.

    WHY ONLY THE SETUP UNIT. It is the one unit that is NOT a top-level construct: it is
    two methods living inside `class TestSet` at indent 4, handed to the model as an
    indented FRAGMENT. Models routinely flush-left a `def` while its body keeps the indent
    it would have at method level (or shift the whole method), so the two methods disagree
    — and the byte-exact splice below rides that straight into the file as
    `IndentationError: unindent does not match any outer indentation level`
    (AWPTCM-T44297, 2026-09-04). TestCase units never hit this: they are whole column-0
    classes the model reproduces cleanly.

    Deterministic because both targets are known from the frame's own slot. Each method's
    `def` is set to `def_indent` and its body re-based to `body_indent` INDEPENDENTLY — so a
    def flush-left with a correct body (the observed failure) is fixed without over-indenting
    that body — while each body line keeps its offset relative to the body base, so nested
    blocks survive. Idempotent: a reply already at the slot indents is returned unchanged.
    Falls back to the raw reply (for the Summary lint to judge) if no method def is found."""
    lines = code.split("\n")
    def_idxs = [i for i, ln in enumerate(lines) if _SETUP_DEF_RE.match(ln)]
    if not def_idxs:
        return code
    out = list(lines)
    bounds = def_idxs + [len(lines)]
    for s, start in enumerate(def_idxs):
        out[start] = " " * def_indent + lines[start].lstrip()
        body = lines[start + 1:bounds[s + 1]]
        base = min((len(l) - len(l.lstrip()) for l in body if l.strip()), default=0)
        for j, l in enumerate(body):
            out[start + 1 + j] = ("" if not l.strip()
                                  else " " * (body_indent + (len(l) - len(l.lstrip())) - base)
                                  + l.lstrip())
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Generate-state gating (PLAN-generate-state-and-sequence-sanity, slice A, 2026-09-21)
# ---------------------------------------------------------------------------
# step6 holds TWO copies of the script: the per-unit `chunks` and the assembled
# `files.test.code`. Only the splice paths write both; `save_script`, `fix_script` and
# `generate_script` write the assembled code alone, so afterwards the chunks are STALE and any
# re-splice (Assemble, Fix units, Apply held) silently discards the repair — measured on
# AWPTCM-T33234, 2026-09-17/18, where a hand-repaired script sat one click from being reverted
# with every pill green. The hash of the script at its last assembly is the join between the
# two copies; when the script's current hash differs, every splice path refuses (409) until
# `rechunk` re-reads the units AND the surrounding frame from the current script.

def _code_hash(code: str) -> str:
    import hashlib
    return hashlib.sha1((code or "").encode("utf-8")).hexdigest()[:16]


_GEN_DIVERGED_REASON = (
    "The assembled script and the generated units are out of step: the script on screen was "
    "written by Fix whole script / Save / Generate Script after the last unit assembly (or no "
    "assembly has been recorded for it). Use 'Re-chunk from script' first — it re-reads the "
    "units and the surrounding frame from the current script — or Assemble / Fix units / Apply "
    "would splice stale units over the current script and discard those edits.")


def _gen_state(step6: dict) -> dict:
    """Where the two copies of the script stand, for the UI's pill and the 409 gate.

    `diverged` is True whenever an assembled script exists whose hash is not the hash recorded
    at the last assembly (or re-chunk). A whole-script Generate/Fix/Save therefore ALWAYS reads
    as diverged until the user re-chunks — deliberately: those paths never wrote the chunks.
    `review_stale` is True when the stored review was not made against this exact code
    (slice B); a review with no recorded hash is treated as stale, since it cannot be proved
    to match."""
    step6 = step6 or {}
    code = ((step6.get("files") or {}).get("test") or {}).get("code") or ""
    chunks = step6.get("chunks") or {}
    script_hash = _code_hash(code) if code else ""
    assembled_hash = str(step6.get("assembled_hash") or "")
    diverged = bool(code) and assembled_hash != script_hash
    review = step6.get("review") or {}
    review_stale = bool(review) and (str(review.get("code_hash") or "") != script_hash)
    frame = step6.get("frame") or {}
    return {
        "script_hash": script_hash,
        "assembled_hash": assembled_hash,
        "units": sum(1 for c in chunks.values() if (c or {}).get("status") == "ok"),
        "frame_snapshot": bool(frame.get("code")),
        "diverged": diverged,
        "reason": _GEN_DIVERGED_REASON if diverged else "",
        "review_stale": review_stale,
    }


def _require_units_current(step6: dict) -> None:
    """The gate every splice / unit-generation path passes first: 409 while diverged."""
    if _gen_state(step6)["diverged"]:
        raise HTTPException(409, _GEN_DIVERGED_REASON)


def _rechunk_from_script(step6: dict, sequence: List[dict]) -> Tuple[List[str], List[str]]:
    """Make the chunks AND the frame agree with the assembled script, in place.

    Re-reads every unit off the current `files.test.code` (`_chunks_from_code` — the same AST
    split that cut the frame) and stores the WHOLE current script as `step6["frame"]`, so a
    later assembly splices into the real frame — module-level helpers a whole-script Fix added
    survive, and an Assemble with unchanged units reproduces the script byte-for-byte. The
    frame carries the sequence shape it was cut against; `_pt_generation_context` ignores a
    snapshot whose shape no longer matches (a re-extracted or renumbered sequence).
    Returns (changed unit ids, dropped unit ids). Raises 409 when the script has no units."""
    code = ((step6.get("files") or {}).get("test") or {}).get("code") or ""
    if not code:
        raise HTTPException(409, "No assembled script to re-chunk. Generate a script first.")
    units = _skeleton_units(code)
    if not units:
        raise HTTPException(409, "The script cannot be split into units: it does not parse, "
                                 "or it has no TestCase_<n> classes and no TestSet.configure. "
                                 "Fix the syntax first (Re-lint shows where).")
    synced = _chunks_from_code(code, None)
    chunks, changed = _resync_chunks(step6.get("chunks") or {}, synced)
    dropped = sorted(k for k in chunks if k not in synced)
    for k in dropped:
        chunks.pop(k, None)
    h = _code_hash(code)
    step6["chunks"] = chunks
    step6["frame"] = {"code": code, "hash": h, "at": utc_now().isoformat(),
                      "units": [u["id"] for u in units],
                      "sequence_shape": _sequence_shape(sequence or [])}
    step6["assembled_hash"] = h
    return changed, dropped


def _try_rechunk(step6: dict, sequence: List[dict]) -> bool:
    """`_rechunk_from_script` for the paths that have just written a whole script (fix_script):
    keep the two copies in step when the new script splits cleanly, and leave the state
    honestly DIVERGED — pill on, splice paths closed — when it does not."""
    try:
        _rechunk_from_script(step6, sequence)
        return True
    except HTTPException:
        return False


def _assemble_units(ctx: dict, chunks: dict) -> Tuple[str, List[str]]:
    """Splice the generated units into the rendered frame. Returns (code, missing_ids).

    Line-based and back-to-front, so replacing one unit cannot shift the line numbers of
    the units not yet replaced. The frame is the server's own render, so this is a pure
    local operation — no model, no reassembly heuristics, no seams to detect. That is the
    whole reason the units are worth generating separately.

    The ONE deterministic normalisation is the setup pair's leading indentation
    (`_reindent_setup_pair`): the only unit that is a class-body fragment rather than a
    top-level construct, so the only one a model can hand back with its two `def` lines at
    disagreeing columns. Everything else is spliced byte-for-byte.
    """
    lines = ctx["skeleton"].split("\n")
    missing: List[str] = []
    for u in sorted(ctx["units"], key=lambda x: x["lines"][0], reverse=True):
        ch = chunks.get(u["id"]) or {}
        code = (ch.get("code") or "").strip("\n") if ch.get("status") == "ok" else ""
        if not code:
            missing.append(u["id"])
            continue
        if u.get("kind") == "setup":
            d_ind, b_ind = _setup_slot_indents(u.get("block") or "")
            code = _reindent_setup_pair(code, d_ind, b_ind)
        lo, hi = u["lines"]
        lines[lo - 1:hi] = code.split("\n")
    return "\n".join(lines), list(reversed(missing))


def _assemble_and_store(key: str, sess: PtSession, ctx: dict, group: str, name: str) -> dict:
    """Splice + re-stamp + manifest + persist + lint. The body of assemble_script, extracted
    (2026-09-07) so the per-unit Fix can re-assemble after its units land without a second
    copy of the assembly rules. Raises HTTPException(409) when a unit is missing."""
    step6 = sess.step6 or {}
    chunks = step6.get("chunks") or {}
    code, missing = _assemble_units(ctx, chunks)
    if missing:
        raise HTTPException(409, "Not every unit has been generated yet. Missing: "
                                 + ", ".join(missing))
    _validate_naming(group, name)
    file_name = f"{name}.py"

    frame = step6.get("frame") or {}
    if frame.get("code") and code == frame["code"]:
        # Nothing changed since the re-chunk: the assembly IS the snapshot, byte for byte.
        # Re-stamping would only move the `# AI <model> <date>` dates and break that proof.
        stamped = code
    else:
        stamped = _restamp_provenance(code, ctx["fragments"],
                                      (_llm_cfg_for(sess, "unit_fill").get("model") or ""),
                                      ctx["sequence"])
    report = gen_assembly.manifest_check(stamped)

    def _apply(fresh: PtSession) -> None:
        step6_f = dict(fresh.step6 or {})
        step6_f["naming"] = {"group": group, "name": name}
        step6_f["files"] = {"test": {"name": file_name, "code": stamped}}
        if (ctx.get("library") or {}).get("members"):
            # The frame imports `from <stem> import *`, so the module must ship with the
            # script (persist + run both read files["library"]).
            step6_f["files"]["library"] = {"name": ctx["library"]["name"],
                                           "code": ctx["library"]["code"]}
        step6_f["assembled_at"] = utc_now().isoformat()
        step6_f["assembled_hash"] = _code_hash(stamped)     # slice A: the join to the chunks
        step6_f["assembly"] = {"units": len(ctx["units"]), "manifest": report,
                               "source": "per-unit"}
        # D6b (t44297 #6, 2026-09-22): KEEP the review, do not delete it.
        #
        # This used to `step6_f.pop("review", None)` — "a fresh assembly supersedes any earlier
        # review: the findings were about a different artefact". The reasoning was right and the
        # remedy was too strong: on 2026-09-09 a review call died with the SSH session, and
        # because re-assembly had already discarded the previous one the script was left with NO
        # review at all until someone re-fired by hand. Deleting to avoid mis-attribution also
        # deletes the only findings anyone has.
        #
        # Slice B (PLAN-generate-state-and-sequence-sanity) made deleting unnecessary: the review
        # carries `code_hash`, `_gen_state` compares it to the current script hash and sets
        # `review_stale`, and the UI renders a stale review collapsed under a badge with
        # per-finding evidence checks. A re-assembly moves that same hash, so the review marks
        # ITSELF stale from here — visibly about a different artefact, and still readable.
        step6_f["iterations"] = int(step6_f.get("iterations") or 0) + 1
        fresh.step6 = step6_f

    sess = _pt_persist_fresh(key, _apply)
    lint = _lint_generated(sess)

    def _apply_lint(fresh: PtSession) -> None:
        step6_f = dict(fresh.step6 or {})
        step6_f["lint"] = lint
        history = list(step6_f.get("lint_history") or [])
        history.append(_lint_history_entry(lint, step6_f.get("iterations") or 0,
                                           "assemble", len(ctx.get("units") or [])))
        step6_f["lint_history"] = history[-50:]           # a rolling window, per session
        fresh.step6 = step6_f

    sess = _pt_persist_fresh(key, _apply_lint)
    files_out = {"test": {"name": file_name, "code": stamped}}
    if (ctx.get("library") or {}).get("members"):
        files_out["library"] = {"name": ctx["library"]["name"], "code": ctx["library"]["code"]}
    return {"files": files_out, "lint": lint, "manifest": report, "units": len(ctx["units"]),
            "gen_state": _gen_state(sess.step6 or {})}


@router.post("/rechunk/{key}")
async def rechunk(key: str):
    """Slice A: make the units and the frame agree with the assembled script (local, no LLM).

    The explicit, visible user action that clears the DIVERGED state. Lock-gated by
    `_pt_persist`."""
    sess = _pt_get(key)
    step6 = dict(sess.step6 or {})
    changed, dropped = _rechunk_from_script(step6, (sess.step2 or {}).get("sequence") or [])
    sess.step6 = step6
    _pt_persist(sess)
    return {"changed": changed, "dropped": dropped, "units": step6["frame"]["units"],
            "gen_state": _gen_state(step6)}


@router.post("/reset_generate/{key}")
async def reset_generate(key: str):
    """Drop the generated units and every derived artefact of the Generate step, keeping steps
    1-4 and the saved script + its lint + naming (Terrence, 2026-09-18: "keep the step history
    up to Generate, and dump all the code after that"). Every splice path then 409s on missing
    units until Generate is run deliberately. Lock-gated by `_pt_persist`."""
    sess = _pt_get(key)
    step6 = sess.step6 or {}
    if not (step6.get("files") or {}).get("test"):
        raise HTTPException(409, "Nothing to reset: no script has been generated for this case.")
    dropped = sorted((step6.get("chunks") or {}).keys())
    kept = {k: step6[k] for k in ("files", "lint", "naming") if k in step6}
    kept["confirmed"] = False
    kept["reset_at"] = utc_now().isoformat()
    kept["reset_dropped"] = dropped
    sess.step6 = kept
    _invalidate_from(sess, 5)
    _pt_persist(sess)
    return {"dropped_units": dropped, "kept": sorted(kept), "gen_state": _gen_state(kept)}


@router.post("/assemble_script/{key}")
async def assemble_script(key: str, request: Request, body: dict = Body(default={})):
    """Build the script LOCALLY from the frame + the generated units, then lint it.

    No LLM. §9.5's assembly step, minus the reassembly guesswork: the frame is ours and the
    units were shape-checked on arrival, so splicing is deterministic. `manifest_check` still
    runs, and it is now strictly stronger than in the whole-script path — the runner's
    `ts.add_testCase(...)` list was written by `_render_skeleton` BEFORE any unit existed, so
    it is a contract the units are measured against rather than a list the same reply wrote.
    """
    data = _data(request)
    sess = _pt_get(key)
    _require_units_current(sess.step6 or {})   # slice A gate
    step6 = sess.step6 or {}
    chunks = step6.get("chunks") or {}
    ctx = _pt_generation_context(key, data, sess)
    if not ctx["units"]:
        raise HTTPException(409, "The skeleton has no fillable units — confirm step 4 first.")

    naming = step6.get("naming") or {}
    group = (body.get("group") or naming.get("group") or "").strip()
    name = (body.get("name") or naming.get("name") or _art_script_name(key)).strip()
    return _assemble_and_store(key, sess, ctx, group, name)


def _settleable_units(sess: "PtSession", ctx: dict, code: str, already: set) -> List[str]:
    """R4/D3: the units a settle round may touch — those whose reasons are LINT-ONLY (a lint
    error mapped to the unit, no review finding, no failed run), present in the frame, not
    already in flight. A unit with a review or run finding is HELD (guardrails D2) and left for
    the reviewer; a whole-file error names no unit (`_fix_reasons` puts it in `unmapped`), so it
    can never enter the settle set. Blocking or policy — both are settleable; the reviewer sees
    what survives the rounds."""
    reasons = _fix_reasons(sess, ctx, code)
    in_frame = set(_chunks_from_code(code, ctx))
    return [uid for uid, r in reasons["per_unit"].items()
            if r["lint"] and not r["review"] and not r["run"]
            and uid in in_frame and uid not in already]


async def _run_fix_round(key: str, data: dict, sess: "PtSession", ctx: dict,
                         targets: List[str], group: str, name: str) -> "PtSession":
    """One settle round: fix `targets` (lint-only, hold=False so they auto-apply — D2/D1), wait,
    and re-assemble + re-lint. Uses the same `_fix_reasons` / `_fix_unit_prompt` / guard shape /
    `_unit_call_and_store` / `_assemble_and_store` as the manual Fix, and the same model routing
    (`unit_fill`), so settle and Fix cannot drift. A reply refused by G2/G6 keeps its unit (the
    2026-09-15 fix), so a round never destroys a unit it could not clean."""
    step6 = sess.step6 or {}
    code = ((step6.get("files") or {}).get("test") or {}).get("code") or ""
    synced = _chunks_from_code(code, ctx)
    reasons = _fix_reasons(sess, ctx, code)
    by_id = {u["id"]: u for u in ctx["units"]}
    baseline_errors = (step6.get("lint") or {}).get("errors") or []
    lo_by_id = {u["id"]: u["lines"][0] for u in reasons["code_units"]}
    llm_cfg = _llm_cfg_for(sess, "unit_fill")
    prepared, guards = [], {}
    for uid in targets:
        prepared.append((uid, by_id[uid],
                         _fix_unit_prompt(key, data, sess, ctx, by_id[uid], synced[uid],
                                          reasons["per_unit"][uid]), False))
        guards[uid] = {"current_code": synced[uid], "assembled_code": code, "sess": sess,
                       "baseline_errors": list(baseline_errors), "findings": [],
                       "lint_errors": list(reasons["per_unit"][uid]["lint"]),
                       "unit_lo": lo_by_id.get(uid, 1), "hold": False}
    _pt_unit_mark(key, targets, True)

    async def _one(uid: str, unit: dict, prompt: str, edited: bool):
        try:
            await run_in_threadpool(_unit_call_and_store, key, uid, prompt, edited,
                                    unit, llm_cfg, "pt_fix_unit", guards.get(uid))
        except Exception as e:
            print(f"[pt] {key}/{uid}: settle fix failed: {e}")
        finally:
            _pt_unit_mark(key, [uid], False)

    await _run_primed_and_wait(prepared, _one)
    fresh = _pt_load(key) or sess
    await run_in_threadpool(_assemble_and_store, key, fresh, ctx, group, name)
    return _pt_load(key) or fresh


@router.post("/assemble_and_settle/{key}")
async def assemble_and_settle(key: str, request: Request, body: dict = Body(default={})):
    """R4 (2026-09-15): Assemble, then automatically clear the lint-only errors — Fix units on
    the settleable set, re-assemble, re-lint — for up to `_PT_SETTLE_ROUNDS` rounds, so there is
    no human step between Generate and Review for the classes a lint can fix (D3, default on).
    Held (review/run) fixes are never touched. Assembles synchronously, then settles in the
    background; poll /units_status and read step6.settle for the rounds."""
    data = _data(request)
    sess = _pt_get(key)
    _require_units_current(sess.step6 or {})   # slice A gate
    step6 = sess.step6 or {}
    ctx = _pt_generation_context(key, data, sess)
    if not ctx["units"]:
        raise HTTPException(409, "The skeleton has no fillable units — confirm step 4 first.")
    naming = step6.get("naming") or {}
    group = (body.get("group") or naming.get("group") or "").strip()
    name = (body.get("name") or naming.get("name") or _art_script_name(key)).strip()
    res = await run_in_threadpool(_assemble_and_store, key, sess, ctx, group, name)

    async def _settle_chain():
        rounds: List[dict] = []
        try:
            for rnd in range(_PT_SETTLE_ROUNDS):
                cur = _pt_get(key)
                code = ((cur.step6 or {}).get("files") or {}).get("test", {}).get("code") or ""
                targets = _settleable_units(cur, ctx, code, _pt_units_inflight(key))
                if not targets:
                    break
                cur = await _run_fix_round(key, data, cur, ctx, targets, group, name)
                lint = (cur.step6 or {}).get("lint") or {}
                rounds.append({"round": rnd + 1, "units": targets,
                               "lint_errors": len(lint.get("errors") or []),
                               "blocking": len(lint.get("blocking_errors") or [])})

                def _apply_progress(fresh: PtSession, _r=list(rounds)) -> None:
                    s6 = dict(fresh.step6 or {})
                    s6["settle"] = {"at": utc_now().isoformat(), "rounds": _r, "running": True}
                    fresh.step6 = s6
                _pt_persist_fresh(key, _apply_progress, attempts=_PT_CHUNK_WRITE_ATTEMPTS)
        except Exception as e:
            print(f"[pt] {key}: settle chain failed: {e}")
        final = ((_pt_get(key).step6 or {}).get("lint") or {})
        record = {"at": utc_now().isoformat(), "rounds": rounds, "running": False,
                  "settled": not (final.get("blocking_errors")),
                  "lint_errors": len(final.get("errors") or []),
                  "lint_ok": bool(final.get("ok"))}

        def _apply_final(fresh: PtSession) -> None:
            s6 = dict(fresh.step6 or {})
            s6["settle"] = record
            fresh.step6 = s6
        try:
            _pt_persist_fresh(key, _apply_final, attempts=_PT_CHUNK_WRITE_ATTEMPTS)
        except Exception as e:
            print(f"[pt] {key}: could not record the settle outcome: {e}")

    asyncio.create_task(_settle_chain())
    return {"assembled": True, "settling": True, "rounds": _PT_SETTLE_ROUNDS,
            "lint": res.get("lint"), "manifest": res.get("manifest")}


@router.get("/step_prompts/{key}")
async def step_prompts(key: str, request: Request):
    """Every unit, with its prompt rendered — the page-load payload for the chunk UI.

    Prompts are RENDERED, not stored. §9.7 forbids storing N full prompts on the session
    ("a 6-chunk generation must not store six 85KB prompts"), and re-rendering is cheap
    and always current. The one exception is a prompt the reviewer has EDITED, which is
    theirs and is kept on the chunk — see generate_step.
    """
    data = _data(request)
    sess = _pt_get(key)
    _require_confirmed(sess, "step5", "Per-step generation")

    # Rendered in a worker thread, NOT inline (2026-09-08). Building the context and 38
    # prompts is pure CPU — measured 38 s on T44297 before `cli_lookup._probes` was cached,
    # a few seconds after — and an `async def` doing that inline stalls the single-worker
    # server's event loop for the duration: no health, no status polls, no other user.
    # "The server is oddly unresponsive" was this endpoint.
    def _render_all() -> dict:
        ctx = _pt_generation_context(key, data, sess)
        chunks = (sess.step6 or {}).get("chunks") or {}
        out = []
        for u in ctx["units"]:
            ch = chunks.get(u["id"]) or {}
            rendered = _render_unit_prompt(key, data, sess, ctx, u)
            src = _unit_source_step(u, ctx["tc_steps"])
            out.append({
                "id": u["id"], "kind": u["kind"], "tc_n": u.get("tc_n"), "label": u["label"],
                "source_n": (src or {}).get("orig_n") or (src or {}).get("n"),
                "action": (src or {}).get("action", ""),
                "verify": (src or {}).get("verify", ""),
                "blank_block": u["block"],
                # The reviewer's edit wins over the freshly rendered one; `edited` tells the
                # UI which it is looking at so it can say so.
                "prompt": ch.get("prompt") or rendered,
                "edited": bool(ch.get("prompt")),
                "code": ch.get("code") or "",
                "status": ch.get("status") or "pending",
                "error": ch.get("error") or "",
                "at": ch.get("at") or "",
                "held": bool(ch.get("held")),
            })
        return {"units": out, "skeleton_chars": len(ctx["skeleton"])}

    return await run_in_threadpool(_render_all)


# The visible line that separates the two halves of a unit prompt (decision 8, 2026-09-07).
# Everything ABOVE it is identical for every unit of a case and travels as the SYSTEM prompt;
# everything below is this unit's own and travels as the user message. Why: the API matches a
# prompt cache only at content-block boundaries, and the CLI puts one on the system prompt and
# one on the user message. A shared prefix INSIDE one differing user block is invisible to the
# cache — measured 2026-09-07: sequential calls with the shared half in the user block read 0
# tokens; the same half as --system-prompt read 7,879 of 8,059 on the second call, at 1/12 of
# the price. The reviewer sees and may edit the whole prompt, marker included; an edited
# prompt that lost the marker is sent whole as the user message (correct, just uncached).
_PT_PROMPT_SPLIT = "==== SHARED CONTEXT ABOVE THIS LINE · THIS UNIT BELOW IT ===="

# R5 (measurement, 2026-09-15). The class of a lint message, by its signature — the same slugs
# the error-class test enumerates. Ordered: a verdict-in-config is a `contract:` message, so its
# specific test comes before the generic one. Used by the lint history and the 6.4 alarms.
_LINT_CLASS_RULES = [
    ("unbound", lambda m: m.startswith("unbound name:")),
    ("suite-owned", lambda m: m.startswith("suite-owned:")),
    ("field", lambda m: m.startswith("unknown field:")),
    ("port-owner", lambda m: "selects `" in m and "'s port, on " in m),
    ("verdict-config", lambda m: "config only; the verdict belongs in main()" in m),
    ("verdict-echo", lambda m: "reason is the step's verify" in m or "reason IS the step" in m
                    or "verbatim — a verdict should say what was OBSERVED" in m),
    ("incomplete", lambda m: m.startswith("incomplete:")),
    ("coverage", lambda m: m.startswith("coverage") or "objective" in m and "no PyTest step" in m),
    ("syntax", lambda m: m.startswith("syntax:")),
    ("imports", lambda m: m.startswith("imports:")),
    ("structure", lambda m: m.startswith("structure:")),
    ("pep8", lambda m: m.startswith("pep8 ")),
    ("contract", lambda m: m.startswith("contract:")),
]


def _lint_class_of(msg: str) -> str:
    m = str(msg or "")
    for slug, pred in _LINT_CLASS_RULES:
        try:
            if pred(m):
                return slug
        except Exception:
            pass
    return "other"


@functools.lru_cache(maxsize=1)
def _generate_prompt_version() -> str:
    """A short hash of the two generate templates, so a prompt edit starts a new trend series
    (R5 / 6.4). Cached; a template edit reloads the server, clearing it."""
    import hashlib
    h = hashlib.sha1()
    for name in ("pt_generate_step.jinja", "pt_generate_script.jinja"):
        try:
            h.update((_TEMPLATES_DIR / "prompts" / name).read_bytes())
        except Exception:
            pass
    return h.hexdigest()[:10]


def _lint_history_entry(lint: dict, iteration: int, source: str, units: int) -> dict:
    """One trend row: counts by authority and by class, for this assembly's lint."""
    from collections import Counter
    errors = [str(e) for e in (lint.get("errors") or [])]
    warnings = [str(w) for w in (lint.get("warnings") or [])]
    by_class: Counter = Counter()
    for e in errors:
        by_class[_lint_class_of(e)] += 1
    for w in warnings:
        by_class["pep8" if w.startswith("pep8 ") else _lint_class_of(w)] += 1
    return {"at": utc_now().isoformat(), "iteration": int(iteration or 0), "source": source,
            "units": int(units or 0), "prompt_version": _generate_prompt_version(),
            "blocking": len(lint.get("blocking_errors") or []),
            "policy": len(lint.get("policy_errors") or []),
            "warning": len(warnings), "errors": len(errors),
            "by_class": dict(by_class)}


def _split_unit_prompt(prompt: str) -> Tuple[str, str]:
    """(shared_half, unit_half). No marker -> ("", prompt): everything goes as the user turn."""
    lines = (prompt or "").split("\n")
    for i, line in enumerate(lines):
        if line.strip() == _PT_PROMPT_SPLIT:
            return "\n".join(lines[:i]).rstrip(), "\n".join(lines[i + 1:]).lstrip("\n")
    return "", prompt or ""


def _unit_system_prompt(shared_half: str) -> str:
    """The code steer, then the case's shared context. Byte-identical for every unit of a
    case — that identity is the whole cache."""
    return _CODE_SYSTEM_PROMPT + ("\n\n" + shared_half if shared_half else "")


def _unit_call_and_store(key: str, unit_id: str, prompt: str, edited: bool,
                         unit: dict, llm_cfg: dict, template: str = "(verbatim)",
                         guard: Optional[dict] = None, repaired: bool = False,
                         repaired_class: str = "") -> dict:
    """Run ONE unit's LLM call and persist the chunk. Blocking; runs in a worker thread.

    Extracted so both the single-unit endpoint and the batch dispatch share exactly one
    implementation of "call, shape-check, record" — a second copy would drift, and the
    shape check is the thing standing between a wrong reply and a file that will not
    compile.
    """
    shared_half, unit_half = _split_unit_prompt(prompt)
    meta = run_prompt_text(unit_half, llm_config=llm_cfg, timeout=600,
                           system=_unit_system_prompt(shared_half), max_tokens=16000,
                           template=template)

    def _store(record: dict) -> None:
        def _apply(fresh: PtSession) -> None:
            step6_f = dict(fresh.step6 or {})
            chunks = dict(step6_f.get("chunks") or {})
            prev = dict(chunks.get(unit_id) or {})
            prev.update(record)
            chunks[unit_id] = prev
            step6_f["chunks"] = chunks
            fresh.step6 = step6_f
        _pt_persist_fresh(key, _apply, attempts=_PT_CHUNK_WRITE_ATTEMPTS)

    def _fail(reason: str, raw: str = "", keep_code: bool = False) -> dict:
        # KEEP THE REPLY. A refused unit is the one you most need to read: the reviewer has
        # to see what came back to judge whether to re-run it or edit the prompt. Discarding
        # it left a red pill with an error string and no way to act on it — which is what
        # Terrence hit on the first real fan-out (2026-09-02). Capped because a runaway
        # reply would otherwise be persisted into the session row in full.
        #
        # WHERE it lands depends on the path (2026-09-15, the T44297 proof fix-run):
        #  * FIX PASS (guard present): the current unit is valid, reviewed code, and a refused
        #    fix must not cost it. KEEP its code and status untouched — assembly still sees the
        #    current unit — and park the refused reply + reason under `refused`, the way a held
        #    fix parks under `held`. Zeroing the code here wiped two reviewed units while the
        #    surrounding comment claimed it "keeps the OLD chunk".
        #  * GENERATION with a real code draft (`keep_code`, 2026-09-15 per Terrence): there is
        #    no prior unit, but the reply parsed to a whole unit that only failed a shape/lint
        #    check. Record status=error AND KEEP that draft as `code`, so the reviewer opens it,
        #    sees the two lines to fix, and edits it — losing the tokens AND the code is the
        #    worst case. Assembly still blocks on the error status; the draft is not silently
        #    shipped, only kept to act on.
        #  * GENERATION with no usable draft (an LLM error, or a reply with no fenced block):
        #    record status=error with an empty code and the raw reply, so the pill can say why.
        if guard and not guard.get("generation"):
            _store({"refused": {"code": (raw or "")[:_PT_RAW_KEEP_CHARS], "reason": reason,
                                "at": utc_now().isoformat()},
                    **({"prompt": prompt} if edited else {})})
            return {"unit": unit_id, "status": "refused", "error": reason}
        if keep_code:
            _store({"status": "error", "error": reason, "at": utc_now().isoformat(),
                    "code": raw or "", "raw": "", "held": None,
                    **({"prompt": prompt} if edited else {})})
        else:
            _store({"status": "error", "error": reason, "at": utc_now().isoformat(),
                    "raw": (raw or "")[:_PT_RAW_KEEP_CHARS], "code": "", "held": None,
                    **({"prompt": prompt} if edited else {})})
        return {"unit": unit_id, "status": "error", "error": reason}

    if meta.get("error"):
        return _fail(meta.get("content", "LLM error"), meta.get("content", ""))
    blocks = _parse_generated_blocks(meta.get("content", ""))
    code = (blocks.get("test_code") or "").strip()
    if not code:
        return _fail("the reply contained no fenced python block", meta.get("content", ""))
    ok, why = _unit_shape_ok(code, unit)
    if not ok:
        return _fail(why, code, keep_code=True)
    if guard and guard.get("generation"):
        # R2 (2026-09-15): arrival-time lint. A freshly generated unit that introduces a
        # per-unit lint error is refused HERE, seconds after the reply, not at Assemble minutes
        # later. The error is recorded (so the pill can say why) and the caller gets one repair
        # turn (R3) before it stands. No prior unit exists, so nothing is "kept".
        why = _arrival_refusal(key, unit, code, guard.get("ctx") or {}, guard.get("sess"))
        if why:
            _fail(why, code, keep_code=True)
            return {"unit": unit_id, "status": "arrival_refused", "reason": why,
                    "code": code, "usage": meta.get("usage")}
    elif guard:
        # VERIFY BEFORE STORE (G2 + G6, 2026-09-14): a fix pass knows the unit it replaces, so
        # the reply is held to it — frozen frame lines byte-identical, and no lint error the
        # current script does not already have. Either failure keeps the OLD chunk (the
        # reply is kept on the record, as every refusal is) and says why.
        ok, why = _unit_frozen_ok(guard.get("current_code") or "", code, unit)
        if not ok:
            return _fail(why, code)
        why = _unit_evidence_gone(guard, code, unit) or _unit_lint_regression(guard, code, unit)
        if why:
            return _fail(why, code)
        if guard.get("hold"):
            # G7 (D2): a review- or run-driven fix is HELD — the unit's code and status are
            # untouched (assembly still sees the current unit) and the reply waits on the
            # chunk with its diff and G3 scope for a human to Apply or Discard. A bad fix
            # then costs one look at a diff, not an Opus review.
            scope = _unit_diff_scope(guard.get("current_code") or "", code, unit,
                                     guard.get("findings") or [], guard.get("lint_errors") or [],
                                     int(guard.get("unit_lo") or 1))
            _store({"held": {"code": code, "at": utc_now().isoformat(), "diff": scope.pop("diff"),
                             "scope": scope,
                             "llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
                             "usage": meta.get("usage")},
                    "error": "", "refused": None, **({"prompt": prompt} if edited else {})})
            return {"unit": unit_id, "status": "held", "edited": edited, "usage": meta.get("usage")}
    _store({"status": "ok", "code": code, "error": "", "raw": "", "at": utc_now().isoformat(),
            "source": "fix" if (guard and not guard.get("generation")) else "generate",
            "held": None, "refused": None, "repaired": bool(repaired),
            **({"repaired_class": repaired_class} if repaired and repaired_class else {}),
            "llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
            "usage": meta.get("usage"),
            **({"prompt": prompt} if edited else {})})
    return {"unit": unit_id, "status": "ok", "code": code, "edited": edited,
            "usage": meta.get("usage"), "repaired": bool(repaired)}


async def _dispatch_primed(items: list, run) -> None:
    """Run the FIRST unit alone to completion, then fan the rest out concurrently.

    Token-efficiency decision 4 (2026-09-07). A prompt-cache entry becomes readable only
    once the request that wrote it has been processed, so eight units fired in the same
    instant all WRITE the shared half and none reads it — with decision 8 in place that is
    the one remaining wave of full-price input per pass (7 × ~7.9k tokens on T44297). One
    call alone, then everyone else reads what it wrote. The price is one unit's wall clock
    (40–120 s measured) before the pills start filling; Terrence accepted that "hesitantly,
    we will see how long that first unit takes" — if it hurts, this is the function to
    change, not the caller.

    `run` is the per-unit coroutine function (uid, unit, prompt, edited); each item is its
    argument tuple. Runs as its own task, so the endpoint still returns immediately.
    """
    if not items:
        return
    await run(*items[0])
    for it in items[1:]:
        asyncio.create_task(run(*it))


@router.post("/generate_units/{key}")
async def generate_units(key: str, request: Request, body: dict = Body(default={})):
    """Dispatch N units in ONE request and return IMMEDIATELY. Poll /units_status.

    THE DEFECT THIS FIXES (2026-09-02, AWPTCM-T44297 — a total self-deadlock)
    ------------------------------------------------------------------------
    The first per-unit UI fired one `/generate_step` request per unit and awaited each.
    Every one of those holds its connection for the whole LLM call, because the request
    blocks in `registry.submit` until the browser posts a result. A browser allows SIX
    connections per origin.

    So 30 requests fired, 6 took every connection and blocked, and the broker's own
    `/api/agent/next` long-poll could no longer get a connection. Nothing was ever
    claimed, so nothing ever returned, so no connection was ever freed. Measured on the
    live server: `pending: 5` (only ~6 of 30 requests had reached the server at all),
    `session_active: false`, zero `claude` child processes, zero LLM records. Raising
    `ckBrokerWorkers` made it WORSE — each worker holds a long-poll on the same origin.

    No test could have caught it. jsdom's stubbed fetch has no connection limit, so the
    fan-out spec passes either way; it proved the code DISPATCHES concurrently, not that
    the transport can carry it.

    The fix is to stop holding connections. One POST enqueues everything and returns; one
    GET reports progress. Two connections instead of thirty, and real concurrency becomes
    whatever the broker's worker count is.
    """
    data = _data(request)
    sess = _pt_get(key)
    _require_units_current(sess.step6 or {})   # slice A gate
    # Off the event loop (2026-09-08): the context alone is seconds of CPU and every
    # unedited unit is rendered below — inline, that froze the whole server (see
    # step_prompts). The trade is that this handler now yields mid-flight, which is why
    # the in-flight mark moves BEFORE the render further down.
    ctx = await run_in_threadpool(_pt_generation_context, key, data, sess)
    wanted = body.get("units")
    by_id = {u["id"]: u for u in ctx["units"]}
    if isinstance(wanted, list) and wanted:
        items = [(w.get("id"), (w.get("prompt") or ""), bool(w.get("edited")))
                 for w in wanted if w.get("id") in by_id]
    else:
        items = [(u["id"], "", False) for u in ctx["units"]]
    if not items:
        raise HTTPException(400, "No known units to generate.")

    llm_cfg = _llm_cfg_for(sess, "unit_fill")
    already = _pt_units_inflight(key)
    dispatch = [(uid, pr, ed) for uid, pr, ed in items if uid not in already]
    if not dispatch:
        return {"dispatched": [], "already_running": sorted(already)}

    # Marked in flight BEFORE the render, not after: the render below yields the event
    # loop for seconds, and a second click landing in that window would otherwise pass the
    # `already` filter and dispatch the same units twice. The mark is undone if the render
    # itself fails, so a bad context cannot leave pills yellow forever.
    _pt_unit_mark(key, [uid for uid, _, _ in dispatch], True)

    def _prepare() -> list:
        prepared = []
        for uid, supplied, flagged in dispatch:
            unit = by_id[uid]
            # An edit is what the BROWSER says is an edit: `edited: true` on the item. It
            # used to be inferred here by comparing the supplied text with a fresh render,
            # which is how a tab loaded before a deploy fed the whole fan-out stale prompts
            # that were then STORED as reviewer edits and served back by step_prompts — so
            # Re-render could not clear them and the next pass repeated the first
            # (AWPTCM-T44297, 2026-09-07 and 2026-09-08, 76 units). Unflagged text is
            # ignored and the unit renders fresh.
            edited = flagged and bool(supplied.strip())
            prompt = (supplied.strip() if edited
                      else _render_unit_prompt(key, data, sess, ctx, unit))
            prepared.append((uid, unit, prompt, edited))
        return prepared

    try:
        prepared = await run_in_threadpool(_prepare)
    except Exception:
        _pt_unit_mark(key, [uid for uid, _, _ in dispatch], False)
        raise

    sem = asyncio.Semaphore(_PT_UNIT_DISPATCH_MAX)

    async def _one(uid: str, unit: dict, prompt: str, edited: bool):
        # R2: the arrival guard lints each reply the moment it lands, against the frame + the
        # units generated so far. R3: on a refusal, one repair turn on the SAME (unit) model
        # (D2) with the lint text and the refused reply, through the fix prompt.
        gen_guard = {"generation": True, "ctx": ctx, "sess": sess}
        try:
            async with sem:
                res = await run_in_threadpool(_unit_call_and_store, key, uid, prompt,
                                              edited, unit, llm_cfg, "(verbatim)", gen_guard)
                budget = _effective_repair_turns()
                first_class = _lint_class_of((res.get("reason") or "").split(": ", 1)[-1]) \
                    if res.get("status") == "arrival_refused" else ""
                turns = 0
                while res.get("status") == "arrival_refused" and turns < budget:
                    turns += 1
                    reasons = {"lint": [res.get("reason") or ""], "review": [], "run": None}
                    repair_prompt = await run_in_threadpool(
                        _fix_unit_prompt, key, data, sess, ctx, unit, res.get("code") or "", reasons)
                    res = await run_in_threadpool(_unit_call_and_store, key, uid, repair_prompt,
                                                  edited, unit, llm_cfg, "pt_fix_unit", gen_guard,
                                                  True, first_class)
        except Exception as e:
            # A task that dies silently leaves a pill yellow forever. Record the reason on
            # the chunk so the row can say what happened and offer a re-run.
            print(f"[pt] {key}/{uid}: unit dispatch failed: {e}")
            try:
                def _apply_crash(fresh: PtSession) -> None:
                    step6_f = dict(fresh.step6 or {})
                    chunks = dict(step6_f.get("chunks") or {})
                    prev = dict(chunks.get(uid) or {})
                    prev.update({"status": "error", "error": f"dispatch failed: {e}",
                                 "at": utc_now().isoformat()})
                    chunks[uid] = prev
                    step6_f["chunks"] = chunks
                    fresh.step6 = step6_f
                _pt_persist_fresh(key, _apply_crash, attempts=_PT_CHUNK_WRITE_ATTEMPTS)
            except Exception as e2:
                print(f"[pt] {key}/{uid}: could not even record the failure: {e2}")
        finally:
            # Cleared here and not in the worker, so the poll can distinguish "running"
            # from "finished" for the whole lifetime of the task, including a crash.
            _pt_unit_mark(key, [uid], False)

    # Primed fan-out (decision 4): the first unit runs alone so its cache write is there
    # for the other N-1 to read; they then fan out under the semaphore as before.
    asyncio.create_task(_dispatch_primed(prepared, _one))
    return {"dispatched": [u for u, _, _, _ in prepared],
            "already_running": sorted(already),
            "max_concurrent": _PT_UNIT_DISPATCH_MAX,
            "primed": prepared[0][0] if len(prepared) > 1 else None}


# --- R5 trends + 6.4 alarms ------------------------------------------------------------------
#
# Thresholds ACCEPTED by Terrence 2026-09-15. A class is a PROMPT defect (the generate prompt
# should stop producing it) when, over the trailing window, it was repaired-or-refused on >=10%
# of units OR appeared in 3 consecutive runs. A class is a LINT-TEXT defect (the message does not
# tell the model what to change — D1) when its repair RETURN RATE is < 50%. A "run" is one
# assembly's lint-history entry; the repair figures come from the units' chunks.
_PT_TREND_WINDOW = 5
_PT_PROMPT_DEFECT_UNIT_FRACTION = 0.10
_PT_PROMPT_DEFECT_CONSECUTIVE = 3
_PT_LINT_TEXT_RETURN_RATE = 0.50
_pt_trend_cache: dict = {"at": 0.0, "value": None}
_PT_TREND_TTL = 60.0


def _pt_repair_stats_from_chunks(chunks: dict) -> dict:
    """{class: {"repaired_ok": n, "arrival_failed": n}} from one session's chunks. A repaired-ok
    unit carries `repaired_class`; an arrival failure is an error chunk whose message is the
    arrival lint's."""
    from collections import defaultdict
    out: dict = defaultdict(lambda: {"repaired_ok": 0, "arrival_failed": 0})
    for ch in (chunks or {}).values():
        if ch.get("repaired") and ch.get("status") == "ok":
            out[ch.get("repaired_class") or "other"]["repaired_ok"] += 1
        err = ch.get("error") or ""
        if ch.get("status") == "error" and err.startswith("generated unit has lint error"):
            out[_lint_class_of(err.split(": ", 1)[-1])]["arrival_failed"] += 1
    return {k: dict(v) for k, v in out.items()}


def _pt_lint_trends(window: int = _PT_TREND_WINDOW) -> dict:
    """Aggregate the last `window` assembly runs (any case) plus the repair figures on their
    sessions, and raise the 6.4 alarms. Read-only over the sessions table."""
    import db as _db
    from collections import Counter, defaultdict
    runs = []                                            # (updated_at, entry, chunks)
    try:
        rows = _db.snapshot_sessions()
    except Exception as e:
        return {"error": str(e), "alarms": [], "runs": 0}
    for sid, kind, case_key, payload, _llm, updated_at in rows:
        if kind != "pt":
            continue
        try:
            raw = json.loads(payload) if isinstance(payload, str) else (payload or {})
        except Exception:
            continue
        s6 = raw.get("step6") or {}
        hist = s6.get("lint_history") or []
        if hist:
            runs.append((updated_at or "", hist[-1], s6.get("chunks") or {}, case_key or sid))
    runs.sort(key=lambda r: r[0], reverse=True)
    runs = runs[:window]
    if not runs:
        return {"runs": 0, "window": window, "alarms": [], "by_class": {}, "prompt_version": _generate_prompt_version()}
    total_units = sum(int(e.get("units") or 0) for _, e, _, _ in runs) or 1
    class_lint = Counter()
    class_runs = defaultdict(int)                        # in how many runs a class appeared
    repair = defaultdict(lambda: {"repaired_ok": 0, "arrival_failed": 0})
    for _at, entry, chunks, _ck in runs:
        for cls, n in (entry.get("by_class") or {}).items():
            class_lint[cls] += n
            class_runs[cls] += 1
        for cls, st in _pt_repair_stats_from_chunks(chunks).items():
            repair[cls]["repaired_ok"] += st["repaired_ok"]
            repair[cls]["arrival_failed"] += st["arrival_failed"]
    alarms = []
    for cls in sorted(set(class_lint) | set(repair)):
        rep = repair.get(cls, {"repaired_ok": 0, "arrival_failed": 0})
        touched = rep["repaired_ok"] + rep["arrival_failed"] + class_lint.get(cls, 0)
        frac = touched / total_units
        if frac >= _PT_PROMPT_DEFECT_UNIT_FRACTION or class_runs.get(cls, 0) >= _PT_PROMPT_DEFECT_CONSECUTIVE:
            alarms.append({"class": cls, "kind": "prompt_defect",
                           "detail": f"class `{cls}` touched {touched}/{total_units} units "
                                     f"({frac:.0%}) over {len(runs)} runs — change the generate prompt, not the repair"})
        attempts = rep["repaired_ok"] + rep["arrival_failed"]
        if attempts >= 3 and (rep["repaired_ok"] / attempts) < _PT_LINT_TEXT_RETURN_RATE:
            alarms.append({"class": cls, "kind": "lint_text_defect",
                           "detail": f"class `{cls}` repair return rate {rep['repaired_ok']}/{attempts} "
                                     f"(<50%) — the lint message is not specific enough"})
    total_ok = sum(r["repaired_ok"] for r in repair.values())
    total_att = total_ok + sum(r["arrival_failed"] for r in repair.values())
    return {"runs": len(runs), "window": window, "total_units": total_units,
            "prompt_version": _generate_prompt_version(),
            "by_class": dict(class_lint), "repair": {k: v for k, v in repair.items()},
            "return_rate": (total_ok / total_att) if total_att else None,
            "alarms": alarms}


def _pt_lint_trends_cached() -> dict:
    import time as _t
    now = _t.time()
    if _pt_trend_cache["value"] is not None and (now - _pt_trend_cache["at"]) < _PT_TREND_TTL:
        return _pt_trend_cache["value"]
    val = _pt_lint_trends()
    # 6.4: log a line the moment a class first crosses a threshold, so a server admin is notified
    # (a monitor can also read /health.pt_lint_alarms). Only NEW alarms log, not every 60s poll.
    try:
        was = {(a["class"], a["kind"]) for a in ((_pt_trend_cache.get("value") or {}).get("alarms") or [])}
        for a in (val.get("alarms") or []):
            if (a["class"], a["kind"]) not in was:
                print(f"[pt] LINT-TREND ALARM ({a['kind']}): {a['detail']}")
    except Exception:
        pass
    _pt_trend_cache.update({"at": now, "value": val})
    return val


def _effective_repair_turns() -> int:
    """D1: 1 by default; 2 while the overall repair return rate is below 50% (the second turn is
    then buying units the first did not fix); back to 1 if that does not move it (an admin call,
    later). Reads the cached trend so it costs nothing per dispatch."""
    try:
        rr = _pt_lint_trends_cached().get("return_rate")
    except Exception:
        rr = None
    if rr is not None and rr < _PT_LINT_TEXT_RETURN_RATE:
        return min(2, _PT_REPAIR_TURNS + 1)
    return _PT_REPAIR_TURNS


@router.get("/lint_trends")
async def lint_trends():
    """R5: the lint trend over the last few runs and the 6.4 alarms. Read-only; the Summary
    banner and the admin panel poll it, and `pt_lint_report.py` prints the same aggregation."""
    return _pt_lint_trends_cached()


@router.get("/units_status/{key}")
async def units_status(key: str):
    """Per-unit status for the pill row. Cheap enough to poll every couple of seconds.

    Deliberately does NOT return each unit's code: 30 units of ~2.5KB on a 2s poll is
    150KB/minute of the same bytes. The UI fetches a unit's code when the reviewer opens
    its page. `changed_at` is the session's own updated_at so a caller can skip a no-op.
    """
    sess = _pt_load(key)
    if sess is None:
        raise HTTPException(404, "PyTest Creator session not found.")
    chunks = (sess.step6 or {}).get("chunks") or {}
    running = _pt_units_inflight(key)
    out = {}
    for uid, ch in chunks.items():
        out[uid] = {"status": ch.get("status") or "pending", "error": ch.get("error") or "",
                    "at": ch.get("at") or "", "chars": len(ch.get("code") or ""),
                    "held": bool(ch.get("held")), "source": ch.get("source") or "",
                    "refused": bool(ch.get("refused")),
                    "refused_reason": (ch.get("refused") or {}).get("reason", "")}
    for uid in running:
        out.setdefault(uid, {"status": "pending", "error": "", "at": "", "chars": 0})
        out[uid]["running"] = True
    return {"units": out, "running": sorted(running),
            "changed_at": getattr(sess, "updated_at", None)}


@router.get("/unit_code/{key}/{unit_id}")
async def unit_code(key: str, unit_id: str):
    """ONE unit's stored reply — the fetch `units_status` says the UI does on open.

    It did not exist until 2026-09-02: the status poll ships no code, and the only thing
    that pulled code was a full `step_prompts` re-render that ran when the WHOLE fan-out
    finished. So during a run every completed unit showed a placeholder, and a unit that
    had been generated by an EARLIER run kept showing that run's code and timestamp as if
    it were current. Both are the same bug — the page could only be right at load and at
    the end. This makes a single unit refreshable at any moment.

    Returns `raw` too, so a refused unit can be read rather than just reported.
    """
    sess = _pt_load(key)
    if sess is None:
        raise HTTPException(404, "PyTest Creator session not found.")
    ch = ((sess.step6 or {}).get("chunks") or {}).get(unit_id)
    if ch is None:
        return {"unit": unit_id, "status": "pending", "code": "", "raw": "",
                "error": "", "at": "", "edited": False}
    return {"unit": unit_id, "status": ch.get("status") or "pending",
            "code": ch.get("code") or "", "raw": ch.get("raw") or "",
            "error": ch.get("error") or "", "at": ch.get("at") or "",
            "edited": bool(ch.get("prompt")),
            "held": ch.get("held") or None, "source": ch.get("source") or "",
            "refused": ch.get("refused") or None}


@router.post("/generate_step/{key}/{unit_id}")
async def generate_step(key: str, unit_id: str, request: Request, body: dict = Body(default={})):
    """Generate ONE unit, blocking until it returns. Kept for a single re-run and for
    dry-run provenance; the UI fans out through /generate_units instead, because one
    blocking request per unit exhausts the browser's six connections per origin and
    deadlocks the broker (see generate_units).

    The prompt is taken from the request VERBATIM when supplied AND flagged `edited`. That
    is the point of the editable frame: the button sends what is on screen, so what the
    reviewer reads is what the model receives. The flag is the browser's, never inferred
    from the text — see generate_units for the two passes that inference cost.
    """
    data = _data(request)
    sess = _pt_get(key)
    _require_units_current(sess.step6 or {})   # slice A gate
    dry_run = await _dry_run(request)
    ctx = await run_in_threadpool(_pt_generation_context, key, data, sess)   # off the loop
    unit = next((u for u in ctx["units"] if u["id"] == unit_id), None)
    if unit is None:
        raise HTTPException(404, f"No such unit '{unit_id}' in this case's skeleton.")

    supplied = (body.get("prompt") or "").strip()
    edited = bool(body.get("edited")) and bool(supplied)
    prompt = (supplied if edited
              else await run_in_threadpool(_render_unit_prompt, key, data, sess, ctx, unit))
    if dry_run:
        return {"prompt": prompt, "unit": unit_id, "edited": edited}

    _pt_unit_mark(key, [unit_id], True)
    try:
        out = await run_in_threadpool(_unit_call_and_store, key, unit_id, prompt,
                                     edited, unit, _llm_cfg_for(sess, "unit_fill"))
    finally:
        _pt_unit_mark(key, [unit_id], False)
    if out.get("status") != "ok":
        raise HTTPException(502, f"Unit {unit_id}: {out.get('error', 'failed')}")
    return out


# ---------------------------------------------------------------------------
# Pass C — the holistic review (PLAN-pytest-creator.md §9.6)
# ---------------------------------------------------------------------------

def _library_prompt_context(step6: dict) -> Dict[str, str]:
    """The companion library (`from <stem> import *`) as prompt context for Review and Fix.

    WHY (2026-09-18, AWPTCM-T33234): the reviewer saw only the script, never the module it
    imports every helper from, so 4 of the final 5 findings were false — `waitForLinkState(...,
    'down')` (the helper handles 'down' explicitly), `checkCurrentPort(..., 'auto', ...)` ('auto'
    means "a negotiated value is present"), `expect_value=True` (declared in the def). A Fix that
    cannot see the library "fixes" a correct call the same way. Empty strings when the suite has
    no library, so the templates' `{% if library_code %}` blocks simply do not render.
    """
    lib = ((step6 or {}).get("files") or {}).get("library") or {}
    return {"library_name": str(lib.get("name") or ""),
            "library_code": str(lib.get("code") or "")}


def _review_lint_findings(sess: PtSession) -> List[str]:
    """The static checks ALREADY performed, as flat lines for the review prompt.

    §9.6: "Asking a model to *ensure it passes lint* is asking it to approximate a checker
    that is already deterministic, offline and free. The right wiring is: run the existing
    lint on the assembled script, and feed ITS findings to the model." So these go in as
    context to be excluded from the review, not as a job to redo — the prompt says
    "do not re-report". Includes warnings (PEP 8 lives there) because a model that cannot
    see them will helpfully rediscover 137 long lines and spend its output saying so.
    """
    lint = (sess.step6 or {}).get("lint") or {}
    out: List[str] = []
    for e in lint.get("errors") or []:
        out.append(f"ERROR: {e}")
    for w in lint.get("warnings") or []:
        out.append(f"warning: {w}")
    return out


# The Review(LLM) `kind` vocabulary — follow-ups #4 (PLAN-t44297-pass-followups), built
# 2026-09-14. Small and DEFINED (each value has a one-line definition in
# pt_review_script.jinja; a test pins the two lists identical) because G5 of
# PLAN-fix-units-guardrails ROUTES on it: a `structural` finding goes to a human, never to
# the fixer. Anything off-enum folds to `other` with the model's tag kept on the finding as
# `kind_raw` — the 2026-09-09 review tagged a parse-index bug `naming_inconsistency` and a
# MISSING precondition `duplicate_setup`, so a tag is audit data, never grounds to reject.
_REVIEW_KINDS = ("verdict_mismatch", "weak_observation", "wrong_symbol",
                 "cross_unit_inconsistency", "missing_precondition", "structural", "other")
_REVIEW_SEVERITIES = ("high", "medium", "low")
_REVIEW_ORDER = {s: i for i, s in enumerate(_REVIEW_SEVERITIES)}


def _normalize_findings(raw: Any, sequence: List[dict]) -> List[dict]:
    """Coerce the model's findings to the stored schema, dropping what cannot be used.

    A finding with no `what` says nothing a reviewer can act on, so it is dropped rather
    than stored as an empty row. Unknown `kind`/`severity` values are folded to 'other'
    and 'medium' rather than rejected — a useful finding under an unexpected label is
    still useful, and rejecting the whole reply over a vocabulary miss is the failure mode
    `extract_json_block` guarding already taught us to avoid.
    """
    valid_steps = {str(s.get("n")) for s in (sequence or [])}
    out: List[dict] = []
    for f in (raw if isinstance(raw, list) else []):
        if not isinstance(f, dict):
            continue
        what = str(f.get("what") or "").strip()
        if not what:
            continue
        kind = str(f.get("kind") or "").strip()
        sev = str(f.get("severity") or "").strip().lower()
        step = f.get("step")
        step_n = str(step) if step is not None and str(step) in valid_steps else None
        row = {
            "severity": sev if sev in _REVIEW_SEVERITIES else "medium",
            "kind": kind if kind in _REVIEW_KINDS else "other",
            "where": str(f.get("where") or "").strip(),
            "step": step_n,
            "what": what,
            "evidence": str(f.get("evidence") or "").strip(),
            "suggestion": str(f.get("suggestion") or "").strip(),
        }
        if kind and kind not in _REVIEW_KINDS:
            row["kind_raw"] = kind          # never invent a tag; keep what the model said
        out.append(row)
    out.sort(key=lambda f: _REVIEW_ORDER.get(f["severity"], 1))
    return out


# ---------------------------------------------------------------------------
# Per-unit Fix + two-tier Review (token-efficiency decision 7, 2026-09-07)
# ---------------------------------------------------------------------------
#
# The whole-script Fix (`fix_script`, below) re-emits the entire file: measured on T44297 it
# changed 9 of 38 classes at 64k output tokens, and it can perturb the 29 it did not need to
# touch. Every finding we have names a class or a line, so it names a UNIT — and a unit can
# be re-generated alone, under the same cached system half as its generation, and spliced
# back by the same assembly. Findings that name nothing (the frame, a library file) stay with
# the whole-script Fix; the endpoint reports them as `unmapped` rather than guessing.
#
# Two-tier Review: the deterministic pass goes to green FIRST. Review refuses (409) while the
# lint has blocking errors, because asking a model to review a script that does not compile
# spends its whole budget rediscovering what the checker already said.

_TC_NAME_RX = re.compile(r"\bTestCase_(\d+)\b")
_LINE_REF_RX = re.compile(r"\bline (\d+)\b|:(\d+):")
_SETUP_REF_RX = re.compile(r"\bTestSet\b|\bconfigure\(\)|\btear_down\(\)|\bTestSet\.(configure|tear_down)\b")


def _unit_id_for_text(text: str, code_units: List[dict]) -> Optional[str]:
    """Which unit a lint line / run result / review `where` talks about, or None.

    Class name first (`TestCase_14` -> tc14), then the setup pair (a TestSet /
    configure() / tear_down() mention with no TestCase named), then a line number inside a
    unit's range in the ASSEMBLED script. `code_units` comes from `_skeleton_units(code)`
    run on the assembled script — the same parser as the frame, so the ranges are exact.
    """
    text = text or ""
    ids = {u["id"] for u in code_units}
    m = _TC_NAME_RX.search(text)
    if m and f"tc{m.group(1)}" in ids:
        return f"tc{m.group(1)}"
    if _SETUP_REF_RX.search(text) and "setup" in ids:
        return "setup"
    for m in _LINE_REF_RX.finditer(text):
        ln = int(m.group(1) or m.group(2))
        for u in code_units:
            lo, hi = u["lines"]
            if lo <= ln <= hi:
                return u["id"]
    return None


def _unit_id_for_finding(f: dict, ctx: dict, code_units: List[dict]) -> Optional[str]:
    """Which unit a review finding is ABOUT. `where` is authoritative (G1, RC1 of
    PLAN-fix-units-guardrails): the reviewer's stated location is resolved ALONE first, and
    `evidence`, then `step`, are consulted only when `where` names nothing.

    Before 2026-09-14 `where` and `evidence` were concatenated and searched for a class
    name, so prose in the evidence hijacked the target: T44297 review #2 finding 5 said
    where=TestSet.configure and its evidence mentioned "TestCase_1 logs 'STEP 1'" — the fix
    landed on tc1, a unit the finding was not about, and cost an Opus review to discover.
    A `where` on the suite (`TestSet…`) can therefore never yield a TestCase.
    """
    ids = {u["id"] for u in code_units}
    where = str(f.get("where") or "")
    if re.search(r"\bTestSet\b", where) and "setup" in ids:
        return "setup"
    uid = _unit_id_for_text(where, code_units)
    if uid:
        return uid
    uid = _unit_id_for_text(str(f.get("evidence") or ""), code_units)
    if uid:
        return uid
    step = f.get("step")
    if step is None:
        return None
    for u in ctx["units"]:
        src = _unit_source_step(u, ctx["tc_steps"])
        if src and str(src.get("n")) == str(step):
            return u["id"]
    return None


# G5 (RC5): a finding whose resolution is a DESIGN change is indistinguishable, to the
# fixer, from a one-line condition fix — so it used to be regenerated like one, producing
# scope changes nobody approved. Two shapes are routable without a model: the finding asks
# for a verdict inside the config-only suite setup (D3: ALWAYS structural — the setup unit
# is config-only by the framework contract), or its suggestion implies adding a case or
# moving a step. Plus the reviewer's own `structural` tag (follow-ups #4).
_VERDICT_ASK_RX = re.compile(
    r"\bpass(ed)?\s*/\s*fail|\bpassed\(|\bfailed\(|\bassert\w*\b|\bverdict\b|"
    r"\bverif(y|ies|ied|ication)\b|\bcheck(s|ed)?\s+that\b", re.I)
_CASE_CHANGE_RX = re.compile(
    # "add a (new) TestCase / case"  — the article or the class word must follow directly,
    # so "Add `dutA.cmd(...)`" (a fix) and "add a case-specific settle" do not match.
    r"\b(add|create|introduce)\w*\s+(a |an |one |another )?(new |separate |dedicated )?"
    r"(test ?case|testcase_?\d*|case)\b(?!-)|"
    # "split/move … into/to a (new) case / its own case / unit"
    r"\b(split|move)\b[^.;]{0,60}?\b(to|into)\s+(a |an |another |its own )?"
    r"(new |separate |dedicated )?(test ?case|testcase_?\d*|case|unit)\b(?!-)", re.I)


def _structural_reason(f: dict, uid: Optional[str]) -> Optional[str]:
    """Why this finding must go to a human instead of the fixer, or None if it is fixable."""
    if (f.get("kind") or "") == "structural":
        return "the reviewer tagged it structural"
    text = f"{f.get('what') or ''} {f.get('suggestion') or ''}"
    if uid == "setup" and _VERDICT_ASK_RX.search(text):
        return "asks for a verdict in the config-only suite setup"
    if _CASE_CHANGE_RX.search(str(f.get("suggestion") or "")):
        return "implies adding a case or moving a step"
    return None


def _fix_reasons(sess: PtSession, ctx: dict, code: str) -> dict:
    """Every current reason to fix, sorted onto units: lint errors, review findings and the
    last run's failing cases (with their log excerpts). `unmapped` holds the ones that name
    no unit — those are the whole-script Fix's job."""
    step6 = sess.step6 or {}
    code_units = _skeleton_units(code)
    per: Dict[str, dict] = {}
    unmapped: List[str] = []

    def slot(uid: str) -> dict:
        return per.setdefault(uid, {"lint": [], "review": [], "run": None, "excerpt": ""})

    for e in (step6.get("lint") or {}).get("errors") or []:
        uid = _unit_id_for_text(str(e), code_units)
        if uid:
            slot(uid)["lint"].append(str(e))
        else:
            unmapped.append(f"lint: {e}")
    structural: List[str] = []
    for f in ((step6.get("review") or {}).get("findings")) or []:
        uid = _unit_id_for_finding(f, ctx, code_units)
        why = _structural_reason(f, uid)
        if why:
            # G5: reported with its reason and NEVER dispatched — a design decision, not a
            # regeneration. Kept apart from `unmapped`, which the whole-script Fix owns.
            structural.append(f"structural: {f.get('where') or '(script)'} — "
                              f"{f.get('what') or ''} [{why}]")
            continue
        if uid:
            slot(uid)["review"].append(f)
        else:
            unmapped.append(f"review: {f.get('where') or '(script)'} — {f.get('what') or ''}")
    runs = (sess.step7 or {}).get("runs") or []
    last = runs[-1] if runs else None
    parsed = (last or {}).get("parsed") or {}
    if parsed.get("cases"):
        excerpts: Dict[str, str] = {}
        log_file = (last or {}).get("log_file")
        if log_file and Path(log_file).exists():
            excerpts = {e["case"]: e["text"] for e in failure_excerpts(
                Path(log_file).read_text(encoding="utf-8", errors="replace"), parsed)}
        for c in parsed["cases"]:
            if c.get("result") in ("PASS", None):
                continue
            uid = _unit_id_for_text(c.get("name") or "", code_units)
            if uid:
                sl = slot(uid)
                sl["run"] = c
                sl["excerpt"] = excerpts.get(c.get("name") or "", "")
            else:
                unmapped.append(f"run: {c.get('name')} {c.get('result')}")
    return {"per_unit": per, "unmapped": unmapped, "structural": structural,
            "code_units": code_units}


def _chunks_from_code(code: str, ctx: dict) -> Dict[str, str]:
    """Each unit's CURRENT text, read off the assembled script by the same parser that cut
    the frame. The reviewer may have hand-edited the script (save_script) since the units
    landed; re-assembling from stale chunks would silently revert those edits, so the
    chunks are re-synced from what is on screen before any unit is re-generated."""
    lines = code.split("\n")
    out: Dict[str, str] = {}
    for u in _skeleton_units(code):
        lo, hi = u["lines"]
        out[u["id"]] = "\n".join(lines[lo - 1:hi])
    return out


def _resync_chunks(chunks: Dict[str, dict], synced: Dict[str, str]) -> Tuple[Dict[str, dict], List[str]]:
    """G4 (RC3 of PLAN-fix-units-guardrails): re-sync the stored chunks from the assembled
    script, writing ONLY the units whose text differs from what is stored — i.e. a hand-edit
    made since they landed, or a unit that was never stored. An identical unit is returned as
    the very record that was stored, `at` and all: "cannot write to a TC the fix is not
    about" is then literally true at the storage layer, and the per-fix write footprint
    shrinks to the units that actually changed. Returns (chunks, [ids rewritten])."""
    out = dict(chunks or {})
    changed: List[str] = []
    for uid, text in synced.items():
        prev = (chunks or {}).get(uid) or {}
        if prev.get("status") == "ok" and (prev.get("code") or "") == text:
            continue
        rec = dict(prev)
        rec.update({"status": "ok", "code": text, "error": "", "at": utc_now().isoformat(),
                    "source": "script"})
        out[uid] = rec
        changed.append(uid)
    return out, changed


# G3 (RC2): the blast radius of a fix. D1 (2026-09-11): 40 % of the unit's NON-SCAFFOLD lines.
_PT_FIX_SCOPE_RATIO = 0.40


def _unit_methods(unit: dict, code: str) -> List[Tuple[str, int, int]]:
    """[(method, first_line, last_line)] in the unit's own 1-based line numbering. The setup
    pair is two bare methods, so it is parsed inside a synthetic class (its text from the
    assembled script carries class-body indentation). Unparseable → [] (scope unknown)."""
    import ast as ast_mod
    setup = unit.get("kind") == "setup"
    src = ("class _P:\n" + code) if setup else code
    try:
        tree = ast_mod.parse(src)
    except SyntaxError:
        return []
    off = 1 if setup else 0
    out: List[Tuple[str, int, int]] = []
    for node in ast_mod.walk(tree):
        if isinstance(node, (ast_mod.FunctionDef, ast_mod.AsyncFunctionDef)):
            out.append((node.name, node.lineno - off, node.end_lineno - off))
    return out


def _unit_diff_scope(current_code: str, new_code: str, unit: dict, findings: List[dict],
                     lint_errors: List[str], unit_lo: int = 1) -> dict:
    """The diff of a fix reply against the current unit, and how far it reaches.

    Anchors = the current lines a finding's `evidence` quotes (whitespace-insensitive) + the
    lines lint errors name (`line N` in the ASSEMBLED script, mapped through `unit_lo`). A
    changed method that contains no anchor is OUT OF SCOPE — the fix touched something the
    reasons never pointed at. The change ratio is counted over the unit's non-scaffold lines
    (frozen frame lines excluded). Neither refuses anything: legitimate fixes can be sizeable
    (tc6's TLV block), so G7 HOLDS the unit with this record and a human decides."""
    import difflib
    cur = (current_code or "").split("\n")
    new = (new_code or "").split("\n")
    diff = "\n".join(difflib.unified_diff(cur, new, fromfile=f"{unit.get('label')} (current)",
                                          tofile=f"{unit.get('label')} (fix)", lineterm="", n=2))
    methods = _unit_methods(unit, current_code or "")

    def _method_of(line_no: int) -> Optional[str]:
        for name, lo, hi in methods:
            if lo <= line_no <= hi:
                return name
        return None

    anchors: set = set()
    quoted = set()
    for f in findings or []:
        for raw in str(f.get("evidence") or "").split("\n"):
            ln = _norm_ws(raw)
            if ln and "..." not in ln and "…" not in ln:
                quoted.add(ln)
    for i, ln in enumerate(cur, 1):
        if _norm_ws(ln) in quoted:
            anchors.add(i)
    for e in lint_errors or []:
        for m in _LINE_REF_RX.finditer(str(e)):
            n = int(m.group(1) or m.group(2)) - unit_lo + 1
            if 1 <= n <= len(cur):
                anchors.add(n)

    changed_cur: set = set()
    changed_lines = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, cur, new, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        changed_lines += max(i2 - i1, j2 - j1)
        span = range(i1 + 1, i2 + 1) if i2 > i1 else [max(1, i1)]   # an insertion sits at i1
        changed_cur.update(span)
    anchored = sorted({m for m in (_method_of(a) for a in anchors) if m})
    changed = sorted({m for m in (_method_of(c) for c in changed_cur) if m})
    frozen = set(_unit_frozen_lines(unit, current_code or ""))
    setup = unit.get("kind") == "setup"
    non_scaffold = sum(1 for ln in cur if ln.strip()
                       and (ln.strip() if setup else ln) not in frozen)
    ratio = changed_lines / max(1, non_scaffold)
    return {
        "diff": diff,
        "anchors": len(anchors),
        "anchored_methods": anchored,
        "changed_methods": changed,
        "out_of_scope_methods": [m for m in changed if m not in anchored] if anchored else [],
        "changed_lines": changed_lines,
        "non_scaffold_lines": non_scaffold,
        "change_ratio": round(ratio, 2),
        "over_threshold": ratio > _PT_FIX_SCOPE_RATIO,
    }


def _apply_held(chunks: Dict[str, dict], ids: Optional[List[str]]) -> Tuple[Dict[str, dict], List[str]]:
    """G7 Apply: promote each held fix (all of them when `ids` is None) to the unit's code.
    Returns (chunks, applied ids). A unit with nothing held is left alone."""
    out = dict(chunks or {})
    applied: List[str] = []
    for uid, ch in (chunks or {}).items():
        held = (ch or {}).get("held")
        if not held or (ids is not None and uid not in ids):
            continue
        rec = dict(ch)
        rec.update({"status": "ok", "code": held.get("code") or rec.get("code") or "",
                    "error": "", "raw": "", "at": utc_now().isoformat(), "source": "fix",
                    "llm": held.get("llm"), "usage": held.get("usage"), "held": None})
        out[uid] = rec
        applied.append(uid)
    return out, applied


def _discard_held(chunks: Dict[str, dict], ids: Optional[List[str]]) -> Tuple[Dict[str, dict], List[str]]:
    out = dict(chunks or {})
    dropped: List[str] = []
    for uid, ch in (chunks or {}).items():
        if (ch or {}).get("held") and (ids is None or uid in ids):
            rec = dict(ch); rec["held"] = None
            out[uid] = rec
            dropped.append(uid)
    return out, dropped


def _archive_script_history(group: str, name: str, iteration: int, file_name: str,
                            previous_code: str) -> str:
    """Archive what a fix replaces, as the whole-script Fix does. Returns the directory."""
    hist_dir = _meta_dir(group or "Ungrouped", name or "unnamed") / "history" / f"iter-{iteration}"
    hist_dir.mkdir(parents=True, exist_ok=True)
    (hist_dir / file_name).write_text(previous_code, encoding="utf-8")
    return str(hist_dir)


def _fix_unit_prompt(key: str, data: dict, sess: PtSession, ctx: dict, unit: dict,
                     current_code: str, reasons: dict) -> str:
    """The generation prompt for this unit — shared half, marker, unit half — followed by the
    fix addendum. Same shared half => same system prompt => the cache the generation pass
    wrote is read here too."""
    gen = _render_unit_prompt(key, data, sess, ctx, unit)
    shared, unit_half = _split_unit_prompt(gen)
    fix_half = render_prompt("pt_fix_unit.jinja", {
        "unit_label": unit["label"], "kind": unit["kind"],
        "current_code": current_code,
        "lint_errors": reasons.get("lint") or [],
        "review_findings": reasons.get("review") or [],
        "run_result": reasons.get("run"),
        "log_excerpt": reasons.get("excerpt") or "",
    })
    return shared + "\n\n" + _PT_PROMPT_SPLIT + "\n\n" + unit_half + "\n\n" + fix_half


async def _run_primed_and_wait(items: list, run) -> None:
    """`_dispatch_primed`, but WAITS for the fan-out too — the fix chain re-assembles after
    the last unit lands, so it needs to know when that is."""
    if not items:
        return
    await run(*items[0])
    if items[1:]:
        await asyncio.gather(*(run(*it) for it in items[1:]))


def _lint_blocks_review(step6: dict) -> Optional[str]:
    """The two-tier gate: the message refusing Review, or None when lint is clean enough.
    Blocking errors only — policy errors (`_POLICY_LINT_MARKERS`) are the reviewer's call,
    and style warnings never gate anything."""
    blocking, _policy = _split_lint_errors(((step6 or {}).get("lint") or {}).get("errors") or [])
    if not blocking:
        return None
    return (f"Lint has {len(blocking)} blocking error(s). Review runs only on a lint-clean "
            f"script (two-tier review): run Fix units to clear them, then Review.")


@router.post("/fix_units/{key}")
async def fix_units(key: str, request: Request, body: dict = Body(default={})):
    """Re-generate ONLY the units the current findings name, then re-assemble. Returns
    immediately like generate_units; poll /units_status, and read step6.fix_units when the
    last unit lands for what happened (assembled / lint / failed / unmapped)."""
    data = _data(request)
    sess = _pt_get(key)
    _require_units_current(sess.step6 or {})   # slice A gate
    step6 = sess.step6 or {}
    test = (step6.get("files") or {}).get("test") or {}
    code = test.get("code") or ""
    if not code:
        raise HTTPException(409, "No assembled script to fix.")
    ctx = _pt_generation_context(key, data, sess)
    if not ctx["units"]:
        raise HTTPException(409, "The skeleton has no fillable units — confirm step 4 first.")
    reasons = _fix_reasons(sess, ctx, code)
    if not reasons["per_unit"] and not reasons["unmapped"] and not reasons["structural"]:
        raise HTTPException(409, "Nothing to fix: no lint errors, review findings or failed "
                                 "run results.")
    if not reasons["per_unit"]:
        parts = []
        if reasons["structural"]:
            parts.append(f"{len(reasons['structural'])} structural finding(s) need a design "
                         f"decision, not a model fix: " + "; ".join(reasons["structural"][:3]))
        if reasons["unmapped"]:
            parts.append(f"{len(reasons['unmapped'])} finding(s) name no unit — use the "
                         f"whole-script Fix for these: " + "; ".join(reasons["unmapped"][:5]))
        raise HTTPException(409, " ".join(parts))
    synced = _chunks_from_code(code, ctx)
    missing = [u["id"] for u in ctx["units"] if u["id"] not in synced]
    if missing:
        raise HTTPException(409, "The assembled script does not contain every unit of the "
                                 "frame (" + ", ".join(missing) + ") — was it generated "
                                 "whole-script? Use the whole-script Fix.")

    # G4: write only what changed. A unit whose stored text already equals what is on
    # screen is not touched — not re-stamped, not re-written — and when nothing differs and
    # there is no previous fix_units record to clear, the session row is not written at all.
    _, changed = _resync_chunks(step6.get("chunks") or {}, synced)

    def _sync(fresh: PtSession) -> None:
        step6_f = dict(fresh.step6 or {})
        new_chunks, changed_now = _resync_chunks(step6_f.get("chunks") or {}, synced)
        if changed_now:
            step6_f["chunks"] = new_chunks
        step6_f.pop("fix_units", None)
        fresh.step6 = step6_f
    if changed or "fix_units" in step6:
        _pt_persist_fresh(key, _sync, attempts=_PT_CHUNK_WRITE_ATTEMPTS)

    by_id = {u["id"]: u for u in ctx["units"]}
    already = _pt_units_inflight(key)
    targets = [uid for uid in reasons["per_unit"] if uid in by_id and uid not in already]
    if not targets:
        return {"dispatched": [], "already_running": sorted(already),
                "unmapped": reasons["unmapped"], "structural": reasons["structural"]}
    llm_cfg = _llm_cfg_for(sess, "unit_fill")
    prepared = [(uid, by_id[uid],
                 _fix_unit_prompt(key, data, sess, ctx, by_id[uid], synced[uid],
                                  reasons["per_unit"][uid]), False)
                for uid in targets]
    # G2 + G6: what each reply is held to. The baseline is the current script's own lint, so
    # a fix is refused only for errors it INTRODUCES, never for ones it inherited.
    baseline_errors = (step6.get("lint") or {}).get("errors")
    if baseline_errors is None:
        baseline_errors = _lint_generated(sess).get("errors") or []
    lo_by_id = {u["id"]: u["lines"][0] for u in reasons["code_units"]}
    guards = {uid: {"current_code": synced[uid], "assembled_code": code, "sess": sess,
                    "baseline_errors": list(baseline_errors),
                    "findings": list(reasons["per_unit"][uid]["review"]),
                    "lint_errors": list(reasons["per_unit"][uid]["lint"]),
                    "unit_lo": lo_by_id.get(uid, 1),
                    # D2: review- or run-driven fixes are HELD for approval (G7); a lint-only
                    # fix is deterministic and applies itself (D1: it bypasses the gate).
                    "hold": bool(reasons["per_unit"][uid]["review"]) or bool(reasons["per_unit"][uid]["run"])}
              for uid in targets}
    naming = step6.get("naming") or {}
    group = (naming.get("group") or "").strip()
    name = (naming.get("name") or _art_script_name(key)).strip()
    previous_code = code
    iteration = int(step6.get("iterations") or 1)
    file_name = test.get("name") or f"{name}.py"

    _pt_unit_mark(key, targets, True)
    sem = asyncio.Semaphore(_PT_UNIT_DISPATCH_MAX)

    async def _one(uid: str, unit: dict, prompt: str, edited: bool):
        try:
            async with sem:
                await run_in_threadpool(_unit_call_and_store, key, uid, prompt, edited,
                                        unit, llm_cfg, "pt_fix_unit", guards.get(uid))
        except Exception as e:
            print(f"[pt] {key}/{uid}: unit fix failed: {e}")
            try:
                def _apply_crash(fresh: PtSession) -> None:
                    step6_f = dict(fresh.step6 or {})
                    chunks = dict(step6_f.get("chunks") or {})
                    prev = dict(chunks.get(uid) or {})
                    prev.update({"status": "error", "error": f"fix failed: {e}",
                                 "at": utc_now().isoformat()})
                    chunks[uid] = prev
                    step6_f["chunks"] = chunks
                    fresh.step6 = step6_f
                _pt_persist_fresh(key, _apply_crash, attempts=_PT_CHUNK_WRITE_ATTEMPTS)
            except Exception as e2:
                print(f"[pt] {key}/{uid}: could not even record the failure: {e2}")
        finally:
            _pt_unit_mark(key, [uid], False)

    async def _chain():
        await _run_primed_and_wait(prepared, _one)
        record: Dict[str, Any] = {"at": utc_now().isoformat(), "units": targets,
                                  "unmapped": reasons["unmapped"],
                                  "structural": reasons["structural"], "assembled": False}
        try:
            fresh = _pt_load(key)
            chunks = ((fresh.step6 if fresh else None) or {}).get("chunks") or {}
            failed = [u for u in targets if (chunks.get(u) or {}).get("status") != "ok"]
            refused = [u for u in targets if u not in failed and (chunks.get(u) or {}).get("refused")]
            held = [u for u in targets if u not in failed and u not in refused and (chunks.get(u) or {}).get("held")]
            applied = [u for u in targets if u not in failed and u not in refused and u not in held]
            record["failed"] = failed
            record["refused"] = refused      # G2/G6: the reply was worse; the CURRENT unit is kept
            record["held"] = held            # G7: waiting on the unit pages for Apply / Discard
            record["applied"] = applied      # lint-only fixes, spliced straight in (D2)
            # A refused unit keeps valid code, so the assembly WOULD splice — but a run that
            # could not clean every unit it touched should not silently ship a partial result;
            # the reviewer sees what was refused and re-runs or edits. (R4 will settle these.)
            if fresh is not None and not failed and not refused and applied:
                record["previous_archived"] = _archive_script_history(
                    group, name, iteration, file_name, previous_code)
                res = await run_in_threadpool(_assemble_and_store, key, fresh, ctx, group, name)
                record["assembled"] = True
                record["lint_ok"] = bool((res.get("lint") or {}).get("ok"))
                record["lint_errors"] = len((res.get("lint") or {}).get("errors") or [])
        except Exception as e:
            record["error"] = str(getattr(e, "detail", e))

        def _apply_record(f2: PtSession) -> None:
            step6_f = dict(f2.step6 or {})
            step6_f["fix_units"] = record
            f2.step6 = step6_f
        try:
            _pt_persist_fresh(key, _apply_record, attempts=_PT_CHUNK_WRITE_ATTEMPTS)
        except Exception as e:
            print(f"[pt] {key}: could not record the fix_units outcome: {e}")

    asyncio.create_task(_chain())
    return {"dispatched": targets, "already_running": sorted(already),
            "unmapped": reasons["unmapped"], "structural": reasons["structural"],
            "primed": targets[0] if len(targets) > 1 else None,
            "counts": {uid: {"lint": len(r["lint"]), "review": len(r["review"]),
                             "run": bool(r["run"])}
                       for uid, r in reasons["per_unit"].items()}}


@router.post("/apply_held/{key}")
async def apply_held(key: str, request: Request, body: dict = Body(default={})):
    """G7 Apply: promote the held fix of the named units (`{"units": [...]}`; omitted = all
    held) into their chunks, archive the previous script, re-assemble and re-lint through the
    one assembly. LOCAL — no model. A unit whose held reply has since been superseded (the
    unit was regenerated) has nothing held and is skipped."""
    data = _data(request)
    sess = _pt_get(key)
    _require_units_current(sess.step6 or {})   # slice A gate
    step6 = sess.step6 or {}
    want = body.get("units")
    ids = [str(u) for u in want] if isinstance(want, list) else None
    _, applied = _apply_held(step6.get("chunks") or {}, ids)
    if not applied:
        raise HTTPException(409, "Nothing held to apply" + (f" for {', '.join(ids)}" if ids else "") + ".")
    ctx = _pt_generation_context(key, data, sess)
    naming = step6.get("naming") or {}
    group = (naming.get("group") or "").strip()
    name = (naming.get("name") or _art_script_name(key)).strip()
    test = (step6.get("files") or {}).get("test") or {}
    previous_code = test.get("code") or ""
    iteration = int(step6.get("iterations") or 1)
    file_name = test.get("name") or f"{name}.py"

    def _promote(fresh: PtSession) -> None:
        step6_f = dict(fresh.step6 or {})
        new_chunks, _done = _apply_held(step6_f.get("chunks") or {}, applied)
        step6_f["chunks"] = new_chunks
        fresh.step6 = step6_f
    fresh = _pt_persist_fresh(key, _promote, attempts=_PT_CHUNK_WRITE_ATTEMPTS)
    archived = _archive_script_history(group, name, iteration, file_name, previous_code) if previous_code else ""
    res = await run_in_threadpool(_assemble_and_store, key, fresh, ctx, group, name)
    return {"applied": applied, "assembled": True,
            "lint_ok": bool((res.get("lint") or {}).get("ok")),
            "lint_errors": len((res.get("lint") or {}).get("errors") or []),
            "previous_archived": archived}


@router.post("/discard_held/{key}")
async def discard_held(key: str, body: dict = Body(default={})):
    """G7 Discard: drop the held fix of the named units (omitted = all). The unit's current
    code stays exactly as it is. LOCAL."""
    sess = _pt_get(key)
    want = body.get("units")
    ids = [str(u) for u in want] if isinstance(want, list) else None
    _, dropped = _discard_held((sess.step6 or {}).get("chunks") or {}, ids)
    if not dropped:
        raise HTTPException(409, "Nothing held to discard.")

    def _drop(fresh: PtSession) -> None:
        step6_f = dict(fresh.step6 or {})
        new_chunks, _ = _discard_held(step6_f.get("chunks") or {}, dropped)
        step6_f["chunks"] = new_chunks
        fresh.step6 = step6_f
    _pt_persist_fresh(key, _drop, attempts=_PT_CHUNK_WRITE_ATTEMPTS)
    return {"discarded": dropped}


@router.post("/review_script/{key}")
async def review_script(key: str, request: Request):
    """Pass C: review the ASSEMBLED script and return FINDINGS — never a rewrite.

    §9.6 is explicit that this must not return a revised script: a rewrite pass
    re-introduces the whole-script output chunking exists to avoid (the same ~35KB in one
    message, the same wall clock), and it can silently undo a correct reused fragment,
    destroying the provenance chain PLAN §1.5 keeps. Findings route into the existing
    `fix_script` loop instead, where a change is a recorded, reviewable action.

    This does NOT invalidate anything downstream. A review reads the script and writes an
    opinion about it; the artefact is untouched, so `_invalidate_from` would only throw
    away a confirmation on the basis of having looked.
    """
    _data(request)
    sess = _pt_get(key)
    dry_run = await _dry_run(request)
    step6 = sess.step6 or {}
    if not (step6.get("files") or {}).get("test"):
        raise HTTPException(409, "No script to review. Run generate_script first.")
    # Two-tier review (2026-09-07): the deterministic pass goes to green first.
    gate = _lint_blocks_review(step6)
    if gate:
        raise HTTPException(409, gate)

    sequence = (sess.step2 or {}).get("sequence") or []
    meta = await run_in_threadpool(run_prompt, "pt_review_script.jinja", {
        "case_key": key,
        "file_name": step6["files"]["test"]["name"],
        "code": step6["files"]["test"]["code"],
        "sequence": sequence,
        "lint_findings": _review_lint_findings(sess),
        **_library_prompt_context(step6),
    }, llm_config=_llm_cfg(sess), timeout=600, dry_run=dry_run,
       # Findings, not a script: the reply is a small JSON object, so the default
       # completion cap is ample and the default JSON system steer is the right one.
       max_tokens=16000)
    if dry_run:
        return _provenance_preview(meta)
    if meta.get("error"):
        raise HTTPException(502, meta.get("content", "LLM error"))

    parsed = extract_json_block(meta.get("content", ""))
    # AN UNREADABLE ANSWER IS NOT A CLEAN SCRIPT — the same trap gather_fragments fell into
    # (see its comment). "No findings" is a legitimate and expected result here, so a reply
    # that fails to parse must NOT reach the same stored shape as a clean review.
    if parsed is None:
        raise HTTPException(502, "Could not parse the review reply as JSON (an unreadable "
                                 "answer is not 'no findings'). Raw response is in provenance.")

    findings = _normalize_findings(
        parsed.get("findings") if isinstance(parsed, dict) else parsed, sequence)
    review = {
        "at": utc_now().isoformat(),
        "findings": findings,
        "reviewed_lint": _review_lint_findings(sess),
        "code_hash": _code_hash(step6["files"]["test"]["code"]),   # slice B: bound to this code
        "provenance": {
            "llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
            "prompt": meta.get("prompt", ""),
            "response": meta.get("content", ""),
        },
    }

    def _apply(fresh: PtSession) -> None:
        step6_f = dict(fresh.step6 or {})
        step6_f["review"] = review
        fresh.step6 = step6_f

    _pt_persist_fresh(key, _apply)
    return {"findings": findings, "at": review["at"],
            "counts": {s: sum(1 for f in findings if f["severity"] == s)
                       for s in _REVIEW_SEVERITIES}}


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
    # Pass C findings are a third, independent reason to fix (§9.6): they name defects
    # NEITHER the linter nor a run can see — a verdict that does not match its step's
    # `verify` text passes lint and passes on the bench, wrongly. Before this, a reviewed
    # script with real findings and a green lint 409'd with "nothing to fix".
    review_findings = ((step6.get("review") or {}).get("findings")) or []
    if not parsed.get("cases") and not lint_errors and not review_findings:
        raise HTTPException(409, "Nothing to fix: no failed run results, lint errors or "
                                 "review findings.")

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
        "review_findings": review_findings,
        "results": parsed.get("cases", []),
        "log_excerpts": excerpts,
        **_library_prompt_context(step6),
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
        # On a fresh copy, so a concurrent save cannot turn the record of a failure into a
        # second failure (see _pt_persist_fresh).
        _attempt_f = {
            "at": utc_now().isoformat(), "phase": "fix", "reason": fix_failure,
            "llm": {k: meta.get(k) for k in ("provider", "model", "auth_method")},
            "prompt": meta.get("prompt", ""), "response": meta.get("content", ""),
            "recovery": blocks["report"], "rejected_code": blocks["test_code"] or "",
        }

        def _apply_fix_failure(fresh: PtSession) -> None:
            step6_f = dict(fresh.step6 or {})
            attempts_f = list(step6_f.get("failed_generations") or [])
            attempts_f.append(_attempt_f)
            step6_f["failed_generations"] = attempts_f[-3:]
            fresh.step6 = step6_f

        _pt_persist_fresh(key, _apply_fix_failure)
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

    # The replacement is applied to the CURRENT stored step6, not the pre-LLM snapshot:
    # `save_script` lets a reviewer hand-edit the code while a fix runs, and writing the
    # snapshot back would silently revert that edit as well as risking a 409.
    _fixed: Dict[str, Any] = {}

    def _apply_fix(fresh: PtSession) -> None:
        step6_n = dict(fresh.step6 or {})
        files_n = dict(step6_n.get("files") or {})
        test_n = dict((files_n.get("test") or {}))
        test_n["code"] = stamped_code
        files_n["test"] = test_n
        if blocks["library"]:
            files_n["library"] = blocks["library"]
        step6_n["files"] = files_n
        step6_n["iterations"] = iteration + 1
        step6_n["confirmed"] = False
        # A fix produces a NEW artefact, so its predecessor's review no longer describes what
        # is on screen — mirror assemble_script and drop it, or the pre-fix findings read as
        # if they were about the rewritten script (2026-09-04). The reviewer re-runs Review to
        # see what remains.
        step6_n.pop("review", None)
        fresh.step6 = step6_n
        _invalidate_from(fresh, 6)  # revised code must be re-reviewed and re-run
        # PERSIST the fresh lint. It was previously computed and returned to the caller but
        # never written back to the session, so the panel kept rendering the PRE-fix lint
        # until a manual Re-lint. Store it here so the assembled-script status is current.
        lint_now = _lint_generated(fresh)
        step6_l = dict(fresh.step6)
        step6_l["lint"] = lint_now
        # Slice A: a whole-script fix wrote the script alone; re-chunk so the units and the
        # frame follow it. If the new script does not split, the state stays DIVERGED (pill
        # on, splice paths closed) rather than pretending.
        _try_rechunk(step6_l, (fresh.step2 or {}).get("sequence") or [])
        fresh.step6 = step6_l
        _fixed["lint"] = lint_now
        _fixed["files"] = fresh.step6["files"]
        _fixed["iterations"] = fresh.step6["iterations"]

    _pt_persist_fresh(key, _apply_fix)
    return {"files": _fixed["files"], "iterations": _fixed["iterations"],
            "lint": _fixed["lint"], "previous_archived": str(hist_dir)}


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

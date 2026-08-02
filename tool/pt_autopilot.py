#!/usr/bin/env python3
"""Autopilot: drive the FULL Ask-CK pipeline for a batch of cases, headlessly.

What it automates, end to end, per case:

  Generator (Objective / Test Case)      PyTest Creator
  ---------------------------------      ------------------------------------
  1  load_case                           1  load_case  (needs the refined bundle)
  2  suggest_testlink -> confirm 1       2  extract_sequence -> confirm 2
  3  suggest_zephyr   -> confirm 2       3  suggest_scripts -> save_matches -> confirm 3
  4  suggest_atp      -> confirm 3       4  gather_fragments -> confirm 5
  5  synthesize_objectives               5  generate_script -> confirm 6 (+ lint)
  6  confirm_objectives
  7  synthesize_steps
  8  export  -> refined-cases/<Group>/<KEY>/

Why a driver at all, when both tools already have a UI: the review steps are
*human* gates by design, and every one of them is also an API endpoint with an
LLM "suggest" partner. Autopilot substitutes the LLM's own shortlist for the
reviewer's click and records that it did so, so the output is honest about being
machine-reviewed rather than looking hand-confirmed.

Every LLM call goes through the RUNNING SERVER, not a direct model call. That is
deliberate: the prompts, the CLI grounding, the coverage gate, the skeleton and
the lints are the product. Calling a model directly would test the model instead
of the pipeline. Which model runs is therefore whatever the workspace LLM default
is set to (`/api/wizard/llm_config`) — set it before starting and this records it.

Resumability is a first-class requirement, not a nicety: a batch of ten cases is
tens of Opus calls and can outlive a session. State lives in TWO places and both
are authoritative for different things — the server's own session rows (what work
exists) and this tool's `state.json` (what the batch has attempted). Re-running is
always safe: each phase re-reads the live session and SKIPS a step that is already
confirmed, so an interrupted batch resumes at the first unfinished step rather
than paying for completed ones twice.

Usage:
    python3 tool/pt_autopilot.py --cases-file cases.txt --phase all
    python3 tool/pt_autopilot.py --case AWPTCM-T33302 --phase generator
    python3 tool/pt_autopilot.py --cases-file cases.txt --phase pytest --run-dir <dir>
    python3 tool/pt_autopilot.py --cases-file cases.txt --status
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER = "http://localhost:8000"

# MUST exceed the server's own ceiling, or the client gives up on work the server then
# finishes and persists — which looks like a failure while actually succeeding, the most
# expensive kind of wrong. llm._CLI_WHOLE_RESPONSE_FLOOR is 1800s for the headless CLI
# backends, so anything at or under that races it. Read the floor from the server's own
# module rather than restating the number, so the two cannot drift apart.
def _server_ceiling(default: int = 1800) -> int:
    try:
        sys.path.insert(0, str(REPO_ROOT / "ask-ck" / "CK-main" / "CK_server"))
        import llm  # noqa: PLC0415
        return int(getattr(llm, "_CLI_WHOLE_RESPONSE_FLOOR", default))
    except Exception:
        return default


HTTP_TIMEOUT = _server_ceiling() + 600

# How many LLM-suggested rows to accept per review step. The UI's two-table
# shortlist has no cap, but an unbounded shortlist inflates every downstream
# prompt, so autopilot takes the top N in the LLM's own order.
MAX_TESTLINK = 8
MAX_ZEPHYR = 8
MAX_ATP = 8
MAX_SCRIPTS_PER_STEP = 3


class Fail(RuntimeError):
    """A step failed in a way that stops this case (but not the batch)."""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _post(path: str, body: Any = None, timeout: int = HTTP_TIMEOUT) -> dict:
    r = requests.post(f"{SERVER}{path}", json=body if body is not None else {}, timeout=timeout)
    if r.status_code >= 400:
        raise Fail(f"POST {path} -> {r.status_code}: {r.text[:600]}")
    return r.json()


def _get(path: str, timeout: int = 120) -> dict:
    r = requests.get(f"{SERVER}{path}", timeout=timeout)
    if r.status_code >= 400:
        raise Fail(f"GET {path} -> {r.status_code}: {r.text[:600]}")
    return r.json()


def _post_soft(path: str, body: Any = None, timeout: int = HTTP_TIMEOUT):
    """POST returning (json|None, status). For endpoints where a 409 is a real answer
    (the coverage gate) rather than a failure."""
    r = requests.post(f"{SERVER}{path}", json=body if body is not None else {}, timeout=timeout)
    try:
        return r.json(), r.status_code
    except Exception:
        return {"detail": r.text[:600]}, r.status_code


def _retry(fn, what: str, log, attempts: int = 2):
    """One retry on a transient LLM failure.

    Scoped narrowly on purpose: a 502 from these endpoints means the model returned
    an error or unparseable output, which a second sample often fixes. A 400/409 is
    a gate talking — retrying that just burns tokens to get the same answer.
    """
    last = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Fail as e:
            last = e
            transient = "502" in str(e) or "timed out" in str(e).lower()
            if not transient or i == attempts:
                raise
            log(f"    retry {i}/{attempts - 1} after transient failure: {str(e)[:200]}")
            time.sleep(3)
    raise last


# ---------------------------------------------------------------------------
# Phase A — Generator
# ---------------------------------------------------------------------------

def _selections_from(suggestions: List[dict], cap: int) -> List[dict]:
    out = []
    for i, s in enumerate(suggestions[:cap]):
        sid = s.get("id") or s.get("key")
        if not sid:
            continue
        out.append({
            "id_or_key": sid,
            "title": s.get("title") or sid,
            "justification": s.get("justification") or s.get("reason") or "LLM suggestion (autopilot)",
            "order": i,
        })
    return out


_REVIEW_STEPS = [
    (1, "suggest_testlink", MAX_TESTLINK),
    (2, "suggest_zephyr", MAX_ZEPHYR),
    (3, "suggest_atp", MAX_ATP),
]


def run_generator(key: str, log, rec: dict) -> dict:
    """Drive the Generator to an exported refined-cases bundle. Idempotent."""
    sess = _post(f"/api/wizard/load_case/{key}")
    if sess.get("read_only"):
        raise Fail("case is locked by another tab/user (read_only) — close it there first")
    s = sess["session"]
    log(f"  loaded: {sess.get('case_title', '')!r}")

    for step, endpoint, cap in _REVIEW_STEPS:
        state = s.get(f"step{step}") or {}
        if state.get("confirmed"):
            log(f"  step{step}: already confirmed ({len(state.get('selections') or [])} selections) — skip")
            continue
        res = _retry(lambda: _post(f"/api/wizard/{endpoint}/{key}"), endpoint, log)
        sugg = res.get("suggestions") or []
        sel = _selections_from(sugg, cap)
        log(f"  step{step}: {len(sugg)} suggested of "
            f"{res.get('num_candidates_considered', '?')} considered -> confirming {len(sel)}")
        out = _post(f"/api/wizard/confirm_step/{key}/{step}",
                    {"selections": sel, **({"none": True} if step == 1 and not sel else {})})
        s = out.get("session", s)
        rec.setdefault("generator_selections", {})[f"step{step}"] = [x["id_or_key"] for x in sel]

    # Step 4 — objective
    if (s.get("step4") or {}).get("objective") and (s.get("step4") or {}).get("confirmed"):
        log("  step4 objective: already confirmed — skip")
    else:
        if not (s.get("step4") or {}).get("objective"):
            log("  step4: synthesizing objective …")
            t0 = time.monotonic()
            _retry(lambda: _post("/api/wizard/synthesize_objectives", {"session": {"key": key}}),
                   "synthesize_objectives", log)
            log(f"    objective synthesized in {time.monotonic() - t0:.0f}s")
        out = _post(f"/api/wizard/confirm_objectives/{key}")
        s = out.get("session", s)

    # Step 5 — steps
    steps_now = ((s.get("step5") or {}).get("testScript") or {}).get("steps") or []
    if steps_now:
        log(f"  step5 steps: already present ({len(steps_now)}) — skip")
    else:
        log("  step5: synthesizing test steps …")
        t0 = time.monotonic()
        res = _retry(lambda: _post("/api/wizard/synthesize_steps", {"session": {"key": key}}),
                     "synthesize_steps", log)
        s = res.get("session", s)
        steps_now = (((res.get("synthesized") or {}).get("testScript")) or {}).get("steps") or []
        log(f"    {len(steps_now)} steps synthesized in {time.monotonic() - t0:.0f}s")
    rec["n_zephyr_steps"] = len(steps_now)

    # Export — the bundle that makes the case Complete (and PyTest-loadable)
    exp = _post("/api/wizard/export", {"session": {"key": key}})
    val = exp.get("validation") or {}
    rec["export"] = {
        "wrote_bundle": exp.get("wrote_bundle"),
        "saved_to": exp.get("saved_to"),
        "valid": val.get("valid"),
        "issues": val.get("issues") or [],
        "warnings": (val.get("warnings") or [])[:6],
        "message": exp.get("message"),
    }
    if not exp.get("wrote_bundle"):
        raise Fail(f"export wrote no bundle: {exp.get('message')} | issues={val.get('issues')}")
    log(f"  exported -> {exp.get('saved_to')} (valid={val.get('valid')})")
    return rec


# ---------------------------------------------------------------------------
# Phase B — PyTest Creator
# ---------------------------------------------------------------------------

def _pt_confirm(key: str, step: int, log, allow_gap: bool = True) -> dict:
    """Confirm a PyTest step, acknowledging a coverage gap only when the server says
    there is one. The gate is a 409 with the untested steps quoted; autopilot has no
    human to ask, so it records the override rather than pretending the gap is absent.
    """
    body, code = _post_soft(f"/api/pytest-create/confirm_step/{key}/{step}")
    if code == 409 and allow_gap:
        detail = (body or {}).get("detail", "")
        log(f"    coverage gate at step {step}: {detail[:300]}")
        body2, code2 = _post_soft(f"/api/pytest-create/confirm_step/{key}/{step}",
                                  {"acknowledge_coverage_gap": True})
        if code2 >= 400:
            raise Fail(f"confirm step {step} failed even with override: {body2}")
        return {"session": (body2 or {}).get("session"), "coverage_gap_acknowledged": detail}
    if code >= 400:
        raise Fail(f"confirm step {step} -> {code}: {body}")
    return {"session": (body or {}).get("session")}


def _script_selections(matches: List[dict], sequence: List[dict]) -> Dict[str, List[str]]:
    """Turn LLM coverage verdicts into the per-step selection map save_matches wants.

    A reviewer picks, for each sequence step, the scripts the match verdict says cover
    THAT step. So do exactly that — `covers_steps` is the verdict's own claim. A match
    that claims no step is not selected anywhere: the honest outcome is 'no reuse for
    this step', which the pipeline already supports (fragments == [] is legitimate).
    """
    valid = {int(s["n"]) for s in sequence if str(s.get("n") or "").strip().isdigit()}
    rank = {"full": 0, "partial": 1}
    by_step: Dict[str, List[str]] = {}
    ordered = sorted(matches, key=lambda m: rank.get(m.get("coverage"), 9))
    for m in ordered:
        sid = m.get("id")
        if not sid:
            continue
        for n in (m.get("covers_steps") or []):
            try:
                n = int(n)
            except (TypeError, ValueError):
                continue
            if n not in valid:
                continue
            bucket = by_step.setdefault(str(n), [])
            if sid not in bucket and len(bucket) < MAX_SCRIPTS_PER_STEP:
                bucket.append(sid)
    return by_step


def run_pytest_creator(key: str, log, rec: dict, trim_verify: int = 0) -> dict:
    """Drive PyTest Creator from a Complete case to a generated + linted script."""
    loaded = _post(f"/api/pytest-create/load_case/{key}")
    if loaded.get("read_only"):
        raise Fail("case is locked by another tab/user (read_only)")
    s = loaded["session"]
    log(f"  loaded: group={loaded.get('group_display')!r} "
        f"objective={len(loaded.get('objective') or '')}ch steps={len(loaded.get('steps') or [])}")
    rec["pt_input_steps"] = len(loaded.get("steps") or [])

    # --- step 2: sequence
    if (s.get("step2") or {}).get("confirmed"):
        seq = (s.get("step2") or {}).get("sequence") or []
        log(f"  step2 sequence: already confirmed ({len(seq)}) — skip")
    else:
        t0 = time.monotonic()
        res = _retry(lambda: _post(f"/api/pytest-create/extract_sequence/{key}"),
                     "extract_sequence", log)
        seq = res.get("sequence") or []
        cov = res.get("coverage") or {}
        log(f"  step2: {len(seq)} sequence steps in {time.monotonic() - t0:.0f}s "
            f"(coverage ok={cov.get('ok')})")
        rec["sequence_kinds"] = {}
        for st in seq:
            k = st.get("kind", "?")
            rec["sequence_kinds"][k] = rec["sequence_kinds"].get(k, 0) + 1
        rec["coverage_step2"] = {"ok": cov.get("ok"), "warning": (cov.get("warning") or "")[:400]}
        out = _pt_confirm(key, 2, log)
        if out.get("coverage_gap_acknowledged"):
            rec["coverage_gap_step2"] = out["coverage_gap_acknowledged"][:400]
        s = out.get("session") or s
        seq = (s.get("step2") or {}).get("sequence") or seq
    rec["n_sequence"] = len(seq)

    # --- optional: trim the sequence so the generated script fits the output budget
    # Generation is capped at ~15 TestCase classes (FINDINGS-generation-size-ceiling.md), and
    # these refined cases run 44-78 sequence steps. Trimming produces a COMPLETE, COMPILING
    # script for a SUBSET of the case — a pipeline proof, never a substitute for the full
    # test. Every dropped step is logged and recorded in state, because a silently shortened
    # test that still reports PASS is the exact failure the coverage gate exists to prevent.
    if trim_verify and not (s.get("step5") or {}).get("confirmed"):
        setup = [x for x in seq if x.get("kind") == "setup"]
        rest = [x for x in seq if x.get("kind") != "setup"]
        if len(rest) > trim_verify:
            kept, dropped = rest[:trim_verify], rest[trim_verify:]
            trimmed = setup + kept
            for i, x in enumerate(trimmed):
                x["n"] = i + 1
            log(f"  TRIM: {len(seq)} -> {len(trimmed)} steps "
                f"({len(setup)} setup + {len(kept)} verify); dropping {len(dropped)}")
            rec["trimmed"] = {
                "from_steps": len(seq), "to_steps": len(trimmed),
                "dropped_count": len(dropped),
                "dropped_actions": [str(x.get("action", ""))[:160] for x in dropped],
                "why": "output-budget ceiling ~15 TestCase classes; this script covers a "
                       "SUBSET of the case and is not a complete test of it",
            }
            _post(f"/api/pytest-create/save_sequence/{key}", {"sequence": trimmed})
            out = _pt_confirm(key, 2, log)
            s = out.get("session") or s
            seq = (s.get("step2") or {}).get("sequence") or trimmed
            rec["n_sequence"] = len(seq)

    # --- step 3: script search
    if (s.get("step3") or {}).get("confirmed"):
        log("  step3 matches: already confirmed — skip")
    else:
        t0 = time.monotonic()
        res = _retry(lambda: _post(f"/api/pytest-create/suggest_scripts/{key}"),
                     "suggest_scripts", log)
        matches = res.get("matches") or []
        sels = _script_selections(matches, seq)
        n_sel = len({x for v in sels.values() for x in v})
        log(f"  step3: {len(matches)} matches of {res.get('mechanical_considered')} mechanical "
            f"in {time.monotonic() - t0:.0f}s -> selecting {n_sel} scripts across {len(sels)} steps")
        _post(f"/api/pytest-create/save_matches/{key}",
              {"selections": sels,
               "user_inputs": "autopilot: selections derived from LLM coverage verdicts"})
        rec["script_selections"] = sels
        rec["n_scripts_selected"] = n_sel
        s = (_pt_confirm(key, 3, log).get("session")) or s

    # --- step 5: fragments (internal step4 'fit decision' is retired — no panel, no gate)
    if (s.get("step5") or {}).get("confirmed"):
        log("  step5 fragments: already confirmed — skip")
    else:
        t0 = time.monotonic()
        res = _retry(lambda: _post(f"/api/pytest-create/gather_fragments/{key}"),
                     "gather_fragments", log)
        log(f"  step5: pool={len(res.get('fragments') or [])} "
            f"selected={len(res.get('selected') or [])} dropped={res.get('dropped')} "
            f"in {time.monotonic() - t0:.0f}s")
        rec["fragments"] = {"pool": len(res.get("fragments") or []),
                            "selected": len(res.get("selected") or []),
                            "dropped": res.get("dropped")}
        s = (_pt_confirm(key, 5, log).get("session")) or s

    # --- step 6: generate
    if (s.get("step6") or {}).get("confirmed"):
        log("  step6 generate: already confirmed — skip")
        step6 = s.get("step6") or {}
    else:
        t0 = time.monotonic()
        res = _retry(lambda: _post(f"/api/pytest-create/generate_script/{key}"),
                     "generate_script", log)
        lint = res.get("lint") or {}
        code = ((res.get("files") or {}).get("test") or {}).get("code") or ""
        log(f"  step6: {res.get('naming')} {len(code)}ch in {time.monotonic() - t0:.0f}s "
            f"errors={len(lint.get('errors') or [])} warnings={len(lint.get('warnings') or [])}")
        for e in (lint.get("errors") or [])[:8]:
            log(f"    LINT ERROR: {e}")
        rec["generate"] = {
            "naming": res.get("naming"),
            "code_chars": len(code),
            "lint_errors": lint.get("errors") or [],
            "lint_warnings": (lint.get("warnings") or [])[:12],
            "iterations": res.get("iterations"),
        }
        # save_script writes the files to generated/ (generate alone only fills the session)
        saved = _post(f"/api/pytest-create/save_script/{key}",
                      {"code": code} if code else {})
        rec["generate"]["written"] = saved.get("written")
        log(f"    written: {saved.get('written')}")
        # A script that does not COMPILE is not a delivered script, and the batch summary must
        # not imply otherwise. The step itself really did complete — the file exists and the
        # lint ran — so this is a distinct outcome rather than a failure: the pipeline worked
        # and the artefact is unusable. Reporting both as "ok" is how a batch comes to claim
        # ten scripts when some fraction of them cannot be imported.
        # Distinguish DOES-NOT-COMPILE from FAILS-A-CONTRACT. They are both lint errors and
        # both block delivery, but they mean different things and point at different fixes:
        # a syntax error is usually the output budget truncating the script mid-token, while a
        # contract error is the model writing valid Python that breaks a house rule (e.g.
        # calling setup.init_portlink() directly and skipping the media assertion). Reporting
        # both as "does not compile" sent me looking for truncation in a script that was in
        # fact complete and parseable.
        errors = lint.get("errors") or []
        syntax = [e for e in errors if e.lower().startswith("syntax")]
        rec["compiles"] = not syntax
        rec["artefact_valid"] = not errors
        rec["lint_syntax_errors"] = syntax
        rec["lint_contract_errors"] = [e for e in errors if e not in syntax]
        if syntax:
            log(f"    DOES NOT COMPILE: {len(syntax)} syntax error(s) — usually the output "
                f"budget truncating the script")
        elif errors:
            log(f"    COMPILES but fails {len(errors)} contract lint(s) — valid Python, "
                f"house rule violated; the fix loop (POST /fix_script) is the remedy")
        else:
            log("    artefact OK: compiles and passes every lint")
        out = _pt_confirm(key, 6, log)
        if out.get("coverage_gap_acknowledged"):
            rec["coverage_gap_step6"] = out["coverage_gap_acknowledged"][:400]
        step6 = ((out.get("session") or {}).get("step6")) or {}
    rec["pt_done"] = True
    return rec


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------

def _load_state(run_dir: Path) -> dict:
    p = run_dir / "state.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"cases": {}}


def _save_state(run_dir: Path, state: dict) -> None:
    (run_dir / "state.json").write_text(json.dumps(state, indent=2, default=str))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", action="append", default=[], help="case key; repeatable")
    ap.add_argument("--cases-file", help="file with one case key per line (# comments ok)")
    ap.add_argument("--phase", choices=["generator", "pytest", "all"], default="all")
    ap.add_argument("--run-dir", help="state/log dir (default: a new timestamped dir)")
    ap.add_argument("--status", action="store_true", help="print progress for the batch and exit")
    ap.add_argument("--stamp", help="run-dir timestamp (scripts cannot mint one repeatably)")
    ap.add_argument("--trim-verify", type=int, default=0, metavar="N",
                    help="cap the sequence at N verification steps so the generated script "
                         "fits the model's output budget (~15 TestCase classes). Produces a "
                         "COMPLETE script for a SUBSET of the case; dropped steps are "
                         "recorded in state.json. See FINDINGS-generation-size-ceiling.md.")
    args = ap.parse_args()

    keys: List[str] = list(args.case)
    if args.cases_file:
        for line in Path(args.cases_file).read_text().splitlines():
            line = line.split("#")[0].strip()
            if line:
                keys.append(line)
    if not keys:
        ap.error("no cases given (--case / --cases-file)")

    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        stamp = args.stamp or time.strftime("%Y%m%d-%H%M%S")
        run_dir = REPO_ROOT / "ask-ck" / "pytest-create" / "autopilot" / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    state = _load_state(run_dir)

    if args.status:
        for k in keys:
            c = state["cases"].get(k, {})
            g = c.get("generate") or {}
            comp, valid = c.get("compiles"), c.get("artefact_valid")
            tri = lambda v: "-" if v is None else ("yes" if v else "NO")
            print(f"{k:16} gen={c.get('generator_status', '-'):8} pt={c.get('pytest_status', '-'):8} "
                  f"seq={str(c.get('n_sequence', '-')):>3} frag={str((c.get('fragments') or {}).get('pool', '-')):>3} "
                  f"code={str(g.get('code_chars', '-')):>6} "
                  f"compiles={tri(comp):>3} lint_clean={tri(valid):>3} "
                  f"trimmed={'-' if not c.get('trimmed') else str(c['trimmed'].get('dropped_count')) + ' dropped'}")
        cs = sum(1 for k in keys if (state['cases'].get(k) or {}).get('compiles'))
        vs = sum(1 for k in keys if (state['cases'].get(k) or {}).get('artefact_valid'))
        print(f"\n# compiles: {cs}/{len(keys)}   passes every lint: {vs}/{len(keys)}")
        return 0

    cfg = _get("/api/wizard/llm_config").get("llm_config") or {}
    state["llm"] = {k: cfg.get(k) for k in ("provider", "auth_method", "model")}
    print(f"# autopilot run dir: {run_dir}")
    print(f"# workspace LLM: {state['llm']}")
    _save_state(run_dir, state)

    log_path = run_dir / "autopilot.log"

    def make_log(key: str):
        def log(msg: str):
            line = f"[{time.strftime('%H:%M:%S')}] {key}: {msg}"
            print(line, flush=True)
            with open(log_path, "a") as fh:
                fh.write(line + "\n")
        return log

    for key in keys:
        rec = state["cases"].setdefault(key, {})
        log = make_log(key)
        for phase, fn, status_field in (
            ("generator", run_generator, "generator_status"),
            ("pytest", run_pytest_creator, "pytest_status"),
        ):
            if args.phase not in (phase, "all"):
                continue
            if rec.get(status_field) == "ok":
                log(f"{phase}: already ok — skip")
                continue
            log(f"--- {phase} ---")
            t0 = time.monotonic()
            try:
                if phase == "pytest":
                    fn(key, log, rec, trim_verify=args.trim_verify)
                else:
                    fn(key, log, rec)
                rec[status_field] = "ok"
                rec[f"{phase}_seconds"] = round(time.monotonic() - t0)
                log(f"{phase}: OK in {rec[f'{phase}_seconds']}s")
            except Fail as e:
                rec[status_field] = "failed"
                rec[f"{status_field}_error"] = str(e)[:1200]
                log(f"{phase}: FAILED — {str(e)[:600]}")
                _save_state(run_dir, state)
                break        # don't run pytest phase on a case with no bundle
            except Exception as e:                      # noqa: BLE001 — batch must survive
                rec[status_field] = "error"
                rec[f"{status_field}_error"] = f"{type(e).__name__}: {e}"[:1200]
                log(f"{phase}: ERROR — {type(e).__name__}: {str(e)[:400]}")
                _save_state(run_dir, state)
                break
            _save_state(run_dir, state)
        _save_state(run_dir, state)

    ok_gen = sum(1 for c in state["cases"].values() if c.get("generator_status") == "ok")
    ok_pt = sum(1 for c in state["cases"].values() if c.get("pytest_status") == "ok")
    print(f"\n# generator ok: {ok_gen}/{len(keys)}   pytest ok: {ok_pt}/{len(keys)}")
    print(f"# state: {run_dir / 'state.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

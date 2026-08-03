"""Generator export — the drop-in refined-cases bundle and push_to_zephyr.

export() gates, synthesizes coverage gaps, assembles + validates the Zephyr payload,
renders the traceability note, and writes the bundle atomically (the Complete marker —
zephyr_payload.json — committed last). push_to_zephyr shells out to upload_refined.py.
Split out of the monolithic routers/wizard.py (PLAN-backend-module-split.md commit 10).
"""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from models import (
    ExportResponse,
    SynthesisRequest,
    WizardSession,
    model_to_dict,
    safe_session_dict,
)
from html_sanitize import sanitize_objective_html
from paths import ASKCK_ROOT, REFINED_DIR
from case_registry import CASE_KEY_RE, get_refined_group, refined_payload_path
from llm import (
    _is_traceability_note,
    build_traceability_note,
    generate_coverage_gaps,
    validate_zephyr_payload,
)
from llm_config import apply_workspace_llm
from session_store import mark_updated, persist_session
from generator.gates import can_synthesize

from ._shared import OUTPUTS_ENV, get_data
# export resolves the stored session through the same authoritative helper synthesis uses.
# Relative import: internal wiring of one router, not a cross-router reach.
from .synthesis import _authoritative_session

log = logging.getLogger(__name__)
router = APIRouter()

def _export_gate(req: SynthesisRequest) -> Tuple[str, WizardSession]:
    """Resolve and authorize the case to export. Returns (case_key, authoritative session).

    Raises 400 on a bad key, 404 when no server-side session exists, 400 when the three DB
    reviews are not confirmed.
    """
    key = None
    if hasattr(req.session, "key"):
        key = req.session.key
    elif isinstance(req.session, dict):
        key = req.session.get("key")

    # SECURITY (adversarial-review finding): case_key becomes a directory component of
    # the on-disk export path, so a value like '../../etc/x' would escape refined-cases/.
    # This is a purely syntactic check on the client-supplied key, so it runs FIRST —
    # ahead of the session lookup and the confirm gate. (Ordering matters: when the
    # confirm gate ran first, a traversal key returned its 400 instead, so the
    # traversal regression test passed without ever exercising this guard.)
    if not key:
        raise HTTPException(400, "Session key is required")
    if not CASE_KEY_RE.match(key):
        raise HTTPException(400, f"Refusing to export: invalid case key '{key}'. "
                                 f"Expected AWPTCM-Txxxx.")

    # SECURITY / STATE (adversarial-review findings wizard.py:1939 + 1936):
    # export() writes the bundle that MARKS A CASE COMPLETE, so it must never build
    # that artefact from client-supplied state. Previously it fell back to
    # `req.session` when the key was absent from both the cache and ck.db — so a
    # stale browser tab could resurrect a session the server had explicitly deleted
    # (clear_session) and re-mark the case Complete. Use the same authoritative
    # resolver every sibling synthesis endpoint uses; 404 when no server session
    # exists rather than trusting the request body.
    stored = _authoritative_session(key)

    # ...and gate on the three DB reviews, matching synthesize_objectives,
    # synthesize_steps and synthesize. Without this, hand-pasting an objective + steps
    # (save_objective/save_steps have no gate either) let an unreviewed case be written
    # as Complete and become push-eligible — bypassing the exact three-review gate the
    # drafting process mandates. Backfilled cases satisfy this via
    # backfill_from_refined, which marks the reviews confirmed from the Complete on-disk
    # bundle.
    if not can_synthesize(stored):
        # A case that is Complete on disk should have been rehydrated by
        # backfill_from_refined. If it wasn't, the bundle itself is unreadable
        # (e.g. AWPTCM-T37861 ships invalid JSON — a bad \' escape), and blaming the
        # user for unconfirmed reviews would be misleading and unactionable. Name the
        # real cause instead.
        _payload = refined_payload_path(key)
        if _payload is not None:
            raise HTTPException(
                400,
                f"This case is marked Complete on disk but its bundle could not be read, "
                f"so its prior reviews could not be restored ({_payload.name}). Fix or "
                f"remove the file, or re-confirm the three database reviews manually.",
            )
        raise HTTPException(
            400,
            "Must complete and confirm reviews of all three databases "
            "(TestLink, Zephyr, ATPyLib) before exporting.",
        )
    return key, stored


async def _ensure_gaps(stored, sess_dict: dict) -> None:
    """Fill sess_dict['gaps'] via the LLM when empty, and persist it onto the session.

    Gaps belong in Traceability and are LLM-generated at objective synthesis/export, not
    collected as a Step 3 form field.
    """
    # Apply the workspace LLM at dispatch time so the coverage-gaps call uses the
    # configured backend, not the default. (`stored` is always the authoritative server
    # session now — never req.session.)
    if hasattr(stored, "llm_config") and apply_workspace_llm(stored):
        mark_updated(stored)
        persist_session(stored)
        sess_dict["llm_config"] = model_to_dict(stored.llm_config)
    llm_cfg = sess_dict.get("llm_config", {})
    if (sess_dict.get("gaps") or "").strip():
        return
    # Run the (blocking) LLM call off the event loop so the agent-bridge long-poll
    # stays serviceable for claude_agent mode. ContextVars (session id) propagate.
    #
    # This was the one LLM call site in the router that omitted the wrap, and in
    # claude_agent mode it is a guaranteed self-deadlock, not just a stall:
    # _call_claude_agent -> registry.submit() blocks on threading.Event.wait(180s),
    # and the event is only set when the browser POSTs to /api/agent/result — which
    # the blocked event loop cannot serve. The export hangs for the full 180s and
    # then reports "local Claude agent did not respond in time", blaming the user's
    # ck-agent for a deadlock the server caused.
    gaps_out = await run_in_threadpool(generate_coverage_gaps, sess_dict, llm_config=llm_cfg)
    sess_dict["gaps"] = gaps_out.get("gaps") or ""
    # Persist onto authoritative session when available
    if stored is not None and hasattr(stored, "gaps"):
        stored.gaps = sess_dict["gaps"]
        if isinstance(stored, WizardSession) or hasattr(stored, "llm_config"):
            try:
                mark_updated(stored)
                persist_session(stored)
            except Exception:
                pass


def _build_test_script(step4: dict, step5: dict, sess_dict: dict) -> dict:
    """The exported testScript: stored steps with the server-built traceability note first.

    Prefer Step 5 testScript; fall back to legacy step4.testScript. Client edits to later
    steps are respected; only the first note step is forced.
    """
    test_script = (
        (step5.get("testScript") if isinstance(step5, dict) else None)
        or (step4.get("testScript") if isinstance(step4, dict) else None)
        or {"type": "steps", "steps": []}
    )
    steps = list(test_script.get("steps", []))
    note_desc = build_traceability_note(sess_dict)
    # The first step must be the server-built traceability note. Previously this
    # UNCONDITIONALLY overwrote steps[0] — destroying a genuine first verification step
    # whenever the stored testScript didn't already begin with the note (e.g. a manually
    # edited or backfilled testScript). Only overwrite when steps[0] IS already the note
    # (regenerate it) or is blank; otherwise PREPEND the note so no real step is lost.
    if steps:
        first = steps[0] if isinstance(steps[0], dict) else {}
        first_desc = (first.get("description") or "").strip()
        if _is_traceability_note(first_desc) or not first_desc:
            steps[0] = {"description": note_desc, "expectedResult": first.get("expectedResult", "")}
        else:
            steps.insert(0, {"description": note_desc, "expectedResult": ""})
    else:
        steps = [{"description": note_desc, "expectedResult": ""}]
    return {"type": "steps", "steps": steps}


def _build_payload(case_key: str, step4: dict, step5: dict, sess_dict: dict) -> dict:
    """The exact zephyr_payload.json shape refined-cases/ + upload_refined.py expect.

    Side effect by design: derives sess_dict['art_string'] from the Step 3 selections when
    absent, because the traceability template renders it too — so this must run before
    _render_traceability, as it did inline.
    """
    test_script = _build_test_script(step4, step5, sess_dict)

    objective = (step4.get("objective") if isinstance(step4, dict) else None) or "<ul><li>Objective not yet synthesized</li></ul>"
    objective = sanitize_objective_html(objective)   # defense-in-depth on the exported artefact

    # Derive art_string for payload if not present (repeatable from selections)
    if not sess_dict.get("art_string"):
        atp_ids = [s.get("id_or_key") or s.get("id", "") for s in (sess_dict.get("step3", {}).get("selections") or []) if s]
        if atp_ids:
            sess_dict["art_string"] = " + ".join(atp_ids[:6])  # cap for cleanliness

    # Exact shape matching real refined-cases examples
    return {
        case_key: {
            "objective": objective,
            "testScript": test_script
        }
    }


def _render_traceability(case_key: str, sess_dict: dict) -> str:
    """traceability.md from the template, with a plain-text fallback that never raises."""
    # Rich context for Jinja (handles key vs id_or_key variations from UI data)
    primary = sess_dict.get("primary")
    tl_sels = sess_dict.get("step1", {}).get("selections", []) or []
    z_sels = sess_dict.get("step2", {}).get("selections", []) or []
    atp_sels = sess_dict.get("step3", {}).get("selections", []) or []
    gaps = sess_dict.get("gaps", "")
    art_string = sess_dict.get("art_string", "")

    # Normalize Zephyr for template
    norm_z = []
    for s in z_sels:
        k = s.get("key") or s.get("id_or_key", "")
        norm_z.append({
            "key": k,
            "title": s.get("title", ""),
            "folder": s.get("folder", ""),
            "justification": s.get("justification", ""),
            "id_or_key": k,
        })

    # Normalize ATP
    norm_atp = []
    for s in atp_sels:
        norm_atp.append({
            "id_or_key": s.get("id_or_key") or s.get("id", ""),
            "title": s.get("title", s.get("description", "")),
            "description": s.get("description", ""),
        })

    template_context = {
        "case_key": case_key,
        "primary": primary,
        "testlink_selections": tl_sels,
        "zephyr_selections": norm_z,
        "atp_selections": norm_atp,
        "gaps": gaps,
        "art_string": art_string,
        "folder": "",  # future: enrich from zephyr_master
    }

    # Render using the output template for repeatable md
    try:
        tmpl = OUTPUTS_ENV.get_template("traceability.md.jinja")
        return tmpl.render(**template_context)
    except Exception:
        # Traceback matters: this silently degrades the exported traceability.md to a
        # bare fallback, and the template name/line is only in the Jinja traceback.
        log.warning("[export] Jinja render failed — using plain-text fallback", exc_info=True)
        return f"# Traceability & Supporting Data for {case_key}\n\n## Primary\n{primary}\n\n## Gaps\n{gaps}\n\n## ART String\n{art_string}\n"


def _write_bundle(target_dir: Path, files: List[Tuple[str, str]]) -> List[str]:
    """Stage every file as a .tmp sibling, then os.replace them into place IN ORDER.

    PARTIAL-WRITE (adversarial-review finding wizard.py:2166): zephyr_payload.json
    is the Complete marker (refined_complete_keys keys off its existence) and it
    used to be written SECOND of three, with the largest, most failure-prone write
    (the session dump, which carries full LLM provenance) last. A disk-full or
    encoding error on that third write left the case marked Complete and
    push-eligible while the API reported wrote_bundle=False — a lying signal.

    So the caller serializes everything up front (a serialization error then fails before
    any file is touched) and passes the payload LAST, making the Complete marker the final
    commit point. Any failure unlinks the staged temp files and leaves the case
    not-Complete. THE ORDER OF `files` IS LOAD-BEARING.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_files: List[str] = []
    staged: List[tuple] = []
    try:
        for name, content in files:
            tmp = target_dir / f".{name}.tmp"
            tmp.write_text(content, encoding="utf-8")
            staged.append((tmp, target_dir / name, name))
        for tmp, final, name in staged:
            os.replace(tmp, final)
            saved_files.append(name)
    except Exception:
        for tmp, _final, _name in staged:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        raise
    return saved_files


def _blocked_export(case_key: str, traceability_md: str, zephyr_payload: dict,
                    session_out: dict, validation: dict) -> ExportResponse:
    """The response when hard validation fails: render everything, write nothing.

    HARDENING (backlog: output-generation): the drop-in bundle is exactly what marks a case
    "Complete" (refined-cases/**/zephyr_payload.json). If the payload fails hard validation,
    refuse to write it — a silently-broken bundle promoting a case to Complete is the failure
    mode this guards. Warnings do NOT block (they're advisory). The client is handed the
    validation detail so it can show WHY nothing was written.
    """
    issues = validation.get("issues") or ["unknown validation failure"]
    # Be precise about state (adversarial-review findings): the guard only prevents
    # WRITING a new/overwritten drop-in bundle — it does not remove one already on disk.
    # A case that was exported successfully before is STILL Complete (Complete is keyed
    # off refined-cases/**/zephyr_payload.json existing), and push_to_zephyr operates on
    # that on-disk bundle. So don't claim "NOT Complete" unconditionally; say what's true.
    stale_bundle_exists = refined_payload_path(case_key) is not None
    if stale_bundle_exists:
        complete_note = (
            "A previously-exported bundle is still on disk, so this case remains marked "
            "Complete and Push-to-Zephyr would use that OLDER bundle. This export did NOT "
            "overwrite it. Fix the issues and re-export to refresh it."
        )
    else:
        complete_note = "No bundle was written, so the case is NOT marked Complete."
    export_message = (
        "Export blocked — the payload did not pass validation, so no drop-in bundle was "
        "written to refined-cases/. " + complete_note + " Issues:\n  - "
        + "\n  - ".join(issues)
    )
    log.warning("[export] BLOCKED for %s (stale_bundle=%s): %s",
                case_key, stale_bundle_exists, issues)
    return ExportResponse(
        traceability_md=traceability_md,
        zephyr_payload=zephyr_payload,
        session_json=session_out,
        validation=validation,
        saved_to=None,
        saved_files=None,
        message=export_message,
        wrote_bundle=False,
    )


@router.post("/export", response_model=ExportResponse)
async def export(req: SynthesisRequest, data=Depends(get_data)):
    """Produce repeatable, templated bundle for the case.
    Uses the authoritative server-stored session ONLY (404 if absent) and requires
    all three DB reviews confirmed (400 otherwise) — client-supplied session content
    is never a write source for the bundle that marks a case Complete.
    - Builds proper first traceability note via server-side function (for repeatability).
    - Renders traceability.md.jinja with full context from selections.
    - Assembles exact zephyr_payload.json shape expected by refined-cases + upload_refined.py.
    - Also writes the main outputs (traceability.md + zephyr_payload.json) directly
      into refined-cases/<Group>/AWPTCM-Txxxx/ (creating folders if needed).
    Cross-references PROGRESS.md (High Priority: Complete output generation - "Update export to produce drop-in refined-cases artifacts")
    and SERVER-README.md (output artifacts drop-in compatible; drop into refined-cases/<Group>/...).
    """
    key, stored = _export_gate(req)

    # Normalize to dict for easy access + context building. `stored` comes from
    # _authoritative_session, so it is always a WizardSession — but this stays tolerant
    # of a plain dict because sess_dict is mutated below (llm_config, gaps) and a
    # pass-through would then write back into the live session.
    sess_dict = model_to_dict(stored)

    case_key = key or sess_dict.get("key", "unknown")
    # Defense in depth: `key` was already shape-checked in _export_gate, but case_key can
    # also come from the stored session, so re-validate whatever will actually be used as
    # the path component — before the LLM gaps call, payload validation, or any write.
    if not CASE_KEY_RE.match(case_key or ""):
        raise HTTPException(400, f"Refusing to export: invalid case key '{case_key}'. "
                                 f"Expected AWPTCM-Txxxx.")
    step4 = sess_dict.get("step4", {}) or {}
    step5 = sess_dict.get("step5", {}) or {}

    await _ensure_gaps(stored, sess_dict)

    # Order matters: _build_payload derives sess_dict['art_string'], which the
    # traceability template renders.
    zephyr_payload = _build_payload(case_key, step4, step5, sess_dict)

    # Run full validation (strengthened for complete output generation)
    validation = validate_zephyr_payload(zephyr_payload)
    if not validation.get("valid"):
        log.warning("[export] validation issues for %s: %s", case_key, validation.get("issues"))
    for w in validation.get("warnings", []):
        log.warning("[export] %s", w)

    traceability_md = _render_traceability(case_key, sess_dict)

    # Full session out for audit/provenance (repeatable). REDACTED: this is written to
    # {case_key}-session.json under refined-cases/ (and returned to the browser), so the
    # llm_config api_key/token must be masked — otherwise a credential lands on disk in a
    # directory that can be committed. The live server-side session keeps the real key.
    session_out = safe_session_dict(stored if not isinstance(stored, dict) else stored)

    if not validation.get("valid"):
        return _blocked_export(case_key, traceability_md, zephyr_payload, session_out, validation)

    # Primary destination: write drop-in artefacts under refined-cases/ (server path).
    # Browser downloads are intentional only if the client asks; default UX is server-side only.
    saved_to = None
    saved_files: List[str] = []
    export_message = ""
    wrote_bundle = False

    # SECURITY (adversarial-review finding): case_key comes from the client-supplied
    # session and is used as a directory component of the on-disk write path, so a value
    # like '../../etc/x' would escape refined-cases/. Validate it against the canonical
    # AWPTCM-Txxxx shape before ANY filesystem write. (push_to_zephyr already does this;
    # the export write path did not.)
    # (case_key was already validated against CASE_KEY_RE above.)
    # Resolve the target dir and confirm it stays inside refined-cases/ BEFORE the write
    # try-block (whose broad `except Exception` would otherwise soften a 400 into a
    # "failed to write" message). Defends against a manipulated folder-derived `group`.
    # Post-restructure (2026-07-13) refined-cases live under
    # ask-ck/objective-drafting/refined-cases/ — use the REFINED_DIR anchor from paths.py,
    # matching case_registry.get_refined_group and refined_complete_keys.
    _export_group = get_refined_group(case_key, data)
    target_dir = REFINED_DIR / _export_group / case_key
    if REFINED_DIR.resolve() not in target_dir.resolve().parents:
        raise HTTPException(400, "Refusing to export outside refined-cases/.")

    try:
        # Serialize up front so a serialization error fails before any file is touched.
        # zephyr_payload.json goes LAST — it is the Complete marker (see _write_bundle).
        saved_files = _write_bundle(target_dir, [
            ("traceability.md", traceability_md),
            (f"{case_key}-session.json", json.dumps(session_out, indent=2, default=str)),
            ("zephyr_payload.json", json.dumps(zephyr_payload, indent=2)),
        ])

        # Prefer repo-relative path for display (portable across machines).
        # ASKCK_ROOT.parent is the Test-cases repo root.
        try:
            saved_to = str(target_dir.relative_to(ASKCK_ROOT.parent))
        except ValueError:
            saved_to = str(target_dir)
        wrote_bundle = True
        export_message = f"Saved drop-in bundle to {saved_to}/"
        log.info("[export] %s", export_message)
    except Exception as e:
        export_message = f"Failed to write to refined-cases: {e}"
        # ERROR: the export the user just asked for produced no bundle. `export_message`
        # is returned to the browser, so the user is told — but the traceback (permissions,
        # missing parent, partial staged write) only exists here.
        log.error("[export] %s", export_message, exc_info=True)

    # Include validation result so callers (and future UI) know the status of repeatability guarantees
    return ExportResponse(
        traceability_md=traceability_md,
        zephyr_payload=zephyr_payload,
        session_json=session_out,
        validation=validation,
        saved_to=saved_to,
        saved_files=saved_files or None,
        message=export_message or None,
        wrote_bundle=wrote_bundle,
    )




@router.post("/push_to_zephyr/{key}")
async def push_to_zephyr(key: str, dry_run: bool = True, force: bool = False,
                         confirm: str = Body(default="", embed=True)):
    """Push a Complete refined case to Zephyr via tool/upload_refined.py.

    Shells out to the CLI (the single owner of Zephyr-write logic), which:
      1. strips a leading '(N)'/'(...)' group from the test-case Name,
      2. creates a NEW Zephyr version (e.g. 1.0 -> 2.0),
      3. uploads objective + testScript onto the new (latest) version,
      4. attaches traceability.md + web links.

    The CLI loads JIRA_KEY from secrets.md itself — the server never handles the
    token. The case must already be Exported (drop-in payload on disk under
    refined-cases/). `dry_run=true` (default) previews with no writes.

    `force=false` (default) leaves the CLI's "already appears refined in Zephyr — SKIP"
    protection in place. Pass force=true only to deliberately overwrite a case that has
    already been refined upstream.

    A real push (`dry_run=false`) additionally requires `confirm` in the body to equal
    the case key. `dry_run` is a query parameter, so a real write was previously one
    character away from a preview — and the browser-side confirm() that stood in for a
    safeguard is not executed by curl. The token has to be typed per case, so no single
    edit to a URL can turn a preview into a production write. It is not authentication;
    it is the missing step between "I meant to look" and "I meant to write".
    """
    if not CASE_KEY_RE.match(key or ""):
        raise HTTPException(status_code=400, detail="invalid case key")

    if not dry_run and (confirm or "").strip() != key:
        raise HTTPException(
            status_code=400,
            detail=(f"a real push must be confirmed: send {{\"confirm\": \"{key}\"}} in the "
                    f"request body. Use dry_run=true to preview with no writes."),
        )

    repo_root = ASKCK_ROOT.parent           # .../Test-cases
    cli = repo_root / "tool" / "upload_refined.py"
    if not cli.is_file():
        raise HTTPException(status_code=500, detail=f"upload tool not found: {cli}")

    # `--force` used to be hardcoded here, which silently disabled the CLI's own last
    # safety net (upload_refined.py:947 — "SKIP: already appears refined in Zephyr…
    # Use --force to overwrite"). The UI had no way NOT to force, so that protection was
    # dead code in practice and any push could overwrite an already-refined live case.
    # It is now opt-in per request; without it the CLI skips cases it judges already
    # refined, which is the tool's designed behaviour.
    cmd = [
        sys.executable, str(cli),
        "--keys", key,
        "--fix-title", "--new-version",
        "--verify",
        *(["--force"] if force else []),
        ("--dry-run" if dry_run else "--execute"),
    ]

    def _run():
        return subprocess.run(
            cmd, cwd=str(repo_root),
            capture_output=True, text=True, timeout=180,
        )

    try:
        proc = await run_in_threadpool(_run)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="push to Zephyr timed out (180s)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to launch push: {e}")

    # The CLI writes its human-readable log to stderr; combine for the UI.
    output = (proc.stdout or "") + (proc.stderr or "")
    return {
        "key": key,
        "dry_run": dry_run,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "output": output.strip(),
    }

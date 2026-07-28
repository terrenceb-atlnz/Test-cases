"""Generator synthesis endpoints — objectives and steps.

synthesize_objectives / save_objective / confirm_objectives / save_steps /
synthesize_steps / synthesize, resolved over the authoritative stored session. Split out
of the monolithic routers/wizard.py (PLAN-backend-module-split.md commit 10).
"""
from fastapi import APIRouter, Body, HTTPException
from starlette.concurrency import run_in_threadpool

from models import SynthesisRequest, WizardSession, model_to_dict, safe_session_dict
from timeutil import utc_now
from html_sanitize import sanitize_objective_html
from llm import (
    synthesize_objectives,
    synthesize_objectives_and_steps,
    synthesize_steps,
)
from llm_config import preview_from
from session_store import load_persisted, mark_updated, persist_session, sessions
from generator.gates import (
    can_synthesize,
    can_synthesize_steps,
    migrate_legacy_step4_to_step5,
    session_has_objective,
    session_objective,
)

# `_session_llm_cfg` lives with the review endpoints that first apply the workspace LLM;
# synthesis reuses it at dispatch time. Relative import: this is one router's internal
# wiring, not a cross-router reach (which the decoupling suite forbids).
from .reviews import _session_llm_cfg

router = APIRouter()

def _session_key_from_req(req: SynthesisRequest) -> str:
    key = None
    if hasattr(req.session, "key"):
        key = req.session.key
    elif isinstance(req.session, dict):
        key = req.session.get("key")
    if not key:
        raise HTTPException(400, "Session key is required")
    return key


def _authoritative_session(key: str) -> WizardSession:
    stored = sessions.get(key) or load_persisted(key)
    if not stored:
        raise HTTPException(404, "Session not found. Load the case and confirm all three steps first.")
    sessions[key] = stored
    if migrate_legacy_step4_to_step5(stored):
        persist_session(stored)
    return stored


@router.post("/synthesize_objectives")
async def synthesize_objectives_endpoint(req: SynthesisRequest):
    """Step 4: generate Traceability gaps + objective HTML only (no test steps).

    Gate: steps 1–3 must be confirmed. User reviews/edits objective, then confirms
    before Step 5 (synthesize_steps).
    """
    key = _session_key_from_req(req)
    stored = _authoritative_session(key)
    if not can_synthesize(stored):
        raise HTTPException(
            400,
            "Must complete and confirm reviews of all three databases (TestLink, Zephyr, ATPyLib) first.",
        )

    # Resolve config through _session_llm_cfg so the workspace LLM is applied at
    # dispatch time (guards against a stale persisted config using the wrong backend).
    llm_cfg = _session_llm_cfg(stored)
    session_dict = model_to_dict(stored)
    if getattr(req, "dry_run", False):
        preview = await run_in_threadpool(synthesize_objectives, session_dict, llm_config=llm_cfg, dry_run=True)
        return preview_from(preview)
    # Run the (blocking) LLM call off the event loop so the agent-bridge long-poll
    # stays serviceable for claude_agent mode. ContextVars (session id) propagate.
    result = await run_in_threadpool(synthesize_objectives, session_dict, llm_config=llm_cfg)

    # Store objective phase only; clear prior "confirmed" so user re-reviews after re-synth.
    # Sanitize the LLM-produced objective HTML before storage — it is rendered raw via
    # innerHTML, and the LLM builds it from corpus text the user didn't author (stored-XSS
    # defense — adversarial-review finding).
    prev4 = stored.step4 if isinstance(stored.step4, dict) else {}
    stored.step4 = {
        "objective": sanitize_objective_html(result.get("objective") or ""),
        "provenance": result.get("provenance"),
        "confirmed": False,
        "confirmed_at": None,
        # Preserve legacy testScript only if still present (prefer step5)
        **({"testScript": prev4["testScript"]} if prev4.get("testScript") and not (stored.step5 or {}).get("testScript") else {}),
    }
    if result.get("gaps"):
        stored.gaps = result["gaps"]

    if not stored.full_session:
        stored.full_session = {}
    stored.full_session["llm_objectives"] = result.get("provenance") or {}
    # Keep merged audit trail
    prev_llm = stored.full_session.get("llm") or {}
    stored.full_session["llm"] = {**prev_llm, **(result.get("provenance") or {})}

    mark_updated(stored)
    persist_session(stored)
    return {
        "phase": "objectives",
        "synthesized": result,
        "can_synthesize_steps": can_synthesize_steps(stored),
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/save_objective/{key}")
async def save_objective(key: str, body: dict = Body(default={})):
    """Persist edited objective HTML from Step 4 (before or as part of confirm)."""
    body = body or {}
    stored = sessions.get(key) or load_persisted(key)
    if not stored:
        raise HTTPException(404, "Session not found.")
    sessions[key] = stored
    objective = (body.get("objective") or "").strip()
    if not objective:
        raise HTTPException(400, "objective HTML is required")
    # Sanitize before storage: the objective is rendered raw via innerHTML, so strip any
    # non-allowlisted tags/attributes (stored-XSS defense — adversarial-review finding).
    objective = sanitize_objective_html(objective)
    s4 = dict(stored.step4 or {})
    s4["objective"] = objective
    # A deliberate edit re-authors the objective against the current selections, so it
    # clears any staleness flagged by invalidate_downstream after an upstream change.
    s4.pop("stale", None)
    # Edits invalidate prior confirm until re-confirmed
    if body.get("confirm"):
        s4["confirmed"] = True
        s4["confirmed_at"] = utc_now().isoformat()
    else:
        # Keep prior confirmed only if body explicitly keeps it; default re-open review
        if "confirm" in body and not body.get("confirm"):
            s4["confirmed"] = False
            s4["confirmed_at"] = None
    stored.step4 = s4
    mark_updated(stored)
    persist_session(stored)
    return {
        "message": "Objective saved" + (" and confirmed" if s4.get("confirmed") else ""),
        "can_synthesize_steps": can_synthesize_steps(stored),
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/confirm_objectives/{key}")
async def confirm_objectives(key: str, body: dict = Body(default={})):
    """Mark Step 4 objective as finalized (optional body.objective overwrites)."""
    body = body or {}
    stored = sessions.get(key) or load_persisted(key)
    if not stored:
        raise HTTPException(404, "Session not found.")
    sessions[key] = stored
    s4 = dict(stored.step4 or {})
    if body.get("objective"):
        s4["objective"] = sanitize_objective_html((body.get("objective") or "").strip())
    if not (s4.get("objective") or "").strip():
        raise HTTPException(400, "No objective to confirm. Run Objective Synthesis first.")
    s4["confirmed"] = True
    s4["confirmed_at"] = utc_now().isoformat()
    # An explicit re-confirm is the user asserting this objective matches the CURRENT
    # selections, so it clears any staleness flagged by invalidate_downstream.
    s4.pop("stale", None)
    stored.step4 = s4
    mark_updated(stored)
    persist_session(stored)
    return {
        "message": "Objectives confirmed — proceed to Step 5 (Test Step Synthesis).",
        "can_synthesize_steps": True,
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/save_steps/{key}")
async def save_steps(key: str, body: dict = Body(default={})):
    """Persist edited testScript steps from Step 5 editor."""
    body = body or {}
    stored = sessions.get(key) or load_persisted(key)
    if not stored:
        raise HTTPException(404, "Session not found.")
    sessions[key] = stored
    ts = body.get("testScript") or {}
    steps = ts.get("steps") if isinstance(ts, dict) else None
    if steps is None and isinstance(body.get("steps"), list):
        steps = body.get("steps")
    if not isinstance(steps, list):
        raise HTTPException(400, "testScript.steps array is required")
    test_script = {"type": "steps", "steps": steps}
    s5 = dict(stored.step5 or {})
    s5["testScript"] = test_script
    # Deliberate edit against the current selections — clears invalidate_downstream's flag.
    s5.pop("stale", None)
    stored.step5 = s5
    # Mirror onto step4 for legacy consumers / combined view
    s4 = dict(stored.step4 or {})
    s4["testScript"] = test_script
    stored.step4 = s4
    mark_updated(stored)
    persist_session(stored)
    return {
        "message": "Steps saved",
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/synthesize_steps")
async def synthesize_steps_endpoint(req: SynthesisRequest):
    """Step 5: generate verification steps from finalized Step 4 objective.

    Gate: steps 1–3 confirmed and an objective present on the session.
    Uses the server-stored objective (after user edit/confirm), not a stale client draft.
    """
    key = _session_key_from_req(req)
    stored = _authoritative_session(key)
    if not can_synthesize(stored):
        raise HTTPException(
            400,
            "Must complete and confirm reviews of all three databases first.",
        )
    if not session_has_objective(stored):
        raise HTTPException(
            400,
            "No objective on session. Complete Step 4 (Objective Synthesis) first.",
        )

    # If client sent a newer objective (edited but not yet saved), accept and persist
    client_obj = ""
    if hasattr(req.session, "step4") and isinstance(req.session.step4, dict):
        client_obj = (req.session.step4.get("objective") or "").strip()
    elif isinstance(req.session, dict):
        client_obj = ((req.session.get("step4") or {}).get("objective") or "").strip()
    if client_obj and client_obj != session_objective(stored):
        s4 = dict(stored.step4 or {})
        s4["objective"] = sanitize_objective_html(client_obj)
        stored.step4 = s4

    llm_cfg = _session_llm_cfg(stored)  # applies workspace LLM at dispatch time
    session_dict = model_to_dict(stored)
    if getattr(req, "dry_run", False):
        preview = await run_in_threadpool(
            synthesize_steps, session_dict, llm_config=llm_cfg,
            objective=session_objective(stored), dry_run=True)
        return preview_from(preview)
    try:
        result = await run_in_threadpool(
            synthesize_steps,
            session_dict,
            llm_config=llm_cfg,
            objective=session_objective(stored),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    stored.step5 = {
        "testScript": result.get("testScript"),
        "provenance": result.get("provenance"),
    }
    # Keep a combined view on step4 for older clients (objective + steps mirror)
    s4 = dict(stored.step4 or {})
    s4["objective"] = sanitize_objective_html(result.get("objective") or "") or s4.get("objective")
    s4["testScript"] = result.get("testScript")
    # Freshly synthesized against the current selections — drop any stale marker.
    s4.pop("stale", None)
    stored.step4 = s4

    if not stored.full_session:
        stored.full_session = {}
    stored.full_session["llm_steps"] = result.get("provenance") or {}
    prev_llm = stored.full_session.get("llm") or {}
    stored.full_session["llm"] = {**prev_llm, **(result.get("provenance") or {})}

    mark_updated(stored)
    persist_session(stored)
    return {
        "phase": "steps",
        "synthesized": result,
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/synthesize")
async def synthesize(req: SynthesisRequest):
    """Legacy combined synthesis (objectives + steps). Prefer split endpoints.

    Still gated on steps 1–3. Stores results in both step4 and step5 for the new UI.
    """
    key = _session_key_from_req(req)
    stored = _authoritative_session(key)
    if not can_synthesize(stored):
        raise HTTPException(
            400,
            "Must complete and confirm reviews of all three databases (TestLink, Zephyr, ATPyLib) first. This gate is enforced server-side per the repeatable process.",
        )

    llm_cfg = _session_llm_cfg(stored)  # applies workspace LLM at dispatch time
    session_dict = model_to_dict(stored)
    result = await run_in_threadpool(synthesize_objectives_and_steps, session_dict, llm_config=llm_cfg)

    stored.step4 = {
        "objective": result.get("objective"),
        "testScript": result.get("testScript"),
        "provenance": result.get("provenance"),
        "confirmed": True,
        "confirmed_at": utc_now().isoformat(),
    }
    stored.step5 = {
        "testScript": result.get("testScript"),
        "provenance": result.get("provenance"),
    }
    if result.get("gaps"):
        stored.gaps = result["gaps"]

    if "provenance" in result:
        if not stored.full_session:
            stored.full_session = {}
        stored.full_session["llm"] = result["provenance"]
    mark_updated(stored)
    persist_session(stored)

    return {
        "phase": "combined",
        "synthesized": result,
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }

# --- export: gate, build, render, write -------------------------------------
# export() was one 351-line handler doing gating, an LLM round-trip, payload assembly,
# validation, Jinja templating and staged atomic writes. Split into named steps
# (PLAN-backend-module-split.md commit 11) so each is reviewable and the pure ones are
# unit-testable — _build_test_script in particular carries a subtle fix that had no direct
# test, and _write_bundle carries the ordering that decides whether a case is Complete.
# Pure motion: every step's body is verbatim from the handler.



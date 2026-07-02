"""
Wizard API router - enforces repeatable step-by-step process.

Per PROGRESS.md (High Priority #1) and SERVER-README.md:
- Backend state machine enforces explicit user confirmation of
  TestLink (step 1), Zephyr (step 2), and ATPyLib (step 3) BEFORE synthesis.
- Process gates must be *real* and server-side.
- Added simple file-based session persistence (under drafting_server/sessions/)
  so confirmed state + selections survive restarts.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Optional, List, Any
from datetime import datetime
from pathlib import Path
import json

from models import WizardSession, SynthesisRequest, ExportResponse, Selection, LLMConfig
from data import load_all_data
from llm import synthesize_objectives_and_steps, suggest_relevant_atp, build_traceability_note
from jinja2 import Environment, FileSystemLoader

router = APIRouter()

# In-memory sessions (replace with DB later). File persistence added for restart survival.
sessions: Dict[str, WizardSession] = {}

# Simple file persistence directory (self-contained under drafting-tool/drafting_server/)
# wizard.py lives in routers/ so go up one more level
BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Output templates for repeatable exports (traceability.md etc.)
OUTPUTS_DIR = BASE_DIR / "templates" / "outputs"
OUTPUTS_ENV = Environment(loader=FileSystemLoader(str(OUTPUTS_DIR)))


def _session_path(key: str) -> Path:
    return SESSIONS_DIR / f"{key}.json"


def _persist_session(sess: WizardSession) -> None:
    """Persist full session (confirmed flags + selections + step4) to disk.
    This fulfills the 'Persist confirmation state per session' requirement.
    """
    sess.updated_at = datetime.utcnow()
    path = _session_path(sess.key)
    try:
        data = sess.dict() if hasattr(sess, "dict") else sess.model_dump()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: failed to persist session {sess.key}: {e}")


def _load_persisted(key: str) -> Optional[WizardSession]:
    """Restore persisted session (used for restart survival and authoritative state)."""
    path = _session_path(key)
    if path.exists():
        try:
            raw = json.load(open(path, encoding="utf-8"))
            return WizardSession(**raw)
        except Exception as e:
            print(f"Warning: failed to load persisted session {key}: {e}")
    return None


def _mark_updated(sess: WizardSession) -> None:
    sess.updated_at = datetime.utcnow()


def _can_synthesize(sess: WizardSession) -> bool:
    """Central repeatable-process gate. Must confirm all three reviews first.
    Enforced in synthesize and returned to clients.
    """
    return bool(sess.step1.confirmed and sess.step2.confirmed and sess.step3.confirmed)


def get_data():
    # Would be from app.state in a fuller implementation
    return load_all_data()

@router.post("/load_case/{key}")
async def load_case(key: str, data=Depends(get_data)):
    """Load or restore a case. Enriches response with real TestLink candidates + Zephyr refs
    so that the UI tables can be populated for a full runnable demo.
    """
    # Check in-memory or disk first
    sess = sessions.get(key) or _load_persisted(key)
    if sess:
        sessions[key] = sess
    else:
        if key not in data.get("zephyr_master", {}):
            raise HTTPException(404, "Case not found")
        sess = WizardSession(key=key)
        # Populate primary decision (cross-ref from data/decisions)
        primary = data.get("decisions", {}).get(key)
        if primary:
            sess.primary = {"m": primary.get("m"), "c": primary.get("c"), "w": primary.get("w")}
        sessions[key] = sess

    _persist_session(sess)

    # Real data for UI tables (demo)
    cdata = data.get("candidates_dict", {}).get(key)
    tl_cands = (cdata or {}).get("candidates", [])[:8] if cdata else []

    zrefs = []
    zm = data.get("zephyr_master", {})
    if key in zm:
        z = zm[key]
        zrefs.append({
            "key": key,
            "title": z.get("title", ""),
            "folder": z.get("folder", ""),
            "justification": "The case being refined"
        })
    # Add a few related from slim_index (simple demo filter)
    for z in data.get("slim_index", []):
        if len(zrefs) >= 5:
            break
        f = z.get("folder", "") or ""
        t = z.get("title", "") or ""
        if "Port" in f or "MDI" in t or "Auto" in t:
            zrefs.append({
                "key": z["key"],
                "title": t[:80],
                "folder": f,
                "justification": "Related Zephyr case (same area/keywords)"
            })

    return {
        "session": sess.dict() if hasattr(sess, "dict") else sess.model_dump(),
        "testlink_candidates": tl_cands,
        "zephyr_refs": zrefs,
        "message": "Case loaded (or restored from persistence). Confirm each of the three database reviews explicitly before synthesis is allowed."
    }


@router.get("/cases")
async def get_cases(data=Depends(get_data)):
    """Return a short list of cases that have candidate data for the demo selector."""
    cands = data.get("candidates", []) or []
    keys = [c["key"] for c in cands if c.get("candidates")][:100]
    # Prioritize the demo auto-negotiation case at the top
    if "AWPTCM-T33234" in keys:
        keys = ["AWPTCM-T33234"] + [k for k in keys if k != "AWPTCM-T33234"]
    return {"cases": keys}


@router.get("/search_atp")
async def search_atp(q: str = "", data=Depends(get_data)):
    """Simple ATPyLib search for Step 3 (demo)."""
    descs = data.get("test_id_desc", {}) or {}
    qlow = (q or "").lower().strip()
    results = []
    for tid, info in list(descs.items())[:2000]:
        text = (tid + " " + (info.get("description") or "") + " " + (info.get("suite_name") or "")).lower()
        if qlow and qlow not in text:
            continue
        results.append({
            "id": tid,
            "title": (info.get("description") or tid)[:90],
            "suite": info.get("suite_name", "")
        })
        if len(results) > 15:
            break
    return {"results": results}


def _build_atp_query(sess: WizardSession) -> str:
    """Build a keyword search query from case + previous selections for ATP retrieval."""
    parts = [sess.key or ""]
    if sess.primary:
        parts.append(str(sess.primary.get("w", "")))
        parts.append(str(sess.primary.get("m", "")))
    for sel in (sess.step1.selections or []):
        parts.append(sel.title or "")
    for sel in (sess.step2.selections or []):
        parts.append(sel.title or "")
    return " ".join(parts)


def _get_atp_candidates(q: str, data: dict, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve candidate ATP tests using simple keyword search (same logic as search_atp)."""
    descs = data.get("test_id_desc", {}) or {}
    qlow = (q or "").lower().strip()
    results = []
    for tid, info in list(descs.items())[:3000]:
        text = (tid + " " + (info.get("description") or "") + " " + (info.get("suite_name") or "")).lower()
        if qlow and qlow not in text:
            continue
        results.append({
            "id": tid,
            "description": (info.get("description") or tid)[:200],
            "suite": info.get("suite_name", "")
        })
        if len(results) >= limit:
            break
    return results


@router.post("/suggest_atp/{key}")
async def suggest_atp(key: str, body: dict = Body(default={}), data=Depends(get_data)):
    """Use LLM to analyze current session selections and pre-select relevant ATPyLib tests.
    Returns suggestions for the user to review/approve in Step 3.
    """
    body = body or {}
    sess = sessions.get(key) or _load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Load the case first.")

    # Build smart query and retrieve candidates
    q = body.get("q") or _build_atp_query(sess)
    candidates = _get_atp_candidates(q, data, limit=25)

    # Call LLM for selection (respects session llm_config)
    llm_cfg = {}
    if hasattr(sess, "llm_config"):
        llm_cfg = sess.llm_config.dict() if hasattr(sess.llm_config, "dict") else sess.llm_config
    suggestions = suggest_relevant_atp(
        sess.dict() if hasattr(sess, "dict") else sess.model_dump(),
        candidates,
        llm_config=llm_cfg
    )

    # Return in a form easy for frontend to apply (pre-check)
    return {
        "query_used": q,
        "num_candidates_considered": len(candidates),
        "suggestions": suggestions  # list of {id, reason}
    }


@router.post("/confirm_step/{key}/{step}")
async def confirm_step(key: str, step: int, body: dict, data=Depends(get_data)):
    """Store user selections + set the confirmed flag for the step.
    This is the explicit confirmation action required by the repeatable process
    (see OBJECTIVE_DRAFTING_PROCESS.md Step 1 user-review pause + SERVER-README).
    Selections are captured server-side for use in templated LLM prompts.
    """
    sess = sessions.get(key) or _load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Call load_case first.")
    sessions[key] = sess

    if step == 1:
        # TestLink + Decisions — the most important gate
        if "selections" in body:
            try:
                sess.step1.selections = [Selection(**s) for s in body["selections"]]
            except Exception:
                pass
        sess.step1.none_selected = bool(body.get("none", False))
        sess.step1.confirmed = True
        sess.step1.confirmed_at = datetime.utcnow()
    elif step == 2:
        if "selections" in body:
            try:
                sess.step2.selections = [Selection(**s) for s in body["selections"]]
            except Exception:
                pass
        sess.step2.confirmed = True
        sess.step2.confirmed_at = datetime.utcnow()
    elif step == 3:
        if "selections" in body:
            try:
                sess.step3.selections = [Selection(**s) for s in body["selections"]]
            except Exception:
                pass
        sess.step3.confirmed = True
        sess.step3.confirmed_at = datetime.utcnow()
        sess.gaps = body.get("gaps", "")
        if "art_string" in body:
            sess.art_string = body.get("art_string", "")
    else:
        raise HTTPException(400, "Invalid step")

    _mark_updated(sess)
    _persist_session(sess)

    return {
        "session": sess.dict() if hasattr(sess, "dict") else sess.model_dump(),
        "can_synthesize": _can_synthesize(sess)
    }


@router.post("/set_llm_config/{key}")
async def set_llm_config(key: str, body: dict):
    """Login-like endpoint. Sets per-session LLM provider and key (Grok or Claude).
    Similar to VS Code extension login flows: key is stored server-side for the session
    and used for synthesis instead of (or overriding) environment variables.
    Never returns the raw key to the client.
    """
    sess = sessions.get(key) or _load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Load a case first.")

    provider = (body.get("provider") or "mock").lower().strip()
    auth_method = (body.get("auth_method") or "api_key").lower().strip()
    api_key = body.get("api_key")
    token = body.get("token")
    base_url = body.get("base_url")
    model = body.get("model")

    if provider not in ("grok", "claude", "openai", "mock"):
        provider = "mock"
    if auth_method not in ("api_key", "account"):
        auth_method = "api_key"

    # Apply to session (credentials stay on server)
    sess.llm_config.provider = provider
    sess.llm_config.auth_method = auth_method
    if api_key:
        sess.llm_config.api_key = api_key
    if token:
        sess.llm_config.token = token
    if base_url:
        sess.llm_config.base_url = base_url

    if model:
        sess.llm_config.model = model
    else:
        # Sensible defaults per provider
        if provider == "grok":
            sess.llm_config.model = "grok-beta"
        elif provider == "claude":
            sess.llm_config.model = "claude-3-5-sonnet-20241022"

    _mark_updated(sess)
    _persist_session(sess)

    # Return safe view (no credentials)
    safe_config = {
        "provider": sess.llm_config.provider,
        "auth_method": sess.llm_config.auth_method,
        "has_key": bool(sess.llm_config.api_key or sess.llm_config.token),
        "model": sess.llm_config.model,
        "base_url": sess.llm_config.base_url,
    }

    return {
        "message": f"LLM config set for {provider}.",
        "llm_config": safe_config,
        "session": sess.dict() if hasattr(sess, "dict") else sess.model_dump()
    }

@router.post("/synthesize")
async def synthesize(req: SynthesisRequest):
    """Synthesis only succeeds when the server-side gate passes.
    Uses the authoritative persisted/in-memory session state (not just client copy).
    This directly implements 'Prevent synthesis until steps 1-3 are explicitly confirmed'.
    """
    key = None
    if hasattr(req.session, "key"):
        key = req.session.key
    elif isinstance(req.session, dict):
        key = req.session.get("key")

    if not key:
        raise HTTPException(400, "Session key is required")

    # Authoritative server state (restored from disk if necessary)
    stored = sessions.get(key) or _load_persisted(key)
    if not stored:
        raise HTTPException(404, "Session not found. Load the case and confirm all three steps first.")

    if not _can_synthesize(stored):
        raise HTTPException(400, "Must complete and confirm reviews of all three databases (TestLink, Zephyr, ATPyLib) first. This gate is enforced server-side per the repeatable process.")

    # Convert for llm.py (expects dict with step1.selections etc.)
    session_dict = stored.dict() if hasattr(stored, "dict") else stored.model_dump()

    # Pass session's llm_config (from "login") so it can override env/MOCK
    llm_cfg = session_dict.get("llm_config", {}) if isinstance(session_dict, dict) else {}
    result = synthesize_objectives_and_steps(session_dict, llm_config=llm_cfg)

    stored.step4 = result
    # Capture full LLM provenance (exact prompts + responses) into session for audit/repeatability
    if "provenance" in result:
        if not stored.full_session:
            stored.full_session = {}
        stored.full_session["llm"] = result["provenance"]
    _mark_updated(stored)
    _persist_session(stored)

    return {
        "synthesized": result,
        "session": stored.dict() if hasattr(stored, "dict") else stored.model_dump()
    }

@router.post("/export", response_model=ExportResponse)
async def export(req: SynthesisRequest):
    """Produce repeatable, templated bundle for the case.
    Uses authoritative server-stored session (after all confirms).
    - Builds proper first traceability note via server-side function (for repeatability).
    - Renders traceability.md.jinja with full context from selections.
    - Assembles exact zephyr_payload.json shape expected by refined-cases + upload_refined.py.
    Cross-references PROGRESS.md (High Priority: Complete output generation) and SERVER-README (LLM templating + output templates section).
    """
    key = None
    if hasattr(req.session, "key"):
        key = req.session.key
    elif isinstance(req.session, dict):
        key = req.session.get("key")

    stored = sessions.get(key) if key else None
    if stored is None:
        stored = _load_persisted(key) if key else None
    if stored is None:
        stored = req.session

    # Normalize to dict for easy access + context building
    if hasattr(stored, "dict"):
        sess_dict = stored.dict()
    elif isinstance(stored, dict):
        sess_dict = stored
    else:
        sess_dict = getattr(stored, "model_dump", lambda: {})()

    case_key = key or sess_dict.get("key", "unknown")
    step4 = sess_dict.get("step4", {}) or {}

    # Rebuild the testScript with server-constructed repeatable note as first step
    test_script = step4.get("testScript", {"type": "steps", "steps": []}) or {"type": "steps", "steps": []}
    steps = list(test_script.get("steps", []))
    note_desc = build_traceability_note(sess_dict)
    if steps:
        steps[0]["description"] = note_desc
        steps[0]["expectedResult"] = steps[0].get("expectedResult", "")
    else:
        steps = [{"description": note_desc, "expectedResult": ""}]
    test_script["steps"] = steps

    objective = step4.get("objective") or "<ul><li>Objective not yet synthesized</li></ul>"

    # Basic validation for repeatable output quality (per backlog)
    if not objective.strip().startswith("<ul>") or "<li>" not in objective:
        print("[export] Warning: objective does not look like valid <ul> list")
    first_step_desc = (test_script.get("steps") or [{}])[0].get("description", "")
    if "Note:" not in first_step_desc or "Traceability" not in first_step_desc:
        print("[export] Warning: first test step missing required traceability Note")

    # Exact shape matching real refined-cases examples
    zephyr_payload = {
        case_key: {
            "objective": objective,
            "testScript": test_script
        }
    }

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
        traceability_md = tmpl.render(**template_context)
    except Exception as e:
        print(f"[export] Jinja render error, fallback: {e}")
        traceability_md = f"# Traceability & Supporting Data for {case_key}\n\n## Primary\n{primary}\n\n## Gaps\n{gaps}\n\n## ART String\n{art_string}\n"

    # Full session out for audit/provenance (repeatable)
    if hasattr(stored, "dict"):
        session_out = stored.dict()
    elif isinstance(stored, dict):
        session_out = stored
    else:
        session_out = getattr(stored, "model_dump", lambda: stored)()

    return ExportResponse(
        traceability_md=traceability_md,
        zephyr_payload=zephyr_payload,
        session_json=session_out
    )
"""
Wizard API router - enforces repeatable step-by-step process.

Per PROGRESS.md (High Priority #1) and SERVER-README.md:
- Backend state machine enforces explicit user confirmation of
  TestLink (step 1), Zephyr (step 2), and ATPyLib (step 3) BEFORE synthesis.
- Process gates must be *real* and server-side.
- Added simple file-based session persistence (under drafting_server/sessions/)
  so confirmed state + selections survive restarts.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from starlette.concurrency import run_in_threadpool
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
from pathlib import Path
import json
import os
import re
import sys
import subprocess

from models import WizardSession, SynthesisRequest, ExportResponse, Selection, LLMConfig, safe_session_dict, redact_llm_config
from html_sanitize import sanitize_objective_html
import db
from llm import (
    synthesize_objectives_and_steps,
    synthesize_objectives,
    synthesize_steps,
    suggest_relevant_atp,
    suggest_relevant_testlink,
    suggest_relevant_zephyr,
    build_traceability_note,
    _is_traceability_note,
    validate_zephyr_payload,
    analyze_atp_coverage,
    generate_coverage_gaps,
    check_claude_cli,
    check_grok_cli,
    _health_ping,
)
from local_llm_key import get_local_llm_key, set_local_llm_key
from jinja2 import Environment, FileSystemLoader
from paths import REFINED_DIR, ASKCK_ROOT

router = APIRouter()

# In-memory sessions (replace with DB later). File persistence added for restart survival.
sessions: Dict[str, WizardSession] = {}

# Cases hidden from the Generator (and PyTest Creator) case lists — out of scope for
# this tool. This is a DISPLAY filter only: the data stays untouched in ck.db (the
# permanent source of truth), it just isn't offered for review. Remove an entry here
# to surface a case/folder again.
#   T44453  — "ART Limits Test"  (New Platform Template/ART Limits Test)
#   T41263-6 — 1335_pbr / 1336_acl / 1344_qos / 5000_mdi_mdix (ART Testsuites folder)
HIDDEN_CASE_KEYS = frozenset({
    "AWPTCM-T44453",
    "AWPTCM-T41263", "AWPTCM-T41264", "AWPTCM-T41265", "AWPTCM-T41266",
})

# Whole categories (Zephyr folders) hidden from the case lists — out of scope. Matched
# by exact folder path, so every case in the folder is hidden regardless of its (non-
# contiguous) test-id, and any future case added to the folder is hidden too.
#   Bootloader (17) + GRUB Bootloader (8) = 25 cases
HIDDEN_CASE_FOLDERS = frozenset({
    "/New Platform Test (MASTER)/Bootloader",
    "/New Platform Test (MASTER)/GRUB Bootloader",
})


def _is_hidden_case(key: str, folder: str = "") -> bool:
    """A case is hidden from the lists if its key is explicitly hidden OR it lives in a
    hidden folder. Display-only; ck.db is untouched."""
    if key in HIDDEN_CASE_KEYS:
        return True
    f = (folder or "").rstrip("/")
    return f in HIDDEN_CASE_FOLDERS

# wizard.py lives in routers/ so go up one more level to the CK_server package root.
BASE_DIR = Path(__file__).resolve().parent.parent
# NOTE: sessions (per-case + the '_workspace_llm' workspace default) live in ck.db
# via db.save_session/load_session — there is no runtime sessions/*.json read/write.
# The sessions/*.json files on disk are frozen pre-migration backups only.

# Output templates for repeatable exports (traceability.md etc.)
OUTPUTS_DIR = BASE_DIR / "templates" / "outputs"
OUTPUTS_ENV = Environment(loader=FileSystemLoader(str(OUTPUTS_DIR)))


def _llm_is_active(cfg: Optional[LLMConfig]) -> bool:
    """True when the config can actually drive synthesis (CLI mode or stored key)."""
    if not cfg:
        return False
    am = (getattr(cfg, "auth_method", None) or "").lower()
    if am in ("claude_code", "claude_agent", "grok_cli"):
        return True
    if am == "local_llm":
        # Key lives server-side (secrets.local.json / env), never on the config.
        return bool(get_local_llm_key())
    if getattr(cfg, "api_key", None) or getattr(cfg, "token", None):
        return True
    return False


def _same_backend(a: Optional[LLMConfig], b: Optional[LLMConfig]) -> bool:
    """True when two configs would hit the SAME LLM backend — compares the
    dispatch-selecting fields (auth_method / provider / model) only, ignoring
    credentials. Used to decide whether a case session's config still matches the
    workspace default or is a stale leftover from a previous default."""
    if not a or not b:
        return False
    f = lambda c, k: (getattr(c, k, None) or "").lower()
    return all(f(a, k) == f(b, k) for k in ("auth_method", "provider", "model"))


def _load_global_llm() -> Optional[LLMConfig]:
    """Load last-applied workspace LLM config (shared across all cases). Commit C:
    from the sessions table (id='_workspace_llm')."""
    try:
        raw = db.load_workspace_llm()
        if not raw:
            return None
        cfg = LLMConfig(**raw)
        return cfg if _llm_is_active(cfg) else None
    except Exception as e:
        print(f"Warning: failed to load workspace LLM config: {e}")
        return None


def _save_global_llm(cfg: LLMConfig) -> None:
    """Persist workspace LLM preference when the user applies a login/config."""
    if not cfg or not _llm_is_active(cfg):
        return
    try:
        data = cfg.dict() if hasattr(cfg, "dict") else cfg.model_dump()
        db.save_workspace_llm(data)
    except Exception as e:
        print(f"Warning: failed to save workspace LLM config: {e}")


def _apply_workspace_llm_if_needed(sess: WizardSession) -> bool:
    """Re-sync this case session's LLM config to the active workspace default.

    Returns True if the session was updated (caller should persist).

    The active workspace default is the single source of truth: `set_llm_config`
    always writes a case's config === the workspace default (there is no code path
    that gives a case a config that legitimately differs), so any divergence is a
    STALE leftover from a previous default, not an intentional per-case override.
    We therefore re-sync whenever the case has no active config OR its config no
    longer matches the workspace default's backend. This fixes the bug where a
    session whose stale config was a headless CLI mode (claude_agent/claude_code/
    grok_cli — which `_llm_is_active` reports active unconditionally, since there
    is no server-side key to check) could NEVER re-sync and kept silently hitting
    the wrong backend. `_llm_is_active` is intentionally left unchanged (it is also
    used for status/`has_key` reporting, where headless=active is correct).

    When there is no active workspace default we leave the session untouched, so
    "the workspace login persists across cases" still holds.
    """
    global_cfg = _load_global_llm()
    if not global_cfg:
        return False
    cur = getattr(sess, "llm_config", None)
    if _llm_is_active(cur) and _same_backend(cur, global_cfg):
        return False
    # Fresh copy so case sessions do not share the same object instance
    raw = global_cfg.dict() if hasattr(global_cfg, "dict") else global_cfg.model_dump()
    sess.llm_config = LLMConfig(**raw)
    return True


def _persist_session(sess: WizardSession) -> None:
    """Persist full session (confirmed flags + selections + step4/5) to ck.db
    (Commit C). llm_config is split into its own column by db.save_session. The
    old sessions/{key}.json file stays in place as a frozen pre-migration backup."""
    sess.updated_at = datetime.utcnow()
    try:
        data = sess.dict() if hasattr(sess, "dict") else sess.model_dump()
        db.save_session("wizard", sess.key, data)
    except Exception as e:
        print(f"Warning: failed to persist session {sess.key}: {e}")


def _load_persisted(key: str) -> Optional[WizardSession]:
    """Restore persisted session from ck.db (restart survival / authoritative state)."""
    try:
        raw = db.load_session("wizard", key)
        if raw is not None:
            return WizardSession(**raw)
    except Exception as e:
        print(f"Warning: failed to load persisted session {key}: {e}")
    return None


def _clear_persisted(key: str) -> None:
    """Delete the persisted session row for a key."""
    try:
        db.delete_session("wizard", key)
        print(f"Cleared persisted session for {key}")
    except Exception as e:
        print(f"Warning: failed to delete session for {key}: {e}")


def _get_full_zephyr_case(key: str) -> dict:
    """On-demand lookup of one full Zephyr case from ck.db. Prefer _get_full_zephyr_cases_batch."""
    found = _get_full_zephyr_cases_batch([key])
    return found.get(key) or {}


def _get_full_zephyr_cases_batch(keys: List[str]) -> Dict[str, dict]:
    """Batch lookup of full Zephyr cases by key. Commit B: indexed SQLite read
    (db.get_zephyr_cases_batch) — replaces the per-request zephyr_cases.jsonl
    linear scan that this used to do."""
    return db.get_zephyr_cases_batch([k for k in keys if k])


def _mark_updated(sess: WizardSession) -> None:
    sess.updated_at = datetime.utcnow()


def _can_synthesize(sess: WizardSession) -> bool:
    """Gate for objective synthesis (Step 4). Must confirm all three DB reviews first."""
    return bool(sess.step1.confirmed and sess.step2.confirmed and sess.step3.confirmed)


def _session_objective(sess: WizardSession) -> str:
    """Finalized objective HTML from Step 4 (or legacy combined step4)."""
    s4 = sess.step4 or {}
    if isinstance(s4, dict):
        return (s4.get("objective") or "").strip()
    return ""


def _session_has_objective(sess: WizardSession) -> bool:
    return bool(_session_objective(sess))


def _session_objectives_confirmed(sess: WizardSession) -> bool:
    s4 = sess.step4 or {}
    if not isinstance(s4, dict):
        return False
    return bool(s4.get("confirmed")) and _session_has_objective(sess)


def _session_test_script(sess: WizardSession) -> Dict[str, Any]:
    """testScript from Step 5, with legacy fallback to step4.testScript."""
    s5 = sess.step5 or {}
    if isinstance(s5, dict) and s5.get("testScript"):
        return s5.get("testScript") or {"type": "steps", "steps": []}
    s4 = sess.step4 or {}
    if isinstance(s4, dict) and s4.get("testScript"):
        return s4.get("testScript") or {"type": "steps", "steps": []}
    return {"type": "steps", "steps": []}


def _can_synthesize_steps(sess: WizardSession) -> bool:
    """Gate for Step 5: reviews confirmed + finalized objective present.

    Prefer objectives marked confirmed (user applied Step 4); allow unconfirmed
    objective if present so re-runs after synthesize_objectives still work when
    the user proceeds without an extra click (UI still prompts to confirm).
    """
    if not _can_synthesize(sess):
        return False
    return _session_has_objective(sess)


def _selection_fingerprint(sess: WizardSession, step: int) -> tuple:
    """Order-insensitive identity of one step's confirmed selections.

    Used to distinguish a real change (different cases picked) from a harmless
    re-confirm of the same shortlist, so re-clicking Confirm never throws away a
    good objective. Compares the chosen ids plus the none_selected flag; display
    order and justification text are not part of the identity.
    """
    state = getattr(sess, f"step{step}", None)
    if state is None:
        return ()
    ids = sorted((s.id_or_key or "") for s in (state.selections or []))
    return (tuple(ids), bool(state.none_selected))


def _invalidate_downstream(sess: WizardSession, changed: bool) -> dict:
    """Un-confirm the objective and mark the test steps stale after an upstream change.

    Only fires when the selections actually changed. The generated content is kept
    (the user may want to edit rather than regenerate it) — what is cleared is the
    claim that it has been reviewed against the CURRENT selections.
    """
    result = {"step4": False, "step5": False}
    if not changed:
        return result

    s4 = sess.step4 if isinstance(sess.step4, dict) else {}
    if s4.get("objective") and s4.get("confirmed"):
        sess.step4 = {**s4, "confirmed": False, "confirmed_at": None, "stale": True}
        result["step4"] = True

    s5 = sess.step5 if isinstance(sess.step5, dict) else {}
    if (s5.get("testScript") or {}).get("steps"):
        sess.step5 = {**s5, "confirmed": False, "stale": True}
        result["step5"] = True

    return result


def _migrate_legacy_step4_to_step5(sess: WizardSession) -> bool:
    """If old session has testScript only under step4, copy to step5 (non-destructive)."""
    s4 = sess.step4 if isinstance(sess.step4, dict) else {}
    s5 = sess.step5 if isinstance(sess.step5, dict) else {}
    if s4.get("testScript") and not (s5 or {}).get("testScript"):
        sess.step5 = {
            **(s5 or {}),
            "testScript": s4.get("testScript"),
        }
        return True
    return False


def _refined_payload_path(key: str) -> Optional[Path]:
    """Path to the on-disk drop-in zephyr_payload.json for a case, if it exists."""
    if not key or not REFINED_DIR.exists():
        return None
    for p in REFINED_DIR.glob(f"*/{key}/zephyr_payload.json"):
        return p
    # Fallback for any deeper nesting of the group dir.
    for p in REFINED_DIR.rglob("zephyr_payload.json"):
        if p.parent.name == key:
            return p
    return None


def _backfill_from_refined(sess: WizardSession) -> bool:
    """Restore step4.objective + step5.testScript from the completed on-disk payload
    when the persisted runtime session is missing them.

    Cases refined before the runtime session captured step4/step5 (or whose session
    was later cleared) are 'Complete' on disk (refined-cases/**/zephyr_payload.json)
    yet load with empty synthesis views — the Generator shows "No objective yet" for
    a case that is actually done. The zephyr_payload.json is the canonical Complete
    artefact (guard_db_only explicitly allows reading it), so use it as the source of
    truth to rehydrate the session. This also keeps a subsequent export/push from
    overwriting the good payload with empty fallback content. Returns True if changed.
    """
    s4 = sess.step4 if isinstance(sess.step4, dict) else {}
    s5 = sess.step5 if isinstance(sess.step5, dict) else {}
    has_obj = bool((s4.get("objective") or "").strip())
    has_steps = bool((s5.get("testScript") or {}).get("steps")
                     or (s4.get("testScript") or {}).get("steps"))
    if has_obj and has_steps:
        return False  # session already carries the synthesis — nothing to do

    path = _refined_payload_path(sess.key)
    if not path:
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[backfill] could not read {path}: {e}")
        return False

    inner = raw.get(sess.key) if isinstance(raw, dict) else None
    if not isinstance(inner, dict):
        # Tolerate a direct-inner shape ({objective, testScript} at top level).
        inner = raw if (isinstance(raw, dict) and ("objective" in raw or "testScript" in raw)) else None
    if not isinstance(inner, dict):
        return False

    changed = False
    objective = (inner.get("objective") or "").strip()
    if objective and not has_obj:
        # Sanitize on backfill too — legacy on-disk bundles predate objective sanitization.
        sess.step4 = {**s4, "objective": sanitize_objective_html(objective),
                      "confirmed": True, "backfilled": True}
        changed = True
    ts = inner.get("testScript")
    if isinstance(ts, dict) and (ts.get("steps")) and not has_steps:
        sess.step5 = {**s5, "testScript": ts, "confirmed": True, "backfilled": True}
        changed = True

    # A backfilled case is Complete on disk, which means the three DB reviews WERE
    # confirmed when it was originally refined — that history just isn't in the
    # runtime session (it predates step4/step5 capture, or the session was cleared).
    # export() now gates on _can_synthesize, so without this the 43 existing bundles
    # would 400 on re-export ("confirm all three reviews") for reviews the user
    # already did. Mark the reviews confirmed-by-backfill so the gate reflects the
    # on-disk truth; `backfilled` distinguishes them from fresh in-session confirms.
    if changed:
        for step in (sess.step1, sess.step2, sess.step3):
            if not step.confirmed:
                step.confirmed = True
                step.confirmed_at = step.confirmed_at or datetime.utcnow()
                step.backfilled = True

    return changed


def get_data(request: Request):
    """The shared corpus references, built ONCE at startup (main.py startup_event).

    This used to be `return load_all_data()`, with the comment "Would be from
    app.state in a fuller implementation" — so every one of the 11 endpoints that
    depends on it rebuilt the whole reference set per request: re-reading
    zephyr_master, all candidates, decisions and two json_docs out of ck.db, plus a
    startup_check() that counts every corpus. Measured 47ms (70ms on py3.10) of
    redundant work per request, and because `get_data` is sync FastAPI ran it in a
    threadpool worker, so it burned one of those too.

    Two quieter costs beyond the latency: load_all_data() prints three lines to
    stdout on every call (data.py:57,88-93), which is where the "Loading lightweight
    references…" noise during ordinary use came from; and two dependencies resolved
    within one request could see two different snapshots of the corpus.

    main.py:132 already assigned this to app.state.app_data at startup and nothing
    read it — pytest_create has always done it correctly (see _data there, whose
    fail-loud 503 this mirrors). Deliberately NOT falling back to load_all_data():
    that would silently restore the per-request cost and mask a boot problem instead
    of reporting it. Safe because startup always runs in production, and the test
    suite drives the app through `with TestClient(...)` (tests/conftest.py:32), the
    context-manager form that fires startup/shutdown events.
    """
    data = getattr(request.app.state, "app_data", None)
    if not data:
        raise HTTPException(503, "Server data not loaded yet.")
    return data


# --- Query tokenization ------------------------------------------------------
# Used to build the keyword query for a step's candidate retrieval (see
# _build_step_query): drop words that carry no discriminating signal so the FTS
# search ranks on the case's actual feature nouns.
#
# NOTE (debt, Part B): this set is duplicated verbatim in db.py:123, which is the
# copy db.search_* actually scores with. Two copies is a drift risk — Part B moves
# the survivors here into wizard/descriptions.py and consumes db's single copy.
# The bespoke Step-2 scorer that used to live below (_score_zephyr_candidate +
# _ZREF_WEAK_ALONE, ~120 lines) is gone: it hand-rolled a slower, weaker
# reimplementation of db.search_zephyr, which is FTS-indexed and scores with the
# shared db._relevance_score. See PLAN-backend-module-split.md A1.

_ZREF_GENERIC_TOKENS = frozenset({
    "port", "ports", "ipv4", "ipv6", "ip", "switch", "switches", "interface",
    "interfaces", "test", "tests", "feature", "features", "basic", "function",
    "functionality", "command", "commands", "show", "config", "configuration",
    "platform", "new", "master", "template", "traffic", "link", "device",
    "devices", "support", "supported", "behaviour", "behavior", "check",
    "verify", "confirm", "using", "with", "from", "that", "this", "when",
    "case", "cases", "area", "manual", "auto", "server", "client", "mode",
    "type", "level", "status", "info", "data", "table", "entry", "entries",
    "packet", "packets", "network", "remote", "local", "enabled", "disabled",
    "enable", "disable", "set", "get", "add", "remove", "for", "via", "and",
    "the", "full", "half", "fixed", "copper", "fibre", "fiber", "gig", "cross",
    "straight", "awp", "cr", "proj", "project", "red", "api", "user", "defined",
    "default", "bridge", "eth", "vlan", "vlans", "tunnel", "queueing", "queuing",
    "priority", "source", "destination", "address", "static", "lag", "lacp",
    "interop", "exploratory", "testing", "platform-test", "functional",
    "field", "info", "error", "message", "generated", "whenever", "address",
})

def _normalize_zephyr_text(s: str) -> str:
    s = s or ""
    s = re.sub(r"^\(\d+\)\s*", "", s)
    s = s.replace("_", " ").replace("/", " ").replace("-", " ")
    return s.lower()


def _zephyr_tokens(s: str) -> List[str]:
    s = _normalize_zephyr_text(s)
    words = re.findall(r"[a-z0-9][a-z0-9+]{1,}", s)
    out: List[str] = []
    for w in words:
        if len(w) < 3:
            continue
        out.append(w)
        # Normalize MDI variants so MDI / MDIX / MDI-MDIX cluster together
        if w in ("mdi", "mdix"):
            out.extend(["mdi", "mdix"])
    return out


def _specific_tokens(toks) -> set:
    return {t for t in toks if t not in _ZREF_GENERIC_TOKENS}


def _build_testlink_description(item: dict, title: str = "") -> str:
    """Full TestLink step body for Step 1 UI — no mid-sentence character truncation.

    Includes all steps with complete action/expected text. Soft-caps only on
    pathological step counts (first 30) so payloads stay reasonable.
    """
    steps = (item or {}).get("steps") or []
    desc_parts: List[str] = []
    for s in steps[:30]:
        action = (s.get("action") or "").strip()
        expected = (s.get("expected") or "").strip()
        if action or expected:
            if action and expected:
                desc_parts.append(f"Step: {action}\nExpected: {expected}")
            elif action:
                desc_parts.append(f"Step: {action}")
            else:
                desc_parts.append(f"Expected: {expected}")
    if desc_parts:
        return "\n\n".join(desc_parts)
    # Fallbacks only when no structured steps exist
    snip = ((item or {}).get("snippet") or "").strip()
    if snip:
        return snip
    return (title or (item or {}).get("title") or "").strip()


def _build_zephyr_case_description(
    slim_meta: dict,
    full: dict,
    title_fallback: str = "",
) -> str:
    """Full Zephyr case body for Step 2 UI — no mid-field character truncation.

    Soft-caps step count only (first 20) for pathological cases; each field is complete.
    """
    desc_parts: List[str] = []
    t = (
        (slim_meta or {}).get("title")
        or (full or {}).get("title")
        or title_fallback
        or ""
    ).strip()
    full = full or {}
    slim_meta = slim_meta or {}

    obj = str(full.get("objective") or "").strip()
    if obj:
        desc_parts.append("Objective: " + obj)
    pre = str(full.get("precondition") or "").strip()
    if pre:
        desc_parts.append("Precondition: " + pre)

    meta = []
    if slim_meta.get("status"):
        meta.append(f"Status: {slim_meta['status']}")
    if "has_objective" in slim_meta:
        meta.append(f"Has objective: {slim_meta['has_objective']}")
    if "num_steps" in slim_meta:
        meta.append(f"Num steps: {slim_meta['num_steps']}")
    if slim_meta.get("labels"):
        meta.append(f"Labels: {', '.join(slim_meta['labels'])}")
    if meta:
        desc_parts.append(" | ".join(meta))

    steps_source = full.get("steps", []) or []
    if steps_source:
        steps_list = []
        for i, s in enumerate(steps_source[:20], 1):
            d = (s.get("description") or "").strip()
            if d:
                steps_list.append(f"{i}. {d}")
        if steps_list:
            desc_parts.append("Steps:\n" + "\n".join(steps_list))

    if not desc_parts:
        desc_parts.append(t or "Related Zephyr case")
    return "\n\n".join(desc_parts)


def _enrich_zephyr_rows(
    rows: List[Dict[str, Any]],
    data: dict,
) -> List[Dict[str, Any]]:
    """Fill description from zephyr_master / batch jsonl for UI rows that only have title."""
    zm = data.get("zephyr_master", {}) or {}
    # Commit B: slim fields (title/folder/status/labels/…) already ride on each
    # row from db.search_zephyr, so no slim_index dict is needed.
    slim_by_key = {}
    need = []
    for r in rows:
        k = r.get("key") or r.get("id")
        if not k:
            continue
        # Re-enrich when description is missing or is just the title
        desc = (r.get("description") or "").strip()
        title = (r.get("title") or "").strip()
        if not desc or desc == title:
            if k not in zm:
                need.append(k)
    full_map = _get_full_zephyr_cases_batch(need) if need else {}
    out = []
    for r in rows:
        k = r.get("key") or r.get("id")
        if not k:
            out.append(r)
            continue
        slim = slim_by_key.get(k) or {
            "key": k,
            "title": r.get("title"),
            "folder": r.get("folder"),
            "status": r.get("status"),
            "labels": r.get("labels"),
            "has_objective": r.get("has_objective"),
            "num_steps": r.get("num_steps"),
        }
        full = zm.get(k) or full_map.get(k) or {}
        desc = _build_zephyr_case_description(slim, full, title_fallback=r.get("title") or "")
        enriched = {**r, "key": k, "description": desc}
        if not enriched.get("title"):
            enriched["title"] = slim.get("title") or full.get("title") or k
        if not enriched.get("folder"):
            enriched["folder"] = slim.get("folder") or full.get("folder") or ""
        out.append(enriched)
    return out


@router.post("/load_case/{key}")
async def load_case(key: str, data=Depends(get_data)):
    """Load or restore a case: session state only, no per-step candidate retrieval.

    Loading is deliberately CHEAP. Each of the three review steps fetches its own
    candidates when the user navigates to it (GET /step_candidates/{key}/{step}) —
    see _STEP_BUILDERS below. This has bitten the tool twice, both times because
    load pre-computed data for a panel the user had not opened yet:

      * Step 3 (ATPyLib) ran a blocking `analyze_atp_coverage` LLM call, adding ~60s
        to EVERY load, for a ranking the step's own "Suggest with LLM" button
        redid on demand anyway.
      * Step 2 (Zephyr) scanned all ~45k slim rows through a bespoke Python scorer:
        a measured 2.7s (3.8s on py3.10) bare on the event loop, so it froze every
        concurrent request — including the agent-bridge long-poll that claude_agent
        mode deadlocks without.

    So: no step does work here, and all three behave identically. See
    ask-ck/ck-facelift/PLAN-backend-module-split.md A1.
    """
    # Check in-memory or disk first
    sess = sessions.get(key) or _load_persisted(key)
    if sess:
        sessions[key] = sess
        if _migrate_legacy_step4_to_step5(sess):
            _mark_updated(sess)
    else:
        if key not in data.get("zephyr_master", {}):
            raise HTTPException(404, "Case not found")
        sess = WizardSession(key=key)
        # Populate primary decision (cross-ref from data/decisions)
        primary = data.get("decisions", {}).get(key)
        if primary:
            sess.primary = {"m": primary.get("m"), "c": primary.get("c"), "w": primary.get("w")}
        sessions[key] = sess

    # Rehydrate a Complete case whose runtime session lost step4/step5 from the
    # canonical on-disk payload, so the UI reflects the finished objective + steps.
    if _backfill_from_refined(sess):
        _mark_updated(sess)

    # Carry over workspace LLM preference (last Apply / Login) so switching cases
    # does not reset provider / CLI mode back to empty defaults.
    if _apply_workspace_llm_if_needed(sess):
        _mark_updated(sess)

    _persist_session(sess)

    zm = data.get("zephyr_master", {}) or {}
    case_title = (zm.get(key, {}) or {}).get("title", "") if key else ""

    return {
        "session": safe_session_dict(sess),   # redacts llm_config secrets
        "case_title": case_title,
        "message": "Case loaded (or restored from persistence). Confirm each of the three database reviews explicitly before synthesis is allowed."
    }


# --- Per-step candidate retrieval (deferred; see load_case) -------------------
# One builder per review step, all with the SAME signature and all reached through
# the SAME endpoint, so the three steps cannot drift apart in startup behaviour
# again. Each returns UI-ready rows for its step's top table. They differ only in
# where the data comes from — which is the intended difference.
#
# All of them search in KEYWORD mode (_STEP_SEARCH_MODE). These are DEFAULT views,
# built from a query auto-derived from the case title — not from something the user
# typed — and semantic search does not earn its cost there. Measured warm, per case
# (mean/max over 10 cases spanning 10 folder leaves):
#
#     step 2   hybrid  763.5 / 2692.0 ms      keyword   95.3 / 576.9 ms
#     step 3   hybrid  437.7 /  773.3 ms      keyword   21.7 /  61.0 ms
#
# Hybrid also pays a ~11.8s sentence-transformer construction on the first call
# after a restart, which would land on a plain panel-open. Note step 2's hybrid
# figure is no better than the 2.7s bespoke scan this commit deleted — swapping one
# slow default for another would have missed the point.
#
# The semantic path is NOT lost: /search_zephyr and /search_atp still default to
# hybrid, so it applies exactly where it pays off — a query the user actually typed.
_STEP_SEARCH_MODE = "keyword"


def _step1_testlink_candidates(key: str, sess: WizardSession, data: dict,
                               case_title: str) -> List[Dict[str, Any]]:
    """Step 1: the case's pre-computed TestLink candidates from ck.db.

    No search needed — build_db already scored and stored these per case; this only
    enriches them with full step text for review.
    """
    cdata = data.get("candidates_dict", {}).get(key) or {}
    testlink = data.get("testlink", {})
    rows: List[Dict[str, Any]] = []
    for cand in (cdata.get("candidates") or [])[:8]:
        aid = cand.get("id")
        full = testlink.get(aid, {}) or {}
        title = cand.get("title") or full.get("title") or aid
        rich_desc = (_build_testlink_description(full, title=title)
                     or cand.get("snippet", "") or title or "")
        rows.append({**cand, "title": title, "description": rich_desc})
    return rows


def _step2_zephyr_candidates(key: str, sess: WizardSession, data: dict,
                             case_title: str) -> List[Dict[str, Any]]:
    """Step 2: external Zephyr cross-refs via the shared FTS search.

    Uses the same _search_zephyr_external the /search_zephyr endpoint uses, so the
    default view and a manual search rank identically (db.search_zephyr → FTS +
    db._relevance_score, excluding the current Cases list + this key).

    This replaced a bespoke 45k-row scan whose output was measured to be ~81%
    score-ties broken alphabetically by title — see PLAN-backend-module-split.md.
    """
    q = _build_zephyr_query(sess, data, key=key, case_title=case_title)
    if not q:
        return []
    rows = _search_zephyr_external(q, data, case_key=key, limit=8,
                                   mode=_STEP_SEARCH_MODE)
    for r in rows:
        r.setdefault("justification", "Candidate from keyword search")
        r.setdefault("source", "keyword")
    return rows


def _step3_atp_candidates(key: str, sess: WizardSession, data: dict,
                          case_title: str) -> List[Dict[str, Any]]:
    """Step 3: keyword-scored ATPyLib candidates (the LLM ranking is on-demand)."""
    q = _build_atp_query(sess, case_title=case_title) if sess else (case_title or key or "")
    raw = _get_atp_candidates(q, data, limit=18, mode=_STEP_SEARCH_MODE)

    rows: List[Dict[str, Any]] = []
    seen_ids = set()
    for c in raw:
        cid = c.get("id")
        if not cid or cid in seen_ids:
            continue
        full_desc = (c.get("description") or "").strip()
        short_title = (c.get("title") or "").strip()
        if not short_title or short_title == full_desc:
            short_title, full_desc = _split_atp_title_description(
                full_desc or c.get("title") or "", cid)
        rows.append({
            "id": cid,
            "title": short_title or cid,
            "score": c.get("score", 0.55),
            "suite": c.get("suite", ""),
            "justification": "Candidate from keyword search",
            "description": full_desc or short_title or "Candidate from keyword search",
            "source": "keyword",
        })
        seen_ids.add(cid)

    # Non-functional tests are not reviewable coverage for Step 3.
    rows = [
        c for c in rows
        if "(not a functional test)" not in (c.get("title", "") + c.get("description", "")).lower()
    ]
    rows.sort(key=lambda c: (-float(c.get("score") or 0), str(c.get("id") or "")))
    return rows[:12]


# step -> (kind, builder). The kind is the frontend's table/bus name.
_STEP_BUILDERS = {
    1: ("testlink", _step1_testlink_candidates),
    2: ("zephyr", _step2_zephyr_candidates),
    3: ("atp", _step3_atp_candidates),
}


@router.get("/step_candidates/{key}/{step}")
async def step_candidates(key: str, step: int, data=Depends(get_data)):
    """Candidates for ONE review step, fetched when the user opens that step.

    The deferred half of the load_case split: see that docstring for why none of
    this runs at case-load time. One endpoint for all three steps so the uniform
    behaviour is structural rather than a convention three call sites remember.

    Off the event loop: steps 2 and 3 reach FTS + (in hybrid mode) sentence-
    transformer inference, and the first such call after a restart also constructs
    the model from disk. Step 1 is threadpooled too — not because it is slow, but
    so all three share one dispatch path.
    """
    entry = _STEP_BUILDERS.get(step)
    if not entry:
        raise HTTPException(400, "step must be 1 (TestLink), 2 (Zephyr) or 3 (ATPyLib)")
    kind, builder = entry

    sess = sessions.get(key) or _load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Load the case first.")
    sessions[key] = sess

    zm = data.get("zephyr_master", {}) or {}
    case_title = (zm.get(key, {}) or {}).get("title", "") or ""
    candidates = await run_in_threadpool(builder, key, sess, data, case_title)
    return {"key": key, "step": step, "kind": kind, "candidates": candidates}


def _refined_complete_keys() -> set:
    """Cases with drop-in refined-cases/**/AWPTCM-Txxxx/zephyr_payload.json are 'complete'."""
    refined_root = REFINED_DIR
    done = set()
    if not refined_root.exists():
        return done
    try:
        for path in refined_root.rglob("zephyr_payload.json"):
            parent = path.parent.name
            if parent.startswith("AWPTCM-"):
                done.add(parent)
    except Exception as e:
        print(f"Warning: scanning refined-cases failed: {e}")
    return done


def _session_progress_map() -> Dict[str, dict]:
    """Per-case wizard progress (confirms + step4/5). Commit C: sourced from the
    sessions table via db.list_session_progress() (identical derivation)."""
    try:
        return db.list_session_progress()
    except Exception as e:
        print(f"Warning: reading session progress failed: {e}")
        return {}


def _cases_index() -> Tuple[set, Dict[str, dict]]:
    """(complete_keys, per-case progress) — the two blocking reads /cases needs.

    Paired in one helper so the handler makes a single threadpool hop, and named so
    the event-loop AST invariant can see what is being dispatched.
    """
    return _refined_complete_keys(), _session_progress_map()


def _build_case_groups(keys, zephyr: dict) -> List[dict]:
    """Group case keys by Zephyr folder leaf for optgroups."""
    groups: Dict[str, List[str]] = {}
    for key in keys:
        folder = zephyr.get(key, {}).get("folder", "") or ""
        group = folder.rstrip("/").split("/")[-1] if folder else "Other"
        groups.setdefault(group, []).append(key)
    for g in groups:
        groups[g].sort(key=lambda k: (k.split("-T")[-1] if "-T" in k else k))
    grouped = []
    for g in sorted(groups.keys()):
        case_list = groups[g]
        enriched = []
        for k in case_list:
            title = zephyr.get(k, {}).get("title", k)
            enriched.append({"key": k, "title": title})
        grouped.append({"label": f"{g} ({len(case_list)})", "cases": enriched})
    return grouped


@router.get("/cases")
async def get_cases(data=Depends(get_data)):
    """Return cases split into complete vs open/incomplete for dual dropdowns.

    - complete: refined-cases has zephyr_payload.json for the case
    - incomplete: all other candidate cases
      - in_progress: has wizard session progress (confirms / step4)
      - not_started: no session progress yet
    """
    cands = data.get("candidates", []) or []
    zephyr = data.get("zephyr_master", {})
    all_keys = [c["key"] for c in cands
                if c.get("candidates") and c.get("key")
                and not _is_hidden_case(c["key"], zephyr.get(c["key"], {}).get("folder", ""))]

    # Off the event loop: _refined_complete_keys rglob's the whole refined-cases tree
    # (measured ~14ms) and _session_progress_map hits ck.db. Small next to the Step-2
    # scan this commit removed, but the same class of bug — blocking I/O in an async
    # handler — so it gets the same treatment. Dispatched via a NAMED helper, not a
    # lambda: tests/test_event_loop_blocking_batch_b.py matches run_in_threadpool's
    # first argument as an ast.Name, so a lambda would hide both calls from the
    # invariant while looking correct. Keep blocking work reachable by name.
    complete_set, progress = await run_in_threadpool(_cases_index)

    complete_keys = sorted(
        [k for k in all_keys if k in complete_set],
        key=lambda k: (k.split("-T")[-1] if "-T" in k else k),
    )
    incomplete_keys = sorted(
        [k for k in all_keys if k not in complete_set],
        key=lambda k: (k.split("-T")[-1] if "-T" in k else k),
    )
    in_progress_keys = [k for k in incomplete_keys if k in progress]
    not_started_keys = [k for k in incomplete_keys if k not in progress]

    def enrich(keys):
        return [
            {
                "key": k,
                "title": zephyr.get(k, {}).get("title", k),
                "status": "complete" if k in complete_set else (
                    "in_progress" if k in progress else "not_started"
                ),
                "progress": progress.get(k),
            }
            for k in keys
        ]

    # Open/partial dropdown order:
    #  1) Single top optgroup with ALL in-progress/partial cases (always first)
    #  2) Not-started cases grouped by folder below
    incomplete_grouped = []
    if in_progress_keys:
        # Sort partials by folder leaf then key so related work stays together within the top block
        def _partial_sort_key(k: str):
            folder = zephyr.get(k, {}).get("folder", "") or ""
            leaf = folder.rstrip("/").split("/")[-1] if folder else "Other"
            num = k.split("-T")[-1] if "-T" in k else k
            return (leaf.lower(), num)

        partial_sorted = sorted(in_progress_keys, key=_partial_sort_key)
        partial_cases = []
        for k in partial_sorted:
            title = zephyr.get(k, {}).get("title", k)
            prog = progress.get(k) or {}
            # Light progress hint in title for the top partials block
            conf = prog.get("confirms", 0)
            hint = f" [{conf}/3 steps]" if conf else ""
            if prog.get("has_step4") and conf:
                hint = " [synth done]"
            elif prog.get("has_step4"):
                hint = " [has draft]"
            partial_cases.append({
                "key": k,
                "title": f"{title}{hint}" if title else f"{k}{hint}",
            })
        incomplete_grouped.append({
            "label": f"In progress / partial ({len(partial_cases)}) — shown first",
            "cases": partial_cases,
            "bucket": "in_progress",
        })
    if not_started_keys:
        for grp in _build_case_groups(not_started_keys, zephyr):
            incomplete_grouped.append({
                "label": f"Not started — {grp['label']}",
                "cases": grp["cases"],
                "bucket": "not_started",
            })

    complete_grouped = _build_case_groups(complete_keys, zephyr)
    for grp in complete_grouped:
        grp["bucket"] = "complete"

    # Flat incomplete list also puts partials first
    incomplete_flat_keys = in_progress_keys + not_started_keys

    return {
        "counts": {
            "total": len(all_keys),
            "complete": len(complete_keys),
            "incomplete": len(incomplete_keys),
            "in_progress": len(in_progress_keys),
            "not_started": len(not_started_keys),
        },
        "incomplete": {
            "cases": enrich(incomplete_flat_keys),
            "grouped": incomplete_grouped,
        },
        "complete": {
            "cases": enrich(complete_keys),
            "grouped": complete_grouped,
        },
        # Backward-compatible flat fields (partials first, then not-started, then complete)
        "cases": enrich(incomplete_flat_keys + complete_keys),
        "grouped": incomplete_grouped + complete_grouped,
    }


@router.get("/search_atp")
async def search_atp(q: str = "", keep_ids: str = "", mode: str = "", data=Depends(get_data)):
    """ATPyLib search for Step 3. mode=keyword|hybrid|semantic (default hybrid when
    vectors are available, else keyword). Merged client-side with preloaded candidates.

    keep_ids: comma-separated ids already shown in the client pool — always
    returned, re-scored against `q`, so a new search re-ranks the whole pool.
    Returns short title + full description (no mid-sentence truncation).
    """
    keep = {s for s in (keep_ids or "").split(",") if s}
    # Off the event loop — see search_testlink.
    cands = await run_in_threadpool(
        _get_atp_candidates, q, data, limit=20, keep_ids=keep, mode=mode)
    return {
        "results": [
            {
                "id": c.get("id"),
                "title": c.get("title") or c.get("id"),
                "description": c.get("description") or "",
                "suite": c.get("suite", ""),
                "score": c.get("score", 0.6),
                "source": "search",
            }
            for c in cands
        ]
    }


# --- Shared keyword relevance scoring ----------------------------------------
# Commit B: the weighted relevance scorer now lives in db._relevance_score and is
# applied inside db.search_testlink / search_zephyr / search_atp (single source of
# truth, shared with tool/ scripts). The three wizard wrappers below delegate to
# those; this module no longer keeps a private copy (was a drift risk).


def _hybrid_on(mode: str) -> bool:
    """True → use semantic+keyword hybrid; False → keyword only. Default (mode
    empty/'hybrid'/'semantic') is hybrid when vectors are available, else keyword;
    'keyword' forces keyword. db.*_hybrid also degrades internally, so this is safe."""
    return (mode or "").lower() != "keyword" and db.HAS_VEC


def _search_testlink(q: str, data: dict, limit: int = 20,
                     keep_ids: Optional[set] = None, mode: str = "") -> List[Dict[str, Any]]:
    """Keyword (or hybrid) search over TestLink. Ranking delegates to db; the
    description is re-enriched with full step text for the UI (Commit B/D)."""
    keep = keep_ids or set()
    rows = (db.search_testlink_hybrid(q, keep_ids=keep, limit=limit) if _hybrid_on(mode)
            else db.search_testlink(q, keep_ids=keep, limit=limit))
    for r in rows:
        full = data.get("testlink", {}).get(r["id"]) or {}
        rich = _build_testlink_description(full, title=r.get("title") or "")
        if rich:
            r["description"] = rich
    return rows


def _search_zephyr_external(
    q: str,
    data: dict,
    case_key: str = "",
    limit: int = 20,
    keep_ids: Optional[set] = None,
    mode: str = "",
) -> List[Dict[str, Any]]:
    """Keyword (or hybrid) external-Zephyr search, omitting the current Cases list
    + primary key. Full descriptions filled by _enrich_zephyr_rows (Commit B/D)."""
    current_cases = {
        c["key"] for c in data.get("candidates", []) or []
        if c.get("candidates")
    }
    if case_key:
        current_cases.add(case_key)
    keep = keep_ids or set()
    if _hybrid_on(mode):
        rows = db.search_zephyr_hybrid(q, case_key=case_key, exclude_keys=current_cases,
                                       keep_ids=keep, limit=limit)
    else:
        rows = db.search_zephyr(q, case_key=case_key, exclude_keys=current_cases,
                                keep_ids=keep, limit=limit)
    return _enrich_zephyr_rows(rows, data)


@router.get("/search_testlink")
async def search_testlink(q: str = "", keep_ids: str = "", mode: str = "", data=Depends(get_data)):
    """TestLink search for Step 1. mode=keyword|hybrid|semantic (default hybrid when
    vectors are available, else keyword). keep_ids: comma-separated pool ids,
    always returned re-scored against `q`."""
    keep = {s for s in (keep_ids or "").split(",") if s}
    # Off the event loop: a hybrid search runs sentence-transformer inference inline,
    # and the FIRST one after a restart also constructs the model from disk (measured
    # 16.2s; ~20ms warm). On the loop that stalls every other request — including the
    # agent-bridge long-poll the LLM call sites are already careful to protect.
    return {"results": await run_in_threadpool(
        _search_testlink, q, data, limit=20, keep_ids=keep, mode=mode)}


@router.get("/search_zephyr")
async def search_zephyr(q: str = "", case_key: str = "", keep_ids: str = "",
                        mode: str = "", data=Depends(get_data)):
    """External Zephyr search for Step 2 (omits current Cases list). mode=keyword|
    hybrid|semantic (default hybrid when vectors are available, else keyword).
    keep_ids: comma-separated pool keys, always returned re-scored against `q`."""
    keep = {s for s in (keep_ids or "").split(",") if s}
    # Off the event loop — see search_testlink.
    return {"results": await run_in_threadpool(
        _search_zephyr_external, q, data, case_key=case_key, limit=20,
        keep_ids=keep, mode=mode)}


# The decision rationale (`w`) is analyst prose about COVERAGE STATUS, mixed in with
# real feature keywords. Its feature words are valuable — for "(163) QoS - Physical
# Queue" the rationale contributes "cos map queues", moving the best cross-ref from
# rank 20 to rank 4; for the DHCPv6 case "range" moves it from 143 to 3. But its
# process vocabulary is pure poison as a ranking term: on "Port - Auto Negotiation"
# the rationale "Auto/Auto negotiation; Zephyr says covered by auto-test" injected
# "zephyr says covered", and FTS then ranked "Test modem support. TPS SAYS Japan only"
# as a top cross-ref. These words are never a feature, so strip them and keep the rest.
_DECISION_META_TOKENS = frozenset({
    "zephyr", "testlink", "atp", "atpylib", "says", "said", "covered", "coverage",
    "cover", "covers", "test", "tests", "tested", "testing", "suite", "suites",
    "case", "cases", "note", "notes", "todo", "tbd", "none", "partial", "partially",
    "existing", "exists", "already", "probably", "maybe", "likely", "unclear",
    "review", "reviewed", "check", "checked", "confirm", "confirmed", "duplicate",
    "obsolete", "deprecated", "manual", "automated", "automation",
})


def _build_zephyr_query(sess: WizardSession, data: dict, key: str = "",
                        case_title: str = "") -> str:
    """Keyword query for Step 2's default external cross-ref view.

    Carries the same signal the retired bespoke scorer derived by hand:
      * the case title and its Zephyr folder leaf (the feature "area"),
      * the primary decision RATIONALE (`w`) — not the match ids (`m`), which are
        AWP-#### noise for ranking,
      * titles of what the user already picked in Step 1, since an upstream choice
        sharpens what a useful cross-ref looks like (same inputs suggest_zephyr uses).

    The case key itself is deliberately excluded: 'awptcm' / the bare test number
    match nothing useful and only dilute the token budget.
    """
    folder = ((data.get("zephyr_master", {}) or {}).get(key, {}) or {}).get("folder") or ""
    leaf = folder.rstrip("/").split("/")[-1] if folder else ""

    parts = [case_title or "", leaf]
    if sess.primary:
        parts.append(str(sess.primary.get("w") or ""))
    dec = (data.get("decisions") or {}).get(key) or {}
    parts.append(str(dec.get("w") or ""))
    for sel in (sess.step1.selections or [])[:6]:
        parts.append(sel.title or "")

    # Deliberately does NOT strip _ZREF_GENERIC_TOKENS. db.search_zephyr does its own
    # specific/generic split, and since the area tier was added it NEEDS the generic
    # words present to derive area affinity — pre-filtering them here made "port"
    # invisible to db and left the best cross-ref for "Port - Auto Negotiation"
    # stranded at rank 9 of a 12-way tie. Division of labour: this function decides
    # which TEXT is relevant (drop analyst process-prose, ids, bare numbers); db
    # decides how to WEIGHT it (specific / area / ignored).
    toks = [t for t in _zephyr_tokens(" ".join(parts))
            if t not in _DECISION_META_TOKENS
            and not t.isdigit() and not t.startswith("awp")]
    # De-dupe while preserving order so a word repeated across parts does not eat
    # the token budget.
    seen: set = set()
    ordered = [t for t in toks if not (t in seen or seen.add(t))]
    return " ".join(ordered[:24])


def _build_atp_query(sess: WizardSession, case_title: str = "") -> str:
    """Build a keyword search query from case + previous selections for ATP retrieval."""
    parts = [sess.key or "", case_title or ""]
    if sess.primary:
        parts.append(str(sess.primary.get("w", "")))
        parts.append(str(sess.primary.get("m", "")))
    for sel in (sess.step1.selections or []):
        parts.append(sel.title or "")
        parts.append(sel.justification or "")
    for sel in (sess.step2.selections or []):
        parts.append(sel.title or "")
    # Prefer specific tokens for search quality
    raw = " ".join(parts)
    toks = [t for t in _zephyr_tokens(raw) if t not in _ZREF_GENERIC_TOKENS]
    # Fall back to raw if everything was filtered
    return " ".join(toks[:24]) if toks else raw


def _split_atp_title_description(full_desc: str, fallback_id: str = "") -> Tuple[str, str]:
    """Split test_id_description text into short title + full body (no mid-sentence truncation).

    Source format is typically:
      Short title line

      [Log-derived analysis] Longer paragraph...
    Title = first non-empty line (before analysis marker). Description = full original text.
    """
    full = (full_desc or "").strip()
    if not full:
        return (fallback_id or "", "")
    # Prefer text before the analysis marker as title when present
    for marker in ("\n\n[", "\n["):
        idx = full.find(marker)
        if idx > 0:
            title = full[:idx].strip().split("\n")[0].strip()
            if title:
                return (title, full)
    # Otherwise first non-empty line is the short title
    for line in full.splitlines():
        line = line.strip()
        if line:
            return (line, full)
    return (fallback_id or full[:80], full)


def _get_atp_candidates(q: str, data: dict, limit: int = 20,
                        keep_ids: Optional[set] = None, mode: str = "") -> List[Dict[str, Any]]:
    """Candidate ATP tests via keyword (or hybrid) search. Full descriptions,
    short title. keep_ids pool rows always returned, re-scored (Commit B/D)."""
    keep = keep_ids or set()
    if _hybrid_on(mode):
        return db.search_atp_hybrid(q, keep_ids=keep, limit=limit)
    return db.search_atp(q, keep_ids=keep, limit=limit)


def _get_refined_group(case_key: str, data: dict) -> str:
    """Determine the appropriate refined-cases group folder for a case.
    Uses the last segment of the zephyr folder (e.g. 'Port', 'IPv4').
    Tries to match an existing refined-cases directory for consistency
    (e.g. 'Port (7)', 'IPv4 (44)'), otherwise uses the base name and creates if needed.
    Cross-references PROGRESS.md (output generation to produce drop-in refined-cases artifacts)
    and SERVER-README.md (drop files into refined-cases/<Group>/...).
    """
    zephyr = data.get("zephyr_master", {})
    folder = zephyr.get(case_key, {}).get("folder", "") or ""
    base = folder.rstrip("/").split("/")[-1] if folder else "Other"

    refined_root = REFINED_DIR
    if refined_root.exists():
        for d in sorted(refined_root.iterdir()):
            if d.is_dir():
                name = d.name
                # Match if base appears in existing group name (case insensitive)
                if base.lower() in name.lower() or name.lower().startswith(base.lower()):
                    return name
    return base


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
    # Off the event loop — see search_testlink.
    candidates = await run_in_threadpool(_get_atp_candidates, q, data, limit=25)

    # Call LLM for selection. _session_llm_cfg applies the workspace LLM at dispatch
    # time so this respects the configured backend even if the session's persisted
    # config is stale/inactive.
    llm_cfg = _session_llm_cfg(sess)
    dry_run = bool(body.get("dry_run"))
    result = await run_in_threadpool(
        suggest_relevant_atp,
        sess.dict() if hasattr(sess, "dict") else sess.model_dump(),
        candidates,
        llm_config=llm_cfg,
        dry_run=dry_run,
    )
    if dry_run:
        return _preview_from(result)
    suggestions = result

    # Enrich with full source descriptions (not just LLM reason) for Step 3 UI
    test_id_desc = data.get("test_id_desc", {}) or {}
    by_id = {c.get("id"): c for c in candidates if c.get("id")}
    enriched = []
    for s in suggestions:
        sid = s.get("id")
        base = by_id.get(sid, {})
        info = test_id_desc.get(sid, {}) or {}
        full_desc = (base.get("description") or info.get("description") or "").strip()
        short_title, full_desc = _split_atp_title_description(
            full_desc or base.get("title") or "", sid or ""
        )
        enriched.append({
            **s,
            "title": short_title or sid,
            "description": full_desc or s.get("reason") or "",
            "suite": base.get("suite") or info.get("suite_name") or "",
            "score": base.get("score", 0.85),
            "justification": s.get("reason") or "LLM suggestion",
        })

    # Return in a form easy for frontend to apply (pre-check)
    return {
        "query_used": q,
        "num_candidates_considered": len(candidates),
        "suggestions": enriched,  # list of {id, reason, title, description, suite, score}
    }


def _session_llm_cfg(sess: WizardSession) -> dict:
    # Apply the workspace LLM login at dispatch time if this session has no active
    # config of its own — otherwise a stale/inactive persisted config (or a session
    # whose workspace login was applied after it was first loaded) would fall through
    # to the LLM layer's default backend, silently using the wrong provider. load_case
    # applies it once; centralizing here guarantees every LLM handler resolves the
    # current workspace backend at call time. Same fix as pytest_create._llm_cfg.
    if _apply_workspace_llm_if_needed(sess):
        _mark_updated(sess)
        _persist_session(sess)
    if hasattr(sess, "llm_config"):
        return sess.llm_config.dict() if hasattr(sess.llm_config, "dict") else sess.llm_config
    return {}


def _preview_from(result) -> dict:
    """Shape a dry_run function result ({dry_run, prompt, ...}) into the standard
    provenance-preview HTTP response. dry_run reuses the endpoint's real path so
    the previewed prompt is 1-for-1 with what a real send would transmit."""
    r = result if isinstance(result, dict) else {}
    return {"provenance": {
        "prompt": r.get("prompt", ""),
        "provider": r.get("provider"),
        "model": r.get("model"),
        "auth_method": r.get("auth_method"),
        "note": r.get("note"),
        "dry_run": True,
    }}


@router.post("/suggest_testlink/{key}")
async def suggest_testlink(key: str, body: dict = Body(default={}), data=Depends(get_data)):
    """LLM pre-select TestLink cases for Step 1 (user reviews/approves)."""
    body = body or {}
    sess = sessions.get(key) or _load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Load the case first.")
    zm = data.get("zephyr_master", {}) or {}
    case_title = zm.get(key, {}).get("title", "") or ""
    q = body.get("q") or " ".join(filter(None, [
        case_title,
        str((sess.primary or {}).get("w") or ""),
        str((sess.primary or {}).get("m") or ""),
    ]))
    # Off the event loop — see search_testlink.
    candidates = await run_in_threadpool(_search_testlink, q, data, limit=30)
    # Also include load-time candidates for this case if present (full TL descriptions)
    testlink = data.get("testlink", {}) or {}
    cdata = data.get("candidates_dict", {}).get(key) or {}
    seen = {c.get("id") for c in candidates}
    for cand in (cdata.get("candidates") or [])[:12]:
        cid = cand.get("id")
        if cid and cid not in seen:
            full = testlink.get(cid, {}) or {}
            title = cand.get("title") or full.get("title") or cid
            candidates.append({
                "id": cid,
                "title": title,
                "description": _build_testlink_description(full, title=title)
                or cand.get("snippet")
                or title
                or "",
                "snippet": cand.get("snippet") or title or "",
                "score": cand.get("score") or 0.5,
            })
            seen.add(cid)
    dry_run = bool(body.get("dry_run"))
    result = await run_in_threadpool(
        suggest_relevant_testlink,
        sess.dict() if hasattr(sess, "dict") else sess.model_dump(),
        candidates,
        llm_config=_session_llm_cfg(sess),
        case_title=case_title,
        dry_run=dry_run,
    )
    if dry_run:
        return _preview_from(result)
    suggestions = result
    # Enrich suggestions with full source descriptions for the UI merge
    by_id = {c.get("id"): c for c in candidates if c.get("id")}
    enriched = []
    for s in suggestions:
        sid = s.get("id")
        base = by_id.get(sid, {})
        full = testlink.get(sid, {}) or {}
        title = base.get("title") or full.get("title") or sid
        full_desc = (
            base.get("description")
            or _build_testlink_description(full, title=title)
            or base.get("snippet")
            or s.get("reason")
            or ""
        )
        enriched.append({
            **s,
            "title": title,
            "description": full_desc,
            "score": base.get("score", 0.85),
            "justification": s.get("reason") or "LLM suggestion",
        })
    return {
        "query_used": q,
        "num_candidates_considered": len(candidates),
        "suggestions": enriched,
    }


@router.post("/suggest_zephyr/{key}")
async def suggest_zephyr(key: str, body: dict = Body(default={}), data=Depends(get_data)):
    """LLM pre-select external Zephyr cross-refs for Step 2."""
    body = body or {}
    sess = sessions.get(key) or _load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Load the case first.")
    zm = data.get("zephyr_master", {}) or {}
    case_title = zm.get(key, {}).get("title", "") or ""
    q_parts = [
        case_title,
        str((sess.primary or {}).get("w") or ""),
    ]
    for sel in (sess.step1.selections or [])[:6]:
        q_parts.append(sel.title or "")
    q = body.get("q") or " ".join(filter(None, q_parts))
    # Off the event loop — see search_testlink.
    candidates = await run_in_threadpool(_search_zephyr_external, q, data, case_key=key, limit=30)
    dry_run = bool(body.get("dry_run"))
    result = await run_in_threadpool(
        suggest_relevant_zephyr,
        sess.dict() if hasattr(sess, "dict") else sess.model_dump(),
        candidates,
        llm_config=_session_llm_cfg(sess),
        case_title=case_title,
        dry_run=dry_run,
    )
    if dry_run:
        return _preview_from(result)
    suggestions = result
    by_id = {c.get("id") or c.get("key"): c for c in candidates}
    # Rebuild rows then re-enrich so LLM-only hits still get full case bodies
    draft = []
    for s in suggestions:
        sid = s.get("id")
        base = by_id.get(sid, {})
        draft.append({
            **s,
            "key": sid,
            "id": sid,
            "title": base.get("title") or sid,
            "folder": base.get("folder") or "",
            "description": base.get("description") or base.get("title") or "",
            "justification": s.get("reason") or "LLM suggestion",
            "score": base.get("score", 0.85),
            "source": "llm",
        })
    enriched = _enrich_zephyr_rows(draft, data)
    # Preserve LLM justification after enrich
    just_by = {s.get("id"): s.get("reason") for s in suggestions}
    for row in enriched:
        k = row.get("key") or row.get("id")
        if just_by.get(k):
            row["justification"] = just_by[k]
    return {
        "query_used": q,
        "num_candidates_considered": len(candidates),
        "suggestions": enriched,
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

    # Snapshot the pre-confirm selections so we can tell an actual change from a
    # harmless re-confirm of the same shortlist (see _invalidate_downstream below).
    _before = _selection_fingerprint(sess, step)

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
        # Gaps are LLM-generated at synthesis/export for Traceability — not user-edited in Step 3
        if "art_string" in body:
            sess.art_string = body.get("art_string", "")
        # Auto-build ART string from confirmed ATP selections when not provided
        if not sess.art_string and sess.step3.selections:
            ids = [s.id_or_key for s in sess.step3.selections if s.id_or_key]
            if ids:
                sess.art_string = " + ".join(ids[:8])
    else:
        raise HTTPException(400, "Invalid step")

    # STATE (adversarial-review finding wizard.py:1381): confirming an upstream DB
    # review only ever set flags forward — it never invalidated the objective (step4)
    # or test steps (step5) that were synthesized FROM the previous selections. A user
    # who went back to Step 1, swapped the TestLink case the objective was written
    # around, and re-confirmed would still see "✓ Confirmed" / "✓ Ready" downstream,
    # then export a bundle whose zephyr_payload.json (old generation) contradicted its
    # own traceability.md (new selections). Invalidation is already the house style
    # one level down (synthesize_objectives self-invalidates at :1690; save_objective
    # comments "Edits invalidate prior confirm"; pytest_create has _invalidate_from) —
    # this edge was simply missing.
    invalidated = _invalidate_downstream(sess, changed=(_selection_fingerprint(sess, step) != _before))

    _mark_updated(sess)
    _persist_session(sess)

    return {
        "session": safe_session_dict(sess),   # redacts llm_config secrets
        "can_synthesize": _can_synthesize(sess),
        "invalidated": invalidated,
    }


@router.post("/clear_session/{key}")
async def clear_session(key: str):
    """Clear both in-memory and persisted session state for a case.
    Useful for resetting after a bad confirm or wanting to start fresh.

    Does NOT clear the workspace LLM preference — Apply / Login still applies
    to the next case you load.
    """
    sessions.pop(key, None)
    _clear_persisted(key)
    return {
        "message": f"Session for {key} cleared (workspace LLM preference kept)",
        "workspace_llm_kept": True,
    }


@router.get("/claude_cli_status")
async def claude_cli_status():
    """Report whether the Claude Code CLI is installed on the server machine.

    Used by the headless "claude_code" auth mode. Checks binary presence + version
    only (spends no tokens). Login state surfaces on first real call.
    """
    return check_claude_cli()


@router.get("/grok_cli_status")
async def grok_cli_status():
    """Report whether the xAI Grok CLI is installed (for SuperGrok/X Premium+ subscription login)."""
    return check_grok_cli()


@router.get("/llm_config")
async def get_llm_config():
    """Return the persisted workspace LLM config (no secrets) for cold page load.

    Without this, a fresh page has no way to learn the stored login, so the LLM
    status shows "No credential" until the user re-applies — even though the
    workspace default is persisted and already drives calls. The browser calls
    this on boot to render the real status (and, for local_llm, whether a key is
    stored). Credentials are never returned; only booleans/flags.
    """
    cfg = _load_global_llm()
    if not cfg:
        return {"llm_config": None}
    am = (getattr(cfg, "auth_method", None) or "").lower()
    safe = {
        "provider": cfg.provider,
        "auth_method": cfg.auth_method,
        "model": cfg.model,
        "base_url": cfg.base_url,
        "has_key": _llm_is_active(cfg),
    }
    if am == "local_llm":
        safe["local_llm_key_set"] = bool(get_local_llm_key())
    return {"llm_config": safe}


@router.post("/llm_health")
async def llm_health():
    """Ping the configured workspace LLM with a minimal completion to confirm it
    is reachable and answering. Exercises the exact real-call path (config
    resolution + credential + transport via _call_llm_with_meta), so it
    distinguishes 'my config is wrong' from 'the backend is down', and the ping
    is recorded in debug-log like any other call. Provider-agnostic: works for
    whatever auth_method is active, not just local_llm.
    """
    cfg = _load_global_llm()
    if not cfg or not _llm_is_active(cfg):
        return {"ok": False, "reason": "not_configured",
                "detail": "No active LLM configuration. Apply a provider on the Configure page first."}
    llm_cfg = cfg.dict() if hasattr(cfg, "dict") else cfg.model_dump()
    t0 = time.monotonic()
    # Tiny prompt through the same choke point every real call uses. run_prompt
    # needs a template; use a throwaway one-liner rendered inline via a literal.
    meta = await run_in_threadpool(
        _health_ping, llm_cfg,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    if meta.get("error"):
        return {"ok": False, "reason": "call_failed",
                "auth_method": getattr(cfg, "auth_method", None),
                "model": meta.get("model"), "latency_ms": latency_ms,
                "detail": (meta.get("error_detail") or meta.get("content") or "LLM error")[:500]}
    content = (meta.get("content") or "").strip()
    return {"ok": True, "auth_method": getattr(cfg, "auth_method", None),
            "provider": meta.get("provider"), "model": meta.get("model"),
            "latency_ms": latency_ms, "reply": content[:80],
            "usage": meta.get("usage")}


@router.post("/set_llm_config")
@router.post("/set_llm_config/{key}")
async def set_llm_config(body: dict, key: Optional[str] = None):
    """Login-like endpoint. Sets the workspace LLM provider (and, when a case
    key is supplied, that case's session config too).

    The case key is OPTIONAL: applying an LLM config no longer requires a loaded
    case. Without a key, the choice is saved as the workspace default
    (sessions/_workspace_llm.json) and load_case copies it onto any case that has
    no active config.

    Supports two styles:
    - "api_key": classic developer key (from the provider's console)
    - "claude_code": headless Claude Code CLI mode (Claude only). No credential is
      collected — calls run through the locally installed `claude` CLI, which the
      hosting user has logged in with their Claude Team account. Usage bills
      against that subscription seat, not API credits.

    Legacy "account" configs (old token-paste flow) are still accepted and treated
    like api_key. Credentials are stored server-side only and never returned.
    """
    sess = None
    if key:
        # Best-effort: attach to the case session when it exists, but an unknown
        # key must not block the workspace-level apply.
        sess = sessions.get(key) or _load_persisted(key)

    provider = (body.get("provider") or "grok").lower().strip()
    auth_method = (body.get("auth_method") or "api_key").lower().strip()
    api_key = body.get("api_key")
    token = body.get("token")
    base_url = body.get("base_url")
    model = body.get("model")

    if provider not in ("grok", "claude", "openai"):
        provider = "grok"
    if provider == "mock":
        raise HTTPException(400, "MOCK provider removed. Use grok, claude or openai with real auth.")
    if auth_method not in ("api_key", "account", "claude_code", "claude_agent", "grok_cli", "local_llm"):
        auth_method = "api_key"
    if auth_method in ("claude_code", "claude_agent") and provider != "claude":
        raise HTTPException(400, "Claude Code modes are only available for the Claude provider.")
    if auth_method == "grok_cli" and provider != "grok":
        raise HTTPException(400, "Grok CLI (subscription) mode is only available for the Grok provider.")
    if auth_method == "local_llm":
        # The radio always pairs local_llm with openai; coerce rather than 400.
        provider = "openai"
        # Key (re-)entered on the Configure page: persist server-side, then make
        # sure it can never land in cfg / the session / the response below.
        new_key = (body.get("local_llm_key") or "").strip()
        if new_key:
            set_local_llm_key(new_key)
        api_key = None
        token = None

    # Build the config (credentials stay on server)
    cfg = LLMConfig(provider=provider, auth_method=auth_method)
    if api_key:
        cfg.api_key = api_key
    if token:
        cfg.token = token
    if base_url:
        cfg.base_url = base_url

    if model:
        cfg.model = model
    else:
        # Sensible defaults per provider
        if auth_method == "local_llm":
            cfg.model = "vllm-fast"
        elif provider == "grok" and auth_method != "grok_cli":
            cfg.model = "grok-beta"
        elif provider == "claude" and auth_method not in ("claude_code", "claude_agent"):
            cfg.model = "claude-3-5-sonnet-20241022"
        # claude_code / claude_agent / grok_cli: leave model unset so the CLI's own default is used

    # Remember as workspace default so future case loads keep this LLM choice
    _save_global_llm(cfg)

    # Also apply to the case session when one is loaded/known
    if sess:
        sess.llm_config = cfg
        _mark_updated(sess)
        _persist_session(sess)

    # Headless mode readiness comes from the CLI install, not a stored credential
    cli_status = check_claude_cli() if auth_method == "claude_code" else None
    grok_cli_status = check_grok_cli() if auth_method == "grok_cli" else None
    # local_llm readiness = a key is stored server-side (never echo the key itself)
    local_llm_key_set = bool(get_local_llm_key()) if auth_method == "local_llm" else None

    # Return safe view (no credentials)
    safe_config = {
        "provider": cfg.provider,
        "auth_method": cfg.auth_method,
        "has_key": bool(cfg.api_key or cfg.token) or
                   (auth_method == "claude_code" and bool(cli_status and cli_status.get("available"))) or
                   (auth_method == "grok_cli" and bool(grok_cli_status and grok_cli_status.get("available"))) or
                   (auth_method == "local_llm" and bool(local_llm_key_set)),
        "model": cfg.model,
        "base_url": cfg.base_url,
    }
    if cli_status is not None:
        safe_config["claude_cli"] = cli_status
    if grok_cli_status is not None:
        safe_config["grok_cli"] = grok_cli_status
    if local_llm_key_set is not None:
        safe_config["local_llm_key_set"] = local_llm_key_set

    scope = "this case and the workspace default" if sess else "the workspace default"
    result = {
        "message": f"LLM config set for {provider} (saved for {scope}).",
        "llm_config": safe_config,
    }
    if sess:
        result["session"] = safe_session_dict(sess)   # redacts llm_config secrets
    return result

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
    stored = sessions.get(key) or _load_persisted(key)
    if not stored:
        raise HTTPException(404, "Session not found. Load the case and confirm all three steps first.")
    sessions[key] = stored
    if _migrate_legacy_step4_to_step5(stored):
        _persist_session(stored)
    return stored


@router.post("/synthesize_objectives")
async def synthesize_objectives_endpoint(req: SynthesisRequest):
    """Step 4: generate Traceability gaps + objective HTML only (no test steps).

    Gate: steps 1–3 must be confirmed. User reviews/edits objective, then confirms
    before Step 5 (synthesize_steps).
    """
    key = _session_key_from_req(req)
    stored = _authoritative_session(key)
    if not _can_synthesize(stored):
        raise HTTPException(
            400,
            "Must complete and confirm reviews of all three databases (TestLink, Zephyr, ATPyLib) first.",
        )

    # Resolve config through _session_llm_cfg so the workspace LLM is applied at
    # dispatch time (guards against a stale persisted config using the wrong backend).
    llm_cfg = _session_llm_cfg(stored)
    session_dict = stored.dict() if hasattr(stored, "dict") else stored.model_dump()
    if getattr(req, "dry_run", False):
        preview = await run_in_threadpool(synthesize_objectives, session_dict, llm_config=llm_cfg, dry_run=True)
        return _preview_from(preview)
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

    _mark_updated(stored)
    _persist_session(stored)
    return {
        "phase": "objectives",
        "synthesized": result,
        "can_synthesize_steps": _can_synthesize_steps(stored),
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/save_objective/{key}")
async def save_objective(key: str, body: dict = Body(default={})):
    """Persist edited objective HTML from Step 4 (before or as part of confirm)."""
    body = body or {}
    stored = sessions.get(key) or _load_persisted(key)
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
    # clears any staleness flagged by _invalidate_downstream after an upstream change.
    s4.pop("stale", None)
    # Edits invalidate prior confirm until re-confirmed
    if body.get("confirm"):
        s4["confirmed"] = True
        s4["confirmed_at"] = datetime.utcnow().isoformat()
    else:
        # Keep prior confirmed only if body explicitly keeps it; default re-open review
        if "confirm" in body and not body.get("confirm"):
            s4["confirmed"] = False
            s4["confirmed_at"] = None
    stored.step4 = s4
    _mark_updated(stored)
    _persist_session(stored)
    return {
        "message": "Objective saved" + (" and confirmed" if s4.get("confirmed") else ""),
        "can_synthesize_steps": _can_synthesize_steps(stored),
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/confirm_objectives/{key}")
async def confirm_objectives(key: str, body: dict = Body(default={})):
    """Mark Step 4 objective as finalized (optional body.objective overwrites)."""
    body = body or {}
    stored = sessions.get(key) or _load_persisted(key)
    if not stored:
        raise HTTPException(404, "Session not found.")
    sessions[key] = stored
    s4 = dict(stored.step4 or {})
    if body.get("objective"):
        s4["objective"] = sanitize_objective_html((body.get("objective") or "").strip())
    if not (s4.get("objective") or "").strip():
        raise HTTPException(400, "No objective to confirm. Run Objective Synthesis first.")
    s4["confirmed"] = True
    s4["confirmed_at"] = datetime.utcnow().isoformat()
    # An explicit re-confirm is the user asserting this objective matches the CURRENT
    # selections, so it clears any staleness flagged by _invalidate_downstream.
    s4.pop("stale", None)
    stored.step4 = s4
    _mark_updated(stored)
    _persist_session(stored)
    return {
        "message": "Objectives confirmed — proceed to Step 5 (Test Step Synthesis).",
        "can_synthesize_steps": True,
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }


@router.post("/save_steps/{key}")
async def save_steps(key: str, body: dict = Body(default={})):
    """Persist edited testScript steps from Step 5 editor."""
    body = body or {}
    stored = sessions.get(key) or _load_persisted(key)
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
    # Deliberate edit against the current selections — clears _invalidate_downstream's flag.
    s5.pop("stale", None)
    stored.step5 = s5
    # Mirror onto step4 for legacy consumers / combined view
    s4 = dict(stored.step4 or {})
    s4["testScript"] = test_script
    stored.step4 = s4
    _mark_updated(stored)
    _persist_session(stored)
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
    if not _can_synthesize(stored):
        raise HTTPException(
            400,
            "Must complete and confirm reviews of all three databases first.",
        )
    if not _session_has_objective(stored):
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
    if client_obj and client_obj != _session_objective(stored):
        s4 = dict(stored.step4 or {})
        s4["objective"] = sanitize_objective_html(client_obj)
        stored.step4 = s4

    llm_cfg = _session_llm_cfg(stored)  # applies workspace LLM at dispatch time
    session_dict = stored.dict() if hasattr(stored, "dict") else stored.model_dump()
    if getattr(req, "dry_run", False):
        preview = await run_in_threadpool(
            synthesize_steps, session_dict, llm_config=llm_cfg,
            objective=_session_objective(stored), dry_run=True)
        return _preview_from(preview)
    try:
        result = await run_in_threadpool(
            synthesize_steps,
            session_dict,
            llm_config=llm_cfg,
            objective=_session_objective(stored),
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

    _mark_updated(stored)
    _persist_session(stored)
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
    if not _can_synthesize(stored):
        raise HTTPException(
            400,
            "Must complete and confirm reviews of all three databases (TestLink, Zephyr, ATPyLib) first. This gate is enforced server-side per the repeatable process.",
        )

    llm_cfg = _session_llm_cfg(stored)  # applies workspace LLM at dispatch time
    session_dict = stored.dict() if hasattr(stored, "dict") else stored.model_dump()
    result = await run_in_threadpool(synthesize_objectives_and_steps, session_dict, llm_config=llm_cfg)

    stored.step4 = {
        "objective": result.get("objective"),
        "testScript": result.get("testScript"),
        "provenance": result.get("provenance"),
        "confirmed": True,
        "confirmed_at": datetime.utcnow().isoformat(),
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
    _mark_updated(stored)
    _persist_session(stored)

    return {
        "phase": "combined",
        "synthesized": result,
        "session": safe_session_dict(stored),   # redacts llm_config secrets
    }

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
    if not _CASE_KEY_RE.match(key):
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

    # ...and gate on the three DB reviews, matching synthesize_objectives (1669),
    # synthesize_steps (1818) and synthesize (1890). Without this, hand-pasting an
    # objective + steps (save_objective/save_steps have no gate either) let an
    # unreviewed case be written as Complete and become push-eligible — bypassing
    # the exact three-review gate the drafting process mandates. Backfilled cases
    # satisfy this via _backfill_from_refined, which marks the reviews confirmed
    # from the Complete on-disk bundle.
    if not _can_synthesize(stored):
        # A case that is Complete on disk should have been rehydrated by
        # _backfill_from_refined. If it wasn't, the bundle itself is unreadable
        # (e.g. AWPTCM-T37861 ships invalid JSON — a bad \' escape), and blaming the
        # user for unconfirmed reviews would be misleading and unactionable. Name the
        # real cause instead.
        _payload = _refined_payload_path(key)
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

    # Normalize to dict for easy access + context building
    if hasattr(stored, "dict"):
        sess_dict = stored.dict()
    elif isinstance(stored, dict):
        sess_dict = stored
    else:
        sess_dict = getattr(stored, "model_dump", lambda: {})()

    case_key = key or sess_dict.get("key", "unknown")
    # Defense in depth: `key` was already shape-checked at the top of the handler, but
    # case_key can also come from the stored session, so re-validate whatever will
    # actually be used as the path component — before the LLM gaps call, payload
    # validation, or any write.
    if not _CASE_KEY_RE.match(case_key or ""):
        raise HTTPException(400, f"Refusing to export: invalid case key '{case_key}'. "
                                 f"Expected AWPTCM-Txxxx.")
    step4 = sess_dict.get("step4", {}) or {}
    step5 = sess_dict.get("step5", {}) or {}

    # Gaps belong in Traceability and are LLM-generated at objective synthesis/export,
    # not collected as a Step 3 form field. Apply the workspace LLM at dispatch time
    # so the coverage-gaps call uses the configured backend, not the default.
    # (`stored` is always the authoritative server session now — never req.session.)
    if hasattr(stored, "llm_config") and _apply_workspace_llm_if_needed(stored):
        _mark_updated(stored)
        _persist_session(stored)
        sess_dict["llm_config"] = stored.llm_config.dict() if hasattr(stored.llm_config, "dict") else stored.llm_config
    llm_cfg = sess_dict.get("llm_config", {}) if isinstance(sess_dict, dict) else {}
    if not (sess_dict.get("gaps") or "").strip():
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
                    _mark_updated(stored)
                    _persist_session(stored)
                except Exception:
                    pass

    # Rebuild the testScript with authoritative server-constructed repeatable note as first step.
    # Prefer Step 5 testScript; fall back to legacy step4.testScript.
    # Client edits to later steps are respected; only the first note step is forced.
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
    test_script = {"type": "steps", "steps": steps}

    objective = (step4.get("objective") if isinstance(step4, dict) else None) or "<ul><li>Objective not yet synthesized</li></ul>"
    objective = sanitize_objective_html(objective)   # defense-in-depth on the exported artefact

    # Derive art_string for payload if not present (repeatable from selections)
    if not sess_dict.get("art_string"):
        atp_ids = [s.get("id_or_key") or s.get("id", "") for s in (sess_dict.get("step3", {}).get("selections") or []) if s]
        if atp_ids:
            sess_dict["art_string"] = " + ".join(atp_ids[:6])  # cap for cleanliness

    # Exact shape matching real refined-cases examples
    zephyr_payload = {
        case_key: {
            "objective": objective,
            "testScript": test_script
        }
    }

    # Run full validation (strengthened for complete output generation)
    validation = validate_zephyr_payload(zephyr_payload)
    if not validation.get("valid"):
        print(f"[export] Validation issues for {case_key}: {validation.get('issues')}")
    for w in validation.get("warnings", []):
        print(f"[export] Warning: {w}")

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

    # Full session out for audit/provenance (repeatable). REDACTED: this is written to
    # {case_key}-session.json under refined-cases/ (and returned to the browser), so the
    # llm_config api_key/token must be masked — otherwise a credential lands on disk in a
    # directory that can be committed. The live server-side session keeps the real key.
    session_out = safe_session_dict(stored if not isinstance(stored, dict) else stored)

    # Primary destination: write drop-in artefacts under refined-cases/ (server path).
    # Browser downloads are intentional only if the client asks; default UX is server-side only.
    saved_to = None
    saved_files: List[str] = []
    export_message = ""
    wrote_bundle = False

    # HARDENING (backlog: output-generation): the drop-in bundle is exactly what marks a case
    # "Complete" (refined-cases/**/zephyr_payload.json). If the payload fails hard validation,
    # refuse to write it — a silently-broken bundle promoting a case to Complete is the failure
    # mode this guards. Warnings do NOT block (they're advisory). The client is handed the
    # validation detail so it can show WHY nothing was written.
    if not validation.get("valid"):
        issues = validation.get("issues") or ["unknown validation failure"]
        # Be precise about state (adversarial-review findings): the guard only prevents
        # WRITING a new/overwritten drop-in bundle — it does not remove one already on disk.
        # A case that was exported successfully before is STILL Complete (Complete is keyed
        # off refined-cases/**/zephyr_payload.json existing), and push_to_zephyr operates on
        # that on-disk bundle. So don't claim "NOT Complete" unconditionally; say what's true.
        stale_bundle_exists = _refined_payload_path(case_key) is not None
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
        print(f"[export] BLOCKED for {case_key} (stale_bundle={stale_bundle_exists}): {issues}")
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

    # SECURITY (adversarial-review finding): case_key comes from the client-supplied
    # session and is used as a directory component of the on-disk write path, so a value
    # like '../../etc/x' would escape refined-cases/. Validate it against the canonical
    # AWPTCM-Txxxx shape before ANY filesystem write. (push_to_zephyr already does this;
    # the export write path did not.)
    # (case_key was already validated against _CASE_KEY_RE at the top of the handler.)
    # Resolve the target dir and confirm it stays inside refined-cases/ BEFORE the write
    # try-block (whose broad `except Exception` would otherwise soften a 400 into a
    # "failed to write" message). Defends against a manipulated folder-derived `group`.
    _export_group = _get_refined_group(case_key, data)
    _export_target = REFINED_DIR / _export_group / case_key
    if REFINED_DIR.resolve() not in _export_target.resolve().parents:
        raise HTTPException(400, "Refusing to export outside refined-cases/.")

    try:
        group = _export_group
        # Post-restructure (2026-07-13) refined-cases live under
        # ask-ck/objective-drafting/refined-cases/ — use the REFINED_DIR anchor
        # from paths.py, matching _get_refined_group and _refined_complete_keys.
        refined_root = REFINED_DIR
        target_dir = refined_root / group / case_key
        target_dir.mkdir(parents=True, exist_ok=True)

        # PARTIAL-WRITE (adversarial-review finding wizard.py:2166): zephyr_payload.json
        # is the Complete marker (_refined_complete_keys keys off its existence) and it
        # used to be written SECOND of three, with the largest, most failure-prone write
        # (the session dump, which carries full LLM provenance) last. A disk-full or
        # encoding error on that third write left the case marked Complete and
        # push-eligible while the API reported wrote_bundle=False — a lying signal.
        #
        # Now: serialize everything up front (so a serialization error fails before any
        # file is touched), stage each file as a .tmp sibling, then os.replace them into
        # place — payload LAST, so the Complete marker is the final commit point. Any
        # failure unlinks the staged temp files and leaves the case not-Complete.
        files_written = [
            ("traceability.md", traceability_md),
            (f"{case_key}-session.json", json.dumps(session_out, indent=2, default=str)),
            ("zephyr_payload.json", json.dumps(zephyr_payload, indent=2)),
        ]
        staged: List[tuple] = []
        try:
            for name, content in files_written:
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

        # Prefer repo-relative path for display (portable across machines).
        # ASKCK_ROOT.parent is the Test-cases repo root.
        try:
            saved_to = str(target_dir.relative_to(ASKCK_ROOT.parent))
        except ValueError:
            saved_to = str(target_dir)
        wrote_bundle = True
        export_message = f"Saved drop-in bundle to {saved_to}/"
        print(f"[export] {export_message}")
    except Exception as e:
        export_message = f"Failed to write to refined-cases: {e}"
        print(f"[export] {export_message}")

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


# Case keys are AWPTCM-Txxxx; validate before passing to the subprocess.
_CASE_KEY_RE = re.compile(r"^AWPTCM-T\d+$")


@router.post("/push_to_zephyr/{key}")
async def push_to_zephyr(key: str, dry_run: bool = True, force: bool = False):
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
    """
    if not _CASE_KEY_RE.match(key or ""):
        raise HTTPException(status_code=400, detail="invalid case key")

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
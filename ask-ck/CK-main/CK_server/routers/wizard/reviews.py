"""Generator review gates — the step 1/2/3 endpoints and case listing.

load_case / get_cases / step_candidates, TestLink (step 1), Zephyr (step 2) and ATPyLib
(step 3) candidate search, the per-step LLM suggestion endpoints, and confirm_step. Split
out of the monolithic routers/wizard.py (PLAN-backend-module-split.md commit 10).
"""
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

import db
import locks
from models import Selection, WizardSession, model_to_dict, safe_session_dict
from timeutil import utc_now
from case_registry import (
    build_case_groups,
    is_hidden_case,
    refined_complete_keys,
    session_progress_map,
)
from llm import (
    suggest_relevant_atp,
    suggest_relevant_testlink,
    suggest_relevant_zephyr,
)
from llm_config import apply_workspace_llm, preview_from
from session_store import load_persisted, mark_updated, persist_session, sessions
from generator.backfill import backfill_from_refined
from generator.gates import (
    can_synthesize,
    invalidate_downstream,
    migrate_legacy_step4_to_step5,
    selection_fingerprint,
)
# Import the NAMES, not the module. The AST invariant in
# tests/test_event_loop_blocking_batch_b.py matches an unwrapped blocking call by
# `ast.Name`, so calling these as `descriptions.get_atp_candidates(...)` would pass
# the check without being covered by it — a silent loss of the threadpool guarantee.
from generator.descriptions import (
    build_atp_query,
    build_testlink_description,
    enrich_zephyr_rows,
    get_atp_candidates,
    hybrid_on,
    zephyr_tokens,
)

from ._shared import get_data

router = APIRouter()

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
    # Per-case lock (PLAN-auth-and-case-locking.md Phase 1). Acquire for this tab; if
    # another tab/user holds a LIVE lock we do NOT acquire (by_me=False) and serve a
    # read-only view (D6a).
    lock = locks.acquire("wizard", key)
    zm = data.get("zephyr_master", {}) or {}
    case_title = (zm.get(key, {}) or {}).get("title", "") if key else ""

    if not lock["by_me"]:
        # Read-only: someone else is editing. Serve a snapshot of the LAST SAVED state
        # and touch NOTHING — the holder's live in-memory object is shared across tabs in
        # this one process, so backfill/apply_workspace_llm here would mutate THEIR work.
        # No hydration persist either (it would 409 against their lock).
        snap = load_persisted(key)
        if snap is None and key not in zm:
            raise HTTPException(404, "Case not found")
        return {
            "session": safe_session_dict(snap or WizardSession(key=key)),
            "case_title": case_title,
            "lock": lock,
            "read_only": True,
            "message": f"'{key}' is being edited in the Generator by {lock['holder_label']} "
                       f"(since {lock['acquired_at']}). You are viewing it read-only.",
        }

    # We hold the lock — normal load.
    sess = sessions.get(key) or load_persisted(key)
    if sess:
        sessions[key] = sess
        if migrate_legacy_step4_to_step5(sess):
            mark_updated(sess)
    else:
        if key not in zm:
            locks.release("wizard", key)   # don't strand a lock on a non-existent case
            raise HTTPException(404, "Case not found")
        sess = WizardSession(key=key)
        # Populate primary decision (cross-ref from data/decisions)
        primary = data.get("decisions", {}).get(key)
        if primary:
            sess.primary = {"m": primary.get("m"), "c": primary.get("c"), "w": primary.get("w")}
        sessions[key] = sess

    # Rehydrate a Complete case whose runtime session lost step4/step5 from the
    # canonical on-disk payload, so the UI reflects the finished objective + steps.
    if backfill_from_refined(sess):
        mark_updated(sess)

    # Carry over workspace LLM preference (last Apply / Login) so switching cases
    # does not reset provider / CLI mode back to empty defaults.
    if apply_workspace_llm(sess):
        mark_updated(sess)

    persist_session(sess)

    return {
        "session": safe_session_dict(sess),   # redacts llm_config secrets
        "case_title": case_title,
        "lock": lock,
        "read_only": False,
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
        rich_desc = (build_testlink_description(full, title=title)
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
    q = build_atp_query(sess, case_title=case_title) if sess else (case_title or key or "")
    raw = get_atp_candidates(q, data, limit=18, mode=_STEP_SEARCH_MODE)

    rows: List[Dict[str, Any]] = []
    seen_ids = set()
    for c in raw:
        cid = c.get("id")
        if not cid or cid in seen_ids:
            continue
        full_desc = (c.get("description") or "").strip()
        short_title = (c.get("title") or "").strip()
        if not short_title or short_title == full_desc:
            short_title, full_desc = db.split_atp_title_description(
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

    sess = sessions.get(key) or load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Load the case first.")
    sessions[key] = sess

    zm = data.get("zephyr_master", {}) or {}
    case_title = (zm.get(key, {}) or {}).get("title", "") or ""
    candidates = await run_in_threadpool(builder, key, sess, data, case_title)
    return {"key": key, "step": step, "kind": kind, "candidates": candidates}


def _cases_index() -> Tuple[set, Dict[str, dict]]:
    """(complete_keys, per-case progress) — the two blocking reads /cases needs.

    Paired in one helper so the handler makes a single threadpool hop, and named so
    the event-loop AST invariant can see what is being dispatched.
    """
    return refined_complete_keys(), session_progress_map()


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
                and not is_hidden_case(c["key"], zephyr.get(c["key"], {}).get("folder", ""))]

    # Off the event loop: refined_complete_keys rglob's the whole refined-cases tree
    # (measured ~14ms) and session_progress_map hits ck.db. Small next to the Step-2
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
        for grp in build_case_groups(not_started_keys, zephyr):
            incomplete_grouped.append({
                "label": f"Not started — {grp['label']}",
                "cases": grp["cases"],
                "bucket": "not_started",
            })

    complete_grouped = build_case_groups(complete_keys, zephyr)
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
        get_atp_candidates, q, data, limit=20, keep_ids=keep, mode=mode)
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


def _search_testlink(q: str, data: dict, limit: int = 20,
                     keep_ids: Optional[set] = None, mode: str = "") -> List[Dict[str, Any]]:
    """Keyword (or hybrid) search over TestLink. Ranking delegates to db; the
    description is re-enriched with full step text for the UI (Commit B/D)."""
    keep = keep_ids or set()
    rows = (db.search_testlink_hybrid(q, keep_ids=keep, limit=limit) if hybrid_on(mode)
            else db.search_testlink(q, keep_ids=keep, limit=limit))
    for r in rows:
        full = data.get("testlink", {}).get(r["id"]) or {}
        rich = build_testlink_description(full, title=r.get("title") or "")
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
    + primary key. Full descriptions filled by descriptions.enrich_zephyr_rows."""
    current_cases = {
        c["key"] for c in data.get("candidates", []) or []
        if c.get("candidates")
    }
    if case_key:
        current_cases.add(case_key)
    keep = keep_ids or set()
    if hybrid_on(mode):
        rows = db.search_zephyr_hybrid(q, case_key=case_key, exclude_keys=current_cases,
                                       keep_ids=keep, limit=limit)
    else:
        rows = db.search_zephyr(q, case_key=case_key, exclude_keys=current_cases,
                                keep_ids=keep, limit=limit)
    return enrich_zephyr_rows(rows, data)


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

    # Deliberately does NOT strip db.GENERIC_TOKENS. db.search_zephyr does its own
    # specific/generic split, and since the area tier was added it NEEDS the generic
    # words present to derive area affinity — pre-filtering them here made "port"
    # invisible to db and left the best cross-ref for "Port - Auto Negotiation"
    # stranded at rank 9 of a 12-way tie. Division of labour: this function decides
    # which TEXT is relevant (drop analyst process-prose, ids, bare numbers); db
    # decides how to WEIGHT it (specific / area / ignored).
    toks = [t for t in zephyr_tokens(" ".join(parts))
            if t not in _DECISION_META_TOKENS
            and not t.isdigit() and not t.startswith("awp")]
    # De-dupe while preserving order so a word repeated across parts does not eat
    # the token budget.
    seen: set = set()
    ordered = [t for t in toks if not (t in seen or seen.add(t))]
    return " ".join(ordered[:24])


@router.post("/suggest_atp/{key}")
async def suggest_atp(key: str, body: dict = Body(default={}), data=Depends(get_data)):
    """Use LLM to analyze current session selections and pre-select relevant ATPyLib tests.
    Returns suggestions for the user to review/approve in Step 3.
    """
    body = body or {}
    sess = sessions.get(key) or load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Load the case first.")

    # Build smart query and retrieve candidates
    q = body.get("q") or build_atp_query(sess)
    # Off the event loop — see search_testlink.
    candidates = await run_in_threadpool(get_atp_candidates, q, data, limit=25)

    # Call LLM for selection. _session_llm_cfg applies the workspace LLM at dispatch
    # time so this respects the configured backend even if the session's persisted
    # config is stale/inactive.
    llm_cfg = _session_llm_cfg(sess)
    dry_run = bool(body.get("dry_run"))
    result = await run_in_threadpool(
        suggest_relevant_atp,
        model_to_dict(sess),
        candidates,
        llm_config=llm_cfg,
        dry_run=dry_run,
    )
    if dry_run:
        return preview_from(result)
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
        short_title, full_desc = db.split_atp_title_description(
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
    if apply_workspace_llm(sess):
        mark_updated(sess)
        persist_session(sess)
    return model_to_dict(getattr(sess, "llm_config", None))


@router.post("/suggest_testlink/{key}")
async def suggest_testlink(key: str, body: dict = Body(default={}), data=Depends(get_data)):
    """LLM pre-select TestLink cases for Step 1 (user reviews/approves)."""
    body = body or {}
    sess = sessions.get(key) or load_persisted(key)
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
                "description": build_testlink_description(full, title=title)
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
        model_to_dict(sess),
        candidates,
        llm_config=_session_llm_cfg(sess),
        case_title=case_title,
        dry_run=dry_run,
    )
    if dry_run:
        return preview_from(result)
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
            or build_testlink_description(full, title=title)
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
    sess = sessions.get(key) or load_persisted(key)
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
        model_to_dict(sess),
        candidates,
        llm_config=_session_llm_cfg(sess),
        case_title=case_title,
        dry_run=dry_run,
    )
    if dry_run:
        return preview_from(result)
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
    enriched = enrich_zephyr_rows(draft, data)
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


def _selection_problem(exc: Exception) -> str:
    """One short, actionable line describing why a Selection failed to build."""
    errors = getattr(exc, "errors", None)
    if callable(errors):
        try:
            parts = []
            for d in list(exc.errors())[:3]:
                loc = ".".join(str(x) for x in (d.get("loc") or ())) or "?"
                parts.append(f"{loc}: {d.get('msg')}")
            if parts:
                return ", ".join(parts)
        except Exception:
            pass
    return f"{type(exc).__name__}: {exc}"[:160]


def _parse_selections(raw: Any, step: int) -> List[Selection]:
    """Validate one step's `selections` payload, or 400 explaining what was wrong.

    This used to be `except Exception: pass`, repeated once per step. That was a
    silent data-loss bug, not merely lax input handling: a single malformed entry
    made the WHOLE list-comprehension raise, the assignment never happened, the
    session silently kept its PREVIOUS selections — and then the handler set
    `confirmed = True` and returned `can_synthesize: true` regardless. The user was
    told the confirm succeeded, then synthesized an objective against selections
    they had just replaced. Same family as 9afdf97's silent session data-loss bug.

    Rejecting the whole payload (rather than keeping the good entries) is deliberate:
    a partial confirm is exactly the silent divergence being fixed. Nothing is
    mutated before this returns, so a 400 leaves the session untouched.

    Cannot fire on the normal UI path: chosen.js `toEntry` always supplies
    `id_or_key` and a `title` that falls back to the id, and the browser sends only
    those four fields. The frontend already surfaces `detail` via
    `alert("Confirm failed: …")`.
    """
    if not isinstance(raw, list):
        raise HTTPException(
            400, f"step {step}: 'selections' must be a list, got "
                 f"{type(raw).__name__}. Nothing was confirmed.")

    parsed: List[Selection] = []
    problems: List[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            problems.append(f"[{i}] expected an object, got {type(item).__name__}")
            continue
        try:
            parsed.append(Selection(**item))
        except Exception as e:
            problems.append(f"[{i}] {_selection_problem(e)}")

    if problems:
        shown = "; ".join(problems[:5])
        more = f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""
        raise HTTPException(
            400, f"step {step}: {len(problems)} of {len(raw)} selection(s) are invalid, "
                 f"so NOTHING was confirmed and the step's previous selections are "
                 f"unchanged. {shown}{more}")
    return parsed


@router.post("/confirm_step/{key}/{step}")
async def confirm_step(key: str, step: int, body: dict, data=Depends(get_data)):
    """Store user selections + set the confirmed flag for the step.
    This is the explicit confirmation action required by the repeatable process
    (see OBJECTIVE_DRAFTING_PROCESS.md Step 1 user-review pause + SERVER-README).
    Selections are captured server-side for use in templated LLM prompts.

    The three steps were three near-identical branches; they are one path now. The
    only real per-step differences are step 1's `none_selected` and step 3's
    `art_string`, both kept verbatim below.
    """
    if step not in (1, 2, 3):
        # Checked FIRST: previously this lived in a trailing `else`, so an invalid
        # step fell past every branch before 400ing. Harmless as written, but it put
        # the guard after the work it guards.
        raise HTTPException(400, "Invalid step")

    sess = sessions.get(key) or load_persisted(key)
    if not sess:
        raise HTTPException(404, "Session not found. Call load_case first.")
    sessions[key] = sess

    # Snapshot the pre-confirm selections so we can tell an actual change from a
    # harmless re-confirm of the same shortlist (see invalidate_downstream below).
    _before = selection_fingerprint(sess, step)

    # Validate BEFORE mutating anything, so a rejected payload cannot leave the
    # session half-updated or wrongly marked confirmed.
    new_selections = (_parse_selections(body["selections"], step)
                      if "selections" in body else None)

    state = getattr(sess, f"step{step}")
    if new_selections is not None:
        state.selections = new_selections
    if step == 1:
        # Only step 1 reads `none`; the browser never sends it (generator.js
        # confirmStep posts `selections` only), so this serves API callers.
        state.none_selected = bool(body.get("none", False))
    state.confirmed = True
    state.confirmed_at = utc_now()

    if step == 3:
        # Gaps are LLM-generated at synthesis/export for Traceability — not user-edited in Step 3
        if "art_string" in body:
            sess.art_string = body.get("art_string", "")
        # Auto-build ART string from confirmed ATP selections when not provided
        if not sess.art_string and sess.step3.selections:
            ids = [s.id_or_key for s in sess.step3.selections if s.id_or_key]
            if ids:
                sess.art_string = " + ".join(ids[:8])

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
    invalidated = invalidate_downstream(sess, changed=(selection_fingerprint(sess, step) != _before))

    mark_updated(sess)
    persist_session(sess)

    return {
        "session": safe_session_dict(sess),   # redacts llm_config secrets
        "can_synthesize": can_synthesize(sess),
        "invalidated": invalidated,
    }



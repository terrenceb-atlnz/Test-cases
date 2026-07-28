"""The Generator's state machine: what a session is allowed to do next.

Seven pure predicates over a `WizardSession`. Together they are the whole reason the
Generator is a gated wizard rather than a form: synthesis cannot run before the three DB
reviews are confirmed, test steps cannot run before an objective exists, and re-confirming
an upstream review with DIFFERENT selections has to invalidate what was generated from the
old ones.

Extracted from `routers/wizard.py` (PLAN-backend-module-split.md commit 9). They read
session state and return a verdict — no I/O, no db, no fastapi — so they are directly
unit-testable, which they were not while they lived in a router module.

The `isinstance(sess.step4, dict)` guards throughout are load-bearing, not defensive
noise. `step4`/`step5` are untyped `Dict[str, Any]` and MUST stay that way: SURVEY-step4-
step5.md measured what happens if they become pydantic models — a model is not a dict, so
every one of these guards silently takes its `else` branch and the invalidation cascade
below stops firing, with the whole test suite still green. Commit 6 was dropped for exactly
this. Do not "tidy" these guards away.

Two helpers the plan expected here do not exist: `_session_objectives_confirmed` and
`_session_test_script` were born unused in 05b194a and deleted in commit 4. Do not re-add
them — tests/test_pydantic_v2_and_logging.py asserts they stay gone.
"""

from models import WizardSession


def can_synthesize(sess: WizardSession) -> bool:
    """Gate for objective synthesis (Step 4). Must confirm all three DB reviews first."""
    return bool(sess.step1.confirmed and sess.step2.confirmed and sess.step3.confirmed)


def session_objective(sess: WizardSession) -> str:
    """Finalized objective HTML from Step 4 (or legacy combined step4)."""
    s4 = sess.step4 or {}
    if isinstance(s4, dict):
        return (s4.get("objective") or "").strip()
    return ""


def session_has_objective(sess: WizardSession) -> bool:
    return bool(session_objective(sess))


def can_synthesize_steps(sess: WizardSession) -> bool:
    """Gate for Step 5: reviews confirmed + finalized objective present.

    Prefer objectives marked confirmed (user applied Step 4); allow unconfirmed
    objective if present so re-runs after synthesize_objectives still work when
    the user proceeds without an extra click (UI still prompts to confirm).
    """
    if not can_synthesize(sess):
        return False
    return session_has_objective(sess)


def selection_fingerprint(sess: WizardSession, step: int) -> tuple:
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


def invalidate_downstream(sess: WizardSession, changed: bool) -> dict:
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


def migrate_legacy_step4_to_step5(sess: WizardSession) -> bool:
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

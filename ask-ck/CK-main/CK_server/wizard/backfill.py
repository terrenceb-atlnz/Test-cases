"""Rehydrating a session from the Complete bundle already on disk.

A case is Complete when `refined-cases/<Group>/<KEY>/zephyr_payload.json` exists. Some of
those were refined before the runtime session captured step4/step5, and others had their
session cleared afterwards — so the Generator would open a finished case showing "No
objective yet". Worse, exporting from that state would overwrite a good payload with empty
fallback content, and the export confirm gate would 400 on reviews the user demonstrably
did (all 43 existing bundles).

So the payload is treated as the source of truth for those two fields, and the three
reviews are marked confirmed-by-backfill to match what the on-disk artefact proves.
`backfilled` on each step keeps that distinguishable from a fresh in-session confirm.

Extracted from `routers/wizard.py` (PLAN-backend-module-split.md commit 9).

One thing to know before editing: this is an UNVALIDATED read of on-disk JSON.
`testScript` is copied verbatim into the session. It is acceptable because all 43 payloads
are uniform (276/276 steps exactly `{description, expectedResult}`) and the server writes
them itself — and it is the deliberate outcome of dropping commit 6 with no boundary
validator. If a malformed bundle ever surfaces, this is the first place to look.
"""

import json
import logging

from case_registry import refined_payload_path
from html_sanitize import sanitize_objective_html
from models import WizardSession
from timeutil import utc_now

log = logging.getLogger(__name__)


def backfill_from_refined(sess: WizardSession) -> bool:
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

    path = refined_payload_path(sess.key)
    if not path:
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("[backfill] could not read %s: %s", path, e)
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
    # export() now gates on can_synthesize, so without this the 43 existing bundles
    # would 400 on re-export ("confirm all three reviews") for reviews the user
    # already did. Mark the reviews confirmed-by-backfill so the gate reflects the
    # on-disk truth; `backfilled` distinguishes them from fresh in-session confirms.
    if changed:
        for step in (sess.step1, sess.step2, sess.step3):
            if not step.confirmed:
                step.confirmed = True
                step.confirmed_at = step.confirmed_at or utc_now()
                step.backfilled = True

    return changed

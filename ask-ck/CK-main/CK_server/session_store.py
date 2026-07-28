"""Where a Generator session lives: the in-memory cache and its ck.db row.

Sessions have two homes and both matter. `sessions` is a per-process dict so a request
does not re-read the DB, and `ck.db` (kind='wizard') is what survives a restart. Every
read/write of the persistent half goes through the four functions here.

Extracted from `routers/wizard.py` (PLAN-backend-module-split.md commit 9). Framework-free
on purpose — no fastapi import — so it can be unit-tested and used by tool/ scripts, the
same rule `db.py` states for itself. The HTTP-shaped wrapper that turns "no session" into
a 404 (`_authoritative_session`) deliberately stays in the router; see the deviation note
below.

**This is where per-case locking lands.** `sessions` is a global mutable dict with no
locking, and two browser tabs on one case can silently overwrite each other TODAY. That is
owned by `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` Phase 1 — do not re-raise it
elsewhere, and put the fix here rather than in a router.

--- Two deviations from the plan, both measured rather than assumed -------------------

1. **NOT made generic over kind='wizard'|'pt', and pytest_create is NOT rewired to it.**
   The plan expected one shared store. The two are not the same function:

   * `pytest_create._pt_persist` **raises HTTPException(500)** on a failed write; this
     module's `persist_session` **swallows and logs ERROR**. Both are deliberate and
     recorded — the pt side was changed to raise precisely because a 200 with no write
     had made "never trust the 200" a documented workaround.
   * `pytest_create._pt_get` compares the cached session's `updated_at` against the DB
     and reloads when the DB is ahead, so a stale process cannot clobber newer work.
     There is no wizard equivalent.

   Merging them would therefore be a behaviour CHANGE in one direction or the other,
   wearing a refactor's clothes. Left as two, with the asymmetry stated here so it is a
   decision rather than an accident.

2. **`_authoritative_session` stayed in the router.** It raises HTTPException(404), so
   moving it would drag fastapi into this leaf and cost the framework-free property that
   makes the rest of it testable. It is an HTTP gate, not storage.
"""

import logging
from typing import Dict, Optional

import db
from models import WizardSession, model_to_dict
from timeutil import utc_now

log = logging.getLogger(__name__)

# The kind discriminator on the ck.db `sessions` table. pytest_create uses 'pt' through
# its own layer (see deviation 1 above).
KIND = "wizard"

# In-memory sessions (replace with DB later). File persistence added for restart survival.
sessions: Dict[str, WizardSession] = {}


def persist_session(sess: WizardSession) -> None:
    """Persist full session (confirmed flags + selections + step4/5) to ck.db
    (Commit C). llm_config is split into its own column by db.save_session. The
    old sessions/{key}.json file stays in place as a frozen pre-migration backup."""
    sess.updated_at = utc_now()
    try:
        data = model_to_dict(sess)
        db.save_session(KIND, sess.key, data)
    except Exception:
        # ERROR, not warning: a swallowed failure here loses the user's confirmed
        # selections and objective while the handler still returns 200. This is the
        # wizard-side twin of the known stale-thread-local-connection bug, where the
        # write silently never reaches ck.db. Keep the traceback — the message alone
        # ("database is locked", "no such table") does not say which caller lost data.
        log.error("failed to persist session %s — CHANGES WERE LOST", sess.key, exc_info=True)


def load_persisted(key: str) -> Optional[WizardSession]:
    """Restore persisted session from ck.db (restart survival / authoritative state)."""
    try:
        raw = db.load_session(KIND, key)
        if raw is not None:
            return WizardSession(**raw)
    except Exception:
        # Traceback matters: the usual cause is a stored row that no longer validates
        # against WizardSession, and only the pydantic error names the offending field.
        log.warning("failed to load persisted session %s", key, exc_info=True)
    return None


def clear_persisted(key: str) -> None:
    """Delete the persisted session row for a key."""
    try:
        db.delete_session(KIND, key)
        log.info("cleared persisted session for %s", key)
    except Exception as e:
        log.warning("failed to delete session for %s: %s", key, e)


def mark_updated(sess: WizardSession) -> None:
    sess.updated_at = utc_now()

"""UTC time helpers — one source of truth for "now" and for reading stored stamps.

WHY THIS MODULE EXISTS
----------------------
`datetime.utcnow()` is deprecated from Python 3.12 (removal scheduled) and, more
importantly, returns a **naive** datetime that merely happens to hold UTC. Naive and
aware datetimes cannot be compared — mixing them raises TypeError — so a codebase that
produces naive stamps in one place and aware ones in another has a latent crash.

`ck.db` already holds stamps written by `datetime.utcnow()`, in two shapes:

  * `sessions.updated_at` column — `isoformat()`      -> "2026-07-28T12:00:00.123456"
  * datetimes inside the JSON `payload`               -> "2026-07-28 12:00:00.123456"
    (space separator, because `db.save_session` uses `json.dumps(..., default=str)`)

Neither carries an offset. `as_utc` interprets such a value as **UTC**, which is what it
always meant; reading it as local time would silently shift every pre-cutover timestamp
by the seat's offset.

PREFER PARSING OVER STRING COMPARISON. A naive stamp is a strict PREFIX of its own aware
form ("…T12:00:00" vs "…T12:00:00+00:00"), so a lexicographic compare reports the aware
side as newer at the identical instant.

Measured, rather than assumed: over the shapes the `sessions.updated_at` column can
actually hold, string comparison and `as_utc` comparison agree on all 8 reachable
combinations **provided the in-memory stamp is aware** — which `models.UtcDatetime`
guarantees. Drop that coercion and exactly one combination diverges (aware column stamp
vs naive cached stamp at the same instant reads as "DB is newer", reloading on every
request). So `_pt_get` parsing both sides is defence-in-depth, not a live bug fix: its
value is that correctness no longer depends on re-deriving that argument each time a
stored format changes, and it holds for the space-separated payload shape and non-UTC
offsets too, where string ordering genuinely inverts.
"""
from datetime import datetime, timezone
from typing import Any, Optional

__all__ = ["utc_now", "as_utc"]


def utc_now() -> datetime:
    """Timezone-aware current UTC time. The replacement for `datetime.utcnow()`."""
    return datetime.now(timezone.utc)


def as_utc(value: Any) -> Optional[datetime]:
    """Coerce a datetime or ISO-8601-ish string to an aware UTC datetime.

    Returns None for anything unusable (None, empty, unparseable, wrong type) so callers
    can treat "no comparable stamp" as a normal case rather than catching exceptions.

    A naive input is treated as UTC (see the module docstring). `fromisoformat` on 3.11+
    accepts both the "T" and " " separators and a trailing "Z", which covers every shape
    written to ck.db.
    """
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip())
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

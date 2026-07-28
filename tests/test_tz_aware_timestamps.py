"""Timezone-aware UTC timestamps, and the two hazards that made the migration risky.

`datetime.utcnow()` is deprecated from Python 3.12 and returns a NAIVE datetime that
merely holds UTC. Replacing it with `datetime.now(timezone.utc)` is one line per site, but
`ck.db` is a permanent source of truth that ALREADY HOLDS naive stamps, so the two shapes
must coexist forever. Two distinct ways that bites:

HAZARD 1 — mixed comparison raises.
    naive > aware  ->  TypeError: can't compare offset-naive and offset-aware datetimes
  This is not hypothetical: it broke test_persist_stamps_updated_at on the first attempt.
  Fixed at the model boundary — `UtcDatetime` coerces on validation, so a session loaded
  from a pre-cutover row can never carry a naive value.

HAZARD 2 — lexicographic ordering is sensitive to formatting.
  A naive stamp is a strict PREFIX of its own aware form:
      "2026-07-28T12:00:00"  vs  "2026-07-28T12:00:00+00:00"
  so a STRING compare calls the aware side newer at the identical instant. `_pt_get`'s
  anti-clobber check is such a string compare.

  Scope claim, measured rather than assumed (see
  test_string_and_parsed_verdicts_agree_only_because_stamps_are_coerced): with HAZARD 1
  fixed at the model boundary the cached stamp is always aware, and then string comparison
  agrees with parsed comparison on all 8 shapes the `sessions.updated_at` column can hold.
  So switching `_pt_get` to parse is defence-in-depth, NOT a live bug fix. Remove the model
  coercion and exactly one combination diverges — an aware column stamp against a naive
  cached stamp at the same instant reads as "the DB is newer", reloading on every request.
  The parse earns its place by making the verdict independent of stored formatting, which
  also covers the space-separated payload shape and non-UTC offsets, where string ordering
  genuinely inverts.
"""
import ast
import datetime as dt
import json
import pathlib

import pytest

from models import PtSession, StepState, WizardSession, model_to_dict
from timeutil import as_utc, utc_now

_SERVER = pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"
_UTC = dt.timezone.utc


# --- utc_now -----------------------------------------------------------------

def test_utc_now_is_aware_and_utc():
    now = utc_now()
    assert now.tzinfo is not None, "the whole point: never naive"
    assert now.utcoffset() == dt.timedelta(0)


def test_utc_now_is_comparable_to_itself():
    assert utc_now() <= utc_now()


# --- as_utc ------------------------------------------------------------------

def test_naive_datetime_is_read_as_utc_not_local():
    """Pre-cutover stamps meant UTC. Reading them as local would shift every one of
    them by the seat's offset — silently, and differently on a differently-configured box.
    """
    naive = dt.datetime(2026, 7, 28, 12, 0, 0)
    got = as_utc(naive)
    assert got == dt.datetime(2026, 7, 28, 12, 0, 0, tzinfo=_UTC)
    assert got.hour == 12, "the wall-clock reading must not move"


def test_aware_input_is_normalized_to_utc():
    plus5 = dt.timezone(dt.timedelta(hours=5))
    got = as_utc(dt.datetime(2026, 7, 28, 17, 0, 0, tzinfo=plus5))
    assert got == dt.datetime(2026, 7, 28, 12, 0, 0, tzinfo=_UTC)


@pytest.mark.parametrize("text", [
    "2026-07-28T12:00:00",              # isoformat() — the sessions.updated_at column
    "2026-07-28 12:00:00",              # str(datetime) — inside the JSON payload
    "2026-07-28T12:00:00+00:00",        # already aware
    "2026-07-28T12:00:00Z",             # Z suffix
    "  2026-07-28T12:00:00  ",          # surrounding whitespace
])
def test_every_stored_string_shape_parses(text):
    """These are the shapes ck.db actually contains — `db.save_session` writes datetimes
    inside `payload` with json.dumps(default=str), which is the SPACE-separated form,
    while the `updated_at` column uses isoformat()."""
    assert as_utc(text) == dt.datetime(2026, 7, 28, 12, 0, 0, tzinfo=_UTC)


def test_microseconds_survive():
    assert as_utc("2026-07-28T12:00:00.123456").microsecond == 123456


@pytest.mark.parametrize("junk", [None, "", "   ", "not a date", 12345, [], {}],
                         ids=["none", "empty", "spaces", "garbage", "int", "list", "dict"])
def test_unusable_input_is_none_not_an_exception(junk):
    """Callers treat "no comparable stamp" as normal, so this must not raise."""
    assert as_utc(junk) is None


# --- HAZARD 1: mixed comparison ----------------------------------------------

def test_mixed_comparison_raises_without_coercion():
    """Proves the hazard is real, so the tests below are not guarding a phantom."""
    with pytest.raises(TypeError, match="offset-naive and offset-aware"):
        _ = dt.datetime(2026, 7, 28) > utc_now()


def test_coercion_makes_the_mixed_comparison_safe():
    assert as_utc(dt.datetime(2020, 1, 1)) < as_utc(utc_now())


@pytest.mark.parametrize("stamp", [
    dt.datetime(2020, 1, 1),            # naive datetime
    "2020-01-01T00:00:00",              # naive string, as stored
    "2020-01-01 00:00:00.123456",       # naive payload form
])
def test_model_coerces_any_stored_stamp_to_aware(stamp):
    """The fix that removes the whole class: coerce at the model boundary, so no session
    in memory can hold a naive value regardless of what the row looked like."""
    sess = PtSession(key="AWPTCM-T1", updated_at=stamp)
    assert sess.updated_at.tzinfo is not None
    assert sess.updated_at < utc_now(), "must be comparable to a fresh aware stamp"


def test_wizard_session_step_confirmed_at_is_coerced():
    # A safely-past date: this seat runs at UTC+12, so "today at 09:00 UTC" is still in
    # the future for most of the local working day.
    sess = WizardSession(key="AWPTCM-T1",
                         step1=StepState(confirmed=True, confirmed_at="2020-01-01T09:00:00"))
    assert sess.step1.confirmed_at.tzinfo is not None
    assert sess.step1.confirmed_at < utc_now()


def test_a_legacy_naive_row_round_trips_and_stays_comparable():
    """End-to-end on the real persistence path: a pre-cutover payload (naive, space
    separator, exactly what json.dumps(default=str) wrote) must load aware."""
    legacy = {"key": "AWPTCM-T33233", "updated_at": "2026-07-28 09:00:00.123456",
              "step1": {"confirmed": True, "confirmed_at": "2026-07-28 09:00:00"}}
    sess = WizardSession(**json.loads(json.dumps(legacy)))
    assert sess.updated_at.tzinfo is not None
    assert sess.step1.confirmed_at.tzinfo is not None
    assert sess.updated_at > sess.step1.confirmed_at   # would TypeError if either were naive


def test_none_stays_none():
    """An unconfirmed step has no stamp; coercion must not invent one.

    Neither form reaches `_coerce_utc`: an omitted field uses the pydantic default without
    validating, and an explicit None is resolved by the None member of the
    `Optional[...]` union before the annotated member's validator runs. Measured, after a
    mutation that made `_coerce_utc(None)` return a stamp failed to turn this red — the
    branch it mutated was unreachable, and has since been deleted. Kept because "None
    stays None" is still the behaviour callers depend on, however it is implemented.
    """
    assert WizardSession(key="AWPTCM-T1").updated_at is None          # default path
    assert StepState().confirmed_at is None                            # default path
    assert WizardSession(key="AWPTCM-T1", updated_at=None).updated_at is None   # validator
    assert StepState(confirmed_at=None).confirmed_at is None                    # validator


def test_a_dumped_session_is_json_serializable():
    """db.save_session does json.dumps(dump, default=str); aware datetimes must survive
    that and be re-readable by as_utc."""
    sess = WizardSession(key="AWPTCM-T1", updated_at=utc_now())
    raw = json.loads(json.dumps(model_to_dict(sess), default=str))
    assert as_utc(raw["updated_at"]) is not None


# --- HAZARD 2: lexicographic ordering ----------------------------------------

def test_string_compare_of_the_same_instant_is_wrong():
    """The trap, stated as an executable fact. A naive stamp is a PREFIX of its aware
    form, so `>` on the strings claims the aware one is later at the same instant."""
    naive_s = "2026-07-28T12:00:00"
    aware_s = "2026-07-28T12:00:00+00:00"
    assert aware_s > naive_s, "string compare: aware looks newer"
    assert as_utc(aware_s) == as_utc(naive_s), "parsed: they are the SAME instant"


def test_string_ordering_of_one_instant_is_arbitrary():
    """Sharper form of the same trap: THREE spellings of the identical instant sort into
    three strictly different string positions, so string order is not a function of time
    at all. The suffixes after "…T12:00:00" are "" < "+00:00" < ".000000" because '+'
    (0x2B) precedes '.' (0x2E) and the empty suffix is a prefix of both.
    """
    same_instant = [
        "2026-07-28T12:00:00.000000",   # naive, explicit zero microseconds
        "2026-07-28T12:00:00+00:00",    # aware
        "2026-07-28T12:00:00",          # naive, microseconds omitted
    ]
    assert sorted(same_instant) == [
        "2026-07-28T12:00:00",
        "2026-07-28T12:00:00+00:00",
        "2026-07-28T12:00:00.000000",
    ], "string sort imposes a strict order on equal instants"
    parsed = [as_utc(s) for s in same_instant]
    assert len(set(parsed)) == 1, "parsed, all three are the SAME moment"


def test_a_non_utc_offset_inverts_string_ordering_outright():
    """`as_utc` accepts any offset, and there a string compare is not merely tie-broken
    wrongly — it is backwards. The local seat runs at UTC+12, so this is the shape a
    stamp would take if anything ever wrote local time into the column.
    """
    earlier = "2026-07-28T23:00:00+12:00"   # 11:00 UTC
    later = "2026-07-28T12:00:00+00:00"     # 12:00 UTC
    assert earlier > later, "string compare puts the EARLIER stamp last"
    assert as_utc(earlier) < as_utc(later), "parsed ordering is correct"


# --- HAZARD 2 applied: the anti-clobber check --------------------------------

@pytest.fixture
def pc():
    from routers import pytest_create as mod
    return mod


def _mk(pc, key, code, stamp):
    sess = pc.PtSession(key=key, group="Port (7)", updated_at=stamp)
    sess.step6 = {"files": {"test": {"name": "t.py", "code": code}}}
    return sess


def test_db_still_wins_when_newer_across_mixed_formats(pc, monkeypatch):
    """The data-loss scenario, now with a NAIVE db stamp and an AWARE cached one — the
    exact mix a pre-cutover row plus a post-cutover process produces."""
    key = "AWPTCM-TTZ1"
    stale = _mk(pc, key, "OLD-STALE-CODE", dt.datetime(2026, 7, 28, 9, 0, 0, tzinfo=_UTC))
    fresh = _mk(pc, key, "NEW-COMMITTED-CODE", dt.datetime(2026, 7, 28, 9, 30, 0, tzinfo=_UTC))

    monkeypatch.setitem(pc.pt_sessions, key, stale)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: "2026-07-28T09:30:00")
    monkeypatch.setattr(pc, "_pt_load", lambda k: fresh)

    got = pc._pt_get(key)
    assert got.step6["files"]["test"]["code"] == "NEW-COMMITTED-CODE", (
        "the stale cache won — a later persist would overwrite newer committed work")


def test_identical_instant_in_two_formats_does_not_reload(pc, monkeypatch):
    """A naive column stamp and an aware cached stamp for the SAME moment must compare
    equal, not "DB is newer". Deliberately not named as a bug fix — see the module
    docstring: this passes with string comparison too, once the cached side is coerced."""
    key = "AWPTCM-TTZ2"
    cached = _mk(pc, key, "CACHED", dt.datetime(2026, 7, 28, 9, 0, 0, tzinfo=_UTC))
    reloads = []

    monkeypatch.setitem(pc.pt_sessions, key, cached)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: "2026-07-28T09:00:00")
    monkeypatch.setattr(pc, "_pt_load", lambda k: reloads.append(k) or cached)

    assert pc._pt_get(key) is cached
    assert reloads == [], "reloaded from the DB for an identical instant"


def test_cache_wins_when_it_is_genuinely_newer(pc, monkeypatch):
    """The other direction must also hold, or every request would refetch."""
    key = "AWPTCM-TTZ3"
    cached = _mk(pc, key, "NEWER-CACHED", dt.datetime(2026, 7, 28, 10, 0, 0, tzinfo=_UTC))
    reloads = []

    monkeypatch.setitem(pc.pt_sessions, key, cached)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: "2026-07-28T09:00:00")
    monkeypatch.setattr(pc, "_pt_load", lambda k: reloads.append(k) or cached)

    assert pc._pt_get(key) is cached
    assert reloads == []


def test_missing_db_stamp_keeps_the_cache(pc, monkeypatch):
    key = "AWPTCM-TTZ4"
    cached = _mk(pc, key, "CACHED", utc_now())
    monkeypatch.setitem(pc.pt_sessions, key, cached)
    monkeypatch.setattr(pc, "_pt_session_updated_at", lambda k: None)
    assert pc._pt_get(key) is cached


def test_string_and_parsed_verdicts_agree_only_because_stamps_are_coerced():
    """Substantiates the module docstring's scope claim by enumeration, so the honesty of
    the `_pt_get` change is checkable rather than asserted in prose.

    `db_stamp` comes from the `sessions.updated_at` column, written by `isoformat()` —
    aware now, naive in pre-cutover rows. `mem_stamp` is `cached.updated_at.isoformat()`,
    which `UtcDatetime` keeps aware. Over that reachable matrix the two strategies agree
    everywhere; drop the coercion and one case diverges.
    """
    base = dt.datetime(2026, 7, 28, 9, 0, 0, tzinfo=_UTC)
    aware = lambda d: d.isoformat()
    naive = lambda d: d.replace(tzinfo=None).isoformat()
    deltas = [dt.timedelta(0), dt.timedelta(seconds=5), dt.timedelta(seconds=-5),
              dt.timedelta(microseconds=1)]

    def disagreements(mem_fmt):
        out = []
        for db_fmt in (aware, naive):
            for delta in deltas:
                db_s, mem_s = db_fmt(base + delta), mem_fmt(base)
                if (db_s > mem_s) != (as_utc(db_s) > as_utc(mem_s)):
                    out.append((db_s, mem_s))
        return out

    assert disagreements(aware) == [], (
        "with the cached stamp coerced to aware, string and parsed comparison must agree "
        "on every reachable shape — if this fails, the _pt_get docstring is now wrong")
    # And the coercion is what buys that: without it, one case diverges.
    assert len(disagreements(naive)) == 1, (
        "expected exactly one divergence without coercion (aware column vs naive cache at "
        "the same instant)")


# --- persistence stamps ------------------------------------------------------

def test_wizard_persist_stamps_aware(monkeypatch):
    import session_store as store

    # session_store.db and routers.wizard.db are the same module object (both `import db`),
    # so patching it here covers every caller.
    monkeypatch.setattr(store.db, "save_session", lambda *a, **k: None)
    sess = WizardSession(key="AWPTCM-T99994")
    store.persist_session(sess)
    assert sess.updated_at.tzinfo is not None


def test_confirm_step_stamps_aware(monkeypatch):
    """confirmed_at is written by confirm_step; it feeds the same comparisons."""
    import asyncio

    import routers.wizard as wizard
    import session_store as store

    monkeypatch.setattr(store.db, "save_session", lambda *a, **k: None)
    key = "AWPTCM-T99995"
    store.sessions[key] = WizardSession(key=key)
    try:
        asyncio.run(wizard.confirm_step(
            key, 1, {"selections": [{"id_or_key": "A", "title": "t"}]}, data={}))
        assert store.sessions[key].step1.confirmed_at.tzinfo is not None
    finally:
        store.sessions.pop(key, None)


# --- source guard ------------------------------------------------------------

def test_no_utcnow_calls_left_in_the_server():
    """AST, not grep: timeutil's docstring necessarily NAMES datetime.utcnow() while
    explaining why it is gone, and a text search would flag that explanation.
    `tool/` is deliberately out of scope — those are build scripts and ck.db is built
    once and never rebuilt.
    """
    offenders = {}
    for path in sorted(_SERVER.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits = [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "utcnow"]
        if hits:
            offenders[path.relative_to(_SERVER).as_posix()] = hits
    assert not offenders, (
        f"deprecated datetime.utcnow() calls: {offenders}. Use timeutil.utc_now(), which "
        f"returns an AWARE datetime — naive stamps cannot be compared against aware ones.")


def test_the_utcnow_guard_actually_detects_the_pattern():
    """Mutation check for the guard above."""
    tree = ast.parse("import datetime\nx = datetime.datetime.utcnow()\ny = utc_now()\n")
    hits = [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "utcnow"]
    assert hits == [2]

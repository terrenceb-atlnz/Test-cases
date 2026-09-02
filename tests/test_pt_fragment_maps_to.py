"""A re-Gather must be able to CORRECT a fragment's step mapping, and a renumbered
sequence must not leave step-numbered data behind.

THE DEFECT THIS FIXES (2026-09-02, AWPTCM-T44297)
-------------------------------------------------
`gather_fragments` merges its results into the existing step-5 pool so a re-Gather adds to
what is there without wiping the reviewer's selections. The merge only ever APPENDED new
fragments: an already-pooled fragment kept whatever `maps_to` it was first gathered with,
and this run's freshly-derived mapping was discarded. `accounting` was refreshed regardless,
so the two diverged.

That divergence is visible, because the UI reads the fragment CARDS from `accounting` and
the coverage pill from `maps_to`. Observed after the sequence was re-extracted from 13 steps
to 31: `accounting` was non-empty for all 31 steps but `maps_to` covered only 25 — steps 14,
15, 16, 17, 20 and 27 displayed ticked fragment cards while their header read "no fragment
selected". The fragments feeding Generate were attributed to steps they never served.

`_add_fragment` was never at fault — it merges each step number as the step loop visits it.
Only the pool merge threw the result away.

Two decisions, both Terrence's:
  * REPLACE the stored mapping with this run's, not union it. On a renumbered sequence the
    stored mapping is wrong rather than incomplete, and a union preserves step numbers that
    no longer mean anything.
  * A re-extraction that changes the sequence CLEARS step 5, because `maps_to` is a set of
    step numbers into the sequence that just changed. step3.selections has the same exposure
    and is deliberately left alone — destroying a reviewer's script picks is his call, not
    the code's.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_ROUTER = REPO / "ask-ck" / "CK-main" / "CK_server" / "routers" / "pytest_create.py"


@pytest.fixture
def pc():
    from routers import pytest_create as mod
    return mod


def _seq(*specs):
    return [{"n": n, "action": a, "verify": "v"} for n, a in specs]


# --- _sequence_shape ---------------------------------------------------------

def test_shape_changes_when_the_step_count_changes(pc):
    """The 13 -> 31 case that started this."""
    a = _seq((1, "cable it"), (2, "bring up"))
    b = _seq((1, "cable it"), (2, "bring up"), (3, "capture"))
    assert pc._sequence_shape(a) != pc._sequence_shape(b)


def test_shape_changes_when_only_the_TEXT_changes(pc):
    """31 steps whose wording changed is the same hazard as 13 becoming 31 — a fragment
    mapped to step 5 now serves different work. A count-only check would miss it."""
    a = _seq((1, "cable the test port"))
    b = _seq((1, "cable the PARTNER port"))
    assert pc._sequence_shape(a) != pc._sequence_shape(b)


def test_shape_is_stable_for_an_identical_sequence(pc):
    """A re-extract that reproduces the same sequence must NOT clear step 5 — a Gather
    costs minutes and real money (measured 334.8s / $1.13 on T44297)."""
    a = _seq((1, "cable it"), (2, "bring up"))
    assert pc._sequence_shape(a) == pc._sequence_shape(_seq((1, "cable it"), (2, "bring up")))


def test_shape_notices_renumbering_even_at_the_same_length(pc):
    """Same texts, different numbers: the join key changed, so downstream is repointed."""
    a = _seq((1, "x"), (2, "y"))
    b = _seq((2, "x"), (3, "y"))
    assert pc._sequence_shape(a) != pc._sequence_shape(b)


# --- the pool merge ----------------------------------------------------------

def _merge_block(src: str) -> str:
    """The re-Gather merge inside gather_fragments' _apply, COMMENTS STRIPPED.

    Anchored on statements, not on words that also appear in prose: the first version
    ended the slice at the first "merged_acct" anywhere, which the fix's own explanatory
    comment mentions — so the block stopped short of the code under test and the assertion
    failed for the wrong reason. Same trap the frontend specs strip comments for.
    """
    start = src.index("async def gather_fragments(")
    body = src[start:]
    body = body[:body.index("\n@router.")]
    block = body[body.index("prev = fresh.step5"):body.index("merged_acct = dict(")]
    return "\n".join(ln for ln in block.splitlines() if not ln.strip().startswith("#"))


def test_an_existing_fragment_gets_this_runs_mapping():
    """The whole defect: the else-branch used not to exist, so the fresh mapping was lost."""
    code = _merge_block(_ROUTER.read_text(encoding="utf-8"))
    assert "else:" in code, (
        "the merge has no branch for an already-pooled fragment, so a re-Gather cannot "
        "correct a stale maps_to — that is the T44297 defect")
    assert '["maps_to"] =' in code, (
        "the existing pool entry's maps_to must be reassigned from this run's fragment")


def test_the_mapping_is_replaced_not_unioned():
    """Terrence's call. A union keeps step numbers from a sequence that no longer exists."""
    code = _merge_block(_ROUTER.read_text(encoding="utf-8"))
    idx = code.index('["maps_to"] =')
    stmt = code[idx:code.index("\n", idx)]
    assert "+" not in stmt and "append" not in stmt and "extend" not in stmt, (
        f"maps_to looks unioned rather than replaced: {stmt.strip()!r}")


def test_the_reviewers_selections_still_survive_a_regather():
    """The merge exists so a re-Gather does not wipe selections. Fixing maps_to must not
    change that — `selected` is keyed on (source_id, symbol), independent of maps_to."""
    block = _merge_block(_ROUTER.read_text(encoding="utf-8"))
    assert 'prev.get("selected")' in block, (
        "a re-Gather must still carry the reviewer's previous selections forward")


# --- re-extract clears step 5 ------------------------------------------------

def test_extract_sequence_clears_step5_on_a_shape_change():
    src = _ROUTER.read_text(encoding="utf-8")
    start = src.index("async def extract_sequence(")
    body = src[start:]
    body = body[:body.index("\n@router.")]
    code = "\n".join(ln for ln in body.splitlines() if not ln.strip().startswith("#"))
    assert "_sequence_shape(" in code, "extract_sequence does not compare sequence shape"
    assert "fresh.step5 = {}" in code, "a renumbering re-extract must clear the fragment pool"


def test_extract_sequence_does_NOT_clear_step3_selections():
    """Deliberate, and Terrence's explicit choice: step3.selections has the same {stepN}
    exposure, but clearing a reviewer's script picks automatically is destructive. It is a
    reported risk, not an automatic wipe. If this ever changes it must be a decision, not
    a side effect of touching this endpoint."""
    src = _ROUTER.read_text(encoding="utf-8")
    start = src.index("async def extract_sequence(")
    body = src[start:]
    body = body[:body.index("\n@router.")]
    code = "\n".join(ln for ln in body.splitlines() if not ln.strip().startswith("#"))
    assert "step3 = {}" not in code and 'fresh.step3 = {}' not in code, (
        "extract_sequence must not silently clear step-3 selections")

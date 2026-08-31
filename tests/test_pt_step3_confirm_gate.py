"""'3. Script Search' must be confirmable from the flow that actually drives it.

Why this exists (observed live 2026-08-30 on AWPTCM-T33351, and 2026-08-27 on
AWPTCM-T44191). `confirm_step` accepted step 3 only on `step3.provenance` or
`step3.matches`, and after the 2026-08-26 move to a per-sequence-step picker
NEITHER is written for a new session:

  * step 3 has never written `provenance` — only steps 2, 5, 6 and 8 do;
  * `matches` comes only from the whole-case POST /suggest_scripts, which left
    the UI on 2026-08-20 when the per-step picker replaced it.

So a step 3 that was visibly complete — 10/10 sequence steps covered, scripts
chosen and saved — was rejected with "Nothing to confirm yet ... (missing
matches)", and step 4 was unreachable behind it because gather_fragments calls
_require_confirmed(sess, "step3", ...). Every pt- session already in ck.db
predates the change and still carried `matches`, which is why the suite stayed
green and the bug reached a user.

The fix (23178e0) accepts the per-step flow's own evidence that the step RAN.
It shipped with no test; these are that test. Four of them are the shapes the
fix was verified against by hand, now held by the gate; the last two pin the
two properties that are easy to break while "fixing" this again:

  * an empty answer is still a legitimate ANSWER, not a step that never ran —
    the property the original `is not None` check existed for; and
  * the escape hatch is scoped to `matches`. Step 5 writes real provenance, so
    `fragments` keeps the original predicate and must NOT accept step_matches.

Offline: no network, no LLM. Real app via TestClient, fake sessions, isolated ck.db.
"""
import pytest


def _seed(key, **steps):
    """Register a throwaway pt session with step 2 already confirmed."""
    from routers.pytest_create import pt_sessions
    from models import PtSession
    sess = PtSession(key=key, group="Authentication & Security (42)",
                     step2={"confirmed": True,
                            "sequence": [{"n": 1, "action": "a", "verify": "v"}]},
                     **steps)
    pt_sessions[key] = sess
    return sess


@pytest.fixture
def confirm(client):
    """POST confirm_step for a throwaway key, cleaning the session up afterwards."""
    from routers.pytest_create import pt_sessions
    made = []

    def _go(key, step, **steps):
        made.append(key)
        _seed(key, **steps)
        return client.post(f"/api/pytest-create/confirm_step/{key}/{step}",
                           headers={"X-CK-Session": "gate-test"}, json={})

    yield _go
    for k in made:
        pt_sessions.pop(k, None)


# --- the regression itself ---------------------------------------------------

def test_step_matches_alone_confirms(confirm):
    """T33351's shape: per-step suggestions ran, no `matches`, no `provenance`."""
    r = confirm("AWPTCM-TSTEPMATCHES", 3, step3={
        "step_matches": {"1": [{"id": "art/1348_security/test-1348.1001.py",
                                "coverage": "partial", "reason": "dot1x/RADIUS setup"}]},
        "selections": ["art/1348_security/test-1348.1001.py"],
        "records": {"art/1348_security/test-1348.1001.py": {"db": "art"}},
    })
    assert r.status_code == 200, r.text
    assert r.json()["session"]["step3"]["confirmed"] is True


def test_selections_alone_confirms(confirm):
    """Keyword search reaches a complete step 3 without ever invoking Suggest."""
    r = confirm("AWPTCM-TSELECTONLY", 3, step3={"selections": ["legacy/tools/dot1x_simulator.py"]})
    assert r.status_code == 200, r.text


def test_a_step_that_never_ran_is_still_rejected(confirm):
    """The gate must keep doing its job — this is the case it exists for."""
    r = confirm("AWPTCM-TNEVERRAN", 3, step3={})
    assert r.status_code == 409
    assert "Nothing to confirm yet" in r.json()["detail"]
    assert "3. Script Search" in r.json()["detail"]


def test_legacy_whole_case_matches_still_confirms(confirm):
    """Pre-2026-08-26 sessions must be unaffected — they are most of ck.db."""
    r = confirm("AWPTCM-TLEGACYMATCH", 3, step3={"matches": [{"id": "x.py"}]})
    assert r.status_code == 200, r.text


# --- the two properties that are easy to break while re-fixing this ----------

def test_an_empty_answer_still_counts_as_having_run(confirm):
    """`_persist_step_matches` writes a step even when it matched NOTHING.

    A sequence step with genuinely no reusable code is a real answer, not an
    unrun step; `bool(step_matches)` sees the dict, not the empty list inside.
    """
    r = confirm("AWPTCM-TEMPTYANSWER", 3, step3={"step_matches": {"1": []}})
    assert r.status_code == 200, r.text


def test_step5_fragments_does_not_gain_the_escape_hatch(confirm):
    """Scoped to `matches`. Step 5 writes real provenance, so its gate stands."""
    r = confirm("AWPTCM-TFRAGSCOPE", 5, step5={
        "step_matches": {"1": [{"id": "x.py"}]},
        "selections": ["x.py"],
    })
    assert r.status_code == 409
    assert "missing fragments" in r.json()["detail"]

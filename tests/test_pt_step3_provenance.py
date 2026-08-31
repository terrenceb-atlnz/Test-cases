"""Step 3 must record what its LLM call actually sent.

Step 3 was the one LLM step in the PyTest Creator that stored no provenance. Steps 2, 5
and 6 each write {llm, prompt, response} onto their step, and the shared panel seeds from
`step3.provenance` — but the only writer of that key was the WHOLE-CASE suggest, which
left the UI on 2026-08-20 when the per-sequence-step picker replaced it. So for every
session driven through the current flow the step-3 provenance panel was permanently
blank, and there was no way to see what a suggest had sent after the fact.

Found 2026-08-31 while fixing the Generate panel's provenance, and the same shape: the
panel was reporting on a code path the flow no longer takes.

One slot rather than one per step is deliberate and pinned below — the session payload is
a row in the permanent ck.db, and a 32-step case would otherwise carry 32 full prompts.

Offline: no network, no LLM. Real module, fake session, monkeypatched transport.
"""
import asyncio
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture
def pc():
    from routers import pytest_create as mod
    return mod


class _Req:
    """Minimal stand-in for the Request the endpoint only uses to reach _data()."""
    headers: dict = {}


def _sess(pc, key="AWPTCM-TPROV3"):
    sess = pc.PtSession(key=key, group="Port (7)")
    sess.step2 = {"confirmed": True,
                  "sequence": [{"n": 1, "action": "configure lldp", "verify": "show lldp"},
                               {"n": 2, "action": "reload", "verify": "show version"}]}
    return sess


def _wire(pc, monkeypatch, sess, content='{"matches": []}'):
    """Point the endpoint at a fake transport and an in-memory session."""
    seen = {}

    def fake_run_prompt(template, ctx, **kw):
        seen["template"] = template
        seen["ctx"] = ctx
        return {"prompt": f"RENDERED for step {ctx['sequence'][0]['n']}",
                "content": content, "provider": "vllm", "model": "fast",
                "auth_method": "api_key"}

    monkeypatch.setattr(pc, "run_prompt", fake_run_prompt)
    monkeypatch.setattr(pc, "_pt_get", lambda k: sess)
    monkeypatch.setattr(pc, "_pt_persist", lambda s: None)
    monkeypatch.setattr(pc, "_data", lambda r: {"scripts_index_by_id": {}})
    monkeypatch.setattr(pc, "_search_slim",
                        lambda *a, **k: [{"id": "art/x/test-1.py", "title": "T"}])
    return seen


def _call(pc, key, step_n, body=None):
    return asyncio.run(pc.suggest_scripts_step(key, step_n, _Req(), body or {}))


def test_a_real_per_step_suggest_records_its_prompt(pc, monkeypatch):
    sess = _sess(pc)
    _wire(pc, monkeypatch, sess)
    _call(pc, sess.key, 2)
    prov = sess.step3["provenance"]
    assert prov["prompt"] == "RENDERED for step 2"
    assert prov["response"] == '{"matches": []}'
    assert prov["llm"] == {"provider": "vllm", "model": "fast", "auth_method": "api_key"}


def test_the_recorded_provenance_names_its_sequence_step(pc, monkeypatch):
    """One slot is only honest if it says which step it belongs to."""
    sess = _sess(pc)
    _wire(pc, monkeypatch, sess)
    _call(pc, sess.key, 2)
    assert sess.step3["provenance"]["step_n"] == 2


def test_one_slot_not_one_per_step(pc, monkeypatch):
    """A later step overwrites — the payload is a permanent ck.db row, not a log."""
    sess = _sess(pc)
    _wire(pc, monkeypatch, sess)
    _call(pc, sess.key, 1)
    _call(pc, sess.key, 2)
    assert sess.step3["provenance"]["step_n"] == 2
    assert "step_provenance" not in sess.step3


def test_recording_provenance_does_not_disturb_step_matches(pc, monkeypatch):
    """_persist_step_matches spreads step3; the provenance write must not race it."""
    sess = _sess(pc)
    _wire(pc, monkeypatch, sess)
    _call(pc, sess.key, 1)
    assert "step_matches" in sess.step3
    assert "1" in sess.step3["step_matches"] or 1 in sess.step3["step_matches"]
    assert sess.step3["provenance"]["step_n"] == 1


def test_a_dry_run_records_nothing(pc, monkeypatch):
    """Refresh (no send) is a preview — it must not write to the session."""
    sess = _sess(pc)
    _wire(pc, monkeypatch, sess)
    out = _call(pc, sess.key, 1, {"dry_run": True})
    assert out["provenance"]["prompt"] == "RENDERED for step 1"
    assert "provenance" not in (sess.step3 or {})


def test_no_candidates_means_no_provenance_and_no_crash(pc, monkeypatch):
    """meta only exists when there was something to rank — the write is guarded on it."""
    sess = _sess(pc)
    _wire(pc, monkeypatch, sess)
    monkeypatch.setattr(pc, "_search_slim", lambda *a, **k: [])
    _call(pc, sess.key, 1)
    assert "provenance" not in (sess.step3 or {})

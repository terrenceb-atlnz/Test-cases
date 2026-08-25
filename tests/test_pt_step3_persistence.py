"""Step-3 suggestion/selection persistence — nothing the Script Search page shows
may evaporate on a reload.

Why this exists (2026-08-26, Terrence). Per-step LLM suggestions lived only in
browser JS: `suggest_scripts_step` said outright "Not persisted to step3.matches",
and `save_matches` stored bare id lists. Observed live: a hard reload lost every
candidate (with its coverage/why verdict), and the CHOSEN rows degraded to
db='other' / coverage='?' / empty why, because nothing server-side held their
records. That was tolerable while the whole-case suggest (which does persist
step3.matches) was the primary path — but that button left the UI, so nothing
persisted at all. Three fixes pinned here:

  1. `_persist_step_matches` — per-step suggestions merge into
     step3.step_matches (newest verdict wins, others kept, fields whitelisted)
     and deliberately do NOT unconfirm step 3 or invalidate downstream:
     candidates are not selections.
  2. `save_matches` — accepts a `records` map so keyword-search picks keep
     db/cov/why forever; ids-only behaviour otherwise unchanged.
  3. The gather-fragments prompt template renders the step-3 review verdicts
     (chosen-for-step / coverage / why) so fragment choice is no longer blind
     to the reasons the scripts were selected — and the suggest endpoint really
     calls the persist helper.

Offline: no network, no LLM, no server. Real module, fake sessions.
"""
import asyncio
import inspect
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


def _sess(pc, key="AWPTCM-TPERSIST"):
    sess = pc.PtSession(key=key, group="Port (7)")
    sess.step2 = {"confirmed": True,
                  "sequence": [{"n": 1, "action": "a", "verify": "v"},
                               {"n": 2, "action": "b", "verify": "w"}]}
    return sess


def _match(sid, cov="partial", reason="because", extra=None):
    m = {"id": sid, "title": "T", "db": "art", "coverage": cov,
         "reason": reason, "covers_steps": [1],
         "score": 9.9, "case_descs": ["internal scoring junk must not persist"]}
    m.update(extra or {})
    return m


# --- 1. _persist_step_matches ------------------------------------------------

def test_step_matches_merge_newest_verdict_wins_and_keeps_the_rest(pc, monkeypatch):
    sess = _sess(pc)
    persisted = []
    monkeypatch.setattr(pc, "_pt_persist", lambda s: persisted.append(s))

    pc._persist_step_matches(sess, 1, [_match("a.py", cov="partial", reason="old"),
                                       _match("b.py")])
    pc._persist_step_matches(sess, 1, [_match("a.py", cov="full", reason="new verdict")])

    got = {m["id"]: m for m in sess.step3["step_matches"]["1"]}
    assert set(got) == {"a.py", "b.py"}, "a re-suggest dropped candidates the page showed"
    assert got["a.py"]["coverage"] == "full" and got["a.py"]["reason"] == "new verdict", \
        "the newest verdict for an id must win"
    assert len(persisted) == 2, "every suggest run must persist"


def test_step_matches_whitelist_and_no_downstream_invalidation(pc, monkeypatch):
    sess = _sess(pc)
    sess.step3 = {"confirmed": True, "selections": {"1": ["a.py"]}}
    sess.step5 = {"fragments": [{"source_id": "a.py", "symbol": "TestCase_1"}]}
    monkeypatch.setattr(pc, "_pt_persist", lambda s: None)

    pc._persist_step_matches(sess, 2, [_match("c.py")])

    rec = sess.step3["step_matches"]["2"][0]
    assert set(rec) <= set(pc._MATCH_PERSIST_FIELDS), \
        f"scoring internals leaked into the permanent session payload: {set(rec) - set(pc._MATCH_PERSIST_FIELDS)}"
    assert sess.step3["confirmed"] is True, \
        "fetching suggestions is not a selection change — it must not unconfirm step 3"
    assert sess.step3["selections"] == {"1": ["a.py"]}, "existing selections were clobbered"
    assert sess.step5.get("fragments"), \
        "fetching suggestions invalidated fragments — only save_matches may do that"


# --- 2. save_matches records -------------------------------------------------

def test_save_matches_stores_whitelisted_records_for_chosen_ids(pc, monkeypatch):
    sess = _sess(pc)
    monkeypatch.setattr(pc, "_pt_get", lambda k: sess)
    monkeypatch.setattr(pc, "_pt_persist", lambda s: None)

    out = asyncio.run(pc.save_matches(sess.key, {
        "selections": {"1": ["kw.py", "kw.py", ""]},
        "records": {"kw.py": _match("kw.py", cov="partial", reason="keyword pick"),
                    "junk": "not-a-dict"},
    }))

    assert out["selections"] == {"1": ["kw.py"]}, "id normalization regressed"
    stored = sess.step3["records"]["kw.py"]
    assert stored["coverage"] == "partial" and stored["reason"] == "keyword pick"
    assert set(stored) <= set(pc._MATCH_PERSIST_FIELDS)
    assert "junk" not in sess.step3["records"]


def test_save_matches_records_accumulate_across_saves(pc, monkeypatch):
    sess = _sess(pc)
    monkeypatch.setattr(pc, "_pt_get", lambda k: sess)
    monkeypatch.setattr(pc, "_pt_persist", lambda s: None)

    asyncio.run(pc.save_matches(sess.key, {"selections": {"1": ["a.py"]},
                                           "records": {"a.py": _match("a.py")}}))
    asyncio.run(pc.save_matches(sess.key, {"selections": {"2": ["b.py"]},
                                           "records": {"b.py": _match("b.py")}}))
    assert set(sess.step3["records"]) == {"a.py", "b.py"}, \
        "a later save dropped earlier chosen-record snapshots"


# --- 3. the review verdicts reach the fragments prompt ------------------------

def test_suggest_endpoint_persists_and_fragments_prompt_renders_review():
    import routers.pytest_create as pc
    src = inspect.getsource(pc.suggest_scripts_step)
    assert "_persist_step_matches(" in src, \
        "suggest_scripts_step no longer persists its matches — reload loses them again"

    import jinja2
    tpl_dir = REPO / "ask-ck" / "CK-main" / "CK_server" / "templates" / "prompts"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tpl_dir)))
    rendered = env.get_template("pt_gather_fragments.jinja").render(
        case_key="AWPTCM-TX",
        sequence=[{"n": 1, "action": "configure radius", "verify": "show dot1x"}],
        scripts=[{"id": "art/x/test-1.py",
                  "symbols": [{"kind": "class", "name": "TestCase_1", "desc": "d"}],
                  "review": [{"step": "1", "coverage": "partial",
                              "why": "sets up RADIUS auth with VLANs"}]}])
    assert "chosen for sequence step 1" in rendered
    assert "partial coverage" in rendered
    assert "sets up RADIUS auth with VLANs" in rendered, \
        "the step-3 WHY no longer reaches the fragments prompt"

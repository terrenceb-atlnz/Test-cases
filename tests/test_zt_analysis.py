"""Zephyr Templating Tool, Phase 3 — the analysis (CK_server/zt_analysis.py + the /analyse job).

The wiki inputs are the real IE520 and IE570 reads (the zt_wiki fixtures, read offline through the
tool itself), so the prompt contexts are built from the shapes the live tool prints. The model is
never called: the router's `_ask` and `_run_tool` are replaced, and what the tests check is what
the SERVER does with a reply — the guardrail (PLAN §5a): a proposal survives only with a key in
that plan's tree, a question that fits the key, a reason and a source, and never on a "Maybe" row.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import pytest

import db
import zt_analysis as za
from llm import render_prompt

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


zw = _load("zt_wiki_for_analysis", ROOT / "ask-ck" / "tools" / "zt_wiki.py")
zs = _load("zt_snapshot_for_analysis", ROOT / "ask-ck" / "tools" / "zt_snapshot.py")


def _wiki(fixture, title):
    pages = json.loads((FIX / fixture).read_text(encoding="utf-8"))
    get = lambda p: pages.get(p["page"].replace("_", " ")) or {"error": {"code": "missingtitle"}}  # noqa: E731
    return zw.read_project(get, title)


IE520 = _wiki("zt_wiki_ie520.json", "Project:3296 IE520 Software")
IE570 = _wiki("zt_wiki_ie570.json", "Project:3001 IE570 Platform Support")
PLAN = json.loads((FIX / "zt_plan_P3248.json").read_text(encoding="utf-8"))
CYCLE = json.loads((FIX / "zt_cycle_C8451.json").read_text(encoding="utf-8"))
CASES = [i["testCaseKey"] for i in CYCLE["items"]]


def _snapshot():
    """The real Port pair through the snapshot tool's own fetch + assemble."""
    def get(path):
        if "/testplan/search" in path:
            return [PLAN]
        if "/testrun/search" in path:
            return [CYCLE]
        kind, key = path.rsplit("/", 2)[-2:]
        if kind == "testplan":
            return PLAN
        if kind == "testrun":
            return CYCLE
        return {"key": key, "name": f"Port case {key}", "folder": "/Port", "status": "Draft",
                "priority": "Normal", "labels": [], "majorVersion": 2}
    return zs.assemble(zs.fetch(get))


TREE = {"plans": [{"key": "AWPTCM-P3248", "name": "Port", "cycles": [
    {"key": "AWPTCM-C8451", "name": "Port", "cases": [{"key": k, "name": f"Port case {k}"} for k in CASES]}]}]}
PORT = TREE["plans"][0]


# --------------------------------------------------------------------------- inputs to the model

def test_version_comes_from_the_strategy_path_and_the_page_version_is_kept_beside_it():
    v = za.version_and_product(IE570)
    assert (v["version"], v["version_source"], v["project_version"]) == ("5.5.6-2", "Test Strategy target path", "5.5.6")
    assert (v["product"], v["middle"], v["number"]) == ("IE570", "Tomahawk", "3001")
    v = za.version_and_product(IE520)
    assert (v["version"], v["project_version"], v["product"]) == ("5.5.6-2", None, "IE520")


def test_feature_lists_split_by_verdict_and_maybe_is_its_own_list():
    f = za.feature_lists(IE570)
    assert len(f["undecided"]) == 6 and all("Maybe" in l for l in f["undecided"])
    assert any(l.startswith("TPS §11.3.3 | Port |") for l in f["supported"])
    assert not set(f["supported"]) & set(f["unsupported"])
    f = za.feature_lists(IE520)
    assert "TPS §11.4 | Port | Continuous POE (HANP) | NO" in f["unsupported"]
    assert f["undecided"] == []


def test_the_plan_prompt_carries_the_plan_the_unsupported_rows_and_the_strategy():
    text = render_prompt("zt_analyse_plan.jinja", za.plan_context(IE520, PORT))
    assert all(k in text for k in CASES) and "PLAN AWPTCM-P3248 — Port" in text
    assert "TPS §11.4 | Port | Continuous POE (HANP) | NO" in text
    assert "### Test Strategy §3.3 Feature Coverage" in text                     # every heading names its document
    assert "Critical Reviewers" not in text                                        # bookkeeping out
    assert "empty template — nothing written" in text                             # D6: IE520's Feature Page
    assert "### TPS §6.1.5.1 Network Ports" in text                               # the device sections
    assert len(text) < 60000


def test_the_gaps_prompt_carries_the_supported_rows_and_the_template_outline():
    text = render_prompt("zt_gaps.jinja", za.gaps_context(IE570, TREE))
    assert "PLAN AWPTCM-P3248 Port" in text and f"    {CASES[0]} Port case" in text
    assert "TPS §11.3.3 | Port | Auto Negotiation | Yes" in text
    assert "AI Information on Secure Boot" in text                                 # IE570's one written section


def test_plain_strips_markup_and_keeps_lines():
    body = "{|\n|-\n!a!!b\n|-\n|[[Page|Label]]||'''bold'''<br>x\n|}\n<!-- hidden -->\n* item"
    assert za.plain(body) == "a | b\nLabel | bold x\n* item"


# --------------------------------------------------------------------------- the guardrail

def _reply(*deselect, notes=()):
    return {"deselect": list(deselect), "notes": list(notes)}


def test_a_well_formed_proposal_is_kept():
    r = za.check_plan_reply(_reply({"key": CASES[0], "question": "q4", "reason": "no PoE",
                                    "source": "TPS §11.4 | Port | Continuous POE (HANP) | NO"}), PORT)
    assert r["deselect"] == [{"key": CASES[0], "kind": "case", "question": "Q4", "reason": "no PoE",
                              "source": "TPS §11.4 | Port | Continuous POE (HANP) | NO"}]
    assert r["dropped"] == []


@pytest.mark.parametrize("bad, why", [
    ({"key": "AWPTCM-T1", "question": "Q3", "reason": "r", "source": "s"}, "not in this plan"),
    ({"key": "AWPTCM-C8451", "question": "Q3", "reason": "r", "source": "s"}, "Q3 is about a case"),
    ({"key": "AWPTCM-P3248", "question": "Q9", "reason": "r", "source": "s"}, "not Q1-Q4"),
    ({"key": CASES[1], "question": "Q4", "reason": "r", "source": ""}, "no reason or no source"),
    ({"key": CASES[1], "question": "Q4", "reason": "MACsec is Maybe", "source": "TPS §11.3.3"}, "Maybe"),
    ({"key": "AWPTCM-P3248", "question": "Q1", "reason": "r", "source": "TPS §11.3.3"}, "Test Strategy's word"),
    ("AWPTCM-T33233", "not an object"),
])
def test_a_bad_proposal_is_dropped_with_why(bad, why):
    r = za.check_plan_reply(_reply(bad), PORT)
    assert r["deselect"] == [] and why in r["dropped"][0]["why"]


def test_a_plan_cut_citing_the_test_strategy_is_kept():
    r = za.check_plan_reply(_reply({"key": "AWPTCM-P3248", "question": "Q1", "reason": "not tested",
                                    "source": "Test Strategy §4 Not Tested"}), PORT)
    assert [d["key"] for d in r["deselect"]] == ["AWPTCM-P3248"]


def test_a_duplicate_is_dropped_and_a_non_object_reply_keeps_everything():
    d = {"key": CASES[0], "question": "Q3", "reason": "r", "source": "s"}
    r = za.check_plan_reply(_reply(d, d), PORT)
    assert len(r["deselect"]) == 1 and r["dropped"][0]["why"] == "duplicate"
    r = za.check_plan_reply(["not", "an", "object"], PORT)
    assert r["deselect"] == [] and "not a JSON object" in r["dropped"][0]["why"]


def test_notes_may_name_a_key_in_the_plan_or_none():
    r = za.check_plan_reply(_reply(notes=["plain note", {"key": CASES[0], "note": "n"},
                                          {"key": "AWPTCM-T9", "note": "stray"}]), PORT)
    assert r["notes"] == [{"key": None, "note": "plain note"}, {"key": CASES[0], "note": "n"}]
    assert "not in this plan" in r["dropped"][0]["why"]


def test_gaps_need_a_requirement_and_a_source():
    r = za.check_gaps_reply({"gaps": [{"requirement": "PROFINET", "source": "Strategy §3.3"}, {"requirement": "x"}],
                             "notes": ["n1", {"note": "n2"}]})
    assert r["gaps"] == [{"requirement": "PROFINET", "source": "Strategy §3.3", "why": ""}]
    assert len(r["dropped"]) == 1 and [n["note"] for n in r["notes"]] == ["n1", "n2"]


# --------------------------------------------------------------------------- the job (router)

@pytest.fixture
def templates():
    db.replace_zt_templates(_snapshot())
    yield
    conn = db.get_connection()
    for t in ("zt_template_links", "zt_template_cases", "zt_template_cycles", "zt_template_plans",
              "zt_template_snapshot"):
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()


def _wait(client, job_id, until=("done", "error", "cancelled"), timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        d = client.get(f"/api/zephyr-tool/analyse/{job_id}").json()
        if d["state"] in until:
            return d
        time.sleep(0.05)
    raise AssertionError(f"analysis still {d['state']}")


def test_an_analysis_reads_the_wiki_asks_per_plan_and_keeps_only_what_passes(client, templates, monkeypatch):
    from routers import zephyr_tool
    asked = []
    monkeypatch.setattr(zephyr_tool, "_run_tool", lambda cmd, timeout, what, stdin=None: IE520)

    def ask(template, context, llm_config):
        asked.append(template)
        if template == "zt_gaps.jinja":
            return {"gaps": [{"requirement": "Industrial protocols", "source": "Test Strategy §3.3"}],
                    "notes": ["Stacks up to 4 — Strategy §2.1"]}, None
        return _reply({"key": CASES[0], "question": "Q4", "reason": "no PoE", "source": "TPS §11.4 | Port | Continuous POE (HANP) | NO"},
                      {"key": "AWPTCM-T999", "question": "Q3", "reason": "r", "source": "s"},
                      notes=["port note"]), None
    monkeypatch.setattr(zephyr_tool, "_ask", ask)
    job = client.post("/api/zephyr-tool/analyse", json={"url": "Project:3296_IE520_Software"}).json()
    d = _wait(client, job["id"])
    assert d["state"] == "done" and sorted(asked) == ["zt_analyse_plan.jinja", "zt_gaps.jinja"]
    assert (d["project"]["version"], d["project"]["product"]) == ("5.5.6-2", "IE520")
    slot = d["plans"]["AWPTCM-P3248"]
    assert [x["key"] for x in slot["deselect"]] == [CASES[0]] and len(slot["dropped"]) == 1
    assert d["gaps"]["gaps"][0]["requirement"] == "Industrial protocols"
    assert d["tps_rows"] == {"sid": 738, "prd": 260, "tested": 0}
    assert not any(k.startswith("_") for k in d)                  # the wiki read and LLM config stay server-side


def test_a_failed_plan_call_leaves_that_plan_ticked_and_says_why(client, templates, monkeypatch):
    from routers import zephyr_tool
    monkeypatch.setattr(zephyr_tool, "_run_tool", lambda *a, **k: IE520)
    monkeypatch.setattr(zephyr_tool, "_ask", lambda t, c, l: (None, "backend down") if t == "zt_analyse_plan.jinja"
                        else ({"gaps": [], "notes": []}, None))
    d = _wait(client, client.post("/api/zephyr-tool/analyse", json={"url": "x"}).json()["id"])
    assert d["state"] == "done"
    assert d["plans"]["AWPTCM-P3248"] == {"state": "error", "deselect": [], "notes": [], "dropped": [], "error": "backend down"}


def test_a_wiki_read_that_fails_fails_the_job(client, templates, monkeypatch):
    from routers import zephyr_tool

    def boom(*a, **k):
        raise RuntimeError("reading the wiki pages failed: no wiki page 'x'")
    monkeypatch.setattr(zephyr_tool, "_run_tool", boom)
    d = _wait(client, client.post("/api/zephyr-tool/analyse", json={"url": "x"}).json()["id"])
    assert d["state"] == "error" and "no wiki page" in d["error"]


def test_cancel_before_the_model_is_asked_asks_nothing(client, templates, monkeypatch):
    from routers import zephyr_tool
    gate, asked = threading.Event(), []

    def slow_read(*a, **k):
        gate.wait(5)
        return IE520
    monkeypatch.setattr(zephyr_tool, "_run_tool", slow_read)
    monkeypatch.setattr(zephyr_tool, "_ask", lambda *a: asked.append(1) or ({}, None))
    jid = client.post("/api/zephyr-tool/analyse", json={"url": "x"}).json()["id"]
    assert client.post(f"/api/zephyr-tool/analyse/{jid}/cancel").json()["cancelling"] is True
    gate.set()
    d = _wait(client, jid)
    assert d["state"] == "cancelled" and asked == []


def test_cancel_mid_analysis_skips_the_calls_not_yet_started(client, templates, monkeypatch):
    from routers import zephyr_tool
    monkeypatch.setattr(zephyr_tool, "PLAN_CALLS_AT_ONCE", 1)        # one call at a time: gaps first, then the plan
    monkeypatch.setattr(zephyr_tool, "_run_tool", lambda *a, **k: IE520)
    started, release, asked = threading.Event(), threading.Event(), []

    def ask(template, context, llm_config):
        asked.append(template)
        started.set()
        release.wait(5)
        return {"gaps": [], "notes": []}, None
    monkeypatch.setattr(zephyr_tool, "_ask", ask)
    jid = client.post("/api/zephyr-tool/analyse", json={"url": "x"}).json()["id"]
    assert started.wait(5)
    client.post(f"/api/zephyr-tool/analyse/{jid}/cancel")
    release.set()
    d = _wait(client, jid)
    assert d["state"] == "cancelled" and asked == ["zt_gaps.jinja"]
    assert d["gaps"]["state"] == "done" and d["plans"]["AWPTCM-P3248"]["state"] == "skipped"


@pytest.mark.parametrize("replies, want", [
    (["{not json", '{"deselect": [], "notes": []}'], ({"deselect": [], "notes": []}, None)),
    (["{not json", "still not"], (None, "the model's reply held no usable JSON (none), twice")),
])
def test_a_reply_with_no_usable_json_is_asked_once_more(monkeypatch, replies, want):
    from routers import zephyr_tool
    calls = []

    def fake(template, context, **kw):
        calls.append(template)
        return {"content": replies[len(calls) - 1], "error": None}
    monkeypatch.setattr(zephyr_tool, "run_prompt", fake)
    assert zephyr_tool._ask("zt_gaps.jinja", {}, {}) == want and len(calls) == 2


def test_a_backend_error_is_not_retried(monkeypatch):
    from routers import zephyr_tool
    calls = []
    monkeypatch.setattr(zephyr_tool, "run_prompt",
                        lambda t, c, **kw: calls.append(t) or {"content": "ERROR: no key", "error": True})
    assert zephyr_tool._ask("zt_gaps.jinja", {}, {}) == (None, "ERROR: no key") and len(calls) == 1


def test_analyse_refuses_without_templates_or_url(client, monkeypatch):
    from routers import zephyr_tool
    monkeypatch.setattr(zephyr_tool.db, "load_zt_templates", lambda: None)
    assert client.post("/api/zephyr-tool/analyse", json={"url": "x"}).status_code == 409
    assert client.post("/api/zephyr-tool/analyse", json={"url": "  "}).status_code == 422
    assert client.get("/api/zephyr-tool/analyse/nope").status_code == 404


def test_the_upload_preview_runs_the_tool_in_dry_run_and_never_anything_else(client, monkeypatch):
    from routers import zephyr_tool
    seen = {}

    def fake(cmd, timeout, what, stdin=None):
        seen.update(cmd=cmd, stdin=json.loads(stdin))
        return {"dry_run": True, "calls": [], "counts": {}, "problems": []}
    monkeypatch.setattr(zephyr_tool, "_run_tool", fake)
    body = {"version": "5.5.6-2", "middle": "Tomahawk", "product": "IE570", "number": "3001",
            "plans": [{"key": "AWPTCM-P3248", "name": "Port", "cycles": []}]}
    assert client.post("/api/zephyr-tool/upload/preview", json=body).json()["dry_run"] is True
    assert seen["cmd"] == [str(zephyr_tool.UPLOAD_TOOL), "--dry-run"] and seen["stdin"] == body
    assert client.post("/api/zephyr-tool/upload/preview", json=dict(body, plans=[])).status_code == 422


def test_the_status_line_says_its_time_is_utc(client, templates):
    assert " UTC: 1 plans" in client.get("/api/zephyr-tool/status").json()["message"]


def _model_that_waits_to_be_stopped(monkeypatch, zephyr_tool, calls):
    """A model call that registers with llm_inflight exactly as the real path does and waits
    until it is cancelled (or 5 s), then answers the way a cancelled call answers."""
    import llm
    import llm_inflight

    def run_prompt(template, context, llm_config=None, **kw):
        cid = llm.current_llm_call_id.get("")
        stop = threading.Event()
        llm_inflight.register(cid, template=template)
        llm_inflight.set_cancel(cid, stop.set)
        calls.append(cid)
        try:
            stopped = stop.wait(5)
            return {"content": "ERROR: cancelled by user", "error": True, "cancelled": stopped}
        finally:
            llm_inflight.finish(cid)
    monkeypatch.setattr(zephyr_tool, "run_prompt", run_prompt)


def test_stop_cancels_the_calls_already_with_the_model(client, templates, monkeypatch):
    """Terrence 2026-10-07: Stop must stop calls mid-flight, the same real cancel every other
    Stop button uses — not wait minutes for them to come back."""
    from routers import zephyr_tool
    monkeypatch.setattr(zephyr_tool, "_run_tool", lambda *a, **k: IE520)
    calls = []
    _model_that_waits_to_be_stopped(monkeypatch, zephyr_tool, calls)
    tab = {"X-CK-Session": "tab-A"}
    jid = client.post("/api/zephyr-tool/analyse", json={"url": "x"}, headers=tab).json()["id"]
    end = time.time() + 5
    while len(calls) < 2 and time.time() < end:                    # the plan call and the gaps call
        time.sleep(0.02)
    t0 = time.time()
    r = client.post(f"/api/zephyr-tool/analyse/{jid}/cancel", headers=tab).json()
    d = _wait(client, jid)
    assert r["calls_stopped"] == 2 and time.time() - t0 < 3
    assert d["state"] == "cancelled" and all(c.startswith(f"zt-{jid}-") for c in calls)
    assert d["plans"]["AWPTCM-P3248"]["state"] == "stopped" and d["gaps"]["state"] == "stopped"
    assert d["plans"]["AWPTCM-P3248"]["deselect"] == [] and d["plans"]["AWPTCM-P3248"]["error"] is None


def test_only_the_page_that_started_an_analysis_can_stop_it(client, templates, monkeypatch):
    """"for this user alone" — another seat's Stop is refused and stops nothing."""
    from routers import zephyr_tool
    monkeypatch.setattr(zephyr_tool, "_run_tool", lambda *a, **k: IE520)
    calls = []
    _model_that_waits_to_be_stopped(monkeypatch, zephyr_tool, calls)
    jid = client.post("/api/zephyr-tool/analyse", json={"url": "x"}, headers={"X-CK-Session": "tab-A"}).json()["id"]
    end = time.time() + 5
    while len(calls) < 2 and time.time() < end:
        time.sleep(0.02)
    r = client.post(f"/api/zephyr-tool/analyse/{jid}/cancel", headers={"X-CK-Session": "tab-B"})
    assert r.status_code == 403
    assert client.get(f"/api/zephyr-tool/analyse/{jid}").json()["state"] == "analysing"
    assert client.post(f"/api/zephyr-tool/analyse/{jid}/cancel", headers={"X-CK-Session": "tab-A"}).status_code == 200
    assert _wait(client, jid)["state"] == "cancelled"

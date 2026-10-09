"""Test Composer / Validation — the server half (PLAN-agent-sessions P1, PLAN-test-validation,
PLAN-test-composer). Records are files under a tmp runs dir; mail is captured, never sent;
device-testing is a fake tree; Zephyr and the wiki are fake GETs. What these pin:

  * the hand-off is built and checked HERE (testbox, consoles, PDU, case keys, a Validation run has
    exactly one saved script, scripts only from generated/, templates only from templates/);
  * results come ONLY from marker lines; relayed events are idempotent by seq; cost and tokens
    come from the session's result lines; a NOTIFY mails once, the finish mails once (D5, C-D4);
  * a re-grade sits BESIDE the framework's verdict (grading tier list), never over it;
  * the campaign reader serves only the campaign's own files (the write boundary is read-only);
  * a project link's Test Results cell becomes a variant checklist with each variant's plans;
  * Templated Projects come from ZTT's upload records, older uploads rebuilt from the audit log.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))
sys.path.insert(0, str(_REPO / "ask-ck" / "tools"))

import tc_campaign  # noqa: E402
import tc_mail  # noqa: E402
import tc_projects  # noqa: E402
import tc_runs  # noqa: E402

SCRIPT = '''
class TestSet:
    def init(self):
        dut = setup.init_swi("swi_a")
'''


@pytest.fixture
def env(tmp_path, monkeypatch):
    gen = tmp_path / "generated"
    (gen / "9001_Port").mkdir(parents=True)
    (gen / "9001_Port" / "test-9001.33234.py").write_text(SCRIPT)
    (gen / "9001_Port" / "library_9001.py").write_text("x = 1\n")
    meta = gen / ".meta" / "9001_Port" / "test-9001.33234"
    meta.mkdir(parents=True)
    (meta / "provenance.json").write_text(json.dumps({"case_key": "AWPTCM-T33234", "group": "Port", "saved_at": "2026-09-23"}))
    monkeypatch.setenv("CK_TC_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("CK_PT_GENERATED_DIR", str(gen))
    sent = []

    class FakeSMTP:
        def sendmail(self, frm, to, msg):
            import email
            m = email.message_from_string(msg)
            sent.append({"to": to, "subject": m["Subject"], "msg": m.get_payload(decode=True).decode("utf-8")})
            return {}
        def quit(self):
            pass

    monkeypatch.setattr(tc_mail, "_smtp", lambda: FakeSMTP())
    monkeypatch.delenv("CK_MAIL_DISABLE", raising=False)
    return {"tmp": tmp_path, "gen": gen, "sent": sent}


def body(**kw):
    b = {"kind": "validation", "testbox": "tb470", "consoles": "u0-u5 (u0 = x230)",
         "pdu": {"ip": "10.36.150.14", "outlets": {"u0": 1, "u1": "7", "bad": 3}},
         "constraints": "triage only", "cases": [{"key": "AWPTCM-T33234", "kind": "script", "script": "9001_Port/test-9001.33234.py"}],
         "options": {"email": "terrence.beach@alliedtelesis.co.nz"}}
    b.update(kw)
    return b


# ------------------------------------------------------------------ the hand-off

def test_a_validation_handoff_names_the_script_by_its_absolute_path(env):
    out = tc_runs.create_run(body(), seat="10.33.22.17")
    h = out["handoff"]
    assert tc_runs.RUN_ID_RE.match(h["run_id"]) and h["schema"] == 1
    assert h["cases"] == [{"key": "AWPTCM-T33234", "kind": "script",
                           "script": str(env["gen"] / "9001_Port" / "test-9001.33234.py"),
                           "script_rel": None,                  # tmp is outside the repo
                           "case_payload_rel": "ask-ck/functions/generator/refined-cases/Port/AWPTCM-T33234/zephyr_payload.json"}]
    assert h["pdu"] == {"ip": "10.36.150.14", "outlets": {"u0": 1, "u1": 7}}
    d = tc_runs.run_dir(h["run_id"])
    assert json.loads((d / "handoff.json").read_text()) == h
    assert tc_runs.load(h["run_id"])["state"] == "created"


@pytest.mark.parametrize("change,why", [
    ({"testbox": "tb470; rm"}, "testbox"),
    ({"consoles": ""}, "consoles"),
    ({"pdu": {"ip": "10.0.0"}}, "PDU"),
    ({"cases": [{"key": "T1", "kind": "script"}]}, "bad case key"),
    ({"cases": [{"key": "AWPTCM-T1", "kind": "maybe"}]}, "kind"),
    ({"cases": [{"key": "AWPTCM-T1", "kind": "script", "script": "../../etc/passwd"}]}, "no saved script"),
    ({"cases": []}, "exactly one script"),
    ({"kind": "deploy"}, "kind must"),
    ({"template": "../x"}, "no template"),
    ({"options": {"email": "not-an-address"}}, "email"),
])
def test_the_handoff_refuses_what_it_cannot_trust(env, change, why):
    with pytest.raises(tc_runs.RunError, match=why):
        tc_runs.create_run(body(**change), seat="s")


def test_consoles_are_free_text_as_the_test_engineer_writes_them(env):
    h = tc_runs.create_run(body(consoles="u0-u5 all (u0 = x230 DUT; u2,u4,u5 IE520 stack; u1 AR4050S)"), seat="s")["handoff"]
    assert h["consoles"].startswith("u0-u5 all (u0 = x230 DUT;")
    with pytest.raises(tc_runs.RunError):
        tc_runs.create_run(body(consoles="u0\nrm"), seat="s")


def test_the_script_list_reads_provenance_and_skips_libraries(env):
    s = tc_runs.list_scripts()
    assert [x["path"] for x in s] == ["9001_Port/test-9001.33234.py"]
    assert s[0]["case_key"] == "AWPTCM-T33234"


# ------------------------------------------------------------------ events → record → mail

def _events(*specs):
    return [dict(seq=i, **s) for i, s in enumerate(specs)]


def test_results_come_from_marker_lines_only_and_relays_are_idempotent(env):
    rid = tc_runs.create_run(body(), seat="s")["run_id"]
    evs = _events({"kind": "state", "state": "running"},
                  {"kind": "text", "text": "I think T33234 will PASS"},
                  {"kind": "marker", "line": "RESULT T33234 UNSUPPORTED -- no fixed copper port -- work/run1.log"},
                  {"kind": "result", "total_cost_usd": 3.97, "num_turns": 6,
                   "model_usage": {"opus": {"inputTokens": 10, "outputTokens": 90, "cacheReadInputTokens": 900}}})
    tc_runs.apply_events(rid, evs)
    out = tc_runs.apply_events(rid, evs)                     # relayed twice: nothing doubles
    r = out["record"]
    assert r["results"] == {"AWPTCM-T33234": {"verdict": "UNSUPPORTED", "reason": "no fixed copper port",
                                              "log": "work/run1.log", "seq": 2}}
    assert r["cost_usd"] == 3.97 and r["tokens"] == 1000 and r["turns"] == 6
    assert len(tc_runs.read_events(rid)) == 4
    assert r["state"] == "running" and r["started"]


def test_the_api_relays_events_and_mails_a_notice_once_and_the_finish_once(env, client):
    rid = client.post("/api/test-composer/runs", json=body()).json()["run_id"]
    evs = _events({"kind": "state", "state": "running"},
                  {"kind": "marker", "line": "NOTIFY campaign -- consoles left logged in -- carried on"})
    r = client.post(f"/api/test-composer/runs/{rid}/events", json={"events": evs, "session_id": "s1"}).json()
    assert [m["what"] for m in r["mailed"]] == ["1 notice(s)"] and r["mailed"][0]["error"] is None
    client.post(f"/api/test-composer/runs/{rid}/events", json={"events": evs})
    more = evs + _events({}, {}, {"kind": "marker", "line": "ASKCK-DONE x"}, {"kind": "state", "state": "done"})[2:]
    r = client.post(f"/api/test-composer/runs/{rid}/events", json={"events": more}).json()
    assert [m["what"] for m in r["mailed"]] == ["finished"]
    assert len(env["sent"]) == 2
    assert "consoles left logged in" in env["sent"][0]["msg"] and "did not stop" in env["sent"][0]["msg"]
    got = client.get(f"/api/test-composer/runs/{rid}").json()
    assert got["record"]["state"] == "done" and got["record"]["session_id"] == "s1"
    assert got["table"] == [{"case": "AWPTCM-T33234", "kind": "script", "cycle": None, "verdict": "NOT TESTED",
                             "reason": "", "log": None, "regrade": None}]


def test_a_regrade_sits_beside_the_frameworks_verdict(env, client):
    rid = client.post("/api/test-composer/runs", json=body()).json()["run_id"]
    tc_runs.apply_events(rid, _events({"kind": "marker", "line": "RESULT AWPTCM-T33234 FAIL -- x -- y"}))
    t = client.post(f"/api/test-composer/runs/{rid}/regrade",
                    json={"case": "AWPTCM-T33234", "verdict": "PASS", "note": "DUT fault, script fine"}).json()["table"]
    assert t[0]["verdict"] == "FAIL" and t[0]["regrade"]["verdict"] == "PASS"
    assert client.post(f"/api/test-composer/runs/{rid}/regrade", json={"case": "AWPTCM-T1", "verdict": "PASS"}).status_code == 422
    assert client.post(f"/api/test-composer/runs/{rid}/regrade", json={"case": "AWPTCM-T33234", "verdict": "MAYBE"}).status_code == 422


def test_unknown_runs_are_404_and_malformed_ids_never_reach_the_filesystem(env, client):
    assert client.get("/api/test-composer/runs/2026-10-09T1200-val-ab12").status_code == 404
    assert client.get("/api/test-composer/runs/..%2F..%2Fetc").status_code == 404


# ------------------------------------------------------------------ the campaign's logs

@pytest.fixture
def campaign(env, monkeypatch):
    dt = env["tmp"] / "device-testing"
    fam = dt / "tb470" / "x230v2-28GS"
    case = fam / "port-2026-10-09T1430" / "33234"
    (case / "work").mkdir(parents=True)
    (case / "work" / "run1.log").write_bytes(b"line1\r\nTestCase_1 UNSUPPORTED\x00\r\n")
    (fam / "secret-elsewhere.txt").write_text("no")
    rid = tc_runs.create_run(body(), seat="s")["run_id"]
    (fam / "CAMPAIGN-QUEUE-2026-10-09T1430.md").write_text(
        f"# q\n## Session facts\nTest Engineer: t@h\nDriver: ask-ck ({rid})\n\n## Results\n\n"
        "| case | title | group | verdict | reason | working log | graded-by |\n|---|---|---|---|---|---|---|\n"
        "| 33234 | MDI | port | UNSUPPORTED | no copper | 33234/work/run1.log | tester |\n\n## Issues\n")
    monkeypatch.setenv("CK_DT_ROOT_SERVER", str(dt))
    return rid


def test_the_campaign_reader_finds_the_queue_by_its_driver_line(campaign, client):
    c = client.get(f"/api/test-composer/runs/{campaign}/campaign").json()
    assert c["found"] and c["queue"] == "tb470/x230v2-28GS/CAMPAIGN-QUEUE-2026-10-09T1430.md"
    assert c["results"] == [{"case": "33234", "title": "MDI", "group": "port", "verdict": "UNSUPPORTED",
                             "reason": "no copper", "working log": "33234/work/run1.log", "graded-by": "tester"}]
    assert [f["path"] for f in c["files"]] == ["tb470/x230v2-28GS/port-2026-10-09T1430/33234/work/run1.log"]
    f = client.get(f"/api/test-composer/runs/{campaign}/file", params={"path": c["files"][0]["path"]}).json()
    assert f["data"] == "line1\nTestCase_1 UNSUPPORTED\n" and f["has_more_before"] is False


def test_the_campaign_reader_serves_nothing_outside_the_campaign(campaign, client):
    for p in ("tb470/x230v2-28GS/secret-elsewhere.txt", "../Test-cases/secrets.md", "/etc/passwd"):
        assert client.get(f"/api/test-composer/runs/{campaign}/file", params={"path": p}).status_code == 403


def test_a_large_log_reads_tail_first_then_earlier_on_line_boundaries(campaign, env):
    p = env["tmp"] / "device-testing" / "tb470" / "x230v2-28GS" / "port-2026-10-09T1430" / "33234" / "work" / "run1.log"
    p.write_text("".join(f"line {i}\n" for i in range(20000)))
    rel = "tb470/x230v2-28GS/port-2026-10-09T1430/33234/work/run1.log"
    a = tc_campaign.read_chunk(campaign, rel)
    assert a["data"].endswith("line 19999\n") and a["has_more_before"] and a["data"].startswith("line ")
    b = tc_campaign.read_chunk(campaign, rel, before=a["start"])
    assert b["end"] == a["start"] and b["data"].endswith("\n")
    assert int(b["data"].splitlines()[-1].split()[1]) + 1 == int(a["data"].splitlines()[0].split()[1])


# ------------------------------------------------------------------ projects and variants

RENDERED = ('<p>TB Thu 06-Aug-2026: [edit] <b>Tested</b> x230-52GP V2</p>'
            "<a href=\"https://jira/#/x?tql=testResult.projectKey_IN_('AWPTCM')_AND_testPlan.key_IN_('AWPTCM-P2903','AWPTCM-P2902')_AND_x&title=x230v2+-+52GP+V2+others&period=DAY\">all</a>"
            "<a href=\"https://jira/#/x?tql=testPlan.key_IN_('AWPTCM-P2903')_AND_x&title=x230-52GT+V2&period=DAY\">a</a>"
            "<a href=\"https://jira/#/x?tql=testPlan.key_IN_('AWPTCM-P2902')_AND_x&title=x230-52GP+V2&period=DAY\">b</a>")


def test_the_test_results_cell_lists_one_variant_per_status_call():
    wt = ("| {{Create page|Test:3171 Test Strategy}}||||colspan=\"2\"| Test Results:<br>"
          "{{Test Status v2|5.5.5-2|3171}}{{Test Status v2|5.5.5-2|3171-V2}}{{Test Status v2|5.5.5-2|3171-28V2}}\n|}\n"
          "{{Test Status v2|9.9|elsewhere}}")
    assert tc_projects.status_calls(wt) == [{"version": "5.5.5-2", "project": p} for p in ("3171", "3171-V2", "3171-28V2")]


def test_a_rendered_status_block_gives_its_status_title_and_plans():
    b = tc_projects.parse_status_block(RENDERED)
    assert b["status"] == "Tested" and b["title"] == "x230v2 - 52GP V2 others"
    assert b["plans"] == [{"key": "AWPTCM-P2903", "name": "x230-52GT V2"}, {"key": "AWPTCM-P2902", "name": "x230-52GP V2"}]


def test_from_wiki_renders_each_variant_read_only():
    calls = []

    def get(params, method="GET"):
        calls.append(params)
        assert method == "GET" and params["action"] == "parse"
        if "page" in params:
            return {"parse": {"wikitext": {"*": "Test Results:<br>{{Test Status v2|5.5.5-2|3171-V2}}\n|}"}}}
        return {"parse": {"text": {"*": RENDERED}}}

    out = tc_projects.from_wiki("https://wiki.atlnz.lc/awpwiki/index.php/Project:3171_AT-x230-V2", wiki_get=get)
    assert out["title"] == "Project:3171 AT-x230-V2"       # zt_wiki.page_title: underscores → spaces
    assert [v["project"] for v in out["variants"]] == ["3171-V2"]
    assert out["variants"][0]["plans"][0]["key"] == "AWPTCM-P2903"
    assert calls[1]["text"] == "{{Test Status v2|5.5.5-2|3171-V2}}"


def test_templated_projects_come_from_upload_records_and_the_audit_log(tmp_path, monkeypatch):
    audit = tmp_path / "audit.jsonl"
    audit.write_text("\n".join(json.dumps(e) for e in [
        {"ts": "2026-10-06T23:16", "event": "start", "selection": {"version": "5.5.6-2", "middle": "Tomahawk", "product": "IE570", "number": "3001"}},
        {"ts": "2026-10-06T23:17", "event": "family", "from": "AWPTCM-P3260", "new": {"plan": "AWPTCM-P3266", "cycles": ["AWPTCM-C8470"]}},
        {"ts": "2026-10-06T23:17", "event": "end", "outcome": "done"}]) + "\n")
    ups = tmp_path / "uploads.jsonl"
    ups.write_text(json.dumps({"ts": "2026-10-10T01:00", "version": "5.5.6-2", "product": "IE570", "number": "3001",
                               "plan": "AWPTCM-P3300", "cycles": []}) + "\n")
    monkeypatch.setenv("CK_ZT_AUDIT", str(audit))
    monkeypatch.setenv("CK_ZT_UPLOADS", str(ups))
    p = tc_projects.templated_projects()
    assert len(p) == 1 and p[0]["id"] == "IE570|5.5.6-2|3001"
    assert sorted(p[0]["plans"]) == ["AWPTCM-P3266", "AWPTCM-P3300"]


def test_the_live_tree_is_plan_cycle_case_with_names(monkeypatch):
    data = {"/rest/atm/1.0/testplan/AWPTCM-P1": {"name": "Port", "testRuns": [{"key": "AWPTCM-C1"}]},
            "/rest/atm/1.0/testrun/AWPTCM-C1": {"name": "Port cycle", "items": [{"testCaseKey": "AWPTCM-T1"}, {"testCaseKey": "AWPTCM-T2"}]},
            "/rest/atm/1.0/testcase/AWPTCM-T1": {"name": "speed", "majorVersion": 2},
            "/rest/atm/1.0/testcase/AWPTCM-T2": {"name": "duplex", "majorVersion": 2}}
    t = tc_projects.live_tree(["AWPTCM-P1"], get=lambda p: data[p])
    assert t["plans"][0]["cycles"][0]["cases"] == [{"key": "AWPTCM-T1", "name": "speed", "majorVersion": 2},
                                                   {"key": "AWPTCM-T2", "name": "duplex", "majorVersion": 2}]
    with pytest.raises(tc_projects.ProjectError):
        tc_projects.live_tree(["P1; drop"], get=lambda p: {})


def test_an_empty_template_runs_nothing_and_says_so(env):
    rows = {t["name"]: t for t in tc_projects.templates_with_counts()}
    assert "setup-a" in rows and rows["setup-a"]["runnable_count"] == 0
    assert "empty template" in rows["setup-a"]["note"]


def test_zt_upload_records_each_finished_family(tmp_path):
    import zt_upload
    src = Path(zt_upload.__file__).read_text(encoding="utf-8")
    assert 'record=_audit_to(UPLOADS_LOG)' in src and 'UPLOADS_LOG = AUDIT_LOG.with_name("zt-uploads.jsonl")' in src


def test_a_repeated_notice_and_late_events_after_the_finish_mail_nothing_new(env, client):
    rid = client.post("/api/test-composer/runs", json=body()).json()["run_id"]
    n = "NOTIFY campaign -- consoles left logged in -- carried on"
    evs = _events({"kind": "marker", "line": n}, {"kind": "state", "state": "done"})
    client.post(f"/api/test-composer/runs/{rid}/events", json={"events": evs})
    assert len(env["sent"]) == 2                              # the notice, then the finish
    late = [{"seq": 2, "kind": "marker", "line": n}, {"seq": 3, "kind": "state", "state": "done"}]
    r = client.post(f"/api/test-composer/runs/{rid}/events", json={"events": late}).json()
    assert r["mailed"] == [] and len(env["sent"]) == 2


def test_a_script_outside_generated_is_refused_even_when_it_exists(env):
    (env["tmp"] / "outside.py").write_text("x = 1\n")
    with pytest.raises(tc_runs.RunError, match="no saved script"):
        tc_runs.create_run(body(cases=[{"key": "AWPTCM-T33234", "kind": "script", "script": "../outside.py"}]), seat="s")


def test_the_real_rendering_is_html_escaped_and_still_parses():
    import html
    escaped = RENDERED.replace("'", "&#39;").replace("&title", "&amp;title").replace("&period", "&amp;period")
    assert "&#39;" in escaped and html.unescape(escaped) == RENDERED
    b = tc_projects.parse_status_block(escaped)
    assert [p["key"] for p in b["plans"]] == ["AWPTCM-P2903", "AWPTCM-P2902"] and b["plans"][0]["name"] == "x230-52GT V2"


def test_a_composer_validate_handoff_names_the_templates_setup_relative_to_the_repo(env):
    h = tc_runs.create_run(body(kind="composer-validate", cases=[], template="setup-a"), seat="s")["handoff"]
    assert h["template_setup_rel"] == "ask-ck/functions/test-composer/templates/setup-a/a.setup"
    with pytest.raises(tc_runs.RunError, match="needs a template"):
        tc_runs.create_run(body(kind="composer-validate", cases=[]), seat="s")


def test_a_script_inside_the_repo_also_carries_its_repo_relative_path(env, monkeypatch):
    monkeypatch.delenv("CK_PT_GENERATED_DIR")
    scripts = tc_runs.list_scripts()
    s = next(x for x in scripts if x["case_key"] == "AWPTCM-T33234")
    h = tc_runs.create_run(body(cases=[{"key": "AWPTCM-T33234", "kind": "script", "script": s["path"]}]), seat="s")["handoff"]
    assert h["cases"][0]["script_rel"] == "ask-ck/functions/pytest-creator/generated/9001_Port/test-9001.33234.py"
    assert h["cases"][0]["case_payload_rel"].endswith("/AWPTCM-T33234/zephyr_payload.json")


def test_a_repaired_copy_is_served_beside_the_original_only_from_the_campaign(campaign, env, client):
    d = env["tmp"] / "device-testing" / "tb470" / "x230v2-28GS" / "port-2026-10-09T1430" / "33234" / "work"
    (d / "test-9001.33234.repaired.py").write_text(SCRIPT + "# fixed: import\n")
    rel = "tb470/x230v2-28GS/port-2026-10-09T1430/33234/work/test-9001.33234.repaired.py"
    r = client.get(f"/api/test-composer/runs/{campaign}/repaired", params={"path": rel, "case": "AWPTCM-T33234"}).json()
    assert r["code"].endswith("# fixed: import\n") and r["original"] == SCRIPT
    assert client.get(f"/api/test-composer/runs/{campaign}/repaired",
                      params={"path": "tb470/x230v2-28GS/secret-elsewhere.txt", "case": "AWPTCM-T33234"}).status_code == 403
    assert client.get(f"/api/test-composer/runs/{campaign}/repaired", params={"path": rel, "case": "AWPTCM-T9"}).status_code == 422


def test_notices_that_arrive_together_go_in_one_mail(env, client):
    rid = client.post("/api/test-composer/runs", json=body()).json()["run_id"]
    evs = _events(*[{"kind": "marker", "line": f"NOTIFY AWPTCM-T33234 -- need {i} -- did {i}"} for i in range(3)])
    r = client.post(f"/api/test-composer/runs/{rid}/events", json={"events": evs}).json()
    assert [m["what"] for m in r["mailed"]] == ["3 notice(s)"] and len(env["sent"]) == 1
    assert "3 notices (AWPTCM-T33234)" in env["sent"][0]["subject"] and "3. Scope:" in env["sent"][0]["msg"]


def test_the_finish_mail_counts_cases_as_the_table_shows_them(env, client):
    rid = client.post("/api/test-composer/runs", json=body()).json()["run_id"]
    client.post(f"/api/test-composer/runs/{rid}/events", json={"events": _events({"kind": "state", "state": "done"})})
    assert "1 NOT TESTED" in env["sent"][-1]["subject"]


def test_finalize_refuses_with_its_reasons_and_never_writes_while_v0_is_open(env, client):
    rid = client.post("/api/test-composer/runs", json=body()).json()["run_id"]
    r = client.post(f"/api/test-composer/runs/{rid}/finalize/AWPTCM-T33234")
    assert r.status_code == 409 and "not finished cleanly" in r.json()["detail"] and "REVIEWED" in r.json()["detail"]
    tc_runs.apply_events(rid, _events({"kind": "marker", "line": "REVIEWED AWPTCM-T33234 tb470/x/review.md"},
                                      {"kind": "state", "state": "done"}))
    r = client.post(f"/api/test-composer/runs/{rid}/finalize/AWPTCM-T33234")
    assert r.status_code == 409 and "V0" in r.json()["detail"]
    prov = json.loads((env["gen"] / ".meta/9001_Port/test-9001.33234/provenance.json").read_text())
    assert "finalized_at" not in prov

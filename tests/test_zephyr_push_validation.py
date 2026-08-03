"""Phase −1 — the Zephyr push must validate before it writes to production.

`tool/upload_refined.py` is the only thing in this project that mutates data outside
the repository, in a system the project does not own. Before this suite it:

  * imported no validator of any kind and pushed whatever JSON was on disk;
  * repaired malformed JSON in memory, silently, and pushed the repair;
  * looked for a traceability heading the template stopped emitting, so step 4 of
    the advertised push (web links) did nothing on 12 of 13 bundles and still
    reported success;
  * left no record of any write;
  * and needed one character changed in a URL to turn a preview into a real push.

Everything here is offline: no network, no Zephyr, no testbox, no subprocess that
could reach one. The HTTP tests stop at the 400 that precedes the shell-out, or stub
the shell-out outright.

See ask-ck/ck-facelift/PLAN-pipeline-end-to-end.md, Phase −1.
"""
import json
import pathlib
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
_TOOL = _REPO / "tool"
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
for _p in (str(_TOOL), str(_SERVER)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import upload_refined as ur  # noqa: E402


NOTE = "Note: Related ART Tests linked in Traceability."


def _payload(steps, objective=None):
    """A minimally valid payload, with the caller's steps after the traceability note."""
    if objective is None:
        objective = "<ul><li>One</li><li>Two</li><li>Three</li></ul>"
    return {
        "objective": objective,
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": [{"description": NOTE, "expectedResult": ""}] + list(steps),
        },
    }


# --- −1.1  validate before a live write ----------------------------------------

def test_blank_expected_result_blocks_the_push():
    """A step with no expected result is not a test. 615 of 645 in the corpus have none."""
    p = _payload([{"description": "Verify LLDP neighbours appear", "expectedResult": ""}])
    v = ur.validate_for_push("AWPTCM-T33235", p)
    assert v["valid"] is False
    assert any("expectedResult" in i for i in v["issues"]), v["issues"]


def test_a_complete_payload_passes():
    p = _payload([
        {"description": "Verify LLDP neighbours appear",
         "expectedResult": "show lldp neighbors lists the peer's chassis ID"},
    ])
    v = ur.validate_for_push("AWPTCM-T33235", p)
    assert v["valid"] is True, v["issues"]
    assert v["checked"] is True, "the server shape validator did not run"


def test_the_traceability_note_is_exempt_from_the_expected_result_rule():
    """The server-injected first step is a pointer, not a test — it has no result."""
    p = _payload([
        {"description": "Verify X", "expectedResult": "X happens"},
    ])
    assert ur.blank_expected_results(p) == []


def test_blank_indices_are_reported_so_the_operator_can_find_them():
    p = _payload([
        {"description": "Verify A", "expectedResult": "a"},
        {"description": "Verify B", "expectedResult": ""},
        {"description": "Verify C", "expectedResult": "   "},
    ])
    assert ur.blank_expected_results(p) == [2, 3]


def test_shape_rules_come_from_the_server_not_a_second_copy():
    """A payload whose first step is not the note must fail — via CK_server's validator."""
    p = {"objective": "<ul><li>a</li><li>b</li><li>c</li></ul>",
         "testScript": {"type": "STEP_BY_STEP", "steps": [
             {"description": "Verify something", "expectedResult": "it happens"},
             {"description": "Verify another", "expectedResult": "it also happens"},
         ]}}
    v = ur.validate_for_push("AWPTCM-T33235", p)
    assert v["valid"] is False
    assert any("traceability" in i.lower() for i in v["issues"]), v["issues"]


def test_validation_fails_closed_when_the_server_validator_is_unavailable(monkeypatch):
    """An import failure must never read as a pass — that is the whole point."""
    monkeypatch.setattr(ur, "_server_validator", lambda: None)
    p = _payload([{"description": "Verify X", "expectedResult": "X happens"}])
    v = ur.validate_for_push("AWPTCM-T33235", p)
    assert v["checked"] is False, "an unavailable validator must be reported, not assumed"


def test_the_note_prefix_literal_matches_the_server():
    """upload_refined keeps its own copy so the blank-result rule survives an import
    failure. Pin the two spellings together so the copy cannot drift."""
    import llm
    assert ur._NOTE_PREFIX == llm.TRACEABILITY_NOTE_PREFIX


# --- −1.2  the escape-repair must be loud --------------------------------------

def test_escape_repair_is_reported(tmp_path):
    bad = tmp_path / "zephyr_payload.json"
    bad.write_text(
        '{"AWPTCM-T33235": {"objective": "<ul><li>don\\\'t</li></ul>",'
        ' "testScript": {"steps": []}}}',
        encoding="utf-8",
    )
    key, payload, repairs = ur.load_payload(str(bad))
    assert key == "AWPTCM-T33235", "the repair should still recover the payload"
    assert repairs, "a repaired payload must say so"
    assert "escape-repair" in repairs[0]


def test_a_clean_payload_reports_no_repair(tmp_path):
    good = tmp_path / "zephyr_payload.json"
    good.write_text(json.dumps({"AWPTCM-T33235": _payload([])}), encoding="utf-8")
    key, payload, repairs = ur.load_payload(str(good))
    assert key == "AWPTCM-T33235"
    assert repairs == []


def test_an_unrepairable_payload_returns_no_key(tmp_path):
    bad = tmp_path / "zephyr_payload.json"
    bad.write_text("{not json at all", encoding="utf-8")
    key, payload, repairs = ur.load_payload(str(bad))
    assert key is None and payload is None


# --- −1.3  the traceability heading the template emits is the one we parse ------

def _render_traceability(**ctx):
    """Render the REAL template with jinja, the way the server does."""
    from jinja2 import Environment, FileSystemLoader
    tdir = _SERVER / "templates" / "outputs"
    env = Environment(loader=FileSystemLoader(str(tdir)), undefined=__import__("jinja2").Undefined)
    return env.get_template("traceability.md.jinja").render(**ctx)


def test_the_template_heading_is_parsed_by_the_uploader(tmp_path):
    """Render the real template, parse it with the real parser, and require links out.

    This is the drift-catcher. The parser looked for '(Step 3)' while the template
    emitted '(Step 2)', so parse_zephyr_links returned [] on every current bundle and
    the push reported success having attached nothing.
    """
    md = _render_traceability(
        case_key="AWPTCM-T33235",
        zephyr_selections=[{"key": "AWPTCM-T40001", "title": "Neighbour ageing",
                            "folder": "/LLDP", "objective": "a real objective",
                            "justification": "same feature area"}],
    )
    assert "Zephyr Cross-References" in md, "the template stopped emitting the section"
    assert "AWPTCM-T40001" in md, "the fixture did not reach the template — wrong context key"
    p = tmp_path / "traceability.md"
    p.write_text(md, encoding="utf-8")
    links = ur.parse_zephyr_links(str(p))
    assert links, f"the uploader found no Zephyr links in the rendered template:\n{md}"


def test_parser_accepts_both_step_numbers_the_corpus_actually_contains(tmp_path):
    for n in (2, 3):
        p = tmp_path / f"t{n}.md"
        p.write_text(
            f"## Zephyr Cross-References (Step {n})\n\n"
            f"- [AWPTCM-T40001](https://jira.atlnz.lc/x/AWPTCM-T40001) — a case\n"
            f"\n## Gaps Noted\n\nnone\n",
            encoding="utf-8",
        )
        links = ur.parse_zephyr_links(str(p))
        assert len(links) == 1, f"(Step {n}) heading was not parsed"


def test_the_real_bundles_now_yield_their_links():
    """Regression floor measured on the committed corpus: 12 bundles, 86 links.

    Before the fix this was 1 bundle and 2 links — the single hand-written bundle that
    happened to use the parser's spelling.
    """
    base = _REPO / "ask-ck" / "objective-drafting" / "refined-cases"
    if not base.is_dir():
        pytest.skip("refined-cases/ not present in this checkout")
    total = sum(len(ur.parse_zephyr_links(str(md)))
                for md in sorted(base.glob("*/*/traceability.md")))
    assert total >= 80, f"Zephyr web links regressed to {total} (was 86 at the Phase −1 fix)"


# --- −1.4  audit every real push -----------------------------------------------

def test_audit_writes_a_record(tmp_path, monkeypatch):
    log = tmp_path / "zephyr-push-audit.jsonl"
    monkeypatch.setattr(ur, "AUDIT_PATH", str(log))
    assert ur.audit("push.intent", "AWPTCM-T33235", before={"status": "unrefined"}) is True
    rec = json.loads(log.read_text(encoding="utf-8").strip())
    assert rec["event"] == "push.intent"
    assert rec["key"] == "AWPTCM-T33235"
    assert rec["before"] == {"status": "unrefined"}
    assert rec["ts"] and rec["user"] and "argv" in rec


def test_the_process_never_creates_a_third_version():
    """'Re-push, keep it v2.0' (2026-08-03 decision) is what the tool already does:
    create_new_version bumps 1.0 -> 2.0 and no-ops at 2.0 or above, so a re-push
    updates the working copy in place and can never produce 3.0."""
    assert ur.TARGET_MAJOR_VERSION == 2


def test_the_audit_record_keeps_the_prior_content(tmp_path, monkeypatch):
    """Zephyr keeps no version history of these pushes, so this log is the only place
    the replaced objective survives.

    The v2.0 decision means a re-push overwrites in place. That is deliberate on the
    Zephyr side and is not something to defend against — but it does mean a push that
    writes a worse objective over a better one is unrecoverable without a local record.
    """
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(ur, "AUDIT_PATH", str(log))
    live = {
        "name": "(4) Auto MDI/MDI-X",
        "objective": "<ul><li>the objective about to be replaced</li></ul>",
        "testScript": {"type": "STEP_BY_STEP",
                       "steps": [{"description": "old step", "expectedResult": "old"}]},
    }
    monkeypatch.setattr(ur, "get_jira_key", lambda: "fake-token")
    monkeypatch.setattr(ur, "fetch_case", lambda key, token: live)
    monkeypatch.setattr(ur, "fix_title", lambda *a, **k: ("unchanged", "n", "n"))
    monkeypatch.setattr(ur, "create_new_version",
                        lambda key, token, dry_run=True: (True, {"action": "skipped", "major": 2}))
    monkeypatch.setattr(ur, "put_case", lambda *a, **k: (True, 200))
    monkeypatch.setattr(ur, "attach_file", lambda *a, **k: (True, 200))
    monkeypatch.setattr(ur, "post_tracelinks", lambda *a, **k: (True, 200))
    monkeypatch.setattr(sys, "argv",
                        ["upload_refined.py", "--execute", "--skip-validation", "--force",
                         "--new-version", "--keys", "AWPTCM-T33235"])
    with pytest.raises(SystemExit):
        ur.main()

    events = [json.loads(l) for l in log.read_text(encoding="utf-8").strip().splitlines()]
    assert [e["event"] for e in events] == ["push.intent", "push.version", "push.outcome"], \
        "the intent record must precede the first write"
    before = events[0]["before"]
    assert before["objective"] == live["objective"], "prior objective was not captured"
    assert before["testScript"] == live["testScript"], "prior steps were not captured"
    assert before["name"] == live["name"]


def test_an_in_place_overwrite_is_observed_not_inferred(tmp_path, monkeypatch):
    """Whether the old content survives depends on the VERSION, not on how refined the
    case looks. create_new_version reports action == 'skipped' when the case is already
    at v2.0 — that, and only that, means the push overwrites in place."""
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(ur, "AUDIT_PATH", str(log))
    monkeypatch.setattr(ur, "get_jira_key", lambda: "fake-token")
    monkeypatch.setattr(ur, "fetch_case", lambda key, token: {"objective": "old", "name": "n"})
    monkeypatch.setattr(ur, "fix_title", lambda *a, **k: ("unchanged", "n", "n"))
    monkeypatch.setattr(ur, "create_new_version",
                        lambda key, token, dry_run=True: (True, {"action": "skipped", "major": 2}))
    monkeypatch.setattr(ur, "put_case", lambda *a, **k: (True, 200))
    monkeypatch.setattr(ur, "attach_file", lambda *a, **k: (True, 200))
    monkeypatch.setattr(ur, "post_tracelinks", lambda *a, **k: (True, 200))
    monkeypatch.setattr(sys, "argv",
                        ["upload_refined.py", "--execute", "--skip-validation", "--force",
                         "--new-version", "--keys", "AWPTCM-T33235"])
    with pytest.raises(SystemExit):
        ur.main()

    version = [json.loads(l) for l in log.read_text(encoding="utf-8").strip().splitlines()
               if json.loads(l)["event"] == "push.version"]
    assert version and version[0]["overwrites_in_place"] is True


def test_audit_reports_failure_instead_of_raising(monkeypatch):
    """An unwritable log must return False so the caller can refuse — not explode,
    and above all not silently continue into a production write."""
    monkeypatch.setattr(ur, "AUDIT_PATH", "/proc/definitely/not/writable/audit.jsonl")
    assert ur.audit("push.intent", "AWPTCM-T33235") is False


def test_the_audit_log_is_not_committed():
    """It records production writes and can quote case content."""
    rel = pathlib.Path(ur.AUDIT_PATH).resolve().relative_to(_REPO)
    ignore = (_REPO / ".gitignore").read_text(encoding="utf-8")
    assert "ask-ck/var/*" in ignore, f"{rel} would be committed"


# --- −1.4  a real push needs an explicit per-case confirmation ------------------

def test_execute_without_confirmation_is_refused(client):
    r = client.post("/api/wizard/push_to_zephyr/AWPTCM-T33235?dry_run=false", json={})
    assert r.status_code == 400
    assert "confirm" in r.json()["detail"]


def test_execute_with_the_wrong_key_is_refused(client):
    r = client.post("/api/wizard/push_to_zephyr/AWPTCM-T33235?dry_run=false",
                    json={"confirm": "AWPTCM-T99999"})
    assert r.status_code == 400


def test_a_bare_post_cannot_execute(client):
    """The original exposure: flip one character in the query string, get a real push."""
    r = client.post("/api/wizard/push_to_zephyr/AWPTCM-T33235?dry_run=false")
    assert r.status_code == 400, "a body-less POST must not perform a production write"


def test_dry_run_still_needs_no_confirmation(client, monkeypatch):
    """Preview must stay frictionless — including for a body-less curl."""
    from routers.wizard import export as export_mod

    class _Proc:
        returncode = 0
        stdout = "=== DRY RUN (no changes will be made) ==="
        stderr = ""

    monkeypatch.setattr(export_mod.subprocess, "run", lambda *a, **k: _Proc())
    r = client.post("/api/wizard/push_to_zephyr/AWPTCM-T33235?dry_run=true")
    assert r.status_code == 200
    assert r.json()["dry_run"] is True


def test_confirmation_lets_a_real_push_through(client, monkeypatch):
    """The gate must not be a wall: the right token still reaches the CLI."""
    from routers.wizard import export as export_mod
    seen = {}

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _fake(cmd, **kw):
        seen["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(export_mod.subprocess, "run", _fake)
    r = client.post("/api/wizard/push_to_zephyr/AWPTCM-T33235?dry_run=false",
                    json={"confirm": "AWPTCM-T33235"})
    assert r.status_code == 200, r.text
    assert "--execute" in seen["cmd"], seen.get("cmd")
    assert "--force" not in seen["cmd"], "the UI path must not force"


def test_the_ui_sends_the_token_only_on_execute():
    js = (_SERVER / "static" / "js" / "generator.js").read_text(encoding="utf-8")
    call = js.split("push_to_zephyr", 1)[1][:600]
    assert "confirm: key" in call, "the UI cannot perform a real push any more"
    assert "execute ?" in call, "the token must be conditional on execute"


# --- the end-to-end refusal, offline -------------------------------------------

def test_main_blocks_the_current_corpus_and_exits_nonzero(monkeypatch, capsys):
    """Run the real CLI over the real bundles, offline, and require a refusal.

    Every one of the 53 committed payloads has at least one verification step with no
    expected result, so a correct gate refuses all 53. That is the honest state of the
    corpus; Phases 1–4 are what change it.
    """
    monkeypatch.setattr(ur, "get_jira_key", lambda: None)
    monkeypatch.setattr(ur, "fetch_case", lambda key, token: None)
    monkeypatch.setattr(sys, "argv",
                        ["upload_refined.py", "--dry-run", "--keys", "AWPTCM-T33235"])
    with pytest.raises(SystemExit) as e:
        ur.main()
    err = capsys.readouterr().err
    assert e.value.code != 0, "a blocked push must not exit 0"
    assert "VALIDATION FAILED" in err
    assert "WOULD BLOCK" in err
    assert "blocked by validation" in err


def test_an_unwritable_audit_log_blocks_the_write(monkeypatch, capsys):
    """No audit record, no push. The record is written before the first network call,
    so a case cannot be left half-modified with nothing saying it happened.

    Every network-writing function is stubbed to explode: if a future edit moves the
    audit below them, this test fails rather than quietly reaching Zephyr.
    """
    def _never(*a, **k):
        raise AssertionError("a network write was attempted after the audit log failed")

    monkeypatch.setattr(ur, "get_jira_key", lambda: "fake-token")
    monkeypatch.setattr(ur, "fetch_case", lambda key, token: None)
    monkeypatch.setattr(ur, "audit", lambda *a, **k: False)
    for name in ("fix_title", "create_new_version", "put_case", "attach_file",
                 "post_tracelinks", "gj"):
        monkeypatch.setattr(ur, name, _never)
    monkeypatch.setattr(sys, "argv",
                        ["upload_refined.py", "--execute", "--skip-validation",
                         "--keys", "AWPTCM-T33235"])
    with pytest.raises(SystemExit) as e:
        ur.main()
    err = capsys.readouterr().err
    assert "refusing to write to Zephyr without an audit record" in err
    assert e.value.code != 0


def test_skip_validation_is_available_but_off_by_default(monkeypatch, capsys):
    """The override exists — deliberately pushing a known-imperfect case stays possible."""
    monkeypatch.setattr(ur, "get_jira_key", lambda: None)
    monkeypatch.setattr(ur, "fetch_case", lambda key, token: None)
    monkeypatch.setattr(sys, "argv",
                        ["upload_refined.py", "--dry-run", "--skip-validation",
                         "--keys", "AWPTCM-T33235"])
    with pytest.raises(SystemExit):
        ur.main()
    err = capsys.readouterr().err
    assert "--skip-validation given: pushing anyway" in err

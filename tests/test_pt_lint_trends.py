"""R5 (PLAN-self-healing-generation.md): the lint-trend measurement and the 6.4 alarms.

A prompt or lint change is judged by class counts across runs, not one run someone watched.
Thresholds (Terrence, 2026-09-15): a PROMPT defect when a class touches >=10% of units over the
window OR appears in 3 consecutive runs; a LINT-TEXT defect when a class's repair return rate < 50%.
"""
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))

from routers import pytest_create as pc  # noqa: E402
import db as dbmod  # noqa: E402


def test_lint_class_of_covers_every_per_unit_class():
    cases = {
        "unbound name: `x` at line 3 in TestCase_1 — nothing": "unbound",
        "suite-owned: TestCase_1.main() line 5 unsets `lldp run` — no later case re-sets it": "suite-owned",
        "unknown field: `port_desc` at line 8 in TestCase_6 — `lldp_basic`": "field",
        "line 22: `peer.cmd('x')` selects `portPeer`, which is dutA's port, on peer": "port-owner",
        "contract: TestCase_1.configure() line 40 calls self.failed() — configure()/tear_down() "
        "are config only; the verdict belongs in main()": "verdict-config",
        "TestCase_7.main() line 9: the passed() reason is the step's verify text verbatim — a "
        "verdict should say what was OBSERVED": "verdict-echo",
        "incomplete: 6 TestCase classes for 14": "incomplete",
        "syntax: invalid syntax": "syntax",
        "imports: framework module 'ATFoo' not found": "imports",
        "structure: no TestCase classes": "structure",
        "contract: TestCase_1.main() has no self.log()": "contract",
        "pep8 E501: line too long": "pep8",
        "something nobody classified yet": "other",
    }
    for msg, slug in cases.items():
        assert pc._lint_class_of(msg) == slug, (msg[:40], pc._lint_class_of(msg))


def test_lint_history_entry_counts_by_authority_and_class():
    lint = {"errors": ["unbound name: `x` at line 1 in TestCase_1 — z", "syntax: bad"],
            "warnings": ["pep8 E501: x"], "blocking_errors": ["syntax: bad", "unbound name: `x`"],
            "policy_errors": []}
    e = pc._lint_history_entry(lint, 3, "assemble", 38)
    assert e["by_class"] == {"unbound": 1, "syntax": 1, "pep8": 1}
    assert e["blocking"] == 2 and e["warning"] == 1 and e["units"] == 38 and e["source"] == "assemble"
    assert e["prompt_version"] == pc._generate_prompt_version()


def test_repair_stats_from_chunks():
    chunks = {"tc1": {"status": "ok", "repaired": True, "repaired_class": "suite-owned"},
              "tc2": {"status": "ok", "repaired": True, "repaired_class": "suite-owned"},
              "tc3": {"status": "error", "error": "generated unit has lint error(s): unbound name: `y`"},
              "tc4": {"status": "ok"}}
    st = pc._pt_repair_stats_from_chunks(chunks)
    assert st["suite-owned"] == {"repaired_ok": 2, "arrival_failed": 0}
    assert st["unbound"] == {"repaired_ok": 0, "arrival_failed": 1}


def _pt_row(case, entry, chunks, updated):
    payload = json.dumps({"step6": {"lint_history": [entry], "chunks": chunks}})
    return (f"pt:{case}", "pt", case, payload, None, updated)


def test_prompt_defect_alarm_fires_on_a_recurring_class(monkeypatch):
    # 3 runs each with a suite-owned error -> 3 consecutive runs -> prompt_defect.
    entry = {"by_class": {"suite-owned": 2}, "units": 10}
    rows = [_pt_row(f"T{i}", entry, {}, f"2026-09-15T0{i}:00") for i in range(3)]
    monkeypatch.setattr(dbmod, "snapshot_sessions", lambda: rows)
    tr = pc._pt_lint_trends(window=5)
    assert tr["runs"] == 3
    kinds = {(a["class"], a["kind"]) for a in tr["alarms"]}
    assert ("suite-owned", "prompt_defect") in kinds


def test_lint_text_defect_alarm_fires_on_a_low_return_rate(monkeypatch):
    # one run, a class repaired 1/4 -> return rate 25% < 50% -> lint_text_defect.
    chunks = {"a": {"status": "ok", "repaired": True, "repaired_class": "field"}}
    for i in range(3):
        chunks[f"e{i}"] = {"status": "error", "error": "generated unit has lint error(s): unknown field: `z`"}
    entry = {"by_class": {"field": 1}, "units": 20}
    monkeypatch.setattr(dbmod, "snapshot_sessions", lambda: [_pt_row("T", entry, chunks, "2026-09-15T09:00")])
    tr = pc._pt_lint_trends(window=5)
    assert tr["return_rate"] is not None and tr["return_rate"] < 0.5
    assert any(a["kind"] == "lint_text_defect" and a["class"] == "field" for a in tr["alarms"])


def test_a_clean_window_raises_no_alarm(monkeypatch):
    entry = {"by_class": {}, "units": 38}
    monkeypatch.setattr(dbmod, "snapshot_sessions", lambda: [_pt_row("T", entry, {}, "2026-09-15T09:00")])
    tr = pc._pt_lint_trends(window=5)
    assert tr["alarms"] == [] and tr["runs"] == 1


def test_effective_repair_turns_rises_to_two_below_50_percent(monkeypatch):
    monkeypatch.setattr(pc, "_pt_lint_trends_cached", lambda: {"return_rate": 0.3})
    assert pc._effective_repair_turns() == 2
    monkeypatch.setattr(pc, "_pt_lint_trends_cached", lambda: {"return_rate": 0.8})
    assert pc._effective_repair_turns() == 1
    monkeypatch.setattr(pc, "_pt_lint_trends_cached", lambda: {"return_rate": None})
    assert pc._effective_repair_turns() == 1


def test_no_history_yet_is_a_clean_empty_result(monkeypatch):
    monkeypatch.setattr(dbmod, "snapshot_sessions", lambda: [])
    tr = pc._pt_lint_trends(window=5)
    assert tr["runs"] == 0 and tr["alarms"] == []


def test_the_lint_trends_endpoint_and_health_field_exist():
    src = (_REPO / "ask-ck" / "CK-main" / "CK_server" / "routers" / "pytest_create.py").read_text()
    assert '@router.get("/lint_trends")' in src
    assert 'step6_f["lint_history"] = history[-50:]' in src
    health = (_REPO / "ask-ck" / "CK-main" / "CK_server" / "main.py").read_text()
    assert '"pt_lint_alarms": _pt_lint_alarms()' in health

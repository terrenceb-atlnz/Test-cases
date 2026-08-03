"""A cleanly-parsing but SHORT script must be an error, and must not be confirmable.

PHASE 7.7. The plan calls this "the one to fear": a generation cut between two classes
compiles, passes every structural assertion, and differs from a complete script only in how
many TestCase classes it contains. That single check was a WARNING, wrapped in a blanket
`except Exception`, and `confirm_step` never looked at `lint.ok` — so the artefact most in
need of stopping was the one that sailed through to run and export.

These tests read the source rather than driving the endpoints, because the surrounding
router needs a live session, a corpus and an LLM. What they pin is the CONTRACT: which list
a shortfall lands in, that a failure of the check is not silence, and that confirmation
consults the lint.
"""
import ast
import pathlib
import re

import pytest

ROUTER = (pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"
          / "routers" / "pytest_create.py")
SOURCE = ROUTER.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _function(name):
    for node in ast.walk(TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {ROUTER.name}")


def _segment(node):
    return ast.get_source_segment(SOURCE, node) or ""


# --------------------------------------------------------- the shortfall is a hard error

def test_a_testcase_shortfall_is_an_error_not_a_warning():
    """The check that detects a truncated-but-compiling script must fail the lint."""
    body = _segment(_function("_lint_generated"))
    match = re.search(r"if verify_steps and n_cases < len\(verify_steps\):\s*\n(\s*)(\w+)\.append",
                      body)
    assert match, "the TestCase-shortfall check is gone — that is the truncation detector"
    assert match.group(2) == "errors", (
        f"a TestCase shortfall appends to `{match.group(2)}`, not `errors`. A script that "
        f"compiles but covers fewer steps than the approved sequence is incomplete, and "
        f"warning about it is what let truncated scripts reach the run stage.")


def test_the_shortfall_message_says_regenerate_rather_than_confirm():
    body = _segment(_function("_lint_generated"))
    assert "regenerate rather than confirm" in body


def test_a_failed_completeness_check_is_not_reported_as_clean():
    """`except Exception: pass` on a check means the check can be dead and the lint green."""
    body = _segment(_function("_lint_generated"))
    handler = re.search(r"except Exception as e:\s*\n(.*?)result_coverage = None",
                        body, re.DOTALL)
    assert handler, "the coverage/completeness exception handler moved"
    assert "errors.append" in handler.group(1), (
        "a completeness check that could not RUN is being swallowed. Unknown is not the "
        "same as clean — if the check did not run, the script is unchecked.")


def test_the_source_step_coverage_gap_is_still_only_a_warning():
    """Deliberate asymmetry: a genuinely untestable source step is the reviewer's call.

    Only the script-vs-approved-sequence shortfall is hard. If this ever flips, generation
    becomes permanently blockable by a source step nobody can automate.
    """
    body = _segment(_function("_lint_generated"))
    match = re.search(r"if not cov\[.ok.\]:\s*\n\s*(\w+)\.append", body)
    assert match and match.group(1) == "warnings"


# ------------------------------------------------------------ confirmation checks the lint

def test_confirm_step_refuses_a_script_with_lint_errors():
    body = _segment(_function("confirm_step"))
    assert "lint" in body, "confirm_step still never looks at the lint"
    assert re.search(r"if\s+step\s*==\s*6", body), \
        "the lint gate must be scoped to the Generate step"
    assert 'lint.get("errors")' in body or "lint['errors']" in body


def test_the_lint_gate_is_not_overridable():
    """A broken artefact is not a judgement call, unlike the coverage gap beside it."""
    body = _segment(_function("confirm_step"))
    gate = body[body.index("step == 6"):]
    assert "acknowledge" not in gate.split("_confirm(")[0], (
        "the lint gate accepts an override flag. A lint ERROR means the script itself is "
        "broken — regenerate it rather than acknowledging it.")


def test_an_unlinted_script_cannot_be_confirmed():
    """Absent lint is not a pass: it means nothing has checked this script."""
    body = _segment(_function("confirm_step"))
    assert "Lint the generated script before confirming" in body


def test_the_gate_raises_409_like_its_neighbours():
    body = _segment(_function("confirm_step"))
    gate = body[body.index("step == 6"):body.index("_confirm(")]
    assert gate.count("HTTPException(") >= 2
    assert "409" in gate

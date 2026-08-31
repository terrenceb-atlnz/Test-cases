"""The generated script's STYLE is checked, and an unavailable checker is never "clean".

THE GAP THIS CLOSES (2026-09-01, Terrence's ask)
------------------------------------------------
`_lint_generated` ran py_compile plus a long list of house-rule and contract assertions,
every one of which is about whether the artefact WORKS. Nothing looked at how it READS —
there was no PEP 8 checker anywhere in the pipeline. A generated script is read by a human
before promotion into `testsuites_art/`, and the model has no reason to keep a line under
120 characters unless something says so: measured across the 7 scripts in `generated/`
(3,121 lines), 171 lines exceed 120 characters and the corpus tops out at 799.

Two properties are worth pinning and one is not.

WORTH PINNING: that a style finding is a WARNING. `blocking_errors` means the artefact
provably cannot work; if E501 landed there, the reviewer's only route past a long line
would be a recorded policy override, for whitespace.

WORTH PINNING: that a MISSING pycodestyle is reported, not silently treated as a clean
pass. This is the Phase 7.7 lesson — the coverage check used to be able to die and still
let the lint report green — applied before it can happen again.

NOT PINNED: the value of `_PEP8_MAX_LINE`, or which codes fire. Pinning those turns every
tuning change into a test edit, which trains people to update the assertion instead of
thinking (the same reasoning as `test_llm_call_timeouts`, which deliberately checks that a
timeout ARGUMENT exists rather than what it is).
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402  (CK_server flat-module layout)


CLEAN = (
    "import sys\n"
    "\n"
    "\n"
    "def main():\n"
    "    total = 1 + 2\n"
    "    return total\n"
)


def test_a_clean_script_produces_no_style_findings():
    findings, unavailable = pc._pep8_findings(CLEAN)
    assert unavailable is None, f"pycodestyle should be installed: {unavailable}"
    assert findings == [], f"clean source flagged: {findings}"


def test_a_long_line_is_reported_with_its_line_number():
    src = CLEAN + "    x = '" + ("y" * (pc._PEP8_MAX_LINE + 40)) + "'\n"
    findings, unavailable = pc._pep8_findings(src)
    assert unavailable is None
    assert any("E501" in f for f in findings), findings
    assert any("line 7" in f for f in findings), (
        f"a finding must name the line it is on: {findings}")


def test_real_style_defects_are_caught_not_just_length():
    """Length is the noisy one; these are the quick real fixes it must not drown out.

    W293 (blank line containing whitespace) and E741 (ambiguous name `l`) both occur in
    the current `generated/` corpus — 40 and 9 times respectively — so they are the actual
    return on adding this check, not hypotheticals.
    """
    src = "def main():\n    l = 1\n    \n    return l\n"
    findings, unavailable = pc._pep8_findings(src)
    assert unavailable is None
    codes = " ".join(findings)
    assert "E741" in codes, f"ambiguous name not caught: {findings}"
    assert "W293" in codes, f"whitespace-only blank line not caught: {findings}"


def test_repeated_findings_collapse_to_a_count():
    """A pathological generation can emit 200 E501s; listing every one buries everything
    else. One line per code, with a sample of line numbers and a `+N more` tail."""
    long_line = "    x = '" + ("y" * (pc._PEP8_MAX_LINE + 40)) + "'\n"
    src = CLEAN + long_line * (pc._PEP8_SAMPLE_PER_CODE + 6)
    findings, _ = pc._pep8_findings(src)
    e501 = [f for f in findings if "E501" in f]
    assert len(e501) == 1, f"E501 should collapse to ONE line, got: {e501}"
    assert "occurrences at" in e501[0], e501[0]
    assert "more)" in e501[0], f"the collapsed tail should say how many were hidden: {e501[0]}"
    # And the sample itself must be capped. Asserting only on the "+N more" tail let a
    # mutation that removed the slice pass: the tail is computed separately, so every
    # line number could be listed AND the summary still claim some were hidden.
    named = __import__("re").findall(r"\bline \d+", e501[0])
    assert len(named) == pc._PEP8_SAMPLE_PER_CODE, (
        f"expected at most {pc._PEP8_SAMPLE_PER_CODE} line numbers named, got "
        f"{len(named)}: {e501[0]}")


def test_style_findings_are_warnings_never_blocking():
    """Structural: read the wiring, because this is about which BUCKET the findings land
    in and a unit test on the helper alone cannot see that."""
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    body = src[src.index("def _lint_generated("):]
    body = body[:body.index("\ndef _persist_generated_files(")]
    assert "warnings.extend(_pep8)" in body, (
        "style findings must go into `warnings`; they are not evidence the script cannot "
        "work, and blocking on them would make whitespace need a policy override")
    assert "errors.extend(_pep8)" not in body and "errors.append(_pep8" not in body, (
        "style findings must never be errors")


def test_a_missing_checker_is_reported_rather_than_reported_clean(monkeypatch):
    """`unknown` is not `clean`.

    The failure this prevents is quiet: a host without pycodestyle (the LAN server, or a
    contributor's box — one of the 2026-08-27 commits came from a host with neither pytest
    nor node) would otherwise show an empty style list, which reads as a pass.
    """
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) \
        else __builtins__.__import__

    def _no_pycodestyle(name, *a, **kw):
        if name == "pycodestyle":
            raise ImportError("No module named 'pycodestyle'")
        return real_import(name, *a, **kw)

    monkeypatch.setattr("builtins.__import__", _no_pycodestyle)
    findings, unavailable = pc._pep8_findings(CLEAN)
    assert findings == []
    assert unavailable and "pycodestyle" in unavailable, unavailable


def test_the_unavailable_path_emits_a_warning_that_says_so():
    """Pins the wiring half of the above: the reason must reach the reviewer."""
    src = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
    body = src[src.index("def _lint_generated("):]
    body = body[:body.index("\ndef _persist_generated_files(")]
    assert "_pep8_unavailable" in body and "style NOT checked" in body, (
        "when the checker is missing the lint must say so; an empty style list would "
        "otherwise be indistinguishable from a clean pass")


def test_pycodestyle_is_declared_as_a_runtime_dependency():
    """It runs on the SERVER, not in the test suite, so requirements-dev is the wrong file.

    Declaring it only in requirements-dev.txt is the `paramiko` mistake again: a feature
    used from the day it landed, declared in no runtime manifest, failing politely and far
    from its cause on any fresh venv.
    """
    runtime = (_REPO / "ask-ck" / "CK-main" / "requirements.txt").read_text(encoding="utf-8")
    assert "pycodestyle" in runtime, (
        "pycodestyle must be in requirements.txt — the server lints with it")

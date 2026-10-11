"""The ATTestSet / ATTestCase framework log parser — pure, offline-testable.

Until 2026-10-12 this module was also the PyTest Creator's execution engine: testbox
profiles (secrets.testboxes.json), a paramiko SSH run with a bench preflight, and the
framework read-only guards that run used. Running a script is Validation's job now: it runs
through the seat agent's /test-mode session and device-testing's bench-runner
(PLAN-test-validation, PLAN-agent-sessions), so Ask-CK no longer connects to a testbox.
What stays is the parser: the contract for the log format a generated script must produce,
which the lint and log-format tests are written against.
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Framework log parsing (pure, offline-testable)
# ---------------------------------------------------------------------------

_TS_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}:\s?")
_CASE_START = re.compile(r"^>> test-(.+?)\s*$")
_CASE_END = re.compile(
    r"^<< test-(.+?):\s*(PASS|FAIL|ERROR|UNSUPPORTED)\s*"
    r"\(numPassed:\s*(\d+)\s*numFailed:\s*(\d+)\)")
_PASS_LINE = re.compile(r"^PASS:\s*(.*)$")
# A case the framework never ran because it was already UNSUPPORTED when its turn came
# (PLAN-unsupported-gating, 2026-10-02): the TestSet runs a case only while `supported` is True,
# and such a case writes no `>>`/`<<` block at all. Two lines say why — the framework's own
# marking pass after TestSet.configure() (a `testCasePlatformWithPropertyIncl` gate; T33234
# run 3 dropped all 14 cases this way), and the generated frame's `mark_cases_unsupported`,
# logged by the case that learned it (T33235 since 056114d uses the same words).
_MARKED_BY_FRAMEWORK = re.compile(r"^Test case (\d+) has been marked as unsupported\b\s*(.*)$")
_MARKED_BY_CASE = re.compile(r"^INFO: TestCase_(\d+) marked unsupported before it runs:\s*(.*)$")
# The script the TestSet runs, from the argument list it logs at start: names a not-run case
# `<family>.<case>.<n>` like the cases that did run, even when none did.
_SCRIPT_STEM = re.compile(r"\btest-(\d+\.\d+)\.py\b")
_FAIL_LINE = re.compile(r"^!!FAIL:\s*(.*)$")


# The framework's own rule, mirrored: ATTestSet.py:71 pulls <suite>/<set> out of the script
# filename, and create_log_file() (:108) writes `test-<suite>.<set>.log`. Kept identical on
# purpose — if the framework's pattern ever changes, this is the one place that must follow.
_FW_TESTSET_RX = re.compile(r"test-(\d+)\.(\d+).*\.py")


def _framework_log_name(test_name: str, remote_logs: List[str]) -> Optional[str]:
    """Pick the TESTSET log out of a run directory, never a device transcript.

    Returns None rather than an arbitrary `.log` when the testset log is absent: a run that
    produced no testset log has nothing to parse, and `parse_framework_log` already reports
    that honestly as `empty_log`/`no_results`. Handing it a device console transcript instead
    would parse to zero cases and read as a clean sweep — the exact "empty must not equal
    success" failure that parser was hardened against.
    """
    m = _FW_TESTSET_RX.search(Path(test_name).name)
    if m:
        wanted = "test-%s.%s.log" % (m.group(1), m.group(2))
        if wanted in remote_logs:
            return wanted
    # A script whose name carries no ART identity leaves the framework on its '0' defaults.
    if "test-0.0.log" in remote_logs:
        return "test-0.0.log"
    return None


def parse_framework_log(text: str, expected_cases: Optional[int] = None) -> Dict[str, Any]:
    """Parse an ATTestSet log into per-case results.

    Returns {cases: [{name, result, pass_msgs, fail_msgs, log_lines: [start, end]}],
             numPassed, numFailed, unparsed_fails, status, expected_cases, verdict}
    log_lines are 0-based indexes into the stripped-line list, used to pull
    excerpts for the LLM fix prompt.

    PHASE 11.1 — EMPTY MUST NOT EQUAL SUCCESS. A run that never started parses to zero
    cases, zero passed and zero failed, which is indistinguishable from a clean sweep by
    every downstream check: `numFailed == 0` reads as green. That matters because the most
    likely first-run outcome is exactly this shape — `_ck_bind_link` aborting correctly on
    a bench problem produces a log with no case results at all.

    So the parser now states a `status` rather than leaving it to be inferred from counts:

        empty_log   nothing to parse
        no_results  the log has content but not one case result  <- the dangerous one
        short       fewer case results than the script registered
        ok          every expected case reported

    `expected_cases` comes from the script's own `ts.add_testCase(...)` registrations, so
    "short" is measured against what the script meant to run, not against a guess. This
    must be in place before the first hardware run or the first verdict is untrustworthy
    by construction.
    """
    lines = text.splitlines()
    cases: List[dict] = []
    current: Optional[dict] = None
    unparsed_fails = 0
    marked: Dict[int, tuple] = {}     # case number -> (reason, line index), first mark wins
    stem: Optional[str] = None

    for i, raw in enumerate(lines):
        line = _TS_PREFIX.sub("", raw).rstrip()
        if stem is None:
            m = _SCRIPT_STEM.search(line)
            if m:
                stem = m.group(1)
        m = _MARKED_BY_FRAMEWORK.match(line) or _MARKED_BY_CASE.match(line)
        if m:
            marked.setdefault(int(m.group(1)), (m.group(2).strip(), i))
            continue
        m = _CASE_START.match(line)
        if m:
            if current is not None:  # previous case never closed (crash/abort)
                current["result"] = current.get("result") or "ERROR"
                current["log_lines"][1] = i - 1
                cases.append(current)
            current = {"name": m.group(1), "result": None,
                       "pass_msgs": [], "fail_msgs": [], "log_lines": [i, None]}
            continue
        m = _CASE_END.match(line)
        if m:
            if current is None or m.group(1) != current["name"]:
                # footer without matching header — record standalone
                current = current or {"name": m.group(1), "result": None,
                                      "pass_msgs": [], "fail_msgs": [], "log_lines": [i, None]}
            current["result"] = m.group(2)
            current["numPassed"] = int(m.group(3))
            current["numFailed"] = int(m.group(4))
            current["log_lines"][1] = i
            cases.append(current)
            current = None
            continue
        m = _PASS_LINE.match(line)
        if m:
            if current is not None:
                current["pass_msgs"].append(m.group(1))
            continue
        m = _FAIL_LINE.match(line)
        if m:
            if current is not None:
                current["fail_msgs"].append(m.group(1))
            else:
                unparsed_fails += 1

    if current is not None:  # log ended mid-case
        current["result"] = current.get("result") or "ERROR"
        current["log_lines"][1] = len(lines) - 1
        cases.append(current)

    # A marked case that has no result block was never run: it is UNSUPPORTED, `ran: False`,
    # and it counts as reported — it is the outcome the script asked for, not a gap. (Under -u
    # a marked case does run, and its own `<<` block then wins.) Placed in case-number order.
    def _case_num(name):
        tail = str(name).rsplit(".", 1)[-1]
        return int(tail) if tail.isdigit() else None
    ran_nums = {_case_num(c["name"]) for c in cases}
    if stem is None:
        stem = next((str(c["name"]).rsplit(".", 1)[0] for c in cases if _case_num(c["name"]) is not None
                     and "." in str(c["name"])), None)
    for num, (reason, li) in sorted(marked.items()):
        if num in ran_nums:
            continue
        cases.append({"name": f"{stem}.{num}" if stem else f"TestCase_{num}", "result": "UNSUPPORTED",
                      "ran": False, "reason": reason or "marked unsupported before it ran",
                      "numPassed": 0, "numFailed": 0, "pass_msgs": [], "fail_msgs": [],
                      "log_lines": [li, li]})
    if marked:
        cases.sort(key=lambda c: (_case_num(c["name"]) is None, _case_num(c["name"]) or 0))
    not_run = [c["name"] for c in cases if c.get("ran") is False]

    num_passed = sum(c.get("numPassed", len(c["pass_msgs"])) for c in cases)
    num_failed = sum(c.get("numFailed", len(c["fail_msgs"])) for c in cases)

    if not (text or "").strip():
        status = "empty_log"
    elif not cases:
        status = "no_results"
    elif expected_cases is not None and len(cases) < expected_cases:
        status = "short"
    else:
        status = "ok"

    # One line a human or a grader can act on. NEVER "0 failed" for a run that did not
    # produce results — that is the sentence this whole function exists to stop printing.
    if status == "empty_log":
        verdict = "NO RESULTS — the run produced no log output at all."
    elif status == "no_results":
        verdict = ("NO RESULTS — the log has content but not one test case reported. "
                   "The script almost certainly aborted before its first case (a bench or "
                   "binding problem), so this is NOT a pass.")
    elif status == "short":
        verdict = (f"INCOMPLETE — {len(cases)} of {expected_cases} registered test cases "
                   f"reported. The run stopped early; the missing cases are untested, not "
                   f"passing.")
    else:
        verdict = f"{num_passed} passed, {num_failed} failed across {len(cases)} case(s)."

    # A case that crashed mid-way has result ERROR and contributes NO numFailed, so a
    # failure count alone still reads clean. `ok` therefore requires every case to have
    # reached a verdict, not merely an absence of failures.
    errored = [c["name"] for c in cases if c.get("result") in (None, "ERROR")]
    unsupported = sorted(c["name"] for c in cases if c.get("result") == "UNSUPPORTED")
    if errored and status == "ok":
        verdict = (f"{num_passed} passed, {num_failed} failed, and {len(errored)} case(s) "
                   f"did not reach a verdict ({', '.join(errored[:5])}) — those are "
                   f"errors, not passes.")

    # ONE OUTCOME PER CASE, AND NO GAPS. That is the whole job here (Terrence, 2026-08-04):
    # consistent results, readable results, formatted for future automation, no gaps. Judging
    # whether an UNSUPPORTED case *should* have been unsupported, tracking expected sets, or
    # deciding what a run means, all belong to the next step (Test Composer) and were scope
    # creep — they have been removed.
    #
    # An UNSUPPORTED case reports its own inapplicability AS A FAILURE LINE, so it carries
    # numFailed >= 1 while being classified UNSUPPORTED. All four in the captured log do:
    #
    #     !!FAIL: DUT does not support USB Media
    #     << test-5700.2002.2: UNSUPPORTED (numPassed: 2 numFailed: 1)
    #
    # So the assertion counters cannot classify a case. The framework's own per-case verdict
    # does. Counters are still reported verbatim — they are the log's numbers, not ours.
    failed_cases = [c["name"] for c in cases if c.get("result") == "FAIL"]

    # Exactly one bucket per case. ERROR covers a case that never reached a verdict, which is
    # a GAP rather than an outcome and is why it is counted separately and never as a pass.
    counts = {"PASS": 0, "FAIL": 0, "UNSUPPORTED": 0, "ERROR": 0}
    for c in cases:
        counts[c.get("result") if c.get("result") in counts else "ERROR"] += 1

    # Readable, and stable enough to parse later. The two tallies are LABELLED, because
    # "N passed" is ambiguous between cases and assertions and the log reports both — the
    # captured passing run is 11 cases and 78 assertions, and conflating them is a mistake
    # made while writing this very function.
    if status in ("empty_log", "no_results"):
        summary = "NO RESULTS"
    else:
        summary = (f"cases: {counts['PASS']} passed, {counts['FAIL']} failed, "
                   f"{counts['UNSUPPORTED']} unsupported")
        if not_run:
            summary += f" ({len(not_run)} not run)"
        if counts["ERROR"]:
            summary += f", {counts['ERROR']} no verdict"
        summary += (f" (of {len(cases)}); assertions: {num_passed} passed, "
                    f"{num_failed} failed")

    gaps = []
    if status == "empty_log":
        gaps.append("the run produced no log output at all")
    elif status == "no_results":
        gaps.append("the log has content but not one test case reported, so the script "
                    "aborted before its first case — this is NOT a pass")
    elif status == "short" and expected_cases is not None:
        gaps.append(f"only {len(cases)} of {expected_cases} registered case(s) reported; the "
                    f"rest are untested, not passing")
    if counts["ERROR"]:
        gaps.append(f"{counts['ERROR']} case(s) did not reach a verdict "
                    f"({', '.join(errored[:5])})")
    if unparsed_fails:
        gaps.append(f"{unparsed_fails} failure line(s) could not be attributed to a case")

    verdict = summary + ("" if not gaps else " — " + "; ".join(gaps) + ".")

    return {
        "cases": [{k: v for k, v in c.items()} for c in cases],
        # Verbatim from the log. Note an UNSUPPORTED case contributes to numFailed.
        "numPassed": num_passed,
        "numFailed": num_failed,
        "unparsed_fails": unparsed_fails,
        # One bucket per case — the machine-readable form of the summary line.
        "counts": counts,
        "parsed_cases": len(cases),
        "expected_cases": expected_cases,
        "failed_cases": failed_cases,
        "errored_cases": errored,
        "unsupported_cases": unsupported,
        # The UNSUPPORTED cases the framework skipped before they ran (no bench power cycle).
        "not_run_cases": not_run,
        "status": status,
        # NOT "the test passed" — this says the RESULTS are trustworthy: the run produced
        # results, every registered case reported a verdict, and no failure line is
        # unattributed. Whether the product passed is `counts["FAIL"] == 0`, which a caller
        # can ask directly. Keeping those two questions apart is the point.
        "results_complete": (status == "ok" and not counts["ERROR"] and not unparsed_fails),
        "verdict": verdict,
    }


def expected_case_count(code: str) -> Optional[int]:
    """How many test cases the script registers, from its own `ts.add_testCase(...)` calls.

    Read from the AST rather than by regex so `add_testCase(X('arg'))` counts too. Returns
    None when the script cannot be parsed, so a caller can tell "no expectation" apart from
    "expected zero".
    """
    try:
        tree = ast.parse(code or "")
    except (SyntaxError, ValueError):
        return None
    count = 0
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_testCase"):
            count += 1
    return count


def failure_excerpts(text: str, parsed: Dict[str, Any], context: int = 15,
                     max_chars: int = 4000) -> List[dict]:
    """Bounded log excerpt per failing case, for the fix prompt."""
    lines = text.splitlines()
    out = []
    for c in parsed.get("cases", []):
        if c.get("result") in ("PASS", None):
            continue
        start, end = c.get("log_lines", [0, 0])
        end = end if end is not None else min(start + 80, len(lines) - 1)
        lo = max(0, start)
        hi = min(len(lines), end + context + 1)
        excerpt = "\n".join(lines[lo:hi])
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars // 2] + "\n... [truncated] ...\n" + excerpt[-max_chars // 2:]
        out.append({"case": c["name"], "text": excerpt})
    return out

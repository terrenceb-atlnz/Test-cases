"""`parse_framework_log` — the function every run verdict derives from, previously untested.

PHASE 11.1/11.2. `validate()` and `fix_script` both decide what happened from this parser's
output, and it had no test and no fixture log. The specific danger is that a run which never
started parses to zero cases, zero passed and zero failed — and `numFailed == 0` reads as a
clean sweep to every downstream check.

That is not a hypothetical shape. It is the most likely FIRST hardware run outcome:
`_ck_bind_link` aborting correctly on a bench problem produces exactly this log. So the
parser now states a status instead of leaving it to be inferred from counts, and this file
pins each state before any real run happens.
"""
import pathlib
import re

import pytest

from pt_exec import expected_case_count, parse_framework_log


# THE REAL FORMAT, taken from a captured run (see the fixtures alongside):
#   >> test-5700.2001.10                       case start, no timestamp prefix
#   2026-02-10 08:15:47: PASS: <message>       assertions carry one
#   << test-5700.2001.10: PASS (numPassed: 3 numFailed: 0)
# Inventing this format is how a parser test passes while the parser cannot read a log.
CLEAN_LOG = """\
>> test-5700.2001.10
2026-02-10 08:15:47: PASS: DUT displayed "Verifying release" during bootup
2026-02-10 08:15:56: PASS: Configuration after tear_down matches the initial TestSet config
<< test-5700.2001.10: PASS (numPassed: 2 numFailed: 0)
>> test-5700.2001.20
2026-02-10 08:21:37: PASS: DUT displayed "Booting..." during bootup
<< test-5700.2001.20: PASS (numPassed: 1 numFailed: 0)
"""

FAILING_LOG = """\
>> test-5700.2001.10
2026-02-10 08:15:47: PASS: interval configured
2026-02-10 08:15:48: !!FAIL: expected 6 LLDPDUs, observed 0
<< test-5700.2001.10: FAIL (numPassed: 1 numFailed: 1)
"""

# A bench/binding abort: real output, real traceback, not one case result.
ABORTED_LOG = """\
2026-08-03 10:00:01: Loading setup file tb470.setup
2026-08-03 10:00:02: init_portlink('swi_a', 'swi_b') returned (None, None)
2026-08-03 10:00:03: Traceback (most recent call last):
2026-08-03 10:00:04:   File "./261_lldp_test.py", line 88, in init
2026-08-03 10:00:05: AttributeError: 'NoneType' object has no attribute 'name'
"""

SCRIPT = """\
import sys

class TestCase_1(TestCase):
    def main(self):
        pass

class TestCase_2(TestCase):
    def main(self):
        pass

def main():
    ts.add_testCase(TestCase_1())
    ts.add_testCase(TestCase_2())
    ts.run(sys.argv)
"""


# ------------------------------------------------------------------- the dangerous states

def test_a_run_that_never_started_is_not_a_pass():
    """THE defect. Zero cases, zero failures — and every count-based check reads green."""
    parsed = parse_framework_log(ABORTED_LOG, expected_cases=2)
    assert parsed["status"] == "no_results"
    assert parsed["ok"] is False, "a run with no results must never be ok"
    assert parsed["numFailed"] == 0        # the trap: this is still zero
    assert parsed["numPassed"] == 0
    assert "NO RESULTS" in parsed["verdict"]
    assert "not a pass" in parsed["verdict"].lower()


def test_an_empty_log_is_distinguished_from_an_aborted_one():
    parsed = parse_framework_log("", expected_cases=2)
    assert parsed["status"] == "empty_log"
    assert parsed["ok"] is False
    assert "NO RESULTS" in parsed["verdict"]


def test_a_short_run_reports_the_missing_cases_as_untested():
    """Stopping after case 1 of 2 is not "1 passed" — case 2 is untested, not passing."""
    parsed = parse_framework_log(CLEAN_LOG, expected_cases=5)
    assert parsed["status"] == "short"
    assert parsed["ok"] is False
    assert parsed["parsed_cases"] == 2 and parsed["expected_cases"] == 5
    assert "INCOMPLETE" in parsed["verdict"]
    assert "untested" in parsed["verdict"]


def test_zero_failures_alone_never_makes_a_run_ok():
    """Property: `ok` must require results, not merely the absence of failures."""
    for log, expected in ((ABORTED_LOG, 2), ("", 2), (CLEAN_LOG, 9)):
        parsed = parse_framework_log(log, expected_cases=expected)
        assert parsed["numFailed"] == 0
        assert parsed["ok"] is False, "zero failures was treated as success"


# ----------------------------------------------------------------------- the normal states

def test_a_clean_run_is_ok():
    parsed = parse_framework_log(CLEAN_LOG, expected_cases=2)
    assert parsed["status"] == "ok"
    assert parsed["ok"] is True
    assert (parsed["numPassed"], parsed["numFailed"]) == (3, 0)
    assert parsed["parsed_cases"] == 2
    assert "3 passed" in parsed["verdict"]


def test_a_failing_run_is_parsed_and_not_ok():
    parsed = parse_framework_log(FAILING_LOG, expected_cases=1)
    assert parsed["status"] == "ok"          # it RAN; the status is about completeness
    assert parsed["ok"] is False             # ...but it failed
    assert parsed["numFailed"] == 1
    assert parsed["cases"][0]["fail_msgs"] == ["expected 6 LLDPDUs, observed 0"]


def test_no_expectation_still_parses():
    """`expected_cases=None` means "unknown", not "expected zero"."""
    parsed = parse_framework_log(CLEAN_LOG)
    assert parsed["expected_cases"] is None
    assert parsed["status"] == "ok"
    assert parsed["ok"] is True


def test_a_case_that_never_closed_is_an_error_not_a_pass():
    """A crash mid-case leaves a header with no footer. It must not read as passing."""
    log = ">> test-5700.2001.10\n2026-02-10 08:15:47: PASS: something\n"
    parsed = parse_framework_log(log, expected_cases=1)
    assert parsed["cases"][0]["result"] == "ERROR"
    assert parsed["ok"] is False


# --------------------------------------------------- against REAL captured framework logs
#
# Two runs of the 5700_bootloader suite on an x230v2, committed under tests/fixtures/.
# Hashed credentials in the device config echo were redacted; nothing else was touched.
# Without a real log, a parser test only proves the parser agrees with the format its
# author imagined.

def _fixture(name):
    return (pathlib.Path(__file__).parent / "fixtures" / name).read_text(
        encoding="utf-8", errors="replace")


def test_a_real_passing_run_parses_as_a_clean_sweep():
    parsed = parse_framework_log(_fixture("framework_run_pass.log"))
    assert parsed["parsed_cases"] == 11
    assert (parsed["numPassed"], parsed["numFailed"]) == (78, 0)
    assert parsed["status"] == "ok" and parsed["ok"] is True
    assert {c["result"] for c in parsed["cases"]} == {"PASS"}


def test_a_real_failing_run_parses_every_verdict_kind():
    """The captured failure carries FAIL, UNSUPPORTED, ERROR and PASS in one log."""
    parsed = parse_framework_log(_fixture("framework_run_fail.log"))
    assert parsed["parsed_cases"] == 16
    assert (parsed["numPassed"], parsed["numFailed"]) == (60, 43)
    assert parsed["ok"] is False
    assert {"FAIL", "UNSUPPORTED", "ERROR", "PASS"} <= {c["result"] for c in parsed["cases"]}
    assert parsed["unparsed_fails"] == 0, "every !!FAIL line was attributed to a case"


def test_the_real_logs_are_told_apart():
    """The whole point: a green run and a red run must not produce the same verdict."""
    good = parse_framework_log(_fixture("framework_run_pass.log"))
    bad = parse_framework_log(_fixture("framework_run_fail.log"))
    assert good["ok"] is True and bad["ok"] is False
    assert good["verdict"] != bad["verdict"]


def test_no_credential_survives_in_the_committed_fixtures():
    """These logs echo device configuration. A hash must never ride into the repo."""
    for name in ("framework_run_pass.log", "framework_run_fail.log"):
        text = _fixture(name)
        for match in re.findall(r"(?:password|secret)\s+\d+\s+(\S+)", text):
            assert match == "<REDACTED-HASH>", f"{name} still carries a credential"


# ------------------------------------------------------------------ the expected-case count

def test_expected_case_count_reads_the_scripts_own_registrations():
    assert expected_case_count(SCRIPT) == 2


def test_expected_case_count_counts_registrations_with_arguments():
    """A regex for `add_testCase(X())` misses this and silently under-counts."""
    code = SCRIPT.replace("TestCase_1()", "TestCase_1('arg')")
    assert expected_case_count(code) == 2


def test_expected_case_count_returns_none_for_unparseable_code():
    assert expected_case_count("class Broken(:") is None


def test_end_to_end_a_registered_but_unrun_case_is_visible():
    """The two halves together: what the script meant to run vs what the log shows."""
    expected = expected_case_count(SCRIPT)
    parsed = parse_framework_log(FAILING_LOG, expected_cases=expected)
    assert parsed["status"] == "short"
    assert parsed["parsed_cases"] == 1 and parsed["expected_cases"] == 2
    assert parsed["ok"] is False


# ------------------------------------------------ UNSUPPORTED is reconciled (2026-08-04)
#
# Measured across the real captured logs: 5 of 13 contain UNSUPPORTED, including the run a
# human labelled PASS (7 of 26). And the set is STABLE — two runs of test-5700.2002 on the
# same platform both report exactly {2, 22, 42, 62}. So UNSUPPORTED is a deterministic
# property of (case x platform), which rules out both simple answers: treating it as green
# loses the signal when a case newly stops being tested, and demanding an acknowledgement
# every time fires on 38% of runs for a set that never changes.

# A REALISTIC UNSUPPORTED case. It detects its own inapplicability at run time and reports
# that as a FAILURE line, so the case carries numFailed >= 1 while being classified
# UNSUPPORTED. All four in the captured log look like this. My first version of this fixture
# used `numFailed: 0`, which no real log does — and that hid the fact that "ok requires
# numFailed == 0" made every reconciliation branch unreachable.
UNSUPPORTED_LOG = """\
>> test-5700.2002.2
2026-02-09 11:41:55: PASS: configuration saved
2026-02-09 11:41:55: !!FAIL: DUT does not support USB Media
<< test-5700.2002.2: UNSUPPORTED (numPassed: 1 numFailed: 1)
>> test-5700.2002.4
2026-02-10 08:15:47: PASS: the feature behaves
<< test-5700.2002.4: PASS (numPassed: 1 numFailed: 0)
"""


def test_an_unsupported_set_matching_the_expectation_is_green():
    parsed = parse_framework_log(UNSUPPORTED_LOG, expected_cases=2,
                                 expected_unsupported=["5700.2002.2"])
    assert parsed["unsupported_status"] == "as_expected"
    assert parsed["ok"] is True, "a stable, expected UNSUPPORTED set must not block a run"
    assert "as expected" in parsed["verdict"]


def test_a_newly_unsupported_case_is_a_regression():
    """The signal my original answer lost: a case quietly stops being tested."""
    parsed = parse_framework_log(UNSUPPORTED_LOG, expected_cases=2, expected_unsupported=[])
    assert parsed["unsupported_status"] == "regression"
    assert parsed["ok"] is False
    assert "REGRESSION" in parsed["verdict"]
    assert "no longer being tested" in parsed["verdict"]


def test_a_case_that_started_running_again_is_loud_but_does_not_fail_the_run():
    """Good news, or a false positive in the script's own capability check — either way a
    human decides, and a run whose case results are fine is not failed for it."""
    parsed = parse_framework_log(
        UNSUPPORTED_LOG, expected_cases=2,
        expected_unsupported=["5700.2002.2", "5700.2002.4"])
    assert parsed["unsupported_status"] == "stale_expectation"
    assert parsed["ok"] is True, "a case that started working must not fail the run"
    assert "SUPPORT CHANGED" in parsed["verdict"]
    assert "false positive" in parsed["verdict"]


def test_an_unestablished_expectation_is_provisional_not_blocking():
    """The first run must be able to come back green — it is the run we care most about."""
    parsed = parse_framework_log(UNSUPPORTED_LOG, expected_cases=2)
    assert parsed["unsupported_status"] == "unestablished"
    assert parsed["unsupported_provisional"] is True
    assert parsed["ok"] is True, "the first hardware run must not be blocked by an unset expectation"
    assert "PROVISIONAL" in parsed["verdict"]


def test_a_run_with_no_unsupported_cases_needs_no_expectation():
    parsed = parse_framework_log(CLEAN_LOG, expected_cases=2)
    assert parsed["unsupported_status"] == "none"
    assert parsed["ok"] is True


def test_the_real_logs_unsupported_set_is_stable_across_runs():
    """The measurement the whole design rests on. If this fails, reconciliation is wrong."""
    a = parse_framework_log(_fixture("framework_run_fail.log"))
    observed = set(a["unsupported_cases"])
    assert observed == {"5700.2002.2", "5700.2002.22", "5700.2002.42", "5700.2002.62"}
    # the same set, supplied as the expectation, must reconcile silently
    b = parse_framework_log(_fixture("framework_run_fail.log"),
                            expected_unsupported=sorted(observed))
    assert b["unsupported_status"] == "as_expected"


def test_an_unsupported_case_does_not_fail_the_run_via_its_failure_counter():
    """THE defect my first fixture hid. Real UNSUPPORTED cases carry numFailed >= 1.

    All four in the captured log do:
        << test-5700.2002.2: UNSUPPORTED (numPassed: 2 numFailed: 1)
    so a rule of "ok requires numFailed == 0" could never pass a run containing even an
    entirely expected UNSUPPORTED case, and every reconciliation branch was unreachable.
    """
    parsed = parse_framework_log(UNSUPPORTED_LOG, expected_cases=2,
                                 expected_unsupported=["5700.2002.2"])
    assert parsed["numFailed"] >= 1, "the fixture must carry the real counter shape"
    assert parsed["failed_cases"] == [], "no case actually reported FAIL"
    assert parsed["ok"] is True, \
        "an expected UNSUPPORTED case failed the run through its assertion counter"


def test_the_reported_counters_still_match_the_log_verbatim():
    """The counters are the log's own numbers and must not be quietly adjusted."""
    parsed = parse_framework_log(_fixture("framework_run_fail.log"))
    assert (parsed["numPassed"], parsed["numFailed"]) == (60, 43)


def test_a_real_failing_case_still_fails_the_run():
    parsed = parse_framework_log(FAILING_LOG, expected_cases=1)
    assert parsed["failed_cases"] == ["5700.2001.10"]
    assert parsed["ok"] is False


def test_the_verdict_is_judged_on_case_results_not_counters():
    """A log where counters look bad but every case verdict is fine."""
    log = (">> test-a\n"
           "2026-02-09 11:41:55: !!FAIL: DUT does not support USB Media\n"
           "<< test-a: UNSUPPORTED (numPassed: 0 numFailed: 1)\n")
    parsed = parse_framework_log(log, expected_cases=1, expected_unsupported=["a"])
    assert parsed["numFailed"] == 1 and parsed["failed_cases"] == []
    assert parsed["ok"] is True

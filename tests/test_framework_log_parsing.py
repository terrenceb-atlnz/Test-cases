"""`parse_framework_log` — the function every run result derives from, previously untested.

PHASE 11.1/11.2. `validate()` and `fix_script` both decide what happened from this parser's
output, and it had no test and no fixture log. The original danger: a run that never started
parses to zero cases, zero passed and zero failed — and `numFailed == 0` reads as a clean
sweep to every count-based check. That is the most likely FIRST hardware run outcome, since
`_ck_bind_link` aborting correctly on a bench problem produces exactly that log.

SCOPE (Terrence, 2026-08-04). What this layer owes: **consistent results, readable results,
formatted for future automation, no gaps in results.** Results are PASS / FAIL / UNSUPPORTED
per case, plus ERROR for a case that never reached a verdict. Judging whether an UNSUPPORTED
case *should* have been unsupported, tracking expected sets across runs, and deciding what a
run means belong to the next step (Test Composer). An earlier version of this file tested all
of that — it was scope creep and has been removed.
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

# All three outcomes in one log. The UNSUPPORTED case is REALISTIC: it detects its own
# inapplicability at run time and reports that as a FAILURE line, so it carries
# numFailed >= 1 while being classified UNSUPPORTED. All four in the captured log look like
# this. An earlier fixture here used `numFailed: 0`, which no real log does — and that hid a
# defect where a single UNSUPPORTED case made a whole run unreportable.
MIXED_LOG = """\
>> test-a
2026-02-09 11:41:55: PASS: configuration saved
2026-02-09 11:41:55: !!FAIL: DUT does not support USB Media
<< test-a: UNSUPPORTED (numPassed: 1 numFailed: 1)
>> test-b
2026-02-10 08:15:47: PASS: the feature behaves
<< test-b: PASS (numPassed: 1 numFailed: 0)
>> test-c
2026-02-10 08:15:48: !!FAIL: expected 6 LLDPDUs, observed 0
<< test-c: FAIL (numPassed: 0 numFailed: 1)
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


def _fixture(name):
    return (pathlib.Path(__file__).parent / "fixtures" / name).read_text(
        encoding="utf-8", errors="replace")


# --------------------------------------------------------- consistent: one bucket per case

def test_every_case_lands_in_exactly_one_bucket():
    parsed = parse_framework_log(MIXED_LOG, expected_cases=3)
    assert parsed["counts"] == {"PASS": 1, "FAIL": 1, "UNSUPPORTED": 1, "ERROR": 0}
    assert sum(parsed["counts"].values()) == parsed["parsed_cases"]


def test_an_unsupported_case_is_not_counted_as_a_failing_case():
    """Its own !!FAIL line inflates numFailed; that must not make it a FAIL."""
    parsed = parse_framework_log(MIXED_LOG, expected_cases=3)
    assert parsed["numFailed"] == 2, "counters stay verbatim from the log"
    assert parsed["failed_cases"] == ["c"], "only the genuinely failing case is a FAIL"
    assert parsed["unsupported_cases"] == ["a"]


def test_a_case_that_never_closed_is_an_ERROR_not_a_pass():
    """A crash mid-case leaves a header with no footer."""
    log = ">> test-5700.2001.10\n2026-02-10 08:15:47: PASS: something\n"
    parsed = parse_framework_log(log, expected_cases=1)
    assert parsed["cases"][0]["result"] == "ERROR"
    assert parsed["counts"]["ERROR"] == 1


# --------------------------------------------------------------------- readable + parseable

def test_the_summary_labels_cases_and_assertions_separately():
    """"N passed" is ambiguous between cases and assertions, and the log reports both.

    The captured passing run is 11 cases / 78 assertions. Conflating them is a mistake made
    while writing this function, so the summary names which tally is which.
    """
    parsed = parse_framework_log(MIXED_LOG, expected_cases=3)
    assert parsed["verdict"] == ("cases: 1 passed, 1 failed, 1 unsupported (of 3); "
                                 "assertions: 2 passed, 2 failed")


def test_a_clean_run_summarises_as_all_passed():
    parsed = parse_framework_log(CLEAN_LOG, expected_cases=2)
    assert parsed["verdict"] == ("cases: 2 passed, 0 failed, 0 unsupported (of 2); "
                                 "assertions: 3 passed, 0 failed")
    assert parsed["results_complete"] is True


def test_counters_are_reported_verbatim_and_never_restated():
    parsed = parse_framework_log(_fixture("framework_run_fail.log"))
    assert (parsed["numPassed"], parsed["numFailed"]) == (60, 43)


# --------------------------------------------------------------------------- no gaps

def test_results_complete_is_about_gaps_not_about_passing():
    """A run can be complete and still have failures. The two questions stay separate."""
    parsed = parse_framework_log(MIXED_LOG, expected_cases=3)
    assert parsed["results_complete"] is True, "every registered case reported a verdict"
    assert parsed["counts"]["FAIL"] == 1, "...and one of them failed"


def test_a_run_that_never_started_reports_no_results():
    """THE original defect: zero cases and zero failures read as a clean sweep."""
    parsed = parse_framework_log(ABORTED_LOG, expected_cases=2)
    assert parsed["status"] == "no_results"
    assert parsed["verdict"].startswith("NO RESULTS")
    assert "NOT a pass" in parsed["verdict"]
    assert parsed["results_complete"] is False
    assert parsed["numFailed"] == 0          # the trap: still zero
    assert parsed["counts"] == {"PASS": 0, "FAIL": 0, "UNSUPPORTED": 0, "ERROR": 0}


def test_an_empty_log_is_distinguished_from_an_aborted_one():
    parsed = parse_framework_log("", expected_cases=2)
    assert parsed["status"] == "empty_log"
    assert parsed["results_complete"] is False
    assert "no log output at all" in parsed["verdict"]


def test_a_short_run_names_the_missing_cases_as_untested():
    parsed = parse_framework_log(MIXED_LOG, expected_cases=9)
    assert parsed["status"] == "short"
    assert parsed["results_complete"] is False
    assert "only 3 of 9" in parsed["verdict"]
    assert "untested, not passing" in parsed["verdict"]


def test_a_case_with_no_verdict_is_a_gap():
    log = MIXED_LOG + ">> test-d\n2026-02-10 08:15:49: PASS: partial\n"
    parsed = parse_framework_log(log, expected_cases=4)
    assert parsed["counts"]["ERROR"] == 1
    assert parsed["results_complete"] is False
    assert "no verdict" in parsed["verdict"]


def test_an_unattributed_failure_line_is_a_gap():
    log = "2026-02-10 08:15:49: !!FAIL: something failed outside any case\n" + MIXED_LOG
    parsed = parse_framework_log(log, expected_cases=3)
    assert parsed["unparsed_fails"] == 1
    assert parsed["results_complete"] is False
    assert "could not be attributed" in parsed["verdict"]


def test_no_expectation_still_parses():
    """`expected_cases=None` means "unknown", not "expected zero"."""
    parsed = parse_framework_log(CLEAN_LOG)
    assert parsed["expected_cases"] is None
    assert parsed["status"] == "ok"
    assert parsed["results_complete"] is True


# --------------------------------------------------- against REAL captured framework logs
#
# Two runs of the 5700_bootloader suite on an x230v2, committed under tests/fixtures/.
# Hashed credentials in the device config echo were redacted; nothing else was touched.
# Without a real log, a parser test only proves the parser agrees with the format its author
# imagined — which is exactly what happened on the first attempt at this file.

def test_a_real_passing_run_is_a_clean_sweep():
    parsed = parse_framework_log(_fixture("framework_run_pass.log"))
    assert parsed["counts"] == {"PASS": 11, "FAIL": 0, "UNSUPPORTED": 0, "ERROR": 0}
    assert parsed["results_complete"] is True
    assert parsed["verdict"] == ("cases: 11 passed, 0 failed, 0 unsupported (of 11); "
                                 "assertions: 78 passed, 0 failed")


def test_a_real_failing_run_carries_every_outcome_kind():
    """The captured failure has FAIL, UNSUPPORTED, ERROR and PASS in one log."""
    parsed = parse_framework_log(_fixture("framework_run_fail.log"))
    assert parsed["parsed_cases"] == 16
    assert parsed["counts"]["PASS"] == 1
    assert parsed["counts"]["FAIL"] == 10
    assert parsed["counts"]["UNSUPPORTED"] == 4
    assert parsed["counts"]["ERROR"] == 1
    assert parsed["results_complete"] is False, "one case reached no verdict — that is a gap"
    assert parsed["unparsed_fails"] == 0, "every !!FAIL line was attributed to a case"


def test_the_real_logs_are_told_apart():
    good = parse_framework_log(_fixture("framework_run_pass.log"))
    bad = parse_framework_log(_fixture("framework_run_fail.log"))
    assert good["verdict"] != bad["verdict"]
    assert good["counts"]["FAIL"] == 0 and bad["counts"]["FAIL"] > 0


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
    assert expected_case_count(SCRIPT.replace("TestCase_1()", "TestCase_1('arg')")) == 2


def test_expected_case_count_returns_none_for_unparseable_code():
    assert expected_case_count("class Broken(:") is None


def test_end_to_end_a_registered_but_unrun_case_is_visible():
    """What the script meant to run, against what the log shows."""
    parsed = parse_framework_log(FAILING_LOG, expected_cases=expected_case_count(SCRIPT))
    assert parsed["status"] == "short"
    assert parsed["parsed_cases"] == 1 and parsed["expected_cases"] == 2
    assert parsed["results_complete"] is False

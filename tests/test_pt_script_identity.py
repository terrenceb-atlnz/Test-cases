"""A generated script must be able to carry its ART identity, and its log must be found.

Why this exists (2026-09-17). The framework derives everything from the script's FILENAME:
`ATTestSet.py:71` matches `test-(\\d+).(\\d+).*\\.py`, and `create_log_file()` writes
`test-<suite>.<set>.log`. When the pattern does not match, the defaults at `ATTestSet.py:53`
(`testSuiteNum = testSetNum = '0'`) silently stand — the framework's own guard against '0'
sits INSIDE the `if m:` branch, so it never fires.

`_NAME_RX` forbade dots, so a generated script could never be named `test-9000.33233.py`.
Every generated run therefore wrote `test-0.0.log` with cases named `0.0.<n>`, and
`pt_exec` — which looked for the script basename plus `.log` — missed it and fell back to
`remote_logs[0]`, an arbitrary `.log` in the workdir. A run leaves one console transcript
PER DEVICE there, so that fallback could return `swi_a.log`; parsing a device transcript
yields zero cases, which every downstream count reads as a clean sweep.

Two fixes, both pinned here: the name may carry dots (and must still reject `..`), and the
log is resolved the framework's way or not at all.

Offline: no network, no SSH, no framework.
"""
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


@pytest.fixture
def px():
    import pt_exec
    return pt_exec


# --- the name may carry the ART identity -------------------------------------------

@pytest.mark.parametrize("name", ["test-9000.33233", "test-9000.0301", "test-1342.0301"])
def test_art_identity_names_are_accepted(pc, name):
    group, out = pc._validate_naming("Port", name)
    assert out == name, "a generated script must be able to carry <suite>.<set>"


@pytest.mark.parametrize("bad", [
    "../../evil", "..", "test-9000..33233", "a/b", "a\\b", ".hidden", "",
])
def test_traversal_and_junk_still_rejected(pc, bad):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        pc._validate_naming("Port", bad)
    assert ei.value.status_code == 400


def test_the_dot_did_not_open_traversal(pc):
    # The specific regression the no-dots rule used to prevent by construction.
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        pc._validate_naming("Port", "../../../etc/passwd")


# --- the log is resolved the framework's way ----------------------------------------

def test_testset_log_is_preferred_over_device_transcripts(px):
    logs = ["swi_a.log", "test-9000.33233.log", "swi_b.log", "pdu.log"]
    assert px._framework_log_name("test-9000.33233.py", logs) == "test-9000.33233.log"


def test_device_transcript_is_never_returned_as_the_run_log(px):
    # THE bug: remote_logs[0] handed back a device console transcript, which parses to
    # zero cases and reads as success.
    logs = ["swi_a.log", "swi_b.log"]
    assert px._framework_log_name("test-9000.33233.py", logs) is None


def test_missing_log_returns_none_rather_than_a_guess(px):
    assert px._framework_log_name("test-9000.33233.py", []) is None


def test_dotless_name_falls_back_to_the_frameworks_zero_defaults(px):
    # A legacy/dotless script leaves the framework on testSuiteNum=testSetNum='0'.
    logs = ["swi_a.log", "test-0.0.log"]
    assert px._framework_log_name("MDIX_test.py", logs) == "test-0.0.log"


def test_the_log_name_is_not_the_script_basename(px):
    # The old rule, and the docs at PLAN-pytest-creator.md:230, said basename + .log.
    logs = ["MDIX_test.log", "swi_a.log"]
    assert px._framework_log_name("MDIX_test.py", logs) != "MDIX_test.log"


def test_suite_and_set_are_taken_from_the_name_not_invented(px):
    logs = ["test-9000.33234.log", "test-9000.33233.log"]
    assert px._framework_log_name("test-9000.33234.py", logs) == "test-9000.33234.log"


def test_resolver_mirrors_the_frameworks_own_pattern(px):
    # If the framework's regex ever changes, this file is the one place that must follow.
    assert px._FW_TESTSET_RX.pattern == r"test-(\d+)\.(\d+).*\.py"


# --- a device transcript must not parse as a passing run -----------------------------

def test_a_device_transcript_parses_as_no_results_not_success(px):
    transcript = "awplus#show interface port1.1.1\n  Link is UP\nawplus#\n"
    out = px.parse_framework_log(transcript)
    assert out["status"] in {"empty_log", "no_results"}
    assert out["cases"] == []

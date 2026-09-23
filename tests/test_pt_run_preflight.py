"""Plan 10.4 (2026-09-23): the Run path checks the bench BEFORE touching hardware.

WHY. `pt_preflight` was a well-tested library that nothing in the product called: `POST /run`
dispatched to hardware with no topology check at all, and a missing cable then surfaced as a
script defect mid-run (`init_portlink()` returns (None, None) silently). Terrence's call: block,
allow an override — preflight has no CANNOT-DETERMINE verdict yet and can be wrong.

Pinned: the run thread reads the chosen .setup over the SAME SSH connection, stops as
`preflight_failed` with the report when UN-RUNNABLE (nothing uploaded), proceeds when runnable,
records a "run anyway" skip, and never blocks on a preflight that itself could not run. The
page shows the refusal and the override. Offline: a fake SSH client, no testbox.
"""
import io
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))
pytest.importorskip("paramiko")
import pt_exec  # noqa: E402

BENCH = """
[switch]
swi_a = /dev/u4
swi_c = /dev/u1

[portlink]
tb-swi_a = eth3-port1.0.23
"""
SCRIPT = """
class TestSet(object):
    def init(self, setup):
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_c')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
"""


class _File(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Sftp:
    def __init__(self, text, fail=False):
        self.text, self.fail = text, fail

    def open(self, path, mode="r"):
        if self.fail:
            raise IOError("no such file")
        return _File(self.text.encode())

    def close(self):
        pass


class _Client:
    def __init__(self, text, fail=False):
        self.sftp, self.closed = _Sftp(text, fail), False

    def open_sftp(self):
        return self.sftp

    def close(self):
        self.closed = True


def _gate(bench, run_extra=None, fail=False):
    run = {"test_file": "test-9001.1.py", "status": "connecting", **(run_extra or {})}
    seen = []
    client = _Client(bench, fail)
    ok = pt_exec._preflight_gate(client, run, {"test-9001.1.py": SCRIPT}, "/cfg/tb.setup",
                                 lambda r: seen.append(dict(r)))
    return ok, run, client


def test_an_unrunnable_script_stops_before_anything_is_uploaded():
    ok, run, client = _gate(BENCH)
    assert ok is False and client.closed
    assert run["status"] == "preflight_failed" and run["finished_at"]
    assert run["preflight"]["runnable"] is False and run["preflight"]["problems"]
    assert "nothing was executed" in run["error"]


def test_a_runnable_script_proceeds():
    bench = BENCH.replace("tb-swi_a = eth3-port1.0.23",
                          "tb-swi_a = eth3-port1.0.23\nswi_a-swi_c = port1.0.1-port1.0.1")
    ok, run, _client = _gate(bench)
    assert ok is True and run["preflight"]["runnable"] is True


def test_run_anyway_skips_and_is_recorded():
    ok, run, _client = _gate(BENCH, {"preflight": "skip"})
    assert ok is True and run["preflight"] == {"skipped": True}


def test_a_preflight_that_cannot_run_does_not_block():
    ok, run, _client = _gate(BENCH, fail=True)
    assert ok is True and "could not run" in run["preflight"]["error"]


def test_the_page_offers_the_override_and_stops_polling_on_a_refusal():
    js = (_REPO / "ask-ck" / "frontend" / "ck-main" / "current" / "pytest-creator"
          / "pytest.js").read_text(encoding="utf-8")
    assert 'data-action="ptRunAnyway"' in js and "ignore_preflight: ignorePreflight === true" in js
    assert "'preflight_failed'" in js
    router = (_REPO / "ask-ck" / "CK-main" / "CK_server" / "routers" / "pytest_create.py").read_text()
    assert '"preflight": "skip" if body.get("ignore_preflight") else None' in router

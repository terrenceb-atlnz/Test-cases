"""POST /api/zephyr-tool/upload/run — the real upload's job (PLAN-zephyr-templating.md §5b P5, P6).

The tool itself (`zt_upload.py --apply`) is tested in test_zt_upload.py; here `_open_upload` is a
fake process printing the tool's progress lines, so nothing reaches Zephyr.
"""
from __future__ import annotations

import io
import json
import threading
import time

import pytest

SEL = {"version": "5.5.6-2", "middle": "Tomahawk", "product": "IE570", "number": "3001",
       "plans": [{"key": "AWPTCM-P3256", "name": "Bootloader Tests", "cycles": []}]}


class FakeProc:
    def __init__(self, lines, rc=0, stderr="", gate=None):
        self._lines, self._rc, self.stderr, self._gate = lines, rc, io.StringIO(stderr), gate

    @property
    def stdout(self):
        for ln in self._lines:
            if self._gate:
                self._gate.wait(5)
            yield json.dumps(ln) + "\n"

    def wait(self):
        return self._rc


def _wait(client, job_id, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        d = client.get(f"/api/zephyr-tool/upload/run/{job_id}").json()
        if d["state"] != "running":
            return d
        time.sleep(0.02)
    raise AssertionError("upload still running")


@pytest.fixture
def launched(monkeypatch):
    from routers import zephyr_tool
    calls = []

    def fake(lines, **kw):
        def open_upload(cmd, stdin):
            calls.append((cmd, json.loads(stdin)))
            return FakeProc(lines, **kw)
        monkeypatch.setattr(zephyr_tool, "_open_upload", open_upload)
    with zephyr_tool._runs_lock:
        zephyr_tool._runs.clear()
    return fake, calls


def test_a_confirmed_upload_runs_the_tool_and_reports_its_progress(client, launched):
    fake, calls = launched
    fake([{"type": "step", "msg": "clone plan: POST … → 200"},
          {"type": "result", "outcome": "done", "created": [{"kind": "plan", "id": 1}], "done": ["AWPTCM-P3256"],
           "skipped": [], "error": None}])
    r = client.post("/api/zephyr-tool/upload/run", json=dict(SEL, confirm_product="IE570", confirm_version="5.5.6-2"))
    d = _wait(client, r.json()["id"])
    assert d["state"] == "done" and d["steps"][0]["msg"].startswith("clone plan") and d["result"]["done"] == ["AWPTCM-P3256"]
    cmd, stdin = calls[0]
    assert cmd[1:6] == ["--apply", "--confirm-product", "IE570", "--confirm-version", "5.5.6-2"] and "--seat" in cmd
    assert "confirm_product" not in stdin and stdin["plans"] == SEL["plans"]


@pytest.mark.parametrize("product,version", [("IE570", "5.5.6-1"), ("IE520", "5.5.6-2"), ("", "")])
def test_the_typed_product_and_version_must_match_or_nothing_starts(client, launched, product, version):
    fake, calls = launched
    fake([])
    r = client.post("/api/zephyr-tool/upload/run", json=dict(SEL, confirm_product=product, confirm_version=version))
    assert r.status_code == 422 and "nothing was written" in r.json()["detail"] and calls == []


def test_one_upload_at_a_time(client, launched):
    fake, calls = launched
    gate = threading.Event()
    fake([{"type": "result", "outcome": "done", "created": [], "done": [], "skipped": [], "error": None}], gate=gate)
    body = dict(SEL, confirm_product="IE570", confirm_version="5.5.6-2")
    first = client.post("/api/zephyr-tool/upload/run", json=body)
    second = client.post("/api/zephyr-tool/upload/run", json=body)
    assert first.status_code == 200 and second.status_code == 409 and len(calls) == 1
    gate.set()
    assert _wait(client, first.json()["id"])["state"] == "done"


def test_a_tool_that_dies_without_a_result_is_an_error_with_its_stderr(client, launched):
    fake, _ = launched
    fake([{"type": "step", "msg": "clone plan: POST … → 200"}], rc=1, stderr="Traceback: boom")
    r = client.post("/api/zephyr-tool/upload/run", json=dict(SEL, confirm_product="IE570", confirm_version="5.5.6-2"))
    d = _wait(client, r.json()["id"])
    assert d["state"] == "error" and "boom" in d["error"] and len(d["steps"]) == 1


def test_a_stopped_upload_says_where_it_stopped(client, launched):
    fake, _ = launched
    fake([{"type": "result", "outcome": "stopped", "stopped_at": "AWPTCM-P3256", "error": "move cycle answered 500",
           "created": [{"kind": "plan", "id": 1}], "done": [], "skipped": []}], rc=1)
    r = client.post("/api/zephyr-tool/upload/run", json=dict(SEL, confirm_product="IE570", confirm_version="5.5.6-2"))
    d = _wait(client, r.json()["id"])
    assert d["state"] == "stopped" and d["result"]["stopped_at"] == "AWPTCM-P3256"

"""Plan 9.1c (2026-09-23): pressing Lint (or Fix) must not overwrite the script on disk.

WHY. `ptLintScript()` pushes the textarea into the session first ("so lint sees them") via
`ptPushCodeEdits(false)`, but that helper always POSTed `/save_script/`, whose last act is
`_persist_generated_files` — the `writeFiles` argument was dead. So the reviewer's first
instinct after a bad fix, "press Lint to see how bad", wrote the bad textarea over the last
good `generated/…/test-*.py`. Now the page sends `write_files`, and only Save writes.
Offline: real module, monkeypatched persistence.
"""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))
pytest.importorskip("models")
from routers import pytest_create as pc  # noqa: E402

JS = _REPO / "ask-ck" / "frontend" / "ck-main" / "current" / "pytest-creator" / "pytest.js"


def _run(monkeypatch, body):
    sess = SimpleNamespace(step6={"files": {"test": {"name": "t.py", "code": "old"}},
                                  "naming": {"group": "g", "name": "t"}})
    wrote = []
    monkeypatch.setattr(pc, "_pt_get", lambda key: sess)
    monkeypatch.setattr(pc, "_pt_persist", lambda s: None)
    monkeypatch.setattr(pc, "_invalidate_from", lambda s, n: None)
    monkeypatch.setattr(pc, "_lint_generated", lambda s: {"ok": True, "errors": []})
    monkeypatch.setattr(pc, "_persist_generated_files", lambda s: wrote.append(1) or ["t.py"])
    out = asyncio.run(pc.save_script("AWPTCM-T1", body))
    return sess, wrote, out


def test_lint_push_updates_the_session_but_not_the_disk(monkeypatch):
    sess, wrote, out = _run(monkeypatch, {"code": "new", "write_files": False})
    assert sess.step6["files"]["test"]["code"] == "new"
    assert wrote == [] and out["written"] == []


def test_save_still_writes_and_an_old_client_still_writes(monkeypatch):
    for body in ({"code": "new", "write_files": True}, {"code": "new"}):
        _sess, wrote, out = _run(monkeypatch, body)
        assert wrote == [1] and out["written"] == ["t.py"]


def test_the_page_sends_the_flag_it_is_given():
    src = JS.read_text(encoding="utf-8")
    body = src[src.index("async function ptPushCodeEdits"):src.index("async function ptSaveScript")]
    assert "body.write_files = !!writeFiles" in body


def test_save_can_repoint_the_library_file_name(monkeypatch):
    sess = SimpleNamespace(step6={"files": {"test": {"name": "t.py", "code": "old"},
                                            "library": {"name": "library_awptcm_t1.py", "code": "x"}},
                                  "naming": {"group": "g", "name": "t"}})
    monkeypatch.setattr(pc, "_pt_get", lambda key: sess)
    monkeypatch.setattr(pc, "_pt_persist", lambda s: None)
    monkeypatch.setattr(pc, "_invalidate_from", lambda s, n: None)
    monkeypatch.setattr(pc, "_lint_generated", lambda s: {"ok": True, "errors": []})
    monkeypatch.setattr(pc, "_persist_generated_files", lambda s: [])
    asyncio.run(pc.save_script("AWPTCM-T1", {"library_name": "library_9001.py", "write_files": False}))
    assert sess.step6["files"]["library"]["name"] == "library_9001.py"
    for bad in ("../evil.py", "x/library.py", "library_9001", "a b.py"):
        with pytest.raises(pc.HTTPException):
            asyncio.run(pc.save_script("AWPTCM-T1", {"library_name": bad}))

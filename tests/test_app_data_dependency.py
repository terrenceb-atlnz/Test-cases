"""The wizard's `get_data` dependency must serve app.state.app_data, never rebuild it.

`get_data` used to be `return load_all_data()`, carrying the comment "Would be from
app.state in a fuller implementation". That TODO was load-bearing: all 11 endpoints
depending on it rebuilt the entire reference set per request — re-reading zephyr_master,
every candidate, decisions and two json_docs from ck.db, plus a startup_check() that
counts all four corpora. Measured 47ms (70ms on py3.10) of redundant work per request,
in a threadpool worker, plus three lines of stdout per call and no guarantee that two
dependencies in one request saw the same snapshot.

main.py had assigned app.state.app_data at startup since forever and nothing read it;
pytest_create always did it correctly. These tests pin the fixed contract so the TODO
cannot quietly come back.
"""
import ast
import pathlib

import pytest

_WIZARD = (pathlib.Path(__file__).resolve().parents[1]
           / "ask-ck" / "CK-main" / "CK_server" / "routers" / "wizard.py")


class _FakeRequest:
    """Minimal stand-in: get_data only reaches request.app.state.app_data."""

    def __init__(self, app_data):
        state = type("S", (), {})()
        if app_data is not _MISSING:
            state.app_data = app_data
        self.app = type("A", (), {"state": state})()


_MISSING = object()


def _get_data():
    import routers.wizard as wizard
    return wizard.get_data


def test_returns_the_exact_app_state_object_not_a_copy():
    """Identity, not equality — the whole point is that nothing is rebuilt.

    This is the assertion that fails if someone reintroduces a per-request build,
    regardless of HOW they import load_all_data.
    """
    sentinel = {"zephyr_master": {}, "_marker": object()}
    got = _get_data()(_FakeRequest(sentinel))
    assert got is sentinel


def test_repeated_calls_return_the_same_object():
    """Two dependencies resolved in one request must see one snapshot."""
    sentinel = {"zephyr_master": {}}
    fn, req = _get_data(), _FakeRequest({"zephyr_master": {}})
    req.app.state.app_data = sentinel
    assert fn(req) is fn(req) is sentinel


@pytest.mark.parametrize("value", [None, {}, _MISSING], ids=["none", "empty", "absent"])
def test_missing_app_data_is_a_clean_503(value):
    """Fail loud rather than fall back to load_all_data().

    A silent fallback would restore the per-request cost invisibly AND mask a boot
    problem. Mirrors pytest_create._data. Safe because startup always runs in
    production and conftest drives the app via `with TestClient(...)`, the
    context-manager form that fires startup events.
    """
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _get_data()(_FakeRequest(value))
    assert exc.value.status_code == 503
    assert "not loaded" in str(exc.value.detail).lower()


def test_get_data_does_not_call_load_all_data():
    """Source-level backstop, in case a future edit rebuilds via a different name.

    The identity test above is the real guard; this one names the specific regression
    so a failure explains itself.
    """
    tree = ast.parse(_WIZARD.read_text(encoding="utf-8"))
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "get_data"), None)
    assert fn is not None, "get_data disappeared from wizard.py"
    called = {n.func.id for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "load_all_data" not in called, (
        "get_data must serve app.state.app_data, not rebuild the corpus per request")


def test_endpoints_serve_the_startup_snapshot(client):
    """End-to-end: the dependency resolves for real requests, and app_data is shared.

    `client` is the session TestClient from conftest (context-manager form, so startup
    has run). Uses keyword mode so no embedding model is involved.
    """
    import CK_server.main as main

    assert getattr(main.app.state, "app_data", None), "startup did not populate app_data"
    before = main.app.state.app_data

    r = client.get("/api/wizard/cases")
    assert r.status_code == 200
    r = client.get("/api/wizard/search_testlink", params={"q": "port", "mode": "keyword"})
    assert r.status_code == 200

    # Serving requests must not have swapped or rebuilt the snapshot.
    assert main.app.state.app_data is before

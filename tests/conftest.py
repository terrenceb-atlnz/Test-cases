"""Shared fixtures for the Ask CK backend tests.

Provides a FastAPI TestClient over the real app. Importing the app pulls in the DB
layer (ck.db is the committed source of truth and present in a normal checkout), so
these are in-process integration tests, not mocks.

Note on interpreter: run with `PYTHONNOUSERSITE=1 .venv/bin/pytest` so an older
fastapi/starlette in ~/.local can't shadow the venv's. pytest.ini sets pythonpath;
this file also prepends both dirs defensively for direct `python -m pytest` runs.
"""
import os
import sys
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CK_MAIN = _REPO_ROOT / "ask-ck" / "CK-main"
_CK_SERVER = _CK_MAIN / "CK_server"
for _p in (str(_CK_MAIN), str(_CK_SERVER)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(scope="session")
def client():
    try:
        from fastapi.testclient import TestClient
    except Exception as e:  # pragma: no cover - env guard
        pytest.skip(f"TestClient unavailable ({e}); install requirements-dev.txt with the venv interpreter")
    import CK_server.main as main
    with TestClient(main.app) as c:
        yield c

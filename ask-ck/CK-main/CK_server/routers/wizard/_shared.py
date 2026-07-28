"""Shared surface for the wizard router package.

Holds the per-request data dependency (`get_data`) and the export template
environment (`OUTPUTS_ENV`) — the two things more than one route module needs. Split
out of `routers/wizard.py` (PLAN-backend-module-split.md commit 10) so the four route
modules (reviews / config / synthesis / export) can import it without importing each
other or the package `__init__`, which would be an import cycle.

This module is part of the router LAYER, so importing FastAPI here is fine — unlike the
pure leaves (`llm_config`, `case_registry`, `session_store`, `generator.*`), which must
stay framework-free.
"""
from pathlib import Path

from fastapi import HTTPException, Request
from jinja2 import Environment, FileSystemLoader

# This module lives in routers/wizard/, so go up THREE levels to the CK_server package
# root (wizard -> routers -> CK_server). The monolithic wizard.py used two levels.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Output templates for repeatable exports (traceability.md etc.)
OUTPUTS_DIR = BASE_DIR / "templates" / "outputs"
OUTPUTS_ENV = Environment(loader=FileSystemLoader(str(OUTPUTS_DIR)))


def get_data(request: Request):
    """The shared corpus references, built ONCE at startup (main.py startup_event).

    This used to be `return load_all_data()`, with the comment "Would be from
    app.state in a fuller implementation" — so every one of the 11 endpoints that
    depends on it rebuilt the whole reference set per request: re-reading
    zephyr_master, all candidates, decisions and two json_docs out of ck.db, plus a
    startup_check() that counts every corpus. Measured 47ms (70ms on py3.10) of
    redundant work per request, and because `get_data` is sync FastAPI ran it in a
    threadpool worker, so it burned one of those too.

    Two quieter costs beyond the latency: load_all_data() prints three lines to
    stdout on every call (data.py:57,88-93), which is where the "Loading lightweight
    references…" noise during ordinary use came from; and two dependencies resolved
    within one request could see two different snapshots of the corpus.

    main.py:132 already assigned this to app.state.app_data at startup and nothing
    read it — pytest_create has always done it correctly (see _data there, whose
    fail-loud 503 this mirrors). Deliberately NOT falling back to load_all_data():
    that would silently restore the per-request cost and mask a boot problem instead
    of reporting it. Safe because startup always runs in production, and the test
    suite drives the app through `with TestClient(...)` (tests/conftest.py:32), the
    context-manager form that fires startup/shutdown events.
    """
    data = getattr(request.app.state, "app_data", None)
    if not data:
        raise HTTPException(503, "Server data not loaded yet.")
    return data

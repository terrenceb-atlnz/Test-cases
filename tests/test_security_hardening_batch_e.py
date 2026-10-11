"""Regression tests for the two accepted-risk security items (2026-07-27g).

Both were documented accepted risks, actioned after the completion pass surfaced facts
the original acceptance did not cover:

  1. `0.0.0.0` bind + unauthenticated push_to_zephyr. Verified live: the server was
     reachable on the LAN IP and POST /api/wizard/push_to_zephyr/{key} answered 200 with
     no credential. `dry_run` is a plain query param defaulting True, so flipping it to
     false is one character; CORS does not apply to non-browser clients and the
     browser-side confirm() is not executed by curl. The NEW fact: `--force` was
     hardcoded, which disables upload_refined.py's own "already appears refined in
     Zephyr — SKIP" protection, so any push could overwrite an already-refined live case.
  2. SSH AutoAddPolicy with no known_hosts anywhere in the repo. The NEW fact: the
     "localhost/single-user" rationale does not apply — this connection is OUTBOUND to a
     lab testbox, so its exposure is independent of the web UI being single-user.
     (Its tests went with that SSH path, pt_exec's run engine, on 2026-10-12: Ask-CK no
     longer connects to a testbox.)

The fixes deliberately preserve existing capability as an explicit opt-in rather than
removing it, so no working setup breaks.

No network, no testbox, no Zephyr writes.
"""
import pathlib
import re

import pytest

from _wizard_src import wizard_router_paths

_REPO = pathlib.Path(__file__).resolve().parents[1]
_CK = _REPO / "ask-ck" / "CK-main"


# --- 1a. the bind default -------------------------------------------------------
def test_run_sh_defaults_to_loopback():
    """The documented model is localhost/single-user; the DEFAULT must match it."""
    src = (_CK / "run.sh").read_text(encoding="utf-8")
    m = re.search(r'^:\s*"\$\{HOST:=([^}]+)\}"', src, re.M)
    assert m, "HOST default not found in run.sh"
    assert m.group(1) == "127.0.0.1", f"run.sh still defaults to {m.group(1)}"


def test_run_sh_still_allows_explicit_lan_exposure():
    """Exposure stays supported — it just has to be deliberate."""
    src = (_CK / "run.sh").read_text(encoding="utf-8")
    assert "HOST=0.0.0.0" in src, "the opt-in path must remain documented"
    # And HOST must still be what actually reaches uvicorn.
    assert '--host "$HOST"' in src or '--host "${HOST}"' in src


def test_main_module_entrypoint_binds_loopback_and_uses_a_real_module_path():
    """The __main__ block hardcoded 0.0.0.0 — and a module path deleted in the 2026-07-13
    restructure, so it could only ever have raised on import."""
    src = (_CK / "CK_server" / "main.py").read_text(encoding="utf-8")
    block = src.split('if __name__ == "__main__":', 1)[1]
    # Strip comments — the fix's own comment names the stale path it replaced.
    code = re.sub(r"#.*$", "", block, flags=re.M)
    assert "drafting_tool" not in code, "stale pre-restructure module path is back"
    assert "CK_server.main:app" in code
    assert '"127.0.0.1"' in code, "entrypoint no longer defaults to loopback"


# --- 1b. the hardcoded --force --------------------------------------------------
def _push_handler_src():
    # push_to_zephyr moved into routers/wizard/export.py (commit 10). Find the package file
    # that defines it and slice out its body — it is the last route in that module.
    for p in wizard_router_paths():
        t = p.read_text(encoding="utf-8")
        if "async def push_to_zephyr(" in t:
            return t.split("async def push_to_zephyr(", 1)[1]
    raise AssertionError("push_to_zephyr handler not found in the wizard router")


def test_force_is_not_hardcoded():
    """--force disabled the CLI's own last safety net on EVERY push."""
    body = _push_handler_src()
    assert '"--force", "--verify"' not in body, "--force is still unconditional"
    assert '*(["--force"] if force else [])' in body, "no opt-in force path"


def test_force_defaults_to_off():
    body = _push_handler_src()
    assert re.search(r"force:\s*bool\s*=\s*False", body), "force must default to False"


def test_force_flag_is_reachable_but_opt_in():
    """The parameter exists (deliberate overwrite is still possible) but is not default."""
    from routers.wizard import push_to_zephyr
    import inspect
    sig = inspect.signature(push_to_zephyr)
    assert "force" in sig.parameters
    assert sig.parameters["force"].default is False
    assert sig.parameters["dry_run"].default is True, "dry_run must stay safe-by-default"


def test_ui_does_not_send_force():
    """The frontend must get the protected behaviour without opting in."""
    js = (_CK.parent / "frontend" / "ck-main" / "current" / "generator" / "generator.js").read_text(encoding="utf-8")
    push_call = js.split("push_to_zephyr", 1)[1][:300]
    assert "force" not in push_call, "the UI now forces pushes again"


def test_the_cli_protection_force_would_bypass_still_exists():
    """Pin the upstream guard this change restores — if the CLI drops it, the fix is moot."""
    cli = (_REPO / "ask-ck" / "frontend" / "ck-main" / "current" / "generator" / "upload_refined.py").read_text(encoding="utf-8")
    assert "not args.force" in cli
    assert "already appears refined" in cli

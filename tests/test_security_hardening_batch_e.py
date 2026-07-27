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

The fixes deliberately preserve existing capability as an explicit opt-in rather than
removing it, so no working setup breaks.

No network, no testbox, no Zephyr writes.
"""
import pathlib
import re

import pytest

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
    src = (_CK / "CK_server" / "routers" / "wizard.py").read_text(encoding="utf-8")
    return src.split("async def push_to_zephyr(", 1)[1].split("\n@router", 1)[0]


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
    js = (_CK / "CK_server" / "static" / "js" / "generator.js").read_text(encoding="utf-8")
    push_call = js.split("push_to_zephyr", 1)[1][:300]
    assert "force" not in push_call, "the UI now forces pushes again"


def test_the_cli_protection_force_would_bypass_still_exists():
    """Pin the upstream guard this change restores — if the CLI drops it, the fix is moot."""
    cli = (_REPO / "tool" / "upload_refined.py").read_text(encoding="utf-8")
    assert "not args.force" in cli
    assert "already appears refined" in cli


# --- 2. SSH host-key pinning ----------------------------------------------------
def _connect_src():
    src = (_CK / "CK_server" / "pt_exec.py").read_text(encoding="utf-8")
    return src.split("def _connect(", 1)[1].split("\ndef ", 1)[0]


def test_known_hosts_are_loaded_before_the_policy_is_set():
    """Order is the whole fix: loading first PINS a testbox we have seen before, so a
    changed key (what a MITM looks like) raises instead of being silently accepted."""
    body = _connect_src()
    assert "load_system_host_keys" in body, "host keys are never loaded"
    assert body.index("load_system_host_keys") < body.index("set_missing_host_key_policy"), \
        "known_hosts must load BEFORE the missing-key policy or nothing is pinned"


def test_autoadd_remains_so_new_hosts_still_work():
    """Trust-on-first-use, not trust-nothing — an unseen testbox must not need a prompt."""
    assert "AutoAddPolicy" in _connect_src()


def test_known_hosts_failure_is_not_fatal():
    """A malformed known_hosts must not block a testbox run."""
    body = _connect_src()
    assert "except Exception" in body
    assert "Warning" in body


def test_pinning_can_be_disabled_deliberately():
    """A legitimately reimaged testbox needs an escape hatch."""
    body = _connect_src()
    assert "CK_SSH_TRUST_ANY" in body


def test_pt_exec_imports_os():
    """`os.getenv` in _connect would NameError on every connect without this import —
    py_compile does not catch it, so pin it explicitly."""
    import pt_exec
    assert getattr(pt_exec, "os", None) is not None


def test_no_other_unpinned_ssh_client_appeared():
    """Any future SSHClient must go through _connect, or it bypasses the pinning."""
    src = (_CK / "CK_server" / "pt_exec.py").read_text(encoding="utf-8")
    assert src.count("paramiko.SSHClient()") == 1, (
        "a second SSHClient exists — route it through _connect so host keys stay pinned")

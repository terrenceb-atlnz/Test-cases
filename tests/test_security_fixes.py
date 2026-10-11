"""Regression tests for the adversarial-review top-cluster security/integrity fixes
(2026-07-27c). Each test pins a fix so it can't silently regress.

Run: PYTHONNOUSERSITE=1 .venv/bin/pytest -q tests/test_security_fixes.py
"""
from html_sanitize import sanitize_objective_html
from models import redact_llm_config, safe_session_dict

# (#2, the framework-guard hardening, went with the PyTest Creator's SSH run path on
# 2026-10-12 — Ask-CK no longer runs anything on a testbox.)


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

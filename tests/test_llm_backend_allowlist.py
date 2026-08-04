"""The LLM backend set is CLOSED — no caller-supplied key, no configurable endpoint.

WHY THIS IS PINNED (2026-08-04, AI governance review)
-----------------------------------------------------
The wiki page written for the governance meeting states that the tool talks only to an
approved set of model backends and that an operator cannot point it at an arbitrary
third-party provider. That sentence has to be TRUE IN CODE, not merely true of the UI.

Before this batch it was only true of the UI. Three separate paths went around it:

  1. `set_llm_config` accepted `auth_method: "api_key"` (and legacy `"account"`) with a
     caller-supplied `api_key` and a free-form `base_url`. Neither has a radio button, but
     both were one curl away.
  2. An UNRECOGNISED `auth_method` was silently rewritten to `"api_key"` rather than
     rejected, so a typo selected the generic-key backend instead of failing.
  3. `LLM_API_KEY` / `LLM_BASE_URL` environment variables were read as a credential and
     endpoint fallback at six call sites — an operator-invisible channel that `run.sh`
     actively advertised in its startup banner.

The tests below are the evidence for the wiki's claim. They are deliberately a mix of
behavioural (the endpoint refuses, the transport refuses) and STRUCTURAL (the env reads
are gone from the source): a behavioural test proves today's paths are shut, and the
structural one catches the re-introduction of the channel somewhere new, which is how
this kind of hole comes back.

See `models.SUPPORTED_AUTH_METHODS` for the approved set and why each entry is on it.
"""
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

import llm  # noqa: E402  (CK_server flat-module layout)
from llm_config import llm_is_active  # noqa: E402
from models import (  # noqa: E402
    RETIRED_AUTH_METHODS,
    SUPPORTED_AUTH_METHODS,
    LLMConfig,
)

_LLM_SRC = (_SERVER / "llm.py").read_text()
_CONFIG_SRC = (_SERVER / "routers" / "wizard" / "config.py").read_text()


# ---------------------------------------------------------------------------
# The set itself
# ---------------------------------------------------------------------------

def test_retired_methods_are_not_supported():
    """The two retired methods must not have crept back into the approved set."""
    assert set(RETIRED_AUTH_METHODS) == {"api_key", "account"}
    assert not set(SUPPORTED_AUTH_METHODS) & set(RETIRED_AUTH_METHODS)


def test_supported_set_is_the_approved_four():
    """A deliberate tripwire: widening the set is a governance decision, not a refactor.

    If you are adding a backend, that is fine — but update the wiki page and this list
    together, so the documented posture and the code cannot drift apart.
    """
    assert set(SUPPORTED_AUTH_METHODS) == {
        "local_llm", "claude_agent", "claude_code", "grok_cli",
    }


def test_default_auth_method_is_the_internal_backend():
    """An unspecified backend must fall to the INTERNAL one, never to a third party."""
    assert LLMConfig().auth_method == "local_llm"


# ---------------------------------------------------------------------------
# The endpoint refuses
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("retired", RETIRED_AUTH_METHODS)
def test_set_llm_config_refuses_retired_auth_method(client, retired):
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "openai", "auth_method": retired,
                          "api_key": "sk-should-never-be-accepted"})
    assert r.status_code == 400, f"{retired} was accepted: {r.text}"
    assert retired in r.json()["detail"]


def test_unknown_auth_method_is_rejected_not_downgraded(client):
    """The specific old bug: anything unrecognised became "api_key" silently."""
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "openai", "auth_method": "totally-made-up"})
    assert r.status_code == 400, "an unknown auth_method was accepted"
    body = r.json()["detail"]
    assert "totally-made-up" in body
    # It must not have quietly landed on the generic-key backend.
    assert "api_key" not in body.split("Supported:")[0]


def test_caller_supplied_key_and_endpoint_are_ignored(client):
    """Even on a SUPPORTED backend, a key/endpoint in the body must not be stored."""
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "grok", "auth_method": "grok_cli",
                          "api_key": "sk-leak", "token": "tok-leak",
                          "base_url": "https://attacker.example/v1"})
    assert r.status_code == 200, r.text
    cfg = r.json()["llm_config"]
    assert cfg.get("base_url") in (None, ""), f"a caller endpoint was stored: {cfg}"
    # The safe view never echoes secrets; assert the whole payload is clean.
    assert "sk-leak" not in r.text
    assert "tok-leak" not in r.text
    assert "attacker.example" not in r.text


def test_mock_provider_still_refused(client):
    """This 400 used to be unreachable — provider was coerced to "grok" before the check."""
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "mock", "auth_method": "local_llm"})
    assert r.status_code == 400
    assert "MOCK" in r.json()["detail"]


def test_supported_backend_still_works(client):
    """The allowlist must not have broken the backends we actually use."""
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "grok", "auth_method": "grok_cli"})
    assert r.status_code == 200, r.text
    assert r.json()["llm_config"]["auth_method"] == "grok_cli"


# ---------------------------------------------------------------------------
# The transport refuses (defence in depth: a session persisted before the change)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("retired", RETIRED_AUTH_METHODS)
def test_transport_refuses_retired_method_without_dispatching(retired, monkeypatch):
    """A stale session naming a retired backend must error, not resume calling out.

    The assertion that matters is `sent == []`: refusing AFTER the request has gone is
    not refusing.
    """
    sent = []
    monkeypatch.setattr(llm.requests, "post",
                        lambda *a, **k: sent.append(a) or pytest.fail("HTTP call made"))
    monkeypatch.setattr(llm.requests, "get",
                        lambda *a, **k: sent.append(a) or pytest.fail("HTTP call made"))

    meta = llm._call_llm_raw("hello", provider="openai", auth_method=retired,
                             api_key="sk-stale-but-present")
    assert meta.get("error") is True
    assert retired in meta["content"]
    assert sent == []


def test_transport_refuses_unknown_method(monkeypatch):
    """A CREDENTIAL IS SUPPLIED ON PURPOSE.

    Without one this passes even with the allowlist deleted, because the no-credential
    guard further down errors anyway and its message interpolates the auth_method — so
    the assertions hold for entirely the wrong reason. Handing it a usable key removes
    that alternative explanation: the only thing left that can refuse is the allowlist.
    (Caught by mutation testing this file, 2026-08-04.)
    """
    monkeypatch.setattr(llm.requests, "post",
                        lambda *a, **k: pytest.fail("HTTP call made"))
    meta = llm._call_llm_raw("hello", provider="openai", auth_method="nonsense",
                             api_key="sk-usable")
    assert meta.get("error") is True
    assert "nonsense" in meta["content"]
    assert "refused" in meta["content"].lower()


def test_env_key_does_not_revive_a_retired_backend(monkeypatch):
    """LLM_API_KEY in the environment must not make anything callable.

    Also passes a direct credential, for the reason given above.
    """
    monkeypatch.setenv("LLM_API_KEY", "sk-from-the-environment")
    monkeypatch.setenv("LLM_BASE_URL", "https://attacker.example/v1")
    monkeypatch.setattr(llm.requests, "post",
                        lambda *a, **k: pytest.fail("HTTP call made"))
    meta = llm._call_llm_raw("hello", provider="openai", auth_method="api_key",
                             api_key="sk-usable")
    assert meta.get("error") is True
    assert "refused" in meta["content"].lower()


# ---------------------------------------------------------------------------
# Structural — the env channel is gone from the source, not just unused today
# ---------------------------------------------------------------------------

def _code_lines(src: str):
    """Source lines with comments and docstring prose excluded.

    A grep for a forbidden pattern finds it in the comment forbidding it — this module's
    own header names both variables. Only executable references should fail the check.
    """
    out, in_doc, delim = [], False, None
    for line in src.splitlines():
        stripped = line.strip()
        if in_doc:
            if delim in stripped:
                in_doc = False
            continue
        if stripped.startswith(('"""', "'''")):
            delim = stripped[:3]
            # A one-line docstring opens and closes on the same line.
            if not (len(stripped) > 5 and stripped.endswith(delim)):
                in_doc = True
            continue
        code = line.split("#", 1)[0]
        if code.strip():
            out.append(code)
    return out


@pytest.mark.parametrize("var", ["LLM_API_KEY", "LLM_BASE_URL"])
def test_no_env_credential_fallback_in_llm_module(var):
    """These were read at six call sites. They must not come back anywhere."""
    hits = [ln for ln in _code_lines(_LLM_SRC) if var in ln]
    assert hits == [], f"{var} is read again in llm.py: {hits}"


@pytest.mark.parametrize("var", ["LLM_API_KEY", "LLM_BASE_URL"])
def test_no_env_credential_fallback_in_config_router(var):
    hits = [ln for ln in _code_lines(_CONFIG_SRC) if var in ln]
    assert hits == [], f"{var} is read again in config.py: {hits}"


def test_set_llm_config_does_not_read_a_caller_endpoint():
    """`base_url` must not be lifted off the request body again."""
    hits = [ln for ln in _code_lines(_CONFIG_SRC)
            if re.search(r'body\.get\(\s*["\'](base_url|api_key|token)["\']', ln)]
    assert hits == [], f"config.py reads a credential/endpoint from the body: {hits}"


# ---------------------------------------------------------------------------
# Readiness reporting agrees with the allowlist
# ---------------------------------------------------------------------------

def test_stale_config_with_a_key_is_not_reported_active():
    """Otherwise the Configure page shows "ready" for a backend the transport refuses."""
    stale = LLMConfig(provider="openai", auth_method="api_key", api_key="sk-old")
    assert llm_is_active(stale) is False


def test_cli_backends_still_report_active():
    for am, provider in (("grok_cli", "grok"), ("claude_agent", "claude"),
                         ("claude_code", "claude")):
        assert llm_is_active(LLMConfig(provider=provider, auth_method=am)) is True, am

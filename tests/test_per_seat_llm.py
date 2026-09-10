"""The LLM choice is PER SEAT: the X-CK-LLM header decides where a request goes.

WHY (2026-09-10, demo day; PLAN-seat-setup-and-per-seat-llm.md §5, decisions D1/D2).
Until this change the `_workspace_llm` row was authoritative for everyone: `set_llm_config`
wrote it on every Apply and `apply_workspace_llm` re-synced every case session to it at
dispatch. On a shared server with several seats that meant one seat picking "(this
server)" or vLLM flipped the transport for every other seat — `PLAN-llm-mode-selection.md`
§5 had named the unauthenticated global write as the hazard.

Now the browser stores its choice and sends it on every /api call as
    X-CK-LLM: <auth_method>;<model>;<unit_model>;<match_model>
`llm_config.effective_llm_config` resolves seat → site default → session copy, never writes
a session, and the governance allowlist is enforced on the header exactly as on the
endpoint (a bad value is a 400, never a silent fallback).
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path[:0] = [str(_REPO / "ask-ck" / "CK-main"), str(_SERVER)]

import llm_config  # noqa: E402
from llm_config import (  # noqa: E402
    SEAT_LLM_HEADER, cfg_for_task, current_seat_llm, effective_llm_config, parse_seat_llm,
)
from models import LLMConfig, PtSession, WizardSession  # noqa: E402


@pytest.fixture
def seat():
    """Bind an X-CK-LLM value for the test body, exactly as the middleware does."""
    tokens = []

    def _set(raw):
        tokens.append(current_seat_llm.set(raw))

    yield _set
    for t in reversed(tokens):
        current_seat_llm.reset(t)


# --- parsing the header ----------------------------------------------------------------

def test_parse_accepts_the_four_field_form_and_derives_the_provider():
    cfg = parse_seat_llm("claude_agent;opus;sonnet;haiku")
    assert (cfg.auth_method, cfg.provider, cfg.model) == ("claude_agent", "claude", "opus")
    assert (cfg.unit_model, cfg.match_model) == ("sonnet", "haiku")
    cfg = parse_seat_llm("local_llm;vllm-thinking")
    assert (cfg.auth_method, cfg.provider, cfg.model) == ("local_llm", "openai", "vllm-thinking")
    assert cfg.unit_model is None, "routing aliases are Claude-only"
    assert parse_seat_llm("local_llm").model == "vllm-fast", "blank model under local_llm = Fast"
    with pytest.raises(ValueError):
        parse_seat_llm("grok_cli")   # retired 2026-09-11: refused like any non-allowlisted value


def test_parse_of_an_empty_header_is_none_not_an_error():
    assert parse_seat_llm("") is None and parse_seat_llm("   ") is None and parse_seat_llm(None) is None


@pytest.mark.parametrize("raw,fragment", [
    ("api_key;x", "no longer supported"),          # retired: named as retired
    ("account", "no longer supported"),
    ("openrouter;gpt", "unknown auth_method"),     # outside the allowlist
    ("claude_agent;opus;gpt-4", "unknown Claude model alias"),   # routing is not free-form
])
def test_parse_refuses_anything_outside_the_governance_allowlist(raw, fragment):
    with pytest.raises(ValueError, match=fragment):
        parse_seat_llm(raw)


def test_blank_routing_means_same_as_model_not_a_fallback():
    cfg = parse_seat_llm("claude_agent;opus;;")
    assert cfg.model == "opus" and cfg.unit_model is None and cfg.match_model is None


# --- resolution precedence --------------------------------------------------------------

def test_the_seat_header_wins_over_the_site_default_and_the_session(seat, monkeypatch):
    monkeypatch.setattr(llm_config, "load_global_llm",
                        lambda: LLMConfig(provider="openai", auth_method="local_llm", model="vllm-fast"))
    sess = WizardSession(key="AWPTCM-T99991")
    sess.llm_config = LLMConfig(provider="claude", auth_method="claude_agent", model="haiku")
    seat("claude_agent;sonnet")
    got = effective_llm_config(sess)
    assert (got["auth_method"], got["model"]) == ("claude_agent", "sonnet")
    assert sess.llm_config.model == "haiku", "the session must never be rewritten"


def test_without_a_header_the_site_default_wins_over_a_stale_session_copy(monkeypatch):
    """The §7.3 bug of old, still covered: a stale headless copy on the case must not
    silently keep hitting its backend once the site default says otherwise."""
    monkeypatch.setattr(llm_config, "load_global_llm",
                        lambda: LLMConfig(provider="openai", auth_method="local_llm", model="vllm-fast"))
    sess = PtSession(key="AWPTCM-T99991")
    sess.llm_config = LLMConfig(provider="claude", auth_method="claude_agent", model="sonnet")
    assert effective_llm_config(sess)["auth_method"] == "local_llm"
    assert sess.llm_config.auth_method == "claude_agent", "resolved, not rewritten"


def test_without_header_or_default_the_sessions_own_active_config_is_used(monkeypatch):
    monkeypatch.setattr(llm_config, "load_global_llm", lambda: None)
    sess = WizardSession(key="AWPTCM-T99991")
    sess.llm_config = LLMConfig(provider="claude", auth_method="claude_agent", model="haiku")
    assert effective_llm_config(sess)["model"] == "haiku"
    bare = WizardSession(key="AWPTCM-T99992")
    bare.llm_config = None
    assert effective_llm_config(bare) == {}
    assert effective_llm_config(None) == {}


def test_two_seats_on_the_same_case_dispatch_to_different_backends(seat, monkeypatch):
    """THE DEMO-DAY HAZARD, closed: the same case, two requests, two backends."""
    monkeypatch.setattr(llm_config, "load_global_llm",
                        lambda: LLMConfig(provider="openai", auth_method="local_llm", model="vllm-fast"))
    sess = WizardSession(key="AWPTCM-T43852")
    seat("claude_agent;opus")
    a = effective_llm_config(sess)
    seat("local_llm;vllm-thinking")
    b = effective_llm_config(sess)
    assert a["auth_method"] == "claude_agent" and b["auth_method"] == "local_llm"
    assert b["model"] == "vllm-thinking"


# --- per-task routing follows the seat ---------------------------------------------------

def test_routing_comes_from_the_seat_when_present(seat, monkeypatch):
    monkeypatch.setattr(llm_config, "load_global_llm",
                        lambda: LLMConfig(provider="claude", auth_method="claude_agent",
                                          model="opus", match_model="haiku"))
    seat("claude_agent;opus;sonnet;")          # unit fills on Sonnet; matching "same"
    base = effective_llm_config()
    assert cfg_for_task(base, "unit_fill")["model"] == "sonnet"
    assert cfg_for_task(base, "step_match")["model"] == "opus", (
        "a seat that chose 'same' must get ITS model, not the site default's haiku routing")


# --- the wire: middleware + endpoints ----------------------------------------------------

def test_a_bad_header_is_a_400_on_any_api_call(client):
    r = client.get("/api/wizard/llm_config", headers={SEAT_LLM_HEADER: "api_key;sk-x"})
    assert r.status_code == 400 and "no longer supported" in r.json()["detail"]
    r = client.get("/api/wizard/llm_config", headers={SEAT_LLM_HEADER: "bogus"})
    assert r.status_code == 400 and "unknown auth_method" in r.json()["detail"]
    assert client.get("/api/wizard/llm_config", headers={SEAT_LLM_HEADER: "claude_agent;sonnet"}).status_code == 200
    assert client.get("/api/wizard/llm_config").status_code == 200


def test_the_header_is_bound_for_the_request_and_released_after(client):
    import routers.wizard.config as cfgmod
    seen = {}

    def spy():
        seen["seat"] = current_seat_llm.get("")
        return None

    original = cfgmod.load_global_llm
    cfgmod.load_global_llm = spy
    try:
        client.get("/api/wizard/llm_config", headers={SEAT_LLM_HEADER: "claude_agent;opus"})
    finally:
        cfgmod.load_global_llm = original
    assert seen["seat"] == "claude_agent;opus"
    assert current_seat_llm.get("") == "", "leaked past the request"


def test_apply_writes_the_site_default_but_never_the_case_session(client, monkeypatch):
    """Apply = this seat + the site default (D17, 2026-09-11; D2 had it seat-only for a day).
    The case session is still never written — a case is shared between seats."""
    import routers.wizard.config as cfgmod
    from session_store import sessions
    writes = []
    monkeypatch.setattr(cfgmod, "save_global_llm", lambda cfg: writes.append(cfg))
    sess = WizardSession(key="AWPTCM-T99993")
    sess.llm_config = LLMConfig(provider="openai", auth_method="local_llm")
    sessions["AWPTCM-T99993"] = sess
    try:
        r = client.post("/api/wizard/set_llm_config/AWPTCM-T99993",
                        json={"provider": "claude", "auth_method": "claude_agent", "model": "opus"})
        assert r.status_code == 200, r.text
        assert r.json()["scope"] == "seat" and r.json()["site_default_written"] is True
        assert r.json()["llm_config"]["auth_method"] == "claude_agent"
        assert [w.auth_method for w in writes] == ["claude_agent"], "Apply must write the site default (D17)"
        assert sess.llm_config.auth_method == "local_llm", "Apply wrote the case session"
    finally:
        sessions.pop("AWPTCM-T99993", None)


def test_set_site_default_alone_still_writes_the_row_for_headless_callers(client, monkeypatch):
    """No page control reaches this since D17, but curl/scripts moving the default without
    posing as a seat still need it (memory workspace-llm-default-gotcha)."""
    import routers.wizard.config as cfgmod
    writes = []
    monkeypatch.setattr(cfgmod, "save_global_llm", lambda cfg: writes.append(cfg))
    r = client.post("/api/wizard/set_site_default_llm",
                    json={"provider": "openai", "auth_method": "local_llm", "model": "vllm-thinking"})
    assert r.status_code == 200, r.text
    assert r.json()["scope"] == "site_default"
    assert [w.auth_method for w in writes] == ["local_llm"]
    # and it enforces the same allowlist
    assert client.post("/api/wizard/set_site_default_llm",
                       json={"provider": "openai", "auth_method": "api_key"}).status_code == 400


def test_the_site_default_endpoint_says_what_it_is(client):
    r = client.get("/api/wizard/llm_config")
    assert r.status_code == 200 and r.json()["scope"] == "site_default"


def test_apply_carries_the_seats_own_routing_forward_not_the_site_defaults(client, monkeypatch):
    """A toggle POST that omits unit_model/match_model must carry the SEAT's routing over,
    read from the header on that very request — not the site default's."""
    import routers.wizard.config as cfgmod
    monkeypatch.setattr(cfgmod, "load_global_llm",
                        lambda: LLMConfig(provider="claude", auth_method="claude_agent",
                                          model="opus", unit_model="haiku"))
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "claude", "auth_method": "claude_agent", "model": "sonnet"},
                    headers={SEAT_LLM_HEADER: "claude_agent;opus;sonnet;opus"})
    assert r.status_code == 200, r.text
    got = r.json()["llm_config"]
    assert (got["unit_model"], got["match_model"]) == ("sonnet", "opus")


def test_no_router_writes_a_session_llm_config_any_more():
    """Structural: the leak path was `sess.llm_config = …` at dispatch. None may remain."""
    import re
    offenders = []
    for path in list((_SERVER / "routers").rglob("*.py")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.llm_config\s*=\s*", line) and not line.lstrip().startswith("#"):
                offenders.append(f"{path.relative_to(_SERVER)}:{i}: {line.strip()}")
    assert offenders == [], offenders
    assert not hasattr(llm_config, "apply_workspace_llm"), "the re-sync is back"

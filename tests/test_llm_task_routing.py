"""Per-task model routing (token-efficiency decision 6, 2026-09-07).

The two fan-out call classes — per-unit generation and per-step script matching — may run
on a cheaper Claude alias than the workspace toggle, while Review and Fix stay on the
toggle model. TOKEN-EFFICIENCY-REPORT-2026-09-04.md §5 is the evidence (Sonnet 5: 4 of 5
sampled units at ~59% of Opus cost; identical step-match shortlist at under half).

What is pinned: the routing lives on the WORKSPACE config and is applied at dispatch from
it (never from a per-case copy); a toggle POST that omits the fields preserves them; the
fields are Claude aliases only and inert under every other backend; and exactly the two
routed call classes read it. Not pinned: the UI markup.
"""
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

import llm_config  # noqa: E402
from llm_config import cfg_for_task, normalize_task_model  # noqa: E402
from models import LLMConfig  # noqa: E402
from routers import pytest_create as pc  # noqa: E402

_PC_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_PC_CODE = re.sub(r'#[^\n]*', '', re.sub(r'"""[\s\S]*?"""', '', _PC_SRC))


def _region(start: str, end: str) -> str:
    return _PC_CODE[_PC_CODE.index(start):_PC_CODE.index(end)]


# --- the config shape ---------------------------------------------------------------

def test_old_persisted_configs_still_deserialize():
    cfg = LLMConfig(**{"provider": "claude", "auth_method": "claude_code", "model": "opus"})
    assert cfg.unit_model is None and cfg.match_model is None


@pytest.mark.parametrize("raw,want", [("", None), (None, None), ("same", None),
                                      ("Sonnet", "sonnet"), ("haiku", "haiku")])
def test_normalize_accepts_blank_and_the_three_aliases(raw, want):
    assert normalize_task_model(raw) == want


def test_normalize_refuses_a_free_form_model_name():
    # A routing field is NOT a second free-form model input — the allowlist stays closed.
    with pytest.raises(ValueError):
        normalize_task_model("claude-3-5-sonnet-20241022")


# --- dispatch ----------------------------------------------------------------------

def test_the_routed_alias_replaces_model_for_its_task_only():
    ws = LLMConfig(provider="claude", auth_method="claude_code", model="opus",
                   unit_model="sonnet")
    base = {"provider": "claude", "auth_method": "claude_code", "model": "opus"}
    assert cfg_for_task(base, "unit_fill", workspace=ws)["model"] == "sonnet"
    assert cfg_for_task(base, "step_match", workspace=ws)["model"] == "opus"
    assert base["model"] == "opus", "the caller's dict must not be mutated"


def test_routing_is_read_from_the_workspace_not_the_session_copy(monkeypatch):
    """apply_workspace_llm documents a per-case config as never a legitimate override, so a
    stale per-case copy carrying its own routing must not win over the workspace row."""
    monkeypatch.setattr(llm_config, "load_global_llm",
                        lambda: LLMConfig(provider="claude", auth_method="claude_agent",
                                          model="opus", match_model="haiku"))
    stale = {"provider": "claude", "auth_method": "claude_agent", "model": "opus",
             "match_model": "sonnet"}
    assert cfg_for_task(stale, "step_match")["model"] == "haiku"


def test_routing_is_inert_under_non_claude_backends():
    ws = LLMConfig(provider="openai", auth_method="local_llm", model="vllm-fast",
                   unit_model="sonnet")
    base = {"provider": "openai", "auth_method": "local_llm", "model": "vllm-fast"}
    assert cfg_for_task(base, "unit_fill", workspace=ws)["model"] == "vllm-fast"


def test_an_unknown_task_is_a_programming_error_not_a_silent_passthrough():
    with pytest.raises(KeyError):
        cfg_for_task({"auth_method": "claude_code"}, "review")


# --- the endpoint --------------------------------------------------------------------

def test_set_llm_config_stores_returns_and_preserves_the_routing(client):
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "claude", "auth_method": "claude_code",
                          "model": "opus", "unit_model": "sonnet", "match_model": ""})
    assert r.status_code == 200, r.text
    cfg = r.json()["llm_config"]
    assert cfg["unit_model"] == "sonnet" and cfg["match_model"] is None
    # The toggle posts only `model`: the routing must survive that.
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "claude", "auth_method": "claude_code", "model": "haiku"})
    assert r.json()["llm_config"]["unit_model"] == "sonnet"
    # And the cold-load endpoint hands it back.
    got = client.get("/api/wizard/llm_config").json()["llm_config"]
    assert got["unit_model"] == "sonnet" and got["model"] == "haiku"
    # An explicit blank clears it.
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "claude", "auth_method": "claude_code",
                          "model": "haiku", "unit_model": ""})
    assert r.json()["llm_config"]["unit_model"] is None


def test_set_llm_config_refuses_a_free_form_routing_model(client):
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "claude", "auth_method": "claude_code",
                          "model": "opus", "unit_model": "gpt-4o"})
    assert r.status_code == 400
    assert "unit_model" in r.json()["detail"]


def test_routing_is_dropped_when_the_backend_is_not_claude(client):
    r = client.post("/api/wizard/set_llm_config",
                    json={"provider": "openai", "auth_method": "local_llm",
                          "unit_model": "sonnet"})
    assert r.status_code == 200, r.text
    assert r.json()["llm_config"]["unit_model"] is None


# --- exactly the two routed call classes read it -----------------------------------

def test_unit_fills_and_step_matching_are_routed_and_nothing_else_is():
    unit_paths = [_region('@router.post("/generate_units/', '@router.get("/units_status/'),
                  _region('@router.post("/generate_step/', "def _review_lint_findings"),
                  _region("def _render_unit_prompt", "@router.get(\"/step_prompts/")]
    for body in unit_paths:
        assert '_llm_cfg_for(sess, "unit_fill")' in body
        assert "_llm_cfg(sess)" not in body
    match_paths = [_region('@router.post("/suggest_scripts/', '@router.post("/suggest_scripts_step/'),
                   _region('@router.post("/suggest_scripts_step/', '@router.post("/save_matches/')]
    for body in match_paths:
        assert '_llm_cfg_for(sess, "step_match")' in body
        assert "_llm_cfg(sess)" not in body
    # Review and the whole-script Fix keep the toggle model.
    for start, end in (('@router.post("/review_script/', '@router.post("/fix_script/'),
                       ('@router.post("/fix_script/', "@router.post(\"/validate/")):
        body = _region(start, end)
        assert "_llm_cfg(sess)" in body and "_llm_cfg_for" not in body


def test_the_dispatch_helper_delegates_to_the_shared_implementation():
    body = _region("def _llm_cfg_for", "async def _dry_run")
    assert "cfg_for_task(_llm_cfg(sess), task)" in body
    assert pc._llm_cfg_for.__doc__ and "workspace" in pc._llm_cfg_for.__doc__.lower()

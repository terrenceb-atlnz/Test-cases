"""The coupling fix: `routers/pytest_create.py` no longer reaches into `routers/wizard.py`.

PLAN-backend-module-split.md commit 8. Before it, pytest_create.py opened with

    from routers.wizard import (
        _load_global_llm, _llm_is_active, _same_backend,
        _refined_complete_keys, _build_case_groups, _is_hidden_case,
    )

— six UNDERSCORE-PRIVATE names imported out of a sibling router, so renaming any one of
them silently broke a different feature, and there was no signal anywhere that the
Generator's internals were load-bearing for the PyTest Creator. On top of that,
`pytest_create._apply_workspace_llm` was a hand-maintained copy of
`wizard._apply_workspace_llm_if_needed` whose docstring said "Mirrors wizard…" — a
drift risk by construction, and the two tools disagreeing about which LLM to talk to is
not hypothetical (it shipped once, fixed 2026-07-20).

Both now import from leaf modules: `CK_server/llm_config.py` and
`CK_server/case_registry.py`.

These are structural tests over the AST, so they keep holding as Part B continues to move
code — a green functional suite cannot see a coupling regression.
"""
import ast
import pathlib

import pytest

from _wizard_src import wizard_router_paths

_SERVER = pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"
_ROUTERS = _SERVER / "routers"
_LEAVES = ("llm_config.py", "case_registry.py", "session_store.py",
           "generator/descriptions.py", "generator/gates.py", "generator/backfill.py")


def _imports(path):
    """(module, imported_name) for every import in a file; module '' for plain imports."""
    out = []
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.ImportFrom):
            out += [(n.module or "", a.name) for a in n.names]
        elif isinstance(n, ast.Import):
            out += [("", a.name) for a in n.names]
    return out


# --- the coupling itself -----------------------------------------------------

def test_pytest_create_imports_nothing_from_the_wizard_router():
    """The headline assertion of commit 8, and the plan's own acceptance check."""
    offenders = [name for mod, name in _imports(_ROUTERS / "pytest_create.py")
                 if mod.startswith("routers.wizard") or mod == "routers"
                 or name.startswith("routers.wizard")]
    assert not offenders, (
        "pytest_create.py imports from the wizard router again: "
        f"{offenders}. Shared code belongs in a leaf module (llm_config, case_registry), "
        "not in a sibling router.")


@pytest.mark.parametrize("path", [_ROUTERS / "pytest_create.py", *wizard_router_paths()],
                         ids=lambda p: p.name)
def test_routers_do_not_import_private_names_from_each_other(path):
    """A leading underscore across a module boundary is the smell, not just the file it
    came from. Catches `from routers.foo import _bar` for any foo.

    Intra-package wiring is fine and expected: the wizard router's own modules import each
    other's helpers via RELATIVE imports (`from .reviews import _session_llm_cfg`), whose
    module name is not `routers.*`, so they are correctly not flagged here — that is one
    router's internals, not a reach across the router boundary."""
    offenders = [f"{mod}.{name}" for mod, name in _imports(path)
                 if mod.startswith("routers") and name.startswith("_")]
    assert not offenders, f"{path.name} imports private names across routers: {offenders}"


@pytest.mark.parametrize("rel", _LEAVES)
def test_the_shared_leaves_never_import_a_router(rel):
    """One-way dependency. A leaf importing routers.* both defeats the split and puts an
    import cycle one edit away (llm_config <- session_store is the documented near-miss).
    """
    offenders = [f"{mod or name}" for mod, name in _imports(_SERVER / rel)
                 if (mod or name).startswith("routers")]
    assert not offenders, f"{rel} imports the router layer: {offenders}"


@pytest.mark.parametrize("rel", _LEAVES)
def test_the_shared_leaves_are_importable_without_fastapi_routing(rel):
    """They must be usable by tool/ scripts and tests with no app in play — which is the
    property that makes them unit-testable at all. `db.py` already documents this rule
    for itself ("No FastAPI imports — tool/ scripts import this module directly")."""
    offenders = [f"{mod or name}" for mod, name in _imports(_SERVER / rel)
                 if (mod or name).split(".")[0] in ("fastapi", "starlette")]
    assert not offenders, f"{rel} pulls in the web framework: {offenders}"


# --- the duplicate that was collapsed ----------------------------------------

def test_the_workspace_llm_sync_exists_exactly_once():
    """Two byte-identical copies differing only in a type annotation, one per router.

    Proven identical before collapsing them (same AST once docstrings are stripped;
    `WizardSession` vs `PtSession` was the whole difference), and the body touches nothing
    but `sess.llm_config`, so one duck-typed function serves both.
    """
    defined = []
    targets = [(str(p.relative_to(_SERVER)), p) for p in wizard_router_paths()]
    targets += [("routers/pytest_create.py", _SERVER / "routers" / "pytest_create.py"),
                ("llm_config.py", _SERVER / "llm_config.py")]
    for rel, path in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and "workspace_llm" in n.name:
                defined.append(f"{rel}:{n.name}")
    assert defined == ["llm_config.py:apply_workspace_llm"], (
        f"workspace-LLM sync is defined in {defined} — it must exist only in llm_config.py")


def test_both_routers_reach_the_same_workspace_llm_function():
    """Not just "no copy" — they must actually be wired to the shared one."""
    wiz_got = set()
    for path in wizard_router_paths():
        wiz_got |= {name for mod, name in _imports(path) if mod == "llm_config"}
    assert "apply_workspace_llm" in wiz_got, (
        f"the wizard router does not import llm_config.apply_workspace_llm (imports: {sorted(wiz_got)})")
    pc_got = [name for mod, name in _imports(_SERVER / "routers" / "pytest_create.py")
              if mod == "llm_config"]
    assert "apply_workspace_llm" in pc_got, (
        f"routers/pytest_create.py does not import llm_config.apply_workspace_llm (imports: {pc_got})")


# --- behaviour of the shared modules -----------------------------------------

def test_apply_workspace_llm_is_duck_typed_over_both_session_kinds(monkeypatch):
    """The one real risk in collapsing them: it must work for a PtSession too."""
    import llm_config
    from models import LLMConfig, PtSession, WizardSession

    workspace = LLMConfig(auth_method="local_llm", provider="vllm", model="fast")
    monkeypatch.setattr(llm_config, "load_global_llm", lambda: workspace)

    for sess in (WizardSession(key="AWPTCM-T99991"), PtSession(key="AWPTCM-T99991")):
        assert llm_config.apply_workspace_llm(sess) is True, type(sess).__name__
        assert sess.llm_config.model == "fast"
        assert sess.llm_config is not workspace, "sessions must not share the config object"
        # Idempotent: already on the workspace backend, so no further write.
        assert llm_config.apply_workspace_llm(sess) is False, type(sess).__name__


def test_apply_workspace_llm_leaves_a_session_alone_when_there_is_no_default(monkeypatch):
    """"The workspace login persists across cases" — with no default, do not clobber."""
    import llm_config
    from models import LLMConfig, WizardSession

    monkeypatch.setattr(llm_config, "load_global_llm", lambda: None)
    sess = WizardSession(key="AWPTCM-T99991")
    sess.llm_config = LLMConfig(auth_method="grok_cli")
    assert llm_config.apply_workspace_llm(sess) is False
    assert sess.llm_config.auth_method == "grok_cli"


def test_a_stale_headless_config_still_resyncs(monkeypatch):
    """The §7.3 bug this function was rewritten for.

    llm_is_active reports a headless CLI mode active unconditionally (there is no
    server-side key to check), so an "is it active?" test alone can never re-sync a stale
    claude_agent config — it kept silently hitting the wrong backend. The backend
    comparison is what fixes it.
    """
    import llm_config
    from models import LLMConfig, WizardSession

    workspace = LLMConfig(auth_method="local_llm", provider="vllm", model="fast")
    monkeypatch.setattr(llm_config, "load_global_llm", lambda: workspace)
    sess = WizardSession(key="AWPTCM-T99991")
    sess.llm_config = LLMConfig(auth_method="claude_agent", model="sonnet")
    assert llm_config.llm_is_active(sess.llm_config), "precondition: headless reads active"
    assert llm_config.apply_workspace_llm(sess) is True
    assert sess.llm_config.auth_method == "local_llm"


@pytest.mark.parametrize("cfg,expected", [
    (None, False),
    ({"auth_method": "claude_agent"}, True),
    ({"auth_method": "grok_cli"}, True),
    ({"auth_method": "claude_code"}, True),
    # CHANGED 2026-08-04 (was True). A stored credential no longer makes a config active
    # on its own — the backend has to be on `SUPPORTED_AUTH_METHODS`. Note the case that
    # used to pass here names "openai" as the AUTH METHOD, which was never a valid one;
    # it reported ready purely because a key was present. That "has a key => usable"
    # fallback is the generic-API-key path retired in the governance batch, so this row
    # now pins the opposite. See tests/test_llm_backend_allowlist.py.
    ({"auth_method": "openai", "api_key": "sk-x"}, False),
    ({"auth_method": "openai"}, False),
    ({"auth_method": "api_key", "api_key": "sk-x"}, False),
    ({"auth_method": "account", "token": "tok-x"}, False),
])
def test_llm_is_active(cfg, expected):
    import llm_config
    from models import LLMConfig
    assert llm_config.llm_is_active(LLMConfig(**cfg) if cfg else None) is expected


def test_same_backend_ignores_credentials_but_not_dispatch_fields():
    """It answers "would these hit the SAME backend", so the key must not matter."""
    import llm_config
    from models import LLMConfig
    a = LLMConfig(auth_method="local_llm", provider="vllm", model="fast", api_key="k1")
    b = LLMConfig(auth_method="local_llm", provider="VLLM", model="Fast", api_key="k2")
    assert llm_config.same_backend(a, b), "case + credentials must not affect the verdict"
    assert not llm_config.same_backend(a, LLMConfig(
        auth_method="local_llm", provider="vllm", model="thinking"))
    assert not llm_config.same_backend(a, None) and not llm_config.same_backend(None, None)


# --- case_registry -----------------------------------------------------------

def test_hidden_cases_are_hidden_by_key_or_by_folder():
    import case_registry as cr
    assert cr.is_hidden_case("AWPTCM-T44453")
    assert cr.is_hidden_case("AWPTCM-T99999", "/New Platform Test (MASTER)/Bootloader/")
    assert not cr.is_hidden_case("AWPTCM-T33233", "/New Platform Test (MASTER)/Port")
    assert not cr.is_hidden_case("AWPTCM-T33233")


def test_hiding_is_display_only():
    """A hiding rule must never be implemented by touching ck.db, the permanent source of
    truth. Pinned structurally because the tempting "fix" is a DELETE."""
    src = (_SERVER / "case_registry.py").read_text(encoding="utf-8")
    for verb in ("DELETE", "UPDATE", "INSERT", "save_session", "delete_session"):
        assert verb not in src, f"case_registry.py writes to the DB ({verb})"


def test_case_key_regex_accepts_real_keys_and_rejects_traversal():
    """It guards filesystem paths and subprocess arguments, so it is a security boundary."""
    import case_registry as cr
    assert cr.CASE_KEY_RE.match("AWPTCM-T33233")
    for bad in ("../../etc/passwd", "AWPTCM-T33233/../x", "pt-AWPTCM-T33233",
                "AWPTCM-TABC", "AWPTCM-T33233 ", ""):
        assert not cr.CASE_KEY_RE.match(bad), bad


def test_build_case_groups_labels_counts_and_sorts_numerically():
    import case_registry as cr
    zephyr = {
        "AWPTCM-T9":   {"folder": "/Root/Port", "title": "nine"},
        "AWPTCM-T100": {"folder": "/Root/Port", "title": "hundred"},
        "AWPTCM-T5":   {"folder": "/Root/IPv4/", "title": "five"},
        "AWPTCM-T7":   {},
    }
    groups = cr.build_case_groups(list(zephyr), zephyr)
    assert [g["label"] for g in groups] == ["IPv4 (1)", "Other (1)", "Port (2)"]
    port = next(g for g in groups if g["label"].startswith("Port"))
    assert [c["key"] for c in port["cases"]] == ["AWPTCM-T9", "AWPTCM-T100"], (
        "case ids must sort NUMERICALLY. The sort key was k.split('-T')[-1], a string, so "
        "T100 came before T9 — invisible while every real key is AWPTCM-T + 5 digits, and "
        "wrong the moment a four- or six-digit id appears (2026-07-28)")
    assert next(g for g in groups if g["label"] == "Other (1)")["cases"][0]["title"] == "AWPTCM-T7"


def test_case_ids_that_are_not_numeric_still_sort_without_raising():
    """int() vs str() in one sort key is a TypeError, so the classes must be separated.

    Reachable: pt session keys are `pt-AWPTCM-Txxxx`, and a malformed row in ck.db is not
    validated on the way to this function.
    """
    import case_registry as cr
    zephyr = {k: {"folder": "/Root/Port"} for k in
              ("AWPTCM-T9", "AWPTCM-T100", "AWPTCM-TABC", "not-a-key", "pt-AWPTCM-T5")}
    cases = cr.build_case_groups(list(zephyr), zephyr)[0]["cases"]
    keys = [c["key"] for c in cases]
    assert keys[:3] == ["pt-AWPTCM-T5", "AWPTCM-T9", "AWPTCM-T100"], (
        f"numeric ids must sort numerically and come first; got {keys}")
    assert set(keys[3:]) == {"AWPTCM-TABC", "not-a-key"}


def test_complete_is_defined_by_the_payload_file(tmp_path, monkeypatch):
    """"Complete" is a filesystem fact: refined-cases/<Group>/<KEY>/zephyr_payload.json."""
    import case_registry as cr
    monkeypatch.setattr(cr, "REFINED_DIR", tmp_path)
    assert cr.refined_complete_keys() == set()
    assert cr.refined_payload_path("AWPTCM-T1") is None

    (tmp_path / "Port (1)" / "AWPTCM-T1").mkdir(parents=True)
    (tmp_path / "Port (1)" / "AWPTCM-T1" / "zephyr_payload.json").write_text("{}")
    # A traceability.md alone is NOT the marker.
    (tmp_path / "Port (1)" / "AWPTCM-T2").mkdir(parents=True)
    (tmp_path / "Port (1)" / "AWPTCM-T2" / "traceability.md").write_text("x")
    # Non-AWPTCM directories are ignored entirely.
    (tmp_path / "Port (1)" / "scratch").mkdir(parents=True)
    (tmp_path / "Port (1)" / "scratch" / "zephyr_payload.json").write_text("{}")

    assert cr.refined_complete_keys() == {"AWPTCM-T1"}
    assert cr.refined_payload_path("AWPTCM-T1").name == "zephyr_payload.json"
    assert cr.refined_payload_path("AWPTCM-T2") is None


def test_refined_group_reuses_an_existing_counted_directory(tmp_path, monkeypatch):
    """Export must land in "Port (7)", not create a bare "Port" beside it."""
    import case_registry as cr
    monkeypatch.setattr(cr, "REFINED_DIR", tmp_path)
    (tmp_path / "Port (7)").mkdir()
    data = {"zephyr_master": {
        "AWPTCM-T1": {"folder": "/New Platform Test (MASTER)/Port"},
        "AWPTCM-T2": {"folder": "/New Platform Test (MASTER)/QoS"},
        "AWPTCM-T3": {},
    }}
    assert cr.get_refined_group("AWPTCM-T1", data) == "Port (7)"
    assert cr.get_refined_group("AWPTCM-T2", data) == "QoS"
    assert cr.get_refined_group("AWPTCM-T3", data) == "Other"

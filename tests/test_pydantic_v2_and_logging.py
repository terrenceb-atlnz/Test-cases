"""Pydantic-v2 serialization, the shared `model_to_dict`, and router logging hygiene.

THE PYDANTIC BUG THIS PINS
--------------------------
19 call sites across three files carried this "portability" hedge:

    obj.dict() if hasattr(obj, "dict") else obj.model_dump()

It reads as "use v1's .dict() if available, else v2's model_dump()". On pydantic v2 it is
INVERTED: `BaseModel.dict()` still exists as a deprecated alias for `model_dump`, so
`hasattr(obj, "dict")` is always True and every site took the v1 path — emitting a
DeprecationWarning and depending on an alias pydantic removes in v3. The `else` branches
were unreachable. The hedge did the exact opposite of its stated purpose.

`models.model_to_dict` replaces all 19. It tries `model_dump` FIRST and never consults
`.dict()` at all.

WHY THE ABSENCE CHECKS ARE AST-BASED
------------------------------------
`model_to_dict`'s own docstring necessarily contains the antipattern it replaced, so a
grep for `.dict()` finds the text forbidding it (see tests/_prose.py — this class of
self-match happened four times in one session). Parsing to AST looks only at real calls,
which is what tests/_prose.py recommends when the target is Python.
"""
import ast
import logging
import pathlib
import warnings

import pytest
from pydantic import BaseModel

from _wizard_src import wizard_router_paths
from models import LLMConfig, WizardSession, model_to_dict, safe_session_dict

_SERVER = pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"
# commit 10: the wizard router is a routers/wizard/ PACKAGE, not one file.
_WIZARD_FILES = wizard_router_paths()
_PYTEST_CREATE = _SERVER / "routers" / "pytest_create.py"
_MODELS = _SERVER / "models.py"
_MAIN = _SERVER / "main.py"

# Every file that carried the hedge. Any `x.dict()` call in these is a regression.
# session_store.py is included because commit 9 moved model_to_dict call sites there out
# of wizard.py — without it, the hedge could grow back in the new home unnoticed.
_SESSION_STORE = _SERVER / "session_store.py"
_HEDGE_FILES = [*_WIZARD_FILES, _PYTEST_CREATE, _MODELS, _SESSION_STORE]

# The extracted leaves that also carry logging discipline (persist-failure ERROR etc.).
_LEAF_LOG_FILES = [_SESSION_STORE, _SERVER / "llm_config.py",
                   _SERVER / "case_registry.py", _SERVER / "generator" / "backfill.py"]

# No file in the router package (or the extracted leaves) may print(). Part B keeps moving
# code out of wizard.py, and the discipline travels with it.
_NO_PRINT_FILES = [*_WIZARD_FILES, *_LEAF_LOG_FILES]

# Files that actually EMIT logs must do so through a named module logger. Among the router
# package that is export.py; the review/config/synthesis modules do no logging (still
# covered for print() above). The persist-failure ERROR this suite pins moved to
# session_store.py in commit 9, so grepping only the router would silently stop covering
# the very site the test was written for — the leaves stay in this set.
_LOGGING_FILES = [p for p in _WIZARD_FILES if p.name == "export.py"] + _LEAF_LOG_FILES


def _model_to_dict_lines() -> set:
    """Line numbers spanned by models.model_to_dict — the one sanctioned `.dict()` user."""
    tree = ast.parse(_MODELS.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "model_to_dict")
    return set(range(fn.lineno, (fn.end_lineno or fn.lineno) + 1))


def _dict_method_calls(path: pathlib.Path):
    """Lines with an attribute call `<something>.dict()`.

    Matches the METHOD only — a bare `dict()` builtin call is an ast.Name, not an
    ast.Attribute, so it is correctly ignored.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "dict"]


# --- model_to_dict behaviour --------------------------------------------------

class _Toy(BaseModel):
    a: int = 1
    b: str = "x"


def test_dumps_a_model_to_a_plain_dict():
    assert model_to_dict(_Toy()) == {"a": 1, "b": "x"}


def test_emits_no_deprecation_warning():
    """The whole point. Under -W error this is what the old hedge failed."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert model_to_dict(_Toy()) == {"a": 1, "b": "x"}


def test_the_old_hedge_would_have_warned():
    """Proves the test above is not vacuous — the pattern really is deprecated here.

    If a future pydantic removes `.dict()`, this raises AttributeError instead and the
    test still fails loudly, which is the correct signal.
    """
    m = _Toy()
    assert hasattr(m, "dict"), "hasattr(obj,'dict') must be True — that IS the bug"
    with pytest.raises(DeprecationWarning):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            m.dict()


def test_a_dict_passes_through_as_a_copy():
    """Not the same object: several call sites mutate the result (export() writes
    llm_config and gaps into it), and aliasing would write back into the live session."""
    src = {"key": "AWPTCM-T1", "nested": {"keep": 1}}
    out = model_to_dict(src)
    assert out == src
    assert out is not src
    out["key"] = "mutated"
    assert src["key"] == "AWPTCM-T1"


@pytest.mark.parametrize("value", [None, 42, "str", object()],
                         ids=["none", "int", "str", "object"])
def test_non_models_become_empty_dict(value):
    """Matches the previous fallback, so callers that did `.get(...)` still work."""
    assert model_to_dict(value) == {}


def test_a_real_wizard_session_round_trips():
    sess = WizardSession(key="AWPTCM-T33233")
    d = model_to_dict(sess)
    assert d["key"] == "AWPTCM-T33233"
    assert isinstance(d["step1"], dict), "nested models must dump too, not stay models"
    assert "llm_config" in d


def test_llm_config_dumps_without_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert isinstance(model_to_dict(LLMConfig()), dict)


# --- safe_session_dict still redacts (guards the rewrite) --------------------

def test_safe_session_dict_still_masks_secrets():
    """safe_session_dict was rewritten on top of model_to_dict. Its ONE security job —
    never serializing api_key/token to the browser or to disk — must be intact."""
    sess = WizardSession(key="AWPTCM-T33233")
    sess.llm_config = LLMConfig(api_key="sk-SECRET-DO-NOT-LEAK", token="tok-SECRET")
    d = safe_session_dict(sess)
    assert d["llm_config"]["api_key"] is None
    assert d["llm_config"]["token"] is None
    assert d["llm_config"]["api_key_set"] is True
    assert "sk-SECRET-DO-NOT-LEAK" not in repr(d)
    assert "tok-SECRET" not in repr(d)


def test_safe_session_dict_accepts_a_plain_dict():
    d = safe_session_dict({"key": "AWPTCM-T1", "llm_config": {"api_key": "sk-x"}})
    assert d["llm_config"]["api_key"] is None


def test_safe_session_dict_returns_empty_for_junk():
    assert safe_session_dict(None) == {}
    assert safe_session_dict(7) == {}


# --- source-level regression guards ------------------------------------------

@pytest.mark.parametrize("path", _HEDGE_FILES, ids=lambda p: p.name)
def test_no_deprecated_dict_method_calls(path):
    """No `x.dict()` at any CALL SITE in the three files that carried the hedge.

    `model_to_dict` itself is exempt: it keeps `.dict()` as a documented last-resort
    fallback for real pydantic v1 models (and `.dict()`-shaped objects), reached only
    when `model_dump` is absent. That single guarded use is the point of the helper.
    """
    hits = [ln for ln in _dict_method_calls(path)
            if not (path == _MODELS and ln in _model_to_dict_lines())]
    assert hits == [], (
        f"{path.name} calls the deprecated pydantic .dict() at line(s) {hits}. "
        f"Use models.model_to_dict(obj) instead — see its docstring for why the "
        f"hasattr(obj, 'dict') hedge is inverted on pydantic v2.")


def test_the_ast_guard_actually_detects_the_pattern():
    """Mutation check: the guard above must not be vacuously green."""
    tree = ast.parse("x = sess.dict()\ny = dict()\nz = model_to_dict(sess)\n")
    hits = [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "dict"]
    assert hits == [1], "must catch sess.dict() but not the dict() builtin"


def test_model_dump_is_preferred_over_dict():
    """The actual invariant: when an object offers BOTH, model_dump wins.

    This is the inversion that made every old call site take the deprecated path. A spy
    proves the branch order at runtime rather than trusting the source reading.
    """
    calls = []

    class _Both:
        def model_dump(self):
            calls.append("model_dump")
            return {"via": "model_dump"}

        def dict(self):
            calls.append("dict")
            return {"via": "dict"}

    assert model_to_dict(_Both()) == {"via": "model_dump"}
    assert calls == ["model_dump"], f"expected model_dump only, got {calls}"


def test_dict_only_objects_are_still_supported():
    """The v1 fallback. Deleting this branch silently broke llm_config redaction for
    `.dict()`-shaped objects — test_security_fixes caught it, and it stays covered here.
    """
    class _V1Style:
        def dict(self):
            return {"key": "AWPTCM-T1", "llm_config": {"api_key": "sk-x"}}

    assert model_to_dict(_V1Style())["key"] == "AWPTCM-T1"
    assert safe_session_dict(_V1Style())["llm_config"]["api_key"] is None


# --- logging hygiene ---------------------------------------------------------

@pytest.mark.parametrize("path", _NO_PRINT_FILES, ids=lambda p: p.name)
def test_no_print_calls(path):
    """wizard.py had 14 print() calls: no levels, no timestamps, no way to quiet them —
    a failed-persistence warning was indistinguishable from boot noise. The modules Part B
    extracted from it inherit the rule."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prints = [n.lineno for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "print"]
    assert prints == [], f"{path.name} uses print() at line(s) {prints}; use `log.<level>()`"


@pytest.mark.parametrize("path", _LOGGING_FILES, ids=lambda p: p.name)
def test_defines_a_module_logger(path):
    """`logging.getLogger(__name__)`, so the record carries the module that emitted it.

    This is not cosmetic: caplog and any log filter select by logger NAME, so a module
    that logs through the root logger (or borrows another module's) cannot be asserted on
    or quieted independently — which is exactly how commit 9 broke two of this file's own
    tests when the persist code moved and kept logging under "routers.wizard".
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "getLogger"]
    assert calls, f"{path.name} must define log = logging.getLogger(__name__)"


def test_losing_a_session_write_is_logged_at_error(caplog, monkeypatch):
    """A failed persist loses the user's confirmed selections while the handler still
    returns 200 (the stale-connection bug). It must not be a mere warning.

    Lives in session_store since commit 9, so the logger to watch is "session_store" —
    caplog.at_level on the wrong logger name captures nothing and the test would fail
    with "logged nothing at all" rather than telling you the module moved.
    """
    import session_store

    def _boom(*a, **k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(session_store.db, "save_session", _boom)
    sess = WizardSession(key="AWPTCM-T99991")
    with caplog.at_level(logging.DEBUG, logger="session_store"):
        # Raises since 2026-07-28 (a lost write must not return 200); the logging
        # contract this test exists for is unchanged.
        with pytest.raises(session_store.SessionWriteError):
            session_store.persist_session(sess)

    records = [r for r in caplog.records if "AWPTCM-T99991" in r.getMessage()]
    assert records, "a failed persist logged nothing at all"
    assert records[0].levelno == logging.ERROR
    assert records[0].exc_info is not None, "keep the traceback — the message alone " \
                                            "does not say which caller lost data"


def test_clearing_a_session_logs_at_info_not_error(caplog, monkeypatch):
    """Level discipline: routine bookkeeping must not read as a fault."""
    import session_store

    monkeypatch.setattr(session_store.db, "delete_session", lambda *a, **k: None)
    with caplog.at_level(logging.DEBUG, logger="session_store"):
        session_store.clear_persisted("AWPTCM-T99992")

    records = [r for r in caplog.records if "AWPTCM-T99992" in r.getMessage()]
    assert records and records[0].levelno == logging.INFO


def test_main_configures_logging_so_info_is_not_dropped():
    """Without basicConfig the root logger sits at WARNING and every log.info() is
    silently discarded — including "[export] Saved drop-in bundle to …", which reached
    stdout as a print() before. force=True because uvicorn also installs root handlers;
    without it the format depends on which ran first.
    """
    tree = ast.parse(_MAIN.read_text(encoding="utf-8"))
    call = next((n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "basicConfig"), None)
    assert call is not None, "main.py must call logging.basicConfig(...)"
    kwargs = {k.arg for k in call.keywords}
    assert {"level", "format", "force"} <= kwargs, f"basicConfig missing {kwargs}"


# --- dead code stays dead ----------------------------------------------------

_DELETED = {
    "wizard router": (_WIZARD_FILES, [
        # thin single-key wrapper; its own docstring said prefer the batch form
        "_get_full_zephyr_case",
        # born unused in 05b194a; _can_synthesize_steps documents why the strict
        # "objectives confirmed" gate is deliberately NOT applied (it would break re-runs)
        "_session_objectives_confirmed",
        # born unused in 05b194a; export() implements the step5→step4 fallback inline
        "_session_test_script",
        # orphaned by 4578030 (A1). _build_atp_query filters generics inline and needs an
        # ORDER-PRESERVING list for its [:24] slice, which this set-returning helper
        # could not provide anyway
        "_specific_tokens",
    ]),
    "routers/pytest_create.py": ([_PYTEST_CREATE], [
        # a full copy of db._score_script_candidate that referenced _PT_GENERIC_TOKENS /
        # _PT_AREA_SUPPORT — names that only ever existed in db.py. It raised NameError on
        # any call and nothing reached it. The comment above it already claimed the
        # scorer lived in db with "no private copy here".
        "_score_script_candidate",
    ]),
}


@pytest.mark.parametrize("label", list(_DELETED))
def test_deleted_helpers_are_not_reintroduced(label):
    paths, names = _DELETED[label]
    defined = set()
    for p in paths:
        defined |= {n.name for n in ast.parse(p.read_text(encoding="utf-8")).body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    back = sorted(set(names) & defined)
    assert not back, f"{label} reintroduced dead helper(s): {back}"


@pytest.mark.parametrize("path", [*_WIZARD_FILES, _PYTEST_CREATE], ids=lambda p: p.name)
def test_no_unreferenced_private_module_functions(path):
    """Generalizes the four deletions above into an invariant.

    A module-level `_helper` that nothing in the file names is either dead or a symptom
    of a gate that was meant to be wired up and never was. Route handlers are exempt by
    construction: they are decorated and do not start with an underscore.

    Applied PER FILE, so a helper shared between the router package's own modules (e.g.
    `_session_llm_cfg`, used by reviews and synthesis) must also be USED in the module
    that defines it — which it is; the sibling reaches it by a relative import.
    """
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    defined = {n.name: n.lineno for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name.startswith("_")}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    # A helper may exist only for the test suite to import; require an explicit opt-out.
    exported = {n for n in defined if f"# keep: " in src.split("\n")[defined[n] - 2]}
    orphans = {n: ln for n, ln in defined.items() if n not in used and n not in exported}
    assert not orphans, (
        f"{path.name} has unreferenced private helper(s) {orphans}. Delete them, wire them "
        f"up, or mark the line above with `# keep: <reason>` if a test imports it.")

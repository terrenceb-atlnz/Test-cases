"""Every lint error must be deliberately classified as blocking or policy.

PHASE 7.8. The split exists because the two kinds have different authorities:

  * blocking — the artefact provably cannot work (will not compile, dies with AttributeError
    on the testbox, or covers fewer steps than the approved sequence). No override; regenerate.
  * policy — the script runs but breaks a house rule. The reviewer is the right authority, so
    it is overridable with a reason that is recorded on the session.

The risk this file addresses is drift. `_split_lint_errors` matches message text, so an error
whose wording changes could silently move class — and an error added later could land in
whichever class the default happens to be. Defaulting to *blocking* makes that fail safe, but
"safe" is not the same as "intended", so every error raised by `_lint_generated` is enumerated
here and asserted against its expected class. Adding an error without listing it fails.
"""
import ast
import pathlib
import re
import sys

import pytest

SERVER = (pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server")
ROUTER = SERVER / "routers" / "pytest_create.py"
SOURCE = ROUTER.read_text(encoding="utf-8")

sys.path.insert(0, str(SERVER / "routers"))


def _split():
    """Import just the classifier, without dragging in the FastAPI app."""
    import importlib.util
    tree = ast.parse(SOURCE)
    wanted = {"_split_lint_errors", "_POLICY_LINT_MARKERS"}
    picked = [n for n in tree.body
              if (isinstance(n, ast.FunctionDef) and n.name in wanted)
              or (isinstance(n, ast.Assign)
                  and any(getattr(t, "id", None) in wanted for t in n.targets))]
    module = ast.Module(body=picked, type_ignores=[])
    ns = {"List": list, "Tuple": tuple}
    exec(compile(module, "<classifier>", "exec"), ns)
    return ns["_split_lint_errors"]


split = _split()


# Every error message `_lint_generated` can raise, with the class it MUST fall in.
# Wording is the literal prefix of each `errors.append(...)` in the router.
BLOCKING = [
    "syntax: invalid syntax",
    "structure: no TestSet(ATTestSet.TestSet) class",
    "structure: no TestCase classes",
    "structure: TestCase_1 missing testCaseDesc",
    "structure: missing ts.run(sys.argv) __main__ entry",
    "contract: unfilled template placeholder on line 42 — every `>>>` marker is an instruction",
    "init(): uses `self.` before the self.<dev> assignment block (line 3 of init) — AttributeError",
    "line 12: reads `portA` but the script never calls `self._ck_bind_link(...)`, so no port link",
    "line 88: uses device `swi_c` but init() never binds `self.swi_c` — this compiles and then dies",
    "init(): `portA` is bound by init_portlink() on lines 10, 14 — the later call DISCARDS",
    "imports: framework module 'ATFoo' not found in framework_surface",
    "imports: framework.ATBar not found in framework_surface",
    "incomplete: 6 TestCase classes for 14 non-setup sequence steps",
    "coverage/completeness check could not run (ValueError: boom)",
]

POLICY = [
    "contract: TestCase_1.main() has no self.log() (needs step-start + observed)",
    "contract: TestCase_1.main() has no non-empty self.passed()/self.failed() determination",
    "contract: TestCase_1.main() has 2 empty self.passed()/self.failed() (empty reason emits no log marker)",
    "contract: TestCase_1.main() missing a leading # ART/SVT/legacy/AI provenance tag (PLAN §1.5)",
    "line 273: calls setup.init_portlink() directly, which skips the run-time MEDIA assertion",
]


@pytest.mark.parametrize("msg", BLOCKING)
def test_blocking_errors_classify_as_blocking(msg):
    blocking, policy = split([msg])
    assert blocking == [msg] and policy == [], \
        f"this error must NOT be overridable: {msg[:70]}"


@pytest.mark.parametrize("msg", POLICY)
def test_policy_errors_classify_as_policy(msg):
    blocking, policy = split([msg])
    assert policy == [msg] and blocking == [], \
        f"this error should be the reviewer's call: {msg[:70]}"


def test_an_unknown_error_is_blocking():
    """Strict by default. A new check is not silently overridable."""
    blocking, policy = split(["something nobody has classified yet"])
    assert blocking and not policy


def test_the_real_error_that_fired_on_t44297_is_overridable():
    """The concrete case that motivated the split.

    The only lint error ever recorded on a real generation, on the best script we have —
    and the model was following the generate prompt when it earned it.
    """
    real = ("line 273: calls setup.init_portlink() directly, which skips the run-time MEDIA "
            "assertion. Bind through `self._ck_bind_link(setup, <dut>, misc, '<role>')` "
            "instead — a port bound without that check can be the wrong media")
    blocking, policy = split([real])
    assert policy == [real] and not blocking


def test_the_truncation_detector_is_never_overridable():
    """The whole point of Phase 7.7 — a short script must not be signable."""
    blocking, policy = split(["incomplete: 6 TestCase classes for 14 non-setup sequence steps"])
    assert blocking and not policy


def test_every_router_error_site_is_covered_by_this_file():
    """A new `errors.append` must be classified here, or this fails.

    Counts the raise sites in `_lint_generated` and compares against the enumeration above.
    A mismatch means an error was added or removed without deciding its authority.
    """
    tree = ast.parse(SOURCE)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_lint_generated")
    seg = ast.get_source_segment(SOURCE, fn) or ""
    sites = len(re.findall(r"errors\.append\(", seg))
    assert sites == len(BLOCKING) + len(POLICY), (
        f"_lint_generated raises {sites} errors but this file classifies "
        f"{len(BLOCKING) + len(POLICY)}. Add the new one to BLOCKING or POLICY and, if it is "
        f"a house rule rather than a broken artefact, to _POLICY_LINT_MARKERS.")

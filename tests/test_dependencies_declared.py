"""Every third-party module the server imports must be declared as a dependency.

THE DEFECT THIS PINS (found 2026-07-30, autopilot batch)
--------------------------------------------------------
`pt_exec.py` has imported `paramiko` since the testbox-execution feature landed, and
`paramiko` appeared in NO requirements file. `PLAN-pytest-creator.md` recorded "paramiko
2.9.3 is installed", which was a fact about one machine, not a declaration.

Why it survived so long: the failure is polite and lands far from the cause. `import
paramiko` sits inside `pt_exec._connect()`, so the server boots fine, every other tool
works, the profile page renders — and the testbox probe simply answers

    {"ok": false, "detail": "SSH connection failed: No module named 'paramiko'"}

which reads as a testbox or lab-network problem. On a fresh venv the entire "6. Run" step
is dead and the message points away from the reason. A missing runtime dependency is
exactly the class of bug a structural test catches for free and a functional test never
does, because the functional path needs hardware.

WHAT THIS ALSO CATCHES
----------------------
`lib2to3`, which `pytest_create._translate_py2` uses for the D3 py2-to-py3 fragment
translation, was REMOVED from the standard library in Python 3.13 — the very version
`requirements.txt` tells you to prefer ("PREFER PYTHON 3.13 — match the testbox"). So on a
correctly-built venv the import fails, `_translate_py2` returns status "unavailable", and
legacy fragments ship untranslated. It degrades by design and never crashes, so nothing
tells you the feature is off. Its docstring even calls this a "very old/stripped runtime",
when the truth is the opposite: a NEW runtime.

`lib2to3` is listed in EXPECTED_UNDECLARED with that explanation rather than being
silently filtered, so the gap is recorded where someone will read it, and closing it (the
maintained fork `fissix` is the drop-in) means deleting a line here.
"""
import ast
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
_REQS = _REPO / "ask-ck" / "CK-main" / "requirements.txt"
_REQS_DEV = _REPO / "ask-ck" / "CK-main" / "requirements-dev.txt"

# import name -> distribution name, where they differ.
_DIST_ALIASES = {
    "sqlite_vec": "sqlite-vec",
    "sentence_transformers": "sentence-transformers",
    "pysqlite3": "pysqlite3-binary",
}

# Guaranteed transitively, and pinning them here would just duplicate fastapi's own
# dependency graph.
_TRANSITIVE_OF_DECLARED = {"starlette"}

# Modules that live in this repo but outside CK_server (tool/ is on the path at runtime).
_REPO_LOCAL = {"cli_lookup"}

# Imports that are deliberately undeclared because a DECLARED package covers the same job.
# Distinct from EXPECTED_UNDECLARED: nothing is broken here, so these must never be
# "fixed" by adding a requirements line.
_OPTIONAL_WITH_DECLARED_FALLBACK = {
    # `lib2to3` was removed from the stdlib in Python 3.13 — the version requirements.txt
    # asks you to prefer, so the recommended environment was the broken one. It is now the
    # stdlib-FIRST preference in pytest_create._py2_refactor_backend, with the declared
    # `fissix` (maintained fork, same refactor API) as the fallback. Declaring lib2to3
    # would be wrong: it is not installable from PyPI for 3.13.
    "lib2to3": "fissix",
}

# Known-undeclared with no cover, and the reason. An entry here is a RECORDED gap, not an
# excuse: the test still fails if a NEW undeclared import appears.
EXPECTED_UNDECLARED: dict = {}


def _local_module_names() -> set:
    """Names importable as siblings because CK_server is on sys.path flat."""
    names = {"CK_server"}
    for p in _SERVER.rglob("*"):
        if "__pycache__" in str(p):
            continue
        if p.suffix == ".py":
            names.add(p.stem)
        elif p.is_dir():
            names.add(p.name)
    return names


def _third_party_imports() -> dict:
    """{top_level_module: {files that import it}} for non-stdlib, non-local imports."""
    local = _local_module_names() | _REPO_LOCAL
    std = set(sys.stdlib_module_names)
    found: dict = {}
    for path in sorted(_SERVER.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:          # relative import — always local
                    continue
                mods = [node.module.split(".")[0]] if node.module else []
            else:
                continue
            for m in mods:
                if m in std or m in local:
                    continue
                found.setdefault(m, set()).add(path.name)
    return found


def _declared() -> set:
    """Distribution names declared in either requirements file (comments stripped)."""
    out = set()
    for f in (_REQS, _REQS_DEV):
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line or line.startswith("-r"):
                continue
            name = re.split(r"[<>=!;\[ ]", line, maxsplit=1)[0].strip()
            if name:
                out.add(name.lower().replace("_", "-"))
    return out


def test_the_scan_finds_the_real_imports():
    """Guard the guard: a scan that matches nothing would pass forever while covering
    nothing. Anchor on imports that are certain to exist."""
    found = _third_party_imports()
    for anchor in ("fastapi", "pydantic", "requests", "paramiko"):
        assert anchor in found, (
            f"{anchor} not detected as a third-party import — the scan is broken, "
            f"not the dependency list. Found: {sorted(found)}")


@pytest.mark.parametrize("module", sorted(_third_party_imports()))
def test_third_party_import_is_declared(module):
    if module in _TRANSITIVE_OF_DECLARED:
        pytest.skip(f"{module} is a transitive dependency of a declared package")
    if module in _OPTIONAL_WITH_DECLARED_FALLBACK:
        fallback = _OPTIONAL_WITH_DECLARED_FALLBACK[module]
        assert fallback.lower() in _declared(), (
            f"'{module}' is undeclared on purpose because '{fallback}' covers it — but "
            f"'{fallback}' is not declared either, so BOTH backends can be absent and the "
            f"feature degrades silently. Declare '{fallback}'.")
        return
    if module in EXPECTED_UNDECLARED:
        pytest.xfail(f"known gap — {EXPECTED_UNDECLARED[module]}")
    dist = _DIST_ALIASES.get(module, module).lower().replace("_", "-")
    importers = ", ".join(sorted(_third_party_imports()[module]))
    assert dist in _declared(), (
        f"CK_server imports '{module}' (in {importers}) but '{dist}' is declared in "
        f"neither requirements.txt nor requirements-dev.txt. On a fresh venv that feature "
        f"is dead. If the import is deliberately optional, it still needs a line — with a "
        f"comment saying what degrades without it, like sqlite-vec has.")


def test_every_recorded_gap_is_still_real():
    """Stops EXPECTED_UNDECLARED from rotting into a list of lies. If a gap has been
    closed — the module is now declared, or no longer imported — this fails and the entry
    must go, so the file cannot accumulate stale excuses."""
    found = _third_party_imports()
    declared = _declared()
    for module, reason in EXPECTED_UNDECLARED.items():
        assert module in found, (
            f"'{module}' is in EXPECTED_UNDECLARED but nothing imports it any more — "
            f"delete the entry. Recorded reason was: {reason}")
        dist = _DIST_ALIASES.get(module, module).lower().replace("_", "-")
        assert dist not in declared, (
            f"'{dist}' IS declared now, so it is no longer a gap — delete its "
            f"EXPECTED_UNDECLARED entry so the next real gap cannot hide behind it.")


def test_a_py2_refactor_backend_is_actually_available():
    """The point of the fallback is that SOME backend resolves on this interpreter.

    Asserting the requirements line is not enough: `_py2_refactor_backend` returning None
    is the failure mode that never raises — `_translate_py2` answers "unavailable", the
    caller soft-warns, and legacy fragments ship untranslated looking merely unlucky. So
    check the resolved backend, not the declaration.
    """
    sys.path[:0] = [str(_REPO / "ask-ck" / "CK-main"), str(_SERVER)]
    from CK_server.routers.pytest_create import _py2_refactor_backend

    mod, fixers_pkg = _py2_refactor_backend()
    assert mod is not None, (
        "neither lib2to3 nor fissix is importable, so D3 py2->py3 fragment translation is "
        "silently off: every legacy fragment ships untranslated behind a soft-warn. "
        "Install the declared fallback (pip install -r ask-ck/CK-main/requirements.txt).")
    assert fixers_pkg.endswith(".fixes"), f"unexpected fixers package {fixers_pkg!r}"
    assert fixers_pkg.split(".")[0] == mod.__name__.split(".")[0], (
        f"backend {mod.__name__} paired with fixers package {fixers_pkg} — mixing one "
        f"library's RefactoringTool with another's fixers is how this silently half-works")


def test_the_translation_really_modernizes_and_yields_valid_py3():
    """End-to-end on the idioms the legacy corpus actually contains.

    A backend that imports but mistranslates is worse than one that is absent, because
    "translated" is a GUARANTEE the rest of the pipeline relies on — the fragment goes
    straight into a generated script with no further Py3 check.
    """
    sys.path[:0] = [str(_REPO / "ask-ck" / "CK-main"), str(_SERVER)]
    from CK_server.routers.pytest_create import _translate_py2

    py2 = ('print "hi"\n'
           'for k, v in d.iteritems():\n'
           '    if d.has_key(k): print k\n'
           'try:\n'
           '    x()\n'
           'except ValueError, e:\n'
           '    print e\n')
    out, status = _translate_py2(py2, "corpus-fragment")
    assert status == "translated", f"expected a translation, got {status!r}"
    ast.parse(out)                                  # the guarantee "translated" makes
    assert 'print("hi")' in out and ".iteritems()" not in out and "except ValueError as e" in out


def test_mixed_tabs_and_spaces_survive_translation():
    """Py2 tolerated mixed indentation and Py3's tokenizer does not; the refactorer fixes
    syntax but preserves indentation, so normalization is a separate step. It was found by
    an adversarial pass (9/85 translations were invalid Py3 for exactly this) — pinned here
    because the fallback swap is a natural place to lose it."""
    sys.path[:0] = [str(_REPO / "ask-ck" / "CK-main"), str(_SERVER)]
    from CK_server.routers.pytest_create import _translate_py2

    out, status = _translate_py2('def f():\n\tif x:\n\t        print "deep"\n', "tabs")
    assert status == "translated", status
    ast.parse(out)
    assert "\t" not in out, "tabs survived; the translated fragment can still fail on 3.x"

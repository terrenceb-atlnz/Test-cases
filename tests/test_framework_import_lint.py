"""The generated-script framework-import lint must follow the surface index, not a list.

Why this exists (2026-07-28): T33235's lint sat red on what was recorded as "a
hallucinated `framework.ATLibrary` import". It was not hallucinated — `ATLibrary` is a
real framework package. The surface index in `ck.db` is keyed by MODULE path only
(`ATLibrary.ATTools`, `ATLibrary.__init__`); a package never appears as a bare key. So a
plain membership test rejected every package import, and `from framework.ATDrivers import
ATSwitch` — an extremely common real import — was an error too. `ATDrivers` passed only
because it had been hardcoded into an allowlist, despite being structurally IDENTICAL to
`ATLibrary` in the data.

The lesson the tests encode: the check must resolve packages FROM the index. An allowlist
is what hid the bug for seven names, so these tests assert no name needs one — the six
formerly-exempt names must pass on their own merits, and a package must pass because the
index implies it.

In-process and offline (no network, no testbox); reads the committed `ck.db`.
"""
import ast
import sys
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
_CK_MAIN = _REPO / "ask-ck" / "CK-main"
for _p in (str(_CK_MAIN), str(_CK_MAIN / "CK_server")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SOURCE = _CK_MAIN / "CK_server" / "routers" / "pytest_create.py"

# The names that used to be exempted by hand. Each is a real key in the surface, so each
# must now pass without an exemption.
FORMERLY_ALLOWLISTED = ["ATTestSet", "ATTestCase", "ATPackets", "Setup",
                        "ATTestTag", "ATTagFilter"]


@pytest.fixture(scope="module")
def surface():
    import db
    s = db.get_json_doc("framework_surface") or {}
    if not s:
        pytest.skip("framework_surface not present in ck.db")
    return s


@pytest.fixture(scope="module")
def resolver(surface):
    """The lint's package-aware membership test, lifted from the live source.

    Kept in lockstep with pytest_create.py by `test_resolver_matches_live_source`
    below, so this helper cannot silently drift from what the server runs.
    """
    packages = {k.rsplit(".", 1)[0] for k in surface if "." in k}

    def known(name: str) -> bool:
        return (name in surface
                or name.replace(".", "/") in surface
                or name in packages
                or f"{name}.__init__" in surface)

    return known


# --- the data-shape fact that caused the bug ------------------------------------------

def test_packages_are_not_bare_keys_in_the_surface(surface):
    """The premise of the bug: a package has no bare key, only `<pkg>.__init__`.

    If this ever stops being true the resolver is harmless, but the reason for its
    existence should be re-read rather than assumed.
    """
    assert "ATLibrary" not in surface
    assert "ATDrivers" not in surface
    assert "ATLibrary.__init__" in surface
    assert "ATDrivers.__init__" in surface


def test_atlibrary_and_atdrivers_are_structurally_identical(surface):
    """The two were treated differently by the allowlist while being the same shape."""
    def shape(pkg):
        return (pkg in surface, f"{pkg}.__init__" in surface,
                any(k.startswith(f"{pkg}.") for k in surface))

    assert shape("ATLibrary") == shape("ATDrivers")


# --- what must now be accepted --------------------------------------------------------

@pytest.mark.parametrize("name", ["ATLibrary", "ATDrivers"])
def test_package_import_is_accepted(resolver, name):
    """`from framework import ATLibrary` — the import that held T33235 red."""
    assert resolver(name)


@pytest.mark.parametrize("name", ["ATLibrary.ATTools", "ATDrivers.ATSwitch"])
def test_submodule_import_is_accepted(resolver, name):
    """`from framework.ATDrivers import ATSwitch` was ALSO rejected before the fix."""
    assert resolver(name)


def test_nested_package_is_accepted(resolver, surface):
    """`ATLibrary.testbox` is a package two levels down — implied by its children only."""
    assert "ATLibrary.testbox" not in surface
    assert resolver("ATLibrary.testbox")
    assert resolver("ATLibrary.testbox.ATTbPortLib")


@pytest.mark.parametrize("name", FORMERLY_ALLOWLISTED)
def test_formerly_allowlisted_names_pass_on_the_data(resolver, surface, name):
    """No name should need a hardcoded exemption — the allowlist hid the real bug."""
    assert name in surface, f"{name} is not in the surface; it would need an exemption"
    assert resolver(name)


# --- what must still be rejected ------------------------------------------------------

@pytest.mark.parametrize("name", ["ATNonExistent", "ATLibrary.ATNope",
                                  "ATDrivers.ATFake", "Bogus.Deep.Path"])
def test_invented_modules_are_still_rejected(resolver, name):
    """The check must still catch a genuinely hallucinated import.

    `ATLibrary.ATNope` is the sharp one: a real package plus a fake submodule must NOT be
    waved through by the new package resolution.
    """
    assert not resolver(name)


# --- structural guards against the fix regressing -------------------------------------

def test_no_hardcoded_import_allowlist_returns():
    """A literal tuple of framework module names next to the import check is the smell.

    Asserting on source because the defect was an allowlist that looked authoritative;
    re-introducing one would restore exactly the blind spot ATLibrary fell into.
    """
    src = SOURCE.read_text()
    marker = "3. Framework imports must exist in the surface index"
    assert marker in src, "import-check comment moved; re-point this guard"
    block = src[src.index(marker):src.index(marker) + 2600]
    # ATDrivers was the name whose exemption masked ATLibrary's rejection.
    assert '"ATDrivers"' not in block and "'ATDrivers'" not in block, (
        "the framework-import check appears to hardcode module names again; "
        "resolve packages from framework_surface instead"
    )


def test_resolver_matches_live_source(surface):
    """The lint's real code must accept the same imports this file's resolver does.

    Guards the fixture above from drifting away from the shipped check: it AST-extracts
    the live `_known` helper and runs it, rather than trusting a copy.
    """
    src = SOURCE.read_text()
    tree = ast.parse(src)
    found = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "_known"]
    assert found, "_known helper not found in pytest_create.py"

    ns = {"surface": surface,
          "packages": {k.rsplit(".", 1)[0] for k in surface if "." in k}}
    exec(compile(ast.Module(body=found, type_ignores=[]), "<lint>", "exec"), ns)
    live = ns["_known"]

    for name in ["ATLibrary", "ATDrivers", "ATLibrary.ATTools",
                 "ATDrivers.ATSwitch", *FORMERLY_ALLOWLISTED]:
        assert live(name), f"live lint rejects real module {name}"
    for name in ["ATNonExistent", "ATLibrary.ATNope"]:
        assert not live(name), f"live lint accepts invented module {name}"

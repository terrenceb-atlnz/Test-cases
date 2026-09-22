"""PRUNE — the deferred half of R1(b) (PLAN-art-family-numbering-and-prune.md §4).

This is the ONLY operation in R1(a)/R1(b) that can delete a reviewer's working code, so the
tests are written around what it must REFUSE to touch, not around what it removes:

* only `# AI: dependency …` members — the ones R1(a)'s closure auto-added — are ever candidates;
* a reviewer-selected `# ART` / `# SVT` / `# legacy` member survives however dead it looks;
* untagged preamble (an LLM-authored library is ALL preamble) is never touched;
* an unparseable script BLOCKS the prune rather than counting as "references nothing", which is
  how a prune deletes the very members that script uses;
* and a no-op prune returns the file it was given, byte for byte.

The libraries under test are built by `_build_library` itself wherever the tag shape matters, so
the tags being matched are the tags the generator actually emits — not a fixture's idea of them.
"""
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"))
from routers import pytest_create as pc          # noqa: E402


ART_TAG = "# ART art/1332_lldp_med/library_1332.py lines 18-41"
AI_TAG = "# AI: dependency `_fmt_port` of " + ART_TAG
AI_TAG_2 = "# AI: dependency `_only_used_by_fmt` of " + ART_TAG

LIB = f'''"""library_9001 — helpers shared by the Port group (ART family 9001)."""
import re


{ART_TAG}
def check_lldp_lag(testCase, eth, tb):
    return True


{AI_TAG}
def _fmt_port(port):
    return _only_used_by_fmt(port.name)


{AI_TAG_2}
def _only_used_by_fmt(name):
    return name.upper()
'''


@pytest.fixture
def group(tmp_path, monkeypatch):
    """An isolated generated/ tree holding one group, 9001_Port, with the library above."""
    gen = tmp_path / "generated"
    (gen / "9001_Port").mkdir(parents=True)
    monkeypatch.setattr(pc, "PT_GENERATED_DIR", gen)
    monkeypatch.setattr(pc, "META_ROOT", gen / ".meta")
    monkeypatch.setattr(pc, "FAMILY_REGISTRY", gen / ".families.json")
    pc._write_family_registry({"Port": 9001})
    (gen / "9001_Port" / "library_9001.py").write_text(LIB, encoding="utf-8")
    return gen / "9001_Port"


def script(folder, name, body):
    (folder / name).write_text(body, encoding="utf-8")


# --- what it removes -------------------------------------------------------------------------

def test_an_auto_added_member_no_script_references_is_removed(group):
    script(group, "test-9001.33234.py", "from library_9001 import *\ncheck_lldp_lag(1, 2, 3)\n")
    plan = pc._prune_library_plan("Port")
    assert not plan["blocked"]
    assert [r["tag"] for r in plan["removed"]] == [AI_TAG, AI_TAG_2]
    assert "def _fmt_port" not in plan["code"]


def test_the_fixed_point_drops_a_member_only_a_DEAD_member_called(group):
    """`_only_used_by_fmt` is referenced — but only by `_fmt_port`, which is itself going. One
    pass would keep it; the walk has to repeat until nothing more is revived."""
    script(group, "test-9001.33234.py", "from library_9001 import *\ncheck_lldp_lag(1, 2, 3)\n")
    plan = pc._prune_library_plan("Port")
    assert {r["names"][0] for r in plan["removed"]} == {"_fmt_port", "_only_used_by_fmt"}


def test_the_pruned_file_is_still_importable_python(group):
    script(group, "test-9001.33234.py", "from library_9001 import *\ncheck_lldp_lag(1, 2, 3)\n")
    compile(pc._prune_library_plan("Port")["code"], "pruned", "exec")


# --- what it must NOT remove -----------------------------------------------------------------

def test_an_auto_added_member_a_script_references_is_kept(group):
    script(group, "test-9001.33234.py", "from library_9001 import *\n_fmt_port(p)\n")
    plan = pc._prune_library_plan("Port")
    assert plan["removed"] == []
    assert "def _fmt_port" in plan["code"] and "def _only_used_by_fmt" in plan["code"]


def test_a_reference_from_a_SECOND_script_in_the_group_counts(group):
    """The whole point of one library per group: a member dead in this script may be the one
    the sibling script imports. Pruning per-script would delete it out from under it."""
    script(group, "test-9001.33234.py", "from library_9001 import *\ncheck_lldp_lag(1, 2, 3)\n")
    script(group, "test-9001.33233.py", "from library_9001 import *\n_fmt_port(p)\n")
    assert pc._prune_library_plan("Port")["removed"] == []


def test_a_reviewer_selected_member_is_never_removed_however_dead(group):
    """No script names `check_lldp_lag` at all here. It stays: a human put it there."""
    script(group, "test-9001.33234.py", "from library_9001 import *\nprint('nothing')\n")
    plan = pc._prune_library_plan("Port")
    assert ART_TAG not in [r["tag"] for r in plan["removed"]]
    assert "def check_lldp_lag" in plan["code"]


def test_a_reference_from_the_untagged_preamble_counts(group):
    """An LLM-authored library is ALL preamble, and its helpers call things too."""
    lib = group / "library_9001.py"
    lib.write_text(LIB.replace("import re\n", "import re\n\n\ndef helper(p):\n    return _fmt_port(p)\n"),
                   encoding="utf-8")
    script(group, "test-9001.33234.py", "from library_9001 import *\nhelper(p)\n")
    assert pc._prune_library_plan("Port")["removed"] == []


def test_a_library_with_no_auto_added_members_is_returned_byte_for_byte(group):
    """The real state of library_9001.py on 2026-09-22: migrated, untagged, nothing to act on.
    A prune that "tidied" such a file would be rewriting work nobody asked it to touch."""
    untagged = "#!/usr/bin/python3\n# Helper library for the Port group\nimport re\n\n\ndef read_polarity(o):\n    return 'mdix'\n"
    (group / "library_9001.py").write_text(untagged, encoding="utf-8")
    script(group, "test-9001.33234.py", "from library_9001 import *\n")
    plan = pc._prune_library_plan("Port")
    assert plan["candidates"] == 0 and plan["removed"] == []
    assert plan["code"] == untagged


# --- when it refuses -------------------------------------------------------------------------

def test_a_script_that_does_not_parse_BLOCKS_the_prune(group):
    """An unparseable script reports no references. Treating that as "references nothing" is
    exactly how a prune deletes the members that script was using."""
    script(group, "test-9001.33234.py", "from library_9001 import *\ndef broken(:\n")
    plan = pc._prune_library_plan("Port")
    assert "does not parse" in plan["blocked"]
    assert plan["removed"] == [] and plan["code"] == LIB


def test_a_missing_library_is_reported_not_crashed(group):
    (group / "library_9001.py").unlink()
    plan = pc._prune_library_plan("Port")
    assert "nothing to prune" in plan["blocked"] and plan["removed"] == []


def test_the_library_itself_is_not_read_as_one_of_the_groups_scripts(group):
    """If the library counted as a script, every member would reference itself alive and prune
    could never remove anything."""
    script(group, "test-9001.33234.py", "from library_9001 import *\ncheck_lldp_lag(1, 2, 3)\n")
    plan = pc._prune_library_plan("Port")
    assert plan["scripts"] == ["test-9001.33234.py"]
    assert plan["removed"], "the library vouched for its own members"


# --- the plan is a plan until asked ----------------------------------------------------------

def test_planning_never_writes(group):
    script(group, "test-9001.33234.py", "from library_9001 import *\ncheck_lldp_lag(1, 2, 3)\n")
    before = (group / "library_9001.py").read_text(encoding="utf-8")
    plan = pc._prune_library_plan("Port")
    assert plan["removed"], "nothing to remove — this test would pass vacuously"
    assert (group / "library_9001.py").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("apply_it, still_there", [(False, True), (True, False)])
def test_the_endpoint_writes_only_when_asked(group, apply_it, still_there):
    import asyncio
    script(group, "test-9001.33234.py", "from library_9001 import *\ncheck_lldp_lag(1, 2, 3)\n")
    res = asyncio.run(pc.library_prune({"group": "Port", "apply": apply_it}))
    assert res["applied"] is apply_it
    on_disk = (group / "library_9001.py").read_text(encoding="utf-8")
    assert ("def _fmt_port" in on_disk) is still_there


def test_the_endpoint_refuses_a_missing_group():
    from fastapi import HTTPException
    import asyncio
    with pytest.raises(HTTPException) as e:
        asyncio.run(pc.library_prune({}))
    assert e.value.status_code == 400


def test_a_blocked_plan_never_carries_removals(group):
    """The invariant the endpoint's guard leans on: blocking returns before removals are
    computed, so `blocked` and `removed` can never both be set."""
    script(group, "test-9001.33234.py", "from library_9001 import *\ndef broken(:\n")
    plan = pc._prune_library_plan("Port")
    assert plan["blocked"] and plan["removed"] == []


def test_the_endpoint_refuses_to_write_a_blocked_plan(group, monkeypatch):
    """...and the endpoint honours it independently, in case that ever stops being true.
    Driven with a planner that reports BOTH, which the real one cannot produce today — the
    point is that the endpoint does not rely on it not producing one."""
    import asyncio
    before = (group / "library_9001.py").read_text(encoding="utf-8")
    monkeypatch.setattr(pc, "_prune_library_plan", lambda g: {
        "group": g, "family": 9001, "library": "library_9001.py", "folder": "9001_Port",
        "scripts": [], "candidates": 1, "kept": [],
        "removed": [{"tag": AI_TAG, "names": ["_fmt_port"]}],
        "code": "# WRITTEN FROM A BLOCKED PLAN\n",
        "blocked": "test-9001.33234.py does not parse"})
    res = asyncio.run(pc.library_prune({"group": "Port", "apply": True}))
    assert res["applied"] is False
    assert (group / "library_9001.py").read_text(encoding="utf-8") == before

r"""ART family numbering — `<family>.<case>.<TestCase>` (PLAN-art-family-numbering-and-prune.md).

Three hazards drive what is pinned here:

1. **Allocation must never hand one number to two groups.** A reused family silently re-points
   yesterday's `test-9001.*.log` at a different group's work, and nothing in the run output
   would say so. So: the registry is authoritative, and a number merely SEEN on disk is taken
   even when the registry has never heard of it.
2. **The filename still has to satisfy the framework.** `ATTestSet` parses
   `test-(\d+).(\d+).*\.py` out of it and names the run log from the match; a name that misses
   sends every run to `test-0.0.log`. The regex is asserted against the real one, not described.
3. **A corrupt or absent registry must degrade, not explode.** It is a state file in a tree
   people edit; taking the Generate panel down over it would be a worse failure than
   re-allocating from what survived.
"""
import json
import re
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"))
from routers import pytest_create as pc          # noqa: E402
from fastapi import HTTPException                # noqa: E402


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """An isolated generated/ tree. The real one is a committed artifact — a test that
    allocated into it would rewrite the repo's own registry."""
    gen = tmp_path / "generated"
    gen.mkdir()
    monkeypatch.setattr(pc, "PT_GENERATED_DIR", gen)
    monkeypatch.setattr(pc, "META_ROOT", gen / ".meta")
    monkeypatch.setattr(pc, "FAMILY_REGISTRY", gen / ".families.json")
    return gen


# --- allocation ------------------------------------------------------------------------------

def test_the_first_group_takes_9001_and_the_next_takes_9002(tree):
    assert pc._family_for_group("Port") == 9001
    assert pc._family_for_group("Switching") == 9002


def test_allocation_is_idempotent(tree):
    """Both generation paths call this; if it moved, the library stem in the frame would move
    with it and slice A's `assembled_hash` gating would 409 every splice."""
    assert pc._family_for_group("Port") == 9001
    assert pc._family_for_group("Port") == 9001
    assert pc._family_for_group("Port") == 9001


def test_9000_is_reserved_and_never_handed_to_a_group(tree):
    for i, g in enumerate(["A", "B", "C", "D"]):
        assert pc._family_for_group(g) == 9001 + i
    assert 9000 not in pc._family_registry().values()
    assert pc.PT_LIBRARY_SUITE == "9000"
    assert pc.PT_FAMILY_MIN == 9001


def test_a_blank_group_becomes_Ungrouped_rather_than_a_second_bucket(tree):
    assert pc._family_for_group("") == pc._family_for_group("Ungrouped")
    assert pc._family_for_group("   ") == pc._family_for_group("Ungrouped")
    assert list(pc._family_registry()) == ["Ungrouped"]


def test_a_number_seen_on_disk_is_never_reallocated(tree):
    """THE failure this guards: a folder restored from git, or committed by the other stream,
    whose number the registry does not know. Handing 9001 to a different group would make two
    groups share a library and a log name."""
    (tree / "9001_Port").mkdir()
    assert pc._family_registry() == {}          # the registry has never heard of it
    assert pc._family_for_group("Switching") == 9002


def test_a_number_seen_only_under_meta_is_also_taken(tree):
    (tree / ".meta").mkdir()
    (tree / ".meta" / "9001_Port").mkdir()
    assert pc._family_for_group("Switching") == 9002


def test_the_registry_wins_over_the_folders(tree):
    """D3: the registry is authoritative. A group that has a number keeps it even when its
    folder was renamed or removed, so the number cannot drift to someone else."""
    pc._write_family_registry({"Port": 9001})
    (tree / "9007_Port").mkdir()                # a stale/hand-made folder disagreeing
    assert pc._family_for_group("Port") == 9001


def test_the_registry_is_consulted_ALONE_not_cross_checked_against_the_folders(tree):
    """The steady state: Port holds 9001 and 9001_Port exists on disk. The lookup has to be the
    registry by itself. Conditioning it on disk — "return the stored number unless it is already
    taken" reads plausible — makes a group's OWN folder evict its own number, so every save
    allocates it a fresh family and the group's scripts scatter across 9001, 9002, 9003…"""
    pc._write_family_registry({"Port": 9001})
    (tree / "9001_Port").mkdir()
    assert pc._family_for_group("Port") == 9001
    assert pc._family_registry() == {"Port": 9001}      # and nothing new was allocated


def test_holes_are_filled_lowest_first(tree):
    pc._write_family_registry({"Port": 9002})
    assert pc._family_for_group("Switching") == 9001


def test_exhaustion_raises_rather_than_wrapping_into_the_reserved_block(tree):
    pc._write_family_registry({f"G{n}": n for n in range(pc.PT_FAMILY_MIN, pc.PT_FAMILY_MAX + 1)})
    with pytest.raises(HTTPException) as e:
        pc._family_for_group("OneTooMany")
    assert e.value.status_code == 507 and "exhausted" in str(e.value.detail)


# --- the registry file -----------------------------------------------------------------------

def test_a_corrupt_registry_reads_as_empty_instead_of_raising(tree):
    (tree / ".families.json").write_text("{not json at all", encoding="utf-8")
    assert pc._family_registry() == {}
    assert pc._family_for_group("Port") == 9001          # and allocation still works


def test_a_missing_registry_reads_as_empty(tree):
    assert not (tree / ".families.json").exists()
    assert pc._family_registry() == {}


def test_values_outside_the_block_are_ignored_not_trusted(tree):
    (tree / ".families.json").write_text(json.dumps(
        {"families": {"Good": 9005, "Reserved": 9000, "Huge": 12345, "Junk": "nine"}}),
        encoding="utf-8")
    assert pc._family_registry() == {"Good": 9005}


def test_the_write_is_atomic_and_leaves_no_temp_behind(tree):
    pc._write_family_registry({"Port": 9001})
    assert [p.name for p in tree.iterdir() if p.is_file()] == [".families.json"]
    body = json.loads((tree / ".families.json").read_text(encoding="utf-8"))
    assert body["families"] == {"Port": 9001}
    assert body["reserved"] == {"9000": "libraries — never allocated to a group"}


# --- the names the framework parses ----------------------------------------------------------

def test_the_script_name_carries_the_family_in_the_suite_position():
    assert pc._art_script_name("AWPTCM-T33234", 9001) == "test-9001.33234"
    assert pc._art_script_name("AWPTCM-T33233", 9002) == "test-9002.33233"


def test_the_framework_still_parses_the_name_it_is_given():
    r"""ATTestSet.py:71 — `test-(\d+).(\d+).*\.py`. A name that misses it silently keeps the
    '0' defaults and every run in the group lands in test-0.0.log."""
    framework_rx = re.compile(r"test-(\d+).(\d+).*\.py")
    m = framework_rx.search(pc._art_script_name("AWPTCM-T33234", 9001) + ".py")
    assert m and m.group(1) == "9001" and m.group(2) == "33234"


def test_a_keyless_case_still_produces_a_parseable_name():
    name = pc._art_script_name("no-digits-here", 9003)
    assert name.startswith("test-9003.0_")
    assert re.search(r"test-(\d+).(\d+).*\.py", name + ".py")


def test_the_group_dir_is_ARTs_suite_dir_shape(tree):
    assert pc._group_dir_name("Port", 9001) == "9001_Port"
    assert pc._group_dir_name("Advanced Management", 9004) == "9004_Advanced_Management"
    assert pc._group_dir_name("Authentication_Security", 9005) == "9005_Authentication_Security"
    assert pc._group_dir_name("Layer-3 Switching", 9006) == "9006_Layer_3_Switching"


def test_the_group_dir_allocates_when_no_family_is_given(tree):
    assert pc._group_dir_name("Port") == "9001_Port"


def test_the_script_and_meta_paths_land_under_the_family_dir(tree):
    assert pc._script_path("Port", "test-9001.33234") == tree / "9001_Port" / "test-9001.33234.py"
    assert pc._meta_dir("Port", "test-9001.33234") == tree / ".meta" / "9001_Port" / "test-9001.33234"


# --- the third part of the triple ------------------------------------------------------------

SEQ = [{"n": 1, "action": "show interface port1.0.1", "verify": "the port reads connected"},
       {"n": 2, "action": "show interface port1.0.2", "verify": "the port reads connected"}]


def test_each_TestCase_carries_the_full_ART_triple():
    """ART's own shape — `testCaseRef = 'CR-52769, 1331.1001.52769'`. ATTestCase._preRun writes
    testCaseRef into the log's TEST_CASE_REFERENCES block, so this is where the reference lands
    in the artifact a reader actually has."""
    sk = pc._render_skeleton("AWPTCM-T33234", "t", SEQ, [], [], "", None, "9001.33234")
    assert "testCaseRef = 'AWPTCM-T33234, 9001.33234.1'" in sk
    assert "testCaseRef = 'AWPTCM-T33234, 9001.33234.2'" in sk


def test_the_case_key_is_never_dropped_for_the_triple():
    sk = pc._render_skeleton("AWPTCM-T33234", "t", SEQ, [], [], "", None, "9001.33234")
    assert sk.count("AWPTCM-T33234") >= 2


def test_without_an_art_set_the_ref_is_the_case_key_alone():
    """The fragment-preview path renders with no family; it must not emit a half-formed id."""
    sk = pc._render_skeleton("AWPTCM-T33234", "t", SEQ, [], [])
    assert "testCaseRef = 'AWPTCM-T33234'" in sk
    assert "9001." not in sk and ", ." not in sk


def test_the_triple_matches_what_the_framework_log_prints():
    """`pt_exec._CASE_START` parses `>> test-<suite>.<set>.<case>`; the ref must be that same
    string, or the reference in the script and the line in the log disagree."""
    sk = pc._render_skeleton("AWPTCM-T33234", "t", SEQ, [], [], "", None, "9001.33234")
    ref = re.search(r"testCaseRef = 'AWPTCM-T33234, (\S+)'", sk).group(1)
    import pt_exec as px
    assert px._CASE_START.match(f">> test-{ref}")

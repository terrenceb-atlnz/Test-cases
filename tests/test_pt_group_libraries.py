"""R1(b) — one library per GROUP, merged by provenance tag (PLAN-group-libraries.md).

Three things are pinned here, in order of how badly they would bite:

1. **The two generation paths must derive the SAME stem.** `_pt_generation_context` exists to
   mirror `generate_script`'s derivation so a per-unit run and a whole-script run start from a
   byte-identical frame. The library stem is part of that frame (`from <stem> import *`), so a
   divergence changes `assembled_hash` and makes slice A's gating 409 on every splice.
2. **Merge, never overwrite.** Every script in a group now writes ONE library path, so the
   second save would otherwise destroy the first script's members.
3. **The fold itself**, including the collision it knowingly introduces.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"))
from routers import pytest_create as pc          # noqa: E402


# --- 3. the stem ---------------------------------------------------------------------------

def test_the_stem_is_the_groups_ART_FAMILY_not_the_case_and_not_the_group_name():
    """Since PLAN-art-family-numbering-and-prune.md the stem is ART's own `library_<suite>`.
    It was `library_<case>` (one copy per case), then `library_<group>` for one day — the group
    fold only existed because every script shared suite 9000, which a family per group fixes."""
    assert pc._family_library_stem(9001) == "library_9001"
    assert pc._family_library_stem(9002) == "library_9002"


def test_the_fold_collision_is_retired_by_the_numbering():
    """`_group_library_stem` knowingly collided `Port A` with `Port-A`. Numbers cannot collide,
    so that trade-off is GONE — asserted here so nobody reintroduces a name-derived stem."""
    assert not hasattr(pc, "_group_library_stem"), (
        "_group_library_stem is back: the stem must key on the family, which is collision-free")
    assert pc._family_library_stem(9001) != pc._family_library_stem(9010)


# --- 1. one derivation, two paths ----------------------------------------------------------

class _Sess:
    def __init__(self, group="", naming=None):
        self.group = group
        self.step6 = {"naming": naming} if naming else {}


def test_effective_group_prefers_the_persisted_naming():
    assert pc._effective_group(_Sess("Port (7)", {"group": "Port"})) == "Port"


def test_effective_group_falls_back_to_the_sanitised_group_display():
    # _group_display strips the candidate count and the charset _validate_naming refuses
    assert pc._effective_group(_Sess("Port (7)")) == "Port"
    assert pc._effective_group(_Sess("Authentication & Security (42)")) == "Authentication_Security"


def test_both_generation_paths_pass_the_group_into_build_library():
    """A source assertion, deliberately: the hazard is that ONE path is updated and the other
    keeps re-deriving, which no behavioural test of either path alone would catch."""
    src = pathlib.Path(pc.__file__).read_text(encoding="utf-8")
    calls = re.findall(r"(?<!def )_build_library\(([^,]+),\s*([^,]+),", src)
    assert calls, "no _build_library call sites found — did it get renamed?"
    for group_arg, family_arg in calls:
        assert group_arg.strip() in ("group", "_group"), (
            f"_build_library is called with group={group_arg.strip()!r}: every call site must "
            "pass a resolved GROUP, or the two generation paths derive different frames")
        assert family_arg.strip() in ("family", "_family"), (
            f"_build_library is called with family={family_arg.strip()!r}: the FAMILY must be "
            "passed in too — re-deriving it inside would let the two paths drift")


# --- 2. merge, never overwrite --------------------------------------------------------------

TAG_A = "# ART art/1332_lldp_med/test-1332.1.py lines 10-12"
TAG_B = "# AI: dependency `LLDP_PHONE_PKT` of " + TAG_A

EXISTING = f'''"""library_9001 — helpers shared by the Port group (ART family 9001)."""
import time


{TAG_A}
def check_lldp_lag(testCase, eth, tb):
    return True
'''

INCOMING = f'''"""library_9001 — helpers shared by the Port group (ART family 9001)."""
import re
import time


{TAG_A}
def check_lldp_lag(testCase, eth, tb):
    return "REWRITTEN BY THE GENERATOR"


{TAG_B}
LLDP_PHONE_PKT = Ether()
'''


def test_a_member_already_present_is_left_byte_for_byte():
    out = pc._merge_library_code(EXISTING, INCOMING)
    assert "return True" in out, "the existing member was replaced"
    assert "REWRITTEN BY THE GENERATOR" not in out


def test_a_member_with_a_new_tag_is_appended():
    out = pc._merge_library_code(EXISTING, INCOMING)
    assert TAG_B in out and "LLDP_PHONE_PKT = Ether()" in out


def test_imports_are_unioned_without_duplicating():
    out = pc._merge_library_code(EXISTING, INCOMING)
    assert out.count("import time") == 1
    assert "import re" in out


def test_an_untagged_library_is_preserved_WHOLE():
    """The real case, not a hypothetical: the T33234 library shipped in 3c680c9 is an
    LLM-authored helper module with zero provenance tags. Merging must not shred it."""
    untagged = '''#!/usr/bin/python3
# Helper library for AWPTCM-T33234 — Port - Auto MDI/MDI-X
import re

_CONFIGURED_RE = {'duplex': re.compile(r'configured\\s+duplex')}


def read_polarity(dev, port):
    return "mdix"
'''
    out = pc._merge_library_code(untagged, INCOMING)
    for line in untagged.splitlines():
        if line.strip():
            assert line in out, f"untagged content lost: {line!r}"
    assert TAG_A in out and TAG_B in out          # and the new members still arrived


def test_merging_into_nothing_is_just_the_incoming_file():
    assert pc._merge_library_code("", INCOMING) == INCOMING
    assert pc._merge_library_code("   \n", INCOMING) == INCOMING


def test_merge_is_idempotent():
    once = pc._merge_library_code(EXISTING, INCOMING)
    assert pc._merge_library_code(once, INCOMING) == once


def test_imports_land_after_the_header_when_the_file_has_none():
    """With no import line to anchor to, new imports must sit after the header comments and
    BEFORE the first statement, or the merged module does not import.

    This found a real bug: the fallback originally anchored to the END OF THE PREAMBLE, and in
    an UNTAGGED file the preamble is the whole file — so the imports landed after the code that
    needed them. It now scans the leading shebang/comment run instead."""
    no_imports = '''#!/usr/bin/python3
# Helper library for the Port group
# second header line

WIDGET = 1
'''
    out = pc._merge_library_code(no_imports, INCOMING)
    lines = out.splitlines()
    assert "import re" in lines and "import time" in lines
    assert lines.index("import re") > lines.index("# second header line"), "imports landed above the header"
    assert lines.index("import re") < lines.index("WIDGET = 1"), "imports landed after the first statement"
    compile(out, "merged", "exec")          # and the result is importable Python


# --- 4. a new member may not re-define a name the library already has (2026-09-24) ----------

TAG_C = "# legacy 5000_mdi_mdix/library_5000.py lines 61-85"

CLASHING = f'''"""library_9001 — helpers shared by the Port group (ART family 9001)."""
import time


{TAG_C}
def check_lldp_lag(testCase, eth, tb, expect_value):
    return "A DIFFERENT CONTRACT UNDER THE SAME NAME"
'''


def test_a_new_tag_member_redefining_an_existing_name_is_refused():
    """AWPTCM-T33235 appended six helpers whose names T33234's library already defined, and the
    later `def` wins at import — so T33234 would have silently called T33235's versions."""
    import pytest
    with pytest.raises(pc.LibraryNameClash) as e:
        pc._merge_library_code(EXISTING, CLASHING)
    assert e.value.names == ["check_lldp_lag"]


def test_the_clash_is_detected_against_an_UNTAGGED_library_too():
    import pytest
    untagged = "import re\n\n\ndef check_lldp_lag(testCase, eth, tb):\n    return True\n"
    with pytest.raises(pc.LibraryNameClash):
        pc._merge_library_code(untagged, CLASHING)


def test_saving_a_clashing_library_writes_NOTHING(tmp_path, monkeypatch):
    import pytest
    from fastapi import HTTPException
    gen = tmp_path / "generated"
    gen.mkdir()
    monkeypatch.setattr(pc, "PT_GENERATED_DIR", gen)
    monkeypatch.setattr(pc, "META_ROOT", gen / ".meta")
    monkeypatch.setattr(pc, "FAMILY_REGISTRY", gen / ".families.json")
    script = pc._script_path("Port", "test-9001.2")
    script.parent.mkdir(parents=True, exist_ok=True)
    lib = script.parent / "library_9001.py"
    lib.write_text(EXISTING, encoding="utf-8")
    s = pc.PtSession(key="AWPTCM-T2")
    s.step6 = {"naming": {"group": "Port", "name": "test-9001.2"},
               "files": {"test": {"name": "test-9001.2.py", "code": "print('x')\n"},
                         "library": {"name": "library_9001.py", "code": CLASHING}}}
    with pytest.raises(HTTPException) as e:
        pc._persist_generated_files(s)
    assert e.value.status_code == 409 and "check_lldp_lag" in e.value.detail
    assert not script.exists(), "the script was written although the save was refused"
    assert lib.read_text(encoding="utf-8") == EXISTING, "the group library was changed"

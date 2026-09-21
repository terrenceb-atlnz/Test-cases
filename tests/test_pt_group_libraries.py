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


# --- 3. the fold ---------------------------------------------------------------------------

def test_the_stem_is_keyed_on_the_group_not_the_case():
    assert pc._group_library_stem("Port") == "library_port"
    assert pc._group_library_stem("Management") == "library_management"


def test_group_names_that_are_not_module_names_are_folded():
    # _GROUP_RX admits spaces, parens and hyphens; a module name admits none of them.
    assert pc._group_library_stem("Authentication_Security") == "library_authentication_security"
    assert pc._group_library_stem("Port (7)") == "library_port_7"
    assert pc._group_library_stem("Layer-3 Switching") == "library_layer_3_switching"
    assert pc._group_library_stem("") == "library_group"          # never a bare "library_"


def test_the_known_collision_is_documented_not_accidental():
    """`Port A` and `Port-A` fold together. This is ASSERTED so it stays a known trade-off:
    if someone later guards it, this test fails and they must update the docstring too."""
    assert pc._group_library_stem("Port A") == pc._group_library_stem("Port-A")


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
    calls = re.findall(r"(?<!def )_build_library\(([^,]+),", src)
    assert calls, "no _build_library call sites found — did it get renamed?"
    for arg in calls:
        arg = arg.strip()
        assert arg in ("group", "_effective_group(sess)"), (
            f"_build_library is called with {arg!r}: every call site must pass the GROUP, "
            "or the two generation paths derive different frames")


# --- 2. merge, never overwrite --------------------------------------------------------------

TAG_A = "# ART art/1332_lldp_med/test-1332.1.py lines 10-12"
TAG_B = "# AI: dependency `LLDP_PHONE_PKT` of " + TAG_A

EXISTING = f'''"""library_port — helpers shared by the Port group."""
import time


{TAG_A}
def check_lldp_lag(testCase, eth, tb):
    return True
'''

INCOMING = f'''"""library_port — helpers shared by the Port group."""
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

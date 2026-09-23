"""Tier A + Tier B import tidy at assembly (Terrence, 2026-09-23: remove at assembly, recorded).

WHY. The frame header is rendered line by line from the selected fragments' imports, so a case
carried imports nothing used (the saved T33234 had three), two lines for one framework
package, and no grouping — and pycodestyle cannot see an unused import (pyflakes F401). Now
Assemble tidies the leading import run deterministically. Pinned: unused names go and are
recorded; same-module `from` lines merge; stdlib / framework / local are grouped; star imports,
the framework base classes and trailing comments survive; anything unjudgeable is left alone;
the pass is idempotent and only runs when the units changed. Offline: real module.
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))
pytest.importorskip("models")
from routers import pytest_create as pc  # noqa: E402

CODE = '''import sys
import time
import re
from framework import ATTestSet, ATTestCase
from framework.ATDrivers import ATTestBox   # tells the testbox from a switch
from framework.ATPackets import *   # scapy + AT layers
from framework.ATLibrary import ATTools
from framework.ATLibrary import ATLimits
from framework.ATDrivers import ATSwitch
from library_9001 import *   # this FAMILY's helpers

X = 1


class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        self.far = isinstance(setup, ATTestBox.TestBox) or ATTools.x(time.time())


if __name__ == '__main__':
    ts = TestSet()
    ts.run(sys.argv)
'''


def test_unused_go_same_module_lines_merge_and_groups_are_separated():
    new, changes = pc._tidy_imports(CODE)
    head = new.split("\nX = 1")[0]
    assert "import re" not in head and "ATLimits" not in head and "ATSwitch" not in head
    assert "from framework.ATDrivers import ATTestBox   # tells the testbox from a switch" in head
    assert "from framework.ATPackets import *" in head and "from library_9001 import *" in head
    assert "from framework import ATTestSet, ATTestCase" in head
    assert head.index("import time") < head.index("\n\nfrom framework import") < head.index("\n\nfrom library_9001")
    assert any("import re" in c for c in changes) and any("ATLimits" in c for c in changes)
    compile(new, "<t>", "exec")


def test_merging_keeps_both_names():
    code = CODE.replace("from framework.ATLibrary import ATLimits",
                        "from framework.ATLibrary import ATPrint").replace(
        "ATTools.x(time.time())", "ATTools.x(time.time()) or ATPrint")
    new, changes = pc._tidy_imports(code)
    assert "from framework.ATLibrary import ATTools, ATPrint" in new
    assert any(c.startswith("merged") for c in changes)


def test_it_is_idempotent_and_leaves_a_broken_script_alone():
    once, _ = pc._tidy_imports(CODE)
    assert pc._tidy_imports(once) == (once, [])
    broken = CODE + "\ndef oops(:\n"
    assert pc._tidy_imports(broken) == (broken, [])


def test_assemble_only_tidies_when_the_units_changed():
    src = Path(pc.__file__).read_text(encoding="utf-8")
    body = src[src.index("def _assemble_and_store("):]
    body = body[:body.index("\ndef ")]
    assert 'if not (frame.get("code") and code == frame["code"]):' in body
    assert "stamped, import_changes = _tidy_imports(stamped)" in body
    assert '"imports": import_changes' in body

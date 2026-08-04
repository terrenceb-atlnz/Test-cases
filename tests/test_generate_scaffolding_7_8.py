"""Phase 7.8 — the generate scaffolding must not earn the model a lint error.

Three self-contradictions between what the prompt/skeleton TELL the model and what the
lint PUNISHES. Two of them produced BLOCKING errors, which have no override — the sharper
form of the T44297 problem that motivated the authority split in the first place.

  1. Rule 3 rendered `_detect_topology`'s raw switch list as "init binds: ...", but the
     skeleton caps the bound set at the DUT plus one partner. Measured before the fix:
         detected -> ['swi_a', 'swi_b', 'swi_c']     what the prompt claimed
         skeleton -> ['swi_a', 'swi_b', 'tb']        what init() really binds
     Wrong in BOTH directions: naming `swi_c` invites `self.testSet.swi_c` and the blocking
     "uses device ... but init() never binds", while the testbox `tb` IS bound and was
     never mentioned.
  2. Eight `>>> FILL` markers sat on CODE lines, which `_strip_fill_markers` documents it
     cannot remove ("a line with real code before the '#' is kept") — so each one that
     survived was a blocking "unfilled template placeholder".
  3. Rules 1 and 8 both claimed the first line of every `main()`.

And a fourth found while fixing #2: the stripper matched `>>> (FILL|replace|remove)` while
the lint errors on ANY `>>>`, so `# >>> adjust operator timeout (s) <<<` was unstrippable
AND a hard error even once it sat on its own comment line.

Moving the markers off code lines would have deleted the ONLY detection of an unfilled
verification slot, because that detection WAS the marker. So the placeholder CODE is now
checked directly — which is the thing that actually matters: a marker is a comment, but
`if False:` is a test that can never pass.

Offline: renders the real skeleton and lints it. No network, no LLM, no testbox.
"""
import ast
import py_compile
import sys
import tempfile
import os
import pathlib

import pytest

_SERVER = pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"
for _p in (str(_SERVER), str(_SERVER / "routers")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest_create as pc  # noqa: E402


SEQ = [
    {"n": 1, "action": "configure the trunk on swi_a and swi_b and swi_c", "verify": "", "kind": "setup"},
    {"n": 2, "action": "check the swi_a version", "verify": "the version is shown", "kind": "verify"},
    {"n": 3, "action": "unplug the cable", "verify": "the link drops", "kind": "physical"},
    {"n": 4, "action": "check the LED", "verify": "the LED is green", "kind": "manual"},
]


def _skeleton(seq=None):
    seq = SEQ if seq is None else seq
    return pc._render_skeleton("AWPTCM-T00001", "a title", seq, [], [])


def _compiles(code):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        py_compile.compile(tmp, doraise=True)
        return True
    finally:
        os.unlink(tmp)


class _Sess:
    """The slice of PtSession that `_lint_generated` reads."""
    def __init__(self, code, seq=SEQ):
        self.key = "AWPTCM-T00001"
        self.step6 = {"files": {"test": {"code": code}}}
        self.step2 = {"sequence": seq}
        self.payload = {self.key: {"objective": "<ul><li>a thing</li></ul>",
                                   "testScript": {"steps": [{"description": "Note: Traceability"},
                                                            {"description": "check the version"}]}}}


def _lint(code, seq=SEQ):
    return pc._lint_generated(_Sess(code, seq))


# ------------------------------------------------- 1. the prompt names what init binds

def test_bound_devices_come_from_the_skeleton_not_the_sequence_text():
    """THE REGRESSION. `swi_c` is mentioned, detected, and deliberately NOT bound."""
    detected, _, _ = pc._detect_topology(SEQ, [])
    assert "swi_c" in detected, "the fixture must exercise the over-detection case"
    devs = pc._skeleton_bound_devices(_skeleton(), detected[0])
    assert "swi_c" not in devs, \
        "the prompt would name a device init() drops — a BLOCKING lint the model cannot win"


def test_every_named_device_is_really_assigned_in_init():
    """The invariant, stated directly: whatever we name, init() must bind."""
    skel = _skeleton()
    devs = pc._skeleton_bound_devices(skel)
    tree = ast.parse(skel)
    init = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "init")
    assigned = {t.attr for n in ast.walk(init) if isinstance(n, ast.Assign)
                for tgt in n.targets
                for t in (tgt.elts if isinstance(tgt, (ast.Tuple, ast.List)) else [tgt])
                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                and t.value.id == "self"}
    assert devs, "the skeleton binds at least the DUT"
    assert set(devs) <= assigned


def test_the_bound_testbox_is_reported():
    """Wrong in the other direction too: init binds `tb` and the prompt never said so."""
    assert "tb" in pc._skeleton_bound_devices(_skeleton())


def test_the_dut_is_first_because_the_prompt_uses_it_as_the_example():
    """`pt_generate_script.jinja` renders `self.testSet.{{ bound_devices[0] }}`; source
    order puts the testbox first, which would make the worked example use `tb`."""
    detected, _, _ = pc._detect_topology(SEQ, [])
    assert pc._skeleton_bound_devices(_skeleton(), detected[0])[0] == detected[0]


def test_a_port_is_not_a_device():
    """`ck_far_port` is a SwitchPort bound in init; it is not reachable as a device."""
    assert "ck_far_port" not in pc._skeleton_bound_devices(_skeleton())


def test_an_unparseable_skeleton_yields_nothing_rather_than_raising():
    assert pc._skeleton_bound_devices("def broken(:") == []


def test_the_generate_prompt_is_actually_fed_the_skeleton_derived_list():
    """The wiring, not just the helper.

    Found by mutation: reverting the call site to `_detect_topology`'s raw list left every
    other test in this file green, because they all exercise `_skeleton_bound_devices`
    directly. A correct helper nobody calls fixes nothing.
    """
    source = pathlib.Path(pc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    # `skeleton_devs` must be derived from the RENDERED skeleton.
    derived = [n for n in ast.walk(tree)
               if isinstance(n, ast.Assign)
               and any(getattr(t, "id", None) == "skeleton_devs" for t in n.targets)
               and isinstance(n.value, ast.Call)
               and getattr(n.value.func, "id", "") == "_skeleton_bound_devices"]
    assert derived, "skeleton_devs is no longer computed from _skeleton_bound_devices"

    # ...and the prompt context must be fed from it.
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == "bound_devices":
                names |= {n.id for n in ast.walk(v) if isinstance(n, ast.Name)}
    assert names, "no `bound_devices` prompt-context entry found at all"
    assert "skeleton_devs" in names, (
        "the generate prompt is fed a device list that is NOT what init() binds — naming a "
        "dropped device earns the blocking 'uses device ... but init() never binds'")


# --------------------------------------------- 2 & 4. every marker is now strippable

def test_no_marker_sits_on_a_code_line():
    """`_strip_fill_markers` keeps any line with real code before the '#', so a marker
    sharing a line with code can only ever become a blocking lint error."""
    offenders = [ln.strip() for ln in _skeleton().splitlines()
                 if ">>>" in ln and not ln.lstrip().startswith("#")]
    assert not offenders, f"markers on code lines: {offenders}"


def test_the_stripper_removes_every_marker_the_skeleton_emits():
    survivors = [ln.strip() for ln in pc._strip_fill_markers(_skeleton()).splitlines()
                 if ">>>" in ln]
    assert not survivors, f"unstrippable markers: {survivors}"


def test_the_stripper_matches_the_shape_the_lint_punishes():
    """The fourth defect: an allowlist of verbs left `# >>> adjust ... <<<` unstrippable
    while the lint errored on any `>>>`. The two must not diverge again."""
    assert pc._FILL_MARKER_RX.search("# >>> adjust operator timeout (s) <<<")
    assert pc._FILL_MARKER_RX.search("# >>> anything at all <<<")


def test_a_stripped_skeleton_still_compiles():
    assert _compiles(pc._strip_fill_markers(_skeleton()))


def test_stripping_never_removes_a_line_carrying_code():
    """The guarantee the stripper is built on, pinned against the new broader regex."""
    code = "x = 1  # >>> FILL: something <<<\ny = 2\n"
    assert "x = 1" in pc._strip_fill_markers(code)


# ------------------------------------- the placeholder detection that replaces them

_HEAD = """import sys
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):
    pass


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = 'd'
    testCaseRef = 'AWPTCM-T00001'
    testCaseMethod = 'm'

    def main(self):
        # AI test 2026-08-05
        self.log('STEP 1: do the thing')
"""


def _case(body):
    return _HEAD + body + "\nts = TestSet()\nts.run(sys.argv)\n"


def test_an_unfilled_if_false_is_an_error():
    errs = _lint(_case("""        output = self.testSet.dut.cmd('show version')
        self.log('OBSERVED: {}'.format(output))
        if False:
            self.passed('ok')
        else:
            self.failed('no')
"""))["errors"]
    assert any("still branches on `if False:`" in e for e in errs), errs


def test_an_unfilled_if_true_is_an_error_too():
    """The mirror image: a test that can never fail."""
    errs = _lint(_case("""        output = self.testSet.dut.cmd('show version')
        self.log('OBSERVED: {}'.format(output))
        if True:
            self.passed('ok')
        else:
            self.failed('no')
"""))["errors"]
    assert any("still branches on `if True:`" in e for e in errs), errs


def test_an_empty_observation_that_is_never_reassigned_is_an_error():
    errs = _lint(_case("""        output = ''
        self.log('OBSERVED: {}'.format(output))
        if 'up' in output:
            self.passed('ok')
        else:
            self.failed('no')
"""))["errors"]
    assert any("never reassigns it" in e for e in errs), errs


def test_the_physical_poll_shape_is_not_flagged():
    """THE FALSE POSITIVE GUARD. The physical step legitimately seeds `output = ''`
    before its poll loop and reassigns it inside — a blanket text match would condemn
    a correct script, which is why the check requires 'never reassigned'."""
    errs = _lint(_case("""        output = ''
        while True:
            output = self.testSet.dut.cmd('show interface status')
            if 'connected' in output:
                break
        self.log('OBSERVED: {}'.format(output))
        if 'connected' in output:
            self.passed('ok')
        else:
            self.failed('no')
"""))["errors"]
    assert not any("never reassigns it" in e for e in errs), errs


def test_a_properly_filled_step_raises_neither_placeholder_error():
    errs = _lint(_case("""        output = self.testSet.dut.cmd('show version')
        self.log('OBSERVED: {}'.format(output))
        if 'AlliedWare' in output:
            self.passed('version banner present')
        else:
            self.failed('no version banner')
"""))["errors"]
    assert not any("still branches on" in e or "never reassigns" in e for e in errs), errs


def test_the_unfilled_skeleton_is_caught_now_that_its_markers_are_gone():
    """End to end: render, strip (as the server does), lint. Before Phase 7.8 this was
    caught only by the marker text; the markers are strippable now, so the code must be."""
    stripped = pc._strip_fill_markers(_skeleton())
    assert ">>>" not in stripped
    errs = _lint(stripped)["errors"]
    assert any("still branches on `if False:`" in e for e in errs), errs
    assert any("never reassigns it" in e for e in errs), errs


@pytest.mark.parametrize("msg,cls", [
    ("contract: TestCase_1.main() line 9 still branches on `if False:` — the skeleton's", "blocking"),
    ("contract: TestCase_1.main() line 9 leaves `output = ''` and never reassigns it —", "blocking"),
])
def test_the_new_errors_are_not_overridable(msg, cls):
    """No reviewer judgement turns an unfilled slot into a test."""
    blocking, policy = pc._split_lint_errors([msg])
    assert blocking == [msg] and policy == []

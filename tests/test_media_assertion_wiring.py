"""The media assertion is actually WIRED — emitted, shipped, and enforced.

`ask-ck/tools/pt_media.py` being correct is worthless if no generated script calls it. Three links in
that chain, each with its own way of silently breaking:

  1. EMITTED  — the skeleton must bind its links through `_ck_discover` / `_ck_bind_link`
                (framework discovery, 2026-09-21), not a FILL slot the model can fill with
                anything (or omit), and never from a `[misc]` declaration.
  2. SHIPPED  — `ck_media.py` must reach the run workdir, or every script dies on `import
                ck_media`. The filename in `files` and the name the template imports are two
                separate strings that must agree.
  3. ENFORCED — a script that calls `setup.init_portlink()` directly gets a port with NO media
                guarantee, which defeats the mechanism entirely. The lint has to reject that.

Pure unit tests — no DB, no network, no hardware, no LLM.
"""
import ast
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))

pc = pytest.importorskip("routers.pytest_create")
models = pytest.importorskip("models")

SKELETON = (REPO / "ask-ck" / "CK-main" / "CK_server" / "templates"
            / "pt_script_template.py.jinja")

SEQ = [{"n": 1, "action": "set speed 1000 and duplex full on the test port",
        "verify": "show interface reports 1000/full", "kind": "verify"}]
# A sequence whose wording triggers the portlink detector, so the binding block renders.
SEQ_LINKED = [{"n": 1, "action": "bring up the port link to the partner",
               "verify": "show interface reports the link up", "kind": "verify"}]


def render(seq=SEQ_LINKED, objective="verify all supported speeds"):
    return pc._render_skeleton("AWPTCM-T99999", "probe", seq, [], None, objective)


def lint_errors(code: str):
    sess = models.PtSession(
        key="AWPTCM-T00000", group="", payload={}, traceability="",
        step2={}, step3={}, step4={}, step5={},
        step6={"files": {"test": {"name": "t.py", "code": code}}})
    return pc._lint_generated(sess)["errors"]


# The LEGACY hand-repaired shape (test-9000.33234.py, saved 2026-09-21 before the discovery
# frame): its own `_ck_bind_link` still calls init_portlink INSIDE the helper. Saved scripts
# must keep linting clean, so the helper's own call stays sanctioned.
CONFORMANT = (
    "class TestSet(ATTestSet.TestSet):\n"
    "    def _ck_bind_link(self, setup, dut, misc, role):\n"
    "        import ck_media\n"
    "        (a, b) = setup.init_portlink(dut, dut, type1='port')\n"
    "        ok, why = ck_media.assert_role_media('', a.name, role)\n"
    "        return a, b, dut\n"
    "    def init(self, setup):\n"
    "        misc = setup.get_all_misc()\n"
    "        dut = setup.init_swi(misc.get('ck_role_dut', 'swi_a'))\n"
    "        self.dut = dut\n"
    "        (dut.portA, self.f, self.g) = self._ck_bind_link(setup, dut, misc, 'copper')\n")


# ------------------------------------------------------------------------ 1. EMITTED


def test_skeleton_defines_and_calls_the_binding_helper():
    sk = render()
    assert "def _ck_discover(self, dut, unit=None):" in sk
    assert "def _ck_bind_link(self, setup, dut, role, optional=False):" in sk
    assert "self._ck_bind_link(" in sk, "helper defined but never called"


def test_the_rendered_skeleton_compiles():
    ast.parse(render())


def test_the_binding_replaced_the_fill_slot():
    """The link step must be deterministic. As a FILL slot the model declared links the test
    never used — T33235 bound 4 devices and 2 links while referencing 1 of each, which made
    the script demand cabling for no reason."""
    sk = render()
    init = re.search(r"def init\(self, setup\):.*?\n    def configure", sk, re.S).group(0)
    assert "FILL: declare this case's port link" not in init
    assert "_ck_bind_link" in init


def test_the_dut_is_the_frameworks_swi_a_slot_and_its_stack_when_it_is_in_one():
    """Terrence 2026-09-21: `swi_a` IS the framework's portable DUT slot (297 corpus lookups;
    a role-named key appears 0 times), so nothing is read from `[misc]` to find it. On a
    stacked bench the ports belong to members and commands go to the master, so the stack
    handle is bound when `get_stack()` reports one."""
    sk = render()
    assert "setup.init_swi('swi_a')" in sk
    assert ".get_stack()" in sk and "setup.init_stk(_stk.name)" in sk
    assert "get_all_misc" not in sk and "ck_link" not in sk and "ck_role_dut" not in sk


def test_discovery_reads_media_from_the_device_and_a_required_role_aborts():
    """The two facts the frame must get from the DEVICE, never a file: what is in each port
    (`show interface <port> status` Type column) and which cages hold a module (`show
    system pluggable`). A required role with no matching link is a bench problem and aborts."""
    sk = render()
    disc = re.search(r"def _ck_discover.*?\n    def _ck_bind_link", sk, re.S).group(0)
    assert "get_all_port_links()" in disc
    assert "show interface %s status" in disc and "show system pluggable" in disc
    assert "ck_media.classify" in disc and "is_pluggable" in disc
    assert "isinstance(far, ATTestBox.TestBox)" in disc
    helper = re.search(r"def _ck_bind_link.*?\n    def init", sk, re.S).group(0)
    assert "RuntimeError" in helper and "optional" in helper
    assert "init_portlink" not in sk, "the frame must not fall back to first-unused matching"


def test_helper_failures_blame_the_bench_not_the_product():
    helper = re.search(r"def _ck_bind_link.*?\n    def init", render(), re.S).group(0)
    assert helper.count("BENCH PROBLEM, not a product defect") >= 1


def test_the_emitted_role_defaults_to_copper_and_follows_fibre_wording():
    assert "'copper'" in render(SEQ_LINKED, "verify all supported speeds")
    fibre = render([{"n": 1, "action": "insert the 1000BASE-SX module and bring the port link up",
                     "verify": "link up", "kind": "verify"}], "")
    assert "'fibre'" in fibre


def test_link_role_detection():
    d = pc._detect_links(SEQ, [], "")
    assert d["copper"] and not d["fibre"]
    assert pc._detect_links([], [], "verify optical fibre negotiation")["fibre"]
    assert pc._detect_links([{"action": "fit a 1000BASE-LX SFP", "verify": ""}], [])["fibre"]


# ------------------------------------------------------------------------ 2. SHIPPED


def test_the_shipped_helper_is_byte_identical_to_the_tested_module():
    """One source. A copy would let the testbox run logic the in-repo tests never saw."""
    assert pc._media_helper_source() == (REPO / "ask-ck" / "tools" / "pt_media.py").read_text(
        encoding="utf-8")


def test_the_shipped_filename_matches_the_name_the_template_imports():
    """Two independent strings; if they drift, every run dies on `import ck_media`."""
    module = Path(pc.MEDIA_HELPER_NAME).stem
    assert re.search(rf"^\s*import {re.escape(module)}\b", SKELETON.read_text(), re.M), (
        f"template does not `import {module}` but runs ship {pc.MEDIA_HELPER_NAME}")


def test_the_run_endpoint_adds_the_helper_to_the_upload_set():
    """Structural, because exercising `/run` needs a live session + SSH. The upload dict is
    the only thing that puts `ck_media.py` in the workdir, so its removal must fail the gate
    rather than surface as `ImportError` on a testbox."""
    src = Path(pc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    run_fn = next((n for n in ast.walk(tree)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == "run_script"), None)
    assert run_fn is not None, "run_script endpoint not found — has it been renamed?"
    body = "\n".join(src.splitlines()[run_fn.lineno - 1:run_fn.end_lineno])
    assert "run_manager.start(" in body, "wrong function: this one does not launch a run"
    assert re.search(r"files\[\s*MEDIA_HELPER_NAME\s*\]\s*=\s*_media_helper_source\(\)", body), (
        "run_script no longer adds the ck_media helper to the upload set — every generated "
        "script would die on `import ck_media` on the testbox")


def test_the_helper_read_fails_loudly_if_the_path_is_wrong(monkeypatch):
    """A silent miss would ship runs with no helper; every script would die on import."""
    monkeypatch.setattr(pc, "_MEDIA_HELPER_SRC", Path("/nonexistent/pt_media.py"))
    with pytest.raises(RuntimeError, match="media helper not found"):
        pc._media_helper_source()


def test_the_shipped_helper_is_importable_on_its_own():
    """It executes on the testbox with no repo on the path, so it must not import siblings."""
    src = (REPO / "ask-ck" / "tools" / "pt_media.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = {n.module.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.ImportFrom) and n.module}
    imported |= {a.name.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.Import) for a in n.names}
    assert imported <= {"re", "typing", "__future__"}, f"unexpected imports: {imported}"


# ----------------------------------------------------------------------- 3. ENFORCED


def test_a_conformant_script_raises_no_media_errors():
    bad = [e for e in lint_errors(CONFORMANT)
           if "init_portlink" in e or "never calls" in e]
    assert bad == [], bad


def test_lint_REJECTS_a_direct_init_portlink_that_bypasses_the_helper():
    mut = CONFORMANT + ("        (dut.portB, dut.portC) = "
                        "setup.init_portlink(dut, dut, type1='port')\n")
    hits = [e for e in lint_errors(mut) if "skips the run-time MEDIA assertion" in e]
    assert hits, lint_errors(mut)


def test_lint_REJECTS_reading_a_port_attribute_with_no_binding_at_all():
    mut = ("class TestSet(ATTestSet.TestSet):\n"
           "    def init(self, setup):\n"
           "        dut = setup.init_swi('swi_a')\n"
           "        self.dut = dut\n"
           "    def configure(self):\n"
           "        p = self.dut.portA\n")
    hits = [e for e in lint_errors(mut) if "never calls" in e]
    assert hits, lint_errors(mut)


def test_the_helpers_own_init_portlink_call_is_not_flagged():
    """The LEGACY helper's own call (test-9000.33234.py) stays sanctioned. Flagging it would
    fail every saved script — the check is scoped to the helper's line range."""
    assert not [e for e in lint_errors(CONFORMANT)
                if "skips the run-time MEDIA assertion" in e]


def test_lint_REJECTS_a_unit_binding_its_own_device():
    """The T33234 setup-unit failure: a unit calling `setup.init_swi()` invents a binding the
    frame did not make. Binding is the frame's job; units reach `self.testSet.<name>`."""
    sk = render()
    mut = sk.replace("        self.log('STEP 1",
                     "        swi_b = self.testSet.setup.init_swi('swi_b')\n        self.log('STEP 1", 1)
    hits = [e for e in lint_errors(mut) if "outside `TestSet.init()`" in e]
    assert hits and "init_swi" in hits[0], lint_errors(mut)


def test_the_frames_own_init_swi_calls_are_not_flagged():
    assert not [e for e in lint_errors(render()) if "outside `TestSet.init()`" in e]


def test_a_commented_port_attribute_does_not_trip_the_no_binding_check():
    mut = ("class TestSet(ATTestSet.TestSet):\n"
           "    def init(self, setup):\n"
           "        dut = setup.init_swi('swi_a')\n"
           "        # p = dut.portA  (documented, not executed)\n")
    assert not [e for e in lint_errors(mut) if "never calls" in e]


# ------------------------------------------------- 4. MINIMALITY: don't bind what you don't use

# Exactly the T33235 shape: three device names in the selected fragments' vocabulary.
FRAGS3 = [{"code": "self.dut.cmd('a')\nself.dutA.cmd('b')\nself.linkP.cmd('c')\n"}]


def render3(seq=SEQ_LINKED):
    return pc._render_skeleton("AWPTCM-T1", "x", seq, [], FRAGS3, "verify speeds")


def init_body(code):
    return re.search(r"def init\(self, setup\):.*?\n    def configure", code, re.S).group(0)


def test_only_the_dut_and_one_partner_are_bound():
    """T33235 bound 4 devices and used 1. Each spurious binding becomes a topology demand a
    bench must satisfy for nothing, which is what made that script un-runnable."""
    body = init_body(render3())
    assert body.count("setup.init_swi(") == 1, "only the DUT should be looked up directly"
    # ART shape (2026-09-07): the neighbour is `peer`, resolved from the far end of the link;
    # the positional second name (`dutA` here) is no longer bound when a link exists.
    assert "self.dut = dut" in body and "self.peer = peer" in body
    assert "self.dutA = dutA" not in body
    assert "self.linkP" not in body


def test_the_dropped_devices_are_named_in_a_comment_not_silently_discarded():
    body = init_body(render3())
    assert "# NOT BOUND: linkP." in body
    assert "link role" in body, "the comment must say how to legitimately get another"


def test_the_partner_is_the_far_end_of_the_bound_link():
    """One link => exactly one partner, so the partner needs no separate lookup — which is
    what makes over-binding structurally impossible rather than merely discouraged."""
    body = init_body(render3())
    # ART shape (2026-09-07): DUT-side `portPeer`, neighbour-side `peer.portDut`, and the
    # neighbour handle is `peer` — never `dut`, which ART reserves for the DUT's own stack.
    assert re.search(r"\(dut\.portPeer, peer_port, peer\) = self\._ck_bind_link\(", body)
    assert "peer.portDut = peer_port" in body
    assert "ck_far_port" not in body


def test_without_a_link_the_partner_is_still_capped_at_one():
    """A console-only partner has no link role to resolve from, so it is bound positionally —
    but the cap still applies."""
    # No link vocabulary at all: "speed" would imply a negotiating partner (a peer LINK), so
    # the console-only shape needs a step that names neither side of a cable.
    body = init_body(render3([{"n": 1, "action": "show version",
                               "verify": "the build string is reported", "kind": "verify"}]))
    assert "_ck_bind_link(" not in body
    assert body.count("setup.init_swi(") == 2      # DUT + one console-only partner
    assert "self.linkP" not in body
    assert "# NOT BOUND: linkP." in body


def test_lint_REJECTS_a_body_using_a_dropped_device():
    """The safety net that makes dropping safe: `self.linkP.cmd(...)` is valid Python and
    compiles, so without this the run dies with AttributeError mid-bench-slot."""
    sk = render3()
    mut = sk.replace("        self.log('STEP 1",
                     "        self.testSet.linkP.cmd('show version')\n        self.log('STEP 1", 1)
    hits = [e for e in lint_errors(mut) if "never binds" in e]
    assert hits and "linkP" in hits[0], lint_errors(mut)


def test_lint_REJECTS_the_self_dev_cmd_shape_too():
    sk = render3()
    mut = sk.replace("    def configure(self):\n",
                     "    def configure(self):\n        self.swiSrc.cmd('x')\n", 1)
    hits = [e for e in lint_errors(mut) if "never binds" in e]
    assert hits and "swiSrc" in hits[0], lint_errors(mut)


def test_the_generated_frame_has_no_unbound_device_errors():
    """No false positives on what generation actually emits — otherwise every case blocks."""
    assert [e for e in lint_errors(render3()) if "never binds" in e] == []


def test_the_real_rendered_skeleton_passes_its_own_media_lint():
    """End to end: what generation actually emits must satisfy the rule generation enforces.
    A frame that fails its own lint would block every case."""
    bad = [e for e in lint_errors(render())
           if "MEDIA assertion" in e or "never calls" in e]
    assert bad == [], bad


def test_lint_ACCEPTS_a_value_one_case_publishes_on_the_TestSet_for_later_cases():
    """AWPTCM-T33235 (2026-09-24): the review asks a case to publish a result for a later case
    (`self.testSet.speedS = ...`). That is a binding, not a device; the lint used to reject the
    very fix the review asked for."""
    sk = render3()
    mut = sk.replace("        self.log('STEP 1",
                     "        self.testSet.speedS = '100'\n        speed = self.testSet.speedS\n"
                     "        self.log('STEP 1", 1)
    assert mut != sk
    assert [e for e in lint_errors(mut) if "never binds" in e] == [], lint_errors(mut)
    # ...and a value nothing publishes is still an unbound read.
    read_only = sk.replace("        self.log('STEP 1",
                           "        speed = self.testSet.speedS\n        self.log('STEP 1", 1)
    hits = [e for e in lint_errors(read_only) if "never binds" in e]
    assert hits and "speedS" in hits[0], lint_errors(read_only)

"""The frame binds a ROLE SET — tb / copper / fibre / cusfp — by FRAMEWORK DISCOVERY (2026-09-21).

WHY. Until 2026-09-21 the frame read `[misc] ck_link_<role>` / `ck_role_dut` from the bench
file to find its links. Terrence's ruling: "I dont want the [misc] section to be callable as a
workaround for not using the existing framework commands. We have a suite of 'show' commands
that identify whatever we need to, the information shouldnt require pre-loading variables to
know it." Verified against the corpus: `swi_a`/`swi_b`/`stk_a` ARE the framework's portable
slots (297/168/192 lookups, a role-named key 0 times); `get_all_port_links()` already returns
every cable with its far device; `show interface status` / `show system pluggable` already say
what is in a port. So the frame binds the DUT as `swi_a` (its stack when in one), discovers
its links through the framework, classifies each by the media the DUT reports, and hands one
link per role to the case. Nothing is pre-declared.

Pinned here: detection from wording AND from slice-C claims; the four-role frame renders four
bind calls with the fixed handles, compiles, reads back through `_skeleton_bound_ports` /
`_skeleton_bound_devices`; pluggable roles are optional with flags; far ports are role-specific
(two pluggables often land on ONE partner switch); the frame compiles for every role subset;
the discovery helper asks the device and never a file; the unit prompt names the pluggable
handles and the UNSUPPORTED idiom. Offline: real module, no LLM, no hardware.
"""
import ast
import itertools
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main" / "CK_server"))
sys.path.insert(0, str(_REPO / "ask-ck" / "tools"))

from llm import render_prompt  # noqa: E402
from routers import pytest_create as pc  # noqa: E402

pytest.importorskip("models")

TEMPLATE = _REPO / "ask-ck" / "CK-main" / "CK_server" / "templates" / "pt_script_template.py.jinja"

STEP = {
    "tb": {"action": "capture LLDPDUs with tcpdump on the testbox", "verify": "frames received"},
    "copper": {"action": "force polarity mdix on the copper test port; the partner switch forces mdi "
                         "over the crossover cable", "verify": "the status row does not read connected"},
    # No copper vocabulary here on purpose: a fibre step whose verify mentions `polarity`
    # (T33234 step 18, "no polarity role is presented") legitimately ALSO binds copper.
    "fibre": {"action": "insert the 1000BASE-SX fibre module and bring the link up",
              "verify": "the link comes up at 1000 full"},
    "cusfp": {"action": "insert a copper SFP (1000BASE-T module) into the SFP cage",
              "verify": "link connected"},
}


def seq(*roles):
    return [dict(STEP[r], n=i + 1, kind="verify") for i, r in enumerate(roles)]


def render(s):
    return pc._render_skeleton("AWPTCM-T1", "t", s, [], [], "", None)


def init_body(code):
    return re.search(r"def init\(self, setup\):.*?\n    def configure", code, re.S).group(0)


def roles_of(d):
    return {k for k in pc.LINK_ROLES if d[k]}


# --- detection --------------------------------------------------------------------------

def test_each_wording_binds_its_own_role():
    assert roles_of(pc._detect_links(seq("tb"), [])) == {"tb"}
    assert roles_of(pc._detect_links(seq("copper"), [])) == {"copper"}
    assert roles_of(pc._detect_links(seq("fibre"), [])) == {"fibre"}
    assert roles_of(pc._detect_links(seq("cusfp"), [])) == {"cusfp"}


def test_all_four_at_once_the_t33234_shape():
    assert roles_of(pc._detect_links(seq("tb", "copper", "fibre", "cusfp"), [])) == \
        {"tb", "copper", "fibre", "cusfp"}


def test_a_fibre_only_case_does_not_also_bind_copper():
    d = pc._detect_links([{"n": 1, "action": "verify optical fibre speed negotiation with the partner",
                           "verify": "link up", "kind": "verify"}], [])
    assert roles_of(d) == {"fibre"} and d["peer"] is True


def test_a_claim_saying_fibre_binds_fibre_without_any_fibre_wording():
    s = [{"n": 1, "action": "bring the link up with the partner", "verify": "link up",
          "kind": "verify", "claim": {"cable": "fibre", "dut": "", "partner": "", "expect": ""}}]
    assert roles_of(pc._detect_links(s, [])) == {"fibre"}


def test_a_crossover_claim_keeps_the_copper_link_next_to_a_fibre_step():
    s = seq("fibre") + [{"n": 2, "action": "bring the link up with the partner", "verify": "connected",
                         "kind": "verify", "claim": {"cable": "crossover"}}]
    assert roles_of(pc._detect_links(s, [])) == {"fibre", "copper"}


# --- the frame's init(): four blocks, fixed handles -------------------------------------

def test_four_roles_render_four_bind_calls_with_the_fixed_handles():
    body = init_body(render(seq("tb", "copper", "fibre", "cusfp")))
    assert "(dut.portA, tb.ethA, _tb) = self._ck_bind_link(setup, dut, 'tb')" in body
    assert "(dut.portPeer, peer_port, peer) = self._ck_bind_link(setup, dut, 'copper')" in body
    assert "peer.portDut = peer_port" in body
    assert "(dut.portFibre, fibre_port, fibre_peer) = self._ck_bind_link(" in body
    assert "fibre_peer.portFibre = fibre_port" in body
    assert "(dut.portCuSfp, cusfp_port, cusfp_peer) = self._ck_bind_link(" in body
    assert "cusfp_peer.portCuSfp = cusfp_port" in body
    assert body.count("self._ck_bind_link(") == 4


def test_nothing_is_read_from_misc_and_nothing_is_pre_declared():
    sk = render(seq("tb", "copper", "fibre", "cusfp"))
    for forbidden in ("get_all_misc", "ck_link", "ck_role_dut", "ck_profile", "init_portlink"):
        assert forbidden not in sk, forbidden


def test_the_dut_is_swi_a_or_its_stack():
    body = init_body(render(seq("copper")))
    assert "dut = setup.init_swi('swi_a')" in body
    assert "_stk = dut.get_stack()" in body
    # ART's shape (2026-09-23): the stack is bound ALONGSIDE, never over, the swi_a handle.
    assert "dut_stack = setup.init_stk(_stk.name) if _stk is not None else None" in body
    assert "dut = setup.init_stk(" not in body


def test_pluggable_roles_are_optional_and_core_roles_are_not():
    body = init_body(render(seq("tb", "copper", "fibre", "cusfp")))
    assert "self._ck_bind_link(\n            setup, dut, 'fibre', optional=True)" in body
    assert "self._ck_bind_link(\n            setup, dut, 'cusfp', optional=True)" in body
    assert "self.fibre_supported = fibre_peer is not None" in body
    assert "self.cusfp_supported = cusfp_peer is not None" in body
    assert "self._ck_bind_link(setup, dut, 'tb')" in body          # no optional=
    assert "self._ck_bind_link(setup, dut, 'copper')" in body


def test_pluggables_are_taken_before_copper_so_copper_cannot_consume_a_copper_sfp():
    body = init_body(render(seq("tb", "copper", "fibre", "cusfp")))
    assert body.index("'cusfp'") < body.index("'fibre'") < body.index("'copper'")


def test_far_ports_are_role_specific_because_pluggables_share_a_partner():
    """On tb470 every partner link lands on ONE switch (swi_e). A shared `<peer>.portDut` for
    the fibre and copper-SFP links would be overwritten by the next binding — so each role
    homes its far port under its own name, as the hand-repaired T33234 did."""
    body = init_body(render(seq("copper", "fibre", "cusfp")))
    far = re.findall(r"^\s+(\w+)\.(port\w+) = (\w+)$", body, re.M)
    assert far == [("cusfp_peer", "portCuSfp", "cusfp_port"),
                   ("fibre_peer", "portFibre", "fibre_port"),
                   ("peer", "portDut", "peer_port")], far


def test_the_frame_reads_back_all_four_links_and_devices():
    sk = render(seq("tb", "copper", "fibre", "cusfp"))
    assert pc._skeleton_bound_ports(sk) == [
        {"role": "tb", "near": "dut.portA", "far": "tb.ethA"},
        {"role": "cusfp", "near": "dut.portCuSfp", "far": "cusfp_peer.portCuSfp"},
        {"role": "fibre", "near": "dut.portFibre", "far": "fibre_peer.portFibre"},
        {"role": "copper", "near": "dut.portPeer", "far": "peer.portDut"},
    ]
    assert pc._skeleton_bound_devices(sk, "dut") == ["dut", "tb", "dut_stack", "cusfp_peer", "fibre_peer", "peer"]


def test_the_shortcut_block_carries_every_bound_handle():
    sk = render(seq("tb", "copper", "fibre", "cusfp"))
    main = re.search(r"    def main\(self\):.*?self\.log\(", sk, re.S).group(0)
    for line in ("ethA = tb.ethA", "portA = dut.portA", "peer = self.testSet.peer",
                 "portPeer = dut.portPeer", "portDut = peer.portDut",
                 "fibre_peer = self.testSet.fibre_peer", "portFibre = dut.portFibre",
                 "cusfp_peer = self.testSet.cusfp_peer", "portCuSfp = dut.portCuSfp"):
        assert line in main, line


# --- discovery: the device is asked, never a file ----------------------------------------

def discover_src(sk):
    return re.search(r"def _ck_discover.*?\n    def _ck_bind_link", sk, re.S).group(0)


def test_discovery_walks_the_frameworks_port_links_and_asks_the_dut():
    d = discover_src(render(seq("copper")))
    assert "unit.get_all_port_links().items()" in d          # the STACK's links when stacked
    assert "isinstance(far, ATTestBox.TestBox)" in d              # the testbox is the TestBox end
    assert "unit.all_members()" in d and "if far in members:" in d  # a stack member is not a partner
    assert "dut.cmd('show system pluggable')" in d
    assert "dut.cmd('show interface %s status' % near.name)" in d
    assert "ck_media.classify(ck_media.media_type(status, near.name))" in d


def test_discovery_sorts_twisted_pair_into_copper_or_cusfp_by_the_pluggable_table():
    d = discover_src(render(seq("copper")))
    assert "bucket = 'cusfp' if ck_media.is_pluggable(near.name, in_cage) else 'copper'" in d


def test_an_empty_cage_is_absent_and_never_a_role():
    """Terrence 2026-09-21: cages themselves aren't 'fibre' or 'copper' because they're empty."""
    d = discover_src(render(seq("fibre")))
    assert "elif kind == ck_media.ABSENT:\n                    bucket = 'absent'" in d
    helper = re.search(r"def _ck_bind_link.*?\n    def init", render(seq("fibre")), re.S).group(0)
    assert "'absent'" not in helper, "no role may draw from the empty-cage bucket"


def test_a_copper_role_falls_back_to_a_copper_sfp_but_never_the_reverse():
    helper = re.search(r"def _ck_bind_link.*?\n    def init", render(seq("copper")), re.S).group(0)
    assert "'copper': ('copper', 'cusfp')" in helper
    assert "'cusfp': ('cusfp',)" in helper and "'fibre': ('fibre',)" in helper


def test_a_partner_switch_is_initialised_once_and_the_testbox_never():
    helper = re.search(r"def _ck_bind_link.*?\n    def init", render(seq("copper")), re.S).group(0)
    assert "if far.name not in self._ck_far:" in helper
    assert "setup.init_swi(far.name)" in helper and "setup.init_stk(far.name)" in helper
    assert "if isinstance(far, ATTestBox.TestBox):" in helper


def test_discovery_is_skipped_when_the_case_needs_no_link():
    sk = render([{"n": 1, "action": "show version", "verify": "build string", "kind": "verify"}])
    assert "_ck_discover" not in sk and "ATTestBox" not in sk


def test_the_deferred_media_helper_ships_only_with_a_pluggable_role():
    assert "def assert_role_media_now(testCase, dut, port, role):" in render(seq("fibre"))
    assert "def assert_role_media_now(testCase, dut, port, role):" in render(seq("cusfp"))
    assert "assert_role_media_now" not in render(seq("tb", "copper"))


@pytest.mark.parametrize("roles", [
    r for n in range(0, 5) for r in itertools.combinations(("tb", "copper", "fibre", "cusfp"), n)])
def test_the_frame_compiles_for_every_role_subset(roles):
    s = seq(*roles) if roles else [{"n": 1, "action": "show version", "verify": "build string",
                                    "kind": "verify"}]
    sk = render(s)
    compile(sk, "frame.py", "exec")
    assert roles_of(pc._detect_links(s, [])) == set(roles)
    body = init_body(sk)
    assert body.count("self._ck_bind_link(") == len(roles)


def test_the_rendered_frame_passes_its_own_lint():
    import models
    sk = render(seq("tb", "copper", "fibre", "cusfp"))
    sess = models.PtSession(key="AWPTCM-T00000", group="", payload={}, traceability="",
                            step2={}, step3={}, step4={}, step5={},
                            step6={"files": {"test": {"name": "t.py", "code": sk}}})
    errs = pc._lint_generated(sess)["errors"]
    frame_errs = [e for e in errs if "contract:" not in e]
    assert frame_errs == [], frame_errs


# --- the unit prompt ----------------------------------------------------------------------

def test_the_unit_prompt_explains_the_pluggable_handles_and_the_unsupported_idiom():
    sk = render(seq("tb", "copper", "fibre", "cusfp"))
    ctx = {
        "case_key": "K", "case_title": "T", "mode": "testcase", "tc_n": 3, "source_n": 3,
        "step": {"n": 3, "action": "insert the module", "verify": "link connected"},
        "setup_steps": [], "blank_block": "class TestCase_3:\n    pass",
        "fragments": [], "shared_fragments": [], "shared_tags_for_unit": [], "shared_cli_reference": "",
        "devices": pc._skeleton_bound_devices(sk, "dut"),
        "bound_devices": pc._skeleton_bound_devices(sk, "dut"),
        "bound_ports": pc._skeleton_bound_ports(sk),
        "framework_surface": {}, "cli_reference": "", "device_note": "", "py2_flagged": False,
        "rules_cli_reference": False, "split_marker": pc._PT_PROMPT_SPLIT, "model_name": "m",
        "gen_date": "2026-09-21", "library": None, "library_tags_for_unit": [],
    }
    out = render_prompt("pt_generate_step.jinja", ctx)
    assert "self.testSet.fibre_supported" in out and "self.testSet.cusfp_supported" in out
    assert "UNSUPPORTED" in out and "self.supported = False" in out
    assert "`dut.portFibre` <-> `fibre_peer.portFibre`" in out
    assert "`dut.portCuSfp` <-> `cusfp_peer.portCuSfp`" in out
    assert "assert_role_media_now" in out
    assert "role contract" not in out and "ck_link" not in out

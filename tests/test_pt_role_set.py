"""The frame binds a ROLE SET — tb / copper / fibre / cusfp — not two booleans (2026-09-21).

WHY. Until now `_detect_links` returned `{tb, peer}` and the frame bound at most two links with
copper and fibre sharing ONE handle set. AWPTCM-T33234 needs four at once, so its setup UNIT
invented the missing bindings and bound the copper test port from the testbox role: 4 of the
first review's 6 highs (memory `frame-binds-two-roles-only`). Terrence's decisions 2026-09-21:
`cusfp` is a first-class role; pluggable roles (fibre, cusfp) are OPTIONAL-with-UNSUPPORTED
while tb/copper abort; handles are portFibre / fibre_peer.portDut and portCuSfp /
cusfp_peer.portDut, copper keeps peer / portPeer / portDut.

Pinned here: detection from wording AND from slice-C claims; a four-role frame renders four
bind calls with the fixed handles, compiles, reads back through `_skeleton_bound_ports` /
`_skeleton_bound_devices`; pluggable roles are try/except-bound with flags and deferred media;
one partner is bound once for two links; the frame compiles for every role subset; the unit
prompt names the pluggable handles and the UNSUPPORTED idiom. Offline: real module, no LLM.
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

from routers import pytest_create as pc  # noqa: E402

pytest.importorskip("models")

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
    d = pc._detect_links([{"n": 1, "action": "bring the link up against the partner", "verify": "up",
                           "kind": "verify", "claim": {"cable": "fibre", "expect": "up"}}], [])
    assert d["fibre"] is True


def test_a_crossover_claim_keeps_the_copper_link_next_to_a_fibre_step():
    s = [{"n": 1, "action": "bring the link up against the partner", "verify": "up", "kind": "verify",
          "claim": {"cable": "crossover", "dut": "mdix", "partner": "mdi", "expect": "up"}},
         dict(STEP["fibre"], n=2, kind="verify")]
    assert roles_of(pc._detect_links(s, [])) == {"copper", "fibre"}


def test_copper_and_fibre_together_bind_both_neighbour_links():
    d = pc._detect_links(seq("copper", "fibre"), [])
    assert roles_of(d) == {"copper", "fibre"} and d["peer"] is True


# --- the frame ----------------------------------------------------------------------------

FOUR = seq("tb", "copper", "fibre", "cusfp")


def test_four_roles_render_four_bind_calls_with_the_fixed_handles():
    body = init_body(render(FOUR))
    assert "(dut.portA, tb.ethA, _tb) = self._ck_bind_link(setup, dut, misc, 'tb')" in body
    assert "(dut.portPeer, peer_port, peer) = self._ck_bind_link(\n            setup, dut, misc, 'copper')" in body
    assert "(dut.portFibre, fibre_port, fibre_peer) = self._ck_bind_link(\n" \
           "                setup, dut, misc, 'fibre', assert_media=False)" in body
    assert "(dut.portCuSfp, cusfp_port, cusfp_peer) = self._ck_bind_link(\n" \
           "                setup, dut, misc, 'cusfp', assert_media=False)" in body
    assert "fibre_peer.portDut = fibre_port" in body and "cusfp_peer.portDut = cusfp_port" in body


def test_pluggable_roles_are_optional_and_core_roles_are_not():
    body = init_body(render(FOUR))
    for role in ("fibre", "cusfp"):
        assert f"self.{role}_supported = True" in body
        assert f"self.{role}_supported = False" in body
        assert f"self.{role}_peer = None" in body
    assert body.count("except RuntimeError as exc:") == 2, "exactly the two pluggable roles are guarded"
    tb_and_copper = body.split("self.fibre_supported = True")[0]
    assert "try:" not in tb_and_copper, "tb and copper must abort the suite, not degrade"


def test_the_frame_reads_back_all_four_links_and_devices():
    sk = render(FOUR)
    assert pc._skeleton_bound_ports(sk) == [
        {"role": "tb", "near": "dut.portA", "far": "tb.ethA"},
        {"role": "copper", "near": "dut.portPeer", "far": "peer.portDut"},
        {"role": "fibre", "near": "dut.portFibre", "far": "fibre_peer.portDut"},
        {"role": "cusfp", "near": "dut.portCuSfp", "far": "cusfp_peer.portDut"},
    ]
    assert pc._skeleton_bound_devices(sk, "dut") == ["dut", "tb", "peer", "fibre_peer", "cusfp_peer"]


def test_the_shortcut_block_carries_every_bound_handle():
    sk = render(FOUR)
    tree = ast.parse(sk)
    case = next(c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "TestCase_1")
    main = ast.get_source_segment(sk, next(f for f in case.body if isinstance(f, ast.FunctionDef) and f.name == "main"))
    for want in ("portA = dut.portA", "portPeer = dut.portPeer", "portDut = peer.portDut",
                 "fibre_peer = self.testSet.fibre_peer", "portFibre = dut.portFibre",
                 "cusfp_peer = self.testSet.cusfp_peer", "portCuSfp = dut.portCuSfp"):
        assert want in main, want


def test_the_helper_defers_media_and_binds_one_partner_once():
    sk = render(FOUR)
    helper = re.search(r"def _ck_bind_link.*?\n    def init", sk, re.S).group(0)
    assert "if not assert_media:" in helper and "DEFERRED" in helper
    assert "_ck_far_devices" in helper and helper.count("setup.init_swi(far_key)") == 1
    assert "def assert_role_media_now(testCase, dut, port, role):" in sk


def test_no_pluggable_role_means_no_deferred_helper_in_the_file():
    sk = render(seq("tb", "copper"))
    assert "def assert_role_media_now" not in sk
    assert "fibre_supported" not in sk and "cusfp_supported" not in sk


@pytest.mark.parametrize("roles", [c for n in range(0, 5) for c in itertools.combinations(pc.LINK_ROLES, n)])
def test_the_frame_compiles_for_every_role_subset(roles):
    links = {r: (r in roles) for r in pc.LINK_ROLES}
    links["peer"] = any(links[r] for r in ("copper", "fibre", "cusfp"))
    tpl = pc._skeleton_env.get_template("pt_script_template.py.jinja")
    code = tpl.render(case_key="AWPTCM-T1", case_title="t", extra_imports=[], setup_steps=[],
                      steps=[{"n": 1, "action": "a", "verify": "v", "kind": "verify"}],
                      switches=["dut"], stacks=[], needs_portlink=links["peer"], setup_keys=["swi_a"],
                      links=links, lib_stem="", objective_lines=[])
    compile(code, "frame.py", "exec")
    assert sorted(l["role"] for l in pc._skeleton_bound_ports(code)) == sorted(roles)


# --- the prompt ---------------------------------------------------------------------------

def test_the_unit_prompt_explains_the_pluggable_handles_and_the_unsupported_idiom():
    from llm import render_prompt
    tpl = pc._skeleton_env.get_template("pt_script_template.py.jinja")  # noqa: F841 (env is loaded)
    sk = render(FOUR)
    ctx = {"devices": pc._skeleton_bound_devices(sk, "dut"), "bound_ports": pc._skeleton_bound_ports(sk)}
    step_src = (Path(pc.__file__).resolve().parents[1] / "templates" / "prompts" / "pt_generate_step.jinja").read_text()
    seg = step_src[step_src.index("Devices, reached from a TestCase"):step_src.index("Every method in the block you fill OPENS")]
    from jinja2 import Environment
    out = Environment().from_string(seg).render(**ctx)
    assert "self.testSet.fibre_supported" in out and "self.testSet.cusfp_supported" in out
    assert "assert_role_media_now(self, <dut>, portFibre, 'fibre')" in out
    assert "UNSUPPORTED" in out
    rules = (Path(pc.__file__).resolve().parents[1] / "templates" / "prompts" / "pt_fill_rules.jinja").read_text()
    assert "self.supported = False" in rules and "portCuSfp" in rules

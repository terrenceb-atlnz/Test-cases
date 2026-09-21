"""Regression tests for the pre-flight topology check (`ask-ck/tools/pt_preflight.py`).

The check exists because `Setup.init_portlink()` fails SILENTLY — it returns `(None, None)`
when the bench declares no matching link, and generated scripts unpack that straight into
port attributes. A run then fails in a way that reads as a script defect when the real cause
is bench cabling.

The failure mode these tests guard against is the check being uselessly pessimistic: a tool
that reported "unsatisfiable" unconditionally would have produced exactly the right answer
for the three real Port (7) scripts on tb470 the morning of 2026-07-30 (0/3 runnable) and
still be worth nothing. So every "cannot" assertion below is paired with a mutation that
makes the same demand satisfiable, and the verdict must flip. That bench then gained two
inter-switch links and went to 2/3, which both fixtures below now pin.

Pure unit tests — no DB, no network, no hardware, no LLM.
"""
import re
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ask-ck" / "tools"))

pt_preflight = pytest.importorskip("pt_preflight")

Bench = pt_preflight.Bench
parse_script = pt_preflight.parse_script
check = pt_preflight.check


# --------------------------------------------------------------------------- fixtures

# SYNTHETIC bench: a two-member stack, two link partners, and exactly ONE declared
# portlink (testbox -> DUT). This is NOT tb470 — it kept that shape only until the
# 2026-07-30 de-stacking. It is retained deliberately, because the tool must still handle
# stack semantics (member expansion, the stackport-is-not-a-data-path note) on any bench
# that has a stack. For a real (but FROZEN) tb470 shape see TB470_2026_07_30 below.
BENCH_STACKED = """
[power]
pwr_c = (pdu, 10.36.150.14, 8)
pwr_d = (pdu, 10.36.150.14, 6)

[switch]
swi_a = /dev/u4
swi_b = /dev/u5
swi_c = /dev/u1
swi_d = /dev/u0

[stack]
stk_a = swi_a, swi_b

[configured_stackport]

[powerlink]
swi_c = pwr_c
swi_d = pwr_d

[portlink]
tb-swi_a = eth3-port1.0.23
"""

# The LIVE tb470 bench as at 2026-07-30 afternoon, after the two IE520s were de-stacked
# (`stack 2 renumber 1` on u5 + stackport/virtual-mac cleared, both rebooted). No [stack]
# any more: swi_a and swi_b are two independent standalone switches joined by two verified
# data links — copper port1.0.1 and fiber port1.0.7, both negotiated 1000/full.
# tb470 as it stood on 2026-07-30 afternoon -- de-stacked IE520 pair, copper + fibre links
# between them, no PDU entry for either IE520. FROZEN ON PURPOSE: this is the input that
# makes the two tests below meaningful, not a description of the bench.
#
# !! THIS IS NOT THE CURRENT BENCH and must not be read as it. The two IE520s have been ONE
#    STACK since 2026-08-18, both are on the PDU, the swi_a<->swi_b links are gone, and
#    swi_a<->swi_c IS now cabled (as an LACP LAG). Current state:
#    ~/claude/IE520-testing/bench-setup/bench-state.md
#    Changing this fixture to match the bench would destroy the 0/3 -> 2/3 contrast it exists
#    to pin. Add a NEW fixture instead if a current-bench case is ever wanted.
TB470_2026_07_30 = """
[power]
pwr_c = (pdu, 10.36.150.14, 8)
pwr_d = (pdu, 10.36.150.14, 6)

[switch]
swi_a = /dev/u4
swi_b = /dev/u5
swi_c = /dev/u1
swi_d = /dev/u0

[configured_stackport]

[powerlink]
swi_c = pwr_c
swi_d = pwr_d

[portlink]
tb-swi_a = eth3-port1.0.23
swi_a-swi_b = port1.0.1-port1.0.1, port1.0.7-port1.0.7
"""


def script(body: str) -> str:
    """A minimal skeleton-shaped script; `body` goes inside init()."""
    lines = textwrap.dedent(body).strip().splitlines()
    return (
        "class TestSet:\n"
        "    def init(self, setup):\n"
        + "".join(f"        {line}\n" for line in lines)
    )


def report(body: str, bench_text: str = BENCH_STACKED) -> dict:
    return check(parse_script(script(body)), Bench.from_text(bench_text))


def kinds(rep: dict):
    return [p["kind"] for p in rep["problems"]]


# ----------------------------------------------------------------- the bench parser


def test_bench_parses_devices_stack_and_links():
    b = Bench.from_text(BENCH_STACKED)
    assert b.switches == {"swi_a": "/dev/u4", "swi_b": "/dev/u5",
                          "swi_c": "/dev/u1", "swi_d": "/dev/u0"}
    assert b.stacks == {"stk_a": ["swi_a", "swi_b"]}
    assert len(b.links) == 1
    assert (b.links[0].devA, b.links[0].portA) == ("tb", "eth3")
    assert (b.links[0].devB, b.links[0].portB) == ("swi_a", "port1.0.23")
    assert b.powerlinks == {"swi_c": ["pwr_c"], "swi_d": ["pwr_d"]}


def test_comma_separated_portlinks_become_separate_consumable_links():
    b = Bench.from_text(
        "[switch]\nswi_a = /dev/u4\nswi_c = /dev/u1\n"
        "[portlink]\nswi_a-swi_c = port1.0.1-port1.0.1, port1.0.3-port1.0.2\n")
    assert len(b.links) == 2


def test_iface_type_reads_the_leading_alpha_run():
    assert pt_preflight.iface_type("port1.0.23") == "port"
    assert pt_preflight.iface_type("eth3") == "eth"
    assert pt_preflight.iface_type("") == ""


def test_malformed_portlink_is_warned_not_crashed():
    b = Bench.from_text("[switch]\nswi_a = /dev/u4\n[portlink]\nswi_a-swi_c = garbage\n")
    assert b.links == []
    assert any("not <portA>-<portB>" in w for w in b.warnings)


# --------------------------------------------------------- the core claim, and its mutation


def test_missing_inter_switch_link_is_reported():
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_c')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
    """)
    assert kinds(rep) == ["LINK"]
    assert not rep["runnable"]
    assert "SILENTLY" in rep["problems"][0]["consequence"]


def test_MUTATION_declaring_that_link_makes_it_runnable():
    """The paired mutation: same script, bench gains the link, verdict must flip."""
    bench = BENCH_STACKED.replace("tb-swi_a = eth3-port1.0.23",
                          "tb-swi_a = eth3-port1.0.23\nswi_a-swi_c = port1.0.1-port1.0.1")
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_c')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
    """, bench)
    assert rep["problems"] == []
    assert rep["runnable"]


def test_declared_link_is_consumed_so_a_second_demand_fails():
    """`init_portlink` looks up a NOT-YET-USED link, so one cable serves one call."""
    bench = BENCH_STACKED.replace("tb-swi_a = eth3-port1.0.23",
                          "swi_a-swi_c = port1.0.1-port1.0.1")
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_c')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
        (dut.portB, lp.portB) = setup.init_portlink(dut, lp, type1='port', type2='port')
    """, bench)
    assert rep["links_demanded"] == 2
    assert rep["links_unsatisfiable"] == 1


def test_MUTATION_two_declared_links_satisfy_two_demands():
    bench = BENCH_STACKED.replace(
        "tb-swi_a = eth3-port1.0.23",
        "swi_a-swi_c = port1.0.1-port1.0.1, port1.0.3-port1.0.2")
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_c')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
        (dut.portB, lp.portB) = setup.init_portlink(dut, lp, type1='port', type2='port')
    """, bench)
    assert rep["runnable"], rep["problems"]


def test_link_matches_in_either_orientation():
    """Declared `tb-swi_a`; the script asks init_portlink(dut, tb) — reversed, still a match."""
    rep = report("""
        tb = setup.init_tb()
        dut = setup.init_swi('swi_a')
        (dut.portTB, tb.ethA) = setup.init_portlink(dut, tb, type1='port')
    """)
    assert rep["runnable"], rep["problems"]


def test_interface_type_filter_is_enforced():
    """A link whose DUT end is an eth port cannot satisfy a demand for type1='port'."""
    bench = BENCH_STACKED.replace("tb-swi_a = eth3-port1.0.23", "swi_a-swi_c = eth1-eth1")
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_c')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
    """, bench)
    assert kinds(rep) == ["LINK"]


def test_MUTATION_empty_type_filter_matches_any_interface():
    bench = BENCH_STACKED.replace("tb-swi_a = eth3-port1.0.23", "swi_a-swi_c = eth1-eth1")
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_c')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp)
    """, bench)
    assert rep["runnable"], rep["problems"]


# ------------------------------------------------------------------------- stacks


def test_same_stack_members_get_the_stackport_note():
    """The trap this whole check was built for: two switches cabled into one stack still
    have no data path between them, and the report has to say so explicitly."""
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_b')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
    """)
    assert kinds(rep) == ["LINK"]
    assert "stackport cabling is NOT a data path" in rep["problems"][0]["detail"]
    assert "stk_a" in rep["problems"][0]["detail"]


def test_a_link_to_one_member_satisfies_a_demand_against_the_stack():
    """`init_portlink` expands a Stack and tries each member combination."""
    rep = report("""
        tb = setup.init_tb()
        stk = setup.init_stk('stk_a')
        (stk.portA, tb.ethA) = setup.init_portlink(stk, tb, type1='port')
    """)
    assert rep["runnable"], rep["problems"]


def test_device_bound_from_stack_is_annotated_with_its_stack():
    rep = report("dut = setup.init_swi('swi_a')")
    swi_a = next(d for d in rep["devices"] if d["role"] == "swi_a")
    assert "member of stk_a" in swi_a["detail"]


# -------------------------------------------------------------------------- power


def test_power_cycling_a_device_with_no_powerlink_is_reported():
    """The other real tb470 gap: neither IE520 is on the PDU, so the DUT stack cannot be
    power-cycled at all."""
    rep = report("""
        dut = setup.init_swi('swi_a')
        dut.powerCycle()
    """)
    assert kinds(rep) == ["POWER"]
    assert "CLI" in rep["problems"][0]["consequence"]


def test_MUTATION_power_cycling_a_device_that_has_an_outlet_is_fine():
    rep = report("""
        lp = setup.init_swi('swi_c')
        lp.powerCycle()
    """)
    assert rep["problems"] == []


def test_power_on_a_stack_needs_every_member_on_an_outlet():
    bench = BENCH_STACKED.replace("swi_c = pwr_c", "swi_a = pwr_c\nswi_c = pwr_c")
    rep = report("""
        stk = setup.init_stk('stk_a')
        stk.powerCycle()
    """, bench)
    # swi_a now has an outlet but swi_b still does not -> still un-runnable.
    assert kinds(rep) == ["POWER"]
    assert "swi_b" in rep["problems"][0]["detail"]


# ------------------------------------------------------------- resolution + robustness


def test_unknown_device_is_reported_as_a_device_problem():
    rep = report("dut = setup.init_swi('swi_zz')")
    assert kinds(rep) == ["DEVICE"]
    assert "swi_zz" in rep["problems"][0]["message"]


def test_a_device_problem_does_not_also_produce_a_bogus_link_problem():
    """One root cause, one finding — an undeclared device must not be double-reported."""
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_zz')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp)
    """)
    assert kinds(rep) == ["DEVICE"]


def test_demand_written_against_self_attribute_resolves():
    rep = report("""
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_b')
        self.dut = dut
        self.lp = lp
        (self.dut.portA, self.lp.portA) = setup.init_portlink(self.dut, self.lp, type1='port')
    """)
    assert kinds(rep) == ["LINK"]
    assert "swi_a" in rep["problems"][0]["role"]


def test_portlink_outside_init_is_still_checked():
    """A portlink bound in a TestCase body has happened before; it is still a demand."""
    text = (
        "class TestSet:\n"
        "    def init(self, setup):\n"
        "        self.dut = setup.init_swi('swi_a')\n"
        "        self.lp = setup.init_swi('swi_b')\n"
        "    def run(self, setup):\n"
        "        (self.dut.portA, self.lp.portA) = setup.init_portlink(self.dut, self.lp)\n"
    )
    rep = check(parse_script(text), Bench.from_text(BENCH_STACKED))
    assert kinds(rep) == ["LINK"]


def test_non_literal_role_warns_instead_of_crashing():
    rep = report("""
        name = 'swi_a'
        dut = setup.init_swi(name)
    """)
    assert any("non-literal role" in n for n in rep["notes"])


def test_unresolvable_device_argument_is_reported_not_ignored():
    rep = report("""
        dut = setup.init_swi('swi_a')
        (dut.portA, mystery.portA) = setup.init_portlink(dut, mystery)
    """)
    assert kinds(rep) == ["LINK"]
    assert "cannot resolve" in rep["problems"][0]["message"]


def test_clean_script_on_a_matching_bench_is_runnable():
    """The all-green path, so the suite proves the check can say yes."""
    rep = report("""
        tb = setup.init_tb()
        dut = setup.init_swi('swi_a')
        (dut.portTB, tb.ethA) = setup.init_portlink(dut, tb, type1='port')
    """)
    assert rep["runnable"] and rep["problems"] == []


# ------------------------------------------------------------------------ the real thing


# A generated TEST SCRIPT, as opposed to the `library` companion the generator writes
# beside it. Both land in generated/<Group>/, so an unfiltered rglob swept the library in
# too — and a library module legitimately binds no devices, which broke both tests below
# the first time a generation actually emitted one (2026-08-31, AWPTCM-T33351:
# 'library_802_1x_single_host.py: no devices detected', and the same file counted as
# trivially "runnable" because a script with no demands has nothing to fail).
#
# The discriminator is the skeleton's own shape, not the filename: every generated test
# script subclasses ATTestSet/ATTestCase, and a library never does. The library's name
# comes from the MODEL (_persist_generated_files validates it for safety, not for a
# prefix), so matching on 'library_' would be guessing at something nothing guarantees.
# This rule also keeps the hand-made .REVIEW.py in scope, which a sidecar-meta rule
# would silently drop.
_TESTSET_RX = re.compile(r"^class\s+\w+\s*\(\s*(?:ATTestSet|ATTestCase)\b", re.M)


def _is_test_script(path: Path) -> bool:
    return bool(_TESTSET_RX.search(path.read_text(encoding="utf-8", errors="replace")))


# generated/.meta/<Group>/<Name>/history/iter-N/ keeps a snapshot of every superseded
# iteration. Those are history, not the current script: asserting over them means a draft
# that was regenerated BECAUSE it was wrong reddens the gate forever, and _verdicts (keyed
# on p.name) silently collapses a snapshot and its live file into one entry. Latent since
# the first multi-iteration case; it only bites once a case is generated more than once.
_GENERATED = sorted(p for p in (REPO / "ask-ck" / "functions" / "pytest-creator" / "generated").rglob("*.py")
                    if ".meta" not in p.parts)
REAL_SCRIPTS = [p for p in _GENERATED if _is_test_script(p)]
# A filter that quietly matched nothing would turn every assertion below into a vacuous
# pass — exactly the failure mode test_every_generated_script_parses_and_is_checkable
# exists to prevent one layer down.
assert not _GENERATED or REAL_SCRIPTS, (
    "generated/ holds .py files but none subclass ATTestSet/ATTestCase — has the skeleton "
    f"changed shape? saw: {[p.name for p in _GENERATED]}")


@pytest.mark.skipif(not REAL_SCRIPTS, reason="no generated scripts in the tree")
def test_every_generated_script_parses_and_is_checkable():
    """Pins that the AST extraction actually understands the real skeleton's shape —
    a check that silently found zero demands would report everything as runnable."""
    for path in REAL_SCRIPTS:
        demands = parse_script(path.read_text(encoding="utf-8", errors="replace"), path)
        assert demands.roles, f"{path.name}: no devices detected"
        # A discovery-frame script (2026-09-21) demands ROLES, not named portlink pairs.
        assert demands.links or demands.role_links, f"{path.name}: no link demands detected"


# The three Port scripts as generated on 2026-07-30, reduced to the ONLY thing the preflight
# reads: their TestSet.init() bindings. Frozen here on 2026-09-21 because the live tree is a
# moving target — the 2026-09-16 clean-slate reset removed those files (recoverable from
# e35bbb2^), the ART rename made the next script `test-9000.<case>.py`, and every regeneration
# changes what a script demands. A pin that read the tree therefore reddened the gate for a
# week over a filename. The STORY these fixtures pin is the tool's: declaring the two verified
# swi_a<->swi_b data links took tb470 from 0/3 to 2/3 (`_verdicts` below).
FROZEN_2026_07_30 = {
    "Port_Auto_MDI_MDI_test.py": """
class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        tb = setup.init_tb()
        dut = setup.init_swi('swi_a')
        lp = setup.init_swi('swi_b')
        (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')
""",
    "Port_Auto_Negotiation_test.py": """
class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        tb = setup.init_tb()
        dut = setup.init_swi('swi_a')
        linkP = setup.init_swi('swi_b')
        dutA = setup.init_swi('swi_c')
        (dut.portTB, tb.ethA) = setup.init_portlink(dut, tb, type1='port')
        (dut.portB, linkP.portA) = setup.init_portlink(dut, linkP, type1='port', type2='port')
""",
    "3_Port_Fixed_port_test.py": """
class TestSet(ATTestSet.TestSet):
    def init(self, setup):
        tb = setup.init_tb()
        dut = setup.init_swi('swi_a')
        dutA = setup.init_swi('swi_b')
        linkP = setup.init_swi('swi_c')
        (dut.portA, linkP.portB) = setup.init_portlink(dut, linkP, type1='port', type2='port')
        (dut.portB, dutA.portA) = setup.init_portlink(dut, dutA, type1='port', type2='port')
""",
}


def _verdicts(bench_text: str, scripts: dict = FROZEN_2026_07_30) -> dict:
    """Per-script verdicts. A FRESH Bench per script — link consumption is per-run state,
    so one bench object would let script #1 use up script #2's cables."""
    return {
        name: check(parse_script(src), Bench.from_text(bench_text))["runnable"]
        for name, src in scripts.items()
    }


def test_real_scripts_on_the_live_bench():
    """Pins the tb470 outcome as at 2026-07-30 afternoon: declaring the two verified
    swi_a<->swi_b data links took that bench from 0/3 to 2/3.

    `3_Port_Fixed_port_test.py` is un-runnable against this fixture because it also wants
    swi_a<->swi_c (the AR4050S), which had no data cabling that day. That has SINCE been
    cabled, as an LACP LAG — so this no longer describes the live bench, and deliberately
    does not try to. The fixture is frozen; see the note above it."""
    v = _verdicts(TB470_2026_07_30)
    assert v.get("Port_Auto_MDI_MDI_test.py") is True, v
    assert v.get("Port_Auto_Negotiation_test.py") is True, v
    assert v.get("3_Port_Fixed_port_test.py") is False, v


def test_real_scripts_were_all_unrunnable_before_the_inter_switch_links():
    """The before-picture, kept as the contrast that gives the test above its meaning: with
    only the testbox->DUT portlink declared, every Port (7) script was un-runnable because
    each needs at least one switch<->switch data link."""
    assert not any(_verdicts(BENCH_STACKED).values()), _verdicts(BENCH_STACKED)


@pytest.mark.skipif(not REAL_SCRIPTS, reason="no generated scripts in the tree")
def test_every_current_script_gets_a_verdict_without_crashing():
    """The tree half, with NO pinned truth: whatever is in generated/ today must parse and
    come back with a boolean verdict and a problems list. What the verdict IS depends on the
    script and is not this test's business (see FROZEN_2026_07_30 for the pinned story)."""
    for p in REAL_SCRIPTS:
        rep = check(parse_script(p.read_text(encoding="utf-8", errors="replace"), p),
                    Bench.from_text(TB470_2026_07_30))
        assert isinstance(rep["runnable"], bool), p.name
        assert isinstance(rep["problems"], list), p.name


# ---------------------------------------------------- the discovery frame (2026-09-21): role demands

# The generated frame's init() as of 2026-09-21: the DUT is swi_a (its stack when in one), and
# links are ROLE demands the frame resolves at run time by discovery. Reduced to what the
# preflight reads. `fibre` is optional (a pluggable role).
DISCOVERY_FRAME = """
class TestSet(ATTestSet.TestSet):
    def _ck_discover(self, dut):
        return {}
    def _ck_bind_link(self, setup, dut, role, optional=False):
        return None, None, None
    def init(self, setup):
        tb = setup.init_tb()
        dut = setup.init_swi('swi_a')
        _stk = dut.get_stack()
        if _stk is not None:
            dut = setup.init_stk(_stk.name)
        self.tb = tb
        self.dut = dut
        self._ck_topo = self._ck_discover(dut)
        (dut.portA, tb.ethA, _tb) = self._ck_bind_link(setup, dut, 'tb')
        (dut.portFibre, fibre_port, fibre_peer) = self._ck_bind_link(
            setup, dut, 'fibre', optional=True)
        (dut.portPeer, peer_port, peer) = self._ck_bind_link(setup, dut, 'copper')
"""

# A stacked DUT whose cables are declared to a MEMBER other than swi_a, plus a partner.
BENCH_STACKED_WITH_PARTNER = BENCH_STACKED + "swi_c-swi_b = port1.0.1-port2.0.1\n"


def test_discovery_frame_yields_role_demands_and_no_non_literal_warning():
    d = parse_script(DISCOVERY_FRAME)
    assert [(r.role, r.dut, r.optional) for r in d.role_links] == [
        ("tb", "swi_a", False), ("fibre", "swi_a", True), ("copper", "swi_a", False)]
    assert d.links == [], "the frame calls no init_portlink"
    assert not any("non-literal" in w for w in d.warnings), d.warnings


def test_role_tb_is_satisfied_by_a_testbox_link_to_any_stack_member():
    rep = check(parse_script(DISCOVERY_FRAME), Bench.from_text(BENCH_STACKED))
    msgs = [p["message"] for p in rep["problems"]]
    assert not any("'tb'" in m for m in msgs), msgs
    assert any("role 'tb' can take tb-swi_a = eth3-port1.0.23" in n for n in rep["notes"])


def test_a_required_partner_role_with_no_partner_link_is_a_problem_naming_the_role():
    rep = check(parse_script(DISCOVERY_FRAME), Bench.from_text(BENCH_STACKED))
    assert not rep["runnable"]
    [prob] = [p for p in rep["problems"] if p["kind"] == "LINK"]
    assert prob["role"] == "copper" and "partner switch" in prob["message"]
    assert "BENCH PROBLEM" in prob["consequence"]


def test_an_optional_role_with_no_link_is_a_note_not_a_problem():
    rep = check(parse_script(DISCOVERY_FRAME), Bench.from_text(BENCH_STACKED))
    assert not any(p["role"] == "fibre" for p in rep["problems"])
    assert any("OPTIONAL role 'fibre'" in n and "UNSUPPORTED" in n for n in rep["notes"])


def test_MUTATION_a_partner_cable_to_another_stack_member_makes_the_frame_runnable():
    """The frame binds the stack that CONTAINS swi_a, so a link declared to swi_b (member 2)
    satisfies a copper demand written against swi_a. Fibre stays optional-unsatisfied."""
    rep = check(parse_script(DISCOVERY_FRAME), Bench.from_text(BENCH_STACKED_WITH_PARTNER))
    assert rep["runnable"], rep["problems"]
    assert any("role 'copper' can take swi_c-swi_b = port1.0.1-port2.0.1" in n for n in rep["notes"])


def test_media_is_declared_unknowable_offline():
    rep = check(parse_script(DISCOVERY_FRAME), Bench.from_text(BENCH_STACKED_WITH_PARTNER))
    note = next(n for n in rep["notes"] if "role 'copper' can take" in n)
    assert "read from the DUT at run time" in note and "show system pluggable" in note


def test_required_roles_are_matched_before_optional_ones_offline():
    """tb470 2026-07-30 shape: two swi_a<->swi_b links. The frame binds fibre (optional) BEFORE
    copper at run time — where it takes only a fibre-media link. Offline every partner link
    looks alike, so matching in source order would let the optional role eat the cable the
    required one needs and print a confident wrong UN-RUNNABLE. Required first: copper and a
    required cusfp take the two links, optional fibre is the one left without."""
    two = DISCOVERY_FRAME + "        (dut.portCuSfp, c_port, c_peer) = self._ck_bind_link(setup, dut, 'cusfp')\n"
    rep = check(parse_script(two), Bench.from_text(TB470_2026_07_30))
    assert rep["runnable"], rep["problems"]
    assert any("OPTIONAL role 'fibre'" in n for n in rep["notes"])
    assert rep["links_demanded"] == 4 and rep["links_unsatisfiable"] == 0


def test_three_required_partner_roles_against_two_links_fail_on_the_last():
    three = DISCOVERY_FRAME.replace("'fibre', optional=True", "'fibre'") + \
        "        (dut.portCuSfp, c_port, c_peer) = self._ck_bind_link(setup, dut, 'cusfp')\n"
    rep = check(parse_script(three), Bench.from_text(TB470_2026_07_30))
    assert not rep["runnable"]
    [prob] = rep["problems"]
    assert prob["role"] == "cusfp" and rep["links_unsatisfiable"] == 1


def test_the_legacy_frames_assert_media_false_reads_as_optional():
    """The saved T33234 binds its pluggable roles with `assert_media=False` inside try/except —
    optional in effect, so the preflight must not fail the script over them."""
    legacy = DISCOVERY_FRAME.replace("'fibre', optional=True", "misc, 'fibre', assert_media=False")
    d = parse_script(legacy)
    assert [(r.role, r.optional) for r in d.role_links] == [("tb", False), ("fibre", True), ("copper", False)]


def test_the_legacy_helpers_own_init_portlink_is_not_a_demand():
    """The saved test-9000.33234.py (pre-discovery) keeps `init_portlink()` INSIDE its own
    `_ck_bind_link`; that is the helper's mechanism, and must not surface as an unresolvable
    demand against a variable named `far`."""
    legacy = """
class TestSet(ATTestSet.TestSet):
    def _ck_bind_link(self, setup, dut, misc, role, assert_media=True):
        far = setup.init_swi('swi_b')
        (near, farp) = setup.init_portlink(dut, far, type1='port', type2='port')
        return near, farp, far
    def init(self, setup):
        tb = setup.init_tb()
        misc = setup.get_all_misc()
        dut = setup.init_swi(misc.get('ck_role_dut', 'swi_a'))
        self.tb = tb
        self.dut = dut
        (dut.portPeer, peer_port, peer) = self._ck_bind_link(setup, dut, misc, 'copper')
"""
    d = parse_script(legacy)
    assert d.links == [] and [(r.role, r.dut) for r in d.role_links] == [("copper", "swi_a")]
    rep = check(d, Bench.from_text(TB470_2026_07_30))
    assert rep["runnable"], rep["problems"]


def test_the_bench_parser_ignores_misc():
    """Terrence 2026-09-21: [misc] is not a lookup layer. Whatever a bench writes there
    changes no verdict."""
    with_misc = BENCH_STACKED_WITH_PARTNER + "\n[misc]\nck_link_copper = nonsense\nck_role_dut = swi_z\n"
    a = check(parse_script(DISCOVERY_FRAME), Bench.from_text(BENCH_STACKED_WITH_PARTNER))
    b = check(parse_script(DISCOVERY_FRAME), Bench.from_text(with_misc))
    assert a["runnable"] == b["runnable"] and a["problems"] == b["problems"]
    assert not hasattr(Bench.from_text(with_misc), "misc")

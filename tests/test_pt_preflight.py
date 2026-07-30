"""Regression tests for the pre-flight topology check (`tool/pt_preflight.py`).

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
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tool"))

pt_preflight = pytest.importorskip("pt_preflight")

Bench = pt_preflight.Bench
parse_script = pt_preflight.parse_script
check = pt_preflight.check


# --------------------------------------------------------------------------- fixtures

# SYNTHETIC bench: a two-member stack, two link partners, and exactly ONE declared
# portlink (testbox -> DUT). This is NOT tb470 — it kept that shape only until the
# 2026-07-30 de-stacking. It is retained deliberately, because the tool must still handle
# stack semantics (member expansion, the stackport-is-not-a-data-path note) on any bench
# that has a stack. For the live tb470 shape see TB470_LIVE below.
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
TB470_LIVE = """
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


REAL_SCRIPTS = sorted((REPO / "ask-ck" / "pytest-create" / "generated").rglob("*.py"))


@pytest.mark.skipif(not REAL_SCRIPTS, reason="no generated scripts in the tree")
def test_every_generated_script_parses_and_is_checkable():
    """Pins that the AST extraction actually understands the real skeleton's shape —
    a check that silently found zero demands would report everything as runnable."""
    for path in REAL_SCRIPTS:
        demands = parse_script(path.read_text(encoding="utf-8", errors="replace"), path)
        assert demands.roles, f"{path.name}: no devices detected"
        assert demands.links, f"{path.name}: no portlink demands detected"


def _verdicts(bench_text: str) -> dict:
    """Per-script verdicts. A FRESH Bench per script — link consumption is per-run state,
    so one bench object would let script #1 use up script #2's cables."""
    return {
        p.name: check(parse_script(p.read_text(encoding="utf-8", errors="replace"), p),
                      Bench.from_text(bench_text))["runnable"]
        for p in REAL_SCRIPTS
    }


@pytest.mark.skipif(not REAL_SCRIPTS, reason="no generated scripts in the tree")
def test_real_scripts_on_the_live_bench():
    """Pins the live tb470 outcome as at 2026-07-30 afternoon: declaring the two verified
    swi_a<->swi_b data links took this bench from 0/3 to 2/3.

    `3_Port_Fixed_port_test.py` remains un-runnable for a DIFFERENT and still-open reason —
    it also wants swi_a<->swi_c (the AR4050S), which has no data cabling. If that gets
    cabled and declared, this test should start failing: update TB470_LIVE."""
    v = _verdicts(TB470_LIVE)
    assert v.get("Port_Auto_MDI_MDI_test.py") is True, v
    assert v.get("Port_Auto_Negotiation_test.py") is True, v
    assert v.get("3_Port_Fixed_port_test.py") is False, v


@pytest.mark.skipif(not REAL_SCRIPTS, reason="no generated scripts in the tree")
def test_real_scripts_were_all_unrunnable_before_the_inter_switch_links():
    """The before-picture, kept as the contrast that gives the test above its meaning: with
    only the testbox->DUT portlink declared, every Port (7) script was un-runnable because
    each needs at least one switch<->switch data link."""
    assert not any(_verdicts(BENCH_STACKED).values()), _verdicts(BENCH_STACKED)

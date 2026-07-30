"""Regression tests for the topology-profile contract (`tool/pt_profiles.py`).

A profile check exists to answer "does this bench implement what generated tests target".
Its dangerous failure mode is being a rubber stamp: a checker that returned `conformant` for
anything would have said exactly the right thing about tb470 (base/fibre/tblink all
implemented, 2026-07-30) and been worth nothing. So every conformance assertion here is
paired with a bench MUTATION that must break it.

The other guarded failure is silent drift between `PROFILES` in the code and the profile
table in `ask-ck/pytest-create/TOPOLOGY-PROFILES.md` — a doc that lists a profile the tool
does not implement, or vice versa, is worse than no doc.

Pure unit tests — no DB, no network, no hardware, no LLM.
"""
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tool"))

from _prose import flat  # noqa: E402  (repo helper: whitespace-collapsed prose matching)

pt_profiles = pytest.importorskip("pt_profiles")
pt_preflight = pytest.importorskip("pt_preflight")

Bench = pt_preflight.Bench
PROFILES = pt_profiles.PROFILES
check_profile = pt_profiles.check_profile
parse_link_ref = pt_profiles.parse_link_ref

SPEC = REPO / "ask-ck" / "pytest-create" / "TOPOLOGY-PROFILES.md"


# --------------------------------------------------------------------------- fixture

# tb470 as at 2026-07-30 afternoon: de-stacked IE520 pair, copper + fibre links between
# them, a testbox data link to the DUT, and polarity verified on both IE520s.
TB470 = """
[misc]
ck_profile     = base, fibre, tblink
ck_role_dut    = swi_a
ck_link_copper = swi_a-swi_b:port1.0.1
ck_link_fibre  = swi_a-swi_b:port1.0.7
ck_link_tb     = tb-swi_a:eth3
ck_cap_swi_a   = polarity
ck_cap_swi_b   = polarity

[switch]
swi_a = /dev/u4
swi_b = /dev/u5
swi_c = /dev/u1
swi_d = /dev/u0

[portlink]
tb-swi_a = eth3-port1.0.23
swi_a-swi_b = port1.0.1-port1.0.1, port1.0.7-port1.0.7
"""


def rep(profile: str, bench_text: str = TB470) -> dict:
    return check_profile(Bench.from_text(bench_text), profile)


def messages(r: dict) -> str:
    return " | ".join(p["message"] for p in r["problems"])


# ------------------------------------------------------------------- the link reference


def test_link_ref_splits_pair_and_port():
    assert parse_link_ref("swi_a-swi_b:port1.0.1") == ("swi_a", "swi_b", "port1.0.1")


def test_link_ref_handles_the_tb_pseudo_device():
    assert parse_link_ref("tb-swi_a:eth3") == ("tb", "swi_a", "eth3")


def test_link_ref_without_a_port_suffix_is_allowed():
    assert parse_link_ref("swi_a-swi_b") == ("swi_a", "swi_b", None)


def test_link_ref_port_suffix_is_split_before_the_device_pair():
    """The ':' must be consumed first, so a port containing '-' could never be mistaken
    for the device separator."""
    assert parse_link_ref("swi_a-swi_b:port1.0.1-x")[2] == "port1.0.1-x"


# -------------------------------------------------------- conformance, and its mutations


def test_the_live_bench_implements_base():
    r = rep("base")
    assert r["conformant"], messages(r)
    assert r["claimed"]


def test_the_live_bench_implements_fibre_and_tblink():
    for name in ("fibre", "tblink"):
        r = rep(name)
        assert r["conformant"], f"{name}: {messages(r)}"


def test_MUTATION_dropping_the_verified_capability_breaks_base():
    bench = TB470.replace("ck_cap_swi_b   = polarity", "ck_cap_swi_b   =")
    r = rep("base", bench)
    assert not r["conformant"]
    assert "polarity" in messages(r) and "swi_b" in messages(r)


def test_MUTATION_removing_the_copper_role_breaks_base():
    bench = TB470.replace("ck_link_copper = swi_a-swi_b:port1.0.1", "ck_link_copper =")
    r = rep("base", bench)
    assert not r["conformant"]
    assert "ck_link_copper" in messages(r) or "not declared" in messages(r)


def test_MUTATION_pointing_a_role_at_an_uncabled_pair_breaks_base():
    """swi_c is a declared DEVICE but has no portlink — the distinction that matters."""
    bench = TB470.replace("ck_link_copper = swi_a-swi_b:port1.0.1",
                          "ck_link_copper = swi_a-swi_c:port1.0.1")
    r = rep("base", bench)
    assert not r["conformant"]
    assert "no [portlink] declared between swi_a and swi_c" in messages(r)


def test_MUTATION_naming_a_port_that_is_not_an_endpoint_breaks_base():
    bench = TB470.replace("ck_link_copper = swi_a-swi_b:port1.0.1",
                          "ck_link_copper = swi_a-swi_b:port1.0.99")
    r = rep("base", bench)
    assert not r["conformant"]
    assert "not an endpoint" in messages(r)


def test_MUTATION_pointing_the_dut_at_an_undeclared_device_breaks_base():
    bench = TB470.replace("ck_role_dut    = swi_a", "ck_role_dut    = swi_zz")
    r = rep("base", bench)
    assert not r["conformant"]
    assert "swi_zz" in messages(r)


def test_a_bench_that_does_not_claim_a_profile_is_not_conformant():
    """Implementing the requirements is not enough — the bench must also claim it, so
    conformance is an explicit assertion by whoever owns the bench."""
    bench = TB470.replace("ck_profile     = base, fibre, tblink", "ck_profile     = fibre")
    r = rep("base", bench)
    assert not r["conformant"]
    assert not r["claimed"]
    assert "does not claim" in messages(r)


def test_capability_is_required_of_the_FAR_end_not_the_dut():
    """base needs polarity on the PARTNER. Dropping only the DUT's own declaration must
    NOT break it — otherwise the check is looking at the wrong device."""
    bench = TB470.replace("ck_cap_swi_a   = polarity", "ck_cap_swi_a   =")
    r = rep("base", bench)
    assert r["conformant"], messages(r)


def test_stack_is_correctly_reported_as_not_implemented():
    r = rep("stack")
    assert not r["conformant"]
    assert "not in [stack]" in messages(r)


def test_MUTATION_declaring_a_real_stack_satisfies_the_stack_profile():
    bench = (TB470.replace("ck_profile     = base, fibre, tblink",
                           "ck_profile     = base, fibre, tblink, stack")
                  .replace("ck_role_dut    = swi_a", "ck_role_dut    = stk_a")
             + "\n[stack]\nstk_a = swi_a, swi_b\n")
    r = check_profile(Bench.from_text(bench), "stack")
    assert r["conformant"], messages(r)


def test_a_one_member_stack_does_not_satisfy_the_stack_profile():
    bench = (TB470.replace("ck_profile     = base, fibre, tblink",
                           "ck_profile     = stack")
                  .replace("ck_role_dut    = swi_a", "ck_role_dut    = stk_a")
             + "\n[stack]\nstk_a = swi_a\n")
    r = check_profile(Bench.from_text(bench), "stack")
    assert not r["conformant"]
    assert "needs >= 2" in messages(r)


def test_unknown_profile_is_rejected_not_silently_passed():
    r = rep("no_such_profile")
    assert not r["conformant"]
    assert "unknown profile" in messages(r)


def test_a_bench_with_no_misc_section_implements_nothing():
    bare = "[switch]\nswi_a = /dev/u4\n[portlink]\ntb-swi_a = eth3-port1.0.23\n"
    assert pt_profiles.declared_profiles(Bench.from_text(bare)) == []
    assert not check_profile(Bench.from_text(bare), "base")["conformant"]


def test_profile_list_accepts_comma_or_whitespace_separation():
    """The framework turns a comma-bearing [misc] value into a list, and a human may write
    either form; both must be understood."""
    for form in ("base, fibre", "base fibre", "base,fibre"):
        bench = TB470.replace("ck_profile     = base, fibre, tblink", f"ck_profile = {form}")
        assert "base" in pt_profiles.declared_profiles(Bench.from_text(bench))


# --------------------------------------------------------------- the documented limitation


def test_media_is_NOT_verified_and_the_spec_says_so():
    """Pins a known, deliberate hole so nobody mistakes a green for a media guarantee:
    pointing ck_link_copper at the FIBRE port passes, because copper and fibre are both
    `port1.0.x`. If this ever starts failing, the checker gained media awareness and the
    Limitations section of the spec must be rewritten."""
    bench = TB470.replace("ck_link_copper = swi_a-swi_b:port1.0.1",
                          "ck_link_copper = swi_a-swi_b:port1.0.7")
    assert rep("base", bench)["conformant"]
    # `flat` collapses whitespace, so the assertion survives a line wrap falling mid-phrase
    # (it did: "**run-time" / "assertion**" were on separate lines).
    spec = flat(SPEC.read_text(encoding="utf-8"))
    assert "Media is NOT machine-verified" in spec
    assert "run-time assertion" in spec


# ------------------------------------------------------------------------- drift guard


def test_spec_table_and_code_list_the_same_profiles():
    """The doc and `PROFILES` must not drift. Parses the profile names out of the spec's
    table (first column, backticked) and compares to the code."""
    spec = SPEC.read_text(encoding="utf-8")
    documented = set(re.findall(r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|", spec, re.M))
    assert documented, "no profile rows parsed out of the spec table — has it been reshaped?"
    assert documented == set(PROFILES), (
        f"documented={sorted(documented)} code={sorted(PROFILES)}")


def test_every_profile_has_a_nonempty_summary():
    for name, prof in PROFILES.items():
        assert prof.summary.strip(), f"{name} has no summary"
        assert prof.name == name, f"{name} disagrees with its own .name ({prof.name})"


def test_every_capability_and_media_key_refers_to_a_link_the_profile_requires():
    """A cap or media rule on a link the profile never requires would never be checked —
    silently dead configuration."""
    for name, prof in PROFILES.items():
        for key in list(prof.caps) + list(prof.media):
            assert key in prof.links, f"{name}: rule on unrequired link {key!r}"

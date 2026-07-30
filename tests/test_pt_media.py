"""Regression tests for the run-time media assertion (`tool/pt_media.py`).

Every fixture below is REAL `show interface <port> status` output captured from the two tb470
IE520s on 2026-07-30 — not invented, because the whole point of this module is that it agrees
with what the hardware actually prints. Between them they cover the four cases that matter:
1000BASE-T (RJ45), 10GBASE-TM (10G RJ45 — same port NUMBER as the 1000BASE-T on the other
unit), 1000BASE-SX (fibre), and `not present` (empty cage, and the reason the Type column
cannot be token-split: `split()[-1]` reads "present").

The failure mode guarded against is a classifier that guesses. Assuming "copper" for an
unrecognised string would produce exactly the false product verdict this module exists to
prevent, so UNKNOWN must stay unsatisfiable.

Pure unit tests — no DB, no network, no hardware, no LLM.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tool"))

pt_media = pytest.importorskip("pt_media")

media_type = pt_media.media_type
classify = pt_media.classify
satisfies = pt_media.satisfies
assert_role_media = pt_media.assert_role_media

TWISTED_PAIR = pt_media.TWISTED_PAIR
FIBRE = pt_media.FIBRE
ABSENT = pt_media.ABSENT
UNKNOWN = pt_media.UNKNOWN
DIRECT_ATTACH = pt_media.DIRECT_ATTACH


# --------------------------------------------------------------- real captured output

# u4 (swi_a) port1.0.1 — the copper link end. AT-SPTXc.
U4_COPPER = """show interface port1.0.1 status
Port        Name               Status      Vlan      Duplex Speed   Type
--------------------------------------------------------------------------------
port1.0.1   -                  connected           1 a-full a-1000  1000BASE-T
awplus#"""

# u4 (swi_a) port1.0.7 — the fibre link end. AT-SPSX.
U4_FIBRE = """show interface port1.0.7 status
Port        Name               Status      Vlan      Duplex Speed   Type
--------------------------------------------------------------------------------
port1.0.7   -                  connected           1 a-full a-1000  1000BASE-SX
awplus#"""

# u5 (swi_b) port1.0.1 — SAME port number as U4_COPPER, DIFFERENT module (AT-SP10TM).
# This pair is the concrete proof that media cannot be inferred from a port name.
U5_COPPER_10G = """show interface port1.0.1 status
Port        Name               Status      Vlan      Duplex Speed   Type
--------------------------------------------------------------------------------
port1.0.1   -                  connected           1 a-full a-1000  10GBASE-TM
awplus#"""

# u5 (swi_b) port1.0.23 — empty cage. Note the two-word Type value.
U5_EMPTY = """show interface port1.0.23 status
Port        Name               Status      Vlan      Duplex Speed   Type
--------------------------------------------------------------------------------
port1.0.23  -                  notconnect       1000 auto   auto    not present
awplus#"""


# ------------------------------------------------------------------------- parsing


def test_parses_type_from_real_copper_output():
    assert media_type(U4_COPPER, "port1.0.1") == "1000BASE-T"


def test_parses_type_from_real_fibre_output():
    assert media_type(U4_FIBRE, "port1.0.7") == "1000BASE-SX"


def test_parses_the_10g_twisted_pair_form():
    assert media_type(U5_COPPER_10G, "port1.0.1") == "10GBASE-TM"


def test_parses_the_two_word_not_present_value():
    """The reason for column slicing: a token split would yield "present"."""
    assert media_type(U5_EMPTY, "port1.0.23") == "not present"
    assert U5_EMPTY.strip().splitlines()[-2].split()[-1] == "present"  # the trap, demonstrated


def test_a_port_not_in_the_output_returns_none():
    assert media_type(U4_COPPER, "port1.0.9") is None


def test_does_not_confuse_a_port_whose_name_is_a_prefix_of_another():
    """port1.0.2 must not match the port1.0.23 row."""
    assert media_type(U5_EMPTY, "port1.0.2") is None


# ---------------------------------------------------------------------- classifying


@pytest.mark.parametrize("raw,expected", [
    ("1000BASE-T", TWISTED_PAIR),
    ("10GBASE-TM", TWISTED_PAIR),
    ("100BASE-TX", TWISTED_PAIR),
    ("10GBASE-T", TWISTED_PAIR),
    ("1000BASE-SX", FIBRE),
    ("1000BASE-LX", FIBRE),
    ("10GBASE-SR", FIBRE),
    ("10GBASE-LR", FIBRE),
    ("100BASE-FX", FIBRE),
    ("1000BASE-CX", DIRECT_ATTACH),
    ("10GBASE-CR", DIRECT_ATTACH),
    ("not present", ABSENT),
    ("", ABSENT),
    (None, ABSENT),
    ("something-weird", UNKNOWN),
])
def test_classification(raw, expected):
    assert classify(raw) == expected


def test_direct_attach_is_not_lumped_in_with_twisted_pair():
    """Twinax/DAC is electrically copper but has no MDI/MDIX concept, so treating it as
    RJ45 would reintroduce the same false-verdict bug in a new shape."""
    assert classify("10GBASE-CR") != TWISTED_PAIR
    assert not satisfies("copper", classify("10GBASE-CR"))[0]


# ----------------------------------------------------------------------- satisfying


def test_copper_role_accepts_both_real_twisted_pair_forms():
    for fixture, port in ((U4_COPPER, "port1.0.1"), (U5_COPPER_10G, "port1.0.1")):
        ok, why = assert_role_media(fixture, port, "copper")
        assert ok, why


def test_copper_role_REJECTS_the_real_fibre_port():
    """The core case: this is what stops `polarity`/`speed 100` running against fibre and
    reporting a product failure."""
    ok, why = assert_role_media(U4_FIBRE, "port1.0.7", "copper")
    assert not ok
    assert "fibre" in why


def test_fibre_role_accepts_the_real_fibre_port_and_rejects_copper():
    assert assert_role_media(U4_FIBRE, "port1.0.7", "fibre")[0]
    assert not assert_role_media(U4_COPPER, "port1.0.1", "fibre")[0]


def test_an_empty_cage_is_refused():
    ok, why = assert_role_media(U5_EMPTY, "port1.0.23", "copper")
    assert not ok
    assert "no pluggable" in why


def test_UNKNOWN_media_is_refused_rather_than_assumed_copper():
    """Never guess. Assuming the common case is how you get a confident wrong verdict."""
    ok, why = satisfies("copper", classify("2500BASE-WHAT"))
    assert not ok
    assert "refusing to assume" in why


def test_an_unknown_role_is_refused():
    ok, why = satisfies("gigabit-ish", TWISTED_PAIR)
    assert not ok
    assert "unknown media role" in why


def test_failure_messages_blame_the_bench_not_the_product():
    """A message that reads as a DUT defect defeats the module's whole purpose — the
    generated script pastes this straight into a failure record."""
    for fixture, port in ((U4_FIBRE, "port1.0.7"), (U5_EMPTY, "port1.0.23")):
        ok, why = assert_role_media(fixture, port, "copper")
        assert not ok
        assert "not a product defect" in why


def test_the_message_carries_the_raw_type_for_diagnosis():
    ok, why = assert_role_media(U4_FIBRE, "port1.0.7", "copper")
    assert "1000BASE-SX" in why and "port1.0.7" in why


def test_roles_here_match_the_profile_link_roles():
    """pt_media's role names must line up with the ck_link_* roles pt_profiles defines,
    or a profile could require a media rule this module cannot evaluate."""
    pt_profiles = pytest.importorskip("pt_profiles")
    profile_links = {l for p in pt_profiles.PROFILES.values() for l in p.links}
    # Every media role must correspond to a real profile link role.
    assert set(pt_media.ROLE_REQUIRES) <= profile_links, (
        f"media roles {sorted(pt_media.ROLE_REQUIRES)} not all in profile links "
        f"{sorted(profile_links)}")

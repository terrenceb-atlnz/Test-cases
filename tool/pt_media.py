#!/usr/bin/env python3
"""Run-time MEDIA assertion for a bound port — the guard no offline checker can provide.

WHY THIS EXISTS. `TOPOLOGY-PROFILES.md` lets a bench say `ck_link_copper =
swi_a-swi_b:port1.0.1`, which removes the old accident where a test bound whichever link
happened to be listed first. But that declaration is **intent, not a guarantee**: media is a
property of the *pluggable*, swappable in seconds with no file change. On tb470 the same port
number already differs between units — u4 `port1.0.1` is a 1000BASE-T, u5 `port1.0.1` is a
10GBASE-TM. No file, and no static checker, can survive that.

And the CLI will not save you. Measured on an IE520, 2026-07-30: on the **1000BASE-SX fibre**
port, `speed ?` still offers `10 … 400000` and `duplex ?` still offers `half`, identically to
copper. Nothing rejects a nonsensical setting. So a speed/duplex matrix bound to fibre — which
is 1000 Mbps-only — records "DUT failed to set speed 100", a **false failure blamed on the
product**; and `polarity` on fibre is a silent no-op, because MDI/MDI-X is a twisted-pair
crossover concept with no fibre equivalent. Both look like defects. Neither is.

So a media-specific test must ASK THE DEVICE what is in the port it just bound, and fail
loudly if it is the wrong thing. That is all this module does.

WHAT A GENERATED SCRIPT DOES WITH IT:

    out  = dut.cmd('show interface {} status'.format(port.name))
    kind = classify(media_type(out, port.name))          # 'twisted_pair' | 'fibre' | ...
    ok, why = satisfies('copper', kind)
    if not ok:
        self.failed(why)          # loud, and names the real cause

DESIGN RULE: never guess. An unrecognised media string returns 'unknown' and `satisfies()`
refuses it, rather than assuming copper because copper is common. A wrong guess here produces
exactly the false verdict the module exists to prevent.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Categories. Deliberately finer than "copper", because MDI/MDIX and the 10/100 speed range
# apply to TWISTED PAIR specifically -- a 10GBASE-CR direct-attach twinax cable is
# electrically copper but has no MDI/MDIX concept either, so lumping it in with RJ45 would
# reintroduce the bug in a new shape.
TWISTED_PAIR = "twisted_pair"
FIBRE = "fibre"
DIRECT_ATTACH = "direct_attach"
ABSENT = "absent"
UNKNOWN = "unknown"

# What each PROFILE role name demands of the port it binds. Role names stay in the vocabulary
# people actually use ('copper'); the categories stay precise.
ROLE_REQUIRES = {
    "copper": (TWISTED_PAIR,),
    "fibre": (FIBRE,),
    # The testbox data link (profile `tblink`, `ck_link_tb = tb-<dut>:<eth>`): a capture /
    # injection path, not a media-under-test, so ANY fitted media satisfies it. An empty
    # tuple means "no media requirement" -- distinct from an UNKNOWN role, which is refused.
    "tb": (),
}

# `<n>BASE-T`, `-TX`, `-TM`, `-T4` ... = RJ45 twisted pair. Real strings seen on tb470:
# 1000BASE-T, 10GBASE-TM.
_TWISTED_RX = re.compile(r"BASE-T[A-Z0-9]*$", re.I)
# Fibre optics: SX LX LH SR LR ER ZR ZX BX FX EX PX ... anything BASE-<not T/C>.
_FIBRE_RX = re.compile(r"BASE-(?:S|L|E|Z|B|F|P|D)[A-Z0-9]*$", re.I)
# Direct-attach / twinax: CX, CR, CX4, KR (backplane).
_DA_RX = re.compile(r"BASE-(?:C|K)[A-Z0-9]*$", re.I)

_ABSENT_STRINGS = frozenset({"", "-", "not present", "notpresent", "none", "unknown"})


def parse_link_ref(value: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """`'swi_a-swi_b:port1.0.1'` -> `('swi_a', 'swi_b', 'port1.0.1')`.

    The `[misc] ck_link_<role>` format. Lives here rather than in `pt_profiles` because THIS
    module is the one shipped to the testbox and executed by the generated script; the
    contract checker imports it from here so there is exactly one definition.

    Splits the port suffix FIRST, so a ':' can never be confused with the '-' separating the
    two device names.
    """
    if not value:
        return None, None, None
    pair, _, port = value.partition(":")
    idx = pair.find("-")
    while idx != -1:
        left, right = pair[:idx].strip(), pair[idx + 1:].strip()
        if left and right:
            return left, right, (port.strip() or None)
        idx = pair.find("-", idx + 1)
    return None, None, (port.strip() or None)


def media_type(status_output: str, port: str) -> Optional[str]:
    """Pull the `Type` column for `port` out of `show interface <port> status` output.

    Column-sliced off the HEADER rather than token-split, because the value can contain a
    space -- an empty cage reports `not present`, which a naive `split()[-1]` would read as
    the single word "present".
    """
    header_idx = None
    for line in status_output.splitlines():
        if header_idx is None and "Port" in line and "Type" in line:
            header_idx = line.index("Type")
            continue
        if header_idx is None:
            continue
        stripped = line.strip()
        if not stripped or set(stripped) <= {"-"}:
            continue
        if stripped.split()[0] != port:
            continue
        # Slice from the header's Type column; values are right-padded, never left of it.
        value = line[header_idx:].strip() if len(line) > header_idx else ""
        if value:
            return value
        # Degenerate/rewrapped output: fall back to the trailing token.
        parts = stripped.split()
        return parts[-1] if len(parts) > 1 else None
    return None


def classify(type_str: Optional[str]) -> str:
    """A media `Type` string -> one category. Never guesses; unrecognised is UNKNOWN."""
    if type_str is None:
        return ABSENT
    t = " ".join(type_str.split()).lower()
    if t in _ABSENT_STRINGS:
        return ABSENT
    if _TWISTED_RX.search(t):
        return TWISTED_PAIR
    if _DA_RX.search(t):
        return DIRECT_ATTACH
    if _FIBRE_RX.search(t):
        return FIBRE
    return UNKNOWN


def satisfies(role: str, category: str) -> Tuple[bool, str]:
    """Does a port of `category` satisfy the media demand of profile role `role`?

    Returns (ok, why) where `why` is written to go straight into a test failure message --
    it has to say the BENCH is wrong, not the product, or it defeats the purpose.
    """
    wanted = ROLE_REQUIRES.get(role)
    if wanted is None:
        return False, (f"unknown media role {role!r}; known roles: "
                       f"{', '.join(sorted(ROLE_REQUIRES))}")
    if not wanted:
        if category == ABSENT:
            return False, (f"BENCH PROBLEM, not a product defect: the port bound for role "
                           f"{role!r} has no pluggable fitted, so this test cannot run here")
        return True, f"role {role!r} has no media requirement (port media {category})"
    if category in wanted:
        return True, f"port media {category} satisfies role {role!r}"
    if category == ABSENT:
        return False, (f"BENCH PROBLEM, not a product defect: the port bound for role "
                       f"{role!r} has no pluggable fitted, so this test cannot run here")
    if category == UNKNOWN:
        return False, (f"BENCH PROBLEM, not a product defect: could not classify the media "
                       f"of the port bound for role {role!r}; refusing to assume it is "
                       f"{'/'.join(wanted)}")
    return False, (
        f"BENCH PROBLEM, not a product defect: role {role!r} requires "
        f"{'/'.join(wanted)} but the bound port is {category}. "
        + ("MDI/MDIX and the 10/100 speed range do not exist on this media, and the CLI "
           "accepts those commands anyway -- so continuing would report a product failure "
           "that is really a cabling error." if role == "copper" else
           "Re-point the ck_link_* role in the bench .setup at a port of the right media.")
    )


def assert_role_media(status_output: str, port: str, role: str) -> Tuple[bool, str]:
    """Convenience: parse, classify and check in one call."""
    raw = media_type(status_output, port)
    ok, why = satisfies(role, classify(raw))
    return ok, f"{why} (port {port}, Type={raw!r})"

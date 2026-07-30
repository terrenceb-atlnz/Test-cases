#!/usr/bin/env python3
"""Canonical TOPOLOGY PROFILES — the contract between a generated test and a bench.

THE POINT. A generated script must never be written against a particular bench: it has to
run unchanged anywhere. But before this file existed, generation picked its `.setup` role
keys POSITIONALLY from whatever device names the selected fragments happened to mention
(`_setup_keys_for` in routers/pytest_create.py), so "the third device I saw" became
`swi_c` — an arbitrary demand no bench had agreed to satisfy. That is how
`3_Port_Fixed_port_test.py` came to require a `swi_a`<->`swi_c` link it never uses.

The fix is NOT to let generation read a bench file. That would make it silently weaken a
test to fit the hardware in front of it — a three-switch test quietly generated as a
two-switch test still goes green, and a false green is unfalsifiable from outside.

Instead, generation targets a CONTRACT. A contract is not a bench:

    generation  ->  declares the PROFILE its test needs      (never reads a .setup)
    a bench     ->  declares the PROFILES it implements       (in its own [misc] section)
    this module ->  MATCHES the two, and says what is missing

So a test that needs a topology nobody has cabled yet fails loudly with a shopping list,
which is the outcome we want. Nothing downgrades the test to fit the bench.

WHY PROFILES AND NOT ONE MONOLITH. "One canonical topology" accretes without bound —
copper partner, fibre partner, 10G, PoE, hub, traffic generator, heat chamber — until no
real bench satisfies it. Profiles are claimable in pieces, so conformance is honest and
partial: tb470 implements `base`+`fibre`+`tblink` and says plainly that it does not
implement `stack`.

ROLES NAME LINKS, NOT JUST DEVICES. A role is a (device, link, media) triple, because the
same device can serve two roles over two different cables — on tb470 `swi_b` is both the
copper partner (port1.0.1) and the fibre partner (port1.0.7). This matters concretely:
MDI/MDI-X is a COPPER-only feature, the framework's `init_portlink(type1='port')` filter
cannot tell copper from fibre (both are `port1.0.x`), and the CLI accepts `polarity` on a
fibre port where it silently does nothing. Asking for `link_copper` by name makes that
class of false green impossible; asking for "a port-type link" does not.

CAPABILITIES ARE HARDWARE-VERIFIED CLAIMS, NOT DOC LOOKUPS. A bench declares
`ck_cap_<device>` from what was actually confirmed on the device. It is tempting to derive
this from ck.db's `cli_command_products`, and that is wrong: `polarity` is documented for
29 products NOT including ie520, yet the IE520 on tb470 supports it (verified at the
console, 2026-07-30). Absence from the harvested docs means UNKNOWN, never unsupported.

--------------------------------------------------------------------------------------
WHAT A BENCH WRITES, in its own `.setup`. `[misc]` is a section the framework already
accepts and stores verbatim, so this breaks no existing bench file:

    [misc]
    ck_profile     = base, fibre, tblink        # comma list -> framework parses as a list
    ck_role_dut    = swi_a
    ck_link_copper = swi_a-swi_b:port1.0.1      # <devA>-<devB>:<port on devA>
    ck_link_fibre  = swi_a-swi_b:port1.0.7
    ck_link_tb     = tb-swi_a:eth3
    ck_cap_swi_b   = polarity                   # VERIFIED on the device, not from docs

The `:<port on devA>` suffix is what disambiguates which of several declared links between
the same pair is meant — exactly the copper/fibre ambiguity above. Keep link values
comma-free: the framework turns any comma-bearing [misc] value into a list.

TO ADD A PROFILE: add an entry to PROFILES below and a row to the table in
`ask-ck/pytest-create/TOPOLOGY-PROFILES.md`. A test asserts those two agree, so they
cannot drift.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pt_preflight import Bench, TB, iface_type  # noqa: E402
# One definition, and it lives in the module the generated script actually ships with.
from pt_media import parse_link_ref  # noqa: E402,F401  (re-exported for callers/tests)

MISC_PROFILE = "ck_profile"
ROLE_PREFIX = "ck_role_"
LINK_PREFIX = "ck_link_"
CAP_PREFIX = "ck_cap_"


class Profile:
    """One claimable tier of the contract.

    devices  role names that must resolve via `ck_role_<role>` to a declared device.
    links    link names that must resolve via `ck_link_<name>` to a DECLARED portlink.
    caps     {link name: (capability, ...)} required of the device at the FAR end of that
             link — far end meaning the end that is not the DUT.
    media    {link name: expected iface type} sanity check on the named port ('port'/'eth').
    stack    if True the DUT role must name a [stack] with >= 2 members.
    """

    __slots__ = ("name", "summary", "devices", "links", "caps", "media", "stack")

    def __init__(self, name, summary, devices=(), links=(), caps=None, media=None,
                 stack=False):
        self.name, self.summary = name, summary
        self.devices, self.links = tuple(devices), tuple(links)
        self.caps = dict(caps or {})
        self.media = dict(media or {})
        self.stack = stack


PROFILES: Dict[str, Profile] = {
    "base": Profile(
        name="base",
        summary="A DUT plus one copper link partner whose MDI/MDIX polarity can be set. "
                "The floor for physical-layer port tests (speed, duplex, MDI/MDI-X): they "
                "need a partner to negotiate against, and polarity control is what makes a "
                "crossover case automatable instead of a manual cable swap.",
        devices=("dut",),
        links=("copper",),
        caps={"copper": ("polarity",)},
        media={"copper": "port"},
    ),
    "fibre": Profile(
        name="fibre",
        summary="A fibre link from the DUT to a partner. Separate from `base` because "
                "fibre has no MDI/MDIX concept at all, so a fibre link can never satisfy "
                "a copper requirement — and the framework's type filter cannot tell them "
                "apart.",
        links=("fibre",),
        media={"fibre": "port"},
    ),
    "tblink": Profile(
        name="tblink",
        summary="A data link from the testbox itself to the DUT, for tests that source or "
                "sink real traffic. Independent of any switch-to-switch cabling: a bench "
                "can have partners but no testbox data path, or the reverse.",
        links=("tb",),
    ),
    "stack": Profile(
        name="stack",
        summary="The DUT is a VCStack of >= 2 members. NOT `base` plus a device: stacking "
                "renames every port (1.0.x -> N.0.x), which leaks into portlinks, "
                "fragments and every port literal, so stacked and unstacked benches are "
                "different topologies rather than sub/supersets.",
        devices=("dut",),
        stack=True,
    ),
}


# ------------------------------------------------------------------------------ parsing


def declared_profiles(bench: Bench) -> List[str]:
    """The profiles a bench claims. Tolerates comma OR whitespace separation, because the
    framework itself turns a comma value into a list and a human may write either."""
    raw = bench.misc.get(MISC_PROFILE, "")
    return [p for p in raw.replace(",", " ").split() if p]


def capabilities(bench: Bench, device: str) -> List[str]:
    raw = bench.misc.get(f"{CAP_PREFIX}{device}", "")
    return [c for c in raw.replace(",", " ").split() if c]


# ------------------------------------------------------------------------------ checking


def check_profile(bench: Bench, profile_name: str) -> dict:
    """Does this bench implement this profile? Pure; returns a report dict."""
    prof = PROFILES.get(profile_name)
    if prof is None:
        return {"profile": profile_name, "conformant": False, "claimed": False,
                "problems": [{"role": None, "message": f"unknown profile {profile_name!r}",
                              "fix": f"known profiles: {', '.join(sorted(PROFILES))}"}],
                "checks": []}

    problems: List[dict] = []
    checks: List[dict] = []
    claimed = profile_name in declared_profiles(bench)
    if not claimed:
        problems.append({
            "role": MISC_PROFILE,
            "message": f"bench does not claim profile {profile_name!r}",
            "fix": f"add it to [misc] {MISC_PROFILE} once the requirements below are met",
        })

    dut = bench.misc.get(f"{ROLE_PREFIX}dut")

    for role in prof.devices:
        key = f"{ROLE_PREFIX}{role}"
        named = bench.misc.get(key)
        if not named:
            problems.append({"role": key, "message": f"[misc] {key} is not declared",
                             "fix": f"add `{key} = <swi_x or stk_x>`"})
            continue
        if not bench.known(named):
            problems.append({"role": key,
                             "message": f"{key} names {named!r}, which the bench does not declare",
                             "fix": "declare it in [switch]/[stack], or point the role elsewhere"})
            continue
        checks.append({"role": key, "detail": f"{named} (declared)"})

    if prof.stack:
        if dut and dut not in bench.stacks:
            problems.append({
                "role": f"{ROLE_PREFIX}dut",
                "message": f"profile requires the DUT to be a stack, but {dut!r} is not in [stack]",
                "fix": "point ck_role_dut at a stk_* with >= 2 members"})
        elif dut and len(bench.stacks.get(dut, [])) < 2:
            problems.append({
                "role": f"{ROLE_PREFIX}dut",
                "message": f"stack {dut!r} has {len(bench.stacks.get(dut, []))} member(s), needs >= 2",
                "fix": "add the other member(s) to [stack]"})
        elif dut:
            checks.append({"role": f"{ROLE_PREFIX}dut",
                           "detail": f"{dut} is a stack of {len(bench.stacks[dut])}"})

    for link in prof.links:
        key = f"{LINK_PREFIX}{link}"
        value = bench.misc.get(key)
        if not value:
            problems.append({"role": key, "message": f"[misc] {key} is not declared",
                             "fix": f"add `{key} = <devA>-<devB>:<port on devA>`"})
            continue
        devA, devB, port = parse_link_ref(value)
        if not devA or not devB:
            problems.append({"role": key, "message": f"{key} = {value!r} is not <devA>-<devB>:<port>",
                             "fix": "e.g. swi_a-swi_b:port1.0.1"})
            continue
        unknown = [d for d in (devA, devB) if d != TB and not bench.known(d)]
        if unknown:
            problems.append({"role": key,
                             "message": f"{key} names undeclared device(s): {', '.join(unknown)}",
                             "fix": "declare them in [switch]/[stack]"})
            continue
        declared = bench.links_between(devA, devB)
        if not declared:
            problems.append({
                "role": key,
                "message": f"no [portlink] declared between {devA} and {devB}",
                "fix": f"cable it, then add `{devA}-{devB} = <portA>-<portB>` to [portlink]"})
            continue
        if port and not any(port in (l.portA, l.portB) for l in declared):
            problems.append({
                "role": key,
                "message": f"{key} names port {port!r}, which is not an endpoint of any "
                           f"declared {devA}-{devB} link",
                "fix": "declared: " + "; ".join(l.raw for l in declared)})
            continue
        want_media = prof.media.get(link)
        if want_media and port and iface_type(port) != want_media:
            problems.append({
                "role": key,
                "message": f"{key} port {port!r} is interface type "
                           f"{iface_type(port)!r}, profile wants {want_media!r}",
                "fix": "point the role at a port of the right type"})
            continue
        checks.append({"role": key, "detail": f"{devA}<->{devB}" + (f" via {port}" if port else "")})

        # capability of the FAR end (the end that is not the DUT)
        for cap in prof.caps.get(link, ()):
            far = devB if devA == dut else devA
            have = capabilities(bench, far)
            if cap not in have:
                problems.append({
                    "role": f"{CAP_PREFIX}{far}",
                    "message": f"{far} must support {cap!r} for profile {profile_name!r}, "
                               f"but declares {have or 'nothing'}",
                    "fix": f"VERIFY on the device (e.g. `{cap} ?` in interface config), then "
                           f"add `{CAP_PREFIX}{far} = {cap}` — do NOT infer it from the docs"})
            else:
                checks.append({"role": f"{CAP_PREFIX}{far}", "detail": f"{cap} (verified)"})

    return {"profile": profile_name, "conformant": not problems, "claimed": claimed,
            "problems": problems, "checks": checks}


def check_profiles(bench: Bench, names: Sequence[str]) -> List[dict]:
    return [check_profile(bench, n) for n in names]

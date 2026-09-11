#!/usr/bin/env python3
"""Bench probe — read a testbox's real state through the FRAMEWORK's own console driver.

WHY THE FRAMEWORK AND NOT A NEW DRIVER. A hand-rolled pyserial loop has to re-solve
login/enable/paging/prompt handling, and — worse — it would see the bench differently
from the tests we are trying to describe. `LoadSetup.init_swi()` gives back the same
`ATSwitch.Switch` a generated script binds, with the same credentials out of the
`.setup`, so what this reports is what a test will meet.

READ-ONLY BY DEFAULT. Every command here is a `show`. The one mutating path is
`--assign-ip`, which exists because cabling discovery needs an address on both ends
and a bench may legitimately have none (tb470's IE520 stack has `vlan1 unassigned`).
It writes running-config only — never `write memory` — so a reload undoes it.

`powerOn=False` is passed to every init: `init_swi`/`init_stk` otherwise call
`power_group.on()`, and this must never touch the PDU on a shared bench.

Run ON the testbox (the consoles are local to it):
    cd /tmp/bench-probe && ln -sfn /home/st-art/framework framework
    sudo -n PYTHONPATH=/home/st-art python3 bench_probe.py -s <path>.setup
"""
import argparse
import json
import sys

from framework.Setup import LoadSetup

# The sequence Terrence specified, plus `show system` (model/serial per member) and
# `show interface status` — the latter is the highest-value single command: port,
# link state, VLAN, duplex, speed AND media in one table, with stackports marked.
COMMANDS = [
    "show system",
    "show running-config",
    "show stack",
    "show vlan brief",
    "show ip interface brief",
    "show interface status",
    "show system pluggable",
    "show mac address-table",
    "show arp",
]


def console_of(dev):
    """The object that accepts `cmd()`.

    A `Stack` is not itself a console — it holds `members`. On a formed AW+ VCStack
    every member's console serves the stack-wide CLI, so any member will do; this is
    also why a stacked pair must not be bound as two devices.
    """
    if hasattr(dev, "cmd"):
        return dev
    for m in getattr(dev, "members", ()) or ():
        if hasattr(m, "cmd"):
            return m
    raise RuntimeError(f"no console on {dev!r}")


# The terminal summary shows only these. The rest are still CAPTURED -- main() says so
# explicitly rather than letting a partial answer look like a complete one, which is the
# failure shape recorded in [[silent-degradation-audit-2026-07-30]].
SUMMARY = ("show system", "show ip interface brief", "show interface status")


def probe(dev, name, commands=None):
    """Run the read-only sequence against one bound device.

    `console.mode('#')` FIRST. `init_swi()`/`init_stk()` build the Switch and resolve
    its credentials (`ATSwitch.__resolve_username_and_password`: default user `manager`,
    password list `['friend', 'P@ssw0rd', 'awplus']`) but do NOT establish the session --
    that happens later in the TestSet lifecycle. Call `cmd()` on a console that has timed
    out to `login:` and every command is typed as a login attempt, which comes back as
    `Login incorrect` and reads like a dead device. Observed here 2026-09-01.
    """
    dev = console_of(dev)
    try:
        dev.console.mode("#")
    except Exception as e:
        return {"!! console.mode('#') failed": f"{type(e).__name__}: {e}"}
    out = {}
    for c in (commands or COMMANDS):
        try:
            out[c] = dev.cmd(c)
        except Exception as e:                      # a product may not have the command
            out[c] = f"!! {type(e).__name__}: {e}"
    return out


def bind_devices(setup, setup_dict, only=None):
    """Bind declared devices. Stacks bind as stacks — a stacked pair is ONE
    logical device whose members share a CLI, not two devices (tb470's own setup
    header: binding them as DUT + partner 'measures one device against itself').

    `only` names devices to bind EXPLICITLY, and deliberately bypasses the
    stack-member skip below. That exists because the skip is wrong in exactly
    the case you most need to read: when a member has FALLEN OUT of its stack
    it is unreachable through `init_stk`, so a default probe cannot see it at
    all. Measured 2026-09-02 — a split stack could not be read without this,
    which is how a pile of one-off scripts got written instead.
    """
    bound = {}
    stacks = setup_dict.get("stacks") or {}
    switches = setup_dict.get("switches") or {}

    if only:
        for name in only:
            if name in stacks:
                d = setup.init_stk(name, powerOn=False)
            elif name in switches:
                d = setup.init_swi(name, powerOn=False)     # member or not
            else:
                print("!! no device {!r} in the .setup (have: {})".format(
                    name, ", ".join(sorted(list(stacks) + list(switches)))))
                continue
            if d is not None:
                bound[name] = d
        return bound

    for stk in stacks:
        d = setup.init_stk(stk, powerOn=False)
        if d is not None:
            bound[stk] = d
    # Members of a bound stack are NOT bound again: their consoles reach the same CLI.
    stacked = {m for info in stacks.values() for m in (info.get("members") or [])}
    for swi in switches:
        if swi in stacked:
            continue
        d = setup.init_swi(swi, powerOn=False)
        if d is not None:
            bound[swi] = d
    return bound


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-s", "--setup", required=True, help="path to the .setup file")
    ap.add_argument("--json", metavar="FILE", help="write the raw capture here")
    ap.add_argument("--device", metavar="NAME", action="append", default=[],
                    help="bind only this device (repeatable), e.g. --device swi_b. "
                         "Works on a stack MEMBER too, including one that has fallen "
                         "out of its stack and is therefore invisible via the stack.")
    ap.add_argument("--cmd", metavar="COMMAND", action="append", default=[],
                    help="run these read-only commands instead of the default set "
                         "(repeatable). Refuses anything that is not a `show`.")
    ap.add_argument("--assign-ip", metavar="DEV=VLAN:CIDR", action="append", default=[],
                    help="MUTATES running-config: e.g. stk_a=vlan1:10.38.215.71/27. "
                         "Never saved to startup-config.")
    args = ap.parse_args(argv)

    setup = LoadSetup(args.setup)
    cmds = list(COMMANDS)
    if args.cmd:
        bad = [c for c in args.cmd if not c.strip().lower().startswith("show")]
        if bad:
            # This probe is the READ-ONLY path and several callers rely on that.
            # A --cmd passthrough that accepted `configure terminal` would quietly
            # turn it into a mutation tool.
            print("!! refusing non-show command(s): {}".format(", ".join(bad)))
            return 2
        cmds = args.cmd

    bound = bind_devices(setup, setup.setupDict, only=args.device)
    if not bound:
        print("!! nothing bound -- check --device names against the .setup")
        return 2
    print(f"bound {len(bound)} device(s): {', '.join(sorted(bound))}\n")

    for spec in args.assign_ip:
        dev_name, rest = spec.split("=", 1)
        vlan, cidr = rest.split(":", 1)
        dev = bound.get(dev_name)
        if dev is None:
            print(f"!! --assign-ip: no bound device {dev_name!r}")
            continue
        print(f"** MUTATING {dev_name}: {vlan} -> {cidr} (running-config only)")
        dev = console_of(dev)
        dev.console.mode("#")
        dev.cmd("configure terminal")
        dev.cmd(f"interface {vlan}")
        dev.cmd(f"ip address {cidr}")
        dev.cmd("end")

    capture = {name: probe(dev, name, cmds) for name, dev in bound.items()}

    if args.json:
        with open(args.json, "w") as f:
            json.dump(capture, f, indent=2)
        print(f"raw capture -> {args.json}")

    for name, out in capture.items():
        print(f"\n{'=' * 70}\n== {name}\n{'=' * 70}")
        shown = cmds if args.cmd else SUMMARY
        for c in shown:
            print(f"\n--- {c} ---\n{out.get(c, '')}")
        # Derived from what was actually SHOWN, so it cannot drift out of step with
        # COMMANDS the way a hardcoded count would -- and reports nothing left over
        # when --cmd already displayed everything.
        rest = [c for c in out if c not in shown]
        if rest:
            where = (f"saved to {args.json}" if args.json
                     else "DISCARDED -- pass --json FILE to keep them")
            print(f"\n--- {len(rest)} more command(s) captured, not shown above: "
                  f"{', '.join(rest)}\n    ({where})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

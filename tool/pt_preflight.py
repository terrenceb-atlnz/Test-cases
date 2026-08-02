#!/usr/bin/env python3
"""PyTest Creator — pre-flight topology check: can this script RUN on that bench?

A generated script is hardware-agnostic by design: it never names a port, and binds every
device and link from the `.setup` at runtime. The cost of that design is that a script can
be perfectly well-formed and still be un-runnable on a given bench, because the bench does
not declare a link the script asks for.

The framework fails that case QUIETLY. `Setup.init_portlink()` returns `(None, None)` when
no matching link exists (`sys.exit(2)` is reserved for fatal misconfig — a null device, a
tb-to-tb link, an unknown device, an invalid eth port name). Generated scripts unpack it
straight into port attributes:

    (dut.portA, lp.portA) = setup.init_portlink(dut, lp, type1='port', type2='port')

so both ends silently become `None` and the test proceeds to build CLI against `None`.
The run then fails in a way that reads as a SCRIPT defect when the real cause is bench
cabling — which is exactly the false signal Part 3b's criteria 5-6 must not be fed.

This check answers the question offline, before any hardware time is spent: no LLM, no
network, no testbox. It reads the script with `ast` and the bench file with `configparser`,
and reports every demand the bench cannot satisfy.

Two failure classes, both observed on the real tb470 bench (2026-07-30):

  LINK   the script asks for a data link between two devices that the `.setup` does not
         declare. Note that STACKPORT cabling is not a data path: two switches can be
         cabled into one stack and still have no `[portlink]` between them.
  POWER  the script power-cycles a device that has no `[powerlink]`, i.e. the device is
         not on a PDU outlet at all, so the power call has nothing to drive.

Usage:
  python3 tool/pt_preflight.py --setup /path/to/tb470.setup
  python3 tool/pt_preflight.py --setup tb470.setup --script ask-ck/pytest-create/generated/Port/x.py
  python3 tool/pt_preflight.py --setup tb470.setup --json

The bench file lives on the testbox, outside this repo. Copy it down first, e.g.
  scp tb470:/home/st-art/st-art/configs/tb470.setup /tmp/

Exit status: 0 = every script is runnable on that bench, 1 = at least one is not,
2 = bad invocation (unreadable setup/script, no scripts found).
"""
from __future__ import annotations

import argparse
import ast
import configparser
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SCRIPT_ROOT = REPO / "ask-ck" / "pytest-create" / "generated"

TB = "tb"  # the framework's reserved name for the testbox itself

# Framework binders the skeleton uses to acquire a device from the .setup.
BINDERS = {"init_swi": "switch", "init_stk": "stack", "init_tb": "tb"}

# Power-cycling shapes. A device that is not on a [powerlink] cannot honour these.
_POWER_ATTRS = frozenset({
    "power", "powerOn", "powerOff", "powerCycle", "power_cycle",
    "powerReset", "power_reset", "hardReboot", "hard_reboot",
})

# An interface's TYPE is its leading alphabetic run: eth3 -> eth, port1.0.23 -> port.
_IFACE_TYPE_RX = re.compile(r"^([A-Za-z]+)")


def iface_type(port: str) -> str:
    """'port1.0.23' -> 'port'; 'eth3' -> 'eth'; '' -> ''."""
    m = _IFACE_TYPE_RX.match((port or "").strip())
    return m.group(1).lower() if m else ""


# --------------------------------------------------------------------------- the bench


class Link:
    """One declared physical link between two devices, consumable exactly once.

    `init_portlink` looks up "a matching, NOT-YET-USED link", so N calls between the same
    pair of devices need N declared links. Modelling that is the difference between
    "declared once, asked for twice" passing and failing.
    """

    __slots__ = ("devA", "portA", "devB", "portB", "used", "raw")

    def __init__(self, devA: str, portA: str, devB: str, portB: str, raw: str):
        self.devA, self.portA, self.devB, self.portB, self.raw = devA, portA, devB, portB, raw
        self.used = False

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Link({self.devA}:{self.portA} <-> {self.devB}:{self.portB})"


class Bench:
    """The topology a `.setup` file declares."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.switches: Dict[str, str] = {}        # swi_a -> /dev/u4
        self.stacks: Dict[str, List[str]] = {}    # stk_a -> [swi_a, swi_b]
        self.links: List[Link] = []
        self.powerlinks: Dict[str, List[str]] = {}   # swi_c -> [pwr_c]
        self.power: Dict[str, str] = {}              # pwr_c -> '(pdu, 10.36.150.14, 8)'
        # [misc] is a free-form key/value area the framework already accepts (Setup.py
        # stores it verbatim, splitting comma values into a list). It is where a bench
        # declares which TOPOLOGY PROFILES it implements -- see tool/pt_profiles.py.
        self.misc: Dict[str, str] = {}
        self.warnings: List[str] = []

    # -- parsing ---------------------------------------------------------------

    @classmethod
    def from_text(cls, text: str, path: Optional[Path] = None) -> "Bench":
        b = cls(path)
        cp = configparser.ConfigParser(strict=False)
        # .setup keys are case-sensitive device names (swi_a, tb-swi_a); the default
        # optionxform lowercases, which is harmless today but would silently merge
        # swi_A/swi_a. Keep them verbatim.
        cp.optionxform = str  # type: ignore[assignment]
        cp.read_string(text)

        if cp.has_section("switch"):
            b.switches = {k: v.strip() for k, v in cp.items("switch")}
        if cp.has_section("stack"):
            for stk, members in cp.items("stack"):
                b.stacks[stk] = [m.strip() for m in members.split(",") if m.strip()]
        if cp.has_section("powerlink"):
            for dev, pwrs in cp.items("powerlink"):
                b.powerlinks[dev] = [p.strip() for p in pwrs.split(",") if p.strip()]
        if cp.has_section("power"):
            b.power = {k: v.strip() for k, v in cp.items("power")}
        if cp.has_section("misc"):
            b.misc = {k: v.strip() for k, v in cp.items("misc")}
        if cp.has_section("portlink"):
            for pair, ports in cp.items("portlink"):
                b._add_portlinks(pair, ports)
        return b

    def links_between(self, devA: str, devB: str) -> List[Link]:
        """Every declared link joining these two devices, in either orientation.

        Unlike take_link() this does NOT consume — it is the read-only query a profile
        conformance check needs (and mirrors the framework's own get_port_link vs
        init_portlink split).
        """
        return [l for l in self.links
                if (l.devA == devA and l.devB == devB) or (l.devA == devB and l.devB == devA)]

    @classmethod
    def from_path(cls, path: Path) -> "Bench":
        return cls.from_text(path.read_text(encoding="utf-8", errors="replace"), path)

    def _add_portlinks(self, pair: str, ports: str) -> None:
        """`swi_a-swi_c = port1.0.1-port1.0.1, port1.0.3-port1.0.2` -> two Links.

        Device names may themselves contain '-' only via the reserved `tb` prefix in
        practice, but split from the RIGHT on the LAST '-' is still wrong for the port
        side; both halves are split on the first '-' that yields two non-empty parts.
        """
        devA, devB = _split_pair(pair)
        if devA is None or devB is None:
            self.warnings.append(f"[portlink] key not understood, ignored: {pair!r}")
            return
        for chunk in ports.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            pA, pB = _split_pair(chunk)
            if pA is None or pB is None:
                self.warnings.append(
                    f"[portlink] {pair}: value {chunk!r} is not <portA>-<portB>, ignored")
                continue
            self.links.append(Link(devA, pA, devB, pB, raw=f"{pair} = {chunk}"))

    # -- queries ---------------------------------------------------------------

    def known(self, role: str) -> bool:
        return role == TB or role in self.switches or role in self.stacks

    def expand(self, role: str) -> List[str]:
        """A stack stands in for any of its members; anything else is itself.

        `init_portlink` expands a Stack device and tries each member combination, so a
        link declared to one member satisfies a demand against the stack.
        """
        return list(self.stacks.get(role, [role]))

    def stack_of(self, role: str) -> Optional[str]:
        for stk, members in self.stacks.items():
            if role in members:
                return stk
        return None

    def has_power(self, role: str) -> bool:
        """True if this device (or, for a stack, every member) can be power-cycled."""
        members = self.expand(role)
        return bool(members) and all(self.powerlinks.get(m) for m in members)

    def take_link(self, roleA: str, roleB: str, type1: str, type2: str) -> Optional[Link]:
        """Consume a declared link matching the demand, or return None.

        Order is not significant to `init_portlink` (the returned ports follow the call's
        argument order), so both orientations are tried; the type filters follow the
        arguments, not the declaration.
        """
        setA, setB = set(self.expand(roleA)), set(self.expand(roleB))
        for link in self.links:
            if link.used:
                continue
            forward = link.devA in setA and link.devB in setB
            reverse = link.devA in setB and link.devB in setA
            if forward and _types_ok(link.portA, link.portB, type1, type2):
                link.used = True
                return link
            if reverse and _types_ok(link.portB, link.portA, type1, type2):
                link.used = True
                return link
        return None


def _split_pair(s: str) -> Tuple[Optional[str], Optional[str]]:
    """Split `a-b` into ('a','b'), preferring the split that leaves both sides non-empty."""
    s = (s or "").strip()
    idx = s.find("-")
    while idx != -1:
        left, right = s[:idx].strip(), s[idx + 1:].strip()
        if left and right:
            return left, right
        idx = s.find("-", idx + 1)
    return None, None


def _types_ok(portForArg1: str, portForArg2: str, type1: str, type2: str) -> bool:
    """An empty type filter matches any interface (framework semantics)."""
    for want, port in ((type1, portForArg1), (type2, portForArg2)):
        if want and iface_type(port) != want.strip().lower():
            return False
    return True


# -------------------------------------------------------------------------- the script


class LinkDemand:
    __slots__ = ("roleA", "roleB", "type1", "type2", "line", "argA", "argB")

    def __init__(self, roleA, roleB, type1, type2, line, argA, argB):
        self.roleA, self.roleB = roleA, roleB
        self.type1, self.type2 = type1, type2
        self.line, self.argA, self.argB = line, argA, argB

    def call_text(self) -> str:
        extra = "".join(
            f", {k}={v!r}" for k, v in (("type1", self.type1), ("type2", self.type2)) if v)
        return f"init_portlink({self.argA}, {self.argB}{extra})"


class PowerDemand:
    __slots__ = ("role", "var", "attr", "line")

    def __init__(self, role, var, attr, line):
        self.role, self.var, self.attr, self.line = role, var, attr, line


class ScriptDemands:
    """What a generated script asks of whatever bench it lands on."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.bindings: Dict[str, str] = {}      # local var  -> .setup role
        self.roles: Dict[str, str] = {}         # role       -> binder kind
        self.links: List[LinkDemand] = []
        self.power: List[PowerDemand] = []
        self.warnings: List[str] = []


def _const_str(node: ast.AST) -> Optional[str]:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _binder_of(call: ast.Call) -> Optional[str]:
    """'setup.init_swi(...)' / 'init_swi(...)' -> 'init_swi'."""
    f = call.func
    name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
    return name if name in BINDERS or name == "init_portlink" else None


def _contract_role(call: ast.Call) -> Optional[str]:
    """Role from a TOPOLOGY-CONTRACT binding: `init_swi(misc.get('ck_role_dut', 'swi_a'))`.

    WHY THIS EXISTS
    ---------------
    Generation deliberately stopped naming devices (2026-07-30, TOPOLOGY-PROFILES.md): the DUT
    is resolved from the bench's own `[misc] ck_role_dut` at RUN time, so one script binds
    correctly on any bench that implements the roles. Preflight, written the same day, could
    only resolve a LITERAL role — so every script written to the new contract fell into the
    "non-literal role" branch, and with no device bound, every link demand against it became
    unresolvable.

    The damage was not just lost coverage: the verdict printed
    `VERDICT: UN-RUNNABLE (0/2 links satisfiable)`, which reads as a definite NO. The truth was
    "cannot determine". A confident wrong negative is worse than an admitted unknown here,
    because the whole purpose of this tool is to decide whether to spend bench time.

    Reading the literal DEFAULT is sound rather than a guess: the generated frame is fixed and
    always emits `misc.get('<key>', '<default>')`, and the default is the role name the
    contract specifies. `check_script` additionally prefers the bench's OWN value for the key
    when the `.setup` declares one, so a bench that renames its roles is still checked
    correctly.
    """
    f = call.args[0] if call.args else None
    if not isinstance(f, ast.Call):
        return None
    # ...get('ck_role_dut', 'swi_a')
    if not (isinstance(f.func, ast.Attribute) and f.func.attr == "get"):
        return None
    if len(f.args) < 2:
        return None
    key, default = _const_str(f.args[0]), _const_str(f.args[1])
    if not key or not key.startswith("ck_role_") or not default:
        return None
    return default


def parse_script(text: str, path: Optional[Path] = None) -> ScriptDemands:
    """Extract device bindings, link demands and power demands via AST.

    AST rather than regex because the whole point is to resolve the LOCAL VARIABLE back to
    the `.setup` ROLE it was bound from — `lp = setup.init_swi('swi_b')` then
    `init_portlink(dut, lp)` — and that indirection is what a textual scan cannot follow.
    """
    d = ScriptDemands(path)
    tree = ast.parse(text)

    # self.<attr> = <local>, so a demand written against self.dut resolves too.
    selfmap: Dict[str, str] = {}

    # Pass 1: bindings. Collected over the whole module, not just init(), because a
    # portlink bound outside init() has happened before and is still a real demand.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        binder = _binder_of(node.value)
        if binder is None or binder == "init_portlink":
            continue
        if binder == "init_tb":
            role = TB
        else:
            role = _const_str(node.value.args[0]) if node.value.args else None
            if role is None:
                role = _contract_role(node.value)
            if role is None:
                d.warnings.append(
                    f"line {node.lineno}: {binder}() called with a non-literal role — "
                    "cannot check statically")
                continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                d.bindings[tgt.id] = role
        d.roles[role] = BINDERS[binder]

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name)
                        and tgt.value.id == "self" and isinstance(node.value, ast.Name)):
                    selfmap[tgt.attr] = node.value.id

    def resolve(arg: ast.AST) -> Tuple[Optional[str], str]:
        """(role, printable) for a device argument."""
        if isinstance(arg, ast.Name):
            return d.bindings.get(arg.id), arg.id
        if (isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name)
                and arg.value.id == "self"):
            local = selfmap.get(arg.attr)
            text_ = f"self.{arg.attr}"
            return (d.bindings.get(local) if local else None), text_
        return None, ast.dump(arg)[:40]

    # Pass 2: demands.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _binder_of(node) == "init_portlink":
            if len(node.args) < 2:
                d.warnings.append(f"line {node.lineno}: init_portlink() with <2 positional args")
                continue
            roleA, argA = resolve(node.args[0])
            roleB, argB = resolve(node.args[1])
            kw = {k.arg: _const_str(k.value) or "" for k in node.keywords if k.arg}
            d.links.append(LinkDemand(roleA, roleB, kw.get("type1", ""), kw.get("type2", ""),
                                      node.lineno, argA, argB))

    # Power demands: `<dev>.powerCycle()` / `<dev>.power.off()` on a bound device.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or node.attr not in _POWER_ATTRS:
            continue
        role, printable = resolve(node.value)
        if role is not None:
            d.power.append(PowerDemand(role, printable, node.attr, node.lineno))

    return d


# ------------------------------------------------------------------------------ verdict


def check(script: ScriptDemands, bench: Bench) -> dict:
    """Match a script's demands against a bench. Pure; returns a report dict."""
    problems: List[dict] = []
    notes: List[str] = []
    devices: List[dict] = []

    for role, kind in sorted(script.roles.items()):
        if role == TB:
            devices.append({"role": TB, "kind": "tb", "ok": True, "detail": "the testbox itself"})
            continue
        if not bench.known(role):
            problems.append({
                "kind": "DEVICE", "role": role, "line": None,
                "message": f"script binds {role!r} but the bench declares no such device",
                "detail": "declared: " + (", ".join(sorted(bench.switches) + sorted(bench.stacks))
                                         or "(none)"),
            })
            devices.append({"role": role, "kind": kind, "ok": False, "detail": "NOT DECLARED"})
            continue
        stk = bench.stack_of(role)
        detail = bench.switches.get(role) or f"members: {', '.join(bench.stacks.get(role, []))}"
        if stk:
            detail += f"  (member of {stk})"
        devices.append({"role": role, "kind": kind, "ok": True, "detail": detail})

    # Links. Order matters: consumption is greedy, so walk demands in source order.
    for dem in sorted(script.links, key=lambda x: x.line):
        if dem.roleA is None or dem.roleB is None:
            unresolved = dem.argA if dem.roleA is None else dem.argB
            problems.append({
                "kind": "LINK", "role": None, "line": dem.line,
                "message": f"{dem.call_text()}: cannot resolve {unresolved!r} to a .setup role",
                "detail": "only devices bound via init_swi/init_stk/init_tb can be checked",
            })
            continue
        if not bench.known(dem.roleA) or not bench.known(dem.roleB):
            continue  # already reported as a DEVICE problem
        if bench.take_link(dem.roleA, dem.roleB, dem.type1, dem.type2) is not None:
            continue

        declared = [l.raw for l in bench.links]
        detail = (f"bench declares {len(declared)} portlink(s): " + "; ".join(declared)
                  if declared else "the bench declares NO [portlink] at all")
        extra = ""
        stkA, stkB = bench.stack_of(dem.roleA), bench.stack_of(dem.roleB)
        if stkA and stkA == stkB:
            extra = (f" NOTE: {dem.roleA} and {dem.roleB} are both members of {stkA} — "
                     "stackport cabling is NOT a data path and cannot satisfy a portlink.")
        elif any(not l.used for l in bench.links):
            extra = " (a link is declared but between other devices, or of another interface type)"
        problems.append({
            "kind": "LINK", "role": f"{dem.roleA}<->{dem.roleB}", "line": dem.line,
            "message": f"{dem.call_text()}: no matching data portlink between "
                       f"{dem.roleA} and {dem.roleB}",
            "detail": detail + extra,
            "consequence": "init_portlink() returns (None, None) SILENTLY — both port "
                           "attributes become None and the script builds CLI against None",
        })

    # Power.
    seen_power: Set[Tuple[str, int]] = set()
    for dem in sorted(script.power, key=lambda x: x.line):
        if not bench.known(dem.role) or (dem.role, dem.line) in seen_power:
            continue
        seen_power.add((dem.role, dem.line))
        if bench.has_power(dem.role):
            continue
        members = bench.expand(dem.role)
        missing = [m for m in members if not bench.powerlinks.get(m)]
        problems.append({
            "kind": "POWER", "role": dem.role, "line": dem.line,
            "message": f"{dem.var}.{dem.attr} power-cycles {dem.role}, which has no [powerlink]",
            "detail": f"no PDU outlet declared for: {', '.join(missing)} — "
                      f"[powerlink] declares: {', '.join(sorted(bench.powerlinks)) or '(none)'}",
            "consequence": "the device is not on a PDU, so it cannot be power-cycled on this "
                           "bench at all; reboot it over the CLI instead",
        })

    if script.warnings:
        notes.extend(script.warnings)
    if bench.warnings:
        notes.extend(bench.warnings)

    return {
        "script": str(script.path) if script.path else "<text>",
        "setup": str(bench.path) if bench.path else "<text>",
        "devices": devices,
        "problems": problems,
        "notes": notes,
        "runnable": not problems,
        "links_demanded": len(script.links),
        "links_unsatisfiable": sum(1 for p in problems if p["kind"] == "LINK"),
    }


# -------------------------------------------------------------------------------- CLI


def _render(rep: dict) -> str:
    out: List[str] = []
    name = Path(rep["script"]).name
    verdict = "RUNNABLE" if rep["runnable"] else "UN-RUNNABLE"
    out.append(f"{name}  vs  {Path(rep['setup']).name}")
    for dev in rep["devices"]:
        mark = "OK " if dev["ok"] else "!! "
        out.append(f"    {mark}{dev['role']:<7} {dev['detail']}")
    if rep["problems"]:
        out.append("")
    for p in rep["problems"]:
        loc = f"line {p['line']}" if p["line"] else "-"
        out.append(f"    !! {p['kind']}  ({loc})  {p['message']}")
        if p.get("detail"):
            out.append(f"         {p['detail']}")
        if p.get("consequence"):
            out.append(f"         -> {p['consequence']}")
    for n in rep["notes"]:
        out.append(f"    note: {n}")
    tail = ""
    if rep["links_demanded"]:
        tail = (f"  ({rep['links_demanded'] - rep['links_unsatisfiable']}"
                f"/{rep['links_demanded']} links satisfiable)")
    out.append(f"    VERDICT: {verdict}{tail}")
    return "\n".join(out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Check a generated script's topology demands against a bench .setup, "
                    "before spending hardware time on a run.")
    ap.add_argument("--setup", required=True, metavar="PATH",
                    help="the bench .setup file (copy it down from the testbox first)")
    ap.add_argument("--script", action="append", default=[], metavar="PATH",
                    help="a generated script; repeatable. Default: every .py under "
                         "ask-ck/pytest-create/generated/")
    ap.add_argument("--json", action="store_true", help="machine-readable report on stdout")
    ap.add_argument("--profile", action="append", default=[], metavar="NAME",
                    help="instead of checking scripts, check whether the bench IMPLEMENTS "
                         "this topology profile; repeatable. 'all' checks every known "
                         "profile. See tool/pt_profiles.py + TOPOLOGY-PROFILES.md")
    args = ap.parse_args(argv)

    setup_path = Path(args.setup)
    if not setup_path.is_file():
        print(f"error: no such .setup file: {setup_path}", file=sys.stderr)
        print("hint: scp tb470:/home/st-art/st-art/configs/tb470.setup /tmp/", file=sys.stderr)
        return 2

    if args.profile:
        # Profile conformance is a property of the BENCH alone — no scripts involved.
        from pt_profiles import PROFILES, check_profiles, declared_profiles  # noqa: PLC0415
        bench = Bench.from_path(setup_path)
        names = (sorted(PROFILES) if "all" in args.profile else args.profile)
        reports = check_profiles(bench, names)
        if args.json:
            print(json.dumps(reports, indent=2))
            return 0 if all(r["conformant"] for r in reports) else 1
        claimed = declared_profiles(bench)
        print(f"{setup_path.name} claims: {', '.join(claimed) or '(nothing)'}\n")
        for rep in reports:
            mark = "IMPLEMENTS" if rep["conformant"] else "DOES NOT IMPLEMENT"
            print(f"{mark}  {rep['profile']}")
            for c in rep["checks"]:
                print(f"    OK  {c['role']:<16} {c['detail']}")
            for p in rep["problems"]:
                print(f"    !!  {p['role'] or '-':<16} {p['message']}")
                if p.get("fix"):
                    print(f"        fix: {p['fix']}")
            print()
        ok = [r["profile"] for r in reports if r["conformant"]]
        print(f"{len(ok)}/{len(reports)} implemented" + (f": {', '.join(ok)}" if ok else ""))
        return 0 if len(ok) == len(reports) else 1

    scripts = [Path(s) for s in args.script] or sorted(DEFAULT_SCRIPT_ROOT.rglob("*.py"))
    missing = [s for s in scripts if not s.is_file()]
    if missing:
        for m in missing:
            print(f"error: no such script: {m}", file=sys.stderr)
        return 2
    if not scripts:
        print(f"error: no scripts found under {DEFAULT_SCRIPT_ROOT}", file=sys.stderr)
        return 2

    reports = []
    for s in scripts:
        # A fresh Bench per script: link consumption is per-run state, so reusing one
        # bench would let script #1's links "use up" script #2's.
        bench = Bench.from_path(setup_path)
        try:
            demands = parse_script(s.read_text(encoding="utf-8", errors="replace"), s)
        except SyntaxError as e:
            reports.append({
                "script": str(s), "setup": str(setup_path), "devices": [],
                "problems": [{"kind": "PARSE", "role": None, "line": e.lineno,
                              "message": f"script does not parse: {e.msg}", "detail": ""}],
                "notes": [], "runnable": False,
                "links_demanded": 0, "links_unsatisfiable": 0,
            })
            continue
        reports.append(check(demands, bench))

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for rep in reports:
            print(_render(rep))
            print()
        bad = [r for r in reports if not r["runnable"]]
        print(f"{len(reports) - len(bad)}/{len(reports)} runnable on {setup_path.name}")
        if bad:
            print("un-runnable: " + ", ".join(Path(r["script"]).name for r in bad))

    return 0 if all(r["runnable"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/python3
# Written independently by Claude (claude-fable-5-1) for AWPTCM-T33241 — (14) IPv4_Local Interfaces - Loopback Address
# Same frame as the Ask CK PyTest Creator (fixed TestSet.init discovery, one TestCase per sequence step,
# the logging contract in every main()); the device logic is Claude's own, from the sequence, the
# objective, the CLI reference in ck.db and the ART corpus. 2026-10-20, for comparison with the tool's output.
#
# ==== OBJECTIVE — expected results this script must demonstrate ====
#   - The device can have a local loopback address assigned to it, and that address is shown
#   in the device's interface and address information.
#   - The loopback address can be reached from the device itself.
#   - The loopback address stays reachable regardless of the state of the device's physical
#   links.
#   - The loopback address can be used as the source address for traffic the device sends.
#   - An address that is not valid for a loopback interface is refused, and the existing
#   configuration is left unchanged.
#   - Removing the loopback address really does remove it, so it is no longer shown and can
#   no longer be reached.
# ==================================================================

import sys
import time
import re
from framework import ATTestSet, ATTestCase
from framework.ATDrivers import ATTestBox   # isinstance(far_end, ATTestBox.TestBox) tells the testbox from a switch
from framework.ATPackets import *   # scapy (Ether, sendp, sniff) + the AT layers (lldp_*, IGMP, LACP, EPSR ...)
from scapy.all import AsyncSniffer, IP, ICMP


# ---------------------------------------------------------------------------------------
# Test data. Addresses are the script's own (RFC 1918, /30 for the point-to-point far end,
# /32 for the loopback) so the test depends on no bench addressing. Port names are never
# written here: every port comes from the frame's discovery.
# ---------------------------------------------------------------------------------------
LOOPBACK_ADDR = '172.31.241.1'          # the address under test, assigned to `interface lo`
LOOPBACK_PREFIX = 32
LOOPBACK_CIDR = '{}/{}'.format(LOOPBACK_ADDR, LOOPBACK_PREFIX)
FAR_VLAN = 3241                         # a VLAN of this test's own, on the DUT's testbox-link port
DUT_FAR_ADDR = '172.31.240.1'           # the DUT's address on that VLAN
TB_FAR_ADDR = '172.31.240.2'            # the testbox's address on the same /30
FAR_PREFIX = 30
PING_COUNT = 3

# Addresses no IPv4 host interface may carry, each with the RFC that says so. The DUT's own
# accept/reject decides each one; because these are invalid everywhere, an acceptance is a
# failure. Deliberately NOT listed: 127.0.0.1/8 (it IS the loopback address, so "invalid for a
# loopback interface" is arguable) and 240.0.0.1 (class E — Linux-based platforms accept it).
INVALID_ADDRESSES = (
    ('224.0.0.1/32', 'a multicast address (RFC 1112)'),
    ('255.255.255.255/32', 'the limited broadcast address (RFC 919 / RFC 1122)'),
    ('0.0.0.0/32', 'the unspecified "this host" address (RFC 1122 3.2.1.3)'),
    ('256.1.1.1/32', 'not an IPv4 address (octet above 255)'),
    ('{}/33'.format(DUT_FAR_ADDR), 'a prefix length longer than 32'),
)

# Filled by TestSet.configure() from the frame's discovery: every DUT-side data port the bench
# cables (the testbox link plus every partner link), never a stack port and never a literal.
DATA_PORTS = []
# The `ip address` lines `interface lo` carried BEFORE the suite (read once in
# TestSet.configure()), so clear_loopback() can leave lo exactly as the bench had it.
LO_ORIGINAL = []


# ---------------------------------------------------------------------------------------
# Helpers. Thin wrappers that drive the CLI and return values; none issues a verdict — the
# TestCases own the verdicts.
# ---------------------------------------------------------------------------------------

def cli_refused(output):
    """True when the CLI answered with an error line. AlliedWare Plus prefixes every parser and
    semantic refusal with '% ' ('% Invalid input detected at ...', '% Invalid address ...'), so
    the prefix is the one signal that holds across releases; the exact wording is not relied on."""
    for line in (output or '').splitlines():
        if line.strip().startswith('%'):
            return True
    return False


def lo_running_config(dut):
    """The `ip address` lines currently under `interface lo` in the running-config."""
    dut.mode('#')
    output = dut.cmd('show running-config interface lo')
    return [line.strip() for line in output.splitlines() if line.strip().startswith('ip address')]


def ip_brief_row(output, ifname):
    """The row of `show ip interface brief` whose FIRST token is `ifname`, or None."""
    for line in output.splitlines():
        if line.split()[:1] == [ifname]:
            return line
    return None


def ip_brief_addr(output, ifname):
    """The address column of that row, without any prefix length. Releases differ on whether
    the column carries `/prefix` (both forms are in the reference), so the host part alone is
    compared. 'unassigned' comes back as itself."""
    row = ip_brief_row(output, ifname)
    if row is None:
        return None
    tokens = row.split()
    return tokens[1].split('/')[0] if len(tokens) > 1 else None


def ping_counts(output):
    """(transmitted, received) parsed from the DUT's ping summary line
    `N packets transmitted, M received, ...`; (None, None) when no summary was printed
    (e.g. `connect: Network is unreachable`)."""
    match = re.search(r'(\d+)\s+packets transmitted,\s*(\d+)\s+received', output or '')
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def ping_from_dut(dut, target, source=None, count=PING_COUNT):
    """Run the DUT's own ping and return (transmitted, received, output)."""
    dut.mode('#')
    command = 'ping {} repeat {} timeout 2'.format(target, count)
    if source:
        command += ' source {}'.format(source)
    output = dut.cmd(command)
    sent, got = ping_counts(output)
    return sent, got, output


def port_status_row(dut, port):
    """The port's own row of `show interface <port> status` (first token == port.name)."""
    dut.mode('#')
    output = dut.cmd('show interface {} status'.format(port.name))
    for line in output.splitlines():
        if line.split()[:1] == [port.name]:
            return line
    return None


def wait_port_state(dut, port, want_connected, timeout=60, poll=2):
    """Poll the port's status row until it reads `connected` (or stops reading it). Returns the
    final row. The down-state token varies by release, so 'down' is the ABSENCE of `connected`."""
    deadline = time.time() + timeout
    row = None
    while time.time() < deadline:
        dut.mode('#')
        output = dut.cmd('show interface {} status'.format(port.name), log=False)
        row = next((line for line in output.splitlines() if line.split()[:1] == [port.name]), None)
        is_connected = row is not None and 'connected' in row.split()
        if is_connected == want_connected:
            return row
        time.sleep(poll)
    return row


def set_loopback(dut, cidr=LOOPBACK_CIDR):
    """Assign the test address to `interface lo`; returns the CLI's response to the command.
    `ip address` OVERWRITES a primary address (CLI reference), so a bench that already puts an
    address on lo is restored by clear_loopback() from what it read at suite start."""
    dut.mode(')#')
    dut.cmd('interface lo')
    response = dut.cmd('ip address {}'.format(cidr))
    dut.mode('#')
    return response


def clear_loopback(dut, original_lines):
    """Remove the test address from `interface lo` and put back whatever the bench had there, so
    the running-config matches the one the suite started from (confCheck)."""
    if LOOPBACK_CIDR in ' '.join(lo_running_config(dut)):
        dut.mode(')#')
        dut.cmd('interface lo')
        dut.cmd('no ip address {}'.format(LOOPBACK_CIDR))
    for line in original_lines:
        if line not in lo_running_config(dut):
            dut.mode(')#')
            dut.cmd('interface lo')
            dut.cmd(line)
    dut.mode('#')


def shutdown_ports(dut, ports, down):
    """`shutdown` (down=True) or `no shutdown` every port in `ports`, one interface at a time."""
    dut.mode(')#')
    for port in ports:
        dut.cmd('interface {}'.format(port.name))
        dut.cmd('shutdown' if down else 'no shutdown')
    dut.mode('#')


def setup_far_end(tb, dut, portA, ethA):
    """A point-to-point IPv4 path between the DUT and the testbox over the testbox link: the
    DUT's port in a VLAN of this test's own with an SVI address, the testbox NIC given the
    other address of the /30 as a secondary, and a host route back to the loopback so the
    testbox can answer a loopback-sourced ping. Returns True when the testbox commands ran."""
    dut.mode(')#')
    dut.cmd('vlan database')
    dut.cmd('vlan {}'.format(FAR_VLAN))
    dut.cmd('interface {}'.format(portA.name))
    dut.cmd('switchport access vlan {}'.format(FAR_VLAN))
    dut.cmd('interface vlan{}'.format(FAR_VLAN))
    dut.cmd('ip address {}/{}'.format(DUT_FAR_ADDR, FAR_PREFIX))
    dut.mode('#')
    ok = True
    for shell in ('ip addr add {}/{} dev {}'.format(TB_FAR_ADDR, FAR_PREFIX, ethA.name),
                  'ip route replace {}/{} via {} dev {}'.format(LOOPBACK_ADDR, LOOPBACK_PREFIX,
                                                                DUT_FAR_ADDR, ethA.name)):
        stdout, stderr = tb.cmd(shell)
        if stderr and 'File exists' not in stderr:
            ok = False
    return ok


def teardown_far_end(tb, dut, portA, ethA):
    """Undo setup_far_end() command for command, on both ends."""
    tb.cmd('ip route del {}/{} dev {}'.format(LOOPBACK_ADDR, LOOPBACK_PREFIX, ethA.name))
    tb.cmd('ip addr del {}/{} dev {}'.format(TB_FAR_ADDR, FAR_PREFIX, ethA.name))
    dut.mode(')#')
    dut.cmd('no interface vlan{}'.format(FAR_VLAN))
    dut.cmd('interface {}'.format(portA.name))
    dut.cmd('no switchport access vlan')
    dut.cmd('vlan database')
    dut.cmd('no vlan {}'.format(FAR_VLAN))
    dut.mode('#')


class TestSet(ATTestSet.TestSet):

    FEATURES = ['ALL']

    def _ck_discover(self, dut, unit=None):
        """Every data link on the DUT, classified by asking the DUT what is fitted in each port.

        `dut` is the switch handle commands go to; `unit` is what owns the ports — the STACK
        when the DUT is in one (its members' [portlink]s all count), else `dut` itself.

        Fixed frame — do not edit or delete. Nothing here is pre-declared (Terrence, 2026-09-21:
        "the information shouldn't require pre-loading variables to know it"). The cables come
        from the bench's own [portlink] section through `get_all_port_links()`; the testbox is
        the far end that is a TestBox; a member of the DUT's own stack is never a partner; and
        the MEDIA of each DUT-side port is read from `show interface <port> status` (its Type
        column) and `show system pluggable` (which cages hold a module). An EMPTY cage has no
        media and is no role — nothing is in it.
        Returns {bucket: [(near_port, far_port, far_device), ...]} for the buckets
        tb / copper (fixed twisted pair) / cusfp (twisted pair in a cage) / fibre / absent / unknown.
        """
        import ck_media
        unit = unit if unit is not None else dut
        members = set(unit.all_members()) if hasattr(unit, 'all_members') else set()
        in_cage = ck_media.pluggable_ports(dut.cmd('show system pluggable'))
        found = {'tb': [], 'copper': [], 'cusfp': [], 'fibre': [], 'absent': [], 'unknown': []}
        for far, pairs in unit.get_all_port_links().items():
            if far in members:
                continue                       # stackport / member cabling is not a data path
            for near, far_port in pairs:
                if isinstance(far, ATTestBox.TestBox):
                    found['tb'].append((near, far_port, far))
                    continue
                if not near.name.startswith('port'):
                    continue                   # an eth0 management link is not a data path
                status = dut.cmd('show interface %s status' % near.name)
                kind = ck_media.classify(ck_media.media_type(status, near.name))
                if kind == ck_media.TWISTED_PAIR:
                    bucket = 'cusfp' if ck_media.is_pluggable(near.name, in_cage) else 'copper'
                elif kind == ck_media.FIBRE:
                    bucket = 'fibre'
                elif kind == ck_media.ABSENT:
                    bucket = 'absent'
                else:
                    bucket = 'unknown'
                found[bucket].append((near, far_port, far))
        # Deterministic order, aggregator members LAST (tb470 sentinel, 2026-09-29):
        # get_all_port_links() walks Stack.members, a SET, so the same bench handed out a
        # different port run to run; and a port in a static-channel-group / channel-group is
        # an aggregator member, where a speed/duplex change on ONE member is an aggregator
        # artefact. Not skipped (the DUT decides; the tester may take the link out of its
        # aggregator for the run) - preferred against, and named in the log and at binding.
        self._ck_lag_ports = set()
        for v in found.values():
            for near, far_port, far in v:
                if near.name.startswith('port') and re.search(
                        r'^\s*(static-)?channel-group\b',
                        dut.cmd('show running-config interface %s' % near.name), re.M):
                    self._ck_lag_ports.add(near.name)

        def _natural(s):
            return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]

        def _order(link):
            near, far_port, far = link
            return (near.name in self._ck_lag_ports, _natural(near.name),
                    _natural(getattr(far, 'name', 'tb')), _natural(far_port.name))
        for v in found.values():
            v.sort(key=_order)
        self.log('topology discovered on %s: %s' % (dut.name, '; '.join(
            '%s=%s' % (k, ','.join('%s%s<->%s.%s' % (
                n.name, ' [LAG member]' if n.name in self._ck_lag_ports else '',
                getattr(f, 'name', 'tb'), p.name) for n, p, f in v))
            for k, v in found.items() if v) or 'NO data links declared'))
        return found

    def _ck_bind_link(self, setup, dut, role, optional=False):
        """Take ONE discovered link for `role` and bind it: (near_port, far_port, far_device).

        Fixed frame — do not edit or delete. `role` is what the TEST needs — 'tb', 'copper',
        'fibre', 'cusfp' — and the link is whichever discovered cable carries that media, so
        the same script binds on any bench cabled for it while the bench declares nothing
        beyond its [portlink]s. A link is never handed out twice; a copper role takes a copper
        SFP only when no fixed twisted-pair link is left; a partner switch is initialised once
        however many links go to it. A REQUIRED role with no link aborts the suite — "this
        bench cannot host this test" is a bench problem, not a test result. An OPTIONAL
        (pluggable) role returns (None, None, None) and the cases needing it report UNSUPPORTED.
        """
        import ck_media
        buckets = {'tb': ('tb',), 'copper': ('copper', 'cusfp'),
                   'cusfp': ('cusfp',), 'fibre': ('fibre',)}[role]
        for bucket in buckets:
            if not self._ck_topo.get(bucket):
                continue
            near, far_port, far = self._ck_topo[bucket].pop(0)
            if isinstance(far, ATTestBox.TestBox):
                # The testbox end of a data link: any fitted media serves a capture/inject
                # path, but an EMPTY cage on the DUT side is a bench problem — say so now.
                status = dut.cmd('show interface %s status' % near.name)
                ok, why = ck_media.assert_role_media(status, near.name, 'tb')
                if not ok:
                    raise RuntimeError(why)
            else:
                # `far` is the device init_all_devices() already initialised — re-initialising
                # it would build a second object (init_stk) or abort the run (init_tb).
                self._ck_far.setdefault(far.name, far)
                far = self._ck_far[far.name]
            self.log('topology: role %r -> %s %s <-> %s %s (%s)' % (
                role, dut.name, near.name, getattr(far, 'name', 'tb'), far_port.name, bucket))
            if near.name in getattr(self, '_ck_lag_ports', ()):
                self.log('WARNING: %s %s is an aggregator member (channel-group in its running-config): '
                         'a speed/duplex change on ONE member is an aggregator artefact, not a port '
                         'result - take it out of the aggregator for the run, or cable a standalone '
                         'link, before trusting this role' % (dut.name, near.name))
            return near, far_port, far
        have = ', '.join('%d %s' % (len(v), k) for k, v in self._ck_topo.items() if v) or 'none'
        why = ("BENCH PROBLEM, not a product defect: no unused %s link on %s (data links "
               "discovered: %s). Cable a %s partner port to the DUT and declare it under "
               "[portlink]." % (role, dut.name, have, role))
        if optional:
            self.log(why + ' This role is OPTIONAL here: the cases needing it report UNSUPPORTED.')
            return None, None, None
        raise RuntimeError(why)

    def init(self, setup):
        # Topology is DISCOVERED through the framework at run time, never declared to this
        # script: the DUT is the framework's `swi_a` slot (its stack, when it is in one), the
        # partners are whatever the bench's [portlink]s cable to it, and which link is copper
        # / fibre / copper-SFP is read from the DUT itself. So the script names no port and no
        # partner, binds correctly on any bench cabled for it, and fails loudly on one that is
        # not. (`swi_a`/`stk_a`: 297/192 corpus lookups; a role-named key appears 0 times.)
        # Every device and link the bench's .setup declares is initialised FIRST, by the
        # framework's own init_all_devices(): get_all_port_links() returns only INITIALISED links
        # and get_stack() is set only by init_stk, so a frame that bound swi_a alone discovered
        # NOTHING — its first hardware run, T33235 on tb470, 2026-09-25, aborted in init() with
        # "no unused copper link". powerOn=False: binding never switches a PDU outlet on (a
        # power-cycle test still has its power objects). tb and swi_a come from the returned
        # device table — init_tb() a second time exits the run.
        _devs = setup.init_all_devices(powerOn=False)
        tb = _devs['tb']
        swi_a = _devs['swi_a']
        # ART's own shape (103 of 239 suites bind BOTH the stack and the swi_a switch):
        # the STACK owns the ports [portlink] declares per member and is what discovery walks;
        # COMMANDS go to the swi_a member handle, which has cmd()/mode() — the framework's Stack
        # class defines neither, and every VCStack member serves the stack-wide CLI. (2026-09-21
        # to 2026-09-23 the frame rebound `swi_a` to the Stack, so every command died on a
        # stacked DUT; Terrence: "Copy what they do, because it works.")
        _stk = swi_a.get_stack()
        dut_stack = _stk                   # initialised above; init_stk() again builds a second Stack
        self.tb = tb
        self.swi_a = swi_a
        self.dut_stack = dut_stack
        self._ck_far = {}
        self._ck_topo = self._ck_discover(swi_a, dut_stack)
        # The TESTBOX data link: the ART shape `(dut.portA, tb.ethA)`. Captures, injected
        # frames and pings happen on `tb.ethA`; `swi_a.portA` is the DUT port under test
        # at the other end of that cable. REQUIRED: a bench without it aborts here.
        (swi_a.portA, tb.ethA, _tb) = self._ck_bind_link(setup, swi_a, 'tb')
        # This test needs NO neighbour switch: a loopback address is a property of the DUT alone.
        # The partner links the bench cables are still discovered (above) so that "regardless
        # of the state of the physical links" can act on every one of them, not only the
        # testbox link; nothing is bound beyond `portA`.

    def configure(self):
        tb = self.tb
        swi_a = self.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        # One-time SUITE setup, runs ONCE before all test cases. Config only — no pass/fail.
        # No device configuration here: every case sets up and removes its own, so each runs
        # alone (--include-test-cases) and confCheck sees the running-config it started with.
        # What IS established once is the list of the DUT's data ports, from the frame's own
        # discovery: the bound testbox link first, then every partner link the bench cables.
        del DATA_PORTS[:]
        DATA_PORTS.append(portA)
        for bucket in ('copper', 'cusfp', 'fibre', 'absent', 'unknown', 'tb'):
            for near, far_port, far in self._ck_topo.get(bucket, []):
                if near.name not in [p.name for p in DATA_PORTS]:
                    DATA_PORTS.append(near)
        self.log('physical data ports this suite will act on: {}'.format(
            ', '.join(p.name for p in DATA_PORTS)))
        # What `interface lo` carries BEFORE the test, so clear_loopback() can put it back.
        del LO_ORIGINAL[:]
        LO_ORIGINAL.extend(lo_running_config(swi_a))
        self.log('interface lo before the test: {}'.format(LO_ORIGINAL or 'no ip address'))
        swi_a.mode('#')

    def tear_down(self):
        tb = self.tb
        swi_a = self.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        # One-time SUITE cleanup, runs ONCE after all cases. No pass/fail.
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = ("Record the baseline: capture 'show running-config interface lo' and 'show ip interface brief' "
                    "(and 'show interface lo' if present) so later steps can compare for unchanged configuration. "
                    "Ensure the test loopback address is not already configured.")
    # ART identity <family>.<case>.<TestCase> — the framework composes the same triple
    # from the filename and this class name, and the run log prints it per case.
    testCaseRef = 'AWPTCM-T33241, 9002.33241.1'
    testCaseMethod = ("Record the baseline: capture 'show running-config interface lo' and 'show ip interface brief' "
                      "(and 'show interface lo' if present) so later steps can compare for unchanged configuration. "
                      "Ensure the test loopback address is not already configured.\n")
    testCaseMethod += ("Verify: Baseline output is captured and the loopback test address does not appear in the "
                       "interface/address output.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        # The precondition: the test address is not on `interface lo`.
        clear_loopback(swi_a, LO_ORIGINAL)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 1: Record the baseline: capture 'show running-config interface lo' and 'show ip interface "
                 "brief' (and 'show interface lo' if present) so later steps can compare for unchanged "
                 "configuration. Ensure the test loopback address is not already configured.")
        swi_a.mode('#')
        running = swi_a.cmd('show running-config interface lo')
        brief = swi_a.cmd('show ip interface brief')
        detail = swi_a.cmd('show interface lo')
        output = '\n'.join((running, brief, detail))
        self.log('OBSERVED: {}'.format(output))
        row = ip_brief_row(brief, 'lo')
        if row is None:
            self.failed("'show ip interface brief' has no row for lo - the loopback interface is not listed")
            return
        self.passed("baseline captured: 'show ip interface brief' lists lo as: {}".format(row.strip()))
        if LOOPBACK_ADDR in running or ip_brief_addr(brief, 'lo') == LOOPBACK_ADDR:
            self.failed('{} is already configured on lo before the test started: {}'.format(
                LOOPBACK_ADDR, [line for line in running.splitlines() if 'ip address' in line]))
        else:
            self.passed('{} is absent from the baseline running-config and address listing'.format(LOOPBACK_ADDR))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        swi_a.mode('#')


class TestCase_2(ATTestCase.TestCase):
    testCaseDesc = ("Enter configure mode, enter 'interface lo' and assign a valid loopback IPv4 address with "
                    "'ip address <loopback-addr>/32'. Exit to privileged mode.")
    testCaseRef = 'AWPTCM-T33241, 9002.33241.2'
    testCaseMethod = ("Enter configure mode, enter 'interface lo' and assign a valid loopback IPv4 address with "
                      "'ip address <loopback-addr>/32'. Exit to privileged mode.\n")
    testCaseMethod += ("Verify: The command is accepted with no CLI error indication (no '% Invalid input' or "
                       "similar message).\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 2: Enter configure mode, enter 'interface lo' and assign a valid loopback IPv4 address with "
                 "'ip address <loopback-addr>/32'. Exit to privileged mode.")
        response = set_loopback(swi_a)
        running = swi_a.cmd('show running-config interface lo')
        output = 'response to "ip address {}": {}\n{}'.format(LOOPBACK_CIDR, response.strip(), running)
        self.log('OBSERVED: {}'.format(output))
        if cli_refused(response):
            self.failed('the DUT refused "ip address {}" on interface lo: {}'.format(
                LOOPBACK_CIDR, response.strip()))
            return
        self.passed('"ip address {}" on interface lo was accepted with no CLI error line'.format(LOOPBACK_CIDR))
        if 'ip address {}'.format(LOOPBACK_CIDR) in running:
            self.passed('the running-config of interface lo now carries "ip address {}"'.format(LOOPBACK_CIDR))
        else:
            self.failed('the command was accepted but "ip address {}" is not in the running-config of lo: {}'.format(
                LOOPBACK_CIDR, running.strip()))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_3(ATTestCase.TestCase):
    testCaseDesc = "Read 'show ip interface brief' and 'show interface lo' (and 'show running-config interface lo')."
    testCaseRef = 'AWPTCM-T33241, 9002.33241.3'
    testCaseMethod = ("Read 'show ip interface brief' and 'show interface lo' (and 'show running-config interface "
                      "lo').\n")
    testCaseMethod += ("Verify: The loopback interface row/section lists the assigned loopback address; the interface "
                       "is shown as up/operational; running-config for the loopback contains the 'ip address' line.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 3: Read 'show ip interface brief' and 'show interface lo' "
                 "(and 'show running-config interface lo').")
        swi_a.mode('#')
        brief = swi_a.cmd('show ip interface brief')
        detail = swi_a.cmd('show interface lo')
        running = swi_a.cmd('show running-config interface lo')
        output = '\n'.join((brief, detail, running))
        self.log('OBSERVED: {}'.format(output))
        row = ip_brief_row(brief, 'lo')
        if row is None:
            self.failed("'show ip interface brief' has no row for lo")
            return
        if ip_brief_addr(brief, 'lo') == LOOPBACK_ADDR:
            self.passed("'show ip interface brief' lists {} on lo: {}".format(LOOPBACK_ADDR, row.strip()))
        else:
            self.failed("'show ip interface brief' shows lo as {!r}, expected {}".format(
                ip_brief_addr(brief, 'lo'), LOOPBACK_ADDR))
        # Status and Protocol are the last two columns of the row (`admin up` / `running`).
        if 'running' in row.split() and 'up' in row.split():
            self.passed('lo is reported admin up and running: {}'.format(row.strip()))
        else:
            self.failed('lo is not reported up/running: {}'.format(row.strip()))
        if LOOPBACK_ADDR in detail:
            self.passed("'show interface lo' shows the address {}".format(LOOPBACK_ADDR))
        else:
            self.failed("'show interface lo' does not mention {}: {}".format(LOOPBACK_ADDR, detail.strip()))
        if 'ip address {}'.format(LOOPBACK_CIDR) in running:
            self.passed('the running-config of lo carries "ip address {}"'.format(LOOPBACK_CIDR))
        else:
            self.failed('the running-config of lo lacks "ip address {}": {}'.format(LOOPBACK_CIDR, running.strip()))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_4(ATTestCase.TestCase):
    testCaseDesc = "From the DUT CLI, run 'ping <loopback-addr>' (a few packets)."
    testCaseRef = 'AWPTCM-T33241, 9002.33241.4'
    testCaseMethod = "From the DUT CLI, run 'ping <loopback-addr>' (a few packets).\n"
    testCaseMethod += 'Verify: Ping output shows replies received from the loopback address with 0% packet loss.\n'

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 4: From the DUT CLI, run 'ping <loopback-addr>' (a few packets).")
        sent, got, output = ping_from_dut(swi_a, LOOPBACK_ADDR)
        self.log('OBSERVED: {}'.format(output))
        if sent is None:
            self.failed('the DUT printed no ping summary for {}: {}'.format(LOOPBACK_ADDR, output.strip()))
        elif got == sent and got > 0:
            self.passed('{} of {} echo requests to {} were answered (0% loss)'.format(got, sent, LOOPBACK_ADDR))
        else:
            self.failed('only {} of {} echo requests to {} were answered'.format(got, sent, LOOPBACK_ADDR))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_5(ATTestCase.TestCase):
    testCaseDesc = ("Record the physical-link-bearing ports from the .setup file's [portlink] section (the test "
                    "port, the partner port and any other linked ports). On each, issue 'shutdown' one at a time; "
                    "after each port is shut down, read 'show interface <port> status' and ping the loopback address "
                    "from the DUT.")
    testCaseRef = 'AWPTCM-T33241, 9002.33241.5'
    testCaseMethod = ("Record the physical-link-bearing ports from the .setup file's [portlink] section (the test "
                      "port, the partner port and any other linked ports). On each, issue 'shutdown' one at a time; "
                      "after each port is shut down, read 'show interface <port> status' and ping the loopback "
                      "address from the DUT.\n")
    testCaseMethod += ("Verify: For each shutdown port, its status row does NOT read 'connected'. After every "
                       "individual shutdown the ping to the loopback address still receives replies with 0% loss and "
                       "'show ip interface brief' still lists the loopback address.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 5: Record the physical-link-bearing ports from the .setup file's [portlink] section (the test "
                 "port, the partner port and any other linked ports). On each, issue 'shutdown' one at a time; after "
                 "each port is shut down, read 'show interface <port> status' and ping the loopback address from the "
                 "DUT.")
        self.log('physical data ports (from the frame\'s discovery, not the .setup text): {}'.format(
            ', '.join(p.name for p in DATA_PORTS)))
        observed = []
        for port in DATA_PORTS:
            shutdown_ports(swi_a, [port], down=True)
            row = wait_port_state(swi_a, port, want_connected=False, timeout=30)
            sent, got, ping_out = ping_from_dut(swi_a, LOOPBACK_ADDR)
            brief = swi_a.cmd('show ip interface brief')
            observed.append('after shutdown of {}: status row {!r}; ping {}/{}; lo row {!r}'.format(
                port.name, row, got, sent, ip_brief_row(brief, 'lo')))
            if row is None:
                self.failed('{} has no row in show interface status after shutdown'.format(port.name))
            elif 'connected' not in row.split():
                self.passed('{} no longer reads connected after shutdown: {}'.format(port.name, row.strip()))
            else:
                self.failed('{} still reads connected after shutdown: {}'.format(port.name, row.strip()))
            if sent and got == sent:
                self.passed('with {} down, {} still answers {} of {} echo requests'.format(
                    port.name, LOOPBACK_ADDR, got, sent))
            else:
                self.failed('with {} down, {} answered {} of {} echo requests'.format(
                    port.name, LOOPBACK_ADDR, got, sent))
            if ip_brief_addr(brief, 'lo') == LOOPBACK_ADDR:
                self.passed("with {} down, 'show ip interface brief' still lists {} on lo".format(
                    port.name, LOOPBACK_ADDR))
            else:
                self.failed("with {} down, 'show ip interface brief' shows lo as {!r}".format(
                    port.name, ip_brief_addr(brief, 'lo')))
        output = '\n'.join(observed)
        self.log('OBSERVED: {}'.format(output))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        shutdown_ports(swi_a, DATA_PORTS, down=False)
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_6(ATTestCase.TestCase):
    testCaseDesc = ("With ALL linked ports now shut down, confirm none shows 'connected' in 'show interface status' "
                    "(match each row by its first token being the port name), then ping the loopback address from the "
                    "DUT and read 'show interface lo'.")
    testCaseRef = 'AWPTCM-T33241, 9002.33241.6'
    testCaseMethod = ("With ALL linked ports now shut down, confirm none shows 'connected' in 'show interface status' "
                      "(match each row by its first token being the port name), then ping the loopback address from "
                      "the DUT and read 'show interface lo'.\n")
    testCaseMethod += ("Verify: No port row reads 'connected'. Ping to the loopback address still gets replies with 0% "
                       "loss and the loopback address is still listed in the interface/address information.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)
        shutdown_ports(swi_a, DATA_PORTS, down=True)
        for port in DATA_PORTS:
            wait_port_state(swi_a, port, want_connected=False, timeout=30)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 6: With ALL linked ports now shut down, confirm none shows 'connected' in 'show interface "
                 "status' (match each row by its first token being the port name), then ping the loopback address "
                 "from the DUT and read 'show interface lo'.")
        swi_a.mode('#')
        status = swi_a.cmd('show interface status')
        sent, got, ping_out = ping_from_dut(swi_a, LOOPBACK_ADDR)
        detail = swi_a.cmd('show interface lo')
        brief = swi_a.cmd('show ip interface brief')
        output = '\n'.join((status, ping_out, detail))
        self.log('OBSERVED: {}'.format(output))
        still_up = []
        missing = []
        for port in DATA_PORTS:
            row = next((line for line in status.splitlines() if line.split()[:1] == [port.name]), None)
            if row is None:
                missing.append(port.name)
            elif 'connected' in row.split():
                still_up.append(row.strip())
        if missing:
            self.failed("ports missing from 'show interface status': {}".format(', '.join(missing)))
        elif still_up:
            self.failed('ports still reading connected with every data port shut down: {}'.format(still_up))
        else:
            self.passed('none of {} reads connected'.format(', '.join(p.name for p in DATA_PORTS)))
        if sent and got == sent:
            self.passed('with every physical link down, {} still answers {} of {} echo requests'.format(
                LOOPBACK_ADDR, got, sent))
        else:
            self.failed('with every physical link down, {} answered {} of {} echo requests'.format(
                LOOPBACK_ADDR, got, sent))
        if ip_brief_addr(brief, 'lo') == LOOPBACK_ADDR and LOOPBACK_ADDR in detail:
            self.passed('{} is still listed on lo in both the brief and the detailed interface output'.format(
                LOOPBACK_ADDR))
        else:
            self.failed('{} is no longer listed on lo (brief: {!r}; detail mentions it: {})'.format(
                LOOPBACK_ADDR, ip_brief_addr(brief, 'lo'), LOOPBACK_ADDR in detail))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        shutdown_ports(swi_a, DATA_PORTS, down=False)
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_7(ATTestCase.TestCase):
    testCaseDesc = ("Restore the links: issue 'no shutdown' on every port shut down in the previous steps, wait for "
                    "the test port link to come up, then ping the loopback address again.")
    testCaseRef = 'AWPTCM-T33241, 9002.33241.7'
    testCaseMethod = ("Restore the links: issue 'no shutdown' on every port shut down in the previous steps, wait for "
                      "the test port link to come up, then ping the loopback address again.\n")
    testCaseMethod += ("Verify: The test port's status row reads 'connected' again; ping to the loopback address still "
                       "succeeds with 0% loss and the address is still shown.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)
        shutdown_ports(swi_a, DATA_PORTS, down=True)
        for port in DATA_PORTS:
            wait_port_state(swi_a, port, want_connected=False, timeout=30)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 7: Restore the links: issue 'no shutdown' on every port shut down in the previous steps, wait "
                 "for the test port link to come up, then ping the loopback address again.")
        shutdown_ports(swi_a, DATA_PORTS, down=False)
        row = wait_port_state(swi_a, portA, want_connected=True, timeout=90)
        sent, got, ping_out = ping_from_dut(swi_a, LOOPBACK_ADDR)
        brief = swi_a.cmd('show ip interface brief')
        output = 'test port {} status row: {!r}\n{}\n{}'.format(portA.name, row, ping_out, brief)
        self.log('OBSERVED: {}'.format(output))
        if row is not None and 'connected' in row.split():
            self.passed('{} reads connected again after no shutdown: {}'.format(portA.name, row.strip()))
        else:
            self.failed('{} did not return to connected within 90 s after no shutdown: {!r}'.format(portA.name, row))
        if sent and got == sent:
            self.passed('with the links restored, {} answers {} of {} echo requests'.format(LOOPBACK_ADDR, got, sent))
        else:
            self.failed('with the links restored, {} answered {} of {} echo requests'.format(LOOPBACK_ADDR, got, sent))
        if ip_brief_addr(brief, 'lo') == LOOPBACK_ADDR:
            self.passed("'show ip interface brief' still lists {} on lo".format(LOOPBACK_ADDR))
        else:
            self.failed("'show ip interface brief' shows lo as {!r}".format(ip_brief_addr(brief, 'lo')))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        shutdown_ports(swi_a, DATA_PORTS, down=False)
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_8(ATTestCase.TestCase):
    testCaseDesc = ("Configure the partner (over its own CLI) or the traffic-capture host with an address in the "
                    "same reachability path as the DUT test port, and ensure the DUT has a route/connected interface "
                    "to it. Start tcpdump/Scapy sniffing on the partner-side capture interface for ICMP echo requests "
                    "from the loopback address.")
    testCaseRef = 'AWPTCM-T33241, 9002.33241.8'
    testCaseMethod = ("Configure the partner (over its own CLI) or the traffic-capture host with an address in the "
                      "same reachability path as the DUT test port, and ensure the DUT has a route/connected "
                      "interface to it. Start tcpdump/Scapy sniffing on the partner-side capture interface for ICMP "
                      "echo requests from the loopback address.\n")
    testCaseMethod += ("Verify: The DUT can reach the far-end address (plain ping from the DUT to the far-end address "
                       "succeeds) and the capture is running.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)
        setup_far_end(tb, swi_a, portA, ethA)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 8: Configure the partner (over its own CLI) or the traffic-capture host with an address in the "
                 "same reachability path as the DUT test port, and ensure the DUT has a route/connected interface to "
                 "it. Start tcpdump/Scapy sniffing on the partner-side capture interface for ICMP echo requests from "
                 "the loopback address.")
        # The far end here is the TESTBOX on the bound testbox link (ethA), addressed in
        # configure(): a /30 between the DUT's SVI and the testbox NIC, plus a host route back to
        # the loopback on the testbox. The capture itself is exercised in STEP 9; this step proves
        # the path and that a sniffer on ethA can start and stop.
        swi_a.mode('#')
        row = wait_port_state(swi_a, portA, want_connected=True, timeout=60)
        brief = swi_a.cmd('show ip interface brief')
        sent, got, ping_out = ping_from_dut(swi_a, TB_FAR_ADDR)
        tb_out, tb_err = tb.cmd('ip -4 addr show dev {}; ip route show {}/{}'.format(
            ethA.name, LOOPBACK_ADDR, LOOPBACK_PREFIX))
        sniffer = AsyncSniffer(iface=ethA.name, filter='icmp', store=True)
        sniffer.start()
        time.sleep(1)
        sniffer_running = bool(getattr(sniffer, 'running', False))
        sniffer.stop()
        output = 'test port {} status row: {!r}\n{}\n{}\ntestbox {}: {}'.format(
            portA.name, row, brief, ping_out, ethA.name, tb_out)
        self.log('OBSERVED: {}'.format(output))
        if ip_brief_addr(brief, 'vlan{}'.format(FAR_VLAN)) != DUT_FAR_ADDR:
            self.failed('the DUT did not take {}/{} on interface vlan{}: {!r}'.format(
                DUT_FAR_ADDR, FAR_PREFIX, FAR_VLAN, ip_brief_row(brief, 'vlan{}'.format(FAR_VLAN))))
            return
        self.passed('the DUT reports {} on interface vlan{}'.format(DUT_FAR_ADDR, FAR_VLAN))
        if sent and got == sent:
            self.passed('the DUT reaches the far end {} over {}: {} of {} echo requests answered'.format(
                TB_FAR_ADDR, portA.name, got, sent))
        else:
            self.failed('the DUT cannot reach the far end {} over {} ({} of {} answered). If {} is a trunk port on '
                        'this bench, its access VLAN is inactive and this is a bench-config finding, not a product '
                        'defect.'.format(TB_FAR_ADDR, portA.name, got, sent, portA.name))
        if sniffer_running:
            self.passed('a packet capture on testbox interface {} starts and stops'.format(ethA.name))
        else:
            self.failed('a packet capture on testbox interface {} could not be started'.format(ethA.name))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        teardown_far_end(tb, swi_a, portA, ethA)
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_9(ATTestCase.TestCase):
    testCaseDesc = "On the DUT, run 'ping <far-end-addr> source <loopback-addr>' (a few packets)."
    testCaseRef = 'AWPTCM-T33241, 9002.33241.9'
    testCaseMethod = "On the DUT, run 'ping <far-end-addr> source <loopback-addr>' (a few packets).\n"
    testCaseMethod += ("Verify: The capture at the far end shows ICMP echo request packets whose IPv4 source address "
                       "equals the loopback address and whose destination is the far-end address. (If the far end has "
                       "a return route to the loopback, echo replies are also seen; the source-address check is the "
                       "pass criterion.)\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)
        setup_far_end(tb, swi_a, portA, ethA)
        wait_port_state(swi_a, portA, want_connected=True, timeout=60)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 9: On the DUT, run 'ping <far-end-addr> source <loopback-addr>' (a few packets).")
        sniffer = AsyncSniffer(iface=ethA.name, filter='icmp and host {}'.format(LOOPBACK_ADDR), store=True)
        sniffer.start()
        time.sleep(1)
        sent, got, ping_out = ping_from_dut(swi_a, TB_FAR_ADDR, source=LOOPBACK_ADDR)
        time.sleep(1)
        packets = sniffer.stop() or []
        requests = [p for p in packets if IP in p and ICMP in p and p[ICMP].type == 8
                    and p[IP].src == LOOPBACK_ADDR and p[IP].dst == TB_FAR_ADDR]
        replies = [p for p in packets if IP in p and ICMP in p and p[ICMP].type == 0
                   and p[IP].src == TB_FAR_ADDR and p[IP].dst == LOOPBACK_ADDR]
        other_src = sorted({p[IP].src for p in packets if IP in p and ICMP in p and p[ICMP].type == 8
                            and p[IP].src != LOOPBACK_ADDR})
        output = ('{}\ncaptured on {}: {} ICMP packets; {} echo requests {} -> {}; {} echo replies back; '
                  'echo requests from other sources: {}'.format(
                      ping_out, ethA.name, len(packets), len(requests), LOOPBACK_ADDR, TB_FAR_ADDR,
                      len(replies), other_src))
        self.log('OBSERVED: {}'.format(output))
        if cli_refused(ping_out):
            self.failed('the DUT refused "ping {} source {}": {}'.format(TB_FAR_ADDR, LOOPBACK_ADDR, ping_out.strip()))
            return
        if requests:
            self.passed('{} echo request(s) arrived at the far end with source address {} (the loopback) and '
                        'destination {}'.format(len(requests), LOOPBACK_ADDR, TB_FAR_ADDR))
        else:
            self.failed('no echo request with source {} reached {} on {} ({} ICMP packets captured, other '
                        'sources: {})'.format(LOOPBACK_ADDR, TB_FAR_ADDR, ethA.name, len(packets), other_src))
        # Replies depend on the far end's route back to the loopback (added by configure()); they
        # are reported as supporting evidence, and the request check above is the verdict.
        if replies and got:
            self.passed('the far end answered: {} echo replies to {}, and the DUT counted {} of {} received'.format(
                len(replies), LOOPBACK_ADDR, got, sent))
        else:
            self.log('INFO: no echo replies to {} were seen (the far end may lack a route back to the loopback); '
                     'not a failure of the source-address check'.format(LOOPBACK_ADDR))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        teardown_far_end(tb, swi_a, portA, ethA)
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_10(ATTestCase.TestCase):
    testCaseDesc = ("Attempt to assign each of these invalid addresses on the loopback interface, one entry per "
                    "attempt, capturing the CLI response after each: (a) a multicast address 224.0.0.1/32, (b) the "
                    "limited broadcast 255.255.255.255/32, (c) the 0.0.0.0/32 address, (d) the 127.0.0.1/8 reserved "
                    "loopback-range address, (e) a class E address 240.0.0.1/32. After each attempt run 'show "
                    "running-config interface lo' and 'show ip interface brief'. Publish nothing; each attempt is its "
                    "own check of rejection.")
    testCaseRef = 'AWPTCM-T33241, 9002.33241.10'
    testCaseMethod = ("Attempt to assign each of these invalid addresses on the loopback interface, one entry per "
                      "attempt, capturing the CLI response after each: (a) a multicast address 224.0.0.1/32, (b) the "
                      "limited broadcast 255.255.255.255/32, (c) the 0.0.0.0/32 address, (d) the 127.0.0.1/8 reserved "
                      "loopback-range address, (e) a class E address 240.0.0.1/32. After each attempt run 'show "
                      "running-config interface lo' and 'show ip interface brief'. Publish nothing; each attempt is "
                      "its own check of rejection.\n")
    testCaseMethod += ("Verify: Each attempt is refused with a CLI error indication (e.g. '% Invalid input' or an "
                       "address-invalid message) as decided by the DUT; after each, the running-config for the "
                       "loopback and the address listing are identical to the state after step 3, with the valid "
                       "loopback address still present and the rejected address absent.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 10: Attempt to assign each of these invalid addresses on the loopback interface, one entry per "
                 "attempt, capturing the CLI response after each. After each attempt run 'show running-config "
                 "interface lo' and 'show ip interface brief'. Each attempt is its own check of rejection.")
        # The list differs from the sequence's (a)-(e) on purpose: 127.0.0.1/8 and 240.0.0.1/32 are
        # dropped as not clearly invalid for a loopback, and two malformed forms are added. See
        # INVALID_ADDRESSES for the reasons.
        swi_a.mode('#')
        before_running = lo_running_config(swi_a)
        before_brief = ip_brief_row(swi_a.cmd('show ip interface brief'), 'lo')
        observed = ['before: lo running-config {}; brief row {!r}'.format(before_running, before_brief)]
        for cidr, why in INVALID_ADDRESSES:
            response = set_loopback(swi_a, cidr)
            after_running = lo_running_config(swi_a)
            after_brief = ip_brief_row(swi_a.cmd('show ip interface brief'), 'lo')
            observed.append('attempt {!r} ({}): response {!r}; lo running-config {}; brief row {!r}'.format(
                cidr, why, response.strip(), after_running, after_brief))
            if cli_refused(response):
                self.passed('{} ({}) was refused by the DUT: {}'.format(cidr, why, response.strip()))
            else:
                self.failed('{} ({}) was NOT refused by the DUT (no error line): {!r}'.format(
                    cidr, why, response.strip()))
            if after_running == before_running and after_brief == before_brief:
                self.passed('after the {} attempt the lo running-config and address row are unchanged, with {} '
                            'still present'.format(cidr, LOOPBACK_ADDR))
            else:
                self.failed('after the {} attempt the lo configuration changed: running-config {} -> {}, brief row '
                            '{!r} -> {!r}'.format(cidr, before_running, after_running, before_brief, after_brief))
                # Put the valid address back so the next attempt starts from the same state.
                set_loopback(swi_a)
        output = '\n'.join(observed)
        self.log('OBSERVED: {}'.format(output))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_11(ATTestCase.TestCase):
    testCaseDesc = 'Ping the valid loopback address once more from the DUT after the rejected attempts.'
    testCaseRef = 'AWPTCM-T33241, 9002.33241.11'
    testCaseMethod = 'Ping the valid loopback address once more from the DUT after the rejected attempts.\n'
    testCaseMethod += ('Verify: Ping still receives replies with 0% loss, showing the existing configuration was '
                       'left unchanged.\n')

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)
        # The rejected attempts this step follows, replayed so the step stands on its own.
        for cidr, why in INVALID_ADDRESSES:
            set_loopback(swi_a, cidr)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log('STEP 11: Ping the valid loopback address once more from the DUT after the rejected attempts.')
        running = lo_running_config(swi_a)
        sent, got, output = ping_from_dut(swi_a, LOOPBACK_ADDR)
        self.log('OBSERVED: lo running-config {}\n{}'.format(running, output))
        if 'ip address {}'.format(LOOPBACK_CIDR) in running:
            self.passed('after the rejected attempts the running-config of lo still carries {}'.format(LOOPBACK_CIDR))
        else:
            self.failed('after the rejected attempts {} is gone from the running-config of lo: {}'.format(
                LOOPBACK_CIDR, running))
        if sent and got == sent:
            self.passed('{} still answers {} of {} echo requests after the rejected attempts'.format(
                LOOPBACK_ADDR, got, sent))
        else:
            self.failed('{} answered {} of {} echo requests after the rejected attempts'.format(
                LOOPBACK_ADDR, got, sent))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_12(ATTestCase.TestCase):
    testCaseDesc = ("Enter 'interface lo' and remove the loopback address with 'no ip address <loopback-addr>/32' (or "
                    "'no ip address'), then exit to privileged mode.")
    testCaseRef = 'AWPTCM-T33241, 9002.33241.12'
    testCaseMethod = ("Enter 'interface lo' and remove the loopback address with 'no ip address <loopback-addr>/32' "
                      "(or 'no ip address'), then exit to privileged mode.\n")
    testCaseMethod += 'Verify: The command is accepted with no CLI error indication.\n'

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 12: Enter 'interface lo' and remove the loopback address with 'no ip address "
                 "<loopback-addr>/32' (or 'no ip address'), then exit to privileged mode.")
        swi_a.mode(')#')
        swi_a.cmd('interface lo')
        response = swi_a.cmd('no ip address {}'.format(LOOPBACK_CIDR))
        swi_a.mode('#')
        running = swi_a.cmd('show running-config interface lo')
        output = 'response to "no ip address {}": {}\n{}'.format(LOOPBACK_CIDR, response.strip(), running)
        self.log('OBSERVED: {}'.format(output))
        if cli_refused(response):
            self.failed('the DUT refused "no ip address {}" on interface lo: {}'.format(
                LOOPBACK_CIDR, response.strip()))
            return
        self.passed('"no ip address {}" on interface lo was accepted with no CLI error line'.format(LOOPBACK_CIDR))
        if 'ip address {}'.format(LOOPBACK_CIDR) in running:
            self.failed('the removal was accepted but "ip address {}" is still in the running-config of lo'.format(
                LOOPBACK_CIDR))
        else:
            self.passed('"ip address {}" is gone from the running-config of lo'.format(LOOPBACK_CIDR))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_13(ATTestCase.TestCase):
    testCaseDesc = "Read 'show ip interface brief', 'show interface lo' and 'show running-config interface lo'."
    testCaseRef = 'AWPTCM-T33241, 9002.33241.13'
    testCaseMethod = "Read 'show ip interface brief', 'show interface lo' and 'show running-config interface lo'.\n"
    testCaseMethod += ("Verify: The removed loopback address no longer appears in any of the outputs and the "
                       "running-config has no 'ip address' line for it.\n")

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        # The state this step presumes: the address was assigned and then removed.
        set_loopback(swi_a)
        clear_loopback(swi_a, LO_ORIGINAL)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 13: Read 'show ip interface brief', 'show interface lo' and 'show running-config interface lo'.")
        swi_a.mode('#')
        brief = swi_a.cmd('show ip interface brief')
        detail = swi_a.cmd('show interface lo')
        running = swi_a.cmd('show running-config interface lo')
        output = '\n'.join((brief, detail, running))
        self.log('OBSERVED: {}'.format(output))
        if ip_brief_addr(brief, 'lo') == LOOPBACK_ADDR:
            self.failed("'show ip interface brief' still lists {} on lo after removal".format(LOOPBACK_ADDR))
        else:
            self.passed("'show ip interface brief' no longer lists {} on lo (row: {!r})".format(
                LOOPBACK_ADDR, ip_brief_row(brief, 'lo')))
        if LOOPBACK_ADDR in detail:
            self.failed("'show interface lo' still mentions {} after removal".format(LOOPBACK_ADDR))
        else:
            self.passed("'show interface lo' no longer mentions {}".format(LOOPBACK_ADDR))
        if 'ip address {}'.format(LOOPBACK_CIDR) in running:
            self.failed('the running-config of lo still carries "ip address {}" after removal'.format(LOOPBACK_CIDR))
        else:
            self.passed('the running-config of lo has no "ip address {}" line'.format(LOOPBACK_CIDR))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


class TestCase_14(ATTestCase.TestCase):
    testCaseDesc = "From the DUT CLI, run 'ping <loopback-addr>' (a few packets)."
    testCaseRef = 'AWPTCM-T33241, 9002.33241.14'
    testCaseMethod = "From the DUT CLI, run 'ping <loopback-addr>' (a few packets).\n"
    testCaseMethod += ('Verify: Ping gets no replies (100% packet loss or an unreachable indication) from the removed '
                       'loopback address.\n')

    def configure(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        set_loopback(swi_a)
        clear_loopback(swi_a, LO_ORIGINAL)

    def main(self):
        # AI claude-fable-5-1 2026-10-20
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        self.log("STEP 14: From the DUT CLI, run 'ping <loopback-addr>' (a few packets) after it was removed.")
        sent, got, output = ping_from_dut(swi_a, LOOPBACK_ADDR)
        self.log('OBSERVED: {}'.format(output))
        if sent is None:
            # No summary line: the DUT reported the address unreachable before sending anything.
            self.passed('the DUT reports {} unreachable after removal: {}'.format(
                LOOPBACK_ADDR, output.strip().splitlines()[-1] if output.strip() else 'no output'))
        elif got == 0:
            self.passed('no reply from {} after removal ({} sent, 0 received)'.format(LOOPBACK_ADDR, sent))
        else:
            self.failed('{} still answers after removal: {} of {} echo requests received'.format(
                LOOPBACK_ADDR, got, sent))

    def tear_down(self):
        tb = self.testSet.tb
        swi_a = self.testSet.swi_a
        ethA = tb.ethA
        portA = swi_a.portA
        clear_loopback(swi_a, LO_ORIGINAL)


if __name__ == '__main__':
    ts = TestSet()
    ts.add_testCase(TestCase_1())
    ts.add_testCase(TestCase_2())
    ts.add_testCase(TestCase_3())
    ts.add_testCase(TestCase_4())
    ts.add_testCase(TestCase_5())
    ts.add_testCase(TestCase_6())
    ts.add_testCase(TestCase_7())
    ts.add_testCase(TestCase_8())
    ts.add_testCase(TestCase_9())
    ts.add_testCase(TestCase_10())
    ts.add_testCase(TestCase_11())
    ts.add_testCase(TestCase_12())
    ts.add_testCase(TestCase_13())
    ts.add_testCase(TestCase_14())
    ts.run(sys.argv)

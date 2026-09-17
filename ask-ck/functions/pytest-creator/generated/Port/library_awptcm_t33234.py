#!/usr/bin/python3
# Helper library for AWPTCM-T33234 — Port - Auto MDI/MDI-X
#
# Shipped beside test-9000.33234.py. Every helper here is a thin, well-behaved
# wrapper around the ART device handle: it drives the CLI, parses the output and
# returns a boolean or a value. None of them issue pass/fail verdicts — the
# TestCases own the verdicts.

import re
import time


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

# 'show interface <port>' on AlliedWare Plus prints, for a copper port, lines of
# the form:
#
#   configured duplex auto, configured speed auto, configured polarity auto
#   current duplex full, current speed 1000, current polarity mdix
#
# Both the "configured" and the "current" families are matched with an EXACT
# token so that 'mdix' can never satisfy an 'mdi' test.

_CONFIGURED_RE = {
    'duplex': re.compile(r'configured\s+duplex\s+(\S+?)[,\s]', re.I),
    'speed': re.compile(r'configured\s+speed\s+(\S+?)[,\s]', re.I),
    'polarity': re.compile(r'configured\s+polarity\s+(\S+?)[,\s]', re.I),
}

_CURRENT_RE = {
    'duplex': re.compile(r'current\s+duplex\s+(\S+?)[,\s]', re.I),
    'speed': re.compile(r'current\s+speed\s+(\S+?)[,\s]', re.I),
    'polarity': re.compile(r'current\s+polarity\s+(\S+?)[,\s]', re.I),
}

_LINK_STATES = ('connected', 'notconnect', 'disabled', 'err-disabled',
                'monitoring', 'faulty', 'inactive')

_PARSER_ERRORS = (
    '% Invalid input detected',
    'Invalid input detected',
    '% Incomplete command',
    'Incomplete command',
    '% Unrecognized command',
    'Unrecognized command',
    '% Ambiguous command',
    'Ambiguous command',
    '% Unknown command',
    'Unknown command',
    "Can't find interface",
)


def _field(output, table, name):
    """Return the named field's exact token from a show interface body."""
    if not output:
        return None
    # Append a sentinel so a value that ends the line still matches the
    # `[,\s]` terminator in the patterns above.
    match = table[name].search(output + '\n')
    if not match:
        return None
    return match.group(1).strip().rstrip(',').lower()


def getConfiguredValue(output, name):
    """'configured duplex|speed|polarity' token, or None if not presented."""
    return _field(output, _CONFIGURED_RE, name)


def getCurrentValue(output, name):
    """'current duplex|speed|polarity' token, or None if not presented."""
    return _field(output, _CURRENT_RE, name)


def getStatusRow(output, portName):
    """The single 'show interface <port> status' row belonging to portName."""
    for line in (output or '').splitlines():
        tokens = line.split()
        if tokens[:1] == [portName]:
            return line
    return None


def getLinkState(output, portName):
    """'connected' / 'notconnect' / ... parsed from the port's status row."""
    row = getStatusRow(output, portName)
    if row is None:
        return None
    for token in row.split():
        if token.lower() in _LINK_STATES:
            return token.lower()
    return None


def checkInvalidCmd(output):
    """Return True when the CLI parser rejected the command.

    Kept as a query, not an assertion: the caller decides whether a rejection
    is a defect (a valid command refused) or the expected outcome (an invalid
    command properly refused).
    """
    if output is None:
        return False
    return any(marker in output for marker in _PARSER_ERRORS)


# ---------------------------------------------------------------------------
# Device interaction
# ---------------------------------------------------------------------------

def configurePort(testCase, device, port, setting, value, settle=0):
    """Apply '<setting> <value>' under 'interface <port>'.

    Returns True when the CLI accepted the command AND the configured value
    reads back as `value`. `settle` is an optional extra wait in seconds after
    the command, for callers that want the link to re-negotiate before they
    read the operational state.
    """
    device.mode(')#')
    device.cmd('interface {}'.format(port.name))
    response = device.cmd('{} {}'.format(setting, value))
    device.mode('#')

    if checkInvalidCmd(response):
        testCase.log('configurePort: {} rejected "{} {}" on {}: {}'.format(
            getattr(device, 'name', device), setting, value, port.name, response.strip()))
        return False

    if settle:
        time.sleep(settle)
    else:
        # A minimal settle so the read-back below reflects the applied value.
        time.sleep(1)

    body = device.cmd('show interface {}'.format(port.name))
    readback = getConfiguredValue(body, setting)
    if readback is None:
        # The platform does not present this field for this media. The command
        # was accepted, which is all this helper can honestly report.
        testCase.log('configurePort: {} does not present a "configured {}" field for {}; '
                     'command accepted.'.format(getattr(device, 'name', device), setting, port.name))
        return True

    if readback == str(value).lower():
        return True

    testCase.log('configurePort: {} {} configured {} reads {!r}, expected {!r}'.format(
        getattr(device, 'name', device), port.name, setting, readback, str(value).lower()))
    return False


def configureDefaultPort(testCase, device, port):
    """Return a port to its factory default speed/duplex/polarity and enable it.

    `no speed` / `no duplex` / `no polarity` are the documented negations. The
    commands are issued unconditionally; a platform that does not implement
    `polarity` on the given media simply refuses that one line, which is logged
    and not treated as a helper failure — the caller's own verify decides what
    the refusal means.
    """
    if port is None:
        return False
    device.mode(')#')
    device.cmd('interface {}'.format(port.name))
    for cmd in ('no speed', 'no duplex', 'no polarity', 'no shutdown'):
        response = device.cmd(cmd)
        if checkInvalidCmd(response):
            testCase.log('configureDefaultPort: "{}" refused on {} {}: {}'.format(
                cmd, getattr(device, 'name', device), port.name, response.strip()))
    device.mode('#')
    return True


def checkConfiguredPort(testCase, device, port, duplex, speed, polarity, expect_value=True):
    """True when 'show interface <port>' reports the configured triple given.

    Comparison is on EXACT tokens, so 'mdix' never satisfies 'mdi'. A field the
    platform does not present is reported and treated as a mismatch when a value
    was expected.
    """
    device.mode('#')
    body = device.cmd('show interface {}'.format(port.name))
    wanted = {'duplex': duplex, 'speed': speed, 'polarity': polarity}
    ok = True
    for name, want in wanted.items():
        if want is None:
            continue
        got = getConfiguredValue(body, name)
        if got != str(want).lower():
            testCase.log('checkConfiguredPort: {} {} configured {} is {!r}, expected {!r}'.format(
                getattr(device, 'name', device), port.name, name, got, str(want).lower()))
            ok = False
    return ok if expect_value else not ok


def checkCurrentPort(testCase, device, port, speed, duplex, polarity):
    """True when 'show interface <port>' reports the current/operational triple.

    'auto' is not an operational value: where the caller passes 'auto' for speed
    or duplex the field is only required to be PRESENT (the link negotiated
    something), not to equal the literal string 'auto'.
    """
    device.mode('#')
    body = device.cmd('show interface {}'.format(port.name))
    ok = True
    for name, want in (('speed', speed), ('duplex', duplex), ('polarity', polarity)):
        if want is None:
            continue
        got = getCurrentValue(body, name)
        if str(want).lower() == 'auto':
            if got is None:
                testCase.log('checkCurrentPort: {} {} presents no current {} while the caller '
                             'expected a negotiated value'.format(
                                 getattr(device, 'name', device), port.name, name))
                ok = False
            continue
        if got != str(want).lower():
            testCase.log('checkCurrentPort: {} {} current {} is {!r}, expected {!r}'.format(
                getattr(device, 'name', device), port.name, name, got, str(want).lower()))
            ok = False
    return ok


def checkLinkStatus(testCase, device, port, wanted):
    """True when the port's link state matches `wanted`.

    Accepts the ART spellings used across the legacy suites: 'running' / 'up' /
    'connected' all mean the port row reads 'connected'.
    """
    device.mode('#')
    output = device.cmd('show interface {} status'.format(port.name))
    state = getLinkState(output, port.name)
    want = str(wanted).lower()
    if want in ('running', 'up', 'connected'):
        return state == 'connected'
    if want in ('down', 'notconnect', 'not connected'):
        return state is not None and state != 'connected'
    return state == want


def waitForLinkState(testCase, device, port, wanted, timeout=60, poll=2):
    """Poll 'show interface <port> status' until the state matches, or time out.

    Returns True on match. Used instead of a bare sleep so that a slow
    auto-negotiation is waited for rather than mis-reported as a defect.
    """
    deadline = time.time() + timeout
    state = None
    while time.time() < deadline:
        device.mode('#')
        output = device.cmd('show interface {} status'.format(port.name), log=False)
        state = getLinkState(output, port.name)
        want = str(wanted).lower()
        if want in ('running', 'up', 'connected'):
            if state == 'connected':
                return True
        elif want in ('down', 'notconnect', 'not connected'):
            if state is not None and state != 'connected':
                return True
        elif state == want:
            return True
        time.sleep(poll)
    testCase.log('waitForLinkState: {} {} is {!r} after {}s, expected {!r}'.format(
        getattr(device, 'name', device), port.name, state, timeout, wanted))
    return False


def checkPortStatusVerify(device, portName, unused='', timeoutMs=60000, pingTimeout=0, poll=2):
    """Legacy-shaped wrapper: wait for `portName` to read 'connected'.

    Returns (elapsed_ms, final_row). elapsed_ms is >= timeoutMs when the port
    never reached 'connected', which is how the legacy callers detect timeout.
    """
    deadline = time.time() + (timeoutMs / 1000.0)
    started = time.time()
    row = None
    while time.time() < deadline:
        device.mode('#')
        output = device.cmd('show interface {} status'.format(portName), log=False)
        row = getStatusRow(output, portName)
        if row is not None and getLinkState(output, portName) == 'connected':
            return int((time.time() - started) * 1000), row
        time.sleep(poll)
    return int(max(timeoutMs, (time.time() - started) * 1000)), row


def yesNo(prompt):
    """Ask the operator a yes/no question on the console.

    Returns True only for an explicit affirmative. An EOF (a run with no
    operator attached) returns False so the calling case fails loudly on a
    missing physical precondition rather than silently assuming it holds.
    """
    question = '{} [y/n]: '.format(prompt)
    while True:
        try:
            answer = input(question)
        except (EOFError, KeyboardInterrupt):
            return False
        answer = (answer or '').strip().lower()
        if answer in ('y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False
        print("Please answer 'y' or 'n'.")

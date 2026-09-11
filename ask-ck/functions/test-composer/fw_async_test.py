#!/usr/bin/env python3
"""Regression test: does the FRAMEWORK console driver survive async log chatter?

WHY THIS IS KEPT. `orient-ie520` §3 names the framework driver (AWPConsoleCore
via `Setup.LoadSetup`) as the single sanctioned way to drive a device, and
retires the campaign-local `console.py` drivers. That decision rests on ONE
measured claim: that unsolicited log output does not break the framework's
command completion. This is the test that established it, kept so a framework
upgrade cannot silently invalidate the guidance. If this starts failing, §3 is
wrong and the legacy drivers had a reason to exist after all.

THE CLAIM IT REFUTED. `console.py`'s docstring asserts the framework decides a
command is finished by testing whether the LAST line of drained output ends in
'#', so log messages -- which on a stack can splice straight onto the prompt --
make a healthy session look hung.

MEASURED 2026-09-02 on tb470 stk_a, formed stack, 24 commands/phase, external
chatter CONFIRMED (14 external log lines, distinct session PIDs + systemd
session churn):

    phase A  terminal no monitor        median 0.41 s  max  0.42 s   0/24 fail
    phase B  terminal monitor + chatter median 0.42 s  max 45.18 s   4/24 FAIL

Four commands ran the full 45 s maxWait and raised `Infinite Loop Detected`
(which is only the flat wall-clock timeout, never a diagnosis). The
`kickInterval = 10.0` recovery (AWPConsoleCore.py:819 -- on 10 s of silence the
framework writes ' \n' to kick a fresh prompt) fires ~4x inside that window and
DOES NOT rescue it.

==> console.py's prompt-after-echo completion (`cmd_fast`) is LOAD-BEARING, not
    an optimisation. The framework driver stays the default for quiet-console
    work -- it was flawless there -- but anything needing `terminal monitor` on
    must not use it.

!! THIS REVERSED AN EARLIER RUN THE SAME DAY, and the reason is the whole point
   of the self_echo/external split in classify(). That run reported ZERO
   failures and "the framework survives". It was INVALID: the bench had split
   into two standalone units ~20 min earlier, so the generator on the other
   console could not log to the unit under test, and the 26 "chatter" lines
   counted were the DUT's OWN keystroke echoes:
       awplus#11:06:46 awplus IMISH[15790]: [manager@ttyS0]terminal no monitor
   Self-echo arrives BEFORE the prompt and the framework copes; genuine
   external output arrives at arbitrary times, including after the prompt, and
   that is what breaks completion. A raw log-line count cannot distinguish
   them, so this test counts them SEPARATELY and reports PARTIAL, never a pass,
   when the external count is zero. Always confirm a FORMED stack first
   (`show stack` -> Normal operation, both members Ready): two standalone units
   cannot log to each other, and the test then silently measures nothing.

STILL NOT COVERED, so do not claim it: the no-prompt/wedge discrimination path
beyond the raise observed here, and config-mode keystroke-echo splicing.

USAGE -- run ON the testbox, from a fresh dated dir (the framework writes its
console logs into cwd), with the load generator started first:

    ln -sfn /home/st-art/framework framework
    python3 ./fw_async_chatter.py /dev/u5 420 &        # the OTHER console
    PYTHONPATH=/home/st-art python3 ./fw_async_test.py \
        -s /home/st-art/st-art/configs/tb470.setup --tty /dev/u4 -n 12

The load generator is a deliberately INDEPENDENT pyserial loop, not the
framework driver: a load generator built on the driver under test could mask a
driver bug with the same bug. It needs no sudo (the tty nodes are world-
writable) and touches no config.

READ-ONLY: every command is a `show`, plus the session-scoped `terminal monitor`
toggle, restored in a finally. `powerOn=False` -- never touch the PDU on a
shared bench.

!! A PASS IS ONLY VALID IF CHATTER ACTUALLY ARRIVED. If no log lines are seen in
   phase B the console was quiet, the condition under test never occurred, and
   the verdict is INCONCLUSIVE -- not a pass (orient-ie520 §4, "a pass
   predicated on absence-of-evidence").
"""
import argparse
import glob
import re
import statistics
import time

from framework.Setup import LoadSetup

# 'awplus NSM[742]:', 'awplus IMISH[1234]:' -- a process[pid]: stamp is the
# signature of an AW+ log line, and cannot occur in `show clock` output.
LOG_LINE_RE = re.compile(r'\w+\[\d+\]:')
CMDS = ["show clock", "show stack"] * 3   # overridden by -n
MAXWAIT = 45.0


def console_of(dev, want_tty=None):
    """Pick the member to drive -- DETERMINISTICALLY.

    `Stack.members` is a SET, so "any member" is nondeterministic and can hand
    back the console another process is already holding. Two processes on one
    serial port produce 'device disconnected or multiple access on port?',
    which reads exactly like a hardware fault. The chatter generator owns the
    other console, so the member under test must be pinned by tty.
    """
    if hasattr(dev, "cmd") and want_tty is None:
        return dev
    cands = [dev] if hasattr(dev, "cmd") else []
    cands += [m for m in (getattr(dev, "members", ()) or ()) if hasattr(m, "cmd")]
    if want_tty:
        for m in cands:
            if str(getattr(m, "tty", "")) == want_tty:
                print("driving member pinned to {}".format(want_tty))
                return m
        raise RuntimeError("no bound member on {} (saw: {})".format(
            want_tty, [str(getattr(m, "tty", "?")) for m in cands]))
    if not cands:
        raise RuntimeError("no console on {!r}".format(dev))
    return cands[0]


def classify(out, command):
    """Split observed log lines into SELF-ECHO and EXTERNAL.

    This exists because the first run of this test was invalidated by assuming
    its load generator was working. With `terminal monitor` on, the device logs
    OUR OWN keystrokes straight back at us --
        awplus#11:06:46 awplus IMISH[15790]: [manager@ttyS0]show clock
    -- so a command that merely echoes itself produces a log line that looks
    exactly like external chatter in a raw count. A self-echo line contains the
    command text we just sent; genuine external chatter does not. Counting them
    together let a run with a DEAD generator report 26 log lines and read as a
    successful test of external chatter. Never re-merge these counters.
    """
    self_echo = external = 0
    for line in (out or "").splitlines():
        if not LOG_LINE_RE.search(line):
            continue
        if command.strip() and command.strip() in line:
            self_echo += 1
        else:
            external += 1
    return self_echo, external


def run_phase(dev, label):
    rows = []
    for c in CMDS:
        t0 = time.monotonic()
        try:
            out = dev.cmd(c, maxWait=MAXWAIT)
            err = None
        except BaseException as e:          # SystemExit is NOT an Exception
            out, err = "", "{}: {}".format(type(e).__name__, e)
        dt = time.monotonic() - t0
        se, ext = classify(out, c)
        rows.append((c, dt, se, ext, err, out))
        print("  {:<12} {:6.2f}s  self_echo={} EXTERNAL={}{}".format(
            c, dt, se, ext, "  ERR " + err if err else ""))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--setup", required=True)
    ap.add_argument("--stack", default="stk_a")
    ap.add_argument("--tty", default="/dev/u4",
                    help="pin the member under test to this console")
    ap.add_argument("-n", type=int, default=3,
                    help="repeats of the (show clock, show stack) pair per phase")
    args = ap.parse_args()

    global CMDS
    CMDS = ["show clock", "show stack"] * args.n

    setup = LoadSetup(args.setup)
    stk = setup.init_stk(args.stack, powerOn=False)
    dev = console_of(stk, want_tty=args.tty)

    dev.console.mode("#")
    # Prove the supported opt-out works: raise instead of sys.exit(2), so a
    # console failure here is catchable evidence rather than a dead process.
    dev.exception_on_exit()

    try:
        print("\n=== PHASE A: terminal NO monitor (quiet console) ===")
        dev.cmd("terminal no monitor", maxWait=20)
        a = run_phase(dev, "A")

        print("\n=== PHASE B: terminal monitor ON (+ external chatter) ===")
        dev.cmd("terminal monitor", maxWait=20)
        b = run_phase(dev, "B")
    finally:
        try:
            dev.cmd("terminal no monitor", maxWait=20)
        finally:
            dev.no_exception_on_exit()

    a_t = [r[1] for r in a]
    b_t = [r[1] for r in b]
    b_self = sum(r[2] for r in b)
    b_ext = sum(r[3] for r in b)
    b_hits = b_self + b_ext

    # Second, independent evidence source: the framework's own console log.
    fw_hits = 0
    for f in glob.glob("*.log"):
        try:
            with open(f, "rb") as fh:
                fw_hits += len(LOG_LINE_RE.findall(
                    fh.read().replace(b"\x00", b"").decode("utf-8", "replace")))
        except OSError:
            pass

    print("\n" + "=" * 62)
    print("phase A  median {:.2f}s  max {:.2f}s".format(
        statistics.median(a_t), max(a_t)))
    print("phase B  median {:.2f}s  max {:.2f}s".format(
        statistics.median(b_t), max(b_t)))
    print("phase-B log lines, SELF-ECHO (our own keystrokes) : {}".format(b_self))
    print("phase-B log lines, EXTERNAL (the load generator)   : {}".format(b_ext))
    print("log lines anywhere in framework console logs  : {}".format(fw_hits))
    print("maxWait ceiling was {:.0f}s".format(MAXWAIT))

    timed_out = [r for r in b if r[1] >= MAXWAIT * 0.9]
    errs = [r for r in b if r[4]]
    if b_hits == 0 and fw_hits == 0:
        print("\nVERDICT: INCONCLUSIVE -- no async log output ever arrived, so "
              "the condition under test did not occur. NOT a pass.")
    elif b_ext == 0:
        print("\nVERDICT: PARTIAL -- only SELF-ECHO splicing was exercised; the "
              "load generator contributed nothing, so EXTERNAL async chatter is "
              "still untested. Check the generator is running against a FORMED "
              "stack (two standalone units cannot log to each other).")
    elif timed_out or errs:
        print("\nVERDICT: FRAMEWORK DRIVER FAILS under async chatter "
              "({} timed out, {} errored) -- console.py's reason to exist "
              "is REAL.".format(len(timed_out), len(errs)))
    else:
        print("\nVERDICT: FRAMEWORK DRIVER SURVIVES async chatter -- commands "
              "completed normally with log lines interleaved.")


if __name__ == "__main__":
    main()

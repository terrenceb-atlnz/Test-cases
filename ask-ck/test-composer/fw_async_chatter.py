#!/usr/bin/env python3
"""Async-log LOAD GENERATOR for fw_async_test.py. Not a device driver.

Repeatedly logs in and out on a console, which AW+ logs -- so a *different*
console with `terminal monitor` on prints those log lines asynchronously. That
is the exact condition fw_async_test.py measures the framework driver against.

WHY THIS IS STANDALONE PYSERIAL, when orient-ie520 §3 says to use the framework
driver for everything. Two reasons, both deliberate:

  1. A load generator built on the driver under test can mask a bug in that
     driver with the same bug. The generator must be independent of the thing
     being measured, or the measurement proves nothing.
  2. This does not "drive a device" in the sense §3 governs -- it produces log
     traffic. It reads no state and makes no assertions, so none of the
     framework's value (setup binding, prompt handling, media awareness) is
     relevant, and none of its behaviour can be mistaken for the DUT's.

It is therefore the one sanctioned exception, and it stays under 60 lines on
purpose. Do NOT grow it into a general console tool -- that is how the drift
§3 retired started.

NON-MUTATING: no `configure terminal`, no shut/no-shut. The hammer campaign
generated chatter with `shutdown` on port1.0.27, but on this bench 27/28 are
live STACKPORTS, so that is off the table.

    python3 ./fw_async_chatter.py /dev/u5 420        # port, seconds

Needs no sudo (the tty nodes are world-writable). Credentials default to the
public AlliedWare Plus defaults, the same pair the framework tries first.
"""
import argparse
import os
import time

import serial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("seconds", type=float)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--user", default="manager")
    ap.add_argument("--password", default="friend")
    args = ap.parse_args()

    # Opening the port drops DTR, which the IE520 reads as a BREAK -- that can
    # park a unit in the bootloader. Clearing HUPCL stops the drop on close.
    os.system("stty -F {} -hupcl 2>/dev/null".format(os.path.realpath(args.port)))

    deadline = time.time() + args.seconds
    cycles = 0
    with serial.Serial(args.port, args.baud, timeout=0.4) as s, \
            open("chatter-{}.log".format(os.path.basename(args.port)), "a",
                 buffering=1, errors="replace") as t:
        while time.time() < deadline:
            for send in ("\r", args.user + "\r", args.password + "\r", "exit\r"):
                s.write(send.encode())
                time.sleep(0.6)
                t.write(s.read(4096).decode(errors="replace"))
            cycles += 1
            time.sleep(0.5)
    print("chatter: {} login/logout cycles".format(cycles), flush=True)


if __name__ == "__main__":
    main()

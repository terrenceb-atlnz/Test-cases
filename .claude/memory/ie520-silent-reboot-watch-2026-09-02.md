---
name: ie520-silent-reboot-watch-2026-09-02
description: "The IE520 silent-reboot console watch (2026-09-02/03) caught one reboot with good evidence, but its watcher script is GONE and three harness defects cap what it proved — read before the deferred weekend re-run"
metadata:
  node_type: memory
  type: project
  verified: 2026-09-03
---

**Deferred, not abandoned.** Terrence, 2026-09-03: *"we will re-engage with that for an
over-the-weekend run at a later time"*. This memory exists so the next run starts from the
findings instead of re-deriving them.

Evidence lives in `~/testbox_home/old test runs/IE520/random-reboot/` — two console watchers,
one per console, **2026-09-02 14:50:13 → 2026-09-03 06:00:19** (15 h 10 m), both ended at the
**scheduled** stop (`[WATCH_END]`), not a crash. Per console: `.run.log`, `.events.jsonl`,
`.transcript.log` (15 MB / 12 MB raw), baseline/final/logfilter, and u5's `.post-reboot.txt`.

## What it proved

One reboot in the window: **member 1 (u5, S/N 264A23066) at 2026-09-02 21:41:05**. Member 2
(u4, 264A23052) had **zero** — so do not describe this as a both-members result.

**"Silent" is now measured, not assumed.** Between the last command sent (`show log permanent`,
echoed 21:38:54) and `BootROM 1.41` the transcript holds **nothing** — no panic, no oops, no
watchdog banner, no AW+ error. A live CLI straight to BootROM.

**It wedged ~2 min BEFORE it reset** — the useful signature, recovered from the permanent log:

```
21:39:06 kern.alert   tipc: No contact from member-1 for 2000ms (3/6 probes timed out)
21:39:08 kern.warning tipc: Member-1 not responding - resetting link from member-2 to peer
21:41:02 kern.warning boardinfo: loading out-of-tree module taints kernel   <- already rebooting
```

The boot was captured in full: `U-Boot 2025.01-04844-gd2292467da4d` / `Bootloader 9.1.0 loaded`
/ netboot `tftp://10.38.215.33/IE520-tb470.rel` 41,107,895 bytes / kernel
`Created: 2026-08-30 23:47:03 UTC` — i.e. it returned on the **same build as member 2**, which is
why that reboot did **not** split the stack. See [[ie520-release-naming-and-drift]].

Not implicated: the reboot followed a `show log permanent`, but u4 polled that same command
**229 times without rebooting**.

## Fix these three before re-running — each caps what the run can prove

1. **65-minute detection lag, with counters claiming health.** Reboot 21:41, `[REBOOT_MARKER]`
   only at 22:46:31. From 21:42 `lines` was frozen at 338 while `log_polls` climbed 87→93 and
   `log_poll_failed` stayed **0**. At 22:13:44 it read `Password:` — proof the session had
   dropped to a login prompt — and logged it **`[LIVENESS_OK]`**. Textbook
   [[checks-must-not-match-their-own-advice]] sibling: a pass predicated on absence of evidence
   (orient-ie520 §4). Treat a login/password prompt as a reboot marker, and treat frozen line
   counts as a failed poll.
2. **Neither watcher watched member 1's own console.** On a formed stack both consoles relay to
   the master (orient-ie520 §6), so u5 was showing member 2's CLI. The pre-wedge seconds on
   member 1's own console — the single most valuable window — were never captured. Bootloader
   text reached u5 only *because* member 1 left the stack and its console reverted to local
   output. **Pin the watcher to the suspect member's own console, and expect the relay.**
3. **The companion tcpdump captured 0 packets.** It listened on **eth3** (10.38.215.65/27) while
   the DUT loads from 10.38.215.33 = **eth2** — a different /27, so it could never see the 41 MB
   transfer that demonstrably happened. `tftp-pcap/` holds a bare 24-byte pcap. Interface list in
   `TB470-HOST-NETWORKING.md`.

## The tooling did NOT survive

**The watcher script is gone** — nothing in the lab tree or repo references `rearm_ok`,
`REBOOT_MARKER` or `liveness_ok`; it was written to a session scratchpad ([[no-stray-scripts]])
and went with it. Only its driver survives: `console.py`, **md5
af8505812378a4001df3d324574301c9**, in five copies (e.g.
`old test runs/IE520/stack-tests/2026-09-02-driver-test/console.py`). There is **no
after-action** for the run. `console.py`'s `cmd_fast` is the right driver here — the framework
driver times out under `terminal monitor` (orient-ie520 §3). A re-run therefore means
**rewriting the watcher**; if it is worth running twice it belongs in the repo, not a scratchpad.

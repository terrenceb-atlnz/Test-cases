---
name: legacy-scripts-vs-framework
description: "The four fixes every legacy corpus script needs on a current testbox framework (py3-only, read-only Switch.name, TBv4 paths) — plus the gate strings and topology assumptions that rot silently and fail mid-run"
metadata: 
  node_type: memory
  type: project
  originSessionId: de51741a-eb27-4ad0-8c77-bf78c701dd63
  modified: 2026-07-29T23:06:51.806Z
---

Corpus scripts recovered from `ck.db` are mostly 2015-era and do **not** run as-is against the
current `/home/st-art/framework`. Found 2026-07-29 staging three stack-reboot scripts for tb105.
The same four breakages recur, so check for them up front rather than crash-and-retry:

1. **The framework is Python 3 ONLY** — `ATSwitch.py` uses f-strings, so `python` (2.7, still
   installed on testboxes) fails to import it. Run legacy scripts under `python3` with
   `PYTHONPATH=/home/st-art`. This then *forces* fixes 2-4.
2. **`dict.iteritems()`** — py2-only, and it is usually in an arg-logging helper called before
   the main loop, so it kills the script instantly. → `.items()`.
3. **`Switch.name` is now a read-only `@property`** (returns `mappedName or setupName`).
   Any `dut.name = ...` raises `AttributeError: can't set attribute`. Assign the underlying
   attributes instead (`obj.mappedName = None; obj.setupName = ...`). Note `Switch.name_is()`
   is a *comparison*, not a setter. Only `name` and `bootsFromFlash` are read-only properties —
   `logFileName`, `console.logFileName`, `preCmdBuf`, `preModeBuf` are all still plain attributes.
4. **TBv4 device paths.** Testboxes with `/etc/network/interfaces` are TBv4, where
   `Switch(tty=...)` wants a full path (`/dev/u5`), not an int. Scripts declaring
   `add_argument("device", type=int)` cannot express that. Watch for a knock-on: a `'%d' % tty`
   log-filename format then `TypeError`s, and a raw path in a filename needs its basename.

Also worth checking before a run: legacy scripts often carry **mis-calibrated timeouts**. A
stack that netboots via TFTP (tb105's x950 loads `tftp://10.37.105.100/x950-tb105.rel`, with a
bootloader "forced to boot from a non-standard location" warning) took **5m44s for ONE unit** to
reach `Configuration update completed` — so a 300s stack-reform budget fails spuriously.

**The gates rot too, and those cost hardware time** (2026-07-30, `0009_..._Master_reboot.py` on
tb105). The four fixes above crash at import; these fail mid-run and read as *device* faults:
a script waited on `'Activating Hot-Standby HA processes'`, a message this software never emits
(zero hits in ~740k lines of capture from the same stack — so no timeout could have saved it);
it monitored **one** arbitrarily-chosen stack member for the promotion message and assumed that
member wins the election; and `['Pending Master' 'Disabled Master']` (no comma) concatenated into
one never-printed string, so that check was silently dead. **Grep every gate string against real
captured console output before launching**, and read gate lists literally. Also check what the
script does *on a finding* — this one aborted the whole loop on the first new exception-log entry,
turning a 10-cycle hunt for an intermittent fault into one data point. A script that has "worked"
is no evidence its gates work: the prior run passed the single-monitor gate only by luck.

**Why:** the fix set is mechanical and identical each time, so knowing it converts a
multi-launch debugging loop into one patch pass. Relevant to PyTest Creator, which reuses
fragments from these same scripts ([[pytest-creator-askck]]).

**How to apply:** never patch `ck.db` or anything under `/home/st-art/framework` — Terrence
called out both as "explicitly bad things" (2026-07-29). Extract `scripts.source_text` to a
staging copy, keep a `.orig` beside it, verify it against `scripts.sha1`, and patch the copy.
Staging at the root of testbox_home works because that path IS `/home/terrenceb` on the testbox
over NFS, so no SCP step is needed. See [[setup-file-declares-topology]] and
[[testbox-console-access]].

---
name: windows-seat-gotchas
description: Four Windows/PowerShell facts the seat-setup demo (2026-09-11) paid for — a 32,767-char command line (pass big steers by --system-prompt-file), case-INSENSITIVE variable names ($Conf == $conf), a native command's stderr is TERMINATING under $ErrorActionPreference='Stop', and navigator.clipboard is undefined on plain http
metadata:
  type: project
  verified: 2026-09-11
---

**Four things a Linux gate cannot reach by running the code** — each cost a demo step on
2026-09-11 (plan `ask-ck/ck-facelift/PLAN-seat-setup-and-per-seat-llm.md` §9):

1. **A Windows command line is capped at 32,767 chars.** The 61k unit steer as an inline
   `--system-prompt` made `Process.Start` fail with *"The filename or extension is too long"*
   (20/20 unit calls, 300 ms each). Linux allows 128 KiB per argument, so `ck_agent.py` never
   saw it. The Windows agent writes the steer to a temp file and passes `--system-prompt-file`.
2. **PowerShell variable names are case-insensitive.** `$Conf` (a path) and `$conf` (a
   hashtable) were one variable; the conf was written to a file literally named
   `System.Collections.Hashtable` and never existed, so "remember my autostart answer" remembered
   nothing. One spelling per name — pinned for both scripts in `tests/test_ck_agent_transport.py`.
3. **Under `$ErrorActionPreference = 'Stop'` (PS 5.1), a native command's stderr line becomes a
   terminating `NativeCommandError` the moment stderr is redirected.** `schtasks /Query` on a
   missing task writes to stderr and killed the setup script after two ✔. Run natives with
   `Continue` and judge by exit code (`Invoke-Native` in `setup.ps1`).
4. **`navigator.clipboard` exists only in a secure context.** Ask CK is plain http on a LAN
   address, so on every real seat it is undefined; use `document.execCommand('copy')`.

**How to apply:** anything that must hold on a Windows seat needs either a live `pwsh` run in
the gate (the agent has one) or a structural pin — and a person at a real seat once, with the
server journal open on the other end. Related: [[claude-code-cli-transport-contract]],
[[demo-windows-seat]], [[user-prefers-manual-ui-testing]].

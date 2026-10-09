---
name: kill-by-pid-not-pattern
description: Stop a process you started by its captured PID — never `pkill -f <name>` when the user runs the same program (2026-10-09: a test ck_agent stopped by pattern could have taken the user's live seat agent; it also killed my own shell)
metadata:
  type: feedback
  verified: 2026-10-09
---

On 2026-10-09 I stopped a throwaway test agent (port 8766) with `pkill -f "[c]k_agent.py"`.
- **Who else matches:** every `ck_agent.py` the user runs matches that pattern, including a
  hand-started live seat agent on 8765. None happened to be running.
- **What else died:** the pattern also matched my own shell, whose command line contained
  "ck_agent.py" (exit 144).

**Why:** the user's processes and Claude's test copies share names on this host: agents,
servers, sentinels.

**How to apply:**
- Record the PID when starting anything long-lived (`$!`, or `pgrep` straight after with a
  unique argument such as the port) and kill that PID.
- If you must find it later, match on something only yours: the port, the scratchpad path.
  Verify the match list before signalling.
- Same family as TESTBOX-ACCESS's "never `pkill -f` over SSH".

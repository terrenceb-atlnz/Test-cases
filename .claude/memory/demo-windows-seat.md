---
name: demo-windows-seat
description: The Windows demo seat for Ask-CK is 10.33.25.50 (TROLLEY3-N11) — the remote client on both demo days (2026-08-20, 2026-09-10) and the first §9 verification seat (2026-09-11); a second, fresh seat 10.33.22.18 confirmed the fixes the same morning
metadata:
  type: project
  verified: 2026-09-11
---

**The Ask-CK demo Windows seat is `10.33.25.50`.** Identified from the `ask-ck.service`
journal for 2026-09-10 13:04–13:34 NZST: it loaded the page, applied LLM config on
AWPTCM-T43852, then long-polled `/api/agent/next` 64 times with no agent to serve it, and
went quiet exactly when the RDP-to-localhost workaround (127.0.0.1 traffic) began. The
same address is the remote seat in `archive/plans/PLAN-llm-mode-selection.md` §1 (archived 2026-09-11)
(2026-08-20, "local agent unreachable"). Terrence confirmed it is the demo device and can
remote into it.

**Why:** the seat-setup plan (`ask-ck/ck-facelift/PLAN-seat-setup-and-per-seat-llm.md` §9)
needs a real Windows seat to verify the served one-liner, the PowerShell agent, login and
autostart. This is that seat; no other Windows client has been seen hitting the server.

**How to apply:**
- Use it for §9 verification (fresh-install run, re-run, logout/login, stale-agent
  replacement, reboot). Ask Terrence to remote in — there is no direct access from this
  host, and no credential is stored anywhere in the repo.
- On demo day 2026-09-10 it had **no** Claude agent, no Git and no source files — only the
  URL. Treat it as the model of a bare seat, which is what the plan must work on.
- To re-identify a seat later: `journalctl --user -u ask-ck.service --since … | grep -oE
  '([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+ - "'` — 10.33.22.17 is this host's own LAN address and
  127.0.0.1 is a browser on this host, so neither is a remote seat.

**2026-09-11:** confirmed by the xrdp log — the 13:35 RDP session on demo day came from
`10.33.25.50`, computer name **TROLLEY3-N11**. The §9 run happened there 07:48–08:08 (five
findings, see [[windows-seat-gotchas]]), then on a fresh seat **10.33.22.18** 09:25–09:32, which
produced 10/10 units on its own Claude. Both seats have a stray `System.Collections.Hashtable`
file in the folder the old one-liner was run from (finding #5) — safe to delete.

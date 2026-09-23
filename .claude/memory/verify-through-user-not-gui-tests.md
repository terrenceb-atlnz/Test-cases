---
name: verify-through-user-not-gui-tests
description: Never spawn GUI windows or other visible actions on Terrence's seat as a verification step; use non-intrusive checks or ask him, and once a question is asked WAIT for the answer before acting again
metadata:
  verified: 2026-09-23
  type: feedback
---

Do not use Terrence's live desktop as a test bench. Verifying a desktop fix by triggering the
app (D-Bus `Activate`, `gtk-launch`, opening windows) puts windows on his screen while he is
working. On 2026-09-14 I did this twice while diagnosing the Files/xrdp display issue — the
second time after I had already asked him "do you see a window?" and not yet received an
answer — and he interrupted me mid-typing.

**Why:** a visible action on the seat interrupts his work, and re-triggering after asking a
question means I preferred acting over waiting — the exact failure mode CLAUDE.md §1 names.

**How to apply:**
- Verify with non-intrusive evidence first: `/proc/<pid>/environ`, `wchan`/`stack`, the
  journal, `systemctl --user show-environment`, `xwininfo -root -tree` (read-only).
- The user is the final verifier for anything visual — ask once, then **wait** for the answer.
- If a visible action is genuinely the only test, say exactly what will appear and get a yes
  first; never repeat it unasked. See [[seat-files-terminal-open-on-xrdp-display]].

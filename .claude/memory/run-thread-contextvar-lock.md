---
name: run-thread-contextvar-lock
description: No test case has ever run on hardware because RunManager's thread cannot inherit the ContextVar holding the session id, so the case lock rejects it before SSH — and it reports as "SSH connect failed"
metadata:
  type: project
---

**The bench was never the problem.** Reproduced offline 2026-08-03 against the real `locks`
module:

```
holder in main thread          : 'browser-tab-abc'   can write: YES
holder inside RunManager thread: ''                  can write: NO -> LockConflictError
```

`RunManager._run` (`pt_exec.py:407-412`) is a `threading.Thread`. `llm.current_session_id` is a
**`contextvars.ContextVar`**, and a new thread starts with a fresh Context — it inherits nothing.
So the run thread's first `on_update` → `_pt_persist` → `locks.require_can_write` presents an
empty holder and is **locked out by the very browser tab that started the run**, before SSH is
attempted.

**It reports as a lab fault.** That first `on_update` sits inside the connect `try/except`, so the
`LockConflictError` surfaces as *"SSH connect failed: … the case is locked"* — which is why
several sessions went looking at cabling, consoles and `.setup` files.

**This, not D13, is why `step7.runs` is empty for every session.** D13 (the phantom stack demand
from `_detect_topology`'s regex over fragment text) blocks *preflight* — and preflight is not
wired into the run path at all. Both routes to hardware were closed for unrelated reasons: the
browser path by this lock, and `pt_autopilot` by having no hardware phase (`--phase` is
`generator|pytest|all`).

**Fix:** `locks` already accepts an explicit `holder=` for exactly this situation (the
`sendBeacon` release path uses it). Either capture `locks.current_holder()` in `run_script` and
pass it into `RunManager.start`, or `contextvars.copy_context().run(...)` the thread body. Also
split the first `on_update` out of the connect `try/except` so a persist failure stops
masquerading as an SSH failure. Plan: `ask-ck/ck-facelift/PLAN-pipeline-end-to-end.md` Phase 11.0.

**How to apply:** before believing any "the testbox rejected it" report from this product,
check whether the failing call ran on a `Thread`. Related: [[ckdb-wal-and-test-isolation]],
[[testbox-console-access]], [[preflight-topology-check]],
[[silent-degradation-audit-2026-07-30]].

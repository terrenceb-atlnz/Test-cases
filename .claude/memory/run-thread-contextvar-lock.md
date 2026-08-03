---
name: run-thread-contextvar-lock
description: FIXED 2026-08-03c — a background thread must carry contextvars.copy_context() or it loses the session id; that silently locked every hardware run out and reported it as "SSH connect failed"
metadata:
  type: project
---

**FIXED** in `pt_exec.RunManager.start` (2026-08-03c, commit `f0a94af`): the thread now runs
as `target=ctx.run` over a `contextvars.copy_context()` captured on the calling thread. A
repo-wide guard (`tests/test_run_thread_context.py`) refuses any other `threading.Thread` in
`CK_server/` unless it carries a `# context-free: <reason>` marker. **Still unproven on real
hardware** — no run has been attempted since; that is Phase 11.4.

**The durable lesson, which is why this memory still exists.** A new `threading.Thread`
starts with a **fresh `contextvars.Context` and inherits nothing.** `llm.current_session_id`
is a ContextVar and `locks.current_holder()` reads it, so the run thread's holder was `''`
while the browser tab held a live lock on the same case:

```
holder in main thread          : 'browser-tab-abc'   can write: YES
holder inside RunManager thread: ''                  can write: NO -> LockConflictError
```

**It wore a lab fault's clothing.** That first `on_update` sits inside the connect
`try/except`, so the lock error surfaced as *"SSH connect failed: … the case is locked"* —
which is why several sessions went looking at cabling, consoles and `.setup` files. This,
not D13, is why `step7.runs` was empty for every session that had ever existed. (D13 blocks
*preflight*, which is still not wired into the run path at all; `pt_autopilot` still has no
hardware phase.)

**Copy the whole Context, not one value.** It fixes every ContextVar at once — including the
one `llm_debug` uses to name its log file, which is why background work had been landing in
`debug-log/no-session.jsonl`.

**How to apply:** before believing any "the testbox rejected it" report from this product,
check whether the failing call ran on a `Thread`. And when a persist/lock failure sits inside
a connect `try/except`, the error message will name the wrong subsystem. Related:
[[ckdb-wal-and-test-isolation]], [[testbox-console-access]], [[preflight-topology-check]],
[[silent-degradation-audit-2026-07-30]], [[mutate-before-you-claim]].

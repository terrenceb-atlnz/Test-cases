---
name: framework-unsupported-needs-a-failure
description: framework TestCase result = counts: no pass+no fail → ERROR; supported=False needs a self.failed() to read UNSUPPORTED; main() still runs after configure() sets it — the fill rules teach the ERROR shape
metadata:
  type: reference
  verified: 2026-09-24
---

Read from `/home/st-art/framework/ATTestCase.py` on tb470 (read-only), `_get_result` and `run`:

| passes | fails | `self.supported` | result |
|---|---|---|---|
| 0 | 0 | any | **ERROR** |
| >0 | 0 | True | PASS |
| >0 | 0 | False | **ERROR** ("unsupported, but passed") |
| any | >0 | True | FAIL |
| any | >0 | False | **UNSUPPORTED** |

And `__run` calls `configure()`, `main()`, `tear_down()` in turn regardless of `self.supported`
(only `skipIfExcl` skips), so a guard in `configure()` alone does not stop `main()`.

**So UNSUPPORTED is `self.supported = False` followed by `self.failed('reason')`** — what ART
does in 224 of its 352 uses (ck.db `scripts`, db='art'). The shape
`self.supported = False; self.log(...); return` reports **ERROR**, and it is exactly what
`pt_fill_rules.jinja` §3d taught as of 2026-09-24 (T33235 had 18 such paths, fixed by hand;
T33234 still has 8). Tracked as G11 in `ask-ck/plans/PLAN-pt-drive-followups-2026-09-24.md`.

**Also from the same file:** `confCheck=True` is the TestCase default — after each case's
`tear_down()` the framework compares every switch's config with the TestSet's, so a case must
restore what it changed (use the documented negation, `no speed`, both ends).

Related: [[art-suite-shape]], [[read-the-transcripts-before-driving-hardware]].

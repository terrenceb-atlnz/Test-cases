---
name: framework-unsupported-needs-a-failure
description: framework TestCase result = counts; in-main UNSUPPORTED = supported=False + self.failed() (costs a whole-bench restart); a case already unsupported at its turn is NOT RUN, no restart — via the declarative gate or an earlier case's mark; the generator teaches both since 2026-10-02
metadata:
  type: reference
  verified: 2026-10-02
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
`self.supported = False; self.log(...); return` reports **ERROR**; `pt_fill_rules.jinja` §3d taught
it until 2026-09-24. Fixed that night (G11, `archive/plans/PLAN-pt-drive-followups-2026-09-24.md`,
branch `pt-followups-2026-09-24`): the rules teach the pair, and `_lint_unsupported_without_failure`
makes the flag without a fail a BLOCKING lint error (`unsupported:`). T33235's 18 and T33234's 8
paths are fixed in their files.

**How to apply:** when writing or reviewing a case's capability gate, put the check and the
`self.failed()` in `main()`; a `configure()` guard alone does not stop `main()`.

**The cost, observed on tb470 2026-09-29:** the in-`main()` pair still trips the framework's
"Setup is no longer reliable" restart, which PDU-cycles the whole bench. T33235 cases 8–12
(no fibre link) cost five cycles of about 4 min each.

**Skipping before the case runs (read 2026-10-02, `ATTestSet.py` ~1755):** the TestSet runs a
case only `if testCase.supported or self.runUnsupported`, checked per case AT ITS TURN. So
without `-u` a case whose `supported` is already False is not run at all — no configure, main or
tear_down, no restart, and **no `<<` result line**. Two ways to get there:
1. **declarative** (a fact `init` knows): a device attribute set in `init`
   (`dut.has_fibre_link = self.fibre_supported`) and on the case
   `testCasePlatformWithPropertyIncl = {'dut': [(['.*'], ['<attr>'])]}` (`'*'` is an invalid
   regex; `.*` matches every family; the key is `getattr(testSet, key)` — a wrong one aborts the
   run). The marking pass reads it after `TestSet.configure()` (T33234 run 3 dropped all 14).
2. **marked by an earlier case** (a fact an earlier case found): set `tc.supported = False` on
   the later case object before its turn (the frame's `publish_value(…, None)` /
   `mark_cases_unsupported`, first hand-written in T33235 `056114d`).
`skipIfExcl = True` matters only under `-u`, where `run()` fails the case without entering
`__run()`, so it stays UNSUPPORTED with no restart. Only a fact the case finds ITSELF still needs
the in-`main()` pair (kind C, deferred). **The generator teaches 1 and 2 since 2026-10-02**
(Terrence; `ask-ck/plans/PLAN-unsupported-gating.md`), lints them (`rolegate:`, `needs:`), and
`parse_framework_log` reports a not-run case as UNSUPPORTED `ran: false` from the
`Test case N has been marked as unsupported` / `INFO: TestCase_N marked unsupported before it
runs:` lines.

**Also from the same file:** `confCheck=True` is the TestCase default — after each case's
`tear_down()` the framework compares every switch's config with the TestSet's, so a case must
restore what it changed (use the documented negation, `no speed`, both ends).

Related: [[art-suite-shape]], [[read-the-transcripts-before-driving-hardware]].

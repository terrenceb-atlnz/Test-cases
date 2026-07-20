# PyTest Creator — Logging Contract (Part 0)

> **Status: SPEC, verified against real hardware (2026-07-21).** This is the required
> log-output behavior every generated script must satisfy so that the tool's
> `parse_framework_log()` can read one PASS/FAIL block per test step — Part 3
> criterion 6 ("logs each step as we require"). The template (Part 1) bakes these
> calls in so a conformant fill cannot omit them.
>
> Grounded in the framework's own source (`/home/st-art/framework/ATTestSet.py`,
> `ATTestCase.py` — read-only), a real run log (`test-1331.1001.log`, 101 cases), and
> the tool's parser (`CK_server/pt_exec.py::parse_framework_log`). All three agree.

## 1. How the framework writes logs (verified from source)

- **Every line is timestamped** by `ATTestSet.log()`:
  `YYYY-MM-DD HH:MM:SS: <message>`. A generated script never writes the timestamp
  itself — it calls `self.log(msg)` and the framework prefixes it.
- **Log file name** is `test-<testSuiteNum>.<testSetNum>.log` (from
  `create_log_file()`), created next to the script. The tool retrieves it by
  basename after the run.
- **Assertions write the machine-readable markers** (`ATTestCase.passed/failed`):
  - `self.passed(reason)` → writes `PASS: <reason>` — **only if `reason` is non-empty.**
  - `self.failed(reason)` → writes `!!FAIL: <reason>` and records the failure — again
    only if `reason` is non-empty; also increments `numFailed`.
  - **Empty `self.passed()` / `self.failed()` writes NO marker line.** It still counts
    toward numPassed/numFailed, but produces no per-assertion evidence in the log.
- **Per-test-case block** (emitted by the framework's `run()` around each case):
  ```
  >> test-<suite>.<set>.<caseNum>
  TEST_CASE_DATETIME_STARTED / TEST_CASE_DESCRIPTION / TEST_CASE_REFERENCES /
  TEST_CASE_METHOD / TEST_CASE_LOGS
  ... the case's own timestamped self.log() / PASS: / !!FAIL: lines ...
  TEST_CASE_DATETIME_ENDED
  << test-<suite>.<set>.<caseNum>: <RESULT> (numPassed: p numFailed: f)
  ```
  `<RESULT>` is one of `PASS | FAIL | ERROR | UNSUPPORTED` (real logs contain
  UNSUPPORTED — a case is not just pass/fail). A single non-empty `failed()` flips the
  case's footer result away from PASS.

## 2. What the parser keys on (must stay in lockstep)

`parse_framework_log()` matches, per stripped line (timestamp removed):
- `^>> test-(.+)$` — case start
- `^<< test-(.+): (PASS|FAIL|ERROR|UNSUPPORTED) \(numPassed: p numFailed: f\)$` — case end
- `^PASS: (.*)$` and `^!!FAIL: (.*)$` — per-assertion markers (a `!!FAIL:` outside any
  case counts as `unparsed_fails`)

Validated: the real 101-case log parses to 101 cases, correct pass/fail counts,
`numPassed 1819 / numFailed 2`, zero unparsed fails. The header/footer blocks come
from the framework automatically — a script gets them **for free** by subclassing
`ATTestCase.TestCase` and being added with `ts.add_testCase(...)`. The script's job is
only to emit the **right PASS/FAIL markers inside each case**.

## 3. The contract every generated `main()` must satisfy

For the tool to see **one clean PASS/FAIL block per test step**, each `TestCase_<n>.main()`
MUST:

1. **Log the step start** — `self.log('<step n>: <what this step does>')` as the first
   action, so the log is human-readable and each block is self-describing.
2. **Log the observed result** — `self.log(...)` the actual output/measurement the
   verification is based on (the evidence).
3. **Assert with a NON-EMPTY reason** — end with exactly one determination:
   `self.passed('<why it passed>')` or `self.failed('<why it failed>')`. The reason
   must be non-empty (empty reasons emit no marker → no per-step evidence → fails
   criterion 6). One case = one step = one pass/fail determination.

And each `TestCase_<n>` class MUST carry:
- `testCaseDesc` — one-line description (mirrors the sequence step)
- `testCaseRef  = '<AWPTCM-key>'` — traceability back to the case
- `testCaseMethod` — the action+verify text
- `main(self)` — the body above

This is exactly the ~72%-of-corpus pattern (see PLAN-pytest-testing §1.4) made
**mandatory**. The template (Part 1) provides these as fixed lines/slots; the lint
(`_lint_generated`) is extended to fail a script whose `main()` lacks a step-start
`self.log`, a result `self.log`, or a non-empty `self.passed()/failed()`.

## 4. Conformance checks (mechanical — used in lint + Part 3 criterion 6)

Given a generated script (offline) and its run log (from tb470):
- **offline (lint):** every `TestCase_<n>.main()` contains ≥1 `self.log(...)`, and
  exactly one `self.passed(<non-empty>)` or `self.failed(<non-empty>)`; each class has
  the four required attributes with `testCaseRef` = the case key.
- **post-run (parser):** `parse_framework_log()` returns exactly one case block per
  sequence step, each with a `PASS`/`FAIL` footer and ≥1 `PASS:`/`!!FAIL:` marker
  line — i.e. `len(cases) == len(sequence)` and no `ERROR`/unclosed blocks.

Criterion 6 scoring: **yes** = one parsed block per step, all with markers; **partial**
= blocks present but some steps missing markers or merged; **no** = no per-step blocks.

## 5. Gotchas baked into the contract (learned from real source/logs)

- Empty `passed()`/`failed()` is silent — the contract requires a reason.
- Results are 4-valued (PASS/FAIL/ERROR/UNSUPPORTED), not boolean — the parser and
  Part 3 rubric account for non-PASS, non-FAIL outcomes.
- One `failed()` anywhere in a case flips that case's footer; "all steps pass" means
  every case footer is PASS and `numFailed == 0`.
- The script must NOT hand-write timestamps, `>> / <<` headers, or `TEST_CASE_*`
  blocks — those are the framework's; duplicating them corrupts parsing.

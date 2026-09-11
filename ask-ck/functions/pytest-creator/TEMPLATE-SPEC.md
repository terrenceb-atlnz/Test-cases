# PyTest Creator — Template Spec (Part 1)

> The standardized ART script skeleton, its slots, and the conformance rules that make
> Part 3 criteria 1–3 and 6 mechanically checkable. Template file:
> `CK_server/templates/pt_script_template.py.jinja`. Logging rules:
> `LOGGING-CONTRACT.md`. Anchor exemplar: `art/1363_ipv6/test-1363.1002.py`.

## Why a template (not just a style anchor)

Before this, generation handed the LLM one exemplar + prose rules and let it compose
freely — so structure varied per run/model and "did it use the template?" had no
answer. The template is a **fixed frame with free fill-slots**: the header, TestSet
structure, one TestCase per step, the logging contract inside each `main()`, and the
`__main__` footer are fixed; only the device logic is filled. Rigidity level was set by
corpus evidence (1,828 ART `main()` bodies): bodies vary hugely → free; the log/assert
skeleton is ~72% consistent → mandatory. See PLAN §1.4.

## The three slot kinds (never conflated)

| Slot | Renders to | Fill? | Pass/fail? |
|------|-----------|-------|-----------|
| **Suite setup** | `TestSet.configure()` / `tear_down()` | config commands | **NO** — setup, not a test |
| **Verification step** | one `TestCase_<n>.main()` per sequence step | device logic + assertion | **YES** — logging contract applies |
| **Framework automatics** | (nothing) | — | reboot/power-cycle/log-clear come free from subclassing |

This mirrors ART reality: setup/config lives in lifecycle methods, not separate
scripts; per-step verification lives in `TestCase` classes; the framework does pre-test
hygiene with zero script code (see `../test-composer/ART-EXECUTION-CHAIN.md`).

## Fixed frame (the LLM must NOT alter)

- `#!/usr/bin/python3`, `import sys`, `from framework import ATTestSet, ATTestCase`
  (+ any real extra imports; `from framework.ATPackets import *` when the frame binds the
  testbox link; `from library_<case> import *` when the suite library exists — see below).
- `class TestSet(ATTestSet.TestSet)` with `FEATURES = ['ALL']`, `init(self, setup)`
  binding topology, `configure(self)`, `tear_down(self)`.
- One `class TestCase_<n>(ATTestCase.TestCase)` **per sequence step, in order**, each
  with `testCaseDesc`, `testCaseRef = '<case_key>'`, the ART multi-line `testCaseMethod  =
  '<action>\n'` / `testCaseMethod += 'Verify: <verify>\n'`, and **three methods**:
  `configure(self)` (the precondition the step presumes — config only), `main(self)`, and
  `tear_down(self)` (the mirror of configure() and of what main() changed, in `no` form).
  The per-case pair is what 172 / 148 of 188 ART tests do (2026-09-07 census).
- **Every method opens with the ART shortcut block**, emitted by the frame from what
  `init()` bound: `tb = self.testSet.tb`, `<dut> = self.testSet.<dut>`, `ethA = tb.ethA`,
  `portA = <dut>.portA`, `peer = self.testSet.peer`, `portPeer = <dut>.portPeer` (158 of 188
  ART tests open this way). It is the complete list of names that exist.
- **Topology, ART shape (2026-09-07):** `init()` binds up to two links from the bench's
  role contract — the TESTBOX link `(<dut>.portA, tb.ethA)` (profile `tblink`; captures and
  injected frames live on `tb.ethA`) and the NEIGHBOUR link `(<dut>.portPeer, peer.portDut)`
  (profile `base`/`fibre`). The neighbour handle is `peer`, never `dut`: ART reserves `dut`
  for the DUT's own stack, and a partner called `dut` made every model read `dut.portA` as
  the DUT port. Which links a case gets is text-driven (`_detect_links`); an unneeded link
  costs one bench-file line, a missing one dies on `interface None`.
- **The suite library** `library_<case>.py` (the ART `library_<suite>.py` convention) holds
  every selected fragment that is a stand-alone function, class or constant, verbatim under
  its provenance tag, plus its source's imports; the frame imports it with `*` and it ships
  and is persisted beside the script. Methods and class-body slices stay fragments.
- `if __name__ == '__main__':` → `ts = TestSet()`, `ts.add_testCase(TestCase_<n>())`
  for every step in order, `ts.run(sys.argv)`.

### Data-driven topology (init is a FIXED frame even for multi-device cases)

`init()` is not hardcoded to one switch. `_detect_topology()` scans the sequence text +
reused fragment code for device names and binds each — matching the verified `.setup`
conventions (switches `swi_a/b/c…`, stacks `stk_a…`; 353 `init_swi` / 114 `init_stk` /
834 `init_portlink` uses across ART):
- **switches** — every `swi_<x>` referenced (default `['swi_a']` when none seen).
- **stacks** — every `stk_<x>` referenced (`init_stk`).
- **portlink** — if the case/fragments mention a port link, a single `init_portlink`
  FILL slot is rendered (links are too case-specific to auto-generate, but the need is
  detected so the slot is present). 
This keeps `init()` a generated frame rather than a free-form slot, preserving the
fixed-frame guarantee for topology.

## Free fill-slots (the LLM completes)

- `TestSet.init` device list, `configure()`/`tear_down()` command bodies.
- Each `main()`: the action (device I/O) and the verification condition, keeping the
  three mandatory logging-contract calls.

## The logging contract inside every `main()` (mandatory)

1. `self.log('STEP <n>: <action>')` — step start.
2. `self.log('OBSERVED: {}'.format(output))` — the evidence.
3. At least one **non-empty** `self.passed('<why>')` or `self.failed('<why>')` on every
   path — checkpoints in the ART style are welcome; a silent branch is not (revised
   2026-09-07 from "exactly one", see LOGGING-CONTRACT.md §3). No verdict in a TestCase's
   own `configure()`/`tear_down()`.

(Empty `passed()/failed()` emit no marker → no per-step evidence → fails criterion 6.
See LOGGING-CONTRACT.md.)

## Conformance checks (mechanical — lint + Part 3)

Run against a generated script offline:

- **C1 template used** (criterion 1): has the fixed frame — `TestSet(ATTestSet.TestSet)`
  with `init`/`configure`/`tear_down`; `TestCase_<n>(ATTestCase.TestCase)` classes;
  `__main__` with `ts.run(sys.argv)`. exactly=all present & one TC per step;
  partially=frame present but TC count ≠ step count or a lifecycle method missing;
  not-at-all=no TestSet/TestCase frame.
- **C6 logging contract** (criterion 6, offline half): every `TestCase_<n>.main()` has
  ≥1 `self.log(...)` AND ≥1 non-empty `self.passed(...)`/`self.failed(...)` with no
  empty-reason call (was "exactly one" until 2026-09-07);
  each class has the three `testCase*` attrs with `testCaseRef` == the case key.
- **C2/C3 snippet reuse/order** (criteria 2–3): compare the filled `main()` bodies
  against the approved step-5 fragments (substring/normalized match) and check fragment
  order matches sequence order. (Computed by the Part 3 offline judge, not lint.)

The generator's `_lint_generated` is extended to fail a script that breaks C1 or the
offline half of C6 (was: generic structure only). Post-run, `parse_framework_log`
supplies the on-hardware half of C6 (one parsed block per step).

## What we standardize AWAY from the exemplar

`art/1363_ipv6/test-1363.1002.py` has `testCaseRef = 'None'`; the template fixes
`testCaseRef` to the AWPTCM case key for traceability. Otherwise the exemplar's shape
(inline TestCase classes, `self.log(output)` evidence, non-empty asserts, per-case
tear_down) IS the target.

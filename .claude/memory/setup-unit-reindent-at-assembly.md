---
name: setup-unit-reindent-at-assembly
description: Why the PyTest Creator's setup unit consistently comes back mis-indented (it's the only non-top-level unit) and where that's fixed — _assemble_units re-indents it
metadata:
  type: project
  verified: 2026-09-04
---

In the PyTest Creator's per-unit generate (step 6), the **`setup` unit** (the
`configure()`/`tear_down()` pair) comes back mis-indented **consistently** — the model
flush-lefts `def configure` to column 0 while `def tear_down` stays at 4 (or shifts a whole
method). The byte-exact splice in `_assemble_units` then rides that straight into the file as
`IndentationError: unindent does not match any outer indentation level`, which fails **both**
the Summary lint (`py_compile`) and `manifest_check` (registered/defined read 0/0 because the
file won't parse). Observed on AWPTCM-T44297, 2026-09-04, and reproduced on a fresh regenerate.

**Why it's the setup unit and nothing else:** every TestCase unit is a **complete top-level
class** (`class TestCase_N` at column 0), which models reproduce cleanly. The setup unit is the
**only** unit that is a **class-body fragment** — two `TestSet` methods at indent 4 — handed to
the model as an indented block. Models reliably preserve top-level indentation but mangle the
leading whitespace of a non-top-level fragment. Nothing downstream normalised it: the arrival
shape-check for the setup unit is **regex-only** (both methods present) and deliberately does
NOT parse/normalise indent (the 2026-09-03 change — a synthetic-class wrapper's line numbers
were unmappable), and `_assemble_units` splices **byte-for-byte** by design.

**Fix (2026-09-04):** `_assemble_units` re-indents the setup pair to the frame slot's known
indents via `_reindent_setup_pair` + `_setup_slot_indents` in
`routers/pytest_create.py` — each method's `def`→4 and its body base→8 set **independently**
(so a flush-left `def` with a correct body isn't over-indented), internal nesting preserved,
idempotent. TestCase units are still spliced verbatim. Assembly is the right place because the
target indent is read off the frame's own slot and the arrival check no longer judges it. See
[[pt-step-numbering-divergence]] for the sibling fact that unit ids (`setup`,`tc1`…) are not
sequence step numbers, and [[pytest-creator-askck]] for the flow.

If you touch the setup unit again: a per-unit **fix** path (regenerate only the finding's units,
splice the rest byte-exact) would make Fix-scope airtight — the current `fix_script` is a
whole-script rewrite that, measured on T44297, only lightly drifted (comment-only touches on
sibling cases a cross-unit finding named), but drift is possible in general.

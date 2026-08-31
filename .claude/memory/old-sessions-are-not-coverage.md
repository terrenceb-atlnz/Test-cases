---
name: old-sessions-are-not-coverage
description: A green suite over a corpus of STORED sessions proves nothing about a new flow — every session predating the change still carries the old shape, so a gate that broke for new work stays green
metadata:
  type: feedback
  verified: 2026-08-31
---

**A corpus of stored sessions is fixture data frozen at the moment each was written. It is not
coverage of the flow that writes them today.**

Measured 2026-08-31. PyTest Creator step 3 moved to a per-sequence-step picker on 2026-08-26.
`confirm_step` still required `step3.provenance` or `step3.matches`, and the new flow writes
neither — so step 3 became unconfirmable and step 4 unreachable behind
`_require_confirmed`. The suite stayed green through all of it, and so did every manual check,
because **every `pt-` session already in `ck.db` predated the change and still carried
`matches`.** The bug was reachable only by driving a case from scratch, which is what Terrence
did. Two more defects in the same session had the same signature: the step-6 naming fields had
no writer before a first successful generation, and `_group_display` returned a default its own
validator rejected — both invisible to any session that had already been generated once.

The tell is a predicate that reads state some EARLIER version of the code wrote. Old rows
satisfy it; new rows do not; nothing in the suite notices because the suite is looking at old
rows.

**How to apply:** when a flow changes what it persists, do not accept the stored corpus as
evidence. Build the new shape explicitly in a test — a fresh session with only what the current
code writes — and assert the gate accepts it. Where a gate has an old predicate and a new one,
pin BOTH: the legacy shape still passing is what proves the change is backward-compatible, and
a from-scratch shape passing is what proves it works at all. Pin the reject case too, or the
gate quietly stops gating. See `tests/test_pt_step3_confirm_gate.py` for the four-shape version
of this, and [[mutate-before-you-claim]] — a test written against the old corpus passes with
the fix reverted, which is the same class of false confidence.

Related: [[llm-provenance-portability]] (the panel previewing a call the flow no longer makes,
found the same day), [[pytest-creator-askck]], [[shared-tree-status-has-short-shelf-life]].

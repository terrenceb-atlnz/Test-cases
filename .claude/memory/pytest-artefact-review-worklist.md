---
name: pytest-artefact-review-worklist
description: "PyTest Creator adversarial-review worklist (T33233) — findings #1/2/4/5/7 DONE, #3 partial; D1/D2/D3 all RESOLVED + implemented 2026-07-27 (see [[d1-fragment-resolver-boundaries]] / [[d3-py2-fragment-translation]])"
metadata: 
  node_type: memory
  type: project
  originSessionId: 05c21640-4b4b-4ca4-a470-32f6bfa5c600
  modified: 2026-07-26T19:56:51.814Z
---

The adversarial review of the T33233 generated artefact produced a prioritized worklist.
We worked through it step-by-step (Terrence: "go step-by-step through this list"). Status
as of 2026-07-23 (all changes committed at session close):

- **#1 device-name reconciliation** — DONE. `_detect_fragment_devices` + topology now bind
  the names the reused fragments actually use; reconciliation note surfaced in preview + prompt.
- **#2 physical-step handling** — DONE. 4-kind taxonomy (setup/verify/physical/manual) in
  `pt_extract_sequence.jinja`; `_step_kind()` single classifier; `_split_sequence` non-mutating;
  template branches: physical→operator-prompt+poll-for-state-change (SVT 3009 `waitForReplugEvent`
  pattern), manual→`yesNo()`, verify→normal, setup→`configure()`. See [[physical-interaction-steps]].
- **#3 fragment quality** — PARTIAL. Cross-step dedupe was already handled (`fragments_by_key`).
  Added `maps_to` phantom-step validation (`_clean_maps`). Line-vs-class extraction + per-step
  cap are OPEN decisions (D1/D2 below).
- **#4 provenance divergence** — FIXED + unit-verified. `_restamp_provenance` now takes `sequence`
  and remaps `orig_n -> class_n` before stamping. Bug was: keyed `maps_to` (original step #s)
  directly by `TestCase_<n>` class #, which diverge once a setup step precedes a verify step →
  wrong tag on the wrong TestCase. Both call sites (generate + fix) pass sequence now.
- **#5 guaranteed-fail default** — NO CHANGE NEEDED. `if False:`/`output=''` are intentional
  scaffolding; `_lint_generated` already hard-rejects a saved script containing `>>> FILL`,
  `output = ''  # >>> replace`, or `if False:  # >>> replace`.
- **#7 zero-reuse marker** — ADDED. Preview emits `# ===== NO REUSE ... =====` on verify
  TestCases with no fragment (physical/manual excluded — they self-generate a pattern).

**Why:** Terrence reframed physical steps as IN scope (not skippable) and directed a
step-by-step pass. The provenance bug was a real correctness defect (wrong-attribution), not
cosmetic.

**How to apply:** All three decisions are now RESOLVED + implemented (2026-07-27, uncommitted);
`NEXT_SESSION_DECISIONS.md` was deleted. Full rationale in [[d1-fragment-resolver-boundaries]]
and [[d3-py2-fragment-translation]]:
- **D1** — NOT `main()`-trim (that framing was ART-only). Hardened the single `_resolve_symbol_code`
  with a `_resolve_end` boundary chain (exact loc → next-unit-start → loc_total), killing the
  `loc[0]+60` fallback; helpers via real loc. No per-lib resolvers, no ck.db rebuild [[db-is-permanent-source]].
- **D2** — keep no cap (no code).
- **D3** — deterministic Py2→Py3 via stdlib lib2to3 at resolve time (not just a soft-warn); untranslatable
  ships original + ⚠ banner + conditional Generate-prompt steer; `(py2→py3)` provenance suffix.
Note: physical classification only appears after re-running Sequence (step 2) on a case with plug/unplug steps.

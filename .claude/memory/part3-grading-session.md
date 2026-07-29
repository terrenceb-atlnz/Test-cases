---
name: part3-grading-session
description: Part 3 grading (PLAN-pytest-testing) — judges changed to Opus+vllm-fast; T33235 generated 2026-07-27; Part 3a green; Part 3b UNBLOCKED 2026-07-29 (tb470.setup now exists, run preconditions verified live)
metadata: 
  node_type: memory
  type: project
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-29T03:41:00.073Z
---

Part 3 of `ask-ck/pytest-create/PLAN-pytest-testing.md` (grading generated scripts on the
6-criterion rubric) started 2026-07-27. State at kickoff:

- **Judges CHANGED from the plan**: Terrence chose **Claude Opus + vllm-fast**, NOT the
  plan's settled §5 decision-3 (Opus + vllm-thinking). Reason: §8.3 found vllm-thinking
  burned its whole 32k budget on reasoning and emitted zero answer. Update the plan's
  decision-3 rather than let this drift silently.
- **T33235 script generated 2026-07-27** (was missing; session stopped at step 5).
  vllm-fast, 70s, lint-clean, 7 TestCases. It is the `decision: new` / zero-fragment
  case — pure gap-fill, so the most interesting one for criterion 4.
- **tb470 doc correction**: PLAN §5b says configs live under `/home/st-art/framework`.
  They do NOT — that dir has no `configs/`. Real path is
  **`/home/st-art/st-art/configs/`** (473 `.setup` files). `tb470.setup` still genuinely
  absent → **Part 3b (criteria 5-6) remains blocked**; Part 3a is not.

**Why:** the plan's own text is stale on two points and the judge choice diverges from a
settled decision — both must land in the doc or the next session re-derives them wrong.

**PART 3b UNBLOCKED 2026-07-29.** `configs/tb470.setup` now EXISTS on tb470 (681 B, created
2026-07-27) — declares a real data-plane topology: swi_a=x930 (also stk_a), swi_c=AR4050S,
swi_d=x530 on /dev/u0/u1/u2, PDU power, testbox uplinks + full inter-switch mesh. `tb470.cfg`
exists but is empty (0 B). Run preconditions re-verified live: framework present, `sudo -n`
OK, python3 3.13.5, ttys u0/u1/u2 present. So criteria 5-6 need only a GO decision, not a
prerequisite. Caveats before running: (1) a run CONFIGURES a shared switch (not read-only) —
confirm the box is free; (2) T33235 has a physical hot-insert step that will auto-timeout-fail
with no operator, so T33234/T33233 (config-only) are the cleaner first-run cases; (3) verify
whether the direct `-s <setup>` path needs the empty tb470.cfg (generate via
framework/config_gen.py if it complains). See [[physical-interaction-steps]].

**How to apply:** grade criteria 1-4 offline for all three cases (Part 3a — done/green);
Part 3b is now runnable. See [[physical-interaction-steps]] —
T33235's hot-insert step 6 was generated as `shutdown`/`no shutdown` (a link bounce,
NOT a real physical prompt+wait), which is a genuine criterion-4 defect the judges
should catch. Related: [[pytest-artefact-review-worklist]], [[vllm-reasoning-model-path]].

**UPDATE 2026-07-27h.** Criterion 4's "all bad" verdict was root-caused to a resourcing
gap and fixed — see [[generator-cli-hallucination]] and
[[cli-fabrication-originates-step2]]. All three cases were re-checked and re-judged after
grounding; every mechanical criterion is now clean. **The full write-up for review is
`ask-ck/pytest-create/NEXT-SESSION-REVIEW.md`** (re-checked grades, how to diff against
the preserved pre-grounding baseline via `tool/pt_compare_runs.py`, 4 regressions, and 5
open questions). Judges were Opus + **vllm-fast run 5x** to measure its own consistency —
`criterion4.json` carries a per-block `self_consistency` record. Watch out for
[[stale-session-connection-bug]] when re-running any of this.

**UPDATE 2026-07-29 — regenerated w/ Thread B + 5-model matrix + side-by-side judging.**
All 3 cases regenerated on vllm-fast against the objective-hardened prompts (objective header
now in every `.py`; T33234's duplicate-portlink lint defect CLEARED). Then a full
generation matrix (vllm-fast/thinking + claude haiku/sonnet/opus, all Thread-B prompts) was
holistically judged by opus + vllm-fast. Artifacts: `comparison/Port (7)/<case>/generate_script.json`
(+ `.judged.json`). Harnesses live in the session scratchpad (parallel_matrix / fix_claude /
pt_matrix_judge / fix_vllm_judge) — NOT yet promoted to tool/. Gotchas learned: (1) many
concurrent `claude -p` calls + ~88K-char prompts blow the 300s cap → cap concurrency at 3, use
600s; (2) the vllm judge is a REASONING model → needs max_tokens≈16000 or it returns nothing.
**Result:** T33233/T33235 → "good" (sonnet/opus) = Thread B fixed the generation half; **T33234
= 10/10 "bad"** (both judges, all 5 models) root-caused to sequence `kind` misclassification —
folded into [[permutation-expander-deferred]] as the next target.

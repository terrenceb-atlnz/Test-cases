---
name: terrence-prefers-session-model-as-judge
description: For quality judging of generated artifacts, Terrence wants the session's own model (the most capable one available) to read and judge directly, not `claude -p` judge calls or the vLLM judge
metadata:
  type: feedback
  verified: 2026-09-04
---

When a task needs a quality verdict on generated output (whole-script vs per-unit, one model's
units vs another's), **be the judge yourself, in-context** — read the artifacts and grade them.
Do not fire `tool/pt_matrix_judge.py`-style judge calls to Opus or the vLLM.

**Why:** Terrence, 2026-09-04, when I proposed the matrix judge for the token-efficiency
investigation: *"Re: judging - I'd rather you be the solo-judge, as you are the most competent
model we have."* It also spends less of his seat: a judge call re-sends the whole artifact at
cache-write prices, while the session already has it in context.

**How to apply:** generation runs on the candidate models are still fine (they are the objects
being compared, not the judges). Read every candidate in full before grading, grade against the
unit's `verify` contract and the framework surface, show the evidence lines, and say what you
could not assess (e.g. behaviour on hardware). `pt_matrix_judge.py` / `pt_judge.py` remain in
the tree for batch matrix work Terrence asks for explicitly. Related: [[mutate-before-you-claim]],
[[read-the-whole-function-before-judging]].

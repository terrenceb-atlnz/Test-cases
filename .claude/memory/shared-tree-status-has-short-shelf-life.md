---
name: shared-tree-status-has-short-shelf-life
description: "This repo is worked concurrently by another stream — re-run the gate and git status before stating either; don't restate an earlier-in-session observation as current"
metadata: 
  node_type: memory
  type: feedback
  modified: 2026-07-27T03:36:26.274Z
  originSessionId: 7daaa873-01d4-42ab-836d-65d158c2ca74
---

The Test-cases working tree is shared with an **active parallel stream** (2026-07-27g: CLI-docs
grounding work — `tool/harvest_cli_docs.py`, `tool/cli_lookup.py`, `tests/test_cli_docs.py`, plus
edits inside `routers/pytest_create.py` and the prompt templates). Files appear, change and get
fixed mid-session without any action from me.

**Why:** in the 27g session close I reported "the gate is currently red from
`tests/test_cli_docs.py`" — true when observed, but the other stream had fixed it ~40 minutes
later, and I restated the stale observation in a summary without re-running. Terrence caught it
("Is this verified true as of this current moment, or a held-over memory") and asked for a durable
correction so he would not be led astray later. The real count was 208 pytest, not the 190 I kept
quoting (190 mine + 18 theirs).

**How to apply:**
- Re-run `./tool/run_tests.sh` and `git status --short` **immediately before** stating gate status
  or working-tree contents — especially in a session-close summary, which is exactly what the next
  session acts on.
- Never carry a status observation forward across a long stretch of work. Treat "the gate was
  green an hour ago" as unknown, not as green.
- When committing, stage **explicit paths**, never `git add -A` — the other stream's uncommitted
  work sits in the same files (see the 27g batches, where `pytest_create.py` had to be split
  hunk-by-hunk to avoid sweeping in their step-label change).
- Test counts drift for the same reason; prefer "my layers: N" over an unqualified repo-wide total,
  or re-measure.

See [[testing-suite-3-layer]] for what the gate actually runs.

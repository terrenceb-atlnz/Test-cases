# PyTest Creator — decisions pending for next session (2026-07-24+)

Written 2026-07-23 at end of session. This captures the adversarial-review worklist
state and the open decisions so we can resume seamlessly. Everything from this session
is committed (see the session-close commit).

## What shipped this session (all verified, all committed)

- **#3 fragment quality (partial):** added `maps_to` **phantom-step validation** in
  `gather_fragments` (`_clean_maps` — drops any `maps_to` number that isn't a real
  sequence step, so provenance/preview can't be driven by a step that doesn't exist).
  Cross-step **dedupe was already handled** (`fragments_by_key` keyed by
  `(source_id, symbol)`, merges `maps_to`).
- **#4 provenance divergence — FIXED.** `_restamp_provenance` now takes the `sequence`
  and builds the same `orig_n -> class_n` remap the preview uses, so a fragment mapped
  to original step 3 stamps `TestCase_2` when a setup step was dropped ahead of it.
  Previously it keyed `maps_to` (original numbers) directly by the `TestCase_<n>` class
  number — those diverge the moment any setup step precedes a verify step, mis-stamping
  the wrong fragment's tag and leaving the real first TestCase unstamped. Unit-verified.
- **#5 guaranteed-fail default — NO CHANGE NEEDED.** The `if False:` / `output = ''`
  scaffolding is intentional (the LLM must replace it), and `_lint_generated` already
  hard-rejects a saved script that still contains `>>> FILL`, `output = ''  # >>> replace`,
  or `if False:  # >>> replace`. The failure mode is already blocked.
- **#7 zero-reuse marker — ADDED.** The fragment preview now emits a positive
  `# ===== NO REUSE — ... Generate writes it from scratch =====` marker on any **verify**
  TestCase with no mapped fragment (physical/manual steps excluded — they generate their
  own interactive pattern, so a missing fragment there is expected, not a gap). Gaps are
  now visible by presence, not inferred from silence.

## OPEN DECISIONS — need your call before I implement

### D1. Fragment granularity: whole-class vs. method/line-level extraction
**The issue the review raised:** `_resolve_symbol_code` pulls the WHOLE class (up to 60
lines past the class def, capped 8000 chars) for a `TestCase_<n>` symbol. The artefact
then carries big commented reference blocks → ~64% comment bloat in the T33233 preview.

**Why I did NOT just change it:** these blocks are *reference material the Generate LLM
adapts*, not verbatim inserts — the LLM reads them, keeps the proven CLI/parsing, and
writes fresh code into the FILL slots. Trimming to just the `main()` body would need the
scripts index to carry per-method line locs (it currently carries only class-level
`loc`), which is an index-schema change + a re-index. `ck.db` is the permanent committed
source of truth — **we do NOT rebuild it** — so this can't be a silent re-derive.

**Options (pick one):**
- **(a) Leave as-is.** Whole-class reference blocks; accept the verbosity. Cheapest;
  the LLM already handles it. *(my default recommendation)*
- **(b) Trim at render time.** In `_assemble_fragment_preview`, show only the `main()`
  body of a `TestCase_<n>` fragment (regex the `def main` slice out of the stored code)
  for the COMMENT preview, while still handing the full code to Generate. Display-only,
  no index change, no db rebuild. ~1hr.
- **(c) Method-level index.** Extend the scripts index with per-method locs so fragments
  can be genuinely method-scoped everywhere. Correct but touches the index schema and
  needs a controlled `ck.db` update — heavier, and bumps against the "never rebuild db"
  invariant. Only if (b) proves insufficient.

### D2. Per-step fragment cap
You explicitly said **"no cap"** for the Fragments display, and I've respected that. The
review suggested a per-step *sanity* cap (catch the LLM dumping 15 near-identical frags
onto one step). The redundant-accounting UI already surfaces duplicates as nested
faint-red entries, so the dump is *visible* rather than hidden.
**Decision:** keep no cap (consistent with your instruction), OR add a soft cap that only
affects auto-selection (chosen stays ≤N, extras demote to redundant). Default: **keep no
cap** unless you've seen a real dump in testing.

### D3. Py2 / old-framework contamination in fragments
The review flagged that some reused fragments come from Py2-era or pre-`framework`
scripts (old idioms, `print` statements, deprecated APIs). We have no filter — a stale
fragment can seed bad patterns into Generate.
**Options:**
- **(a) Do nothing** — rely on lint + the reviewer eyeballing the preview. *(current)*
- **(b) Soft-warn** — flag fragments whose code has Py2 tells (`print `-statement,
  `except X, e:`, `iteritems`, `has_key`) with a preview banner, no auto-drop.
- **(c) Score-demote** — down-rank such scripts in Step-3 search so they surface less.
Recommend **(b)** — cheap, non-destructive, keeps the reviewer in control.

## How to resume
Say e.g. "D1: option b, D2: keep no cap, D3: option b" and I'll implement in one pass.
The physical-step classification only appears after **re-running Sequence (step 2)** on a
case with plug/unplug steps (T33233 steps 3/4) — existing sequences default to `verify`.

## Verification done this session
- provenance remap unit test (divergence corrected: class#1←fragA, class#2←fragB)
- all four step kinds render + `py_compile` clean; setup→configure(), physical→wait-loop,
  manual→yesNo, verify→normal
- preview gap-marker test: 1 NO-REUSE on the uncovered verify step, none on physical
- both routers import clean; all four jinja templates parse

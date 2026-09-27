---
verified: 2026-09-28
---
# PLAN — The family library comes first: read it at fragment selection, dedupe by job, not by name

> ## Status (read first)
>
> **PLAN ONLY — nothing below is started.** Written 2026-09-28 at Terrence's request: *"did we
> make it so Families check their own library before deciding they need one? Ideally anything
> that goes to the Library should probably read it first, before we have more doubling again."*
> and, on the plan: *"I absolutely DO want a plan for the family libraries to be incorporated
> more closely, and included at fragment selection (after theyre at least partially built)."*
> Every claim in §0 was checked against the code on 2026-09-28. §3 holds the decisions this
> needs from Terrence before work starts.

## 0. What exists today (verified 2026-09-28)

The family library is `generated/<family folder>/library_<family>.py`, one per group, merged
never overwritten (tag-keyed members; `_merge_library_code`), the ART shape (memory
`art-suite-shape`). Since G7 / G14 (2026-09-24, `ab8fa88`):

- **At assembly** (`_build_library`, `routers/pytest_create.py` ~1990–2180): the family file is
  read from disk (`_read_family_library`) and **a selected fragment whose top-level NAME the
  family already defines is not shipped** (`family_replaced`); the family's public helpers are
  listed by signature (`family_members`) and the generate prompts
  (`pt_generate_script.jinja` §"The group's own helpers", `pt_generate_step.jinja` ~133) say
  *call these, with these signatures, rather than writing or adapting another*. The returned
  library code is the family file with this build's new members merged in.
- **Review and Fix** see the library (`_library_prompt_context`; `pt_review_script.jinja`
  "Helpers this script imports (authoritative)"; `pt_fix_script.jinja` the same), so a finding
  that contradicts a helper's docstring is a false positive by rule.
- **The save's clash guard (G3)** refuses a library merge that would redefine a name.

So "read it first" is true at the assembly seam — **by name only**, and one step too late.

## 1. The gaps (the doubling Terrence means)

1. **Fragment selection is blind to the library.** `gather_fragments` (~5573) renders
   `pt_gather_fragments.jinja` from the sequence and the step-3 scripts' symbols only. The
   model picks corpus fragments for every step, including steps a family helper already
   serves. T33235's own gather chose legacy `library_5000` helpers whose *names* the family
   file had (`configurePort` with a different sixth argument) — caught at assembly because the
   names clashed. The uncaught twin is a helper with a **different name and the same job**
   (`waitLinkUp` beside the family's `waitForLinkState`): it ships, and the library doubles.
2. **Dedupe is lexical.** `_library_top_names` compares names. Nothing compares what a
   fragment does with what a family member does.
3. **No lint sees a local twin.** A `def` written inside a unit (or at module level in the
   script) that reimplements a family member passes every check; only the library merge is
   guarded, and only by name.
4. **"Partially built" is real.** The family file exists only after the group's first save.
   The first script of a group has nothing to read — by design — and the second script is
   where doubling starts. Nothing today tells the second session that the file now exists.

## 2. Proposal — smallest first, each with tests and a mutation check

- **P-A — the gather step sees the library.** In `gather_fragments`, when
  `_read_family_library(_effective_group(sess), _family_for_group(group))` is non-empty, pass
  `family_members` (from `_library_signatures`) to `pt_gather_fragments.jinja`. New prompt
  section *"The group's own library — `library_<family>.py`, already imported by every script
  in this group"*, and two rules: a step a member serves is **covered by the library** — list
  the member under `chosen` with `"source_id": "library"` (no corpus fragment for that job);
  and if a corpus fragment genuinely does the job better, choose it AND name the member it
  supersedes under `"supersedes"`. Server side: a `library` choice resolves to no code
  (nothing to extract) but is recorded in `accounting` so the Fragments panel shows *covered by
  `library_9001.configurePort`*; a `supersedes` is recorded for the reviewer and shown beside
  the fragment. When the family file does not exist the section does not render (the
  `{% if %}` pattern the generate prompts already use).
- **P-B — the unit prompt's rule gets a mechanical backstop (lint `library:`).** A `def` in
  the script whose name equals a family member → BLOCKING (it shadows the import); a `def`
  whose body is close to a member's (difflib ratio ≥ 0.8 after normalising names) → warning
  naming the member to call instead. Same lint family as `unsupported:` / `published:`.
- **P-C — Review and Fix are told the library is the helper source.** One rule each: a
  suggestion never proposes a new helper the family already provides; it proposes the call.
  The library code is already in both prompts, so this is a sentence plus a test.
- **P-D — the second session learns the library grew.** The Fragments panel shows the family
  members available at gather time; `gather_fragments` provenance records the family file's
  hash so a later re-gather can say *"library changed since"*.

Order: P-A (the ask), then P-B, then P-C; P-D last. Measure P-A by re-running T33235's gather
as a provenance dry run (`dry_run`, no send) and counting chosen corpus fragments a library
member covers, before and after.

## 3. Decisions needed from Terrence before work starts

- **D1** — May the fragment reply choose a library member (`"source_id": "library"`), or is
  the library only *"do not select a fragment that does this"* guidance? (P-A proposes the
  former: it makes coverage visible and auditable.)
- **D2** — P-B's near-copy threshold, and warning vs blocking for the near-copy case (the
  exact-name case is blocking either way).
- **D3** — Does a re-gather of an existing session when the library has grown count as a
  new Fragments step (invalidating step 5 onward), or as an in-place refresh?

## 4. Invariants this must not break

- `ck.db` is never rebuilt or written outside the server; the scripts index stays as is.
- The family file is merged by tag, never overwritten; the G3 clash guard stays the backstop.
- Prompt examples are the spec (memory `prompt-examples-are-the-spec`): the new prompt
  section ships with an example that matches real data, and a test that the example renders.
- Nothing here changes the frame or the assembled-hash gating (slice A).

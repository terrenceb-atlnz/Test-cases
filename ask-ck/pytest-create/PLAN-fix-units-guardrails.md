# PLAN — Guardrail `fix_units` so it can only touch what a finding actually names

> ## Status (read first)
>
> **PROPOSED 2026-09-09 — nothing implemented.** Written at Terrence's request after the
> T44297 pass: *"a plan to guardrail the 'fix units' command so it cannot write in any other
> TC that isn't affected by an error. this is costing a lot of rework and i dont want such an
> unreliable process."* Every root cause below is taken from the code and the stored session,
> not inferred; every guardrail maps to one. Decisions D1–D6 at the end are Terrence's.
>
> Related pending items in `ask-ck/objective-drafting/PROGRESS.md` ("Pending fixes"): #4
> (constrained `kind` vocabulary — G5 depends on it), #5 (ck.db WAL-on-NFS — G4 shrinks the
> write pattern that triggered it), #6 (headless review transport).

## The measured cost that motivates this

T44297, last 24 h (debug log, `sess-pjkmca6yz2`): **3 reviews + 5 fix runs; 6 of those 8 runs
were rework.** Two review cycles (~90k input tokens each) existed only to discover what a fix
had done wrong or done to the wrong unit. The fix runs themselves were cheap; the *reviews
that policed them* were the sink. The process is unreliable in a specific, reproducible way,
described below.

## Root causes — from the code

All in `ask-ck/CK-main/CK_server/routers/pytest_create.py` unless noted.

**RC1 — the finding's `evidence` prose hijacks the target unit.**
`_unit_id_for_finding` (≈L5818) feeds `f"{where} {evidence}"` to `_unit_id_for_text`, which
tests `_TC_NAME_RX` (`TestCase_(\d+)`) **before** `_SETUP_REF_RX`. Review #2 finding 5 had
`where = "TestSet.configure"` but its `evidence` said *"…TestCase_1 logs 'STEP 1'…"* — so the
class name in the prose won and the fix landed on **tc1**, a unit the finding was not about.
`where` — the reviewer's stated location — was silently overridden.

**RC2 — scope is a suggestion, not a check.**
`templates/prompts/pt_fix_unit.jinja` says *"Change only what the findings require; keep every
other line of this unit as it is"* and lists lines to keep EXACTLY (class name,
`testCaseDesc`/`testCaseRef`/`testCaseMethod`, the three `def` signatures, the shortcut lines,
the provenance tag). `_unit_call_and_store` (≈L5432) enforces only `_unit_shape_ok` — a
shape/existence check. **Nothing diffs the reply against `current_code`; nothing verifies the
frozen lines.** Result: tc1 gained step-1 assertions and tc6 was re-implemented wholesale, both
stored as `ok`.

**RC3 — every unit is written on every fix.**
`_chunks_from_code` → `_sync` re-syncs **all** units' chunks from the assembled file
unconditionally before dispatch (to capture hand-edits). Content is a no-op for untouched
units, but it is a whole-session CAS write per fix — the very pattern behind the NFS
corruption (PROGRESS #5) — and it means "untouched" units are literally rewritten to storage.

**RC4 — a fix is trusted on shape alone.**
No check that the finding's `evidence` pattern is gone from the new unit; no isolated lint of
the returned unit before storing. The tc6 regression (fabricated `lldp_basic` attributes
`port_desc`/`sys_name`/`sys_desc`, which no scapy layer here has) was stored as `ok` and cost
a full Opus review to discover.

**RC5 — structural findings are auto-fixed like mechanical ones.**
A finding whose resolution needs a *new* TestCase, or verdicts inside the **config-only**
setup unit (the framework contract; see `[[setup-unit-re-indent-at-assembly]]`), is
indistinguishable from a one-line condition fix, so it gets regenerated like any other —
producing scope changes nobody approved (finding 5 again).

## Guardrails — one per root cause

### G1 — `where` is authoritative; `evidence` is fallback only  *(RC1)*
Resolve the target from `where` **alone** first: class name → `tcN`; setup reference →
`setup`. Only when `where` resolves to nothing, fall back to `evidence`, then `step`. A
`where` that names `TestSet`/`configure()`/`tear_down()` can **never** yield a `tcN`.
- Test (pin the real dict): review #2 finding 5 → `setup` (or unmapped under G5), **never**
  `tc1`. Existing `tests/test_pt_fix_units.py` is the home.

### G2 — the frozen scaffold is enforced, not requested  *(RC2)*
Turn the prompt's "EXACTLY as they are" list into a hard check in `_unit_call_and_store`
(extend `_unit_shape_ok` or add `_unit_scope_ok(current, new, unit)`): class name,
`testCaseDesc`/`testCaseRef`/`testCaseMethod` lines, the three `def` signatures, each method's
opening shortcut-lines block, and the provenance tag line in `main()` must be **byte-identical**
to `current_code`. Violation → `_fail("fix altered a frozen line: …")`; the old chunk is kept.

### G3 — a blast-radius diff gate  *(RC2)*
Diff the returned unit against `current_code` (line-level, `difflib`). Anchor set = the lines
in `current_code` that the finding's `evidence` matches (fuzzy) + any lint line numbers. A
change is **in scope** if it falls inside a method containing an anchor. Changes outside every
anchored method, or a change ratio above a threshold (proposal: >40 % of the unit's
non-scaffold lines), are **HELD** — status `held`, diff kept, surfaced for approval — not
stored and not hard-rejected. Rationale: legitimate fixes can be sizeable (tc6's TLV block),
so the gate flags *unexpected* breadth and a human decides. → **D1**.

### G4 — untouched units are never written  *(RC3)*
`_chunks_from_code`/`_sync` write a chunk **only when its text differs** from the stored
chunk (i.e. a real hand-edit). Identical text → no write, no `at`/`status` re-stamp. This makes
"cannot write to any TC not affected" literally true at the storage layer, and shrinks the
per-fix write footprint that PROGRESS #5 blames.
- Test (mutate-before-you-claim): run a fix targeting tc6 with a hand-edited tc9; assert tc9's
  chunk is rewritten **and** tc11's `at` is byte-unchanged.

### G5 — structural findings route to a decision, never to the fixer  *(RC5)*
Classify a finding **structural** when it maps to `setup` AND asks for a verdict/assertion (the
setup unit is config-only by contract), or its `suggestion` implies adding a case or moving a
step. Structural → `unmapped` with reason *"structural — needs a design decision"*, shown in
the UI, **excluded from dispatch**. Depends on PROGRESS #4: a constrained `kind` enum with a
`structural` value makes this routable rather than heuristic. → **D3**.
- Test: finding 5's real dict → structural/unmapped.

### G6 — verify before store  *(RC4)*
Before a returned unit is stored: (a) G2 frozen check; (b) an **isolated lint** of the unit
spliced into the current frame (unbound names, syntax — the existing linter); (c)
**finding-addressed**: when the finding carries `evidence`, that exact snippet must no longer
appear in the new unit, else `_fail("finding evidence still present")`. Any failure keeps the
old chunk and reports why.
*Honest limit:* (a)–(c) cannot catch a **fabricated scapy attribute** (tc6's phantom
`port_desc`) — that is semantics, not syntax. An optional stretch that *would* have caught it:
a `known-field` check — any `getattr(<layer>, 'name')` / `pkt[<layer>].name` on an `lldp_*`
layer must name a field seen in `library_*.py` / the framework's LLDP contrib. → **D4**.

### G7 — preview / approve mode  *(the direct answer to "unreliable")*
`fix_units` returns per-unit **diffs** and HOLDS every change (`status: held`) until approved;
an *Apply* per unit (or all) commits and re-assembles. Proposal: default **on** for
review-driven fixes (the class that drifts), **auto-apply** for lint-only fixes (deterministic,
low risk). A bad fix then costs one look at a diff, not an Opus review. This is also the
mechanism G3's "held" state lands in. → **D2**.

## Order

G1 + G5 first (targeting — they stop the wrong-unit class outright and are small) → G4 (no
untouched writes) → G2 + G6 (verify-before-store) → G3 + G7 (they share the diff machinery
and the `held` state). **Gate after every step** (`./tool/run_tests.sh`); tests never write
the permanent `ck.db`. Existing suite to extend, not duplicate: `tests/test_pt_fix_units.py`.
Frontend: the `held` state and per-unit diff need a render in `static/js/pytest.js` (G7) —
pairs naturally with PROGRESS #1–#3 (error timestamps, regenerate cue, Fix-button legend).

## Explicitly NOT in this plan

- Sending the fixer only the affected *method* instead of the whole unit. Rejected for now:
  it breaks the unit's self-containment context the prompt relies on and would fight the
  cache-shared prefix. G3/G7 get the same protection at the storage layer.
- Changing which model fixes. Orthogonal; Terrence's 2026-09-09 call (Opus for fixes, to cut
  re-review churn) stands and is not touched here.
- Whole-script Fix. Out of scope; it is the documented escape hatch for `unmapped` findings.

## Decisions needed before starting

| # | decision | recommendation |
|---|---|---|
| D1 | G3 threshold, and do lint-only fixes bypass the gate? | 40 % non-scaffold lines; yes, lint-only bypasses |
| D2 | G7 default: hold-for-approval for review-driven fixes? auto-apply lint-only? | yes / yes |
| D3 | G5: a `setup`-mapped finding that asks for a verdict → always structural (never fixed)? | yes — config-only is the contract |
| D4 | G6 stretch: implement the scapy known-field check (would have caught tc6)? | yes if cheap; it is the one check that catches the class we actually hit |
| D5 | tc1 already carries an unapproved step-1 scope change from fix run 5 — keep or revert? | Terrence's call; not a plan item, but pending |
| D6 | Land G7's UI in the same pass as PROGRESS #1–#3, or separately? | same pass — one step-5 UI change, not three |

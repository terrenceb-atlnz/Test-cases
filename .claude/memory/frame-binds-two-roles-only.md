---
name: frame-binds-two-roles-only
description: RECORD (all SHIPPED 2026-09-21) — why the generated frame used to bind only {tb, peer} with copper+fibre on ONE handle (4 of 6 highs on T33234), and the four process designs A–D agreed during that repair; the frame now binds a ROLE SET (tb/copper/fibre/cusfp, pluggables optional) — see PLAN-frame-role-set.md and PLAN-generate-state-and-sequence-sanity.md
metadata:
  type: project
  verified: 2026-09-21
---

> **UPDATE 2026-09-21 — EVERYTHING in this memory is BUILT.** Sections A–D and the FIRST TASK:
> commits 56c7022, fc8348b, f75581b (plan `PLAN-generate-state-and-sequence-sanity.md`). The frame
> itself: `e022e1c` + `6ada916` (plan `PLAN-frame-role-set.md`) — `_detect_links` returns the role SET
> `{tb, copper, fibre, cusfp}`, the frame binds one `_ck_bind_link` block per role with fixed handles
> (`portPeer`/`peer.portDut`, `portFibre`/`fibre_peer.portDut`, `portCuSfp`/`cusfp_peer.portDut`),
> pluggable roles are OPTIONAL-with-UNSUPPORTED (`<role>_supported`, media asserted by the insertion
> case via `assert_role_media_now`), `cusfp` is a profile + media role, and the preflight reads the
> role contract. The *why*s are in CHANGELOG 2026-09-21. This file stays as the record of the
> diagnosis and the agreements; nothing here is pending. T33234's live session reads `diverged`
> until Terrence clicks Re-chunk; nothing can revert the repair meanwhile.

**Terrence, 2026-09-17: "I want to repair it in the next session."** The evidence below is
already collected and verified against the code — do not re-derive it.

## The one-line statement

Generation, lint and Fix Units are all **unit-scoped**. Review is the **only** stage that reads
the assembled whole. So a defect that lives in the *relationship between* units cannot be
prevented upstream, cannot be caught by lint, and cannot be fixed per-unit — it can only be
found late and repaired by the whole-script Fix, which rewrites everything.

The biggest such relationship is the **port role contract**, and the frame is supposed to own
it — the comment block above `_skeleton_units()` in `pytest_create.py` is explicit that *"The frame is NOT a model's work."* But the
frame can only express two roles, so on a case that needs more, the `setup` **unit** invents
the rest. That is a model's work, and on T33234 the model got it wrong.

## The three-layer diagnosis (each verified 2026-09-17)

**Layer 1 — the spec collapses two roles onto one handle.**
`ask-ck/functions/pytest-creator/TOPOLOGY-PROFILES.md`, table *How the generated frame binds these*:

| Role | Binding in `init()` | Handles the units use |
| `copper` / `fibre` | `(dutA.portPeer, peer_port, peer) = self._ck_bind_link(...)` | `peer`, `portPeer`, `peer.portDut` |

`copper` and `fibre` share **one** handle set by design. A case that needs a copper link *and*
a fibre link **simultaneously** cannot be expressed. There is no `cusfp` (copper-SFP) role at
all, and steps 16/17 of T33234 need one.

**Layer 2 — the detector returns two booleans, not a role set.**
`_detect_links()` in `CK_server/routers/pytest_create.py` returns exactly
`{"tb": bool, "peer": bool}`. A *set* of roles is not representable. Note the reader on the
other side, `_skeleton_bound_ports()`, already documents a `"copper"` role in its
example docstring — the reader is general; the **producer** is the bottleneck.

**Layer 3 — so the units inherit an under-specified frame.**
The frame emits at most two `_ck_bind_link` calls. T33234 needed four roles (`copper`,
`cusfp`, `fibre`, `tb`). The `setup` unit filled the gap and bound `portA` from the **`tb`**
role — a testbox NIC — while every copper case asserted against `peer.portDut`. Two different
cables. The original Review said it verbatim:

> *"portA... binds from the 'tb' role (a testbox NIC), yet every copper case also runs
> `show interface <partner port>` and `configureDefaultPort` on `peer`/`portDut` as if
> portA's far end were the peer switch — the far end of portA is `tb.ethA`, not
> `peer.portDut`."*

## Why: the measured cost on AWPTCM-T33234

First generated script: **15 findings** (6 high / 7 medium / 2 low). Four of the six highs were
*relationships between units*, not defects inside any one unit:

1. `portA`'s role contract — `TestSet.init` ↔ every copper case
2. step-2 polarity baseline → step-5 inverse comparison — `TestCase_1` ↔ `TestCase_4`
   (nothing ever stored the baseline, so the mandatory comparison silently degraded to an
   INFO log and the case could pass without demonstrating the objective)
3. one handle serving both copper-SFP and fibre — `TestCase_16` ↔ `TestCase_17`/`_18`
   (**caused directly by layer 1 above**)
4. the same `current polarity` field adjudicated three different ways — `TestCase_9` passes on
   the field's absence, `TestCase_13` hard-fails on it, `TestCase_14` asserts it strictly

**Fix Units could not repair any of them, and the tool behaved correctly in failing.** Handed
`tc5` and asked to fix `tc5`, the model saw a class that is coherent *in isolation*, returned
the same code, and the G2/G6 guardrail rejected it as a no-op — `tc3`, `tc5`, `tc8` are still
parked under `chunks[uid].refused` in the session. `setup` and `tc4` were tagged **structural**
and routed to a design decision, so they were never attempted at all. This is not a model-
quality problem; it is asking a question the context cannot answer.

**The whole-script Fix repaired all six highs** because it had the entire 113 KB in one context
*plus* all 15 findings at once — so it could see that two symptom findings shared one cause and
fix the cause. Result: **7 findings** (2 high / 4 med / 1 low), of which one (`expect_value=True`
at `TestCase_9`) is a **false positive** — the kwarg really is declared at
`def checkConfiguredPort` in `library_awptcm_t33234.py`.

Cost of that hammer: **19 of 19 classes rewritten**, no unit byte-identical, 113 KB → 135 KB,
and it **introduced a new high** — binding `cusfp`/`fibre` at suite-init *and asserting the
media there* contradicts steps 16/18, whose entire purpose is the operator **inserting** those
modules. Terrence's ruling on that one, 2026-09-17: **bind by port reference only, defer the
media assertion until after the insertion cases.**

## How to apply

The repair is to make the role contract expressible in the **frame**, so the defect class
becomes unrepresentable rather than reviewable:

1. **`_detect_links()` → a role set.** Replace `{"tb": bool, "peer": bool}` with an ordered set
   of role names. Keep the deliberate over-inclusiveness documented in its docstring — a bound-unused
   link costs one `ck_link_*` line, an unbound-needed link costs a dead bench run — and keep the
   legacy fallback (a case naming neither side gets `peer`) or old cases regress.
2. **Add a `cusfp` role + profile** to `TOPOLOGY-PROFILES.md`, and **split `copper` from
   `fibre`** in that table so they no longer share `portPeer`/`peer`. This is the layer-1 fix and
   it is a spec change, not just code.
3. **Emit one `_ck_bind_link` per detected role** in `_render_skeleton`, with distinct
   handles. `_skeleton_bound_ports` already parses arbitrary roles, so the prompt's
   handle section and rule 3 should follow for free — verify that.
4. **Deferred media assertion** per the ruling above: bind by port reference, assert media only
   after the insertion case has confirmed the module.
5. Optional but high value: a **lint check** for cross-unit handle consistency — one unit using
   a different port handle than its siblings for the same declared role. That was a Review
   finding twice and it is deterministic.

Before editing: read the design docs first per [[pipeline-layer-contract]], and remember
[[autonomous-judgement-divergence]] — verification confirms what IS, never what SHOULD be. The
ART house shape these bindings emulate is [[art-suite-shape]]; the role/profile contract itself
is [[topology-profiles-contract]]; the preflight that catches a missing cable is
[[preflight-topology-check]]. Any renaming of handles is a frame change, so
[[setup-unit-reindent-at-assembly]] and the frozen-frame byte-identity rule documented above `_skeleton_units` both
apply.

## Adjacent bug found the same day — same root theme

**`fix_script` never syncs `step6.chunks`.** It rewrites `files.test.code`
(`fix_script`'s inner `_apply_fix` in `pytest_create.py`) and pops `review`, but leaves all 19 chunks holding the
**pre-repair** unit bodies. Since `apply_held`, `fix_units` and Assemble all
re-splice **from chunks** via `_assemble_and_store`, any of them silently destroys a whole-script
repair. The UI legend warns about *Re-Assemble* only — it does **not** name Apply held or Fix
units, which have the identical effect. `discard_held` is the one held action that
does not re-assemble, so it is safe.

This is the same theme as the main entry: the pipeline keeps **two truths** — the unit-scoped
`chunks` and the whole-script `files.test.code` — and nothing reconciles them. Either
`fix_script` should re-chunk its output through `_skeleton_units`, or the session should record
which truth is current and refuse the other path. **T33234's session is in exactly this state
right now** (iterations=2, chunks stale, held cleared, `refused` still set on tc3/tc5/tc8), so
whoever picks this up must not press Assemble on it.

## The UX half — Terrence, 2026-09-17, looking at the live panel

> *"This is a bad place for a casual user to be."*

Observed on the step-5 Generate panel with the session in the desynced state described above.
The server bug is only half the repair; the panel is the other half.

- **Zero UI indication that anything will break.** Five buttons silently destroy the repair and
  none of them says so. The legend's only caution is *"Don't re-Assemble after THAT one"* — it
  names **Re-Assemble** and not `Fix units`, `Apply held`, `Assemble + settle` or
  `Generate all units`, which have the identical effect.
- **Every pill is green.** `setup` + 1–18 all show ✓, `19/19 unit(s) generated`, `lint OK`,
  2 non-blocking style warnings. The green reports on the **chunks**, which are the stale copy.
  Nothing on screen distinguishes "these units built the file you are looking at" from "these
  units are a previous draft that will overwrite it".
- **Findings are attributed to units that did not produce them.** The 7 findings are keyed
  `TestSet.init`, `TestSet.configure`, `TestCase_7`… but Review ran **after** `Fix whole script`
  rewrote the file, so they describe code that exists only in `files.test.code`. The unit page
  for `setup` still shows the old, green, superseded body.
- **The UI actively recommends the destructive action.** The findings block reads *"feed to the
  Fix button (here, or on step 7 Validate)"* — and `Fix units` is one of the five that destroys
  the repair.
- **Token cost is large and mostly invisible.** On this case: Review 54.6k in / 12.7k out
  (67.3k), whole-script Fix 45.6k in / 52.9k out (98.5k) — on top of a full per-unit generate
  and an 11-unit Fix Units round whose 8 held fixes were all ultimately discarded.
- **Nobody reaches this state unaided.** *"A user couldn't get this far without CLI claude
  helping them in the first place."* Working out which button was safe meant tracing five
  endpoints to `_assemble_and_store` in the router. That is not a reasonable ask of the panel's
  user.

Minimum viable shape for the UI half: the session records **which truth is current**
(unit-spliced vs whole-script), the panel states it plainly, the buttons that would switch
truths are disabled or gated behind a confirm naming what is lost, and the unit pills stop
reading green once they no longer describe the assembled file. Verification per
[[user-prefers-manual-ui-testing]]. This is the same failure class as
[[silent-degradation-audit-2026-07-30]]: a polite green surface over a feature that is not doing
what the user believes it is doing.

## AGREED DESIGN for the UI/state half — Terrence confirmed 2026-09-18

Principle: **derived state must be bound to its source by a hash, never by a flag a writer has
to remember to set.** Two instances, same fix shape.

### A. Units vs assembled script ("two truths")

1. **Divergence is computed, not stored.** Every assembly already records `step6.assembly`;
   add the hash of the code it produced. `diverged = hash(files.test.code) != assembly.hash`.
   True exactly when re-splicing the units would NOT reproduce what is on screen — i.e. exactly
   when the unit-level buttons are destructive.
2. **Server enforces first.** `assemble_script`, `assemble_and_settle`, `fix_units`,
   `apply_held`, `generate_units` → **409** when diverged, with a message naming what would be
   lost and how it got there ("changed by whole-script Fix at HH:MM / hand-saved at HH:MM").
   **No force override** (Terrence's call): the only exits are Re-chunk or Discard.
3. **UI mirrors the server fact.** Those five buttons disabled with the 409 text as tooltip; a
   banner on the Summary page ("Script is ahead of its units — units are stale"); unit pills
   switch from green ✓ to a grey/⚠ state so they stop asserting they describe the file. Safe
   set stays live: Re-lint, Review, Fix whole script, Save, Discard held. An **unsaved hand
   edit in the code box also greys them client-side** (the one case the server cannot see).
4. **Re-chunk** — a LOCAL action that runs the existing `_skeleton_units()` parser over the
   current script and rebuilds `chunks` from it: divergence → 0, pills honest, buttons re-enable.
   **`fix_script` must call it itself** so a whole-script Fix never leaves the units stale; the
   disabled state then only ever arises from an unsaved hand edit — exactly when a human should
   be asked. This is the fix to the disease; 1–3 make the symptom impossible to walk into blind.

### B. Review findings vs the code they reviewed

Today `fix_script` and `apply_held` pop `step6.review`; **`save_script` does not**, so a hand
edit (or a headless save) leaves the previous findings on screen as if current — observed
2026-09-18: the `TestCase_15` finding still displayed, quoting a `SKIPPED:` line that no longer
existed in the file.

1. **Stamp `review.code_hash`** when Review runs. Valid iff it equals `hash(files.test.code)`.
   Every present and future code writer invalidates it for free.
2. **UI renders by that fact.** Match → findings as now. Mismatch → collapse to one line:
   *"N findings from a previous version (HH:MM) — the code has changed since. Run Review."*
   Kept as history, never shown as current.
3. **Per-finding "still there?"** — reuse Fix Units' existing *finding evidence still present*
   check: test each old finding's quoted `evidence` against the current code. Gone → **likely
   resolved**; present → **still present**. Deterministic and honest about its limit ("evidence
   gone" ≠ "defect proven fixed"); it prompts a re-Review, it does not replace one.

Both A and B belong in the same session as the frame repair above; A.4 (`fix_script` re-chunks)
is the smallest change with the largest effect and should land first.

## C. Sequence sanity — Terrence's shape, confirmed 2026-09-18

**Why (measured on T33234):** sequence step 5's verify ("inverse assignment at each end AND still
complementary" over a crossover cable) contradicts physics — exactly one end flips, the ends
MATCH — and steps 6 and 7 both claim to be "the matched pair" over the same crossover cable.
Neither was caught until a review pass 20+ hours later, because **every stage after Confirm
Step 2 treats the verify text as an axiom**: Generate implements it faithfully (TestCase_4 is a
correct implementation of a wrong sentence), lint is semantic-blind, and Review's prompt says the
verify "is the contract" so it can only report code-vs-text. Two humans read the steps for
OVERLAP and missed a PHYSICS error — reading for one property does not catch another. Same
origin as [[cli-fabrication-originates-step2]]: born at step 2, amplified downstream.

**The plan (Terrence: "not exactly the way you've presented"):**

1. **Sanity is baked INTO the Extract Sequence call** — not a separate pass. The call that
   assembles the sequence also checks it: (a) cross-step consistency (two steps cannot both be
   the matched pair over one cable; a later step must not presume state an earlier step
   cleared) and (b) domain invariants. "If the LLM call assembles the sequence, it should ALSO
   check it — there's really no reason not to."
2. **The invariant check lives in that same call, and the CLI reference rides with it** to stop
   drift. `pt_extract_sequence.jinja` ALREADY receives `cli_reference`
   (`_cli_reference_for_case`), so the CLI half exists; what is missing is a maintained
   **domain-facts block** the prompt reads — crossover vs straight-through pairing, an auto-MDI
   partner adapts to either forced role, fibre has no MDI/MDI-X, `configured` vs `current`,
   half duplex impossible ≥ 1 Gig ([[awplus-speed-duplex-constraint]]). Today those facts live
   only in memory files; they need a home the prompt can read (a `ck.db` facts table is the
   natural one — the server reads corpora only from `ck.db`).
3. **A claims table on the Sequence page**: per step, the physical claim in one line plus the
   expected link/device state ("Step 5 — crossover, both auto → ends complementary" beside
   "Step 6 — crossover, DUT forced MDI → matched pair" is visibly wrong where two paragraphs of
   prose are not). Not needed for every script; Terrence: invaluable for **negative testing and
   steps that change device state**. Render it from the sanity output of (1), so Confirm Step 2
   is a judgement a human can actually make at a glance.

Not adopted (recorded so it is not re-proposed as new): a Review-side `sequence_defect` finding
kind. Terrence placed the check at step 2, where the text is born, not at Review.

**The two sequence defects this would have caught were RESOLVED by hand on 2026-09-18**
(Terrence: "Do A and B"): steps 5/6/7/9/10 rewritten for auto-partner physics (A) and real
negatives by forcing the PARTNER role (B); TestCase_4/5/6/8/9 rewritten to match; step 15's
TestCase_14 lost its down-link allowance the same day. The repaired `test-9000.33234.py` was
saved through the UI after a clean Review. Terrence then clicked Generate by mistake (my
instruction "5. Generate → Summary" read as a button), which produced 19 FRESH units in
`step6.chunks` that were never assembled — the two truths now diverge maximally on this case,
which is exactly what section A's hash-bound gating is for.

## FIRST TASK next session (Terrence, 2026-09-18: "leave it" for now)

**T33234's session still holds 19 fresh, unassembled units** beside the saved script. Nothing in
the current server can drop them: every session write goes through the PT endpoints and none
resets the Generate step (`clear_session` wipes steps 2–4 too; rebuilding steps 3–4 needs their
LLM searches again). Terrence declined a same-day backend change because saving any
`CK_server/*.py` bounces production while another seat was connected
([[editing-backend-restarts-production]]). **Until this lands, do NOT click Assemble on
T33234** — it would splice the fresh units into the frame and discard the repair (the file is
committed in 2a1be33, so it is recoverable, but that is not "no accidents").

Build first: `POST /reset_generate/{key}` — lock-gated; steps 1–4 untouched; step6 becomes
`{files, lint, naming}` only (no chunks/review/assembly/settle/fix_units/lint_history),
`confirmed=False`, `_invalidate_from(sess, 5)`. Every splice path then 409s "missing units"
until Generate is run deliberately. ~25 lines + a test; it is the first slice of section A.
Then run it against T33234 and Terrence re-confirms Generate by hand.

## D. Review is blind to the suite library (found 2026-09-18, DEFERRED)

`review_script` renders `pt_review_script.jinja` with `code`, `sequence` and `lint_findings`
only. The script does `from library_awptcm_t33234 import *`, and the library ships beside it
(`generated/Port/library_awptcm_t33234.py`), but the reviewer never sees it. On the final
T33234 review **4 of 5 findings were this one blindness**: `waitForLinkState(..., 'down')`
(the helper handles 'down' explicitly, twice flagged), `checkCurrentPort(..., 'auto', 'auto',
...)` (the helper treats 'auto' as "value present"), and `expect_value=True` (declared in the
def; also the false positive of 2026-09-17). They will recur on EVERY review of every suite
until fixed.

**Repair:** pass `step6.files.library.code` (when present) into the review prompt as a
read-only "helpers available to this script" block, and tell the reviewer that any symbol
defined there is in scope and its documented behaviour is authoritative. Same for
`fix_script` — a whole-script Fix that cannot see the library will "fix" a correct call.
Cheap, no design decision needed; do it alongside section A.

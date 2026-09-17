---
name: frame-binds-two-roles-only
description: DEFERRED repair (agreed 2026-09-17) — the generated frame can bind only {tb, peer} and TOPOLOGY-PROFILES collapses copper+fibre onto ONE handle, so a multi-role case forces the setup UNIT to invent the role contract; that was the single cause of 4 of 6 high findings on T33234
metadata:
  type: project
  verified: 2026-09-17
---

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

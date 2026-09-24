---
verified: 2026-09-24
---
# PLAN — what driving T33235 through the PyTest Creator exposed (2026-09-24)

> ## Status (read first)
>
> **PLAN ONLY — nothing below is started.** Written at Terrence's request after the T33235 script
> was finished by hand (`generated/9001_Port/test-9001.33235.py`, lint-clean, preflight RUNNABLE on
> tb470). Each item names the evidence from that drive. Four guard defects found on the way were
> fixed the same day and are listed only for completeness (§0).
>
> **Decisions needed from Terrence before work starts:** D-A (how many tool review rounds, and
> who stops them), D-B (does T33234 get the UNSUPPORTED fix now), D-C (headless agent path: build
> or not). Two script choices Claude made while finishing T33235 are at the end for review
> (R1, R2).

The drive: fresh sequence extract → per-step script matches → fragments → 34 units (22 Opus, 12
Sonnet after the seat's weekly limit hit) → assemble → **four** tool reviews and three Fix rounds
→ a hand-merge → a hand-finish and self-review. The tool review/Fix loop is where most of the time
and tokens went. Terrence: *"we are already two-reviews past what i want the tool to actually do.
which means theres yet another breakdown in the process, and we need to fix it soon."*

## 0. Fixed on 2026-09-24 (for reference)

| id | defect | fix |
|---|---|---|
| G1 | evidence guard refused a fix when ANY quoted line survived | refuse only when every judged line survives |
| G2 | lint read `self.testSet.X = …` (a published value) as an unbound device | counts as a binding |
| G3 | library merge appended same-name helpers → duplicate `def`, later wins | 409, nothing written |
| G4 | frozen-line guard froze every `x = a.b` body line after Re-chunk | freezes only same-name shortcuts |

All four: tests in `tests/`, mutation-checked, deployed by Terrence (the auto-mode classifier
refuses Claude's copy into `CK_server/` — see §7 P4).

## 1. The review/Fix loop overruns — do first (Terrence: "fix it soon")

- **P1 — no bound on review rounds, no cost shown.** Four reviews of one script, each ~355–375k
  prompt characters on Opus; the last two were of a script Claude had hand-merged. Nothing tells
  the user a round's size or stops a fifth.
  *Proposal:* show the prompt size/cost of a Review before it is sent; after a hand edit
  (`save_script` with code), mark the tool review as not-the-next-step and offer "review in
  session" instead; a per-script round counter on the Generate panel. **D-A:** what is the
  intended number of tool review rounds (one?), and should the tool refuse more or just warn?
- **P5 — `fix_units` has no unit filter.** It re-dispatches every unit with a mapped finding, so
  stale findings re-fix units already fixed. *Proposal:* `{"units": [...]}` like `apply_held`, and
  drop findings whose unit changed since the review (the review already carries a code hash).
- **G5 — the evidence guard cannot see a moved line.** tc20's defect was *where*
  `logBefore = dut.cmd(...)` ran; the correct fix moves it and is refused. *Proposal:* when every
  judged line survives but their order relative to the unit's other lines changed, accept.
- **G10 — review advice can contradict the lint** (G2 was the instance: the review asked for
  `self.testSet.X`, the lint refused it). *Proposal:* a test that renders each review suggestion
  shape the prompt teaches and lints it.

## 2. Framework facts the units got wrong — prompt + lint

Each was found in Claude's own review, hand-fixed in T33235, and would recur on the next case.

- **G11 — UNSUPPORTED is taught wrong and reports ERROR.** Framework `ATTestCase._get_result`:
  no pass and no fail → ERROR; `supported=False` + a fail → UNSUPPORTED; `supported=False` + only
  passes → ERROR. `main()` runs even when `configure()` set the flag. ART writes
  `self.supported = False` then `self.failed('reason')` (224 of 352 uses in ck.db's ART corpus).
  `pt_fill_rules.jinja` §3d teaches `self.supported = False; self.log(...); return`.
  *Proposal:* correct §3d (and the `pt_generate_step.jinja` role notes); a lint: a
  `self.supported = False` with no `self.failed(` before the method returns is an error.
  **D-B:** T33234 has 8 such paths — fix now (hand, no tool round) or leave until it is next run?
- **G12 — units key `show system pluggable` on `port1.0.x`; the table prints `1.0.x`.** Five
  units and one refused reply; every module-type decision silently fell back. `ck_media`
  (`ask-ck/tools/pt_media.py`) already parses it. *Proposal:* the fill rules point pluggable
  questions at `ck_media.pluggable_ports` / `is_pluggable`; a lint for `show system pluggable`
  output matched against a `port…` name.
- **G13 — units are not told about the post-tear-down configuration check** (`confCheck=True`
  by default: running-config after each case's tear_down must equal the TestSet's). One unit reset
  with `speed auto` instead of the documented `no speed`. *Proposal:* one rule in the fill rules
  (restore with the documented negation, both ends); a lint pairing config changes in
  configure/main with a reset in tear_down (the audit script from the T33235 review is a start).

## 3. Cross-case values have no contract

- **G6 — units invent their own schema for a shared value.** TestCase_28 wrote the step-29
  reference as `{status_duplex, …}`; TC29 read `{row, current}`; TC30 read `{duplex, speed,
  current}` → TC29 failed every port, TC30 compared nothing. 15 units hard-coded `'100'`/`'1000'`
  instead of reading step 14's S.
- **G15 — no "producer failed" path.** When step 14 finds no S, 15 later units crash or send
  `speed None`.
  *Proposal (one design for both):* the sequence step that produces a value declares it
  (`publishes: speedS`), the frame declares the attribute in `TestSet.init` with its shape, and a
  consumer's unit prompt receives the producer's declaration plus the rule "if it is None, report
  UNSUPPORTED with a reason". This is the missing piece behind review findings #5, #6, #8, #9,
  #10, #15 of T33235's review #3.

## 4. The family library should be the helper source

- **G7 — fragments pull legacy helpers that collide with `library_<family>.py`.** T33235 selected
  `library_5000` helpers whose names exist in `library_9001` with different contracts
  (`configurePort`'s 6th argument: expected outcome vs settle seconds).
- **G14 — assembly rebuilds the session library from fragments**, so a hand-set family library is
  replaced again on the next re-assembly (G3's guard caught it on save).
  *Proposal:* generation reads the family library first; its members are offered to units as the
  helpers to call (signature + one line), and a fragment helper whose name the family already
  defines is dropped from the library build. Then G3's 409 becomes rare instead of routine.
- **G8 — `library_9001.configurePort` raises KeyError for a setting it cannot read back**
  (`'no', 'speed'`). *Proposal:* `_field` returns None for an unknown name. Shared with T33234 —
  hand edit to a merged member, which the merge keeps.
- **G9 — legacy `checkLinkStatus` greps `sh int <port> brief` for `connected`**, which brief never
  prints; every model that copies it writes a poll that cannot pass. *Proposal:* mark that fragment
  in the index (or prefer the family version by name, which G7 does anyway).

## 5. Sequence extraction and matches

- **S1 — the extract prompt still writes mid-run pluggable swaps.** The 2026-09-23 precondition
  ruling changed T33234's code only; `pt_extract_sequence.jinja` still says to write operator
  swaps. *Proposal:* the physical-step rule says fitted pluggables are a precondition; an insert or
  swap step is written only when the case is ABOUT insertion.
- **S4 — "try every speed on every script"** had to be hand-written into each sweep step; the
  extract skips values it judges not applicable. *Proposal:* an extract rule — a value the command
  documents is attempted everywhere; the verify is accept-if-legal / reject-if-not.
- **S2 — `save_sequence` keeps `step3.step_matches` keyed by old step numbers.** *Proposal:* drop
  matches whose step text changed (or all, when the shape changed — the sanity flags already do).
- **S3 — `save_sequence` leaves `step2.notes` describing deleted steps.** Harmless today (nothing
  reads it); clear or mark it stale.

## 6. Transport and seat

- **P3 — the seat's weekly limit hit mid-generate.** 12 unit jobs failed; they were regenerated on
  Sonnet from the UI. *Proposal:* the unit status shows "failed: seat limit (resets …)" distinctly
  from a model error, and Generate stops dispatching after the first limit error.
- **P2 — no headless path for `claude_agent`.** Driving the API needed a hand-written broker
  (`/api/agent/next` → local agent `/run` → `/api/agent/result`). **D-C:** is headless driving a
  supported use (then ship the broker as a tool), or was today a one-off?

## 7. Process and tooling

- **P4 — server changes need Terrence to deploy.** The classifier refuses Claude's copy into the
  live tree. What worked: patch in the scratchpad, tests + mutation in a scratch copy of
  `CK_server`, one `cp` by Terrence, then Claude checks the worker restart time, `/health` and the
  gate. *Proposal:* write that down in SERVER-README as the procedure.
- **B1 — `pt_preflight`'s hint path** (`~/claude/device-testing/…`) does not resolve on the dev host.

## For review — script choices Claude made while finishing T33235

- **R1 (tc3, step 4; and TC2, step 3) — who decides whether 10/100 is legal on the copper test
  port.** Options: (a) assume legal everywhere (false-fails a 1000 Mbps-only copper SFP); (b) infer
  from `show system pluggable` Type (unreliable: a copper SFP reads `1000BASE-T` whether tri-speed
  or not); (c) a fixed port must accept; on a copper SFP the DUT's answer decides and that branch is
  verified. **Chose (c).**
- **R2 — steps 29–31 with no monitored port bound → UNSUPPORTED** (Terrence chose this, option a).

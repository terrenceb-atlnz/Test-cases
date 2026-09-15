# PLAN — Self-healing generation: prevent, detect on arrival, correct bounded, measure

> ## Status (read first)
>
> **REVIEWED 2026-09-15 — every decision made (D1–D6, §5); the §6.4 thresholds accepted; nothing
> built yet.** Build order (§4): R2 + R3 + R5 first, then R1 (+ R1(b)), then R4, then the D6
> re-measurement and R6. Each step gated and smoke-tested on the scratch server before the
> hosted tree changes. Grew out of the guardrails plan's proof run (`PLAN-fix-units-guardrails.md`,
> complete the same day): the fresh Generate → Assemble on T44297 produced 9 lint errors in
> 38 units, every one of a class the tool can already detect, and every one still needing a
> person to read the summary, pick units, press Fix and re-assemble. Terrence's framing:
> *"we are trying to make the tool robust enough to handle these errors without having to drive
> a concurrent CLI session as well."* This plan is for every protocol, not LLDP.

## 1. The evidence — three runs on AWPTCM-T44297

| run | what came out | how it was found |
|---|---|---|
| 2026-09-08 first ART-frame pass | lint CLEAN; 3 `NameError`s hidden in it (`analyse_lldp_packets` × 7 units, `re` × 4, `LLDP_PHONE_PKT`) | by reading; became `_lint_unbound_names` |
| fix run 5 (2026-09-10) | tc1 undid the suite's `lldp run`; tc6 read fabricated fields (`port_desc`, `sys_name`, `sys_desc`) | by review + reading; became G8(b) and D4 |
| **2026-09-15 proof run** (Sonnet units, new prompt, all guardrails) | 38/38 units ok in 14 min; assembly lint **1 blocking + 8 policy**: `LLDP_PHONE_PKT` undefined in tc28; tc12/tc25/tc33 toggle `lldp transmit`/`lldp receive` the suite owns; **0 fabricated fields** | by lint, at Assemble |

Every error so far belongs to one of four classes, and none of the classes is about LLDP:

| # | class | example | today |
|---|---|---|---|
| 1 | a name lifted from context that nothing defines | `LLDP_PHONE_PKT` — six OFFERED fragments (ART 1332 method bodies) call `sendp(LLDP_PHONE_PKT, …)`; the module-level definition in `library_1332.py` was never offered, so the model used a name it had seen and nothing shipped it | detected at Assemble (`_lint_unbound_names`); nothing prevents it |
| 2 | state the suite owns, touched by a case | `no lldp transmit` / `lldp transmit` in a case's `main()`; `lldp run` in fix run 5. Any protocol has a global enable: spanning-tree, IGMP snooping, LACP | prompt block G8(a) + lint G8(b), at Assemble; Sonnet still did it in 3/38 |
| 3 | vocabulary that does not exist | fabricated fields (D4), CLI output formats, framework methods | **prevented**: declared vocabulary in the prompt, the same list in the lint (fields, methods, CLI reference) |
| 4 | semantics only a reviewer sees | verdict mismatch, weak observation, missing precondition, cross-unit inconsistency | Review → held fix → human Apply (G7). Correctly manual |

The pattern of the last two weeks is that each class we hit became a lint. That is the right
pattern, and it leaves the loop itself — read, pick, Fix, re-assemble, repeat — in a person's
hands. This plan gives the loop to the tool for classes 1–3 and leaves class 4 and the bench
where they are.

## 2. Principle — four layers, in order of leverage

1. **Prevent** what has a single root cause (class 1: the fragment set is not closed).
2. **Detect on arrival**, not at Assemble — the fix path already has the machinery.
3. **Correct automatically, bounded**, for lint-class defects only, reusing Fix units.
4. **Measure**, so a prompt or lint change is judged by class counts across cases, not by one
   run and someone watching.

What stays manual, by decision: applying a review- or run-driven fix (G7's hold is the cheap
approval for a judgement call), and anything that touches hardware.

## 3. The work

### R1 — Fragment closure  *(prevents class 1)*

**Now:** `_build_library` copies each SELECTED stand-alone fragment verbatim and already
computes its unresolved names (to refuse members that would die at import). A fragment that is
*offered to adapt* (a method body) is shown with whatever module-level names it uses, and
nothing carries their definitions.

**Change:** for every offered or selected fragment, resolve its free names against the SOURCE
suite — the script's own module level and its `library_<suite>.py` (both are in `scripts`) —
and treat a resolved module-level definition (constant, helper, class that is not a framework
dupe) as a **dependency**: pulled into the suite library under its own provenance tag,
recursively until closed, or, per D4 below, listed on the fragment card at step 4 as
"needs `LLDP_PHONE_PKT` from `library_1332.py`" with a one-click add. The prompt then says the
same thing it says today — call it by name, never paste — and it is true.

**Touch points:** `_build_library`, `_fragment_source_text` (+ a sibling-library lookup by
suite directory in `db.py`, read-only), the step-4 fragment cards in
`frontend/ck-main/current/pytest-creator/`, `_lint_unbound_names` (unchanged; it is the oracle).
**Test:** the real T44297 fragment 14 closes to `LLDP_PHONE_PKT`'s definition; a fragment whose
dependency is a framework layer stays a `framework_dupe`; a dependency that cannot be resolved
is reported, never guessed.

**R1(b) — one library per group (Terrence, D4).** We are re-structuring ART's features into our
own suites, so the library is OURS, not ART's: named after the script's mother folder
(`library_management.py` for `Management/…`, `library_port.py`, …) until a suite naming
convention is settled — today it is `library_<case>` (`_library_stem`). Consequences:
- **Merge, never overwrite.** Two scripts in one group write the same file, so persisting a
  library MERGES members into the existing one, keyed by provenance tag (one tag = one member);
  a member already present is left byte for byte.
- **Auto-added members are marked** (`# AI: dependency of <fragment tag>` under the provenance
  tag) and only those are ever removed by the tool.
- **Prune precisely.** After review, an auto-added member that no script in the group references
  (the unbound-names walk in reverse, over every script in the group folder) is removed — that
  member only, nothing else in the file moves. Reviewer-selected members are never pruned.
- A later **polishing pass** over scripts and libraries is expected; this plan does not do it.

### R2 — Arrival-time lint  *(detects classes 1–3 within seconds of the reply)*

**Now:** `_unit_call_and_store` runs the shape check on every reply and the full guard
(`_unit_frozen_ok`, `_unit_evidence_gone`, `_unit_lint_regression`) only when the caller passes a
`guard` — fix passes do, `generate_units` does not. The whole-file lint first runs at Assemble.

**Change:** generation passes a **generation guard**: the current unit is empty, the assembled
code is the partial assembly `_assemble_units(ctx, chunks-so-far)` (missing units keep their
frame placeholders), and the lint result is scoped to **errors whose line maps into this
unit** — never the unmapped ones, because the placeholders of units not yet generated raise
`contract:` errors that are nobody's fault yet. The per-unit checks that matter here are already
per-line: unbound names, suite-owned commands, port owner, layer fields, verdicts in
`configure()`/`tear_down()`. Coverage and completeness stay Assemble-only.

**Touch points:** `generate_units._prepare` / `_one` (build and pass the guard),
`_unit_lint_regression` (a `scope` flag: mapped-to-this-unit only), `_unit_call_and_store`
(no change to the store shape). **Test:** a generated reply that re-issues a suite-owned command
is refused at arrival with the G8(b) text; a reply using `getattr(layer, 'port_desc', None)` is
refused with the D4 text; the placeholders of ungenerated units never refuse anything.

### R3 — One repair turn  *(corrects what R2 catches, without a person)*

**Now:** a refused fix keeps the current unit; a failed generation shows FAILED with the reason
and the UI says "re-run them individually".

**Change:** when the arrival lint refuses a **generated** reply, re-prompt the same unit once,
same model, with the unit prompt + its own reply + the exact lint text ("your reply was refused
because …; return the whole unit again"). Store the repaired reply if it passes; otherwise store
the unit as `error` with the lint text so the pill and the unit page show *why*, and nothing is
stored silently. Bounded to one turn (D1). Two invariants on the repaired reply, from §6.2:
it may not carry fewer `self.passed()`/`self.failed()` calls than the refused one (a repair that
deletes the check it could not make legal is refused), and an unbound-name repair may not
define the missing name inside the unit (a stub `LLDP_PHONE_PKT = None` passes the lint and
tests nothing) — it builds from the layers the prompt lists or calls the library.
Record `repaired: true` on the chunk so the
measurement (R5) can count how often it was needed. Cost on the proof run: 4 extra unit calls on
38 (about a tenth), all on the cached shared half.

**The repair prompt is the fix prompt** (Terrence's question at §6.2, answered yes): `_fix_unit_prompt`
already renders the unit's generation prompt + `pt_fix_unit.jinja` with `lint_errors`,
`review_findings` and `run_result`; a repair is that prompt with lint errors only. Every lint
error carries what the review-finding shape carries — `kind` (its class prefix), `where` (the
unit and method the line falls in), `what` (the message), `evidence` (the offending line, we
hold the code), `fix` (the remedy clause every lint message ends with) — so the data exists at
arrival and one template serves both. R3 therefore reduces to: on refusal at generation, call
the fix path once for that unit with lint-only reasons, `hold: False`, on the unit model (D2).

**Touch points:** `_unit_call_and_store` (a `repair` hook on refusal when `guard["generation"]`),
`_fix_unit_prompt` (reused unchanged), the unit page (a "repaired once" note next to the ✓). **Test:** a first reply with a suite-owned toggle
and a clean second reply → stored, `repaired: true`; two bad replies → `error` with the lint text;
a fix pass (not generation) never repairs — it holds or refuses as today.

### R4 — Assemble and settle  *(the net for anything that slipped R1–R3)*

**Now:** Assemble lints and stops. Fix units is a separate click per round.

**Change:** after Assemble, if the lint has errors, run **Fix units on the lint-only set**
(units with lint errors and no review findings), re-assemble, re-lint — at most two rounds (D3).
D2 of the guardrails plan already says lint-only fixes apply themselves and every reply passes
G2/G6/D4, so this adds no new authority; it removes the clicks. A held fix (review- or run-driven)
is never applied by the loop. The Summary shows the rounds: "round 1: 9 errors → round 2: 1 →
settled" with the surviving errors listed.

**Touch points:** `_assemble_and_store` (a `settle` caller around it, or a new
`POST /assemble_and_settle/{key}`), `fix_units` internals factored so the loop can call them
without a request, the step-5 Summary. **Test:** a script whose only errors are lint-only settles
in one round; one with review findings assembles, lints, and stops with the findings intact; the
loop never exceeds its round budget.

### R5 — Measurement  *(so the next prompt change is judged by data)*

**Change:** every lint result is appended to `step6.lint_history` as
`{at, round, source: generate|assemble|settle|fix|repair, counts: {blocking, policy, warning},
by_class: {unbound, suite_owned, port_owner, field, verdict_echo, …}}` (the class is the error's
prefix, which `tests/test_lint_error_classes.py` already enumerates). A read-only tool,
`ask-ck/tools/pt_lint_report.py`, aggregates across sessions: errors per unit per class per model
per prompt version, so "did the declared-fields line reduce class 3?" has an answer that is not
one LLDP run. Same for `repaired` and settle rounds.

**Touch points:** `_assemble_and_store._apply_lint`, `_unit_call_and_store` (repair record),
the new tool (read-only `file:…?mode=ro` open, like every other reader). **Test:** the history
grows by one entry per lint; the report reproduces today's proof run as 1 blocking (unbound) +
8 policy (suite-owned) on 38 units.

### R6 — Cost comparison for the higher-ups  *(D6)*

An infographic (a private artifact page, then a PDF if wanted) comparing cost per script and
errors per unit across the four ways T44297 has been generated: **whole-script single call**,
**per-unit Opus** (2026-09-08/09), **per-unit Sonnet + guardrails** (2026-09-15) and **per-unit
Opus + guardrails** (the re-measurement D6 asks for, on the scratch server). Data sources, both
present: `CK_server/debug-log/*.jsonl` — 16 per-seat files from 2026-07-20 to 2026-09-15, each
record with `model`, `template`, `usage` (incl. `cost_usd`, cache reads/writes) and
`duration_ms` — and the figures already written into PROGRESS.md (whole-script call $1.58 for
one call; per-unit Opus $12.15 morning / $6.31 after caching / $5.79 / $6.47; today's Sonnet
$4.37). Coverage is checked before a bar is drawn: a run whose usage was not logged is shown as
"not measured", never estimated. Errors per unit come from R5 for the new runs and from the
session-state notes for the old ones (3 hidden NameErrors on a lint-clean 09-08 script).

## 3a. Precondition landed 2026-09-15 — a refused fix keeps the unit

Found while running the manual fix on the T44297 proof assembly: `_unit_call_and_store._fail`
zeroed a unit's code on the FIX path, so a fix refused by G2/G6 destroyed the reviewed unit it
was protecting (tc25, tc28 came back from Opus worse, were refused, and were wiped). Fixed the
same day — `_fail` is guard-aware, a refused fix keeps the current unit and records the reply
under `refused`, the chain classifies refused units and will not auto-assemble over one. **This
gates R3 and R4:** the repair turn and the settle loop both refuse fixes, and would have
destroyed units on every refusal. Shipped with 5 tests; gate pytest 1514.

## 4. Order and cost

R2 first (smallest change, reuses the fix guard verbatim, would have caught all nine errors
before Assemble), then R3 (makes R2 self-sufficient), R5 alongside them (it only records what
the lint computes), then R1 (removes class 1 at the source and improves step 4), then R4.
Roughly: R2 + R3 + R5 one session with tests; R1 one session; R4 half a session. Every step is
gated by `./ask-ck/tools/run_tests.sh` and smoke-tested on the scratch server before the hosted
one sees it.

**Acceptance:** re-run the T44297 proof on a scratch copy. Generate → (repairs) → Assemble and
settle produces a lint-clean assembly with **no human step between Generate and Review**, the
history records what was repaired and settled, and the reviewer's findings are about
semantics, not about what a lint could have said.

## 5. Decisions for Terrence

Measured on the 2026-09-15 proof run (38 Sonnet units, `usage` recorded per chunk):
**$4.37 for the run, ≈ $0.115 per unit**; 1.30 M tokens of which 771 k were cache reads and
202 k cache writes; the shared prompt half is ≈ 27 k tokens (the setup unit's cache write).
A unit's wall clock is 40–120 s. Those numbers are what the trade-offs below are priced in.

### D1 — how many repair turns at generation  ✅ DECIDED 2026-09-15

**What it controls.** How long the tool argues with the model about ONE unit before a person
sees it. R2 refuses the reply; D1 says what happens next.

| option | what happens on a refused reply | cost on the proof run | what it risks |
|---|---|---|---|
| 0 | store `error` + lint text; the person re-runs the unit | nothing | the loop is still the person's |
| **1** | one re-prompt with the lint text; then `error` | 4 extra calls ≈ $0.46, ≈ +10 %; +1 unit wall clock on those 4 | a second bad reply is shown, not spent on |
| 2 | two re-prompts | ≤ 8 calls; +20 % worst case | pays for units the model did not understand twice |
| until clean | loop | unbounded | thrash; masks a prompt defect (§6.4) |

**Terrence's rule:** start at **1**. R5 reports the **return rate** (repaired replies that pass ÷
repair turns taken). While it is ≥ 50 % stay at 1. If it drops below 50 %, raise to 2. If the
rate does not move at 2, go back to 1 — the second turn is buying nothing — and investigate the
**error specificity** instead (is the lint text telling the model what to change?). The budget
is a server-side constant the admin panel can set (`1` or `2`); R5's Summary line shows the
current rate next to it.

### D2 — repair on the unit model, or on the fix model  ✅ DECIDED 2026-09-15

**Terrence:** the **lint-triggered automatic repair (R3) runs on Sonnet**; every other fix —
review-driven, run-driven, and the settle rounds of R4, which are Fix units — **stays on Opus
for now** (`opus-for-per-unit-fix`). Reasoning kept for the record: the repair defect is a lint
text, a wrong repair costs one refusal (R2 catches it) and no review is spent; and the prompt
cache is per model, so an Opus repair would re-write the ≈ 27 k-token shared half at full price
(≈ $1 for the first repair) where Sonnet reads it. **Cost implication for D3:** a settle round
is Opus, so round 1 on the proof run (4 units) is ≈ $1–1.5.

### D3 — settle: rounds, and default or button  ✅ DECIDED 2026-09-15: budget 2, default ON, rounds visible

Terrence: *"when does a round trigger? … 'what one round is' is never directly addressed."*
Right — here it is, definition first.

**When a round triggers.** Exactly one event: **an assembly's whole-file lint has finished** and
its error list contains at least one **settleable** error. An error is settleable when all three
hold:
1. it is one of the **per-unit lint classes** — unbound name, suite-owned command, port owner,
   unknown field, verdict in `configure()`/`tear_down()`, and (D5) echoed verdict — i.e. a class
   a single unit's rewrite can clear. `incomplete:`, coverage, manifest, `syntax:` and
   `imports:` errors are whole-file: no unit fix clears them, so they never trigger a round;
2. its line maps to a **unit** (`_fix_reasons` does this today);
3. that unit has **no review finding and no bench-run failure** — otherwise the unit is HELD
   (guardrails D2) and the round leaves it alone.

Nothing else triggers a round: not a warning, not a held unit, not the user pressing Fix.

**What one round is.** Three steps, no click between them:
1. **Fix units** on the settleable units only — one Opus call per unit (D2), the fix prompt with
   lint reasons only, `hold: False`, every reply through G2/G6/D4 as today;
2. **re-assemble** (`_assemble_and_store`);
3. **re-lint.**

**When it stops.** After a round, one of three: (a) no settleable errors remain → **settled**;
(b) settleable errors remain and the round budget is not spent → the next round, with the
refusal reasons of round 1 added to the affected units' reasons; (c) the budget is spent → stop
and list what survived. The Summary shows every round as it runs: *"settling — round 1 of 2:
tc12, tc25, tc28, tc33 → 1 error left; round 2 of 2: tc28 → 1 error left; stopped"*.

**Worked on the 2026-09-15 proof run.** Assemble → lint: 9 errors. Settleable: all 9 — suite-owned
in tc12/tc25/tc33 (policy) and the unbound `LLDP_PHONE_PKT` in tc28 (blocking); none of the four
units has a review finding (no review yet). **Round 1:** Fix units on those 4 (Opus, ≈ $1–1.5),
re-assemble, re-lint. Expected: the three toggles are removed; tc28 either builds the phone frame
from `lldp_basic_phone` (passes) or still names a constant nothing ships (refused by the arrival
guard, error stands). **Round 2** (if tc28 stood): one more Opus call on tc28 with the refusal
text. Then stop; the Summary shows tc28's error and the person decides — and R1 would have removed
this very case before Generate.

**Terrence: "2 is fine. Make it default for now, with rounds visible."** The table below is the
reasoning that was put to him, kept for the record:

| question | options | my recommendation |
|---|---|---|
| **round budget** | 1 / 2 / 3 | **2** — round 2 exists for a fix that G2/G6/D4 REFUSED in round 1 (the unit gets one more try with the refusal reason); errors that survive two rounds are the prompt's or a lint's problem, not the loop's |
| **default or button** | settling runs automatically after every Assemble (Assemble-only kept as a secondary action) — or a separate "Assemble & settle" button | **default on, rounds visible** — the goal is no human step between Generate and Review; against it, the seat's Opus is spent without a click — if seats object, make it a per-seat setting |

**Cost per round on the proof run:** ≈ $1–1.5 (4 Opus fix calls, one cache write). Two rounds
worst case ≈ $3. Time: one to two unit wall clocks per round (fixes run concurrently).

### D4 — fragment closure  ✅ DECIDED 2026-09-15: AUTOMATIC, into OUR group library

**The concrete case.** Six offered fragments call `sendp(LLDP_PHONE_PKT, …)`; the definition
lives at module level in `library_1332.py` of the same ART suite and was never offered.

**Terrence:** we compile our **own** suite libraries as part of generation — ART's features are
being re-structured into different suites, so borrowing one or two ART libraries per script is
tolerable but a *suite* of scripts each needing distinct libraries is not: condense into one.
Hence **automatic** closure, into a library **named after the script's mother folder** (Port,
Switching, Management, …) until a suite naming convention is settled; a polishing pass of
scripts and libraries will follow later anyway. **Pruning:** an auto-added member that review
makes unnecessary is actually removed — that member only, without touching the others — to
prevent bloat. Built as R1(b). The step-4 "needs X" card is dropped from scope (the reviewer
sees auto-added members on the Summary and in the library file, each under its tag).

### D5 — promote the echoed-verdict warning to a policy error  ✅ DECIDED 2026-09-15: yes

`_lint_verdict_echo` warns when a `passed()`/`failed()` reason is a step's verify or action
text **verbatim** (4 on the proof run: tc7, tc8, tc9). It becomes a **policy** error — overridable
with a reason, in the settle set, the fix prompt already knows the rule ("say what was OBSERVED").
Not blocking: the script runs and a verbatim reason is occasionally the honest one. Requires the
POLICY list in `tests/test_lint_error_classes.py` and `_POLICY_LINT_MARKERS` to gain the entry.

### D6 — the unit model  ✅ DECIDED 2026-09-15: re-measure, then the comparison (R6)

**Data so far.** Sonnet, new prompt, all guardrails: 4 of 38 units carried the 9 errors (≈ 11 %
of units). $4.37 for the run. Opus at list prices is roughly five times Sonnet's rate, so the
same run is of the order of $20 — before knowing whether Opus makes fewer of these errors.

**Terrence:** re-measure — one Opus generation of the same case, on the scratch server, with
R5 recording errors per class — and then build **R6**, the infographic for the higher-ups:
cost (and errors per unit) for **whole-script single call** vs **per-unit Opus** vs **per-unit
Sonnet + guardrails** vs **per-unit Opus + guardrails**, from the historical usage records, to
show the trend is the right way. Not needed to build R1–R5.

### Summary

| # | decision | state |
|---|---|---|
| D1 | repair turns | **1**; raise to 2 if the return rate < 50 %; back to 1 if 2 does not move it, and fix the lint text |
| D2 | repair model | **Sonnet** for the lint-triggered repair; **Opus** for every other fix incl. settle rounds |
| D3 | settle | **budget 2, default on after every Assemble, rounds shown live**; Assemble-only kept as a secondary action |
| D4 | closure | **automatic**, into OUR per-group library; merge by tag; prune auto-added members precisely (R1(b)) |
| D5 | echoed verdict | **policy error** |
| D6 | unit model | **re-measure Opus on scratch**, then R6 the cost comparison |

## 6. Honest limits

### 6.1 A lint catches only a class with a rule
Every lint in the file exists because a run or a review found the class first: unbound names
(2026-09-08), suite-owned commands and fabricated fields (fix run 5), the port owner (the first
ART pass). Discovery is not free and this plan does not make it free — the next new class will
still cost a review or a bench run. What it does: (a) makes each discovered class cheap to
prevent *next* time (R2/R3 apply to any lint added later without new plumbing); (b) R5 records
which review `kind`s recur, which is the queue of lint candidates; (c) Review + held fixes remain
the net for class 4, and this plan does not touch G7. **Example with no rule today:**
`cross_unit_inconsistency` (unit 25 assumes ports another unit configured). No per-unit lint can
see it; Review can.

### 6.2 A repair can be compliant and hollow
The repair prompt says "your reply was refused because …". Two ways a model satisfies that
without fixing anything, both seen in the wild in other tools:
- **Delete the check.** Refused for `no lldp transmit` in `main()`, the repair removes the toggle
  AND the observation that depended on it, returns a unit with one fewer verdict, and the lint
  is clean. **Mitigation (R3 invariant):** the repaired reply may not carry fewer
  `self.passed()`/`self.failed()` calls than the refused one. Cheap, deterministic, not
  foolproof — a verdict can be kept and emptied — but G6's evidence rule and the echoed-verdict
  lint bound that too.
- **Define the missing name.** Refused for unbound `LLDP_PHONE_PKT`, the repair writes
  `LLDP_PHONE_PKT = None` (or an empty `Ether()`) at the top of `main()`. The unbound-names lint
  is clean and the test sends nothing. **Mitigation (R3 invariant):** an unbound-name repair may
  not bind the missing name inside the unit; it must build from the layers the prompt lists
  (`Ether()/lldp_basic_phone(...)`) or call a library member. R1 removes most of these cases
  before they reach R3.
A repair can also simply be a *different* bad reply; R2 refuses it and D1 stops the argument.

**Terrence's question — should the repair prompt have the review-finding structure, and do we
have the data at the initial check?** Yes to both, and it simplifies R3 (folded in above): the
fix prompt `pt_fix_unit.jinja` already takes lint errors beside review findings, and a lint
error at arrival carries everything a finding carries — class, unit + method (from the line),
message, the offending line itself, and the remedy clause. So the repair IS a lint-only fix pass
on the unit model; no second template, no second code path.

### 6.3 The partial assembly is blind across units
R2 lints a unit spliced into the frame plus the units generated so far. Anything that needs the
whole script stays at Assemble: `incomplete:` counts, objective coverage, the runner's manifest,
and the suite-owned lint's view of a `tear_down()` in a unit not yet generated. The setup unit is
generated first (the primed dispatch), so the suite-owned lint does have the suite's own commands
at every case unit's arrival — but a case regenerated later sees only the setup as it is then.

### 6.4 A working repair loop hides a weak prompt  — Terrence: the bigger concern
If R3 quietly repairs every class-2 toggle, nothing pushes anyone to make the prompt stop
producing them, and the run costs 10 % more forever. *"Analytics-driven revision is the only way
to ensure we don't repeat these errors. If the lint is defining an error and it keeps getting
repaired, the prompt needs to be changed."*

**The measure (R5).** Per lint class, per prompt version (the template file's git blob hash, so a
prompt edit starts a new series): units generated, units refused at arrival, repaired, repair
return rate, errors surviving settle — over a trailing window of the last **5 runs** (any case,
any seat).

**The alarm — thresholds ACCEPTED by Terrence 2026-09-15 ("good enough for now; email connectivity later"):**
- **A class is a prompt defect** when, over the trailing window, it was refused-and-repaired on
  **≥ 10 % of units**, OR it appeared in **3 consecutive runs**. (On the proof run class 2 is
  3/38 = 8 % in one run: below the first line, one run into the second.)
- **A class is a lint-text defect** when its repair **return rate < 50 %** (D1's rule): the model
  is told about the error and still cannot fix it → the message is not specific enough.

**Where the alarm shows** (no email path exists on this host; three visible places and one for
the logs):
1. the **admin panel** (double-click CK's face): a "Lint trends" card, red when any threshold is
   crossed, naming the class, the prompt version and the numbers;
2. the **step-5 Summary** banner on every case while the alarm stands: *"class `suite-owned` has
   been repaired on 12 % of units over the last 5 runs — the generate prompt is the fix, not
   the repair"*;
3. **`/health`** gains `lint_trends: {alarms: [...]}` so the `ck` status command and any monitor
   can read it;
4. a server log line `[pt] LINT-TREND ALARM …` at the moment a threshold is first crossed.
Thresholds live as server constants editable from the admin panel; the alarm clears when the
window falls back under both lines, and the report keeps the history so a prompt change can be
shown to have worked.

### 6.5 Automatic spend and time on the hosted server  — the reload question: a non-issue, confirmed
R3 and R4 spend the seat's models without a click per call, on the production server. Bounds are
the mitigation: one repair turn, two settle rounds, the settle set restricted to per-unit
lint-class errors, and the rounds shown live. Everything here is proven on the scratch server
(`ask-ck/tools/run_scratch_server.sh`) before the hosted tree changes.

**Terrence's question — what is an "edit" that hot-reloads?** Only a change to a **Python source
file under `ask-ck/CK-main/`**. `run.sh` (which the systemd unit runs) starts uvicorn with
`--reload` from that directory, and uvicorn's reloader watches `*.py` under its working directory
and nothing else. So: users working in the app, session saves, case loads, Terrence's surface-doc
reload — every write to `ck.db` — **never** restarts the server or touches an in-flight unit;
`ck.db` lives in `ask-ck/db/`, outside the watched tree, and is data, not code. What does kill
in-flight units: a `.py` edit under `CK-main` (a developer saving a file, or a scratchpad edit
script landing there), an explicit restart (`ck`, the admin panel), or a crash. `.jinja` templates
and the front-end files are not watched by the reloader (a template edit is picked up on the next
render without a restart — unverified, noted as such). Rule that follows: sequence server-code
edits into idle windows; data traffic is never the problem.

### 6.6 The measurement is only as good as the class labels
R5 keys on the error prefix that `tests/test_lint_error_classes.py` enumerates. A reworded lint
message moves its class silently unless that test is updated — which is exactly what that test
exists to force. The cross-case report reads sessions read-only and never writes `ck.db`.

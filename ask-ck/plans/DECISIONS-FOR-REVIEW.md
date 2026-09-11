# Decisions taken while executing PLAN-pipeline-end-to-end.md — FOR TERRENCE'S REVIEW

Every judgement call made without you, with the alternative that was rejected and what it
would cost to overturn. Written as the work happened, newest phase last. Nothing here is
settled — this file exists so you can overturn any of it in one pass.

**Session:** 2026-08-03c (autonomous run). Gate at each commit is recorded inline.

---

## 0. Standing decisions YOU made at the start of this run

Recorded so the constraints the work ran under are visible next to its output.

| | Decision | Consequence |
|---|---|---|
| **Hardware** | tb470 **read-only only** — preflight and console reads allowed, no config push, no script execution | Phase 11 is fixed and proved offline; the first real run is left for you |
| **External writes** | ck.db migration **yes** (verified backup first); production Zephyr push **no** | Phase −1.7 is built and dry-runnable, never executed |
| **Fan-out** | I implement; independent skeptics adversarially verify before each commit | Slower per fix, and it caught 8 real defects in my own work — see D-01..D-06 |

---

## 1. Parser / assembly (the refuted output ceiling)

**Context.** An adversarial reviewer found **7 ways my first version silently deleted real
code while reporting a clean recovery**. Silent loss is the exact failure this plan exists
to end, so the module was rewritten rather than patched. Each rule below is now decided by
evidence rather than by a heuristic.

### D-01 — Seam repair keeps code unless keeping it fails to parse
**Chose:** at each message seam, try both readings (drop the trailing partial line / keep
it) and take the one that parses, preferring the reading that drops nothing.
**Rejected:** always drop the trailing line (my first version). It is right when the stream
was cut mid-line and **wrong** when the model wrote the fence on the same line as a complete
statement — which deleted that statement silently.
**Residual risk:** where both readings parse, "keep" wins. On the real replies that keeps
two truncated *comments*, which carry no behaviour. Low.
**To overturn:** `stitch_parts` in `gen_assembly.py`.

### D-02 — Duplicate classes resolved on AST node count, not character length
**Chose:** when a continuation re-emits a class the previous part left half-written, keep
the definition with more AST nodes.
**Rejected:** longest wins. A re-emitted class with a padded `testCaseDesc` but two fewer
verification steps is longer and **less** complete; the reviewer demonstrated exactly that.
**Residual risk:** node count is a proxy for completeness, not a proof. If you would rather
this never guess, the alternative is to refuse the reply and re-generate.

### D-03 — A fenced block after `ts.run(...)` is commentary, not a continuation
**Chose:** stop consuming code at the chunk containing the runner; count the rest in
`report["blocks_after_runner"]`.
**Why:** `ts.run(sys.argv)` is by construction the last statement in a standardized script.
Without this, a "to run it locally:" block was concatenated in as module-level code that
would execute on import.
**Residual risk:** a model that emitted the runner early and then continued would lose the
tail. Not observed in any of the five stored replies. **Worth your eye.**

### D-04 — An unlabelled fenced block is assumed to be Python
**Chose:** treat ` ``` `, ` ```python `, ` ```py `, ` ```python3 ` as script; anything else
(` ```bash `) is excluded and recorded in `report["non_python_blocks"]`.
**Rejected:** requiring an explicit `python` tag — the stored replies include bare fences.

### D-05 — Fences inside string literals are DETECTED, not recovered
**Chose:** leave it broken and loud. A ``` inside a string or docstring, and a column-0
`class`/`def` inside a docstring, still mis-split the reply — but the result fails to parse,
`report["parses"]` is False, and the caller **refuses** the script.
**Rejected:** a tokenizer-based fence scan. The text is not valid Python until it is
assembled, so there is nothing to tokenize; the honest fix is to fail loudly.
**This is a known limitation, documented in the module docstring.**

### D-06 — Generation now REFUSES a reply that did not reassemble
**Chose:** `generate_script` and the fix pass raise **502** when the recovery report says
the assembly does not parse or fails its own `ts.add_testCase(...)` manifest.
**Previously:** a partial script was stamped, linted, persisted and written to disk with an
HTTP 200. **This is a user-visible behaviour change** — a case that used to "succeed" with a
broken artefact will now show an error. That is the intent, but you will see it.

### D-07 — Forensic record no longer truncated (Phase 7.9)
**Chose:** `step6.provenance.response` stores the **whole** reply; it was cut at 20,000
chars with no marker, so every stored generation was incomplete and the primary evidence for
this entire class of defect was destroyed by the record meant to capture it.
**Cost:** session rows get bigger — the multi-part replies are 37k–173k chars.
**Watch:** `ck.db` growth. If that is unacceptable, the alternative is to store the reply
outside the DB and keep a pointer.

---

## 2. Truncation signal (Phase 7.1)

### D-08 — Detection reads the `result` envelope, NOT assistant `stop_reason`
**My first implementation was dead code and a skeptic caught it.** Captured live against
CLI 2.1.207 (`CLAUDE_CODE_MAX_OUTPUT_TOKENS=200`): `stop_reason` is **null on every genuine
assistant message**, including the ones that hit the cap. The only truthy value sits on a
message the CLI *synthesizes* to carry the error, and it reads `stop_sequence`, not
`max_tokens`. The real signal is `result.is_error` + `terminal_reason == "api_error"` +
`"output token maximum"` in the result text.
**Consequence for the plan:** Phase 7.1's own wording ("capture `stop_reason` and raise") is
**wrong as written** and has been implemented differently. The captures are committed under
`tests/fixtures/` so this is checkable, not a claim.

### D-09 — The CLI's synthesized error text is stripped from the answer, failing OPEN
**Chose:** exclude a message only when its `id` is present **and** is not a `msg_...` id.
A message with no id is kept.
**Why fail open:** dropping real model output is far worse than keeping one line of CLI
error text. My first version dropped id-less messages and broke three existing tests — the
gate caught it.

---

## 3. Run path (Phase 11.0)

### D-10 — The whole `contextvars.Context` is copied, not just the lock holder
**Chose:** `RunManager.start` captures `contextvars.copy_context()` on the calling thread
and runs the thread inside it.
**Rejected:** threading an explicit `holder=` through `on_update`. Copying the context fixes
**every** ContextVar at once — including the one `llm_debug` uses to name its log file, which
is why background work has been landing in `debug-log/no-session.jsonl`.
**Verified by mutation:** reverting to a bare `threading.Thread` turns 3 tests red.

### D-11 — Thread guard uses an inline `# context-free:` marker, not a file allowlist
**Chose:** a repo-wide test refuses any `threading.Thread(...)` whose target is not a copied
context, unless the construction carries a `# context-free: <reason>` comment.
**Rejected:** a hardcoded list of permitted files, which rots silently — and the failure
this guard catches is invisible at run time.
**Applied to:** `main.py`'s embedding warm-up, which genuinely runs at startup with no
request context to inherit.

---

## 4. Step generation (Phase 2)

### D-12 — `generate_steps.jinja` rewritten; every step must carry an expectedResult
> ⚠️ **REVERSED 2026-08-05.** The "every step must carry an expectedResult" half of this decision
> was wrong: a Zephyr manual step is *meant* to leave the field empty (memory
> `expected-results-deliberately-absent`). The premise was circular — a push gate asserted it,
> then this prompt was changed to satisfy the gate. `synthesize_steps` now forces the field
> empty and the push gate rule is deleted. The Phase 2.2 half (rendering the four context
> fields) stands. See PLAN-pipeline-end-to-end.md §2026-08-05c.

**Chose:** deleted *"expectedResult usually empty or brief"*, rewrote the example to show
filled expected results with measurable values, required test data + measurement method per
step, and removed *"one or a few steps per major objective bullet"* (the rule that produced
steps at 0.98 similarity to their bullet).
**Also (Phase 2.2):** the template now renders `testlink_selections`, `zephyr_selections`,
`atp_selections` and `gaps` — all four were being **built by `_synthesis_context` for every
call and never rendered**, so step synthesis worked from strictly less evidence than the
stage before it, for no reason but a missing template reference.
**Consequence you must sign off:** the **53 committed bundles stay non-compliant** until
regenerated. Plan §2.4 says regenerate after Phases 4 and 7.2 — I have **not** regenerated
them, because that spends real tokens against a prompt you have not reviewed.
**The new prompt is unproven against a live model.** Its examples are unit-tested; its
output is not. **First thing to check tomorrow.**

---

## 5. The size gate (Phase 7.4/7.5)

### D-13 — The blocking size gate is DELETED, not recalibrated
**Chose:** removed the 409 entirely; `_size_estimate` is advisory and never blocks.
**Why not just fix the constants:** the premise is wrong, not the numbers. The gate assumed
the CLI's 32,000 `maxOutputTokens` is the whole answer budget. Measured `output_tokens` on
the stored multi-message generations: **67,326 / 66,334 / 57,188 / 34,966** — every one over
32,000, every one a complete script. 32,000 bounds a *message*; the answer continues.
**Consequence:** a very large case will now attempt generation where it used to be refused
up front. It costs tokens to find out. The protection moved to arrival-time
(`_recovery_failure` + the completeness lint), which reasons about what was delivered.
**Also removed:** `acknowledge_size_overflow`, whose override path had no caller — neither
the browser nor `pt_autopilot` could send it, so the documented escape hatch was unreachable.

### D-14 — Expansion is recorded as a RANGE, not a constant
Re-measured across 36 recovered generations: **0.71–1.90, median 0.90**, against
`_FILL_EXPANSION = 1.95`. One number cannot carry both marker-stripping (deterministic) and
model verbosity (variable). `tool/pt_measure_expansion.py` reproduces the table.

---

## 6. Run verdicts (Phase 11.1)

### D-15 — `ok` requires results, and every case reaching a verdict
**Chose:** `parse_framework_log` states a `status` (`empty_log` / `no_results` / `short` /
`ok`) plus a plain-English `verdict`, and `ok` requires results to exist AND no case to be
left in `ERROR`.
**Why:** zero cases parsed to `0 passed, 0 failed`, and every downstream check reads
`numFailed`. "Nothing ran" and "everything passed" were the same value — and "nothing ran"
is the most likely first-run outcome.
**Found while writing the tests:** a case that crashes mid-way is `ERROR` and contributes no
`numFailed`, so a failure count alone *still* read clean. Fixed.
**Judgement call:** `UNSUPPORTED` is reported, not failed — it is a legitimate outcome. If
you would rather an UNSUPPORTED case block a green verdict, that is a one-line change.

### D-16 — The log fixtures are real, and redacted
Committed two captured runs of the 5700_bootloader suite on an x230v2. **Two hashed device
credentials in the config echo were redacted** (`password 8 <REDACTED-HASH>`); nothing else
was altered, and a test asserts no credential survives in either fixture. My first fixtures
used an invented log format the real regexes cannot read — worth knowing, because such a
test proves only that the parser agrees with the format its author imagined.

---

## 7. Confirmation gate (Phase 7.7)

### D-17 — A lint error blocks confirmation, with NO override
**Chose:** the TestCase-shortfall check becomes an `error`; `confirm_step` refuses step 6
while `lint.errors` is non-empty, or if the script was never linted.
**Deliberate asymmetry:** the objective-coverage gap beside it stays a warning with an
acknowledge flag, because a source step can be genuinely untestable and you are the right
authority. A lint error means the artefact is broken — regenerate it. A test pins the
asymmetry so neither drifts into the other.
**Consequence:** cases that were previously confirmable may now refuse. That is the intent,
but it will show up as friction before it shows up as value.

---

## 8. Blocked / not done, and why

| Item | Status | Reason |
|---|---|---|
| Phase −1.7 Zephyr re-push | built, not executed | your instruction: dry-run only |
| Phase 11.4 first hardware run | not attempted | your instruction: read-only bench |
| Regenerating the 53 bundles | not done | needs your sign-off on the new steps prompt (D-12) |
| `git push` | **blocked** | the push was refused by the permission layer; commits are local. **You may need to push manually, or approve it.** |
---

## 9. REVISED 2026-08-04 after review with Terrence

Two decisions were re-opened with more evidence. Both changed.

### D-17 REVISED — the lint gate is split by AUTHORITY, and the prompt bug is fixed
**Was:** a lint error blocks confirmation, no override.
**Now:** 14 errors are **blocking and never overridable** (syntax, missing structure, an
unfilled `>>> FILL` marker, `self.` before assignment, an unbound device or port —
AttributeError on the testbox — a duplicate portlink binding, bad imports, the truncation
detector, and a completeness check that could not run). 5 are **policy, overridable with a
recorded reason** (the four logging-contract rules, and a direct `setup.init_portlink()`).

**What changed my mind — the evidence, not the argument.** Across the 4 stored sessions with
a lint result, T33233/T33234/T33235 are 0 errors. **Exactly one error has ever fired**, on
**T44297, the best script we have generated**: *"line 273: calls setup.init_portlink()
directly, which skips the run-time MEDIA assertion."* Under a blanket no-override rule that
script is permanently unconfirmable. And the model was **following our prompt**: the generate
prompt said *"bind every device you use in `TestSet.init`"* and pointed at `init_portlink()`,
while `_ck_bind_link` — the sanctioned wrapper the lint demands — **appeared in the prompt
zero times**. The lint was failing the model for complying with our instructions.

**So the prompt bug is fixed first** (Phase 7.8): rule 3 now says `init()` is fixed frame, do
not add bindings, do not call `init_portlink()` yourself, and says why (the media assertion).
`tests/test_prompt_agrees_with_lint.py` now asserts that every enforced rule is actually
conveyed by the prompt — a rule enforced in code that no instruction ever gave is a trap.
**Unrecognised errors default to blocking**, and `tests/test_lint_error_classes.py` enumerates
all 19 so a new check cannot drift into "overridable" unnoticed.

### D-05 REVISED — no string-fence recovery, and now with a reason recorded
**Was:** accept the limitation. **Briefly became:** add a candidate reading for fences inside
string literals. **Now:** firmly no recovery — diagnosis only.

Terrence's challenge was the right one: *"is this a plan for an eventuality that has yet to
arise, and could the solution itself create issues?"* Both halves hold.

- **Frequency is zero.** No triple-backtick in 830 corpus scripts, 1,250 harvested CLI sample
  outputs, or the 5 stored generations. (The precursor is common — the model writes
  markdown-style inline code in comments constantly, 76 such tokens across those five
  replies — so the case is plausible, just unobserved.)
- **The fix would have been worse than the gap.** Seam repair is sound because its candidate
  readings differ by ONE LINE, so "it parses" is strong evidence. A string-fence candidate
  moves where the code boundaries are, so candidates differ structurally — and among
  structurally different assemblies "it parses" is a weak filter, because plenty of wrong
  Python parses. It would have converted a **loud refusal into a possible silent wrong
  assembly**: precisely the failure class the adversarial review found seven of.

What shipped instead is `gen_assembly.diagnose_unrecoverable` — it names the fence-in-a-string
signature so a future occurrence arrives as a diagnosis rather than a `SyntaxError` on a line
nobody wrote. A test guards against a recovery path being added later without re-arguing this.

**Process note worth keeping.** I had this right originally, then changed position when
Terrence rated the other answer higher, and designed an implementation for it. The measurement
was identical before and after; only my confidence moved, and it moved for the wrong reason.
---

## 10. The remaining four differences, resolved 2026-08-04

Reviewed against measurement rather than argument. **Three of the four landed on an option
neither of us picked first**, and one was a bug I had introduced.

### D-18 (Q3) — UNSUPPORTED is RECONCILED, not passed and not failed
**Neither answer survived the data.** 5 of 13 real logs contain UNSUPPORTED, including the run
a human labelled PASS (7 of 26 cases). And the set is **stable**: two runs of test-5700.2002
on the same platform both report exactly `{2, 22, 42, 62}`, the longer run adding three more
as more of the suite ran. UNSUPPORTED is a deterministic property of (case × platform).
- My "report, do not fail" loses the signal when a case newly stops being tested.
- Terrence's "never green without an ack" fires on **38% of runs** for a set that never
  changes, and would have blocked a run a human accepted.
**Built:** compare against a recorded expectation per script+profile. `as_expected` is green;
`regression` (newly UNSUPPORTED — no longer tested) and `stale_expectation` (a case now runs)
are loud; `unestablished` asks once, so a first run establishes the set.
**Open:** the expectation currently rides in on the bench profile
(`profile["expected_unsupported"]`). Where it should durably live — profile, session, or a
per-case field in `ck.db` — is **your call**, and it is the one loose end in this item.

### D-19 (Q4) — evidence is persisted before refusing; retry is explicit
**Terrence was right, and the bug was worse than the question implied.** The 502 refusal fired
**before `sess.step6` was written**, so refusing DESTROYED the whole reply — Phase 7.9's exact
defect, re-created one layer up, for the one case where the evidence matters most.
**Built:** the attempt (prompt, full reply, recovery report, rejected code) is recorded under
`step6.failed_generations` (last 3) *before* the refusal, and a previously-good script is left
untouched. Same in `fix_script`.
**Retry stays explicit, on cost evidence:** generate calls run a median 97s, but the
multi-message ones — exactly the ones that fail reassembly — measured **326–778s**, worst
1,576s (26 min). An inline auto-retry would produce a 10–26 minute request the client
abandons, on precisely the cases that trigger it.
**Principle worth keeping:** retry only causes that are plausibly non-deterministic; refuse
deterministic ones once, loudly.

### D-20 (Q5) — decide on an unambiguous margin, refuse a coin-flip
**Refusing every duplicate would have rejected 2 of the 5 real replies** in cases the evidence
already settles. The three real duplicates: `TestCase_21` 14 nodes vs **434**, `TestCase_40`
**0 (does not parse)** vs 922, `TestCase_9` **0** vs 116 — and the model's own assembly note
says *"part 2 (`TestCase_21`–`TestCase_30`)"*, confirming the later one.
**Built:** exactly one parses → take it. Both parse and one is ≥3× richer → take it.
Otherwise **ambiguous**, and the reply is refused. `_DUPLICATE_OBVIOUS_FACTOR = 3` sits an
order of magnitude below the closest real margin (31×), so it decides every observed case and
escalates anything close. A test guards the threshold from drifting up into real data.

### D-21 (Q6) — a block after the runner now REFUSES
Terrence's answer, taken unchanged: `blocks_after_runner` is **0 across all five** replies, so
refusing costs nothing observed and never silently discards code the model meant to include.
**Deliberately not coupled to retry** — a model that habitually appends "to run it locally" is
deterministic, so a second expensive call would fail identically.

### Scorecard, for the record
12 decisions compared blind: **5 matched.** Of the 7 that differed, on review **1 went my way**
(Q12, string fences), **2 went Terrence's way** (Q4 persistence, Q6 post-runner), and **4
landed somewhere neither of us started** (Q2 split, Q3 reconciliation, Q5 margin, and Q4's
retry mechanism). The consistent lesson: every difference dissolved once someone measured, and
in every case the measurement was cheap and available all along.
---

## 11. Q3 re-reviewed 2026-08-04 — Terrence was right twice, and I had shipped a dead branch

### D-18 REVISED — no platform key, and the reconciliation was UNREACHABLE

**Terrence's challenge:** *"Im mildly concerned with the detail of x230v2, is this just an
arbitrary name or is this an actually evidence-based assertation? I'd also like to point out
that the scripts should be platform-agnostic, so they should rely on the bench configuration
(which is a step to be taken in the FUTURE project, Test Composer)."*

**On `x230v2`:** not arbitrary, but weaker than I presented it. It is the framework's own label,
emitted while deciding **licence bundles** (`No license bundles require loading on swi_a for
platform family x230v2`), and I never verified how it is computed. I offered it as a capability
contract on the strength of an incidental log line.

**On the architecture: he is right, and it makes the whole idea unnecessary.** The scripts
already detect capability at run time themselves — that is what *produces* the UNSUPPORTED
verdict:

    !!FAIL: DUT does not support USB Media
    !!FAIL: DUT supports SD Card but no SD Card installed
    !!FAIL: No USB media present, test unsupported

Keying an expectation on a platform label would import platform-awareness into the verdict
layer to re-derive something the script has already established, against
`scripts-must-be-hardware-agnostic`. **Q3a and Q3b are parked**: no platform extraction, no
durable-storage decision. The expectation stays a caller-supplied parameter, and where it
lives is a Test Composer question.

### THE BUG THIS REVIEW EXPOSED — my reconciliation could never report green

A real UNSUPPORTED case reports its own inapplicability **as a failure line**, so the case
carries `numFailed >= 1` while being classified UNSUPPORTED. All four in the captured log do:

    << test-5700.2002.2: UNSUPPORTED (numPassed: 2 numFailed: 1)

`ok` required `numFailed == 0`, so **no run containing even a fully expected UNSUPPORTED case
could ever be green** — every branch I built was unreachable. My synthetic fixture used
`numFailed: 0`, which no real log does, and it hid the defect completely. That is the *second
time* an invented fixture masked a real bug in this work (the first was the log format itself).
The verdict now reads **case results**, not assertion counters; the counters are still reported
verbatim because they are the log's own numbers.

### D-22 (Q3c) — an unrecorded UNSUPPORTED set is PROVISIONAL, not blocking
The first run can be green. The set is reported, marked `unsupported_provisional`, and any
later change is still loud. Rationale: blocking the first hardware run — the one this whole
plan points at — on an expectation nobody has had a chance to record is friction with no
safety gain, and the set is visible either way.

### D-23 (Q3d) — a case that started running again is LOUD but does not fail the run
**Terrence:** *"This could be the result of a false positive. Loudly identify the change in
support and let a human verify."* The verdict now says `SUPPORT CHANGED`, names the cases, and
states both readings — the platform gained the capability, or the script's own capability check
is a false positive — while leaving `ok` decided by the actual case results. A `regression`
(a case newly UNSUPPORTED, i.e. newly untested) still blocks.
---

## 12. Q3 traced to the device, and then CUT BACK — 2026-08-04

### Where `x230v2` actually comes from (Terrence asked; I had not checked)

Traced through the device console capture, not the test log:

| Time | What happened |
|---|---|
| 11:29:00 | framework runs `sh sys` on the DUT over the serial console `/dev/u0` |
| 11:29:01 | the DEVICE replies: `Base 691 Base **AT-x230-18GT V2** X1-0 A10719G254500012` |
| 11:29:39 | the framework emits `platform type is x230v2` / `platform family x230v2` |

So it **is** evidence-based — it traces to the device's own `show system` output. But it is a
**lossy normalisation**: `AT-x230-18GT V2` → `x230v2` drops `18GT`, the port count and media
variant. The framework's own adjacent line says *"platform **family**"*, which is the honest
word — a family label collapses variants that may differ in capability.

### And my "deterministic property of (case × platform)" claim was WRONG

Mapping each UNSUPPORTED case to its own stated reason:

| Case | Reason | Depends on |
|---|---|---|
| `.2` | `DUT does not support USB Media` | platform capability |
| `.22` | `No USB media present, test unsupported` | **bench state** |
| `.42` | `No USB media present, test unsupported` | **bench state** |
| `.62` | `No USB media present, test unsupported` | **bench state** |

**Only 1 of 4 is a platform property.** Three are "did someone plug a USB stick in" — same
device, same platform, different day, different answer. The stability I measured was two runs
on a bench nobody had touched, and I generalised n=2 into a design principle. Terrence's
original objection — that this belongs to **bench configuration**, in Test Composer — was
right for a reason I had not yet found.

### D-18/D-22/D-23 WITHDRAWN — the whole reconciliation was scope creep

**Terrence:** *"I see that a lot of scope creep regarding the return of results, what to do
with logs, etc. That's for the next step. Our current goals regarding logs are: Consistent
results / Readable results / Formatted appropriately for future automation / No gaps in
results."*

Correct, and the expectation machinery (expected sets, `regression` / `stale_expectation` /
`unestablished` / provisional flags) has been **deleted**. It was judging what a run *means*,
which is Test Composer's job. What remains is exactly the four goals:

- **Consistent** — one bucket per case: PASS / FAIL / UNSUPPORTED, plus ERROR for a case that
  never reached a verdict. `sum(counts.values()) == parsed_cases`, always.
- **Readable** — one line, with the two tallies **labelled**: `cases: 1 passed, 10 failed,
  4 unsupported, 1 no verdict (of 16); assertions: 60 passed, 43 failed`. Labelled because
  "N passed" is ambiguous between cases and assertions — the captured run is 11 cases / 78
  assertions, and I conflated them myself while writing the function.
- **Formatted for automation** — a `counts` dict keyed by outcome, beside the log's verbatim
  counters.
- **No gaps** — `results_complete` means the RESULTS are trustworthy (the run produced
  results, every registered case reported a verdict, no unattributed failure line). It
  deliberately does **not** mean "the test passed"; that is `counts["FAIL"] == 0`, which a
  caller asks directly. Keeping the two apart is the point — conflating them is the original
  empty-equals-success defect.

**Left for Test Composer, explicitly:** whether an UNSUPPORTED case *should* be unsupported,
tracking sets across runs, and the observation that case `.62`'s UNSUPPORTED verdict conceals
a second failure (`Problem occurred whilst setting boot environment on swi_a, abort`). That
last one is recorded here rather than acted on.


---

## 13. Phase 4 — CLI grounding, executed 2026-08-04

**Session:** autonomous, at your direction ("proceed as far as possible, store any decisions
until the end"). **All six sub-items 4.1–4.6 are implemented.** Gate **966 → 1006** pytest
(+40 new, all mutation-verified), 92 Vitest unchanged, both guards, `ck.db` untouched.

**Measured effect**, replaying all 53 refined cases through the real injection path
(`detect_commands` + `feature_commands` + `prompt_block`, mirroring
`routers/pytest_create.py:1509-1524`). Both columns use the SAME harness, so this is a fair
before/after and not a redefinition:

| | Before | After |
|---|---|---|
| Zero commands detected — no grounding at all | 15 | **10** |
| Commands detected, but no real output | 19 | **0** |
| Real device output or worked usage present | 19 | **43** |

Set-diff of the zero-detection cases: **5 fixed** (T33277, T33279, T37861, T37865, T43817),
**0 regressed**. Both of the plan's named verification targets pass — T33277 reaches
`show spanning-tree`'s 2,388 chars; T44297 reaches `lldp tlv-select`.

### D-24 — All of it is READ-TIME. Nothing normalises `ck.db`

`ask-ck/var/ck.db` is the permanent single source of truth: built once, shipped via LFS,
`build_db.py` refuses to rebuild, no migration framework. 4.1 offers "derive at read time
(or normalise via 0.1)" and 4.5 says "re-classify from the data already in ck.db". So the
repair lives in `cli_lookup.py` and re-derives on the way out.

**Rejected:** patching the `command`/`syntax`/`sample_output` columns. It would have been
the repo's first in-place mutation of the permanent DB — the same call you made for Phase 1
of case-locking — and it couples the fix to a rebuild that cannot happen.

**To overturn:** the derivation is three pure functions (`norm_cmd`, `real_command_name`,
`reclassify`); a future migration could run them once and drop the read-time layer.

### D-25 — Re-derive from `pre_blocks`, not from the `syntax` column

`pre_blocks` holds every `<pre>` block **verbatim** on 6,305 of 6,323 rows, so the
classification is redone from the ORIGINAL input rather than un-picked from a lossy result.
Rows without it fall back to the stored columns untouched, and a recovery that finds nothing
can never erase what the harvest already stored (`sample = sample or recovered`).

### D-26 — The harvester is fixed too, but the live path does not depend on it

`harvest_cli_docs.classify()` now uses the same general prompt regex. Since `ck.db` is never
rebuilt this changes nothing today; it stops a future harvest re-creating the defect. The two
implementations are pinned to agree by test, because two copies of one rule is how this comes
back.

### D-27 — Precision over recall in every classifier

`cli_lookup`'s own FEATURE_ALIASES header sets the rule: *"a wrong alias injects
confidently-wrong grounding, which is worse than none"*. A syntax template misread as device
output would hand the model a fabricated output format under a heading that says "match these
formats exactly" — the exact failure Phase 4 exists to stop. So: `syntax` is always the
fallback classification, never `sample_output`; a block under 3 lines stays syntax; a
placeholder-dense block stays syntax; an ambiguous abbreviation is **refused, not guessed**.

**Cost of this choice:** some real output is still filed as syntax. I did not chase it.

### D-28 — 4.4's premise is partly wrong: `tables` CANNOT replace the speed prose

4.4 says surface `cli_commands.tables` *"replacing 18 lines of hand-written prose about
`speed` forms"* (`pt_extract_sequence.jinja:76-98`). On inspection those 18 lines hold **three
different kinds** of knowledge and the tables only supply one:

| The prose says | Status |
|---|---|
| The three `speed` **forms** (`speed 1000` FORCES / `speed auto 1000` NEGOTIATES / `no speed`) | **KEPT.** `tables` holds a value matrix, not form semantics. `tests/test_prompt_examples.py::test_speed_rule_covers_every_documented_form` already pins that the prompt must convey these, and it is right to. |
| **"Do NOT assert which speeds a given port supports: the CLI reference does not state it"** | **CORRECTED — this is now false.** `tables` states exactly that, per port type. The instruction was telling the model to ignore real grounding. |
| **HALF DUPLEX IS IMPOSSIBLE AT ≥1 Gig** | **KEPT UNTOUCHED.** The prompt itself notes no reference page states it (memory `awplus-speed-duplex-constraint` agrees). Deleting it would lose knowledge nothing can re-supply. |

So 4.4 shipped as **additive** (tables now render as `legal values:`) plus a one-sentence
correction, not as a deletion. The rewritten sentence keeps the original safety intent: the
table is keyed by port **type**, and which type a given bench port is remains unknown at
generation time, so the outcome still gets expressed in words rather than a fixed verdict.

**This is the decision most worth your eye** — it is a prompt-text edit, and prompt text is
one of the two things you flagged as hardest to unwind.

### D-29 — 4.6 ships `Default` and `Mode` only

`notes` has `Overview`, `Default`, `Mode`, `Example`, `Usage notes`, `Related commands`.
Shipped: **Default** and **Mode** — short, factual, directly assertable ("what does this read
before I touch it", "which config mode must the script be in"). Rejected: `Overview` (restates
the command in prose), `Example` (a lead-in sentence with no content), and **`Related
commands`, deliberately — it invites the model to reach for commands the case never named.**

### D-30 — Added a `spanning-tree` FEATURE_ALIASES entry, because 4.1 alone cannot hit the target

The plan's own verification target is T33277 → `show spanning-tree`'s 2,388 chars.
De-hyphenation cannot get there: T33277 names the protocol in **prose** ("spanning-tree
statistics and counters", "spanning tree can be enabled", "spanning-tree diagnostic") and
never writes a command, so there is no lexical path to the row. That is precisely what
FEATURE_ALIASES exists for, and its header sets the criterion — *"add entries as real cases
surface them"*. This is a real case surfacing one.

`stp` is deliberately **absent** from the prose list: three letters in an acronym-dense corpus
is the ambiguous alias the header warns against, and `rstp`/`mstp`/`spanning tree` cover every
real mention across the 53 cases. Pinned by test.

### D-31 — Worked examples now ground a command that prints nothing

Not in the plan; found while verifying the flagship case. `lldp tlv-select` — the command
T44297 is entirely about — has **0 chars** of `sample_output` because it is a config command
that prints nothing, but **12 real worked example lines** showing the correct form.
`prompt_block` rendered neither syntax examples nor usage, so the one command that mattered
reached the model with no evidence at all. It now emits `real usage:` when there is no output.

### Corrections to the plan's own numbers

Recorded because the plan states them as measurements, and mine differ. Both are heuristic;
mine are stated with their method so you can re-derive them.

| Plan | Mine | Why |
|---|---|---|
| "~591 of 3,297" then "1,090 of 4,035 pairs" store a hyphen-losing name | **768 of 3,297 distinct names** | Mine requires a syntax-token prefix to normalise-match the stored name exactly, and stops at the first placeholder. The plan flags its own figure as "a conservative floor — depends on the detection heuristic". |
| 4.5 strands "404,041 chars in 559 rows" | **735 rows / 586,740 chars** candidate; **607 rows / 269,603 chars actually recovered** | Two distinct causes, measured separately: 157 rows with a non-`awplus` hostname, and 735 with promptless multi-line output. "Recovered" counts only rows that gained a `sample_output` they did not have. |
| Baseline "15 zero / 37 no-output / 1 with output" | **15 / 19 / 19** | Zero-detection agrees exactly. The other two differ because the plan counted only blocks containing an `awplus` prompt line as real output; mine counts any rendered output section. Before/after in this section uses one harness throughout. |

### Not done, and why

- **A second measurement pass over the remaining 10 zero-detection cases.** They name no
  command and no aliased feature; each would need a FEATURE_ALIASES entry, and inventing ten
  at once is exactly the auto-derivation the table's header forbids. They should come one real
  case at a time.
- **`Usage notes` from `notes`** — often long and prose-shaped. Left out under D-27's budget
  rule; easy to add if you want it.

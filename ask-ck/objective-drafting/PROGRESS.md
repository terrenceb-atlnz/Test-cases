# PROGRESS.md — Ask CK Workbench (Server-Backed)

**Purpose**: This file exists so future sessions can quickly understand exactly where we are, what has been built, what the priorities are, and how to continue seamlessly.

**Last Updated**: 2026-08-03c (by Claude)

## Latest session (2026-08-03c) — the ceiling is dead in code, and the run path is unblocked

**Ask: "perform as many Phases as possible, leave all decisions for me until the very end,
make a best-effort guess to bypass blockers and record them."** Autonomous run against
[`PLAN-pipeline-end-to-end.md`](../ck-facelift/PLAN-pipeline-end-to-end.md). Every judgement
call is in [`DECISIONS-FOR-REVIEW.md`](../ck-facelift/DECISIONS-FOR-REVIEW.md) — 17 entries,
each with the alternative rejected. **Gate 803 → 895 pytest** (+92 Vitest unchanged).

Standing constraints Terrence set before the run: tb470 **read-only** (no config push, no
script execution), **ck.db migration allowed / production Zephyr push not**, and skeptics
adversarially verify each fix before commit.

### Shipped

- **The parser fix (`f0a94af`) — `CK_server/gen_assembly.py`.** All five stored replies now
  recover **completely**: every class registered by `ts.add_testCase(...)` is defined, carries
  a `main()`, and the whole script parses. 21→40 classes on the big one, **0→6** on the "D15
  regression". Generation now **refuses** a reply that did not reassemble, instead of stamping,
  linting and persisting a partial script behind an HTTP 200.
- **Phase 11.0 (`f0a94af`) — the run path is open.** `RunManager.start` carries a
  `contextvars.copy_context()`, so the run thread no longer gets locked out by the browser tab
  that started it. Verified by mutation (revert → 3 tests red). A repo-wide guard refuses any
  other uncarried thread. **Not yet proven on hardware** — that is Phase 11.4 and it needs you.
- **Phase 2.1–2.3 (`f0a94af`).** `generate_steps.jinja` no longer says expectedResult is
  "usually empty" *and* shows an empty one as its only example. It also now renders
  `testlink_selections` / `zephyr_selections` / `atp_selections` / `gaps` — **all four were
  built by `_synthesis_context` for every call and never referenced**, so step synthesis worked
  from strictly less evidence than the stage before it.
- **Phase 7.4/7.5 (`5f4af0a`) — the size gate is deleted.** Not recalibrated: its premise is
  false. Measured `output_tokens` on the stored multi-message generations — **67,326 / 66,334 /
  57,188 / 34,966** — every one over the 32,000 "hard cap" and every one a complete script.
  32,000 bounds a *message*. `tool/pt_measure_expansion.py` re-measures expansion at 0.71–1.90
  (median 0.90) against the fitted constant of 1.95. The booby-trap test that pinned the refuted
  premise is gone, replaced by a staleness guard over the comments that repeated it.
- **Phase 11.1/11.2 (`86c062a`) — "nothing ran" no longer reads as "everything passed".**
  `parse_framework_log` states a status and a verdict; `ok` requires results to exist and every
  case to reach a verdict. Real captured fixtures from an x230v2 bootloader run (one clean, one
  genuinely failing), with two hashed device credentials redacted.
- **Phase 7.7 (`81c9c94`).** A script with fewer TestCase classes than the approved sequence is
  now a lint **error**, not a warning — it is the only signal that a cleanly-parsing script is
  short — and `confirm_step` refuses to sign off a script with lint errors.

### What the adversarial verification actually caught

**Both skeptics refuted my work, and both were right.** The truncation-signal fix was **dead
code**: `stop_reason` is null on every genuine assistant message even when truncated, and the
only truthy value sits on a message the CLI synthesizes. Reproduced independently before
rewriting it against the `result` envelope. The first parser was worse — **seven ways to
silently delete real code while reporting a clean recovery**, including eating the
`ts = TestSuite(...)` every framework script needs. Rewritten so every rule is decided by
evidence rather than heuristic.

### Pick up here

1. **Phase 11.4 — the first hardware run.** Everything is fixed and proved offline; nothing has
   touched tb470. This is the deliverable the whole plan points at.
2. **Sign off the new steps prompt, then Phase 2.4** — regenerate the 53 bundles. They stay
   non-compliant with the Zephyr gate until then, and the new prompt is unit-tested but
   **unproven against a live model**.
3. **Read `DECISIONS-FOR-REVIEW.md`** — 17 calls made without you, three worth arguing about
   (D-03 blocks-after-runner, D-15 UNSUPPORTED handling, D-17 the non-overridable lint gate).
4. Phases 0, 1, 3, 4, 5, 6, 8, 9, 10, 12 are untouched.

## Latest session (2026-08-03b) — full-pipeline audit (284 findings): the output ceiling is a PARSER BUG, and Phase −1 ships

**Focus: "no objectives is never OK" through to "we have never executed a single test case" —
one plan, in pipeline order, leave no stone unturned.** Deliverable is
[`ask-ck/ck-facelift/PLAN-pipeline-end-to-end.md`](../ck-facelift/PLAN-pipeline-end-to-end.md)
(~1,750 lines): a 16-station walkthrough of the pipeline, 14 phases, decisions recorded inline.
Built from a 27-agent adversarially-verified audit — **284 findings, 206 CONFIRMED, 77 PARTLY,
0 refuted.** Gate **775 → 803** pytest (+92 Vitest unchanged).

### The two results that change what to do next

- **The generation "output ceiling" does not exist — it is a fence-parser defect.** Replaying the
  five stored replies in `CK_server/debug-log/no-session.jsonl` through the real
  `_parse_generated_blocks` regex (`pytest_create.py:883`): the model sent 173,351 chars /
  **42 TestCase classes** and the parser kept 21; the "D15 regression" reply was a complete
  6-class script from which it kept **0**. **All five replies end in `ts.run(sys.argv)` — nothing
  ever truncated.** The CLI splits long answers across assistant messages, each re-opening a
  ` ```python ` fence, and the non-greedy `(.*?)``` ` stops at the *continuation's opening* fence,
  usually mid-token. The model even labels its parts and closes with plain-English assembly
  instructions; the parser discards those too. **The parser-kept figures are, to the character,
  the numbers in `FINDINGS-generation-size-ceiling.md` and `RESULTS-2026-08-03.md`** — both
  documents measured parser output and called it model output. This invalidates the ~9–20 class
  ceiling, `_size_overflow`'s three constants, **chunked generation (the plan's largest item,
  costed XL)**, and D15's diagnosis. Recovery is not uniform (the 4-part reply re-emits a partial
  *class*), so assembly must work at class granularity — S/M, not XL.
- **The reason nothing has ever run on hardware is a `ContextVar` lock defect, not the bench.**
  `RunManager._run` is a `threading.Thread`, and `llm.current_session_id` is a `ContextVar` that a
  new thread does not inherit — so the run thread's first `_pt_persist` is locked out **by the very
  browser tab that started it**, before SSH is attempted, and the failure surfaces as "SSH connect
  failed: … the case is locked". Reproduced offline against the real `locks` module. D13/the stack
  demand is *not* the blocker — preflight is not wired into the run path at all.

### Shipped

- **Phase −1 (`949004f`, `0743889`) — the Zephyr push validates, confirms and audits before it
  writes.** It previously imported no validator at all and pushed whatever JSON was on disk.
  Now: shape rules **imported** from `llm.validate_zephyr_payload` (one owner) and **failing
  closed**; every non-note step must carry an `expectedResult`; the silent escape-repair is loud
  and blocking; a real push needs `{"confirm": "<key>"}`; every `--execute` writes an audit record
  to `ask-ck/var/zephyr-push-audit.jsonl` *before* the first network call, and a case whose record
  cannot be written is refused. **The gate refuses all 53 committed bundles** (618 of 648 steps
  have no expected result) — the honest state of the corpus.
- **A heading mismatch was silently dropping Zephyr web-links.** The parser looked for
  `(Step 3)`; the template emits `(Step 2)`. `parse_atpylib_links` had already been fixed for the
  same drift 30 lines above and it was never carried across. **2 links → 86, across 12 bundles.**
- 28 tests in `tests/test_zephyr_push_validation.py`, all offline; a 9-mutation harness, all 9
  caught. The first pass left one asleep, which is why the harness exists.

### Decisions taken

- **The 43 cases already live in Zephyr (`6f254e7`, 2026-07-22) will be re-pushed, staying at
  v2.0.** No v3.0. `TARGET_MAJOR_VERSION = 2` already enforces this. Consequence: Zephyr keeps no
  version trail, so the local audit log carries the replaced content; and a re-push needs
  `--force`, so it is a deliberate CLI run, not the button.
- Backfill `ck.db` behind a migration mechanism; regenerate all 53 refined cases after Phases 1–4;
  triage the 305 empty cases rather than authoring all of them.

### Corrections to the record

- **The `ck.db` build timeline was backwards.** `build_db.py:506` writes `built_at` with
  `datetime.utcnow()`, so `2026-07-20T01:16` is UTC = 13:16 local and the extractor was fixed
  **6h12m before** the build, not after. Cross-check: `meta.src_mtime:scripts_index.json` =
  13:12:30 local. No race — the build simply re-used a five-day-old intermediate.
- Memory `claude-code-cli-transport-contract` asserted the output ceiling as fact; corrected.

### Pick up here

1. **Fix `_parse_generated_blocks`** (`pytest_create.py:883`) to assemble across inner fences,
   then re-measure. Everything in Phases 7–9 is calibrated against parser output, so this comes
   before any constant is re-fitted.
2. **Phase 11.0** — propagate the lock holder into the `RunManager` thread (or
   `contextvars.copy_context()`), with a test. Small, and it unblocks the endgame.
3. **Phase 2** — `generate_steps.jinja:15-16` says "expectedResult usually empty or brief" *and*
   its only example is `""`. That one line is why 95% of steps have no pass criteria, and it is
   now a hard blocker on re-enabling the push.
4. Stations 14 (preflight) and 16 (judging) are written into the plan but were never walked
   through with Terrence.

## Session (2026-08-03) — 10 refined cases via Opus; generation hits a hard OUTPUT CEILING; 12 transport defects fixed

> **⚠ Superseded in part by 2026-08-03b (above): the "OUTPUT CEILING" in this entry is a
> fence-parser defect, not a model limit. The measurements below are parser output.**

**Focus: take 10 "Not Executed" AWPTCM cases end-to-end (objectives → refined cases → pytest →
judges → tb470) automatedly with Opus.** Two of the three deliverables landed; the third is
blocked by a measured, quantified limit rather than by anything left half-done. Gate **719 → 775**
pytest (+92 Vitest unchanged). Full record: `ask-ck/pytest-create/autopilot/RESULTS-2026-08-03.md`.

- **Objectives + refined test cases: 10/10, all `valid=True`, zero warnings** — 422 refined steps
  under `refined-cases/{IPv4 (44),Management (71),Switching (75)}/`. The inputs were nearly empty
  (**6 of 10 had no objective at all, 8 had no steps text**), so essentially all content came from
  the title plus the three corpora, and it is domain-correct: the SNMPv1 objective covers
  read-only vs read-write community separation, GET-NEXT lexicographic ordering with clean
  end-of-MIB termination, SET rejection under a read-only community, and access-list parse
  behaviour at agent start-up. Refined-case total on disk: **42 → 53**.
- **New tool `tool/pt_autopilot.py`** drives both wizards headlessly through the **running
  server** (never a direct model call — the prompts, CLI grounding, coverage gate, skeleton and
  lints *are* the product). It substitutes each review step's own LLM suggestion for the
  reviewer's click and records that it did so, is resumable per-step across session limits, and
  reports `compiles` separately from `lint_clean`.
- ⚠️ **THE BLOCKER — generation is capped at ~9–20 `TestCase` classes.** The 32,000-token output
  budget is **shared with thinking**, is not raisable, and `--max-thinking-tokens` caps a single
  *block* not the total (measured **20,400** thinking tokens under a 2,048 cap). Above the ceiling
  a script truncates **without erroring** — and at 21 steps it truncated on a statement boundary,
  so `ast.parse` **succeeded** on a script missing 1 of 17 TestCases and the `__main__` entry.
  Also note trimming step count does **not** shrink the answer: the model fills the budget (44
  steps → 86,644 chars; trimmed to 21 → **88,593**). All 10 cases (44–78 sequence steps) are
  3–5x over. Gated up front now by `_size_overflow()`, free and instant, with an explicit
  `acknowledge_size_overflow` override. Measurements: `FINDINGS-generation-size-ceiling.md`.
- **Best pytest result** (T44297 trimmed to 6 verification steps): complete + parseable, 6/6
  TestCases, and it grades a clean sweep offline — `pt_grade.py` **C1 EXACTLY / C2 EXACTLY /
  C3 RIGHT / C6 YES (6/6)**; `pt_judge.py` criterion 4 **n/a because every TestCase reuses a real
  fragment** (no invented gap-fill). One lint error remains: it calls `setup.init_portlink()`
  directly, bypassing `_ck_bind_link` and the media assertion — the 2026-07-30 guard working.
- **The tb470 run path is VERIFIED for the first time** —
  `profiles/tb470/check` → `ok/ssh/framework/sudo` all true, Python 3.13.5. It had never passed
  because **`paramiko` was declared in no requirements file**; the polite failure
  (`"SSH connection failed: No module named 'paramiko'"`) read as a lab fault. Profile must use
  `user: terrenceb` (`st-art` does not authenticate) and the *server* needs the keyring
  `SSH_AUTH_SOCK` — `TESTBOX-ACCESS.md` §3a.
- **12 defects fixed, all mutation-tested (36 mutations attempted, 36 caught)**, in 3 new offline
  test files (`subprocess.run` monkeypatched, zero tokens). Highlights: `claude -p` was running as
  an **agent** (2.67M input tokens, 23 min, **$4.65**, empty result, `is_error:false`); its
  `result` field returns only the **final** assistant message so long answers lost their head;
  the caller's `system` message was **dropped entirely** on that path; `_JSON_SYSTEM_PROMPT`
  ("no markdown fences") was being sent to the two templates that need a **fenced** block;
  `gather_fragments` read an **unparseable** reply as an **empty** one (two cases recorded 0
  fragments while step 3 had selected 12 scripts); and `lib2to3` was removed in Python **3.13**,
  the version we target, silently disabling D3 py2 translation (now falls back to `fissix`).
- **Pending / not done:** nothing regenerated for the other 9 cases (they need splitting first, or
  chunked generation). **Three defects left OPEN by choice**, each needing a design decision:
  generation over-declares an unused `init_stk('stk_a')` so the script demands a stack tb470 has
  not got (the minimality guarantee covers `init_swi`, not `init_stk`, and no lint catches
  bound-but-never-used); `pt_preflight` cannot follow `_ck_bind_link`'s run-time link resolution,
  so no contract-based script can reach a clean RUNNABLE verdict; and `POST /fix_script` **regressed
  a good script** (37,744 → 25,172 chars, 0 TestCases) — harmless only because it does not write
  to disk. No hardware run happened: preflight correctly refused, so no bench time was spent.

## Latest session (2026-07-30) — tb470 de-stacked and cabled, and generation now targets a TOPOLOGY CONTRACT

**Focus: make Part 3b actually runnable, and fix the reason it wasn't.** Started as
".setup housekeeping", turned into a hardware fix plus the biggest change to generation since
the skeleton landed. Gate **612 → 719** pytest (+92 Vitest unchanged). Nothing regenerated yet.

- **`tb470.setup` COMPLETE, and the bench is genuinely different.** Terrence supplied the PDU
  (`10.36.150.14`, outlets **8**/**6** — the front-panel letters H/F are labels only; `Setup.py`
  does `int()` on that field) and cabled the two IE520s together. Roles were renamed on his
  call: **IE520s = `swi_a`/`swi_b`, AR4050S → `swi_c`, x230 → `swi_d`**. ⚠️ `swi_b` therefore
  binds a *different device* than it did on 07-29 — an older script's `init_swi('swi_b')`
  silently gets the second IE520. See memory `tb470-topology-and-setup`.
- **The "bugged out" stack was a SPLIT stack, and the fix was hardware, not config.** Both
  IE520s were provisioned into virtual chassis 3039 with uncabled stackports, so u5 became a
  **`Disabled Master`** in failover mode with **all 26 front-panel ports `err-disabled`** —
  which is why newly-cabled links stayed down. De-stacked both (`no stackport`,
  `no stack virtual-mac`, `stack 2 renumber 1`, reboot); both now report
  `Operational Status: Standalone unit` and **both links are up at 1000/full** (copper
  `port1.0.1`, fibre `port1.0.7`). ⚠️ **Do not cable 27/28 between them** — IE520 stackports are
  dedicated and `stack virtual-chassis-id` has no `no` form, so both are ID 1 in one chassis and
  a stackport link would recreate the duplicate-master state. Full detail in `TESTBOX-ACCESS.md`
  §4a.
- **`tool/pt_preflight.py` — offline "can this bench run this script?".** Built because
  `Setup.init_portlink()` returns **`(None, None)`** for an undeclared link, and the skeleton
  unpacks that into port attributes: on `3_Port_Fixed_port_test.py` every TestCase then dies on
  `portA.name`, reading as a *script* defect when the cause is *cabling*. It found **0/3**
  Port (7) scripts runnable; after the new `swi_a-swi_b` links, **2/3**. The last one wants
  `swi_a`↔`swi_c` (AR4050S, uncabled) — but that demand is a generation artifact, see below.
- **Topology profiles: generation targets a CONTRACT, never a bench** (`TOPOLOGY-PROFILES.md`,
  `tool/pt_profiles.py`). Terrence rejected feeding generation the bench's device list, and he
  was right: it would silently *weaken* a test to fit the hardware present, and a false green is
  unfalsifiable. So generation declares the **profile** it needs, a bench declares in its own
  `[misc]` what it **implements**, and the checker matches. Profiles are claimable in pieces
  (`base`/`fibre`/`tblink`/`stack`) because one monolithic topology accretes until nothing
  satisfies it. **Roles name LINKS, not devices** — tb470's `swi_b` is both the copper and the
  fibre partner over different cables. tb470 implements `base, fibre, tblink`; `stack` correctly
  reports not implemented.
- **The media trap this closes.** MDI/MDI-X is copper-only, the framework's `type1='port'`
  filter cannot tell copper from fibre (both are `port1.0.x`), and **the CLI is media-blind** —
  on the 1000BASE-SX port `speed ?` still offers `10…400000` and `duplex ?` still offers `half`.
  So the old `swi_a-swi_b = port1.0.1-…, port1.0.7-…` bound copper *only because copper was
  listed first*: one comma-order edit from setting `polarity mdix` into the void and reporting a
  confident green. `tool/pt_media.py` asserts media at run time from the pluggable — the only
  guard that survives someone swapping an SFP (u4 `port1.0.1` is 1000BASE-T, u5's is 10GBASE-TM).
- **Generation now emits the contract AND binds only what it uses.** `init()` resolves the DUT
  from `ck_role_dut` and binds its one link through fixed-frame `_ck_bind_link` (resolves the
  role, refuses a `(None, None)` link, asserts media); `ck_media.py` ships with every run from
  `tool/pt_media.py`. **Minimality:** the device set is now a *consequence* of the topology —
  one link ⇒ one partner, and the partner **is** that link's far end, so no second `init_swi()`
  exists to over-declare with (T33235 bound 4 devices and used 1). Extras are dropped with a
  `# NOT BOUND:` comment. Two lints enforce it: a direct `init_portlink()` outside the helper is
  an error, and using a device `init()` never bound is an error.
- **Corrections worth carrying:** ck.db's CLI reference absence means **UNKNOWN, not
  unsupported** (`polarity` isn't listed for `ie520`; the device supports it). And two of my own
  over-claims were retracted — the copper/10G module mismatch links fine, and `no stackport` did
  *not* clear the real member's dedicated stackports.
- **New doc — `ask-ck/ARCHITECTURE.md`** (executive summary, linked from the README doc map and
  from SERVER-README's head). One page: the stack and languages (**Python/FastAPI back end,
  vanilla-JS ES-module front end — no React, no TypeScript, no build step**), the four tools and
  their real state, the data layer with measured row counts, LLM strategy, the hardware bridge,
  the four invariants, deployment limits, and where the risk actually sits. Every figure was
  **measured, not copied from prose**, and the doc says so with a date — which immediately caught
  a stale live claim in the README (`4,652 commands, 993 with sample output` → actual **6,323 /
  1,250**, the reference having been refreshed from the authoritative per-device zips on
  2026-07-29). Corrected.
- **Pending / not done:** nothing regenerated, so preflight is still 2/3 and the three scripts
  in the tree are pre-change artifacts. Regenerating T33235 under the new frame is the
  experiment that tests whether over-declaration was the bottleneck. Step **`kind`
  misclassification** (`PLAN-permutation-expander.md`) is untouched and is what actually made
  T33234 grade 10/10 bad — though the partner is now a bound, contract-resolved device, so
  partner-side `polarity` is finally available as the automatable substitute for the faked cable
  swap.

## Latest session (2026-07-29c) — objective→Generate (Thread B), Part 3b unblocked, model-matrix judging

**Focus: shore up PyTest Creator generation so objective context reaches the `.py` output, then finish the Part 3 blockers.** (Ran alongside the reboot-scripts stream; commits interleave on `main`.)

- **Thread B (commit `81bc972`):** the objective now flows into the Generate prompt AND is baked into the emitted `.py` as a `# ==== OBJECTIVE ====` header (single source: it rides into both the artifact and the prompt via the embedded skeleton). New generate-prompt rule 1a grounds each verdict in the objective slice. Tests + gate green.
- **Part 3b unblocked (commit `83fb11d`):** `configs/tb470.setup` turned out to be the reference doc's worked example copied verbatim (x930/x530 — powered off). Read every live tb470 console + NIC/MAC tables and rewrote `tb470.setup` to the verified real rig (IE520 DUT / AR4050S / x230, verified portlink, skeleton sections, backup kept). Owed: PDU IP + inter-switch cabling. See memory `tb470-topology-and-setup`.
- **Part 3a re-run:** all 3 cases regenerated with Thread B (objective header everywhere; T33234's duplicate-portlink lint defect cleared), then a 5-model matrix (vllm-fast/thinking + claude haiku/sonnet/opus) judged side-by-side by opus + vllm-fast via the new `tool/pt_matrix_judge.py`.
- **Result:** T33233/T33235 → "good" (sonnet/opus) = generation half fixed. **T33234 = 10/10 "bad"** = the next shit-in is **sequence-extraction `kind` misclassification** (per-case reconfig→setup collapse; physical cable-swap→verify fake), not model quality. Folded into `ask-ck/ck-facelift/PLAN-permutation-expander.md` (deferred subsystem).

## Latest session (2026-07-29) — commit 10 lands; the module split is COMPLETE

**Focus: the one straggler from `PLAN-backend-module-split.md` — commit 10, the atomic
`routers/wizard.py` → `routers/wizard/` move. All 11 commits are now done (6 stays dropped).**

- **`routers/wizard.py` (1972 lines) is now a package.** Four route modules split on the
  file's *existing* concern order — `reviews` (148–981: load_case, step candidates, the
  three searches + suggests, confirm_step), `config` (982–1190: session clear, CLI status,
  LLM config, health), `synthesis` (1191–1497: objectives + steps), `export` (1498–EOF: the
  drop-in bundle + push_to_zephyr) — plus `_shared.py` (get_data + OUTPUTS_ENV; a leaf, so no
  import cycle) and `__init__.py` (mounts the four sub-routers, re-exports the public surface).
- **Every function body moved BYTE-IDENTICAL** — proven, not asserted: the four sliced bodies
  reassembled and `diff`ed against the original 148–EOF are identical (no line lost, duplicated
  or reordered). The only new code is the per-module import headers, computed from an AST scan
  of the actual free names in each slice (several grep hits were prose false-positives — reviews
  needs no stdlib/logging at all; export was the only module that logs). The last line of the
  file had no trailing newline, so `wc -l` said 1971 and a naive `NR<=1971` slice dropped the
  closing `}` of push_to_zephyr — the byte-identity diff caught it.
- **The two cross-module privates use RELATIVE imports** (`_session_llm_cfg` reviews→synthesis,
  `_authoritative_session` synthesis→export) so `test_shared_modules_decoupling` does not read
  one router's internal wiring as a cross-router reach. Both are also used within their own
  defining module, so the per-file unreferenced-private check stays green.
- **Six hardcoded `routers/wizard.py` source reads across the suite now go through one helper**,
  `tests/_wizard_src.py` (`wizard_router_paths()` / `wizard_router_source()`), which RAISES if it
  finds nothing. A hardcoded path that silently stops matching — passing green while covering
  nothing — was the precise failure mode the plan flagged; the helper makes the next move
  re-route every caller at once. Parametrized structural tests now fan out over the six package
  files instead of one, so **pytest rose 559 → 584** (more coverage, not new behaviour).
- **Also fixed a stale doc note:** `PLAN-llm-observability.md` still labelled its follow-on
  features "UNCOMMITTED"; they shipped in `47833de` (verified). Corrected.
- **Gate:** 584 pytest + 85 Vitest, both guards, ck.db signature unchanged (isolation held).
  `/health` ok (`is_permanent_db: true`, 39 sessions). Both commits (`3f07243` split,
  `a4435a8` doc fix) pushed to `origin/main`; tree clean.
- **No open stragglers left from prior plans.** What remains is done or externally blocked:
  `PLAN-auth-and-case-locking.md` unstarted (6 open decisions, D1 likely an org/IT call);
  `PLAN-pytest-testing.md` Part 3a needs the two LLM judges + T33233 regen, Part 3b blocked on
  `configs/tb470.setup` (Terrence-side hardware topology). See also memory
  `commit-and-push-on-session-end` for pushing from a Mac-attached SSH session.

## Latest session (2026-07-28f) — the wizard module split, all but one commit

**Focus: `PLAN-backend-module-split.md` Part B. 7 commits, `591dbb9`→`e0886c0`.
`routers/wizard.py` 2515 → 1971 lines, and `pytest_create.py` no longer imports anything
from it. 424 → 559 pytest tests.**

| commit | what |
|---|---|
| `591dbb9` | `refactor: extract wizard/descriptions.py` (plan commit 7) |
| `1f3b7e4` | `test: the ck.db snapshot cache key could not see a WAL write` (out of plan) |
| `104d3e6` | `refactor: extract llm_config.py + case_registry.py; drop pytest_create's wizard imports` (8) |
| `e15c360` | `refactor: extract session_store.py + wizard/{gates,backfill}.py` (9) |
| `77ab960` | `refactor: decompose export()` (11, taken before 10) |
| `03a0aac` | `refactor: rename CK_server/wizard → generator; a lost session write now 500s` |
| `e0886c0` | `test: E2E and smoke checks must not write the permanent ck.db` |

**Only plan commit 10 remains** — the atomic `routers/wizard.py` → `routers/wizard/` move.
Commit 6 stays dropped.

### The coupling fix landed

`pytest_create.py` opened with six **underscore-private** imports out of `routers/wizard.py`,
so renaming any one of them silently broke a different tool. They now live in leaf modules
both routers import: `CK_server/llm_config.py` and `CK_server/case_registry.py`. The plan's
own acceptance check holds — `grep "from routers.wizard import"` returns `main.py` and tests
only. `pytest_create._apply_workspace_llm` was a hand-copy of the wizard function whose
docstring said "Mirrors wizard…"; proven byte-identical in body (differing ONLY in the
annotation) and collapsed into one duck-typed `llm_config.apply_workspace_llm`.

### "Mechanical" was verified, not asserted — and it mattered

Every moved function was unparsed from HEAD, had the deliberate renames applied, and
compared. All 20 identical, bar three where a `'wizard'` literal became a `KIND` constant
(asserted mechanically, not eyeballed). For `export()` the check went further: HEAD's
monolithic `wizard.py` was loaded as a second module and both `export()`s run over the same
session with `REFINED_DIR` in tmp — artefacts byte-identical, whole response equal,
`wrote_bundle=True`. Comparing through the live server first had given an identical **400**
and proved nothing; equivalence on the error path is not equivalence.

### Three false greens found, all in tests

1. **A test that passed for the wrong reason.** Commit 8 moved `REFINED_DIR`'s reader to
   `case_registry`; three tests patched `wizard.REFINED_DIR`. Two went red.
   `test_backfill_noop_leaves_gate_closed` kept passing — its key has no bundle in the real
   tree either, so "backfill did nothing" was true whether or not the redirect worked, while
   it silently read the production `refined-cases/`.
2. **A guard that matched its own advice** (5th occurrence in this repo). My new check for
   `Connection.backup()` grepped the whole file, so mutating the call to
   `pass  # src.backup(dst)` left it GREEN — the docstring and the commented-out call both
   contain the string. Now reads code lines only via `tests/_prose.py`.
3. **An end-to-end test that accepted the wrong status.** The lost-write 500 test did not
   seed a session, so `confirm_step` 404'd long before reaching the persist; it accepted
   404-or-500 and asserted nothing.

### Two behaviour changes, on request

- **A failed session write now returns 500, not 200.** `persist_session` logged ERROR and
  carried on, so a confirm or export completed with the user's confirmed selections or
  synthesized objective gone and nothing in the response saying so. `pytest_create._pt_persist`
  had exactly that shape and was already fixed for that reason. Raises a DOMAIN error
  (`SessionWriteError`) so `session_store` stays framework-free; `main.py` has one app-wide
  handler.
- **Case ids sort numerically.** `AWPTCM-T100` sorted before `AWPTCM-T9` — a string compare
  on the id. Harmless only because every real key is `AWPTCM-T` + five digits.

### Test traffic no longer writes ck.db — and the rule behind it

Terrence: *"ck.db is designed to go dirty when users actually operate in it. When tests are
run for smoke checks or E2E or whatever, that data is useless and shouldn't be propagated."*

The pytest suite was already isolated. Two paths were not: **Playwright** (`webServer:
'./run.sh --bg'` with `reuseExistingServer: true` — i.e. attach to whatever is on :8000,
which is the real dev server) and **my own curl smoke checks**, which created a session row
for `AWPTCM-T45102` and bumped two stamps. Those three rows were discarded by restoring
ck.db from git; it is back to `sessions_rows 30185cd466774462` / 39 sessions. Both paths now
use `tool/run_scratch_server.sh` (throwaway `backup()` copy, port 8123, own pid/log files),
verified by driving the offending case load against it and confirming the real DB stayed
signature-identical while the copy took the write. `/health` now reports `db.db_path` +
`db.is_permanent_db`, since previously the only way to tell which database a server was on
was to read its process environment.

### State at close

- **559 pytest + 85 Vitest**, both guards, ck.db signature check — all green. `ck.db` clean
  at `sessions_rows 30185cd466774462`, 39 sessions.
- Every commit gated before it landed, staged by explicit path, and pushed.
- **Not done:** plan commit 10. Playwright not run (standing instruction).

## Latest session (2026-07-28d) — first real CLI session on hardware; it falsified a documented rule

> **Note on this log:** `SESSION_STATE.md` already uses `2026-07-28c` for the Generator
> deferred-per-step-loading work (`PLAN-backend-module-split.md` A1). PROGRESS has **no**
> entry for A1-A5 (`0c06586`…`0b47926`) — those six commits are recorded in SESSION_STATE
> and the plan's status header only. Left for whoever did that work; noted here so the
> next session does not read PROGRESS's top entry as covering it.

**Focus: drove a live device for the first time (tb105 `u5`, an 8-member x950 stack), then
reviewed the project's CLI-facing surfaces against what the hardware actually reports. The
headline is that a rule stated in three places was simply wrong, and only hardware showed it.**

- **"The FIRST index is the chassis/slot" was false — it is the STACK MEMBER.** In
  `portA.B.C`, A is the stack member, B is the bay (0 = base board, 1+ = a populated
  expansion slot), C the port. The live stack reported `port1.0.x`–`port8.1.x`, its first
  index tracking `show stack` member IDs 1-8 exactly, with members 5-8 each carrying a
  `.0.` base board AND a `.1.` expansion slot. The claim sat in `pt_generate_script.jinja`,
  the port-hardcode lint's own comment, AND `test_cli_feature_grounding.py`'s docstring —
  each contradicting itself, since all three illustrated it with `port1.1.x`, a change to
  the SECOND index. Per the governing lesson (the model implements the EXAMPLE), generated
  code was mostly unharmed; the wrong *rule* was the defect, because it leaves no concept
  that ports span members. All three corrected.
- **The harvested reference proved it independently, and the first test I wrote was wrong.**
  That test assumed every doc example was single-unit and asserted the first index was
  pinned at 1. It failed — `show stack resiliencylink`, `show platform`, `show powerinline`
  and `show udld port` all print `port2.x.y`. The failure was the better evidence: doc
  examples number a second UNIT, never a second chassis, and `show stack resiliencylink`
  carries both `port2.0.11` and `port2.2.11`, so one unit presents two bays under one first
  index. Now the assertion.
- **Two new lint warnings, from hazards only visible on real hardware.** (1) `interface
  eth0` under config — eth0 reports `Vlan: none` and is in no VLAN, but still appears in
  `show interface status` as an ordinary connected row. (2) A loop that enumerates
  interface rows and then drives the device with no `stackport` exclusion — stack links
  appear in that table with `stackport` in the Vlan column, so such a loop can split the
  stack mid-run. Both key off code shape, not case text. Zero false positives across all
  three real generated scripts.
- **A stack-detection alias set was built and then REVERTED — Terrence caught it.** The
  `.setup` file already declares stack membership (`[stack]`), the ports never to touch
  (`[configured_stackport]`) and the testbox cabling (`[portlink] tb-swi_X = ethN-portA.B.C`);
  inferring any of it from case prose repeats the exact mistake this project already
  recorded for port naming ("a RUNTIME hardware property — take it from the .setup, do not
  guess"). Measured before reverting: `_STK_RX` hits 192/195 corpus scripts that call
  `init_stk` (98%) but 0/4 stack cases written in prose — so the gate would have failed
  silently on precisely the new cases it was for. The right fix is to PARSE the `.setup`,
  which nothing in `CK_server` does today; that would make the stackport rule exact instead
  of heuristic. Not started.
- **`.setup` schema captured at last** — `ask-ck/pytest-create/SETUP-FILE-REFERENCE.md`,
  from a real testbox, closing the open TODO in `ART-EXECUTION-CHAIN.md` that asked for a
  working example. Also records `[switch] swi_a = /dev/u0` (the console mapping is the same
  `uN` namespace as the shell aliases) and that TFTP boot means CLEARING `[boot_from_flash]`,
  not setting it False. Writing `configs/tb470.setup` now needs only tb470's device list and
  cabling — the schema is no longer the blocker.
- **Session count discrepancy left alone:** the corpus port-literal count is cited as 350 in
  the generate prompt and 125 in the lint comment and test docstring. An independent count
  here gave 294 literals / 9,923 bound uses, matching neither — the counting method differs.
  Not reconciled; needs whoever took the original measurement.
- **Tests 393 → 424 pytest** (5 mine; the rest another stream's ck.db-isolation work, still landing at time of writing — re-check before commit) + 85
  Vitest, both guards green.

## Latest session (2026-07-28b) — the prompts were the defect, ~14 fixes, venv on 3.13

**Focus: "prioritize improving the prompts, the judges are a symptom not the cause"
(Terrence). Confirmed emphatically — every defect found this session came from our own
guidance or measurement, none from model weakness. 12 commits, `ed419aa`→`86993e8`.**

- **The governing lesson: where prose and an EXAMPLE disagree, the model copies the
  EXAMPLE.** An example in a prompt is not documentation, it is the specification the model
  implements. Four separate defects in generated scripts came from wrong examples in our own
  files. `tests/test_prompt_examples.py` now EXECUTES each prompt example against real
  harvested CLI output, so a wrong one fails in milliseconds with zero tokens spent — the
  two worst bugs below were pure data checks.
- **Two guaranteed-wrong-on-hardware defects.** (1) Rule 3b bound `port = dev.portA` (a
  `SwitchPort`) while rule 4d compared `[port]` against a string token — never matches, so
  every `show ecofriendly` step was a **false RED on every run**. Two rules disagreeing with
  each other. (2) Rule 4d's example had `if/elif` and no `else`, so the silent-failure case —
  precisely what rule 4c exists to catch — wrote **no verdict at all** and scored as a pass:
  a false green inside the anti-false-green rule.
- **The structural one, worst thing found all session.** Rules 4b/4c/4d — 6,480 chars
  including "NEVER HARDCODE A PORT NAME", "ASSERT ON THE FEATURE UNDER TEST" and "PARSE THE
  ROW FOR YOUR PORT" — were ALL inside `{% if cli_reference %}`. None depend on grounding.
  So for any case naming no harvested command (physical replug, reboot, traffic) the
  generator got a port-bearing skeleton with **every false-green guard removed**.
- **Skeleton deep dive** (Terrence: "reduce what's needed, clarify every portion, root
  assumptions in truth"): **39% smaller** (22,833→14,150 chars on a 14-step case; the 3-line
  idiom example had been emitted once per TestCase, ~49% of each block comment). Assumptions
  verified against the 830-script corpus — `mode(')#')` is the config idiom (4,812 uses) not
  `cmd('conf t')` (69); `port.name` for CLI text (1,013 vs 241). Wrong ones fixed: a
  `{{ devices }}` variable that was **never passed** (silent fallback every render), and
  `.down()`/`.speed` attributed to `SwitchPort` when they are `ATTestBox.Eth` methods
  (`dev.portA.speed = 1000` does not even raise — it creates a dead attribute).
- **`distutils.strtobool` in the skeleton was a LIVE break, not latent** — removed in Python
  3.12, and tb470 runs **3.13.5**, so every manual-step script would have `ImportError`ed on
  the target before running a test. `py_compile` cannot catch a missing module. Generalised
  into a lint over stdlib modules removed in 3.12/3.13.
- **A manual step could discard an entire testbox run.** `yesNo()` called bare `input()`
  while the runner never writes to stdin → 30-minute block; the timeout then `raise`d
  *before* writing stdout, throwing away every PASS/FAIL already produced. Both halves fixed.
- **The "returns 200 but the write never lands" debt was never a lost write.** `_pt_get`
  preferred a per-process cache over the DB, so a stale instance answered *and re-persisted*,
  overwriting newer work. Found a **24-day-old `drafting_server` process** on :8991 from a
  directory that no longer exists — killed. `_pt_get` now reloads when the DB is newer;
  `_pt_persist` raises instead of printing.
- **Measurement bug that invented two regressions.** `pt_grade` resolved a fragment's
  `maps_to` to a TestCase number, falling back to the raw step number for non-verify steps —
  but fragments legitimately map to SETUP steps. 15 of 41 mappings misresolved, so T33234's
  reported C2 "partially" / C3 "wrong" were **pure measurement error**: both are clean.
- **Domain rules the docs cannot supply.** The re-extracted sequence asserted "speed 1000 +
  duplex half … Link is UP" — **half duplex is impossible at ≥1 Gig**, a physical constraint
  no CLI page states. Compound cause: the source Zephyr step said "where supported" and the
  extractor dropped the qualifier. Both rules added; 1G+half assertions 1→0.
- **Environment: venv moved to Python 3.13.14 to match the testbox** (`032f521`), following
  the procedure already in `PLAN-backend-module-split.md` Part 0. `setup.sh` had two real
  bugs — `ensure_python` tried bare `python3` FIRST despite claiming newest-first (3.10 here
  while 3.13 was installed), and an existing venv meeting the floor is reused and never
  upgraded. Both fixed; the rationale is documented in README/requirements/SERVER-README.
- **Prevention mechanism** (`tests/_prose.py`): four times this session a check fired on its
  own advice text. Now encoded as `code_lines` / `flat` / `code_fences` with the four
  historical cases regression-locked.
- **Tests 208 → 295 pytest** + 72 Vitest, both guards green, `/health` ok on 3.13 with all
  83,816 embeddings. Every prompt fix verified by regeneration, not only by test.
- **Still open:** T33234 TestCase_8 (configures the partner's `polarity mdi` but never the
  local `polarity auto`; judges 5 bad / 1 good). Part 3b still blocked on `configs/tb470.setup`.

## Latest session (2026-07-28) — two "model defects" that were both OUR bugs

**Focus: the two items left open at the end of 27h. Both turned out to be defects in our own
tooling rather than LLM quality — the reported diagnosis was wrong in each case.**

- **`framework.ATLibrary` was NOT a hallucinated import.** `ATLibrary` is a real framework
  package; the **lint** was broken. `framework_surface` is keyed by module path
  (`ATLibrary.ATTools`, `ATLibrary.__init__`), so a package never has a bare key and a plain
  membership test rejected **every** package import — `from framework.ATDrivers import
  ATSwitch` included. `ATDrivers` passed only because it sat in a hardcoded allowlist despite
  being structurally identical. Now resolves packages from the index; the allowlist is gone
  (all 6 exempted names are real keys). T33235 lints clean with **code unchanged**. The
  review's suggested fix — ground the prompt's import surface — would have taught the model to
  avoid writing valid Python. `90e83ef`.
- **The LPI/EcoMode false green was a resourcing gap, exactly as Terrence said.** The
  `ecomode` tree was never passed to the prompt; AW+ calls it **`ecofriendly`** and it was in
  `ck.db` all along. Two defects: (1) `detect_commands()` is purely lexical, so prose
  ("EcoMode"/"LPI"/"EEE") has no path to `ecofriendly lpi` → added `FEATURE_ALIASES`; (2)
  worse, variant selection preferred the most-shared `show interface` variant, and only 1 of 8
  prints `current ecofriendly lpi` — so 3 of the 4 steps were grounded on output with **no**
  EEE field *while told to match it exactly and invent nothing*. **The grounding steered the
  model into the false green.** Graded relevance ranking fixes it.
- **Graded result:** T33233 2 gap-fill blocks (`bad×11, good×1`) → **0**; T33234 **12 of 12**
  (`bad×63, good×9`) → **1 of 14**; T33234 fragments 0/7 → **11/23** (answering the old
  "is selection broken?" question — no, the sequence was too vague to match on). Both lint
  clean, C1/C2/C3/C6 best-grade. Scripts now run `show ecofriendly` and parse the row for the
  port under test, asserting `Configured`/`Status`.
- **Terminology corrections from Terrence, worth carrying forward:** `ecofriendly` is the
  proper CLI name and "ecomode" is slang (recognised on input, never emitted); **`lpi` is
  deprecated** (modern diagnostics say EEE) but stays first-class because it is the only
  spelling the config command accepts, it is the live `show ecofriendly` value, and
  **TestLink cases are years old and almost unanimously say LPI** — and TestLink is where
  reused fragments come from. And **`port1.1.x` is not legacy**: it tracks chassis vs
  standalone (x908gen3 is current), and an **x950 with a populated card slot uses it too**, so
  port naming is a runtime hardware property.
- **Port names now come from the `.setup` topology.** The skeleton seeded
  `port = 'portX.Y.Z'` and the prompt literally instructed `port = 'port1.0.1'` — the origin
  of hardcoded ports, wrong on any chassis. Both fixed (corpus: 10,578 bound attributes vs 125
  literals), plus a comment-aware lint warning that caught 3 real hardcodes on a regeneration.
- **Tests 208 → 250** (+19 import-lint, +23 feature-grounding), 72 Vitest, both guards green.
  Judging artifacts consolidated back under `judging/Port (7)/`.
- **Hardware-agnostic is the GOAL, not a fallback (Terrence).** I had framed threading the DUT
  platform into grounding as making it "hardware-accurate rather than best-guess" — wrong on
  both counts. The scripts must run on **all** platforms interchangeably (the CLI barely
  deviates), so `prompt_block(product=...)` is deliberately left unpassed: tuning the reference
  to one platform would push code toward platform-specific output. Breadth-based variant
  selection is *correct*. `.setup` is the mechanism — `[portlink]` resolves ports at runtime, so
  the same source runs on an x930/AR4050S/x530 and yields `port1.1.x` on a chassis unchanged.
- **`.setup` binding fixed — two layers.** The lookup STRING is the `[switch]` key
  (`swi_a`/`swi_b`/… — 621 of ~650 corpus calls); the local VARIABLE carries the role
  (`dutA = setup.init_swi('swi_a')`). The generator was emitting `init_swi('dut')` from role
  names, which fails against any real `.setup`. `_setup_keys_for()` maps them positionally now.
- **Found a guaranteed-crash bug doing it:** the scripts called
  `init_portlink(self.dut, …)` three lines *above* `self.dut = dut` — an `AttributeError` on
  every run, so they could never have executed on the testbox. Valid syntax, so `py_compile`
  and every structural check passed it. Now a lint **error**; both cases regenerate clean.
- **Still open:** T33234 TestCase_8 (unrelated to LPI — configures the partner's
  `polarity mdi` but never the local `polarity auto`; judges 5 bad / 1 good).

## Latest session (2026-07-27h) — CLI grounding: the generator was starved, not stupid

**Focus: root-cause the "all 9 gap-fill blocks graded bad" result from Part 3a. Answer: a
RESOURCING gap, not model quality. Harvested the real AlliedWare Plus CLI reference into
`ck.db` and grounded both LLM prompts; added an objective-coverage gate. Uncommitted at
time of writing — see the commit that follows.**

- **The evidence that settled it.** Across the Part 2B matrix (5 models x 3 cases, one run
  each) **every model** fabricated a `speed=1000`/`state=up` output schema on T33235 —
  vllm-fast 39, vllm-thinking 52, haiku 13, sonnet 39, **opus 35**. A defect that survives
  Opus is not fixable by swapping models. Root cause: the prompts demanded "exact CLI
  fields" while showing **zero** examples of real output. Real output is
  `current duplex full, current speed 1000, current polarity mdix`.
- **It originates at step 2, not step 6.** `speed=1000` lands in each step's `verify` text
  at Sequence Extraction; `_render_skeleton` then stamps it into the skeleton **4x per
  TestCase**, and Generate obediently copies it (T33235: 13 in the sequence -> 57 in the
  script; the two fragment-backed cases had 0 -> 0). Grounding step 6 alone would have left
  the generator arguing with its own skeleton.
- **`tool/harvest_cli_docs.py`** — renewable harvest of `docs.atlnz.lc/preview/` into
  `ck.db` (`cli_commands` + `cli_command_products` + FTS). **73,006 fetches, 58.6 min, ZERO
  failures**; 4,652 unique commands (993 with sample output), 61,240 product x command rows.
  Content-addressed because a command page is byte-identical across families ~96% of the
  time (Terrence's "commands are standard across devices" rule, verified at scale); the
  per-product rows are a thin support matrix. Soft-404s (HTTP 200 + "may have moved in the
  latest rebuild") are detected and counted, never recorded as empty commands.
- **`tool/cli_lookup.py`** — retrieval + `prompt_block()`/`detect_commands()`, so only the
  commands a case actually references are injected. Wired into **both** prompts.
- **Measured result:** T33235 `key=value` **13 -> 0** in the sequence and **57 -> 0** in the
  script; T33233 shed 13 placeholder `portA` refs; all three cases now quote 14-23 real CLI
  formats where they previously quoted none. T33235 also went from *zero* fragments to 14
  (the grounded sequence gave script-search better terms), so it now grades C2 **exactly** /
  C3 **right** instead of `n-a`.
- **Objective-coverage gate (Terrence's invariant).** Every Zephyr step needs >=1 PyTest
  step. Prompted by a real regression: re-extracting T33234 went 14 -> 9 steps and silently
  dropped source step 4 — the whole MDI/MDI-X forced-polarity **negative path**. Enforced on
  the **Confirm** button for *2. Sequence* and *5. Generate* (Generate still completes), with
  a 409 that QUOTES each untested step; `acknowledge_coverage_gap` overrides deliberately.
- **Regressions the grounding itself caused — found by checking, three fixed:** `speed 2000`
  (invented value -> added an "arguments must come from the reference" rule); `show interface
  eth1` (the block picked the LONGEST sample, which was a TQ wireless *router* interface ->
  now prefers the variant most families share); `self.dut.port1.0.1` (a SyntaxError — a CLI
  port name used as a Python attribute -> added a "port names are CLI text" rule).
  ~~**Still open:** a hallucinated `framework.ATLibrary` import keeps T33235's lint red.~~
  **CLOSED 2026-07-28 — it was a lint bug, not a hallucination.** `ATLibrary` is a real
  framework package; the import check tested bare-name membership against a surface keyed
  by module path, so *every* package import was rejected (`from framework.ATDrivers import
  ATSwitch` too) and `ATDrivers` passed only via a hardcoded allowlist. Check now resolves
  packages from the index; T33235 lints clean with the generated code unchanged.
- **Product debt found:** the server can return **HTTP 200 while the write never reaches
  `ck.db`** — thread-local SQLite connections go stale after an external write, and
  `_pt_persist` swallows the failure into a `print`. Cost real debugging time; workaround is
  restart-and-verify-`updated_at`, never trust the 200.
- **Tests/guards:** 208 pytest (+18 new CLI-docs) + 72 Vitest all green; both guards green;
  `/health` 200. `ck.db` 420 MB, still LFS-tracked, corpora untouched (the CLI tables are a
  new externally-sourced reference, not a corpus rebuild).

## Latest session (2026-07-27g) — adversarial review CLOSED (19 fixes, 4 batches) + network hardening + multi-user plan

**Focus: finish the verification that was paused at ~50% in 27c, fix everything real that it
found, then take the two accepted-risk security items to a decision. All committed + pushed to
`main` (11 commits, `6b50f80`→`94b98cf`).**

- **Re-fired the paused verification** over exactly the 35 unadjudicated rows (`wf_f4fcd274-366`,
  40 agents, ~19 min, 1.9M tokens): one verifier per file-cluster reading live code, then a
  dedicated refuting skeptic per confirmed finding. **21 survived, 14 dismissed** (10 refuted at
  verify, 4 killed by the skeptic), 0 unclear. The original run's script was gone (prior session,
  no `.claude/workflows/`), so this was a fresh workflow over the recorded rows — nothing lost,
  only the verdicts were missing.
- **Batch A `6b50f80` — export authority.** `/export` resolved the session client-side on a
  fallback (a stale tab could resurrect a deleted session and re-mark a case Complete), had no
  confirm gate, never invalidated downstream work when selections changed, and wrote the Complete
  marker before the most failure-prone write. All four fixed. **Migration guard:**
  `_backfill_from_refined` now marks the three reviews confirmed from the on-disk bundle, or the
  new gate would have 400ed every legacy re-export — verified across all 43 bundles.
- **Batch B `40ec299` — event-loop blocking.** The review named three blocking search handlers;
  an **AST sweep found four more**, incl. `load_case` (runs on every case load). Seven wrapped.
  The sharpest was `export`'s coverage-gaps call: a *guaranteed* 180s self-deadlock in
  `claude_agent` mode, then a misleading "your ck-agent didn't respond". Cold model load measured
  **16.2s**, not the estimated 8.5s → warmed on a daemon thread at startup.
- **Batch C `ba69e22` — silent content loss.** Anchored the traceability-note strip (unanchored
  `"Traceability" in …` was DELETING real verification steps, and the payload validator passed
  them, so cases exported a step short with no warning); replaced 13 fragile jinja slots with a
  `pyliteral` filter (a typed newline produced an **uncompilable** skeleton, shown to the user and
  fed to the model as the structure to copy); fixed setup-step provenance mis-attribution;
  tightened the provenance-echo regex. **The review's suggested fix for that last one did not
  work** — `_PROVENANCE_TAG_RX` is a loose lint check that also matches prose; caught by the tests.
- **Batch D `be9149d` — error signals.** Claude empty/truncated response guards (mirroring the
  OpenAI branch), the two frontend `fetch`es missing `res.ok` (one rendered an HTTP error as a
  *green success*, the other wiped the in-memory session), `keep_ids` pinning through the RRF
  merge, the stale run-status sweep, and the never-called `gc()`.
- **Security `6eaa43e` — the two accepted-risk items, decided by Terrence.** Verified live first:
  the box answered on its LAN IP and an unauthenticated `push_to_zephyr` returned 200. Now binds
  `127.0.0.1` by default (LAN exposure is an explicit `HOST=0.0.0.0`); `--force` is no longer
  hardcoded (it was disabling `upload_refined.py`'s own "already refined — SKIP" guard on *every*
  push); SSH host keys pinned trust-on-first-use. Confirmed after: LAN refused, localhost 200,
  SKIP fires by default and is still overridable with `?force=true`.
- **Data `e54fdd2`.** `AWPTCM-T37861` ("POE - lldp max power and cli power") shipped invalid JSON —
  a Python-style `\'` escape — since its first commit; the only one of 43. One backslash removed;
  all 43 now pass the export gate (was 42/43).
- **Two defects found by skeptics WHILE REFUTING**, not on the original list: the SSE latin-1
  mojibake (`text/event-stream` → requests defaults ISO-8859-1, so every non-ASCII byte on the live
  vLLM path corrupted silently as valid JSON, flowing into stored objectives and on to Zephyr —
  the most consequential correctness bug of the pass) and an inert Py2 prompt marker.
- **Backlog closed** as a `ck-facelift` historical record: 62 candidates → 31 fixed, 31 dismissed,
  0 outstanding. Dismissals kept **with their refutation reasoning** so they are not re-raised.
- **New plan (no code): `ck-facelift/PLAN-auth-and-case-locking.md`.** Terrence chose real
  multi-user as the end-state and added a hard requirement: a per-case session lockout so
  concurrent overwrites are impossible in *both* tools. Phase 1 (locking) is sequenced first and
  is **not** gated on auth — the concurrency bug is live today: session writes are unconditional
  whole-blob upserts keyed by case with no owner (`db.py:918`, 32 write paths), so two tabs on one
  case silently destroy each other's work. Six decisions deferred to next session, notably where
  identity comes from (likely an org/IT call).
- **Tests 48 → 190 pytest, 47 → 72 Vitest.** Several are structural rather than example-based (an
  AST sweep asserting no async handler calls a blocking function unwrapped; source assertions that
  a guard precedes the state write), so they catch the *next* regression. Also fixed test fixtures
  that were leaking throwaway sessions into `ck.db`, and removed two stray rows from earlier runs.
- **Invariants:** `guard_db_only` + framework-RO green, `/health` 200, no corpus/JSON/rebuild
  changes. Note the repo gate is currently red from **`tests/test_cli_docs.py`** — untracked
  in-progress CLI-docs work by another stream, failing independently of everything above.
  > **✅ CORRECTION (same session, re-verified after the doc sync): the gate is GREEN.** The other
  > stream fixed those two failures while this sync was being written. `./tool/run_tests.sh` →
  > guards OK, **208 pytest** (190 mine + 18 theirs), 72 Vitest, ALL GREEN. The "currently red"
  > line above was a stale observation restated without re-checking — it was true when first seen
  > and wrong within the hour. Their CLI-docs work (`pytest_create.py`, two prompt templates,
  > `tool/cli_lookup.py`, `tool/harvest_cli_docs.py`, `tests/test_cli_docs.py`) is still
  > **uncommitted** — that half was accurate.
  >
  > **Lesson for this tree:** it is shared with an active parallel stream, so any claim about gate
  > status or working-tree contents has a shelf life of minutes. Re-run `./tool/run_tests.sh`
  > before acting on one — do not trust a status statement from earlier in a session.

## Latest session (2026-07-27f) — LLM-button UX feedback + a 3-layer test suite

**Focus: (1) the reported LLM-button UX gaps, then (2) a full front-to-back automated-test
build-out — a Playwright E2E as a known-good reference, a Vitest+jsdom unit layer derived from it,
and one unified gate. All committed + pushed to `main` (4 commits: `4f990ea`→`e871caa`).**

- **LLM-button UX (`27c5d39`).** Three gaps: no pressed feedback, no success signal, no in-flight
  state (→ repeat clicks stacking LLM calls). Fix = one shared mechanism in `dom-helpers.js`:
  `setButtonBusy(btn,on,{label})` (pressed style + animated spinner + working label + disable +
  label stash/restore; returns `false` if already busy → the handler bails, the anti-stacked-call
  guard) and `flashButtonDone(btn,ok)` (brief green ✓ / red ✗). New CSS (`@keyframes ck-spin`,
  `.ck-spinner`, `.btn.is-busy/.is-done/.is-error`, `prefers-reduced-motion` fallback). Wired across
  all ~13 LLM buttons: generator synth/export, db-search suggest (previously no disable + alert-only
  errors), pytest (folded into the shared `ptApi` wrapper), llm health-check, provenance dry-run.
- **Playwright E2E (`4f990ea`) — sparingly-run, `e2e/`.** One deterministic golden-path against the
  REAL app (boot → load case → keyword-search TL/Zephyr/ATP → tick + choose → Export → assert the
  validation gate BLOCKS it). **Key discovery:** the keyword-only path can't produce a *green*
  export — `validate_zephyr_payload` needs a synthesized objective (`<ul>`+≥3`<li>`) and ≥2 steps,
  both LLM-only — so the honest 100%-deterministic assertion is the blocked outcome (Option A).
  Grounding selectors in the real DOM caught three things a guessed test would miss (collapsed-
  accordion sidebar; `#load-status` self-clears so `#session-view` is the real signal; in-progress
  cases pre-load chosen rows → assert the delta). Green + stable 4/4 runs (~7s). Pinned Chromium
  1234 downloaded (cached 1228 didn't match Playwright 1.62).
- **Vitest + jsdom unit layer (`8759903`) — regular, `js-tests/`.** 47 tests / 5 files, derived from
  what the E2E proved: `dom-helpers` (the button feedback — regression-locks the UX work), `tables`
  (renderers + the "top table hides already-chosen ids" behaviour), `chosen` (choose/dedup/restore),
  `merge` (dedup/score-resort/description-preference; the `merge*` fns exported for this — one-line,
  runtime-unchanged). DOM fixtures lifted from the real `index.html` (throws on a renamed id →
  drift-detection). Chose Vitest over Jasmine for the readable diff+source-frame failure output.
- **Unified gate (`e871caa`).** `tool/run_tests.sh` now runs guards + pytest (48) + `npm test`
  (Vitest 47) in one command; **fails loudly** if npm is present but deps aren't installed (a silent
  layer-skip would falsely read green). The E2E stays OUT of the gate (`npm run e2e`). Verified all
  green together, exit 0. Both `ck-facelift/PLAN-{playwright-e2e,frontend-unit-tests}.md` marked
  BUILT+PASSING.
- **Invariants:** guard_db_only green, `/health` 200, tree clean. No corpus/JSON/rebuild changes.

## Latest session (2026-07-27e) — Adversarial-review batch 3: llm.py JSON-parser cluster

**Focus: the correctness cluster from the backlog — 5 llm.py JSON-parse sites that silently
dropped LLM results. Verified each vs live code, unified them behind one robust extractor.
Committed + pushed this session (after the security batches landed at `1340d9b`).**

- **Root cause (shared across 5 findings):** ad-hoc greedy regexes (`\[\s*\{.*\}\s*\]`,
  `\{.*\}`) and a brace-depth counter that counted `{`/`}`/`[`/`]` **inside JSON string
  values**. Result: valid JSON with a bracket in a string, a prose brace before the real
  object, a nested array inside an object, or an illustrative non-JSON code fence would all
  silently return None / drop all steps / discard the ranking.
- **Fix:** hardened the single shared `extract_json_block` (`llm.py`) — it now (a) tries EVERY
  ```json fence in order and accepts the first that parses, (b) scans for a balanced structure
  that is **string-and-escape-aware** (brackets inside `"..."` ignored), and (c) walks opener
  positions **left-to-right across both bracket types** so the outermost structure wins (an
  object with a nested array no longer returns the inner array). Repointed the 4 ad-hoc sites
  (`parse_llm_to_structured`, `_parse_suggest_id_list`, `analyze_atp_coverage`, and the two
  in-function regexes) at it; `_parse_suggest_id_list` also accepts an object-wrapped array.
- **Caught my own design bug via the tests:** the first cut walked all `{` positions before any
  `[`, so a nested object was returned instead of its containing array — fixed by scanning by
  position across both types.
- **Tests:** +10 unit tests (`tests/test_llm_json_extractor.py`, no network) → **48/48 green**,
  guards green, `/health` 200. Backlog rows struck (5 llm.py + the agent_bridge:18 fold-in).

## Latest session (2026-07-27d) — Adversarial-review batch 2: path-traversal + auth

**Focus: triaged the next batch from `ADVERSARIAL-REVIEW-BACKLOG.md` — the 4 confirmed
security items (path-traversal + agent-bridge auth + CORS). Verified each vs live code, fixed,
tested in-process only (no testbox/network — honoring a CrowdStrike constraint). Uncommitted.**

- **Library-filename traversal (HIGH)** — `_persist_generated_files` validated only
  `Path(name).stem` (strips dirs) but wrote the raw `lib["name"]`, so `../../evil.py` escaped
  the generated dir. Fix: validate the full basename (`.py` + `_NAME_RX`) before building the
  path + assert the resolved parent == the script dir.
- **Export case_key traversal (HIGH)** — `export()` built `REFINED_DIR/group/case_key` from the
  client-supplied session key with no validation. Fix: `_CASE_KEY_RE` check at the TOP of the
  handler (before the LLM gaps call / payload validation / any write) + a resolved-path-under-
  refined-cases defense. Also closes the `wizard.py:1936/1939` export-gate findings. *(Caught my
  own ordering bug via the new test — the guard was initially placed after the validation early-
  return; moved it to the top.)*
- **Agent-bridge job ownership (HIGH)** — `deliver_result` accepted any `job_id` with no session
  check. Fix: `_Job` now stores its owning `session_id`; `deliver()` rejects a mismatched
  `session_id`; `/next` + `/result` bind to the authoritative `X-CK-Session` header (query param
  is legacy fallback).
- **CORS absent (HIGH)** — no CORSMiddleware, so any origin could drive `/api/agent/*` on a shared
  deployment. Fix: `CORSMiddleware` locked to a localhost allowlist, widenable via
  `CK_ALLOWED_ORIGINS`; `allow_credentials=False`, methods GET/POST.
- **Tests:** +8 in-process regression tests (`tests/test_security_batch2.py`) → **38/38 green**,
  guards green, `/health` 200. Backlog doc rows struck; ~41 candidates remain (next themes: the
  llm.py JSON-parser cluster (correctness), confirm_step invalidation cascade, run_status stale).

## Latest session (2026-07-27c) — Full adversarial review (14 domains) + top-cluster security fixes

**Focus: ran a full orchestrated adversarial review of the whole Ask-CK app (14 risk domains ->
3-skeptic verification -> synthesis), paused before synthesis to triage, then fixed the confirmed
critical/high cluster. Uncommitted at write time — Terrence commits himself.**

- **Review workflow** (`askck-adversarial-review`, run `wf_f53aa173-a88`): 14 domain reviewers
  produced **62 candidate findings** (2 critical / 21 high / 19 medium / 20 low); adversarial
  verification (3 refuting skeptics each, majority-real survives) ran to ~50% then was paused for
  triage. Priority weighting: security > data-integrity > correctness > robustness.
- **6 confirmed top-cluster fixes implemented + tested** (each verified against live code first):
  1. **SSH command injection (CRITICAL)** — `body["setup"]` flowed unvalidated
     (`pytest_create.py`) then UNQUOTED into the remote exec string (`pt_exec.py`). Fix: reject
     shell-metachar setup paths (400) **and** `shlex.quote()` every interpolated exec component.
  2. **Framework-guard bypass (CRITICAL)** — `_assert_command_allowed`'s verb denylist ignored
     redirection (`>`), inline interpreters (`python -c`), command substitution (`$()`/backticks),
     `rsync`/`install`, and `cp --target-directory`. Fix: refuse those shapes whenever the sub-command
     touches the framework dir; handle `-t`/`--target-directory` dest. (7 new bypasses blocked, all
     3 legit commands still pass; guard harness still green.)
  3. **Stored XSS (HIGH)** — the objective HTML is rendered raw via `innerHTML` and was never
     sanitized server-side. Fix: new stdlib `html_sanitize.py` allowlist sanitizer (tags-only, no
     attributes, drops script/style), applied at EVERY objective store point (synthesize/save/confirm/
     backfill/export). No JS changed — frontend renders the now-safe HTML.
  4. **Secret leak (HIGH)** — `llm_config.api_key`/`token` were serialized to the browser
     (`GET /session`, ~8 wizard session responses, `set_llm_config` echo) and written to the on-disk
     exported `*-session.json`. Fix: `redact_llm_config`/`safe_session_dict` in `models.py`, applied
     to all browser + disk session serializations (server-side store keeps the real key).
  5. **Admin reset never cleared PT sessions (HIGH)** — deleted with kind `"pytest"` but PT sessions
     use kind `"pt"` (`db._session_id`); the `scope=all` loop also only iterated wizard keys. Fixed.
  6. **Export destroyed a real first step (HIGH)** — unconditional `steps[0]` overwrite with the
     traceability note. Fix: prepend the note when `steps[0]` is a genuine step; only overwrite when
     it's already the note or blank.
- **Tests:** +16 regression tests (`tests/test_security_fixes.py`, `test_export_note_and_admin.py`)
  → **30/30 green**, both guards green, `/health` 200, redaction + setup-rejection verified live via
  TestClient.
- **Remaining ~45 candidate findings preserved** to `ask-ck/pytest-create/ADVERSARIAL-REVIEW-BACKLOG.md`
  for a later triage pass (marked "verify before fixing" — the review's own gate refuted ~⅓ of
  candidates). Notable still-open: LLM JSON-parser greedy-regex bugs (`llm.py`, ~5 findings), the
  agent-bridge job-ownership/CORS gap, `confirm_step` invalidation cascade, a couple more path-traversal
  candidates (export case_key, library filename).

## Latest session (2026-07-27b) — Backlog reconciliation + 4 open items cleared + adversarial review

**Focus: reconciled the stale §5/§8/§9 backlog against live code (5 items were already shipped),
then implemented all four genuinely-open items and ran a 3-reviewer adversarial pass that found +
fixed 4 real defects. Uncommitted at write time — Terrence commits himself.**

- **Backlog reconciled (§5a/§5b/§8/§9).** Verified live: `requirements.txt` exists, load_case ATP
  latency already fixed, `tool/` scripts already repathed, `ask-ck/` tracked+LFS, E2E smokes
  superseded by Part 2A/2B → all moved to a struck **§5a Resolved**. SERVER-README's stale manual
  `pip install` line repointed to `requirements.txt`.
- **Item 3 — Process-page label drift (`main.py`).** `/process` no longer emits broken `/#step-N`
  wizard deep-links or a `#Step N` nav bar that matched nothing. It now links the nav to the doc's
  own `## Step N:` headings via GitHub-style slug ids that exist on the page. **Adversarial fix:**
  the repeated `## Zephyr Cross-References (Step 3)` heading (×4) was producing duplicate `id`s
  (pre-existing, but the slug change kept it) → added a shared document-order dedup counter
  (`-1`/`-2`/…) consumed by BOTH the h2-id pass and the nav-slug discovery, so nav slug == heading id
  is guaranteed (verified: 19 h2s, identical order, 0 duplicate ids).
- **Item 2 — Output-generation hardening (`wizard.py::export`, `models.py`).** Export now **refuses
  to write the drop-in bundle** (the artefact that marks a case Complete) when the payload fails hard
  validation — previously it printed the issues and wrote anyway. New `ExportResponse.wrote_bundle`
  flag. **Adversarial fix:** the blocked message is now **stale-bundle-aware** — if a prior successful
  export left a bundle on disk the case is STILL Complete (and Push-to-Zephyr uses that older bundle),
  so it no longer falsely claims "NOT Complete"; wording scoped to "no drop-in bundle written to
  refined-cases/" (gaps/llm_config DB persistence before validation is real and acknowledged).
- **Item 1 — Error/loading UX (`generator.js`, `dom-helpers.js`, `index.html`, `styles.css`).** New
  shared `showStatus()` helper + `.status-banner` (success/warning/error/busy, theme-aware, escaped).
  Export + both LLM synthesis steps now surface outcomes **in-page** (busy spinner text, blocked
  reasons as a readable issue list, advisory warnings) instead of `alert()`/`console.warn` only.
  **Adversarial fix:** `#export-status` moved from generated HTML into static `index.html` so status
  calls can never silently no-op. **Reviewer cleared XSS** (title + items both escaped; validation
  issues are static server strings). `main.js?v=` 24→26.
- **Item 4 — Automated tests + CI (new `tests/`, `pytest.ini`, `requirements-dev.txt`, `tool/run_tests.sh`).**
  First test suite: 14 tests (validator branch coverage, `/export` refuse-to-write via TestClient,
  `/process` anchor correctness). Dev-only deps (`pytest`, `httpx`) in `requirements-dev.txt` (runtime
  `requirements.txt` stays lean). `tool/run_tests.sh` runs guards + pytest in one command (the
  `guard_*.py` idiom). Run: `PYTHONNOUSERSITE=1 .venv/bin/pytest -q` or `./tool/run_tests.sh`.
- **Adversarial review (3 parallel reviewers, findings verified before fixing):** duplicate-id
  (fixed), stale-bundle message (fixed), export-status silent-no-op (hardened), XSS (cleared, no
  defect), unescaped nav label (latent-only, trusted file, noted). All guards green, 14/14 tests
  green, `/health` 200, 0 duplicate ids on `/process`.

## Latest session (2026-07-27) — PyTest Creator D1/D3: fragment resolver boundaries + Py2→Py3 pre-translation

**Focus: resolved the three open PyTest Creator decisions (D1/D2/D3, from the now-deleted
`NEXT_SESSION_DECISIONS.md`), then implemented D1+D3 and adversarially tested them against the
live `ck.db`. Uncommitted at write time — Terrence commits himself.** All decision rationale is
preserved in memory (`d1-fragment-resolver-boundaries`, `d3-py2-fragment-translation`).

- **D2 — keep no cap (no code).** The chosen/redundant split already surfaces LLM dumps without
  hiding them, and only SELECTED fragments reach the Generate prompt, so a display cap wouldn't
  help the token/context concern.
- **D1 — hardened the single fragment resolver (`routers/pytest_create.py`).** The framing in the
  review ("whole-class vs main()-trim vs method-index") was ART-only; corpus measurement showed
  ~423/830 scripts aren't ART-class-shaped and the real defect was the **blind `loc[0]+60` fallback**
  firing on **650/3517 test_case entries (~18%, ALL legacy)**. New `_resolve_end()` boundary chain:
  exact `loc[1]` → next-unit-start−1 (573/650) → `loc_total` (77/650) → clamp. Also: helper symbols
  now resolve via their **real `loc`** (dropped the fragile stop-at-next-`def` regex that mis-sliced
  nested defs). Rejected per-library resolvers — `db.py` already normalized all 3 DBs to one schema.
  **No `ck.db` rebuild, no schema change.**
- **D3 — deterministic Py2→Py3 pre-translation (`routers/pytest_create.py` + `pt_generate_script.jinja`).**
  60 legacy scripts expose 342 reusable symbols with Py2 idioms; the Generate prompt had NO
  modernization rule and Rule 4 actively steered the model to *preserve* them; lint can't catch
  runtime-only tells (`.iteritems()`/`.has_key()`). New `_translate_py2()` via stdlib **`lib2to3`**
  (a real Py2 parser — translates what it can, fails loud on what it can't). Hardened so
  `status=="translated"` **guarantees valid Py3**: `expandtabs(8)` normalization (Py2 tab/space
  mixing) + a self-verify `ast.parse` that degrades to `parse_error` (ship original) if the result
  still isn't Py3. Fragments carry `py2_translated`/`py2_flagged`; provenance tags get `(py2→py3)`;
  the preview shows a ⚠ PYTHON 2 banner and the Generate prompt gets a **conditional** modernize rule
  (present only when a flagged fragment is selected — zero prompt weight otherwise).
- **Adversarial testing found + fixed a real defect:** 9/85 translations were invalid Py3 due to
  Py2 tab/space mixing lib2to3 preserves → fixed at source (see above). Final: 27 checks green
  (unit + integration); **6,193 symbols resolved across the whole corpus with zero exceptions**;
  both known ParseError files ship originals verbatim; the conditional prompt steer verified on/off.
- **Guards green** (`guard_db_only`, `guard_framework_readonly`); server boots, `/health` 200.
  `NEXT_SESSION_DECISIONS.md` deleted (all three decisions closed; rationale lives in memory).

## Latest session (2026-07-23) — PyTest Creator UX revision + adversarial-review worklist (physical steps, provenance fix)

**Focus: a large hands-on revision of the PyTest Creator while Terrence tested it, then a step-by-step pass through the T33233 adversarial-review worklist. All committed + pushed this session.**

**UX / flow changes (steps 1–4):**
- **1. Cases** split into **Open/Partial** + **Complete** dropdowns by PyTest work state; partials auto-sorted to top (`pt_cases` endpoint, `cases.js`).
- **2. Sequence** shows current steps + the LLM's extracted execution order with **drag-and-drop reorder** and a static `from`/source column; the extractor now also classifies each step's **kind**.
- **3. Script Search** rebuilt to a **per-step page-within-a-page carousel** (one step/screen, Prev/Next + green-✓/yellow-✗ step-pill nav); per-step candidate→chosen tables; selections stored per step (`{stepN:[ids]}`) and flattened downstream. Whole-sequence LLM field removed.
- **4. Fit Decision REMOVED** (moot under the fixed skeleton); visible steps 5–8 renumbered 4–7, internal `stepN` keys unchanged.
- **4. Fragments** rebuilt per-step, **no cap**, selected/not-selected split, chosen/redundant accounting (redundant nested faint-red under the chosen it duplicates), and a collapsible **assembled-artefact preview**.
- **Generator load perf:** `load_case` was ~64s because it fired a blocking `analyze_atp_coverage` LLM call; removed it → ~2.4s (data-display only).
- **Case hiding:** ART Limits Test + 4 ART Testsuites cases + Bootloader/GRUB Bootloader categories hidden from the Generator case lists (display-only, DB untouched).

**Adversarial-review worklist (T33233) — went step-by-step:**
- **#1 device-name reconciliation — DONE.** Bind the device names the reused fragments actually reference (`_detect_fragment_devices`); reconciliation note surfaced in preview + Generate prompt.
- **#2 physical-step handling — DONE.** 4-kind taxonomy (**setup/verify/physical/manual**) in `pt_extract_sequence.jinja`; single `_step_kind()` classifier; `_split_sequence` made non-mutating. Template branches: physical → operator-prompt + poll-`show interface status` for the state change (**SVT 3009 `waitForReplugEvent`**), manual → `yesNo()`, setup → `configure()`, verify → normal. **Physical plug/unplug steps are in scope, not skipped.**
- **#3 fragment quality — PARTIAL.** Cross-step dedupe already handled; **added `maps_to` phantom-step validation** (`_clean_maps`). Line-vs-class extraction + per-step cap deferred → `NEXT_SESSION_DECISIONS.md`.
- **#4 provenance divergence — FIXED + unit-verified.** `_restamp_provenance` now takes the sequence and remaps original-step → `TestCase_<n>` class number before stamping; previously a dropped setup step shifted the numbering and the wrong fragment's tag landed on the wrong TestCase. Both call sites (generate + fix) pass the sequence.
- **#5 guaranteed-fail default — no change needed;** lint already rejects `if False:`/`output=''`/`>>> FILL` in a saved script.
- **#7 zero-reuse marker — ADDED.** Verify steps with no fragment carry a positive `# ===== NO REUSE … =====` in the preview (physical/manual excluded).

**Open decisions for next session:** `NEXT_SESSION_DECISIONS.md` (repo root) — D1 fragment granularity, D2 per-step cap, D3 Py2 contamination.

**Verification:** provenance remap unit test; all 4 step kinds render + `py_compile`; preview gap-marker test (1 NO-REUSE on the uncovered verify, none on physical); routers import clean; all jinja templates parse; guards green; `/health` 200.

## Latest session (2026-07-22d) — Claude-agent token reporting + Haiku/Sonnet/Opus selector + Traceability-gaps decoupling

**Focus: (1) decoupled the Traceability-gaps LLM call from Objective synthesis (committed `8503cea`); (2) made the per-user Claude agent report token usage + cost and added a three-way model selector. Docs synced + committed this session.**

- **Traceability gaps decoupled from Objective synthesis (`8503cea`).** Step 4 (`synthesize_objectives`, `llm.py`) used to make a *second* LLM call (`generate_coverage_gaps`) just to inject an "Automation gaps (Traceability context)" block into `generate_objectives.jinja`. That block didn't meaningfully shape the declarative objective bullets, and gaps are already generated independently at **export time** when `traceability.md` is rendered (`/api/wizard/export`, `if not gaps: generate_coverage_gaps`). Removed the gaps block from the template and the internal gaps call — **Step 4 is now a single self-contained objective call**, and dry-run preview == real send byte-for-byte. `traceability.md` and its gaps are unchanged (still built at export). Existing cases already carry their gaps on disk → unaffected. Prompted by a two-model comparison where the gaps call added noise + tokens with no benefit.
- **Why "— tok" was showing (root cause, from the debug-log).** The user compared two Objective runs; one showed `937 in / 2,971 out`, the other "— tok". The debug-log (`CK_server/debug-log/`, which was **not** empty — an earlier diagnosis wrongly said so; the check used a flaky relative path + wrong template filter) showed the first was **vLLM** (`local_llm`) and the second was **Claude via the agent bridge** (`claude_agent`). The agent bridge simply wasn't forwarding token usage, so `normalize_usage` returned `None` and the badge honestly showed "— tok". The content rendered fine in both — observability gap only, not a truncated answer.
- **Claude-agent token usage + cost (this commit).** Four-file passthrough, all in-repo: `ask-ck/agent/ck_agent.py` now lifts `usage` + `total_cost_usd` from the `claude -p --output-format json` envelope and returns them from `/run`; `static/js/agent.js` (`ckBrokerLoop`) forwards them in the `/api/agent/result` POST; `routers/agent_bridge.py` passes `total_cost_usd` through; `agent_jobs.py` `deliver()` stores both on the job result in the exact shape `llm_debug.normalize_usage` expects (usage sub-dict + top-level `total_cost_usd`). Server side + `normalize_usage` were already ready — server-side `claude_code` reports tokens for the same reason (it keeps the envelope). Verified end-to-end with a simulated deliver (cache tokens fold into input, cost surfaces, no-usage still → honest `None`). **The ck-agent runs on the user's machine → they must restart it (`cd ask-ck/agent && ./run-agent.sh`) to enable this.**
- **Haiku / Sonnet / Opus model selector (this commit).** Mirrors the vLLM Fast/Thinking toggle: new `claudeAgentRow` radio group in `index.html` (shown only when `claude_agent` is selected, default **Sonnet**); `static/js/llm.js` wires Apply (`setLLMConfig`), a live-persist toggle (`applyClaudeMode`), restore-on-reload, the status line (`Claude — my local machine · <Model>`), and `main.js` binds the radios. The model flows `llm_config.model` → `job.model` → ck-agent → `claude --model <name>` (CLI aliases `haiku`/`sonnet`/`opus`). A model typed in the free-text field still overrides.
- **Guards green** (`guard_db_only`, `guard_framework_readonly`); `/health` 200.

## Latest session (2026-07-22c) — Push-to-Zephyr button + all 43 refined cases pushed to Zephyr v2.0

**Focus: built a "Push to Zephyr" button in the Generator's export step (shells out to `tool/upload_refined.py`), added title-cleanup + version-2 handling, then pushed all 43 Complete cases to the live Zephyr Scale (Server/DC) instance and audited them for consistency. Uncommitted at write time; committing + pushing to main this session.**

- **`tool/upload_refined.py` — new Zephyr-write capabilities:**
  - `--fix-title`: strips a leading `(N)`/`(…)` group from the case **Name** (e.g. `(4) Auto MDI/MDI-X` → `Auto MDI/MDI-X`); name-only PUT.
  - `--new-version`: **idempotent toward v2.0** — bumps 1.0→2.0 via the internal `POST /rest/tests/1.0/testcase/{id}/newversion` (reverse-engineered from a devtools HAR of the UI "New Version" → Accept), but does NOTHING if already at v2.0+ (never produces 3.0). New helpers `create_new_version` + `get_case_version_info`. Order per Terrence's spec: **fix-title → new-version → payload PUT** (atm PUT-by-key lands on the new latest version).
  - **Attachment de-dup (replace semantics):** `attach_file` now deletes any existing same-named attachment before uploading (the API has no update; repeated pushes were accumulating duplicate `traceability.md`). New `get_attachments` + `delete_attachment` (DELETE → 204).
  - **Looser link parser:** `parse_atpylib_links` now reads **un-backticked** ART suite IDs from the ATPyLib Cases section (most files author them in prose), filters year tokens (19xx/20xx), de-dupes per-suite, and skips a reviewed non-suite denylist (`1024`).
  - **Repathed discovery** to `ask-ck/objective-drafting/refined-cases/` (was still on the pre-2026-07-13 root path → found 0 cases). Fixed the misleading `Summary: 0 ok` counter (success was only counted on the web-links branch).
- **Server + UI:** new `POST /api/wizard/push_to_zephyr/{key}?dry_run=…` (`routers/wizard.py`) shells out to the CLI — the **server never handles the JIRA token** (the CLI loads it from `secrets.md`). "Preview Push (dry-run)" + "Push to Zephyr" buttons in the Generator step-6 export actions (`static/js/generator.js` + `styles.css`).
- **`_backfill_from_refined` (load fix, `routers/wizard.py`):** loading a previously-Complete case showed empty objective/steps because its runtime session in `ck.db` had empty step4/step5 (cases refined before the session captured them). Load now rehydrates step4/step5 from the canonical on-disk `zephyr_payload.json` (guard_db_only allows that read) and self-heals the DB session.
- **Push does NOT export-first (important):** an early version re-exported the bundle before pushing, which **degraded** a backfilled case's `traceability.md` (the incomplete session lacks step1–3 selections). Removed — Push now operates on the canonical on-disk bundle; click **Export Repeatable Bundle** first if you edited. One case (T33241) was hit + fully repaired (restored file, re-attached, `2024` link re-added).
- **Live outcome — all 43 Complete cases pushed + independently verified:** 43/43 at **v2.0**, 43/43 titles **clean** (32 had a `(N)` prefix stripped), 43/43 **exactly one** `traceability.md` (7 had duplicates, cleaned), **40** have ART web-links (3 have none — no ART IDs in their traceability.md, by design), step 0 is 39 identical + 4 intentionally richer (kept). Zephyr instance is Jira Server v9.4.3 / Adaptavist ATM; internal `tests/1.0` API accepts the Bearer PAT.
- **Guards green** (`guard_db_only`, `guard_framework_readonly`).

## Latest session (2026-07-22b) — vLLM streaming transport + stale-`llm_config` re-sync

**Focus: (1) built the streaming transport that Part 2B §7.7 named as the real fix for `vllm-thinking` read-timing-out on `generate_script`; (2) fixed the §7.3 stale-`llm_config` root cause in both routers. Committed at session close; push to main pending (this environment lacks GitHub SSH auth — Terrence to push).** Living doc: `ask-ck/pytest-create/PLAN-pytest-testing.md` §8 (streaming) + §9 (re-sync).

- **Streaming the vLLM path (`llm.py`).** The OpenAI-compatible branch of `_call_llm_raw` now sends `stream: true` + `stream_options: {include_usage: true}` and consumes the SSE body, accumulating `content`/`reasoning_content` deltas + final `finish_reason`/usage into the **same triplet** the non-streamed path produced — so every guard (length/null/truncation) and the token-usage badges are unchanged. **Why structural, not a bigger ceiling:** with a streamed body the HTTP `read` timeout is the gap *between* chunks, not the whole-response wall clock; vLLM streams `reasoning_content` throughout the thinking phase, so a reasoning pass of any length completes as long as chunks keep flowing. The prior static 600s floor could still be exceeded (§7.7: it was); this removes the ceiling. Anthropic native path left non-streaming (no such failure).
- **Verified live (real org vLLM):** `vllm-fast` trivial ask 1.0s + correct badges; `vllm-thinking` `generate_script`-scale prompt completed at 395.6s (`finish=stop`, was failing at 600s in Part 2B); **ceiling-gone proof** — a `vllm-thinking` call with a deliberately short **30s** read timeout ran **21+ min with no timeout** (killed for time, not failure), proving the read budget is now inter-chunk.
- **Token-processing-over-time capture (in progress).** Identical prompt through both models, chunk-instrumented. **`vllm-fast` baseline:** 48.7s, **first answer token at 21.3s** (21s of reasoning-only first), 8,733 completion tokens, 8,731 chunks. **Key finding: `vllm-fast` is *also* a reasoning model** — both reason and both stream `reasoning_content`; the difference is reasoning-phase *duration*, not reasoning-vs-not. The vLLM SSE structure is identical for both. **`vllm-thinking` on the same prompt: 2,149s (35.8 min, 44× slower), `finish=length`, ZERO answer emitted** — it spent the entire 32k-token budget on reasoning (29,137 reasoning tokens) and never transitioned to the answer. **Streaming fixed the transport (the 35.8-min call completed with no read-timeout — the 600s ceiling would have aborted it) but NOT the model's fitness:** `vllm-thinking` is unfit for `generate_script`-scale generation. Strengthens the vllm-fast-default recommendation. Infographic (token curves over time, both models): `ask-ck/pytest-create/comparison/vllm_tokens.html` (+ published artifact).
- **Stale-`llm_config` re-sync (`routers/wizard.py` + `routers/pytest_create.py`, §9).** Fixed the §7.3 root cause: both workspace-apply functions gated only on `_llm_is_active`, which reports headless CLI modes (`claude_agent`/`claude_code`/`grok_cli`) active unconditionally — so a session whose *stale* config was a headless mode could never re-sync to the workspace default and kept silently hitting the wrong backend. Now the **active workspace default is authoritative**: re-sync whenever the session config is inactive OR diverges from it (new `_same_backend` helper compares auth_method/provider/model). `_llm_is_active` left untouched (its status/`has_key` uses are correct as-is). Safe because `set_llm_config` is the only writer of a case's config and always writes it === the workspace default — no legitimate per-case divergence exists. Unit-verified 8/8 (no vLLM) + concurrency-reviewed. **Surfaced pre-existing debt (§9.4):** dual-instance sessions (in-memory cache vs fresh DB load) can drop unrelated state under concurrency — logged, not this fix's fault, not a blocker.
- **Still deferred:** Part 3a/3b (the `wizard.py` twin bug is now fixed).

## Latest session (2026-07-22) — vLLM read-timeout fix + §1.5 provenance tags + Part 2B model matrix

**Focus: continued the plan after the standing "fix next session" vLLM read-timeout note. All work uncommitted at session end — Terrence commits himself.** Living doc: `ask-ck/pytest-create/PLAN-pytest-testing.md` §7 (full bug-by-bug log with rationale).

- **vLLM read-timeout fixed (`llm.py`).** The two HTTP calls hardcoded `timeout=120`, ignoring every caller's requested timeout entirely — the actual cause of the `suggest_zephyr`/`synthesize_objectives` failures logged in the prior handoff. Now a `(connect=10, read=<caller's timeout>)` split, with the `local_llm` read floor raised to 600s (only when the caller asked for ≥120s, so the health-ping's 30s still fails fast). Verified against real requests.
- **§1.5 inline source-provenance tags — built** (was tracked debt from Part 2A). `# ART/SVT/legacy <suite/file> lines a-b` tags derived mechanically from fragment metadata, or `# AI <model> <date>` for gap-fill; stamped authoritatively server-side after generation (never trusting LLM self-report). Verified on a real live T33234 regenerate — found and fixed a real duplicate-tag bug along the way (model echoed the prompt's instruction text as a second comment line; fixed by stripping the whole leading comment run, not just the first line). Also scrubbed a `— not yet implemented` string leaking into the skeleton's placeholder `failed()` text.
- **`max_tokens` was never overridable — found live.** Verifying §1.5 hit a real `finish_reason=length` on `generate_script` at the 16000-token default (a full generated script is the biggest-output step). Threaded an optional `max_tokens` param end-to-end (`run_prompt`→`_call_llm_with_meta`→`_call_llm_raw`); `generate_script`/`fix_script` now request 32000.
- **Two more real bugs found and fixed while setting up Part 2B** (both blocked the pipeline, not cosmetic): (1) a session's stale `llm_config` (leftover `claude_agent`) never re-syncs to the workspace default because `_llm_is_active()` treats headless-CLI auth methods as unconditionally active — same latent gap exists in `wizard.py`, left unfixed there (bigger blast radius); (2) `confirm_step` rejected a legitimate `fragments: []`/`matches: []` answer (empty list is a valid "no reuse needed" result, e.g. a `decision: new` case) because Python falsy-checks an empty list the same as "never ran" — blocked the ENTIRE rest of the pipeline for any case with a genuinely empty Fit Decision. Both fixed narrowly, verified live.
- **Part 2B built and run for real** (`tool/pt_model_matrix.py`, new): 75 real LLM calls (3 target cases × 5 LLM-bearing steps × vLLM-fast/thinking + Claude Haiku/Sonnet/Opus). Grok CLI is logged in but genuinely quota-exhausted (real 403) — logged as an omission, not silently dropped. Results committed at `ask-ck/pytest-create/comparison/Port (7)/<CaseKey>/<step>.json`. **Headline finding: `vllm-fast` is the clear reliability+latency winner (0/15 errors); `vllm-thinking` failed 3/15 — including `generate_script` timing out even at the raised 600s floor** — confirms the plan's own hypothesis that streaming, not just a bigger static timeout, is the real fix needed for the thinking model on large-output steps. Keyword-vs-LLM step-3 search: one case showed full agreement with mechanical rank, the other showed the LLM genuinely promoting a better-matching script the keyword scorer under-ranked (misleading vocabulary overlap between two suite families) — both real, useful signal.
- **Verified LLM access live before assuming blocks:** vLLM key present + working, Claude Haiku/Sonnet/Opus all reachable via `claude -p --model <alias>`, Grok logged in but quota-exhausted, tb470 reachable (SSH/sudo/framework) but `configs/tb470.setup` genuinely absent (Terrence-side physical-topology prerequisite — the one real remaining block, per §5b).
- **Still pending:** Part 3a (offline judging, criteria 1-4, two LLM judges) and Part 3b (tb470 execution, criteria 5-6) — gated only on `configs/tb470.setup` + a stored testbox profile.

## Latest session (2026-07-21b) — PyTest Creator Part 2A: first real vLLM walkthrough + vLLM-path hardening

**Focus: Part 2A — first real end-to-end walkthrough of the 8-step PyTest Creator flow on T33234 (`AWPTCM-T33234`, Port Auto MDI/MDI-X), driven headless via the org vLLM against the permanent `ck.db`. All committed + pushed to main (`e6c0d64`, `1ccf1a7`).** Full record: `ask-ck/pytest-create/PART2A-WALKTHROUGH.md`.

- **Pipeline works end-to-end steps 1–6.** load_case → extract_sequence → suggest_scripts → assess_fit → gather_fragments → generate_script all return correct output against the live DB; the generated ~24–35 KB script **compiles + passes conformance lint**. Step 7 (run) correctly gates with a clean `400` when no testbox profile exists (fails safe). Every step verdict: **KEEP**; the 8-step decomposition + confirm-gating is sound, nothing mergeable. Live execution (7–8) is blocked only on the `tb470` profile + `.setup` prereq (Part 3b).
- **Three real vLLM-path bugs found + fixed (`e6c0d64`, all in `llm.py`).** All rooted in the org models being **reasoning models** (chain-of-thought in `message.reasoning_content` before the answer in `message.content`): (1) `max_tokens=2000` exhausted mid-reasoning → `content` null → raised to 16000 for `local_llm`; (2) parser assumed non-null string — crashed on `None` and silently degraded on cap-truncated JSON → now guards + raises a clear `finish_reason=length` error + falls back to `reasoning_content`; (3) `extract_json_block` tried `[` before `{` so a top-level object with a nested array returned the inner array → now picks whichever bracket appears first. The health-ping's tiny prompt had masked all three — no headless vLLM run had ever completed before.
- **Adopted the documented vLLM system+user shape + FILL-marker guarantee (`1ccf1a7`).** `resources.md` documents system+user; the code sent user-only. `run_prompt` now prepends a default JSON-only steer (`_JSON_SYSTEM_PROMPT`), threaded through `_call_llm_with_meta`→`_call_llm_raw` (OpenAI: system role; Anthropic: top-level `system` field). Measured on `extract_sequence`: completion tokens 7959→5141 (−35%), latency 45.5s→28.9s (−37%), and the `notes` field went **empty→populated** (model now honors the skip-and-note rule). Separately, generation non-determinism left `# >>> FILL` scaffolding comments in one run (lint caught it) → fixed with a deterministic server-side `_strip_fill_markers` (44→0, filled code preserved) **and** a strengthened `pt_generate_script.jinja` rule.
- **Content findings for Part 2B/3 (not pipeline breaks):** extract_sequence initially over-expanded + ignored the skip-and-note rule (fixed by the system message); assess_fit verdict flip-flops `new`↔`extend` (reasoning-model non-determinism); **inline provenance tags (§1.5) confirmed NOT emitted** by the model (prompted, not enforced); a `— not yet implemented` string leaks into `failed()` reasons; generated CLI syntax (e.g. `polarity auto`) needs on-device validation.
- **Still pending (next):** Part 2B (keyword-vs-LLM + model matrix: vLLM fast/thinking, Claude Haiku/Sonnet/Opus, logged per-case), Part 3a/3b (judging + tb470 execution). Guards green; `/health` ok (830 scripts, 83816 embeddings).

## Latest session (2026-07-21) — PyTest Creator: DB-only source fix, framework read-only guard, standardized template (Part 1)

**Focus: planning + building the PyTest Creator standardization/testing effort. All committed + pushed to main.** Living plan: `ask-ck/pytest-create/PLAN-pytest-testing.md`.

- **Fixed a live DB-only violation (`c29f53e`).** `routers/pytest_create.py::_read_source` was reading script source off the retired `testsuites_art/` mount (`Path(rec["path"]).read_text()`), which no longer exists on disk. Now reads from `ck.db` (`rec["source_text"]` / `db.get_script_source`); `rec["path"]` is provenance-only. A 4-agent full audit of all 17 `CK_server/*.py` confirmed this was the ONLY live violation; cleaned up dead scaffolding (removed `DATA_DIR`/`PT_DATA_DIR` anchors, vestigial `SESSIONS_DIR`/`_session_path`/`GLOBAL_LLM_PATH`, stale comments). **Extended `tool/guard_db_only.py`** from 1 to 4 detected shapes (retired corpus JSON; script source off disk; retired mount roots; retired corpus-dir anchors).
- **Testbox framework dir is READ-ONLY (`152e86b`).** `/home/st-art/framework` (profile `framework_path`) must never be written/edited/mutated; copy locally to edit. Enforced in `pt_exec.py` (`_assert_write_allowed` on SFTP targets, `_assert_command_allowed` on remote commands, source-vs-dest aware) + new runnable `tool/guard_framework_readonly.py` (15 cases).
- **Part 0 — logging contract (`ca90ff8`).** `ask-ck/pytest-create/LOGGING-CONTRACT.md`: the required per-step log format, verified against the framework source on tb470 + a real 101-case log + the tool's `parse_framework_log` (all three agree). Gotchas: empty `passed()/failed()` emits no marker; results are 4-valued (PASS/FAIL/ERROR/UNSUPPORTED).
- **Part 1 — standardized script template (latest commit).** Generation now **fills a fixed skeleton** (`templates/pt_script_template.py.jinja`) instead of composing freely: data-driven `init` (switches/stacks/portlink detected from sequence+fragments), suite `configure`/`tear_down` (no pass/fail), one `TestCase_<n>` per verification step with the logging contract + per-case `tear_down`, `__main__` footer. `pt_generate_script.jinja` rewritten to fill-not-compose; `_lint_generated` extended for template/logging-contract conformance. Static exemplar chosen: `art/1363_ipv6/test-1363.1002.py` (replaces the dynamic 6011). Inline source-provenance tags planned (§1.5: `# ART/SVT/legacy <id> <lines>` / `# AI <model> <date>`). Docs: `TEMPLATE-SPEC.md`.
- **ART execution chain documented** (`ask-ck/test-composer/ART-EXECUTION-CHAIN.md`) — the full ATPyLib run chain in dependency order (`<hostname>.cfg` → `.setup` → build load → `runAll` → `runTestSuite` → `test-*.py` → log → parse), the two entry points (suite runner vs our direct single-script path), and what Test Composer should reuse vs emulate. Finding: our direct `-s <setup>` path likely does NOT need `config.cfg` (a suite-runner concern) — to verify on the first real tb470 run.
- **Testbox reachable this seat:** `ssh tb470` (device on u5, passwordless sudo, framework present). Neither `configs/tb470.setup` nor `tb470.cfg` exists yet — prerequisites before Part 3b execution.
- **Still pending (next):** Part 2A (first real end-to-end walkthrough on T33234), Part 2B (model-comparison harness), Part 3a/3b (judging + tb470 execution). Guards green; `/health` ok.

## Latest session (2026-07-20c) — ck.db is the PERMANENT single source of truth

**`ck.db` committed to the repo via Git LFS; courier/source files deleted; rebuild removed. All pushed to main.**

- **DB is now THE data, not a cache.** `ck.db` (412 MB) + its ~84k vectors + the bundled offline embedding model are committed via Git LFS (`.gitignore` un-ignores them; `/var/` rule anchored so it no longer shadows `ask-ck/var/`). A fresh clone gets a populated, semantically-searchable DB with **zero build step**.
- **Couriers/intermediates DELETED** (148 files): `zephyr_cases.jsonl`, `index.json`, `slim_index.json`, `zephyr_master.json`, `testlink_awp.json`, `test_id_description.json`+`.csv`, `candidates.json`, `decisions/*` (14), ~120 `suite_*_enriched.json` + `all_test_suites.json`, `scripts_index.json`, `scripts_slim_index.json`, `scripts_sources.jsonl`, `scripts_index_enrich.jsonl`, `framework_surface.json`, `scripts_index.meta.json`. **Kept:** the raw Zephyr XML export (immutable provenance root).
- **No rebuild / no APIs / no re-fetch.** `tool/build_db.py` is provenance-only and refuses to run (would delete the committed DB). Admin panel Rebuild-DB + Rebuild-embeddings removed (`routers/admin.py`, `admin.js`, `index.html`); reset-session + restart kept. `setup.sh` verifies the shipped DB instead of building it.
- **Verified after teardown:** server boots + all searches (keyword/semantic/hybrid/code) work with couriers GONE; `/health` ok, vectors on, 83816 embeddings; guard green; `build_db --fresh` correctly refuses. Order was safe: committed+pushed+fsck-verified the DB *before* any deletion.
- Docs synced: README, SERVER-README, this file, PLAN-db-only-search (final-state header). Memory: `db-is-permanent-source`.

## Latest session (2026-07-20b) — Strict DB-only Phase 1 + script-code + semantic embeddings

**Read next for design:** `ask-ck/ck-facelift/PLAN-db-only-search.md` (Phase 1 now ✅). Committed this session.

- **Literal script source code ingested.** `build_script_index.py` → `scripts_sources.jsonl` (830 files / 5,782 code chunks); `build_db.py --fresh` filled `scripts.source_text` + `script_chunks` + `chunks_fts`. `db.search_code` / `search_code_hybrid` return real line-scoped code.
- **Semantic embeddings populated.** `build_db.py --embed` → **~84k vectors** across all 5 entities incl. `vec_chunks` (was 0). `/health` reports `vector_search:true, embeddings:83816`.
- **Embedding model is now stand-alone.** Bundled under `ask-ck/var/models/`, forced `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` in `db.py` + `run.sh` — zero external dependency (the org vLLM LLM is the tool's function, not an external dep).
- **Strict DB-only runtime (Phase 1 DONE).** `data.py` + `pytest_create.py` source every corpus/reference from `db.*`; dead `load_json_safe`/`load_json_abs` removed; `main.py` **fails fast** if `ck.db` absent; **`tool/guard_db_only.py`** fails if a corpus JSON read reappears under `CK_server/` (verified it catches a regression).
- **Three latent bugs fixed:** (1) `build_db.py embed()` checked `db.HAS_VEC` before opening the connection that sets it → `--embed` had never run. (2) `db._vector_hits` ran the sqlite-vec KNN as a JOIN → sqlite-vec rejects it → error swallowed → semantic/hybrid silently returned keyword-only. (3) huggingface load-time ping (above).
- Docs synced (README, SERVER-README, both DB plans). ck.db gitignored = derived rebuildable cache (documented rationale).
  > **Superseded (2026-07-20b):** that last clause is no longer true — `ck.db` became the
  > **permanent, committed** source of truth (Git LFS, un-ignored, NOT rebuildable; the
  > courier build inputs were deleted and `build_db.py` refuses to run). Left in place
  > because dated entries are frozen; see the newer entries above and `db-is-permanent-source`.

## Latest session (2026-07-20) — LLM observability + Local LLM + admin panel + fast restart

**All committed + pushed (`47833de`, on top of `66fb289`).** Nothing pending.

- **LLM observability (`PLAN-llm-observability.md`, DONE).** Per-panel "Last LLM request" debug footer + token badges (honest `— tok` where a transport reports no usage); per-session JSONL log in gitignored `CK_server/debug-log/`; `GET /api/llm/recent` + `/log`. Backend: `llm._call_llm_with_meta` split into `_call_llm_raw` + instrumented wrapper; ContextVars `current_panel_id`/`current_request_path` set by main.py middleware from `X-CK-Panel`/path; recorder in `llm_debug.py` (credential-whitelisted). New: `CK_server/llm_debug.py`, `routers/llm_debug.py`, `static/js/llm-debug.js`.
- **Local LLM (org vLLM) login mode.** Third radio `local_llm` → OpenAI-compatible `http://vllm.ai.atlnz.lc/v1`, rides the existing OpenAI HTTP path; **Fast/Thinking toggle** (`vllm-fast`/`vllm-thinking`) applies live (no Apply click). Key stored server-side in gitignored `CK_server/secrets.local.json` (0600; env `LOCAL_LLM_KEY` fallback), never in browser/cfg/session/response/debug-log. `local_llm` is now the **default** radio. New: `CK_server/local_llm_key.py`.
- **Cold-load status:** `GET /api/wizard/llm_config` (no secrets) so a fresh page shows the real login, not "No credential". **Cache-Control: no-cache on `/static/js/*`** so bare-specifier ES-module imports always revalidate (was: stale child module shadowing new code even after a `?v=` bump).
- **Admin panel + fast restart.** Hidden admin panel (**double-click CK's face**): reset current-case / workspace / ALL sessions, rebuild embeddings + rebuild DB (background jobs polled at `/api/admin/job`), restart server (touches a watched `.py` so `--reload` fires). `routers/admin.py` at `/api/admin/*`; `static/js/admin.js`. **Localhost/single-user — no auth.** `run.sh --bg` (prompt-free bg start) / `--restart`; a plain restart needs only `run.sh`, NOT `setup.sh` (which rebuilds the DB).
- Also: earlier this window, an adversarial review (verify agents died on a session limit → findings adjudicated by hand) drove 6 fixes; see the plan's handoff header.

## Latest session (2026-07-16) — SQLite migration DONE + DB-only-search direction planned

**Read next:** `ask-ck/ck-facelift/PLAN-db-only-search.md` — the phased plan + testbox checklist for the next session.

- **DB migration COMPLETE (`PLAN-db-migration.md`).** All four commits landed: **A `6cb97ca`**, **B `bdb2043`**, **C `14cf4ad`**, **D `1a0ef2a`**. Corpora + sessions now live in `ask-ck/var/ck.db` (gitignored, rebuildable via `python3 tool/build_db.py --fresh --verify`). Server reads corpora from the DB (per-request `zephyr_cases.jsonl` scan + ~50 MB boot RAM gone); FTS5 keyword search (parity 79/80 vs live scorer) + sqlite-vec hybrid/semantic (`mode=keyword|hybrid|semantic`). **Vector `--embed` runs only where `enable_load_extension` exists (Linux / `pysqlite3-binary`)** — not mac system Python; keyword degrades gracefully.
- **Two feature branches built — STAGED, UNCOMMITTED, unit-verified, DB-rebuild pending:**
  - **Scripts literal-code** — the DB had only enrichment/tags/signatures; now captures actual `.py` source: `scripts.source_text` + `script_chunks` (per test-case/helper, loc-sliced) + `chunks_fts` + `vec_chunks`; `db.search_code`/`search_code_hybrid`. `build_script_index.py` emits `scripts_sources.jsonl` (courier), `build_db` ingests it (graceful if absent).
  - **Zephyr enrichment** — fixes two silent-drop bugs (`<details>` plain bodies → `script_text`, ~1,300; per-step `<testData>`, ~1,285) + adds `issues` (JSON, ~480) & `attachments` (filenames, ~250) as nullable columns; `script_text`+`refs_text` into `zephyr_fts` recall only (results unchanged).
- **DIRECTION DECISION — strict DB-only search:** `ck.db` is the SOLE search + runtime-reference source; server reads ZERO JSON; originals ingest direct-to-DB; JSON survives only as a build courier for remote sources (testbox/APIs), never searched. Phase 1 (repoint the ~5 remaining `data.py`/`pytest_create.py` runtime JSON reads to existing `db.*` getters) is the small first step. **Not started — for a future session.**
- **Pending single rebuild:** the two branches + the real extractions (Zephyr XML re-extract, scripts on the testbox) all land in ONE coordinated `build_db --fresh --verify` (+ `--embed`) — see the plan's testbox checklist.

## Latest session (2026-07-14) — PyTest Creator built + UI polish

- **PyTest Creator fully implemented** (was a 501 stub). 8-step gated flow turning a Complete refined case into a runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test script, executed on a real testbox, iterated via an LLM fix loop to Final Validation. Plan + living tracker: **`ask-ck/pytest-create/PLAN-pytest-creator.md`** (start there for PyTest Creator work).
  - Sidebar steps: 1. Cases / 2. Sequence / 3. Script Search / 4. Fit Decision / 5. Fragments / 6. Generate / 7. Run / 8. Validate, plus a **Testboxes** panel.
  - New files: `tool/build_script_index.py` + `tool/enrich_script_index.py` (script index: 999 files across testsuites_art/svt_scripts/test_scripts + 55-module `framework_surface.json`; outputs to `ask-ck/pytest-create/data/`); `CK_server/pt_exec.py` (testbox profiles in gitignored `secrets.testboxes.json`, framework-log parser, threaded paramiko SSH runner); full rewrite of `routers/pytest_create.py`; 7 prompt templates (`pt_*.jinja`, `enrich_script_index.jinja`); `models.py` `PtSession`; `llm.py` `run_prompt`/`extract_json_block` + `timeout` param.
  - Robustness fix: LLM replies that come back as a bare JSON array (instead of the wrapped object) are now tolerated across sequence/matches/fragments parsing.
- **Export path fix**: the Generator's *Export Repeatable Bundle* wrote to the pre-restructure `ask-ck/refined-cases/` (didn't exist). Now uses the `REFINED_DIR` anchor → `ask-ck/objective-drafting/refined-cases/`. Verified by exporting T33233 (complete count 42 → 43).
- **UI**: new **Help → Main** splash page (default landing) with the CK photo, welcome blurb, and collapsible per-tool guides in inverse-sidebar order (Generator open, PyTest Creator, then Test Composer / Zephyr as TBD); CK photo added to the sidebar "Ask CK" logo line; buttons/dropdowns/search bars no longer stretch full-width; Generator panels gained an "Objective / Test Case Generator" eyebrow header above the dynamic case title.
- **Docs**: root `README.md` (hero CK image + per-tool guides matching Main), `SERVER-README.md` (PyTest Creator section), `SESSION_STATE.md`, and this file updated. `ckc.jpg` copied into `CK_server/static/` so it serves at `/static/ckc.jpg`.

**Remaining for PyTest Creator** (needs credentials/hardware): run `tool/enrich_script_index.py` with a logged-in CLI then rebuild; first real-LLM walkthrough (suggested case AWPTCM-T33234); first real-testbox SSH run; gitignore/LFS decision for the regenerable `ask-ck/pytest-create/data/`.

---

**Prior session theme (2026-07-13)**:
- **Repo restructure**: `drafting-tool/` → `ask-ck/CK-main/` (server code in `CK_server/`, was `drafting_server/`); root `data/`, `refined-cases/`, and process docs → `ask-ck/objective-drafting/`; per-tool dirs pre-staged (`ask-ck/pytest-create/`, `test-composer/`, `zephyr-tool/`).
- **Repathing**: new `CK_server/paths.py` single source of truth (DATA_DIR, REFINED_DIR, PROCESS_MD); `data.py`, `wizard.py`, `main.py`, `run.sh` fixed for the new layout. Boot-verified (410 cases: 368 open / 42 complete / 3 in progress).
- **Ask CK multi-tool facelift** (see `ask-ck/ck-facelift/PLAN-facelift.md`): app renamed **Ask CK**; sidebar sections (top→bottom) LLM (+ **Configure** panel), **Zephyr Templating Tool** (4 stub steps), **Test Composer** (1 stub step), **PyTest Creator** (Cases wired + Creator stub), **Objective/Test Case Generator** (the full wizard, visible steps renumbered **1–6**, display-only).
- LLM login UI moved out of old Step 0 into a main-area **Configure** panel (all element ids preserved; `showLLMConfig`/`#llmCredential`/`#llm-config-card` dead code removed).
- New navigation: `goToPanel(panelId)` primitive + `goToStep()` wrapper; `PANEL_META` page-header registry; ✓ nav-badges scoped to `#nav-generator`.
- Backend stubs: `routers/zephyr_tool.py`, `routers/test_composer.py`, `routers/pytest_create.py` (`/api/zephyr-tool|test-composer|pytest-create/status`; pytest `generate/{key}` → 501).

**Prior session (2026-07-13, Grok)**: load_case zrefs verify; relevance-ranked external Zephyr; dual case dropdowns; Search+Suggest Steps; table/stack-overflow fixes; workspace LLM persistence; gaps moved to synth/export; favicon; `git lfs migrate`.

---

## 1. High-Level Status

| Area | Status | Notes |
|------|--------|-------|
| Architecture Decision | Complete | Server-backed (FastAPI), multi-tool workbench (Ask CK) |
| Project Structure | Restructured 2026-07-13 | All work under `ask-ck/`; anchors in `CK_server/paths.py` |
| Core Backend | Strong | Gates, file sessions, search/suggest for TL/Zephyr/ATP, relevance zrefs, workspace LLM file |
| LLM Integration | Complete | Three login modes via sidebar Configure: **Local LLM** (org vLLM, OpenAI-compatible, Fast/Thinking, default), Claude Code CLI (per-user agent), Grok CLI; workspace default in the sessions table (`id='_workspace_llm'`); real-only (no MOCK). Per-request observability: debug footer + token badges + `CK_server/debug-log/` JSONL (2026-07-20) |
| Admin / restart | **Complete (2026-07-20)** | Hidden admin panel (double-click CK's face): reset sessions, rebuild embeddings/DB (background jobs), restart server. Fast restart: `run.sh --bg` / `--restart` (setup.sh only for first-time/rebuild). Localhost/single-user; `/api/admin/*` |
| Data Integration (Generator steps 2–4) | Implemented | Real TL candidates; external Zephyr ranked; ATP scored; Search/Suggest merge on all three |
| Repeatable Outputs | Advanced | Templates + note construction; export → `objective-drafting/refined-cases/`; gaps generated at synth/export |
| Process Enforcement | Implemented | Server-side confirms (domain steps 1–3) before synthesize |
| Frontend UI | Advanced (multi-tool) | Ask CK sidebar: Help→Main splash + tool sections; Generator + PyTest Creator full; Test Composer/Zephyr stubs; `goToPanel` navigation |
| PyTest Creator | **Complete (2026-07-14)** | 8-step gated flow (Cases→Validate) + Testboxes; script index + framework-surface; SSH execution; LLM fix loop. Tracker: `ask-ck/pytest-create/PLAN-pytest-creator.md`. Pending: enrichment run, real-LLM/testbox shakeout |
| Test Composer / Zephyr Templating | Scaffolded (TBD) | Placeholder panels + router stubs only |
| Documentation | Updated 2026-07-13 | PROGRESS / SERVER-README / LESSONS / READMEs / BoS-EoS prompts repathed |
| Hosting / nginx | Ready | Example config (paths may need the CK-main update) |
| Persistence | File-based | Per-case `CK_server/sessions/<key>.json` + workspace LLM JSON + refined-cases export |
| Polish & Completeness | Good | Facelift verified (boot + endpoints + served UI); manual E2E smoke still recommended |

**Overall Phase**: Usable. Generator and PyTest Creator both runnable end-to-end (PyTest Creator awaiting first real-LLM/testbox shakeout); Test Composer and Zephyr Templating remain scaffolds awaiting design/implementation.

---

## 2. Key Decisions & Rationale (Carry Forward)

- **Ask CK is the umbrella**: one server (`CK_server`), one UI (`static/index.html`), multiple sidebar tools. Future tool = card div + `PANEL_META` entry + sidebar item + router module (+ `include_router` in `main.py`).
- **Numeric step scheme is load-bearing and display-decoupled**: `data-step` 0–5, panel ids `step-0..step-5`, badge ids `#step1-badge..#step5-badge`, session keys `step1..step5`, and `confirm_step/{key}/{1|2|3}` are UNCHANGED. Sidebar labels 1–6 are display-only. Never bulk-replace "Step N".
- **Paths live in `CK_server/paths.py`** — anchor all data/output/doc references there, never CWD-relative.
- **Server-backed is required** (LLM synthesis, growing data, nginx host, extensibility).
- **Repeatability**: Jinja prompt templates + structured parse/output templates + server-built first testScript note.
- **Process gates must be real** (server-side confirms before synthesis).
- **All Ask CK work stays under `ask-ck/`**.
- **Gaps are not a review-step form field**: user confirms ATP selections only; LLM writes Gaps for Traceability at synthesize/export (`generate_gaps.jinja`).
- **LLM preference is workspace-scoped**: Apply/Login (Configure panel) persists the workspace default to the sessions table (`id='_workspace_llm'` — migrated off the old `sessions/_workspace_llm.json` file in the 2026-07-16 DB migration; any lingering `.json` is legacy). load_case copies onto cases without active config. `set_llm_config` no longer requires a case — keyless `POST /api/wizard/set_llm_config` saves the workspace default; with a key it also stores onto that case's session. `GET /api/wizard/llm_config` returns it (no secrets) for cold-load status.
- **PyTest Creator selection is isolated**: `ptCase` global + `#ptCaseSelOpen/#ptCaseSelDone`; must never touch `currentKey` / `#caseSel` / page header.
- **Complete vs open cases**: Complete = `refined-cases/**/AWPTCM-Txxxx/zephyr_payload.json` exists; partials (session progress) listed first in Open dropdown.

---

## 3. Current File Structure

```
ask-ck/
├── ck-facelift/PLAN-facelift.md    # 2026-07-13 facelift plan (as executed)
├── CK-main/
│   ├── SERVER-README.md            # Operational manual
│   ├── run.sh                      # PYTHONPATH=CK-main, uvicorn CK_server.main:app
│   ├── nginx-drafting-server.conf.example
│   ├── (design assets + legacy single-file index.html)
│   └── CK_server/
│       ├── main.py                 # Ask CK title; favicon; /process; 4 routers
│       ├── paths.py                # DATA_DIR / REFINED_DIR / PROCESS_MD anchors
│       ├── data.py                 # loads from objective-drafting/data/
│       ├── llm.py                  # gaps gen, suggest TL/Zephyr/ATP, analyze rank-only
│       ├── models.py
│       ├── routers/
│       │   ├── wizard.py           # Generator API (/api/wizard)
│       │   ├── zephyr_tool.py      # stub (/api/zephyr-tool)
│       │   ├── test_composer.py    # stub (/api/test-composer)
│       │   └── pytest_create.py    # stub (/api/pytest-create; generate → 501)
│       ├── static/index.html       # Ask CK multi-tool UI
│       ├── static/favicon.svg
│       ├── templates/prompts/      # generate_objectives/steps/gaps, suggest_*, analyze_atp_coverage
│       ├── templates/outputs/traceability.md.jinja
│       └── sessions/               # _workspace_llm.json + AWPTCM-Txxxx.json
├── objective-drafting/             # THIS DIR: PROGRESS, LESSONS, PLAN, PROCESS, README
│   ├── data/                       # zephyr_master, candidates, decisions, suites, zephyr_full (LFS)
│   └── refined-cases/<Group>/AWPTCM-Txxxx/
├── pytest-create/                  # (empty) future PyTest Creator assets
├── test-composer/                  # (empty) future Test Composer assets
└── zephyr-tool/                    # (empty) future Zephyr Templating Tool assets
```

---

## 4. What Is Currently Implemented (Working)

### Backend
- Data load anchored via `paths.py`: zephyr_master, candidates, decisions, slim_index, test_id_desc, testlink (boot-verified counts).
- **Step 2 zrefs**: relevance scoring over slim_index (keywords, hard anchors, omit current Cases list + primary); batch JSONL enrichment for top hits; returns `score` + `justification`.
- LLM: CLI modes `grok_cli` / `claude_code`; Jinja prompts; provenance; no MOCK.
- **generate_coverage_gaps** at synthesize (+ export if gaps empty).
- **Workspace LLM**: `_workspace_llm.json` on Apply/Login; applied on load when case has no active config.
- **GET /api/wizard/cases**: dual lists + counts; search + suggest endpoints for TL/Zephyr/ATP.
- Export: writes to `objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/`; validation hooks.
- **Tool stubs**: `/api/zephyr-tool/status`, `/api/test-composer/status`, `/api/pytest-create/status` + `POST /api/pytest-create/generate/{key}` → 501.

### Frontend (Ask CK UI)
- **Sidebar** (always expanded): LLM status + **Configure**; Zephyr Templating Tool (1. Info / 2. Test Plan / Cycle / Cases / 3. Link Test Scripts / 4. TBD); Test Composer (1. TBD); PyTest Creator (1. Cases / 2. Creator); **Objective/Test Case Generator** (1. Cases … 6. Test Steps (LLM)).
- **Navigation**: `goToPanel(panelId)` toggles `.tool-panel` cards + section-aware active state; `goToStep()` wrapper keeps all wizard flows; `PANEL_META` drives page header (tool panels get static titles; Generator shows `KEY — Title`).
- **LLM Configure panel**: relocated login chunk (radios, Check Grok/Claude CLI, model, Apply/Login, instructions) — ids preserved; `updateLLMStatus` still dual-writes inline + sidebar status.
- **PyTest Creator Cases**: **Complete cases only** (`#ptCaseSelDone`), fed by the same `/api/wizard/cases` fetch inside `refreshCaseSelects`; `handleCasePairChange` shared helper; selection isolated in `ptCase`; Creator panel shows selected case.
- Placeholder panels (dashed `.placeholder-panel`, theme-aware) — zt-info and tc panels fetch stub `/status` messages.
- ✓ nav-badges scoped to `#nav-generator`; heading badges + confirm/synthesis flows unchanged.
- Prior batch retained: dual case dropdowns, Search+Suggest toolbars, cols-5/cols-6 tables, editors, review summary, post-synth teal **Export Repeatable Bundle** + **Edit / Revise Steps** guard, favicon.

---

## 5. What Is Not Yet Implemented (Priorities)

> **Backlog reconciled 2026-07-27** against the live code — several long-standing rows
> were already shipped and had gone stale. See **§5a Resolved since 2026-07-13** for the
> struck items (kept for auditability); §5b is the genuinely-open backlog.

### 5a. Resolved since 2026-07-13 (verified live 2026-07-27)
- ~~**Manual E2E smoke on the facelift** / **Real CLI smoke on full UI path**~~ — **superseded.**
  The facelift has been in production use for weeks, and PyTest Creator Part 2A/2B drove a
  real end-to-end walkthrough on live vLLM (fast + thinking) **and** Claude Haiku/Sonnet/Opus
  (75 real LLM calls). The Generator flow + Configure-panel login are exercised every session.
- ~~**load_case ATP rank is slow (LLM)**~~ — **fixed** (2026-07-23). The blocking
  `analyze_atp_coverage` LLM call was removed from Load ([`wizard.py`](../CK-main/CK_server/routers/wizard.py) ~L757);
  Load is now keyword-scored + instant (~64s → ~2.4s), LLM ranking is on-demand via the
  ATPyLib step's "Suggest with LLM" button.
- ~~**Repath/verify `tool/` scripts** (`upload_refined.py` etc.)~~ — **done.** `upload_refined.py`
  is fully on the `ask-ck/objective-drafting/refined-cases/` layout and was used to push all
  43 Complete cases to live Zephyr (2026-07-22c).
- ~~**`requirements.txt` / setup**~~ — **exists** at `ask-ck/CK-main/requirements.txt`. (The
  SERVER-README's manual `pip install fastapi uvicorn …` prose was stale and has been repointed.)
- ~~**`ask-ck/` tree untracked / LFS patterns unconfirmed**~~ (was a §8 Known Issue) —
  **obsolete.** 285 files tracked under `ask-ck/`; `data/zephyr_full/*.xml` resolves `filter: lfs`
  and is LFS-listed.

### 5b. Open backlog

**Genuinely open — user-facing / quality** — *all four DONE 2026-07-27b (see the session entry above)*:
1. ~~**Error handling + loading UX**~~ — **DONE.** In-page `.status-banner` on export + both LLM
   synthesis steps (`showStatus`); load_case latency was already fixed (§5a).
2. ~~**Output generation hardening**~~ — **DONE.** Export refuses to write a bundle that fails hard
   validation (`wrote_bundle` flag; stale-bundle-aware messaging). *Remaining nice-to-have: broaden
   validator exemplar coverage (thin ATP, empty selections) — low priority.*
3. ~~**Process Reference page label drift**~~ — **DONE.** Nav links the doc's own `## Step N:`
   headings via deduped slug ids; broken `/#step-N` / `#Step N` anchors removed.
4. ~~**Automated tests + CI**~~ — **PARTLY DONE.** First test suite exists (`tests/`, 14 tests,
   `pytest.ini`, `requirements-dev.txt`, `tool/run_tests.sh`). *Remaining: a `.github/workflows` CI
   job to run `tool/run_tests.sh` on push — deferred (no CI runner wired for this repo yet).*

**Feature work (not "polish")**
- **Design first real step of a new tool** — M (Test Composer, or Zephyr Templating → Info).
- **PyTest Creator Part 3a/3b** — offline LLM judging + first real tb470 execution; gated
  on `configs/tb470.setup` + a stored testbox profile (Terrence-side physical prereq).
- Server-side indexing for full jsonl/suites search quality (M).

### Lower / Future
- Hash routing / deep links (refresh currently lands on Generator Cases) (S–M).
- Multi-user auth (L).
- Advanced LLM (critique loop, few-shot from past refined cases) (L).
- One-command nginx setup (S–M).

---

## 6. How to Resume Work (For Future Sessions)

1. Read this **PROGRESS.md** completely.  
2. Read **`ask-ck/CK-main/SERVER-README.md`** (run + workflow).  
3. Skim **LESSONS_LEARNED.md** (esp. 2026-07-13 entries).  
4. Start server from repo root:
   ```bash
   ./ask-ck/CK-main/run.sh
   # → http://localhost:8000/
   ```
5. Apply LLM once (sidebar **LLM → Configure**) — preference persists in `_workspace_llm.json`.  
6. Use **Open / partial** for unfinished work; **Complete** for refined payloads.  
7. Do not reintroduce review-step gaps editing or MOCK paths; do not renumber the internal step scheme.

---

## 7. Important Context to Remember

- Main goals: **repeatable process** + **repeatable outputs** with user review gates and templated LLM.  
- Ask CK is becoming multi-use: Generator is the mature tool; PyTest Creator / Test Composer / Zephyr Templating Tool are scaffolds with matching `ask-ck/<tool>/` dirs for future assets.  
- Legacy single-file tool (`CK-main/index.html`) is reference only.  
- Gaps belong in Traceability artefact (LLM-authored at completion), not as a mid-wizard free-text gate.

---

## 8. Technical Debt & Known Issues

### Technical Debt
- LLM JSON parsing hardened 2026-07-27e (single string-aware `extract_json_block`); a fully
  structured-output contract is still a future nicety, but the greedy-regex silent-drop bugs are gone.
- Full zephyr_cases.jsonl not fully indexed for search (keyword scan + slim_index scoring only).
- **Test suite exists** (`tests/`, 48 tests via `PYTHONNOUSERSITE=1 .venv/bin/pytest` or
  `./tool/run_tests.sh`; dev deps in `requirements-dev.txt`). Still **no CI runner** (`.github/workflows`).
- zrefs scoring ~1.5s over 45k slim_index — acceptable but not optimized.
- ~~load_case still runs ATP LLM ranking (latency)~~ — **fixed 2026-07-23** (removed from Load; on-demand only). gaps no longer on load (good).
- ~~`tool/` scripts not yet verified against the 2026-07-13 restructure paths~~ — **done** (`upload_refined.py` repathed + used to push 43 cases).

### Known Issues / Limitations
- Shared multi-tenant server pooling one CLI login is unsupported (per-user local host intended).
- Grok CLI may still emit preamble; stripping helps but is imperfect.
- GitHub: large sources must stay LFS in **all** history commits (use `git lfs migrate` if reintroducing big files). ~~The `ask-ck/` tree is currently **untracked**~~ — **now tracked** (285 files; `data/zephyr_full/*.xml` resolves `filter: lfs` and is LFS-listed).
- `/process` page anchor text ("Step 1..4") predates the 1–6 sidebar renumber; links were never live (no hash routing). *(Still open — see §5b item 3.)*
- Some older session JSON may still hold stale Step 3 gap text; synth/export overwrites for Traceability.

---

## 9. Prioritized Backlog with Effort Estimates

*(Reconciled 2026-07-27; the 4 quality items cleared 2026-07-27b — this table lists only open work.)*

| Priority | Item | Effort | Notes |
|----------|------|--------|-------|
| Medium | First real new-tool step (design + build) | M | Test Composer or Zephyr Templating |
| Medium | PyTest Creator Part 3a/3b | M | Offline judging + tb470 exec; gated on `configs/tb470.setup` |
| Medium | Full data indexing | M | zephyr_cases.jsonl search quality |
| Low | CI job for `tool/run_tests.sh` | S | Test suite exists; just needs a `.github/workflows` runner |
| Low | Validator exemplar breadth | S | Thin ATP / empty-selection edge cases in `validate_zephyr_payload` |
| Low | Hash routing, multi-user, advanced LLM, nginx one-command | M–L | |

**DONE 2026-07-27b:** Error/loading UX (in-page banners), Output-gen hardening (export refuse-to-write
+ `wrote_bundle`), Process-page drift (deduped heading-anchor nav), first automated test suite (14 tests).

**Completed this session (2026-07-13, Claude)**:
- Repo restructure support: `paths.py` + repath of data.py / wizard.py / main.py / run.sh (boot-verified)  
- Ask CK facelift: rename, sidebar multi-tool sections, 1–6 display renumber, `goToPanel`/`PANEL_META` navigation  
- LLM Configure panel relocation + dead-code cleanup (`showLLMConfig`, `#llmCredential`, `#llm-config-card`)  
- New tool scaffolds: 7 placeholder panels + 3 router stubs; PyTest Creator Cases wired (isolated selection)  
- Nav-badge scoping to Generator  
- Docs repathed: root README, this file, SERVER-README, LESSONS, READMEs, BoS/EoS prompts, SESSION_STATE entry

---

## 10. Cross-References

- Root `README.md` — project framing; Ask CK summary  
- Root `SESSION_STATE.md` — broader history (2026-07-13 entries)  
- `OBJECTIVE_DRAFTING_PROCESS.md` (this directory) — process source of truth  
- `ask-ck/ck-facelift/PLAN-facelift.md` — facelift plan as executed  
- External `AGENTS.md` — machine/CLI environment if present  

---

## 11. Session Handoff Checklist

When starting a new session:
- [ ] Read `ask-ck/objective-drafting/PROGRESS.md` (this file)
- [ ] Read `ask-ck/CK-main/SERVER-README.md`
- [ ] Skim `ask-ck/objective-drafting/LESSONS_LEARNED.md` (2026-07-13)
- [ ] Run `./ask-ck/CK-main/run.sh`; hard-refresh browser
- [ ] Confirm Ask CK sidebar: LLM Configure + 4 tool sections; Generator "1. Cases" active
- [ ] Apply LLM once (Configure panel); switch cases — status must stick
- [ ] Load open case → Search/Suggest steps 2–4 → confirms → synthesize (5/6) → check Gaps in traceability → export
- [ ] PyTest Creator case selection does NOT change the Generator's loaded case
- [ ] Review steps have **no** gaps textarea
- [ ] At end: update PROGRESS + LESSONS + SERVER-README; append root SESSION_STATE if impactful

---

**This file is the primary handoff document.** Keep it updated after every significant session.

# PLAN — End-to-end pipeline repair: from "no objective" to "a test actually ran"

> ## Status (read first)
>
> **Status:** ACTIVE. Written 2026-08-03 from a 12-stage adversarially-verified audit —
> 27 agents, **284 findings, 206 CONFIRMED, 77 PARTLY, 1 unverified, 0 refuted.**
>
> | | |
> |---|---|
> | **Phase −1.1 – −1.4** | ✅ **DONE** 2026-08-03 (`949004f`, `0743889`). 28 tests, 9 mutations all caught. |
> | **Phase −1.5, −1.6** | Deferred with reasons recorded in Phase −1. |
> | **Phase −1.7** (43 live cases) | Decided: re-push, stay at v2.0. Executes after Phases 1–4. |
> | **Parser fix** (the recommended deviation) | ✅ **DONE** 2026-08-03c (`f0a94af`). `CK_server/gen_assembly.py`; all five stored replies recover COMPLETELY. |
> | **Phase 2.1 – 2.3** | ✅ **DONE** 2026-08-03c (`f0a94af`); prompt **reviewed and signed off 2026-08-05**, plus generation-time compliance reporting (see below). **2.4 (regenerate 53) NOT done** — no longer blocked on a review, but still needs the go-ahead to spend the tokens. |
> | **Phase 7.1, 7.4, 7.5, 7.7, 7.9** | ✅ **DONE** 2026-08-03c (`f0a94af`, `5f4af0a`, `81c9c94`). |
> | **Phase 7.6** (chunked generation) | ❌ **WITHDRAWN.** Measured 67,326 output tokens in one call — see below. |
> | **Phase 11.0** | ✅ **DONE** 2026-08-03c (`f0a94af`). Verified by mutation. **Unproven on hardware.** |
> | **Phase 11.1, 11.2** (log parsing) | ✅ **DONE** 2026-08-03c (`86c062a`). Real captured fixtures, credentials redacted. |
> | **Phase 7.8** (generate-prompt contradictions) | ✅ **Rule 3 DONE** 2026-08-04 (`9c1a553`) — it was producing the only lint error that has ever fired. Rules 1/8, the untrimmed device list and the on-code FILL markers remain. |
> | **Phase 4** (CLI grounding) | ✅ **DONE 2026-08-04** — all of 4.1–4.6, read-time in `tool/cli_lookup.py` (`ck.db` untouched). Over the 53 refined cases: zero-detection **15 → 10**, commands-but-no-output **19 → 0**, real output/usage **19 → 43**; 5 cases fixed, 0 regressed. Both verification targets pass. 40 tests, 11 mutations all caught. **4.4 deviates** — `tables` cannot replace the speed-forms prose, only one false sentence in it; see `DECISIONS-FOR-REVIEW.md` §13 D-28. |
> | **Phases 0, 1, 3, 5, 6, 8, 9, 10, 12** | Not started. |
> | **Phase 11.3 – 11.5** | Not started. 11.4 needs hardware. |
>
> ### 2026-08-04 — decisions reviewed with Terrence; six changed
>
> The autonomous run's judgement calls were reviewed as a blind experiment (12 presented as
> neutral questions; **5 matched**, and of the 7 that differed **4 landed on an option neither
> of us picked**). Everything is recorded in
> [`DECISIONS-FOR-REVIEW.md`](DECISIONS-FOR-REVIEW.md) §9–12. What changed in the plan's terms:
>
> - **Phase 7.7's no-override rule was too strict and is now split by authority.** 14 lint
>   errors block with no override; 5 are house rules a reviewer may accept with a recorded
>   reason. The trigger: the only error ever to fire on a real generation was a house rule, on
>   our best script, **earned by following our own prompt** — so 7.8's rule-3 fix landed first.
> - **A refusal must not destroy the evidence.** The 502 fired before `sess.step6` was written,
>   re-creating Phase 7.9's defect one layer up. Attempts now persist to
>   `step6.failed_generations` before refusing.
> - **Phase 11.1's scope is capped.** Run results owe four things and no more — consistent,
>   readable, formatted for automation, no gaps. Expected-UNSUPPORTED sets, drift states and
>   provisional flags were built and then **deleted as scope creep**: judging what a run *means*
>   is Test Composer's job. `results_complete` states whether the results are trustworthy, which
>   is deliberately not "the test passed".
> - **Two claims from 2026-08-03c are withdrawn:** `x230v2` as a capability anchor (it is a lossy
>   framework label over the device's real `AT-x230-18GT V2`), and "UNSUPPORTED is a
>   deterministic property of (case × platform)" — only 1 of 4 real cases is a platform
>   capability; three are bench state (`No USB media present`).
>
> ### 2026-08-05 — both pre-2.4 reviews are DONE; Phase 2.4 is unblocked
>
> The two items held open above ("still unreviewed, and worth doing before Phase 2.4") were
> reviewed with Terrence and are now closed.
>
> - **The lint authority split STANDS AS WRITTEN — 14 blocking / 5 policy, no
>   reclassification.** All 19 errors were re-read against the rule that defines the split
>   ("does the reviewer's judgement help?"). Three were argued for change and all three were
>   declined: moving the no-verdict contract error to blocking; softening
>   `coverage/completeness check could not run` (it punishes OUR defect, not the artefact);
>   and softening the `framework_surface` import miss (it blocks against an index `ck.db`
>   can never rebuild). Fail-closed was preferred in each case. **Do not re-raise these
>   without new evidence — they are settled, not unexamined.** The enumeration in
>   `tests/test_lint_error_classes.py` remains the authority, and still fails on any
>   unclassified new error.
> - **The steps prompt text is SIGNED OFF**, with one wording fix and one real defect found
>   behind it. Every rule was checked against the code: the "first step is injected
>   server-side" claim is true (`llm.py:build_traceability_note`), the topology rule names
>   roles rather than devices, and all four context fields it renders are really built by
>   `_synthesis_context`. Fixed: the measurement rule demanded the read in the *description*
>   while two of the three examples put it in `expectedResult` — and per
>   `prompt-examples-are-the-spec` the model follows the example, so the rule as worded could
>   not hold. It now permits either field.
>
> **The defect the review found — the new expectedResult rule had NO enforcement at
> generation** (fixed 2026-08-05). `parse_llm_to_structured`'s numbered-list fallback sets
> `expectedResult` to `""` for every step unconditionally, and returned them
> indistinguishably from a compliant JSON parse; `validate_zephyr_payload` never reads
> `expectedResult` at all. The only gate was `upload_refined.validate_for_push`, a pipeline
> stage later — so the way to discover a blank regeneration was to push it, and a reply that
> ignored the requested format was indistinguishable from a model that simply did not comply.
> Verified by running the real parser, not by reading it. Now `parse_llm_to_structured`
> reports `steps_source` (`json` / `numbered_list` / `none`), `steps_compliance()` audits
> blanks excluding the injected note, and `synthesize_steps` returns `steps_quality` and
> persists it in provenance — so Phase 2.4 can be audited per case as it runs. Deliberately
> **advisory**: `validate_zephyr_payload` is the shared push gate and its verdict is
> unchanged, pinned by a test. 12 tests, 9 mutations all caught. Gate 1006 → 1018.
>
> **Phase 2.4 is no longer blocked on a review.** It still needs the explicit go-ahead to
> spend the tokens.
>
> ### 2026-08-03c — what changed in the plan itself
>
> **Phase 7.6 is withdrawn, and Phase 7.4 was more wrong than recorded.** The gate's premise —
> that the CLI's 32,000 `maxOutputTokens` bounds the answer — is false. Measured `output_tokens`
> on the stored multi-message generations: **67,326 / 66,334 / 57,188 / 34,966**, every one over
> the "hard cap" and every one a complete script. 32,000 bounds a *message*. So the blocking
> gate is deleted rather than recalibrated, and `acknowledge_size_overflow` went with it (it had
> no caller and was unreachable).
>
> **Phase 7.1 as written is wrong and was implemented differently.** It says "capture
> `stop_reason` and raise". Captured live against CLI 2.1.207, `stop_reason` is **null on every
> genuine assistant message, including ones that hit the cap**; the only truthy value is on a
> message the CLI synthesizes, and it reads `stop_sequence`. Detection reads the `result`
> envelope instead. Structural captures are committed at `tests/fixtures/cli_stream_*.jsonl`.
>
> **The first parser fix was wrong in seven ways and an adversarial reviewer caught all of them.**
> It silently deleted real code — including the `ts = TestSuite(...)` every framework script
> depends on — while reporting a clean recovery. Rewritten so each rule is decided by evidence:
> seam repair picks the reading that parses and drops least, unit spans stop at the next column-0
> statement, duplicates resolve on AST richness rather than character count, and a block after
> the runner is commentary. **Every judgement call is recorded in
> [`DECISIONS-FOR-REVIEW.md`](DECISIONS-FOR-REVIEW.md) for Terrence to overturn.**
>
> **Still not walked through with Terrence:** Stations 14 (preflight) and 16 (judging).
>
> **Two things happened after the first draft that change the order** — both reproduced
> independently before being written down:
> 1. **The output ceiling does not exist** (see below). Phase 7 is rewritten; chunked generation,
>    the largest item in this plan, is withdrawn.
> 2. **Phase 11.0** — a `ContextVar` lock defect, not the bench, is why nothing has ever executed.
>
> **Recommended deviation from strict pipeline order:** fix `_parse_generated_blocks` first.
> Every measurement in Phases 7–9 is calibrated against its output, so re-fitting a constant
> before that lands is wasted work. Phase 2 (`generate_steps.jinja`) is also now a hard blocker
> on re-enabling the push, rather than a successor to Phase −1.
>
> **Not yet walked through with Terrence:** Stations 14 (preflight) and 16 (judging).
>
> **Why this plan exists.** Terrence, 2026-08-03: *"I want to fix these issues in order from
> beginning (no objectives is never ok) to the end (we never executed ANY test cases, over
> multiple sessions). Leave no stone unturned. We can take as long as we need to fix this, but
> it needs fixing."*
>
> **Both endpoints are literally true in the data, not impressions:**
> - **324 of 410 AWPTCM target cases have no objective** (+4 junk, +2 Japanese — only **80
>   usable English, 20%**). 305 have no objective, no steps, no script text, no refs.
> - **`step7.runs` is empty for every PyTest session that has ever existed.** Six sessions, four
>   with a generated script, **zero hardware runs recorded, ever.**
>
> **The structural diagnosis — read this before any individual fix.** The pipeline is four
> stacked LLM layers — objective → refined steps → sequence → script — where **every gate
> measures consistency with the previous LLM layer** and the top gate is shape-only. The
> external anchors that do exist (real CLI sample output, real reused fragments) were both
> measured during this audit and **both are substantially inert**: CLI grounding fires for only
> 19 of 53 cases because command names are de-hyphenated in `ck.db`, and the provenance tag that
> "proves" fragment reuse has **0.000 code overlap** with the cited source on all six TestCases
> of the flagship script. So there is currently **no working anchor anywhere in the chain.**
> That is why the artefacts grade well and nothing has ever run.
>
> **Audit status: COMPLETE.** All 12 stages audited — **284 findings** — each adversarially
> verified by an independent agent instructed to refute it: **179 CONFIRMED, 47 PARTLY,
> 0 REFUTED**, plus **57 the auditors missed entirely**. 17 findings are execution-blocking.
> The verifiers for stages I and K, and the three completeness critics, were lost to a session
> limit on the first run and re-run on resume.
>
> **The headline is Phase 11.0, and it was not what anyone expected.** The reason no test case has
> ever executed is not the stack demand (D13) and not the bench: `RunManager._run` is a
> `threading.Thread` whose lock holder comes from a **`ContextVar` a new thread does not
> inherit**, so **every browser-initiated run raises `LockConflictError` before SSH is
> attempted** — and reports it as *"SSH connect failed"*. Reproduced offline with the real
> `locks` module. The other route to the bench, `pt_autopilot`, has no hardware phase at all.
>
> Zero refutations across 226 verified claims is a strong signal, but **the 47 PARTLY corrections
> matter** — several changed the work, not just the wording, and each is recorded inline in the
> phase it affects rather than in a separate list.
>
> **THE OUTPUT CEILING DOES NOT EXIST.** This is the largest correction in the audit, it was
> found by two independent completeness critics, and I reproduced it end to end before writing
> it down. Replaying the five stored replies in `debug-log/no-session.jsonl` through the real
> `_parse_generated_blocks` regex ([pytest_create.py:883]):
>
> | reply | model emitted | parser kept | `ts.run(sys.argv)` present |
> |---|---|---|---|
> | 06:47:37 | 173,351 chars / **42 classes** | 86,656 / 21 | yes |
> | 07:00:16 | 96,070 / 17 | 88,602 / 16 | yes |
> | 07:25:59 | 48,702 / 12 | 42,331 / 9 | yes |
> | 07:48:13 | 37,674 / 6 | 37,661 / 6 | yes |
> | 07:56:58 (the "D15 regression") | 49,546 / 6 | 25,171 / **0** | yes |
>
> **Every reply is complete.** The CLI splits long answers across assistant messages, each
> re-opening a ```` ```python ```` fence, and the non-greedy `(.*?)``` ` stops at the
> *continuation's opening* fence — discarding everything after part 1, usually mid-token, which
> is exactly what "truncation" looked like. Verified seam at offset 25,181 of the 07:56:58
> reply: it cuts inside `self.log('LLDP transmit interval in effect: {}` and the next part
> re-emits that line. The model **labels each part** (`# ---- continuation … part 2: TestCase_21
> onwards ----`) and closes with plain-English assembly instructions naming which duplicate to
> discard — and the parser throws those away too.
>
> The parser-kept figures are, to the character, the numbers in
> `FINDINGS-generation-size-ceiling.md` and `RESULTS-2026-08-03.md`. **Those documents measured
> parser output and called it model output**, and every decision downstream inherits it.
>
> What this invalidates: the ~9–20 class ceiling (42 arrived in one call); `_size_overflow`'s
> three constants, whose docstring claims "ALL THREE CONSTANTS ARE MEASURED"; **chunked
> generation, the single largest item in this plan, costed XL**; and D15's diagnosis. It does
> not invalidate the transport findings — the installed CLI (v2.1.207, verified) does expose
> `--effort`, `--session-id`, `--resume` and `--fork-session` that `llm.py` never passes, and
> the CLI transport still discards the `stop_reason` both HTTP backends act on. Those become
> small optimisations rather than the headline. See Phase 7, now rewritten.
>
> Recovery is **not** uniform, and the plan must budget for that: a naive strip-and-join fixes
> 07:00:16 only; line-level de-duplication of the re-emitted partial line additionally fixes
> 07:56:58; the four-part 06:47:37 reply re-emits a whole partial **class**, so assembly has to
> work at class granularity. S/M, not the ~20 lines a first read suggests — and not XL.
>
> **Ordering.** Strict pipeline order as asked, with **one exception taken out of order and
> justified in Phase −1** — it can damage production data outside this repo.

---

## Phase −1 — The Zephyr push (out of order, deliberately)

> **CORRECTION — the audit's framing of this was stale, and I checked before acting.**
> Stage C described "a single unauthenticated POST performs a real production write". The
> *network* half of that was **already fixed on 2026-07-27g** and is pinned by
> `tests/test_security_hardening_batch_e.py`:
> - `run.sh` and `main.py` both default to **`127.0.0.1`** (loopback), test-pinned.
> - `--force` is **no longer hardcoded** — opt-in, defaults `False`, and the UI does not send
>   it, so `upload_refined.py`'s "already appears refined in Zephyr — SKIP" guard is live.
> - `dry_run` defaults `True`, test-pinned.
>
> So this is **not** a "one curl from the internet" problem. What is real and unaddressed is
> the *content*: **the push performs no validation whatsoever**, and the push path has three
> concrete defects. That is still worth fixing first — the bundle it would write is, per
> Phase 3, 95% missing expected results, machine-reviewed with no record of it, and in one
> measured case (T33304) targets the wrong command family for a real capability (see Phase 3).

**What is actually wrong (all verified directly):**

1. **No validation before a live write.** `tool/upload_refined.py` never imports
   `validate_zephyr_payload`. It pushes whatever JSON is on disk.
2. **A silent escape-repair.** [upload_refined.py:76-80] catches a JSON parse failure and
   retries with `raw.replace("\\'", "'").replace("\\ ", " ")`. A malformed bundle is repaired
   in memory and pushed with no warning.
3. **Every Zephyr web link is silently dropped.** [upload_refined.py:225] searches for
   `## Zephyr Cross-References (Step 3)`; the template emits
   `## Zephyr Cross-References (Step 2)` ([traceability.md.jinja:23]). The regex never matches,
   `_zephyr_links` returns `[]`, and step 4 of the advertised push does nothing — **96 links
   across 12 bundles**. The push reports success.
4. **Empty expected results go straight through.** [upload_refined.py:124] passes
   `expectedResult` verbatim, so 615 of 645 steps would reach Zephyr blank.
5. `dry_run` as a query parameter is one character from an execute. Low risk on loopback, but
   free to harden.

**Fixes — STATUS: −1.1 to −1.4 BUILT 2026-08-03. −1.5 and −1.6 deferred, see below.**

New suite: `tests/test_zephyr_push_validation.py` (25 tests). **Seven mutation checks run, all
seven caught** — the first pass left one asleep (an audit-log failure no longer blocking the
push was invisible, because nothing exercised the `--execute` path) and that gap is now covered.

**−1.1 DONE.** `upload_refined.py` now validates every payload before it can reach a live case.
The shape rules are **imported** from `CK_server/llm.py:validate_zephyr_payload` rather than
restated — a second copy would drift, and the drift would only surface as bad data in Zephyr.
The import is lazy and **fails closed**: if the server module cannot be loaded the case is
refused, never passed. Added the content rule: **every non-note step must carry an
`expectedResult`**. Validation runs in `--dry-run` too, so the preview reports what would be
refused. `--skip-validation` is the deliberate override, off by default.

> **Correction to this plan's own number.** It said the rule "blocks 43 of 53". Measured against
> the real corpus with the real code: **it blocks 53 of 53.** The 43 figure was the count of
> cases with *no* expected results anywhere; every one of the remaining 10 has *at least one*
> blank step, and the rule is per-step. 3 cases also fail the server's traceability-note rule
> (T33243, T33246, T33234). A gate that refuses 100% of the current corpus is the honest
> reading of it — Phases 1–4 are what change that, not a weaker gate.

**−1.2 DONE.** `load_payload` returns a third value, `repairs`. The escape-repair still happens
(it is tolerant of pre-existing authoring damage and never writes to disk) but it is reported
per case, and it is added to the blocking issues so a repaired payload cannot be `--execute`d
without `--skip-validation`. **No bundle currently needs repair (0 of 53)**, so this is a latent
path; it is covered synthetically in the suite rather than by the corpus.

**−1.3 DONE.** The parser accepts `(Step 2|3)`, mirroring `parse_atpylib_links`, which had
already been fixed for exactly this drift and never carried across. Pinned three ways: render
the real template and parse it with the real parser; both headings parse in isolation; and a
regression floor on the committed corpus.

> **Measured before and after.** Before: **1 bundle, 2 links** — the single hand-written bundle
> that happened to use the parser's spelling. After: **12 bundles, 86 links.** (This plan
> previously said 96; 86 is the counted figure.)

**−1.4 DONE, with one deliberate deviation.** A real push now requires `{"confirm": "<case key>"}`
in the request body, and the token must equal the case key — so no single edit to a URL turns a
preview into a production write. Every `--execute` writes a `push.intent` record to
`ask-ck/var/zephyr-push-audit.jsonl` **before the first network call** (who, when, key, argv,
pre-push state, and what it intends to change), and a `push.outcome` after; **a case whose audit
record cannot be written is refused.** `ask-ck/var/*` is gitignored, which is correct — the log
records production writes and can quote case content. A blocked case now makes the process exit
non-zero, so the UI cannot report a refused push as success.

> **Deviation:** this plan said "move `dry_run` into the request body". It stays a query
> parameter. `tests/test_security_hardening_batch_e.py` deliberately pins
> `dry_run` default `True` and `force` default `False` **as signature parameters** — a reviewed
> 2026-07-27g safety decision. Moving them would have broken those assertions to buy nothing:
> the exposure was never the transport, it was that no *second* fact was required. The
> confirmation token supplies that. All 14 of those tests still pass unchanged.

**−1.7 NEW, and it needs your decision — 43 cases are ALREADY live in production Zephyr.**

Raised by a completeness critic, verified directly:
`6f254e7 2026-07-22 generator: Push-to-Zephyr button + title-cleanup + v2.0 versioning;
all 43 cases pushed`. This plan treated the push purely as a *future* risk and never asked what
had already gone out. What is already out there:

- **43 AWPTCM cases at version 2.0**, in the company QA record, outside this repo and outside
  git — every one produced by the **title-only objective prompt** that is this plan's headline
  defect (Phase 1).
- Each carries an attached `traceability.md` with the defects Phase 3 documents — "Objective:
  No" rendered for cross-references that *do* have objectives, a blank `Folder:` on every line,
  and a provenance sentence citing `data/zephyr_full/`.
- **No record of which 43, what payload, or when.** `ask-ck/var/zephyr-push-audit.jsonl` does
  not exist on disk — confirmed. The audit log arrived with −1.4, five weeks late. The only
  reconstruction available is git history plus whatever Zephyr's own version log retained.

This forces a call that has to be made **before** regeneration, not after, because it decides
whether the regenerated bundles are additive or corrective:

**DECIDED (2026-08-03): re-push the 43, and keep them at v2.0.** No v3.0.

The tooling already does exactly this and needs no change to honour it: `TARGET_MAJOR_VERSION
= 2` and `create_new_version` returns `{"action": "skipped"}` for any case already at v2.0 or
beyond, so `--new-version` is a no-op there and the payload updates v2.0 in place. Re-running is
capped by construction; it can never produce 3.0.

Two consequences follow:

1. **Zephyr keeps no version history of these pushes — so the local audit log does.**
   > *"I don't want a snapshot, I want a working copy. no version control required."*
   > — Terrence, 2026-08-03, **scoped to Zephyr.** In Zephyr: stay at v2.0, overwrite in
   > place, no v3.0 and no version trail. That is settled.
   >
   > It does **not** extend to the local record, and reading it that way was my error — I
   > briefly stripped the content capture out on the strength of it. The Zephyr decision is
   > in fact the reason to keep a local copy: with no version trail upstream, a re-push that
   > writes a worse objective over a better one is otherwise unrecoverable.

   *Built:* `push.intent` captures the full prior `objective`, `testScript` and `name`, and a
   `push.version` record states whether the write landed in place — **observed** from
   `create_new_version`'s reported action, not inferred.
   > A first cut inferred "in place" from `status == "refined"`, the does-this-look-refined
   > heuristic. A test with a small live case (63-char objective, 1 step → `partial`) caught
   > it: the heuristic and the version are different questions, and only the version decides
   > whether the old text survives.

   The log stays local and disposable: `ask-ck/var/*` is gitignored, the server never reads
   it, and it is a few hundred KB for all 43.

2. **A re-push needs `--force`.** All 43 classify as `refined`, so the CLI's own "already
   appears refined — SKIP" guard fires on every one. `--force` is opt-in and the UI deliberately
   does not send it (pinned by `test_ui_does_not_send_force`), so the re-push must be a
   deliberate CLI run, not a button. That is the right shape for it — leave the UI as it is.

Sequence: Phases 1–4 → regenerate all 53 → the new validator must pass → then
`--execute --force --new-version --verify` over the 43, in batches, with the audit log retained.

> **Also worth stating plainly:** the gate built in −1.1 now refuses **all 53** bundles, so the
> push is effectively disabled until the `expectedResult` defect is fixed. A critic argues that
> makes Phase 2 a hard *blocker* on Phase −1 rather than a successor to it — otherwise the
> choice is between shipping steps with no pass criteria and shipping nothing. That is correct,
> and it is an argument for pulling the `generate_steps.jinja` fix forward, not for weakening
> the gate.

**−1.5 DEFERRED — blocked on Phase 3.7.** There is no machine-confirmed marker to read yet;
the acknowledgement has nothing to key on. Build it with 3.7.

**−1.6 DEFERRED — belongs with the export path, not the push path.** Re-export overwriting
`traceability.md` with an empty render is a defect in `export()`, and −1.3's regression floor
(≥80 links across the corpus) will now fail loudly if it starts happening. That converts −1.6
from a silent risk into a caught one, which is enough to let it wait for its own phase.

---

## Context

### Two results that redirect the plan

**1. The missing objectives were never in Zephyr.** The audit replayed the surviving 125 MB
export (`raw data/Zephyr-Database-30_Jun_2026.xml`, 45,427 `<testCase>` elements) through the
real `extract_zephyr_xml.parse_testcase` and matched **all 410/410** target keys. No objective
was dropped by the extractor; the only 5 XML-only objectives are this project's own uploads
round-tripped back in. **No re-extraction will recover them.** The cheapest hypothesis is dead —
objectives must be *authored*, grounded in other corpora, and gated.

**2. `ck.db` was built from a stale intermediate, and half a megabyte of real content is
missing.** `meta.built_at = 2026-07-20T01:16`, from a `zephyr_cases.jsonl` generated
**2026-07-15 13:37**. Four extractor fixes never reached the permanent DB:

> **CORRECTION — this plan had the timeline backwards, and the verifier caught it.**
> An earlier draft said `tool/extract_zephyr_xml.py` was fixed "five hours and forty-seven
> minutes *after* the build", implying a race. It is the opposite. `build_db.py:506` writes
> `built_at` with `datetime.utcnow()`, so `2026-07-20T01:16:07` is **UTC** = **13:16 local**.
> The extractor was fixed at **07:03:44 +1200** — **6h12m before** the build. Decisive
> cross-check: `meta.src_mtime:scripts_index.json` = **13:12:30 local**, 3m37s before
> `built_at`; were `built_at` local, the build would predate its own input by twelve hours.
>
> So the correct story is worse than a race: **the fix already existed, and the build simply
> re-used a five-day-old intermediate instead of re-running it.** No timing accident to
> excuse it, and nothing about the permanence invariant caused it.

| Content | In ck.db |
|---|---|
| PLAIN script bodies | **0** (1,298 cases, 556,013 chars missing) |
| Per-step `testData` | **0** (3,440 fields missing) |
| Issue links | **0** (480 missing) |
| Attachment lists | **0** (250 missing) |

`schema.sql:195-199` asserts `script_text` and `refs_text` are indexed recovered content. **Both
columns are empty in all 45,427 rows.** Two of `zephyr_fts`'s seven indexed columns are dead
weight reading as live capability.

> **Correction to a widely-held assumption.** The audit checked `tool/guard_db_only.py` directly:
> it forbids exactly four shapes, **all of them runtime *reads* of retired corpus JSON**. It says
> nothing about writing or extending `ck.db`. **The permanence invariant does not block a fix
> here.** The genuine risk is the opposite — there is no migration discipline, so an ad-hoc
> in-place mutation would be unversioned and unreviewable. Phase 0 establishes that discipline
> before anything uses it.

### The two anchors that were supposed to work, and don't

**CLI grounding is inert for most cases.** `ck.db` stores command names **with hyphens
stripped**, taken from doc-page slugs: `show spanningtree` where the syntax column itself holds
`show spanning-tree [interface <port-list>]`. Measured: **~591 of 3,297 distinct command names (18%, a conservative floor — the exact count depends on the detection heuristic) are
de-hyphenated.** `detect_commands` matches literal names, so correctly-spelled AlliedWare Plus
text never matches. Consequences:

- The RSTP case T33277 writes "spanning-tree" three times and gets `detect_commands → []` —
  **zero CLI grounding** — while `show spanningtree` sits in `ck.db` with 2,388 chars of real
  sample output.
- Replayed across all 53 refined cases: **only 19 receive any real CLI sample output at step 2;
  15 receive none at all.** For 34 of 53 the model writes verifies for output it has never been
  shown, while the prompt tells it the injected block is "authoritative; match these formats
  exactly".
- This, not model quality, is the mechanism behind memory `cli-fabrication-originates-step2`.
- Separately, `detect_commands` **abandons a command entirely when its first occurrence sits
  inside a longer match**, so grounding depends on sentence order.
- `cli_commands.tables` — **5,368 rows of documented per-media argument matrices** — is read by
  no prompt, while `pt_extract_sequence.jinja` spends 18 hand-written lines teaching the three
  `speed` forms.

**Fragment reuse is not proven, and the grader cannot tell.** On T44297 — the one script the
batch delivered clean — all six `main()` bodies carry a server-stamped
`# ART …/library_1332.py lines a-b` provenance tag, and the **normalised code overlap with the
cited fragment is 0.000 for all six.** The stamp is built purely from `maps_to`
([pytest_create.py:994-1017]) and never from the emitted code: **it proves a fragment was
*offered* for a step, not that its code was used.** TestCase_2 is stamped to `log_packet`, a
six-line `sys.stdout` helper, while its body invents `ts._ck_capture_lldpdus`.

And `pt_grade`'s C2 "snippets used: EXACTLY" **recomputes the expected tag from the same
`maps_to` the server stamped from**, using the same helper — it *measures the stamper against
the stamper*, and explicitly refuses to let code overlap downgrade the verdict. **The clean
sweep reported on 2026-08-03 is, for C2, a tautology.**

### Key verified facts by stage

**Source (410 targets):** 324 no objective / 4 junk / 2 Japanese / 80 usable. **322 report
`num_steps>0` with every step a blank placeholder.** `has_objective` is `1 if obj.strip() else 0`
([build_db.py:127,161]) so `'l'` counts — and both flags are **rendered into LLM-visible prompt
text** as `Has objective: True | Num steps: 1`. CJK is far wider than the 2 known cases: **850
Zephyr objectives, 477 TestLink summaries, 592 TestLink preconditions** — 1,169 rows unreachable
by FTS and noise to the English-only embedder. The ART enrichment loss recorded in 2026-06 is
still present: **~2,100 automated tests missing** (suite 1354: 1,623 reported, 426 enriched).

**Objective drafting:** `_synthesis_context` ([llm.py:1017-1029]) returns exactly
`{case_key, primary, testlink_selections, zephyr_selections, atp_selections, gaps, art_string}` —
**nothing from the case's own row.** 86 targets do have an objective and 32 a precondition; both
are ignored. T43870's precondition is **1,665 chars of real AlliedWare Plus config** the drafter
never sees. The prompt transmits **titles only — ~6% of the evidence the confirmed selections
point at** — and the rich description **is already persisted on `Selection.justification`** and
**is rendered by the ATP-suggestion prompt**, just not by the objective prompt. Retrieval is
title-guessing too: every corpus query is built from the case title plus a rationale, never the
body. `synthesize_objectives` **never validates**, and the UI never checks `provenance.error`, so
**a failed objective call renders as success**. Neither wizard LLM call passes `max_tokens`, so
api_key backends cap at **2,000**.

**Refined cases:** **615 of 645 verification steps (95%) have no `expectedResult`; 43 of 53 cases
have none at all.** Root cause is the prompt: `generate_steps.jinja:15` says *"expectedResult
usually empty or brief"* and its only example is `"expectedResult": ""`. Steps are largely a
**grammatical transposition of the objective bullets** — no test data, no measurement method, no
topology. Where objectives *are* good they are genuinely traceable to reviewer-selected evidence
(AWP-15157's snmpd.conf access-list defect becomes objective bullet 11; ART 2031.10.2 becomes
RSTP step 19) — **the drafting is not filler, it is under-resourced.** One measured fabrication:
**T33304's headline bullet and four steps are written against `vlan classifier rule ... mac`,
a form that does not exist** — the only forms are `ipv4` and `proto`.

> **Corrected by the verifier, and I had overstated it.** AlliedWare Plus *does* have MAC-based
> VLAN assignment — `platform mac-vlan-hashing-algorithm` exists and its overview names the
> **Multiple Dynamic VLAN** feature, and `MAC VLAN` is a real Pre-Ingress classifier resource in
> `show platform classifier statistics`. So the objective describes a **real capability via the
> wrong command family**, not an impossible one. Less damning than "fabricated" — but a test
> written against the non-existent rule form still fails on the box, and Stage C has zero CLI
> grounding to catch it. That is the defect.

**Validation and export:** `validate_zephyr_payload` ([llm.py:870-929]) is five shape rules.
**Its sole `warnings.append` cannot fire for an AWPTCM key — "zero warnings" is vacuous.** A
review step can be **confirmed with zero selections**. Export **never checks `step4.confirmed`**,
so an unreviewed objective ships as Complete in three POSTs. The `stale` marker is written and
displayed but **read by no gate**. Re-exporting a backfilled Complete case **overwrites its
`traceability.md` with an empty render** — destroying the file `upload_refined.py` parses its
links out of. `push_to_zephyr` **never attaches Zephyr web links at all** (the parser looks for a
heading the template does not emit — 96 links across 12 bundles). `upload_refined.py` pushes
whatever JSON is on disk **with no validation** and a silent escape-repair. Only **12 of 53**
refined dirs carry a session record, so 41 Complete cases have no provenance. Re-running
overwrites in place — **no diff, no history**. And the ten 2026-08-03 cases' three "human review
gates" were satisfied by **the machine accepting its own suggestions**, which the bundle does not
record.

**Sequence extraction:** **T33304's real root cause is now known, and it is not what the docs
say.** The model returned 30,183 chars with **53 sequence entries, 52 parsing cleanly, covering
33 of 34 Zephyr steps, zero fabricated tokens.** One entry contained a JavaScript ternary
(`"zephyr_step_idx": 44 > 0 ? 23 : 23`) which broke the outer object; `extract_json_block` then
**silently returned the first array element** as `parsed`; `_parsed_list` found no `sequence`
key; the router answered `502 "LLM returned no sequence"`. **221 seconds and $0.36 of Opus
discarded, reported as a hard failure.** Worse: because the recovered object is not `None`, this
**re-opens D8** — `gather_fragments`'s guard only catches `parsed is None`, so a tail-truncated
reply (exactly what the 32k ceiling produces) parses into an inner object and **silently records
zero fragments** again. And the 502's promise *"Raw response stored in provenance"* is **false** —
provenance is written ten lines *after* the raise. There is **no temperature or seed on the
transport actually used**; the same case yields 44–50 steps run to run and **flips the coverage
gate**. `extract_sequence` passes **no `max_tokens`** (2,000 cap on api_key). Nothing validates a
sequence entry's shape or `kind` vocabulary — an out-of-vocabulary kind **silently degrades a
physical step** into an ordinary CLI TestCase, discarding the operator prompt, which is exactly
what memory `physical-interaction-steps` forbids.

**Fragments:** the D1 resolver hardening is **genuinely correct** (0 of 6,193 corpus symbols
resolve to a bad head line) and fissix is live (95 of 6,193 translated, 0 unavailable). But: the
fragment pool is **append-only**, so a re-gather never drops fragments whose source script the
reviewer de-selected — **13 of 18 selected fragments in T33233 are orphans**. Fragments mapped
only to *setup* steps have no destination and are dropped from preview, stamping and grading —
**7 of 13 in T44297**, 54% of the approved reuse, invisible but still consuming prompt budget.
`code[:8000]` **cuts mid-token** while the tag still claims the full line range (218 of 6,193).
A duplicate top-level helper resolves to the **first definition — the one Python never
executes** (21 scripts). `loc[0]` is the `def` line, so **decorators are cut out**. For the 146
py2/unparseable scripts the index has **no end line and no helpers**, so a "fragment" runs to the
next top-level class — 96 slices carry module-level code. **`scripts_fts`, `vec_scripts`,
`chunks_fts` and `vec_chunks` are all built, shipped and unread** — selection is a hand-weighted
bag-of-words scan over title/summary/tags/directory. **Nothing anywhere asks whether a fragment's
source script still works**, and the majority are `legacy`. `confirm_step` **never requires the
previous step to be confirmed**, so Fragments can be signed off while Script Search is not —
live in T33235.

**Generation / size gate:** zero test coverage. The gate reserves **2,048** tokens for thinking
against a **measured ~20,400**. **False-negative regime, computed: it refuses above ~18 TestCase
classes but a high-thinking run fits only ~7 — anything between 7 and 18 silently truncates.**
And it runs at Generate, **three paid LLM steps after the step count that triggers it is known**.

**Skeleton:** **D13 root cause confirmed twice, independently.** `stacks` is a **regex over a
text blob** of sequence text plus fragment code ([pytest_create.py:1247]) with no usage check and
no cap — **234 of 6,193 corpus symbols would force `init_stk('stk_a')`**. One line above,
`switches` is derived from devices the fragments actually reference and capped at two.

**Fix loop:** `fix_script` assigns → invalidates → lints → **persists**, so the regression is the
session's copy before anyone can object. It also **re-stamps authoritative reuse tags onto
whatever the fix pass returned**, so a D15 regression ships looking like verified reuse.

**Preflight:** the verdict is **binary** ([pt_preflight.py:514]); D14 needs a third state.

**Run:** `parse_framework_log` returns `cases: [], numPassed: 0, numFailed: 0` for a run that
never started — and `_ck_bind_link` correctly aborting on a bench problem produces exactly that,
so **"this bench cannot host this test" reads as "0 failures"**. `pt_autopilot` has **no hardware
phase**.

**Judging:** **C4 and C5 have never been graded.** C2 is the tautology above.

**Test coverage — the shape of the whole problem:**

| Prompt | Test files |
|---|---|
| `pt_generate_script.jinja` | 4 |
| `pt_extract_sequence.jinja` | 3 |
| `pt_fix_script.jinja` | 1 |
| **all six drafting prompts** | **0** |

Also untested: `_size_overflow`; `gather_fragments` (both D8 branches); `_resolve_symbol_code` /
`_resolve_end` / `_unit_starts` (the D1 hardening — the "27 adversarial checks" were never
committed); `_coverage_gate_error`; `_parsed_list`; `_step_kind`. The timeout/`max_tokens` AST
invariant **scans only `pytest_create.py`**, so both wizard call sites are structurally exempt.

**Dead entry points still documented as live:** `pt_assess_fit.jinja` (no code reference),
`tool/build_refined_viewer.py` (both input paths removed), `tool/render_batches.py`
(`data/candidates.json` deleted). `tool/build_script_index.py` and `enrich_script_index.py`
**cannot run on this host** — their source roots do not exist — so every index-level defect above
is frozen into `ck.db` and must be worked around at read time.

### Invariants

1. `ck.db` permanent, built once, shipped via LFS. **The guard permits extension; there is no
   migration discipline. Phase 0 creates one.**
2. Server reads corpora only from `ck.db`. Guard: `tool/guard_db_only.py`.
3. `/home/st-art/framework` read-only. Guard: `tool/guard_framework_readonly.py`.
4. The org vLLM is core function; its models are reasoning models.

Gate: `./tool/run_tests.sh` — currently **775 pytest / 92 Vitest, green**.

---

## Walkthrough — how the pipeline fails, station by station

*Read this before the phase list. The phases are organised by what to fix; this is organised by
what happens to a case as it travels. Each station: what it does → what breaks → why → the fix.*

**The shape of it in one paragraph.** A case starts as a title. Four LLM layers turn it into a
script — objective, refined steps, sequence, code. Each layer is gated, but **every gate checks
the layer above it**, and the top gate checks only HTML shape. Two external anchors were built to
break that circularity — real CLI sample output, and reuse of real framework code — and **both
measure as inert**. So nothing in the chain is tied to reality until the script reaches hardware,
and no script ever has.

---

### Station 1 — Source data (`ck.db.zephyr_cases`, 410 AWPTCM targets)

- **Does:** holds the manual test case we start from.
- **Breaks:** 324 have **no objective** (+4 junk like `'l'`, +2 Japanese) — only **80 usable**.
  305 have *nothing at all*. 322 report `num_steps>0` where every step is a blank placeholder.
- **Why:** the emptiness is **genuine** — the audit replayed the 125 MB Zephyr export through the
  real parser and matched 410/410 keys; nothing was dropped. But separately, **`ck.db` was built
  from an intermediate 5h47m older than the extractor fixes**, so 1,298 script bodies (556 KB),
  3,440 `testData` fields, 480 issue links and 250 attachments are **zero** — while `schema.sql`
  says they are populated. And `has_objective` is `1 if obj.strip() else 0`, so `'l'` counts.
- **Fix:** Phase 0 — migration discipline, then backfill the four missing outputs; a read-time
  quality classifier; stop reading the two lying columns (they are currently rendered *into the
  prompt* as `Has objective: True`).

### Station 2 — The three corpus reviews (wizard steps 1–3)

- **Does:** reviewer picks supporting TestLink / Zephyr / ATP cases as evidence.
- **Breaks:** a step can be **confirmed with zero selections**. Retrieval queries are built from
  the case *title* plus a rationale, never its body. Step 1's ranking is a **frozen TF-IDF baked
  into `ck.db`** that can never be re-run and covers TestLink only.
- **Why:** `confirm_step` sets `confirmed = True` unconditionally; the three steps load by three
  different mechanisms.
- **Fix:** Phase 1.3 (query from the body) and 1.5 (refuse a zero-selection confirm).

### Station 3 — Objective synthesis (wizard step 4)

- **Does:** writes the objective as an HTML `<ul>` of artefact bullets.
- **Breaks:** **this is the "no objectives is never OK" station.** The prompt receives the case
  key, a ~30-char rationale, and the **titles** of the selections — about **6%** of the evidence
  they point at. It never sees the case's own title, objective, precondition, steps or
  `script_text`. Prompts measure 1,799–3,400 chars of pure titles.
- **Why:** `_synthesis_context` returns seven fields, none sourced from the case row; the prompt
  interpolates `s.title` only. **The rich evidence is already built and shown to the reviewer,
  and already rendered by a sibling prompt — it is discarded at the last hop.** Also:
  `synthesize_objectives` never validates, and the UI never checks `provenance.error`, so **a
  failed call renders as success**.
- **Fix:** Phase 1 — pass the case row and the selection bodies, cite evidence per bullet, gate on
  groundedness.
- **Nuance worth keeping:** where objectives exist they are **genuinely good** and traceable to
  the selected evidence. The drafting is under-resourced, not fraudulent.

### Station 4 — Step synthesis (wizard step 5)

- **Does:** turns objective bullets into verification steps.
- **Breaks:** **615 of 645 steps (95%) have an empty `expectedResult`; 43 of 53 cases have none
  at all.** Steps are largely a grammatical transposition of the objective — no test data, no
  method, no topology.
- **Why:** the prompt says *"expectedResult usually empty or brief"* **and its only example is
  `"expectedResult": ""`**. The model is doing exactly what it was asked. It also receives the
  objective and nothing else — the corpus context is assembled and then not rendered.
- **Fix:** Phase 2 — rewrite the rule *and the example*, render the context, require test data and
  method.
- **Consequence downstream:** a step with no expected result gives sequence extraction only an
  imperative sentence to derive a verdict from. This is the single largest contributor to
  fabrication further down.

### Station 5 — Validation and export

- **Does:** the quality gate before a case is Complete.
- **Breaks:** it is five **shape** rules — `<ul>`, ≥3 `<li>`, note first, ≥2 steps, every step has
  a `description` key. It never looks at `expectedResult`. **Its sole `warnings.append` cannot
  fire for an AWPTCM key**, so "10/10 valid, zero warnings" was *arithmetically guaranteed*.
  Export never checks `step4.confirmed`; the `stale` marker is written, displayed, and **read by
  no gate**; re-export of a backfilled case **overwrites `traceability.md` with an empty render**.
- **Fix:** Phase 3 — content rules that can fail, plus export integrity.
- **Expected result of the fix:** **43 of 53 existing cases should fail.** A green run means the
  gate is broken again.

### Station 6 — Push to Zephyr

- **Does:** writes the refined case back to the system of record.
- **Breaks:** **no validation of any kind**; a silent escape-repair patches malformed JSON in
  memory and pushes it; **every Zephyr web link is silently dropped** (parser looks for
  `(Step 3)`, template emits `(Step 2)` — 96 links across 12 bundles) while reporting success.
- **Why:** `upload_refined.py` never imports the validator.
- **Fix:** Phase −1. *(The "unauthenticated curl" framing was stale — loopback bind, opt-in
  `--force` and default `dry_run` all landed 2026-07-27g and are test-pinned.)*

---
*Handoff to the PyTest Creator. Everything above is now treated as authoritative input.*

---

### Station 7 — Sequence extraction (pt step 2)

- **Does:** turns refined steps into an ordered machine sequence.
- **Breaks:** **T33304's real failure lives here, and it is not what the docs say.** The model
  returned 30,183 chars — **53 entries, 52 parsing cleanly, covering 33 of 34 steps, zero
  fabricated tokens.** One field contained a JavaScript ternary; that broke the outer JSON;
  `extract_json_block` **silently returned the first array element**; the router said *"LLM
  returned no sequence"*. **$0.36 and 221s discarded and logged as a hard failure.**
- **Why:** the extractor falls through to inner openers on an outer parse failure. Because the
  recovered object is not `None`, **this also re-opens D8** — `gather_fragments`'s guard only
  catches `None`, so a tail-truncated reply records **zero fragments** again.
- **Also:** the 502 promises *"raw response stored in provenance"* — provenance is written **ten
  lines after the raise**. No temperature or seed; the same case yields 44–50 steps run to run and
  **flips the coverage gate**.
- **Fix:** Phase 5 — typed parse failures, store the response *before* raising, principled loud
  repair, determinism recording.

### Station 8 — Coverage gate

- **Does:** claims every source step is exercised.
- **Breaks:** it compares an **LLM sequence** against **LLM-generated refined steps**, by matching
  a self-declared integer `zephyr_step_idx`. **It never reads any words.** A sequence semantically
  unrelated to its claimed source passes perfectly.
- **Fix:** Phase 5.3 — anchor it to expected results once Station 4 produces them.

### Station 9 — Script matching and fragment reuse (pt steps 3–5)

- **Does:** finds real framework code to reuse.
- **Breaks:** the **provenance tag proves a fragment was *offered*, not used** — measured
  **0.000 code overlap on all six TestCases** of the flagship script. The pool is **append-only**,
  so de-selected scripts leave orphans (13 of 18 in T33233). Setup-mapped fragments are dropped
  from preview, stamping and grading (7 of 13 in T44297) while still consuming prompt budget.
  `code[:8000]` cuts mid-token while the tag claims the full range. Duplicate helpers resolve to
  the **dead first definition**. Decorators are cut off. `scripts_fts`, `vec_scripts`,
  `chunks_fts` and `vec_chunks` are all **built, shipped and unread**.
- **Why:** the stamp is derived from `maps_to`, never from the emitted code.
- **Fix:** Phase 6 — measure real overlap and stamp `reused`/`adapted`/`not-used`.

### Station 10 — CLI grounding (feeds stations 7 and 11)

- **Does:** the anchor that stops invented CLI output.
- **Breaks:** **`ck.db` stores command names de-hyphenated** from doc-page slugs —
  `show spanningtree` where its own syntax column says `show spanning-tree`. **~591 of 3,297
  commands.** The RSTP case writes "spanning-tree" three times and gets **zero grounding** while
  2,388 chars of real output sit unreachable. Across 53 cases **only 19 get any grounding, 15 get
  none** — and **the flagship prompt's 18,773-char grounding block contained zero sample output**
  while telling the model *"match these formats exactly, character for character"*.
- **Also:** `harvest classify()` requires a literal `awplus` prompt, stranding **404,041 chars** of
  real output in the `syntax` column of 559 rows. `tables` (5,368 rows) and `notes` (6,319) reach
  no prompt.
- **Fix:** Phase 4. **This is the highest-leverage fix in the plan** — pure data normalisation, no
  LLM, and it is the anchor for stations 4, 5, 11 and 14.

### Station 11 — Skeleton render and the size gate (pt step 6a)

- **Does:** renders the authoritative frame and refuses cases too big to generate.
- **Breaks (D13):** `stacks` comes from a **regex over a text blob** of step prose plus fragment
  code — a mention of `stk_a` in a *comment* binds a stack. One line above, `switches` is derived
  from devices the code actually uses and capped at two. **This is what blocked the hardware run.**
- **Breaks (the gate):** it reserves the **per-block** thinking cap (2,048) as if it were the
  total, against a measured **~20,400** — so the false-negative band is **10–15 TestCase
  classes**. `fits` scales the fixed head linearly, over-stating by ~20%. `_FILL_EXPANSION = 1.95`
  is fitted to one case; three others measure **0.96–1.00**. It hardcodes the CLI's cap for every
  backend, fires **before** the `dry_run` branch (so the free preview is refused exactly when
  needed), and **`acknowledge_size_overflow` has no caller anywhere** — the documented override is
  a dead end. Zero tests.
- **Fix:** Phases 7.4–7.5 and 8.

### Station 12 — Generation (pt step 6b)

- **Does:** fills the skeleton.
- **Breaks:** truncates silently above the ceiling — and can truncate on a statement boundary so
  `ast.parse` **succeeds** on a script missing a TestCase.
- **Why — and this is the reversal:** the 2026-08-03 session concluded the variance was
  irreducible. It is not. The installed CLI exposes **`--effort`** (bounds total thinking) and
  **`--session-id`/`--resume`** (multi-turn), and `llm.py` passes neither. The CLI transport
  **discards the `stop_reason` both HTTP backends already raise on** — that single omission causes
  all three "masks". And **40.9% of the answer is verbatim re-emission of the server's own
  skeleton** — 5,344 tokens retyping what the server holds.
- **Fix:** Phase 7.1–7.3 (cheap, may remove the need for chunking), then 7.6 if still needed.
- **Prompt defects here too:** rule 3 tells the model to *"bind every device you use in
  `TestSet.init`"* — contradicting the fixed frame, and it **directly caused the only outstanding
  lint error on the best script**. The model was right; the prompt was wrong.

### Station 13 — Lint and the fix loop

- **Does:** the last offline check, and the repair path.
- **Breaks:** the completeness check is a **warning**, wrapped in a blanket `except`, and
  `confirm_step` never reads `lint.ok`. The unbound-port check **switches off entirely** once
  `_ck_bind_link` is called once. **No lint catches a device bound but never used** (D13's
  sibling). The generated **library is never linted** but is uploaded to hardware.
- **The fix loop (D15):** `fix_script` assigns → invalidates → lints → **persists**, so the
  regression *is* the session before anyone can object; it re-stamps provenance so it **looks
  verified**; it is the only script-emitting endpoint **with no size gate** while demanding the
  whole file back — so it cannot fit by construction. And **pressing the UI's Lint button routes
  through `save_script`, overwriting the good file on disk.**
- **Fix:** Phase 9 — a lexicographic worse-than metric (**error count alone scores the regression
  a tie**), gate the fix call, archive on all three overwrite paths.

### Station 14 — Preflight

- **Does:** decides whether to spend bench time.
- **Breaks:** the verdict is **binary**, so "cannot determine" prints as `UN-RUNNABLE` (D14). But
  the dangerous direction is the opposite: **false RUNNABLE on five routes**, one live — `check()`
  never reads the bench's own `ck_role_dut`, and the docstring cites an override **that does not
  exist**. `_ck_bind_link` **discards the `:<port>` disambiguator**, so a fibre case binds copper
  on tb470. **Nothing in the product ever calls preflight** — `POST /run` goes straight to
  hardware.
- **Fix:** Phase 10.

### Station 15 — The run

- **Does:** executes on the bench. **It has never happened. `step7.runs` is empty for all six
  sessions that have ever existed.**
- **Breaks — the real cause, reproduced offline:** `RunManager._run` is a `threading.Thread`; its
  first status write goes through `_pt_persist` → `locks.require_can_write`, whose holder is a
  **`ContextVar` a new thread does not inherit**. Holder is `''`, the browser tab holds the lock,
  **`LockConflictError` before SSH is attempted** — and it surfaces as *"SSH connect failed: … the
  case is locked"*. Both routes to the bench were closed: this on the browser path, and
  `pt_autopilot` having **no hardware phase** at all.
- **Then, behind it:** `parse_framework_log` returns `numPassed: 0, numFailed: 0` for a suite that
  never started — and `_ck_bind_link` correctly aborting on a bench problem produces exactly that.
  **The loud guard arrives as a clean sheet.** It also has **no test and no fixture log**, though
  every downstream verdict (`validate()`, `fix_script`) derives from it. And `pt_autopilot`'s
  status counts a non-compiling script as `pytest ok` — it would have reported **10/10** for the
  2026-08-03 batch.
- **Fix:** Phase 11.0 (the lock), then 11.1 (`NO RESULTS` as a distinct state) *before* the first
  run, or the first verdict is untrustworthy by construction.

### Station 16 — Test coverage (cross-cutting, but it explains all of the above)

- **Does:** 41 backend files (775 parametrized), 9 Vitest specs (92), 2 Playwright specs.
- **Breaks:** **every gate the product added to stop silent under-testing is itself untested** —
  `_size_overflow`, `_coverage_report`/`_coverage_gate_error`, the structural half of
  `_lint_generated` (the `ts.run` and logging-contract checks that were the *only* things that
  revealed the truncated 16-of-17 script), the D8 fragment guard, `_contract_role` (the D12 fix),
  and `parse_framework_log`. **7 of 17 pipeline stages are effectively untested**, and
  **4 of the PyTest Creator's 25 endpoints** are ever called over HTTP by any test — all four for
  lock/security reasons.
- **10 of 14 prompt templates have zero tests**, including all six drafting prompts. Both Jinja
  environments use the **default `Undefined`**, so a dropped context key renders empty and
  silently.
- **`guard_db_only.py` has a one-`#` bypass** — its `ALLOW_RX` includes `"# "`, so any line with a
  trailing comment is skipped. Neither invariant guard has a test proving it can still detect a
  violation.
- **The coverage is shaped like the bugs that were *filed*, not like the pipeline.** The covered
  stages are the ones with a bug history; the uncovered ones decide whether a test case exists at
  all.
- **Fix:** Phase 12.3 — the offline, tokenless, hardware-free pipeline-contract tier. Every piece
  it needs already exists (`run_scratch_server.sh`, `conftest._isolate_db`, `dry_run`) and is
  simply never used together.

### Station 16 — Judging

- **Does:** grades the artefact.
- **Breaks:** **every criterion that runs is a bookkeeping check.** C1 counts classes; C2/C3
  compare **server-stamped tag strings**; C6 pattern-matches log shapes. **None reads a CLI
  command, an assertion or an expected value.** C2 returns "exactly" while reporting
  `avg_code_overlap: 0.000`, because it recomputes the expected tag from the same `maps_to` the
  server stamped from — **it measures the stamper against the stamper.** Criterion 4, the only
  semantic one, is **excluded by construction on exactly the cleanest-looking scripts**. C4 and C5
  have never been graded. The rubric's final authority — the human holistic verdict — **has no
  mechanism anywhere**, so no script has ever received a final verdict.
- **Fix:** Phase 12 — and note `pt_matrix_judge`'s HOLISTIC prompt **already asks the right
  question** and was simply never pointed at the delivered artefact.

---

## Principles

1. **Every phase installs a working anchor**, not just a repaired defect. Two anchors already
   exist on paper and are inert; adding a third paper anchor is worthless.
2. **Every gate added must be able to fail.** Write the failing case first. The recurring
   pathology here is a check that *cannot* fire.
3. **Every phase is verifiable offline, without tokens and without hardware.**
4. **No silent salvage.** The three worst defects in this audit — `extract_json_block`'s inner
   object, the provenance stamp, C2's tautology — are all *partial success presented as full
   success*. Prefer a loud failure to a recovered fragment of an answer.

---

## Phase 0 — A coverage register: provable evidence that every case was checked

> **Reframed 2026-08-03 by Terrence.** My first draft treated "79% of cases have no objective" as
> the defect. **It is not — it is the input condition this product exists to address.** Terrence:
> *"I dont really care too terribly much if they have no objectives or test steps, its more
> important to say 'yes here is the evidence that we checked **every** test case'."*
>
> So Phase 0's goal is **auditable completeness**, not input quality. Source poverty is a
> *property to record per case*, never a reason a case goes unaccounted for.
>
> **We cannot produce that evidence today.** Measured:
>
> | | |
> |---|---|
> | AWPTCM targets | 410 |
> | Hidden as out of scope | **30** — a hardcoded `frozenset` in `case_registry.py`, justified in a code comment and nowhere a reviewer looks |
> | In scope | 380 |
> | Refined (Complete) | 53 |
> | …of those, carrying a record of **how they were made** | **12** |
> | …**Complete with no provenance at all** | **41** |
> | Never touched | 327 |
>
> There is no register. `get_cases` returns complete / in_progress / not_started — a UI dropdown,
> not an audit record. For 41 of the 53 cases we have finished, we cannot say what evidence was
> consulted, which model wrote it, or whether a human ever looked.

**0.1 — The coverage register** (`tool/ck_coverage.py` + a page in the UI). One row per target
case, no exceptions, each carrying:

- **scope**: in-scope / excluded — and for an exclusion, **the reason and who decided**, not a
  frozenset membership;
- **source evidence found**: what the case itself carried, and what the corpora offered
  (candidate count and best score per corpus);
- **state**: not-started / in-progress / refined / generated / preflighted / **run** / graded;
- **provenance**: prompts, models, selections, and whether each gate was confirmed by a human or
  by the machine (Phase 3.7);
- **verdict, including the negative ones**: `authored`, `blocked: no corpus evidence`,
  `blocked: source empty and no candidates`, `excluded: out of scope`. **A case with nothing
  available must produce a recorded "checked, found nothing" — an absence is not an answer.**

This register *is* the deliverable Terrence asked for. Everything else in Phase 0 exists to make
its rows trustworthy.

**0.2 — Migration discipline.** A versioned, reviewable, idempotent migration mechanism for
`ck.db` with a recorded schema version and dry-run. Required by 0.4 and Phase 4; without it the
first write sets a bad precedent on a 459 MB non-rebuildable LFS blob.

**0.3 — Fix the false negatives in the evidence record — but WIRE THE CONSUMERS FIRST.**

`ck.db` was built from an intermediate 5h47m older than the extractor fixes, so **1,298 script
bodies (556 KB), 3,440 `testData` fields, 480 issue links and 250 attachments are absent from our
copy while present in the source.** Then correct `schema.sql`, which claims these columns are
populated.

> ⚠️ **SEQUENCING CORRECTION — the adversarial verifier caught two things that change this.**
>
> 1. **None of the recoverable content belongs to the 410 targets.** All 1,298 bodies are in the
>    45,017 **cross-reference** rows. The backfill enriches *exemplars we cite as evidence*, not
>    the target cases' own bodies. Still valuable — exemplars are the grounding — but it does not
>    make a single target less empty.
> 2. **Nothing reads those columns today.** `script_text`, `issues`, `attachments` and
>    `refs_text` have no consumer in any prompt, review row or ranking. Loading 556 KB into
>    `ck.db` right now would leave **every prompt byte-identical** while spending the one
>    irreversible act available on a permanent LFS-shipped DB — and the obvious verification
>    ("`script_text` non-empty ≥ 1298") would give a **false green**.
>
> **Revised order:** wire the consumers (Phase 1.1/1.2 render this content into the prompts and
> the review rows), prove the pipeline uses it, *then* backfill and measure the difference in
> what the model actually receives. The migration mechanism (0.2) is still built first.
>
> **De-risked:** the precedent exists — `cli_commands` was added to the "built once" DB **eight
> days after the build** by a standalone loader (`tool/load_cli_docs_from_zips.py`). Extending
> `ck.db` is not unprecedented, and `guard_db_only.py` does not forbid it.

**0.4 — Make the accounting fields trustworthy.** `has_objective` is `1 if obj.strip() else 0`
(so `'l'` counts) and `num_steps` counts blank placeholders (wrong for **322 of 410**). Any
completeness report keyed on either is wrong for 79% of the corpus. Replace with a read-time
classifier (`case_quality.py`) computing content-bearing steps and a graded `objective_state`;
repoint every consumer; add a test that fails if either raw column is read in a decision path.
**Also remove them from LLM-visible prompt text** — a model currently reads `Has objective: True`
about a case whose objective is `'l'`.

**0.5 — The register is SCOPED, and so is the claim.**

> **Second correction from Terrence, 2026-08-03:** *"'we checked every case' is relative to the
> content being checked. 'we checked every DHCP case' doesnt mean we need to choose the Bootloader
> stuff. We wont be automating bootloader and GRUB bootloader tests (its impossibly out of scope
> here), thats why we are omitting them."*
>
> I had proposed recording the 30 hidden cases as attributed per-case exclusions. That is noise.
> Bootloader and GRUB are not excluded *cases* — they are **not in the universe**: bootloader
> behaviour is driven over serial during boot, before anything the framework can attach to. That
> is a **one-line scope statement, not 25 rows.**

The scope unit is the **Zephyr folder**. A claim is made per scope — "every Port case", "every
IPv4 case" — and the denominator is that folder, not 410.

| Scope | Cases | Refined | With provenance |
|---|---|---|---|
| **Port** | **7** | **7** | 1 |
| IPv4 | 44 | 19 | 4 |
| Switching | 75 | 8 | 4 |
| Authentication & Security | 42 | 5 | 1 |
| Sanity Check | 15 | 5 | 0 |
| Management | 71 | 4 | 2 |
| QoS | 22 | 4 | 0 |
| IPv6 / Advanced Management / 11 more | 109 | 0 | 0 |
| *Bootloader + GRUB — not automatable, out of universe* | *25* | *1* ⚠️ | *0* |

Consequences:

- **Port is already 7/7** — the one scope where the claim is earned today, and therefore the
  natural pilot for the register. But only **1 of the 7** carries provenance, so it cannot
  currently be *demonstrated*.
- ⚠️ **One Bootloader case was refined anyway**, despite the hidden set. Harmless, but it is
  exactly the drift a scoped register surfaces and a `frozenset` does not.
- Out-of-universe categories are declared **once, with the reason**, at the top of the register.
- Within a scope, a case with no corpus evidence still gets a row saying so. **An absence is not
  an answer** — but a category we do not automate is simply not in the denominator.

**0.6 — Language.** 1,169 CJK-bearing rows across Zephyr and TestLink are unreachable by FTS and
noise to the English embedder. Detect, record, translate into prompt context at read time. Under
this framing the point is not translation quality — it is that a Japanese-authored case must not
be recorded as "no evidence found" when the evidence exists and we simply cannot read it.

**Verification:** the register accounts for **410 of 410** with no row in an unknown state; after
0.3, `script_text` is non-empty for 1,298 cases; every one of the 41 provenance-less Complete
cases is either backfilled with a record or explicitly marked `provenance: none (pre-register)`.

---

## Phase 1 — An objective may never be ungrounded

> **The measurement, not the description.** The audit recovered the *exact* prompt sent for
> `AWPTCM-T43870` from stored provenance: **23 bare `ID: title` lines and nothing else.**
>
> | | |
> |---|---|
> | Body content those 23 confirmed selections point at | **18,961 chars** |
> | Actually transmitted | **1,224 chars** of titles |
> | **Ratio** | **6.5%** |
>
> Breakdown: 8 TestLink selections = 334 title chars vs **8,830** of body (AWP-20423 alone has
> 2,173 chars of preconditions); 7 Zephyr exemplars = 238 vs **7,126**; 8 ATP = 652 vs **3,005**.
> Separately, `_synthesis_context` ([llm.py:1017-1029]) returns seven fields, **none from the
> case's own row** — not its objective, precondition, steps, `script_text`, labels, or its title.

**1.1 — Pass the case's own row** into `_synthesis_context`: title, objective, precondition,
`steps`, `script_text`, `refs_text`, `labels`, `self_snippet`. Flag empty fields explicitly so the
model is *told* it is working from nothing.

> **Cheaper than first estimated — effort S, not M.** `data["zephyr_master"]` already holds **all
> 410 target bodies resident in RAM (~3 MB)** ([data.py:64]). This is a pure dict-field addition
> with **no DB round-trip**. It also does not depend on Phase 0.3's backfill: the three targets
> with `script_text` already have it, and the backfill's 1,298 bodies are all cross-references.

**1.2 — Hydrate each selection's body at prompt time**, from `ck.db`, via
`db.get_testlink_case` / `db.get_zephyr_case` — **not** from whatever the UI persisted.

> **Correction — "it's 95% built" does not generalise.** I had said the rich body is already on
> `Selection.justification` and only needs rendering. It depends how the row was selected:
> [db-search.js:186-187,260-261,333] build **LLM-suggested** rows as
> `justification: s.reason || "LLM suggestion"`, so for those the stored justification can
> literally be the string `"LLM suggestion"`. Rendering it helps some rows and not others.
> Hydrating from the DB is the correct fix; the template change is a stopgap.

**1.2a — Index TestLink `preconditions`.** **3.75 MB across 9,267 cases is in no FTS index, no
relevance score, and no rendered description.** For those rows `build_testlink_description` falls
back to the bare title — so even a correct 1.2 returns a title again. **This hole defeats the
headline fix for a large slice of the corpus** and must land with it.

**1.3** Build retrieval queries from the case **body**, not just its title. Title-derived queries
retrieve title-similar candidates whose titles are then the only thing sent to the model.

> **Partial correction:** "title-only" overstates two of the four query builders.
> `descriptions.py:189-191` appends `sel.justification` for every step-1 selection — often the
> full 300–450-char TestLink step body — so the **ATP** query is materially richer than a title.
> `_build_zephyr_query` also folds in the folder leaf and the decision phrase. The claim holds for
> the *case's own body* never participating; it overstates how bare the queries are.

**1.4** Per-bullet provenance: every `<li>` carries a citation. Uncited bullets are marked
`UNGROUNDED` — flagged and counted, not removed.

**1.5 — The grounding gate (must be able to fail).** Refuse export on: zero confirmed selections
on any step; ungrounded fraction over threshold; near-restatement of the title; non-English
output. Each with an explicit recorded `acknowledge_*` override.

**1.6** Fix the defects on this path: `synthesize_objectives` must validate and the UI must
surface `provenance.error`; pass explicit `max_tokens` on both wizard call sites; reject an LLM
error string being parsed into a step; fix the non-greedy `<ul>…</ul>` extractor that truncates
nested lists; extend the timeout/`max_tokens` AST invariant to `routers/wizard/`.

**1.7 — Tests, because there are none.** `tests/test_drafting_prompts.py`: render every drafting
prompt against real corpus rows; assert the evidence block is non-empty when selections exist;
pin every gate's failure case.

---

## Phase 2 — A step must state what should happen

**2.1** Rewrite `generate_steps.jinja`. Delete *"expectedResult usually empty or brief"*.
**Change the example** — the example is the spec.

**2.2** Give step synthesis the corpus context it already builds and then does not render.

**2.3** Require test data, measurement method and topology per step.

> **Measured directly across all 53 bundles (645 steps).** Best-match similarity of each step to
> its nearest objective bullet: **mean 0.55, median 0.51, and 33% above 0.6.** So a third of all
> steps are close paraphrases — but two-thirds do add something, and the audit's blanket
> "largely a grammatical transposition" is too strong. The top third is indefensible, though.
> `AWPTCM-T33303` at **0.98**:
>
> > **BULLET:** *Per-VLAN and per-interface frame counters increment consistently with the tagged
> > and untagged traffic actually forwarded.*
> > **STEP:** *Verify per-VLAN and per-interface frame counters increment consistently with the
> > tagged and untagged traffic actually forwarded.*
> > **expectedResult:** `''`
>
> The step is the bullet with `Verify ` prepended. **The prompt asks for exactly this** —
> `generate_steps.jinja:13` says *"One or a few steps per major objective bullet"* and `:14` says
> *"Use 'Verify...', 'Set...', 'Test with...', 'Confirm...'"*. An objective bullet is a
> declarative **end state**; a step must be a **procedure**. Converting the grammar adds no
> test-design information, and the prompt never asks for any.

**2.4 — Rework debt.** All 53 refined cases were produced by the old prompt and must be
regenerated, not patched. **Do this after Phase 4 and Phase 7.2**, or the run is wasted.

---

## Phase 3 — Validation must be able to fail; export must not destroy

**3.1** Content rules in `validate_zephyr_payload`, each emitting a real issue or warning:
non-empty `expectedResult` on every non-note step; no step is a bare restatement of a bullet; no
step is an LLM error string; CLI tokens resolve against `cli_commands` (needs Phase 4); steps
cover the objective; objective is grounded (Phase 1.4).

**3.2** Make `warnings` reachable at all.

**3.3** Fix export integrity:
- **Check `step4.confirmed`.** `can_synthesize` ([gates.py:29]) gates only steps 1–3; nothing
  anywhere reads `step4.confirmed`. The documented review pause between objective and steps is
  advisory in the UI and **absent from the API**.
- **Refuse a confirm with zero selections** — 2 of 44 real sessions have one, and `AWPTCM-T33235`
  has all three empty.
- **Make a server-side gate read `stale`.** It is written at [gates.py:85,90] and read at exactly
  two places, both frontend badges ([generator.js:171,193]). Any non-browser caller — including
  `pt_autopilot` — is unaffected by it.
- **Stop re-export gutting `traceability.md`.** `backfill.py` restores step4/step5 but never
  step1–3 `selections`, so a rehydrated case re-exports with an empty cross-reference section.
  **Latent, not realised** — see 3.4. Fix as prevention.

**3.4** Fix `traceability.md`.

> **CORRECTED by Terrence — my finding was confounded.** I reported that "41 of 53
> traceability.md files have no Zephyr cross-reference section" and attributed it to re-export
> having *already gutted 40 artefacts*. Terrence's read — *"they were likely generated before we
> increased the documentation"* — is correct. By commit date:
>
> | Last commit | Has Zephyr rows | Count |
> |---|---|---|
> | 2026-07-13 | No | **40** |
> | 2026-07-13 | Yes | 2 |
> | 2026-07-14 | No | 1 |
> | **2026-08-03** | **Yes** | **10** |
>
> The template gained the section in `05b194a`, dated **2026-07-13**. Those 40 were rendered by
> the older template. **Every case the current pipeline has exported has its cross-references.**
> My `session.json` correlation was confounded: 10 of the 12 session records are also from
> 2026-08-03, so both variables proxied "generated recently". 51/53 correlation, zero causation.
> The 40 need a **re-render**, not a repair.
>
> **What does still apply to current output:** across rows that render, `- Objective:` reads
> **No on 84 of 86** — the template asks `{{ 'Yes' if (s.objective or '')|length > 5 else 'No' }}`
> and the selection dict carries no `objective` key; `- Folder:` is blank for the same reason.
> Verified on `AWPTCM-T44297`, a 2026-08-03 case. **This is the file `upload_refined.py` attaches
> to the live Zephyr case**, so a pushed artefact asserts every cross-referenced case has no
> objective and no folder.
>
> **Withdrawn:** I also listed its `data/zephyr_full/` reference as a deleted path. It is not —
> the directory holds the 125 MB export plus a README, both tracked, and `.gitignore:35-37` says
> they are *"intentionally included ... because tools depend on them."* That line is correct.

It also never contains the objective itself — fix that, and carry the per-bullet citations from
Phase 1.4 so the artefact actually traces.

**3.5** Make `upload_refined.py` run the validator; remove the silent escape-repair. Fix the
Zephyr-web-links parser looking for a heading the template does not emit.

**3.6** Write a session record for every export — 41 of 53 Complete cases have no provenance —
and keep history on re-run.

**3.7** Record machine-confirmed gates in the bundle. The ten 2026-08-03 cases have never been
reviewed by a human and nothing says so.

**Verification:** run the new validator over all 53 bundles and publish the failure table.
**Expect 43 of 53 to fail on `expectedResult` alone.** A green result means the gate is broken
again.

> **Baseline correction:** I previously said all 53 pass validation today. They do not — **50
> pass, 3 fail** (`T33243`, `T33246`, `T33234`), each on *"First test step must be the
> server-generated traceability note"*. All ten of the 2026-08-03 batch are valid with zero
> warnings, so the "zero warnings is vacuous" finding stands unchanged.

---

## Phase 4 — Make CLI grounding actually match

**The highest-leverage fix in the plan.** It is a data-normalisation problem, it needs no LLM,
and it unblocks the anchor for Phases 2, 3, 5 and 12.

**4.1 — De-hyphenation.** ~591 of 3,297 distinct command names (18%, a conservative floor — the exact count depends on the detection heuristic) are stored hyphen-stripped from doc-page
slugs while their own `syntax` column holds the correct spelling. Derive the real command name
from `syntax` at read time (or normalise via 0.1) and match both forms.

**4.2** Fix `detect_commands` abandoning a command when its first occurrence sits inside a longer
match — grounding currently depends on sentence order.

**4.3** Handle abbreviated and negated forms in fragment code, and **flag a command the reference
does not recognise** rather than silently omitting it.

**4.4** Surface `cli_commands.tables` (5,368 rows of per-media argument matrices) to the prompts,
replacing 18 lines of hand-written prose about `speed` forms.

**4.5 — Recover the stranded sample output.** `harvest_cli_docs.classify()` requires a literal
`awplus` prompt in a `<pre>` block ([harvest_cli_docs.py:69,169-172]); anything else is filed as
*syntax*. That strands **404,041 chars of real sample output in the `syntax` column of 559
rows**, and is a large part of why `sample_output` covers only 1,250 of 6,323. Re-classify from
the data already in `ck.db` — no re-fetch, no network.

**4.6** Surface `notes` (6,319 rows) alongside `tables` — release-note "Command changes" and
legal-parameter matrices reach no prompt and no validator.

> **The measurement that makes this Phase 4's priority.** Stage J reconstructed the flagship
> generation prompt from `ck.db`: **95,038 chars, of which 18,773 (19.8%) is the CLI grounding
> block — and it contained ZERO real sample output.** The commands T44297 is actually about never
> reached it. Rule 4b told the model *"NEVER invent CLI output. Match assertions to the REAL CLI
> REFERENCE above, character for character"* — against a reference showing no output. **That is
> the script that graded 6/6.**

**Baseline — measured by me, replaying all 53 refined cases through the real `cli_lookup`:**

| Outcome | Cases |
|---|---|
| **Zero commands detected** — no grounding at all | **15** |
| Commands detected, but **no real sample output** | **37** |
| **Real sample output present** | **1** |

The anchor delivers what it exists for on **1 of 53 cases**. (The audit said 19; it counted any
non-empty block. Mine counts blocks containing actual device output.)

**De-hyphenation, measured:** **1,090 of 4,035** distinct `(command, syntax)` pairs store a
command name whose own `syntax` column contains hyphens it lacks — e.g. stored
`2fa email expiry time` against syntax `2fa email-expiry-time <1-1440>`.

**The flagship case, end to end.** `AWPTCM-T44297` is an LLDP **TLV-select** test.

```
detect_commands('configure lldp tlv-select port-description')  ->  []
detect_commands('configure lldp tlvselect  port-description')  ->  ['lldp tlvselect']
```

Writing the command **correctly** finds nothing. And `lldp tlvselect`'s `sample_output` is
**0 chars**, so even a match would ground nothing. The anchor fails twice over on the one command
the case is about.

What the model actually received:
- **step 2** (from the refined case): **196 chars**, one command — `management address` — zero output.
- **step 6** (from sequence + fragments, read from the stored prompt): a 95,038-char prompt whose
  CLI block is **5,032 chars over 12 commands** — `switchport access vlan`, `clear lldp
  statistics`, `show lldp neighbors`, `tcpdump`, `speed`… — with **zero `awplus` prompt lines**,
  i.e. **no real device output at all.**

Both blocks are headed *"REAL CLI REFERENCE (AlliedWare Plus — authoritative; match these formats
exactly, do NOT invent output tokens)."* **This is the script that graded C1 EXACTLY / C2 EXACTLY /
C3 RIGHT / C6 YES.**

**Verification target:** near-total coverage; assert T33277 ("spanning-tree") resolves to
`show spanningtree`'s 2,388 chars of real output, and that T44297 reaches `lldp tlv-select`.

---

## Phase 5 — Sequence extraction must not misdiagnose or silently salvage

**5.1 — Fix `extract_json_block`.**

> **REPRODUCED, not inferred.** The T33304 reply survives in
> `CK_server/debug-log/no-session.jsonl`. Replayed through the real `llm.extract_json_block`:
>
> ```
> reply chars: 30183
> extract_json_block returned type: dict
>   keys: ['n', 'action', 'verify', 'kind', 'zephyr_step_idx']
>   has "sequence" key?: False          -> _parsed_list [] -> 502
>
> after repairing the ONE ternary:
>   sequence entries: 53
> ```
>
> The offending token is `"zephyr_step_idx": 44 > 0 ? 23 : 23`. A one-line regex repair recovers
> **all 53 entries**. The model's answer was fine; the parser threw it away.

**Mechanism (code-read, [llm.py:1608-1636]).** `_extract_first_balanced` collects **every**
opener position — both `{` and `[` — and returns the first that parses. When the outer
`{"sequence": [...]}` fails, the loop walks inward and succeeds on **the first array element**.
Its own docstring states the opposite intent ("an object with a nested array must not return the
inner array"); the fallback loop defeats it whenever the outer object is the thing that is broken.

Return a **typed failure** distinguishing *malformed-outer* / *unparseable* / *legitimately
empty*. Then fix all four `_parsed_list` call sites to honour the distinction — and note this is
also the **door that re-opens D8**, because `gather_fragments` guards only on `parsed is None` and
a salvaged inner object is not `None`.

**5.2 — Make the provenance promise true.** The 502 says the raw response is stored; it is
written ten lines after the raise. Store it **before** raising, at every 502 site.

**5.3 — Attempt principled repair, loudly.** A JavaScript ternary in a JSON field is repairable.
Repair it, **record that a repair happened**, and never present a repaired parse as a clean one.

**5.4** Pass explicit `max_tokens`; detect truncation from the CLI envelope's own token counts.

**5.5** Validate sequence entry shape and `kind` vocabulary. An out-of-vocabulary kind currently
degrades a physical step to an ordinary TestCase, deleting the operator prompt.

**5.6** Record model, parameters and prompt hash. Set temperature on the CLI transport, or accept
and document non-determinism — today the same case yields 44–50 steps and **flips the coverage
gate**.

**5.7 — Move the size check to step 2.** It is knowable the moment the sequence is confirmed and
currently runs three paid LLM steps later.

**5.8** Fix the autopilot recording pre-trim coverage as if it were the outcome.

---

## Phase 6 — Fragment reuse must be real

**6.1 — Make the provenance tag mean what it claims.**

> **Code-read** ([pytest_create.py:994-1017]): `tag_by_step` is built entirely from
> `f.get("maps_to")` — the **LLM-supplied** mapping — and `_fragment_tag(source_id, loc, …)`.
> **The emitted code is never examined.** The tag asserts *where a block came from* on the basis
> of which step a fragment was *offered* for.
>
> **Measured directly on the delivered T44297 script** (normalised, comment-stripped, best match
> against every candidate fragment):
>
> | TestCase | Tag | Overlap |
> |---|---|---|
> | 1 | `ART library_1332.py lines 85-111` | **0.024** |
> | 2 | `ART library_1332.py lines 10-15` | **0.031** |
> | 3 | `legacy lldp_class.py lines 335-344` | **0.062** |
> | 4–6 | `legacy lldp_class.py lines 102-136` | **0.066–0.069** |
>
> (The audit reported 0.000; my normalisation leaves 2–7% of shared Python tokens — `self.`,
> `log(`, `port`. Same conclusion, and I report my own number.)
>
> **The concrete case.** `TestCase_2` is stamped `# ART 1332_lldp_med/library_1332.py lines 10-15`.
> That fragment is `log_packet`, a six-line stdout capture helper:
> `old_stdout = sys.stdout / sys.stdout = StringIO() / pkt.show() / …`. What follows the tag is
> `dut.mode(')#')`, `dut.cmd('lldp run')` — **not one line of it.**

Measure actual overlap between the emitted `main()` and the cited fragment; stamp
`reused` / `adapted` / `not-used` accordingly, and let the tag say which.

**6.2 — Fix C2 in `pt_grade`** to grade the *code*, not the stamp. It currently measures the
stamper against the stamper and cannot fail on the model ignoring its fragments.

**6.3** Make the fragment pool track de-selection — 13 of 18 in T33233 are orphans from scripts
the reviewer removed.

**6.4** Give setup-mapped fragments a destination, or stop selecting them — 7 of 13 in T44297
were invisible while consuming ceiling-bound prompt budget.

**6.5** Fix `code[:8000]` cutting mid-token while the tag claims the full range; mark truncation.

**6.6** Fix duplicate-helper resolution returning the first (dead) definition; include decorators
(`loc[0]` is the `def` line); handle the 146 py2 scripts with no end line and no helpers.

**6.7** Use the indexes that are already built and shipped — `scripts_fts`, `vec_scripts`,
`chunks_fts`, `vec_chunks` are all unread while selection is a bag-of-words scan over directory
names.

**6.8 — A fragment currency check.** Nothing asks whether a legacy source script still works.
The known fix set (py3-only framework, read-only `Switch.name`, TBv4 device paths, **gate strings
that no longer exist in the software**) is applied by nobody, and a rotted gate string does not
fail — it *waits*.

**6.9** Make `confirm_step` require the previous step confirmed.

**6.10** Write the missing tests: both D8 branches, and the D1 resolver hardening.

---

## Phase 7 — Generation must not silently truncate

> **The 2026-08-03 conclusion was wrong, and the ceiling is far cheaper to fix than believed.**
> That session concluded the thinking variance was irreducible and left the ceiling unfixed
> (decision #15). The audit checked the installed binary: **`claude --help` (v2.1.207) documents
> `--effort <level>`, which bounds *total* thinking — the knob the findings doc says does not
> exist — and `--session-id` / `--resume` / `--fork-session`, i.e. multi-turn continuation.**
> Chunked generation was costed as "real work" partly on the assumption the transport is
> single-shot. **It is not.** Every downstream decision followed from a refuted premise.

**Do these four first — they are cheap and may make 7.6 unnecessary:**

**7.1 — Stop discarding the truncation signal.** `_parse_cli_stream` reads only assistant text
and the terminal `result`; it never reads `message.stop_reason` or `usage`. Both HTTP backends
**already raise** on `stop_reason == max_tokens`. **This single omission is the cause of all
three "masks"** the findings document describes — a truncated generation returns HTTP 200 and
gets stamped, linted, persisted and written to disk. Capture `stop_reason` and raise.

**7.2 — Pass `--effort`.** Gated by the same `_is_long_call` predicate as the thinking cap, so
the 30s health ping is untouched (the D11 regression).

> **Verify before relying on this.** I confirmed the flag exists on the installed binary
> (`--effort <level>  Effort level for the current session`). I have **not** confirmed
> empirically that it bounds *total* thinking rather than per-block — that is the audit's
> inference from what the flag is for, and it is exactly the assumption `--max-thinking-tokens`
> violated. **First task of 7.2 is to measure it**: same prompt at each level, recording total
> output tokens, thinking tokens and delivered chars. If it does not bound the total, 7.6 becomes
> load-bearing again. Same caveat for `--resume` in `-p` mode: verify it preserves earlier turns
> and still honours `--tools ""`.

**7.3 — Stop re-emitting the skeleton.** Measured by me across every stored generation
(`difflib` matching runs ≥40 chars, skeleton vs delivered):

| case | delivered | verbatim from skeleton | share | ≈ output tokens |
|---|---|---|---|---|
| T33233 | 19,807 | 14,535 | **73.4%** | 5,029 |
| T33234 | 20,523 | 16,135 | **78.6%** | 5,583 |
| T33235 | 20,227 | 16,147 | **79.8%** | 5,587 |
| T44297 | 37,744 | 15,447 | 40.9% | 5,345 |

> **The absolute figure is near-constant at ~15–16k chars / ~5,300 output tokens, whatever the
> case.** That is the fixed frame being retyped every time. The percentage only looks lower for
> T44297 because it wrote more novel code. So this is a **flat ~5,300-token tax on every
> generation** — and against the heavy-thinking answer budget of ~14,500 tokens, that is
> **up to 37% of everything the model is able to say**, spent transcribing text the server
> rendered seconds earlier and still holds in memory.
>
> (My T44297 figure matches the audit's 15,446 to within rounding; the other three cases it did
> not measure.)

Change the output contract to slot-only: the model returns `main()`/`tear_down()` bodies keyed by
class number, the server splices them into its own frame. It *is* the assembly step chunking
needs — build it once.

**7.4 — Fix the gate's arithmetic.** Three separate errors:
- It reserves the **per-block** cap (2,048) as if it were the total against a measured ~20,400 —
  over-stating the answer budget by up to 51%. Reconstructed from the real skeleton in `ck.db`,
  the false-negative band is **10–15 TestCase classes** (my cruder estimate was 7–18; theirs is
  from the actual stored skeleton and is the one to use).
- `fits` **scales the fixed skeleton head linearly with class count**, over-stating the
  survivable count by ~20% — so the gate's own remediation advice sends you back over its limit.
- **`_FILL_EXPANSION = 1.95` is fitted to one case.** Measured by me across every stored
  generation in `ck.db` (skeleton from `step6.provenance.prompt`, delivered from
  `step6.files.test.code`):
>
> | case | skeleton | delivered | expansion | classes |
> |---|---|---|---|---|
> | T33233 | 19,843 | 19,807 | **1.00** | 10 |
> | T33234 | 21,448 | 20,523 | **0.96** | 14 |
> | T33235 | 20,222 | 20,227 | **1.00** | 8 |
> | T44297 | 22,980 | 37,744 | **1.64** | 6 |
>
>   The constant is set **above the single highest observation**, against a real range of
>   **0.96–1.64**. Three of four deliver at parity with the skeleton, because filled code replaces
>   FILL markers and comment scaffolding roughly 1:1. One constant is carrying two unrelated
>   effects — marker-stripping (deterministic, computable) and model verbosity (variable).
>   Separate them.
- It **hardcodes the CLI's 32,000 cap for every backend** and runs before the session's LLM
  config is read.

**7.5 — Repair the gate's surroundings:**
- **Delete the booby trap.** `tests/test_claude_cli_transport.py:239` asserts ≥28,000 answer
  tokens for "a ~42-TestCase skeleton" — it **pins the refuted premise**, so correcting 7.4 turns
  it red and the next engineer reverts the fix. A test encoding a known-wrong number is worse
  than no test. Same for the comment at `llm.py:198-203`, which claims ~44 TestCases.
- **The gate fires before the `dry_run` branch.** Verified: `dry_run` is read at :2900, the gate
  raises at :2948, the early return is at :2991. So the **zero-token** prompt preview — the
  documented paste-into-another-LLM feature — is refused with a 409 on exactly the over-budget
  cases a reviewer most needs to inspect. Move it below the early return.
- **`acknowledge_size_overflow` has no caller.** Verified: exactly two occurrences repo-wide,
  both in `pytest_create.py` — the message text at :876 and the read at :2947. Neither the
  browser nor `pt_autopilot` can send it, and the 9-line message renders into a one-line status
  span. **The documented override is unreachable.**
- **The two constant errors point in OPPOSITE directions.** The thinking reserve (2,048 against a
  measured ~20,400) makes the gate ~2.6x too *permissive*; `_FILL_EXPANSION` at 1.95 against a
  measured 0.96–1.00 shape makes it ~1.95x too *strict*. They partially cancel — which is exactly
  why the gate looked calibrated on the one case it was fitted to, and why the band in which it
  is wrong depends on **two run-time variables it cannot observe** (how much thinking this run
  consumes, and how verbose this shape turns out). Any fix must make the pessimism explicit and
  recorded, not emergent from two errors cancelling.
- **Write the tests** — boundary, constant pins with measurement provenance, `fits` correctness,
  the override path, the dry-run case.

**7.6 — Chunked generation**, if 7.1–7.4 do not open enough headroom. Chunk unit is one TestCase
class, batched by measured novel-fill cost (~1,286 output tokens/class after 7.3). **Never chunk
the frame.** Use `--session-id`/`--resume` so each chunk gets a full budget over shared context.
~8 call sites assume one-shot.

**7.7 — Promote the completeness check to an error.** The one lint that detects a cleanly-parsing
truncated script is a **warning**, wrapped in a blanket `except Exception`, and **`confirm_step`
never checks `lint.ok`**. The failure mode the findings doc calls "the one to fear" is advisory.

**7.8 — Fix the generation prompt's self-contradictions** (all `prompt-examples-are-the-spec`):
- **Rule 3 tells the model to "bind every device you use in `TestSet.init`"** — contradicting the
  fixed frame, and it **directly produced the only outstanding lint error on the best script**.
  The model's reasoning was correct; the prompt was wrong.
- Rules 1 and 8 both claim the first line of every `main()`; the lint enforces rule 8's.
- The prompt names devices from the **untrimmed** switch list, including ones the skeleton
  explicitly did not bind.
- **Four `>>> FILL` markers sit on code lines** where the server-side stripper cannot remove
  them, so each miss is a hard lint error. Move them to their own comment lines.

**7.9 — Stop truncating the forensic record.** `step6.provenance.response` is cut at 20,000 chars
with no marker — **every stored generation's reply is incomplete**, destroying the primary
evidence for exactly this class of defect.

> **DECISION REQUIRED, but now better-informed.** With 7.1–7.4 landed the ceiling may be high
> enough that 7.6 is unnecessary. If it is still needed, `--resume` makes it much cheaper than
> costed. Splitting refined cases remains the worst-supported option — Phase 3 found **the wizard
> cannot create a child case or partition an objective at all.**

---

## Phase 8 — The script must demand only what it uses

**8.1** Fix D13: derive `stacks` from devices the fragments actually *reference in emitted code*
and drop any no TestCase body uses — the same treatment `switches` already gets one line above.

> **THE FULL CAUSAL CHAIN, PROVEN — this is why no test has ever run on hardware.**
>
> 1. Two selected fragments come from `art/1332_lldp_med/test-1332.{1001,2001}.py`, whose
>    `TestSet.init()` contains `setup.init_stk('stk_a')` — **incidental** to the LLDP logic being
>    reused. (2 of 40 fragments in the pool.)
> 2. **The sequence text mentions `stk_*` nowhere.** Verified.
> 3. `_detect_topology` ([pytest_create.py:1240-1247]) regexes `_STK_RX` over
>    `sequence_text + fragment_code` → finds `stk_a`.
> 4. The skeleton renders `stk_a = setup.init_stk('stk_a')` — **assigned and never used.**
> 5. tb470 declares no `[stack]` → `pt_preflight` correctly reports UN-RUNNABLE → **no bench time
>    was ever booked.**
>
> So the reason nothing has executed is that **two reused LLDP fragments happened to come from a
> script written for a stack.** The evidence for the stack demand is a variable name inside
> borrowed code the generated script does not even call. This connects Station 9 → 11 → 15, and
> fixing it at the detection layer (not the template) unblocks the endgame.

**8.2** An AST bound-but-never-used lint, accounting for `self.<name>`, `getattr` and string
indirection.

**8.3** A property test: render the skeleton across a range of sequences; assert the device set is
exactly the set used.

---

## Phase 9 — Lints and the fix loop must not accept regressions

> **My first draft of 9.1 was wrong and would not have caught the regression.** Stage G showed
> **lint error *count* is not a valid worse-than metric**: every structural check sits behind
> `if tree:` ([pytest_create.py:1619]), so a script with a `SyntaxError` yields **exactly one**
> lint error — the same count as the 2026-08-03 best artefact's one media error. "Reject if more
> errors" scores the D15 regression as a **tie and accepts it.**

**9.1** Reorder `fix_script`: evaluate the **candidate** before assignment and before persist,
and refuse with 409 if worse. "Worse" must be a **lexicographic composite**, not a count:
`parses` → `TestCase class count` → `ts.run present` → `error count`. A parse failure is
automatically worse regardless of counts.

**9.1a — Gate the fix call itself.** `fix_script` is the **only script-emitting endpoint with no
`_size_overflow` check**, and its prompt demands the entire file back — so a fix on a
near-ceiling script **cannot fit by construction**. That is the mechanism of D15, not bad luck.

**9.1b — Tell the fix prompt what it must produce.** It receives lint *errors* only — never
warnings, coverage, or **the expected TestCase count**. The model repairing a script has no way
to know it dropped one, which is precisely the D15 outcome.

**9.1c — Stop the Lint button destroying the good copy.**

> **Code-verified, and the mechanism is worse than "routes through".** `ptLintScript()`
> ([pytest.js:893](../CK-main/CK_server/static/js/pytest.js#L893)) calls
> `await ptPushCodeEdits(false)` before linting — *"push current edits into the session first so
> lint sees them"*. But `ptPushCodeEdits` **always** POSTs to `/save_script/` regardless of its
> `writeFiles` argument; the `if (!writeFiles)` branch contains **only a comment** and changes
> nothing:
>
> ```js
> if (!writeFiles) {
>   // save_script both persists edits and writes files; for lint-only we still
>   // use it (files on disk mirror the session) — acceptable per plan.
> }
> return await ptApi(`/save_script/${S.ptCase.key}`, {...});
> ```
>
> `save_script` then calls `_persist_generated_files(sess)`. So **pressing Lint writes the
> textarea to `generated/<Group>/<Name>.py`**, and the `writeFiles` parameter is dead.
>
> That was a conscious trade-off when written ("acceptable per plan") — but it predates D15. Now
> that a fix pass can regress a script, *the reviewer's first instinct after a bad fix — press
> Lint to see how bad — destroys the last good copy on disk.* Only `history/iter-N/` survives.

`save_script` also has **no validation of any kind**.

**9.1d — Archive on every overwrite path.** Only `fix_script` archives; `generate_script` and
`save_script` both destroy the previous artefact with no copy. The safety net that preserved the
2026-08-03 best script exists on one of three paths.

**9.2** Stop `_restamp_provenance` re-tagging a regressed artefact as verified reuse.

**9.3** Guard `save_script` as defence in depth; persist lint per iteration.

**9.4** Close remaining fixed-frame bypass routes beyond the `init_portlink` one already caught.

**Verification:** replay the exact 2026-08-03 regression (37,744/6 → 25,172/0) as a test.

---

## Phase 10 — Preflight must admit what it cannot determine

> **Priority inverted by the audit.** I had D14's wrong *negative* as the headline. Stage H found
> the dangerous direction is the opposite: **false RUNNABLE on at least five routes, one live and
> demonstrated.** `check()` never reads the bench's own `ck_role_dut`, and `_contract_role`'s
> docstring claims a `check_script` override **that does not exist** — so a bench declaring
> `ck_role_dut = swi_c` is checked as if the DUT were `swi_a`, and the tool says **RUNNABLE** for
> a script that will get `(None, None)` on hardware. Combined with Phase 11.1's
> empty-equals-success, that spends bench time to produce a bogus clean sheet.

**10.1 — Kill the false RUNNABLE routes first**: the missing `bench.misc` read; power demands on
an unresolved role dropped silently (both tb470 IE520s are **not** on the PDU); link demands
counted per AST node so N calls through one helper count as one; `hub=` and two other corpus
binder idioms modelled as nothing.

**10.2** Add `CANNOT-DETERMINE`. Today `runnable = not problems` and a parse failure, an
undeclared device, an unresolvable role and a genuinely missing cable all print the same word.

**10.3** Fix D14 by checking the **contract** via `pt_profiles.py`, not by tracing
`_ck_bind_link`.

**10.4 — Wire preflight into the product.** `grep` finds exactly one reference in the whole
server, and it is a docstring. **`POST /run` dispatches to hardware with no topology check at
all.** The tool is well-tested as a library and invisible to every user.

**10.5 — Fix the copper/fibre bug the contract exists to prevent.** `_ck_bind_link` parses the
`:<port>` disambiguator out of `ck_link_<role>` and **throws it away**
([pt_script_template.py.jinja:146], `_named_port` never used). A fibre case binds `port1.0.1` —
copper, listed first — on tb470. TOPOLOGY-PROFILES.md claims this is implemented; it is not.

**10.6 — Resolve the structural contradiction that caused T44297's lint error.** `tblink` is a
declared profile tb470 implements, the LLDP case genuinely needs a capture path, **and the only
sanctioned binding path cannot bind a testbox link** — so the lint forbids the only way to get
one. **The model did the only thing available to it.** Fix the frame, not the model.

**10.7** Fix the two test fixtures that both claim to be "tb470 as at 2026-07-30 afternoon" and
disagree — the preflight one has no `[misc]` contract block, which is why 10.1's live false
RUNNABLE was invisible. Stop the "real scripts" corpus rglobbing into `history/`, where D15 keeps
known-bad artefacts.

---

## Phase 11 — Execute on tb470

> ## 11.0 — THE ACTUAL BLOCKER, reproduced offline
>
> **Every browser-initiated run dies before SSH is attempted, and reports it as an SSH failure.**
>
> `RunManager._run` runs in a `threading.Thread` ([pt_exec.py:407-412]). Its first `on_update`
> ([:421]) persists through `_pt_persist` → `locks.require_can_write`, whose holder comes from
> `llm.current_session_id` — a **`ContextVar`**. A new thread starts with a *fresh* Context, so it
> inherits nothing. The thread's holder is `''` while the browser tab holds a live, heartbeated
> lock on the same case. Reproduced with the real `locks` module:
>
> ```
> holder in main thread          : 'browser-tab-abc'   can write: YES
> holder inside RunManager thread: ''                  can write: NO -> LockConflictError
> ```
>
> Because that first `on_update` sits inside the connect `try/except`, the user is told
> **"SSH connect failed: … the case is locked"** — the polite-and-misleading shape memory
> `silent-degradation-audit-2026-07-30` warns about, and one that reads as a lab fault.
>
> **This supersedes the D13/stack explanation as the reason nothing has ever run.** D13 blocks
> *preflight* — which Phase 10.4 shows is not even wired into the run path. This blocks the
> **run itself**, deterministically, on every browser attempt. And the other path — `pt_autopilot`
> — has no hardware phase at all. Both routes to the bench were closed, for different reasons.
>
> The 2026-08-03 tb470 probe passing (`ok/ssh/framework/sudo` all true) measured the **profile
> check**, a different code path. It was real, and it did not exercise this.
>
> **Fix:** propagate the holder explicitly into the run thread (`locks` already accepts an
> explicit `holder=` for exactly this reason — see the `sendBeacon` release path), or capture and
> re-apply the parent `Context`. Then add the test that would have caught it: assert a
> `RunManager`-spawned thread can persist while the initiating session holds the lock.

**11.1 — Fix empty-equals-success next.** `parse_framework_log` returns 0/0 for a run that never
started, and `_ck_bind_link` correctly aborting on a bench problem produces exactly that. Record
expected TestCase count; report `NO RESULTS` as a distinct loud state. **This must land before
the first run or the first verdict is untrustworthy by construction.**

**11.2** Sweep the run path for the same shape; generalise `test_dependencies_declared.py` from a
hand-written list to enumerating actual runtime imports. Also: **`parse_framework_log` has no test
and no fixture log**, though `validate()` and `fix_script` both derive every verdict from it —
write one with a real captured log before the first run.

**11.3** Give `pt_autopilot` a `hardware` phase, resumable, recording preflight verdict, log,
parsed results and expected-vs-observed counts.

**11.4 — Run one case, honestly.** **A failing test that genuinely ran is the deliverable.** A
PASS obtained by weakening the test is the failure mode this plan exists to prevent.

**11.5** Then the rest of the batch.

---

## Phase 12 — Judge whether it tested the right thing

> **Every criterion that runs on a delivered script is a bookkeeping check.** C1 counts classes
> and attributes; C2/C3 compare server-stamped tag *strings*; C6-offline pattern-matches log
> shapes. **Not one reads a CLI command, an assertion, or an expected value.**

**12.0 — Fix the judges before trusting them.**
- **Both LLM judge harnesses shell out to `claude -p` with the exact D5/D9/D10 defects fixed in
  `llm.py` on 2026-08-03** ([pt_model_matrix.py:125-128]) — tools enabled, uncapped thinking,
  reading only `result`. Every Opus judge call is the $4.65-empty-reply shape. Route them through
  `llm.py`.
- **C2 returns "exactly" while reporting `avg_code_overlap: 0.000` on 6 of 6 blocks.** Uniform
  zero is not adaptation; it is the signature of code unrelated to the cited source.
- **`agreement()` classes good-vs-bad as "near-miss"**, so the only criterion-4 run ever produced
  a **100% accept-vs-reject split between judges** and printed none of it as needing attention.
- **C1 skips its TestCase-count check entirely when there is no step2 sequence** — losing the one
  signal that catches the "parses cleanly, 16 of 17" truncation.
- C6's `OBSERVED` check is a `re.S` wildcard: any `self.log(` anywhere before the word `OBSERVED`
  anywhere — including in a comment — satisfies it.
- The Opus judge uses the **drifting `opus` alias**, which on this seat resolves to a different
  model than the pinned generator.

**12.1** Unblock C5 (needs Phase 11) and C4. **Criterion 4 is excluded by construction on exactly
the scripts that grade cleanest**: it judges only `# AI`-tagged blocks, so broad `maps_to` ⇒ zero
gap-fill ⇒ `n/a` ⇒ **no semantic review at all**. One fragment with a wide `maps_to` suppresses
it for every block — no malice required. And the "unforgeable" reuse/invented split rests on an
**LLM-authored `maps_to`** from the same model family one step earlier.

**12.2 — Objective fidelity, the missing criterion.** Does each TestCase verify a specific
objective bullet, and does its assertion match real device behaviour? Grounded against
`cli_commands.sample_output` (Phase 4 makes this reachable). **This would have caught T33304's
non-existent `vlan classifier rule ... mac` form.**

> **Most of it already exists.** `pt_matrix_judge.py`'s HOLISTIC prompt asks exactly the right
> questions — *"Does every part of the objective get exercised by some TestCase's action +
> assertion?"*, *"Do assertions verify the feature under test, or merely that the command ran?"* —
> and is **hard-wired to the model-matrix directory**, so it was never pointed at the delivered
> artefact. Re-target it. Also: **the rubric's designated final authority, the human holistic
> verdict, has no mechanism anywhere in the repo** — it is written as `null`, so **no script has
> ever received a final verdict**, and the four blocks Opus called "bad" were never adjudicated.

**12.2a** Make the offline grader gate something. `pt_grade.main()` always `return 0` and is not
in `run_tests.sh`, so the only automated quality measurement is advisory. Add a gating mode.
Also surface `lint_ok`, which is reported but consumed by no criterion and no caveat — a "clean
sweep" currently coexists with a live blocking lint error.

**12.3 — An offline pipeline-contract suite** in the gate: render every prompt against real
corpus rows; run every validator over the on-disk bundles; run the size gate against known
artefacts; run preflight against `tb470.setup`; replay CLI grounding coverage. Token-free,
hardware-free. This is what stops the next defect being found 25 minutes and dollars into a
generation.

> **Every piece already exists and is never used together:** `tool/run_scratch_server.sh` (a
> throwaway `ck.db` on port 8123), `tests/conftest.py::_isolate_db`, and the `dry_run` render path.
> What is missing is **replay** — `dry_run` returns the *prompt*, not an answer, so an end-to-end
> offline run of the four LLM stages needs recorded fixtures. There is no cassette/VCR machinery
> anywhere in the repo. Building it is what makes the whole tier possible.

**12.4 — Fix the gate's own holes**, found by Stage K:
- **`guard_db_only.py` has a one-`#` bypass** — its `ALLOW_RX` includes `"# "`, so any line
  carrying a trailing comment is skipped entirely. Invariant #2's enforcement can be defeated by
  adding a comment.
- **Neither invariant guard has a test proving it can still detect a violation.** `guard_db_only`
  scans a clean tree, so it prints `GUARD OK` whether it works or is broken.
- **Both Jinja environments use the default `Undefined`**, so a dropped context key renders empty
  and silently. Switch to `StrictUndefined` and pin each template's context contract.
- **Prose-based absence assertions outside `test_prompt_examples.py` do not use `tests/_prose.py`**
  and will self-match — exactly the trap memory `checks-must-not-match-their-own-advice` records.
- **`pt_autopilot` blanket-acknowledges any 409 at confirm step 6**, disabling the only automated
  check on TestCase-count shortfall — and mis-reports a lock conflict as a coverage gap.

---

## Cross-cutting

Stage L found this layer in **better** shape than the memories claim — the 2026-07-30 CLI
transport contract is fully in code and fully test-pinned, workspace-LLM centralisation holds
with no router bypassing it, `_pt_persist` raises, and locking Phase 1 shipped. But:

- **The CLI transport has no empty-completion guard** — the *un-fixed half of D5*. `--tools ""`
  removed the cause; the **detector was never added**, so an empty reply from any other source is
  still reported as success.
- **`_is_long_call`'s 120s threshold sits below the 180s default timeout**, so **every call that
  forgot a `timeout` gets a 30-minute budget and forced extended thinking** — the D11 pathology
  re-entered through the default rather than the flag.
- **Every Objective-Drafting wizard LLM call sends no system steer, no timeout and no
  `max_tokens`** — the wizard calls `_call_llm_with_meta` directly, bypassing `run_prompt`. The
  steer measured at *"~22x fewer completion tokens"* applies to PyTest and not to the Generator,
  on the same reasoning models.
- **The autopilot takes a per-case lock it never heartbeats**, and its longest call (30 min
  ceiling) **exceeds the 15-minute idle TTL** — so the lock is stealable during the single most
  expensive call in the pipeline. Worse, **`_pt_confirm` treats every 409 as the coverage gate**,
  so a lock conflict is logged as a coverage gap and retried with the wrong override.
- **The autopilot's headline status counts a non-compiling script as `pytest ok`** — it computes
  the honest verdict, logs `DOES NOT COMPILE`, then returns ok. It would have reported **10/10**
  for the 2026-08-03 batch; RESULTS had to be written by hand as "1 complete, 0 clean".
- **Resumption skips any confirmed step**, and confirmation happens unconditionally after
  generation regardless of lint — so **a case confirmed with a broken script can never be
  regenerated by the harness.**
- **Both override flags claim a "recorded choice" and nothing is written** to the session or the
  artefact. `--trim-verify` rewrites the confirmed sequence in `ck.db` with no marker that steps
  were dropped.
- The harness **hardcodes `localhost:8000`** with no override, so it can only drive the real
  server and therefore the permanent `ck.db` — it cannot be exercised against
  `tool/run_scratch_server.sh`.
- **Cost control.** $4.65 + $5.24 burned on two agentic-loop failures with `is_error: false`. No
  budget ceiling, duration alarm or spend alert exists. Worse, **a timed-out or killed CLI call
  records no usage and no cost**, so telemetry is systematically biased toward cheap successes —
  any ceiling built on the current record would under-count exactly the expensive failures.
- **Observability.** Record thinking tokens, truncation detection and cost per call.
- **Dead entry points.** Delete or fix `pt_assess_fit.jinja`, `build_refined_viewer.py`,
  `render_batches.py`; mark the two index builders as unrunnable on this host.
- **`run.sh` always passes `--reload`** — editing under `ask-ck/CK-main` bounces the server and
  kills in-flight LLM calls.
- **NFS staleness** — read batch progress from `state.json`, not a log tail.

---

## Decisions — SETTLED 2026-08-03 by Terrence

**Do not re-litigate these.** All four were taken deliberately; the reasoning is recorded so a
later session does not reopen them.

| # | Decision | Terrence's call |
|---|---|---|
| 1 | **`push_to_zephyr` exposure** (Phase −1) | ✅ **Fix it now, before anything else.** Own small commit: confirmation token in the body, refuse to push an unvalidated bundle, audit-log every real push. Everything else waits. |
| 2 | **Backfill `ck.db`** (Phase 0.4) | ✅ **Yes, behind a migration mechanism.** Build the versioned/idempotent/dry-runnable migration tool (0.1) *first*, then backfill the 556 KB of script bodies, 3,440 `testData`, 480 issues, 250 attachments. Sets the discipline for any future write to the permanent DB. |
| 3 | **The 53 refined cases** (Phase 2.4) | ✅ **Regenerate all 53, after Phases 1–4 land.** Patching cannot add test-design information that was never generated. Regenerating before CLI grounding is fixed wastes the run — hence the ordering. |
| 4 | **The 305 empty cases** | ✅ **Triage.** Use the Phase 0 classifier plus cross-corpus candidate scores: author the ones with solid TestLink/ATP/script evidence behind the grounding gate; mark the rest **blocked on source data**. Do not pay tokens to be told no. |

### Still open

| # | Decision | Status |
|---|---|---|
| 5 | **Chunked generation vs splitting cases** (Phase 7.6) | **Deferred pending measurement** — 7.1–7.4 may raise the ceiling enough that 7.6 is unnecessary. Ask again with the `--effort` numbers in hand. Splitting remains worst-supported: the wizard cannot create a child case or partition an objective at all. |
| 6 | **Grounding threshold** (Phase 1.5) | **Defaulting** to: refuse on zero confirmed selections; warn above 40% ungrounded bullets; refuse above 70%; refuse a title-restatement above 0.8 similarity. Tunable from the first real batch — surfaced in the report, not buried in a constant. |
| 7 | **Is a failing first hardware run acceptable?** (Phase 11.4) | **Assumed yes.** A failing test that genuinely ran is the deliverable; a PASS obtained by weakening the test is the failure mode this plan exists to prevent. Confirm before bench time is spent. |

---

## What "done" looks like

1. `push_to_zephyr` cannot be triggered by an unauthenticated curl, and cannot push an
   unvalidated bundle.
2. `ck_corpus_report.py` shows the objective distribution, and `script_text` is populated for
   1,298 cases.
3. The new validator over the 53 bundles produces a **non-empty failure table** — the gate fires.
4. Every refined step has an expected result, and a sample appear verbatim in real CLI output.
5. **CLI grounding fires for near-all 53 cases, not 19.**
6. A provenance tag that says "reused" means the code was reused, and C2 can fail.
7. A previously-over-ceiling case generates completely; the size gate refuses what it used to
   wave through.
8. `pt_preflight` returns a clean `RUNNABLE` for a contract-based script.
9. **A `RunManager` thread can persist while the initiating session holds the lock** — pinned by
   a test. This is the one that unblocks everything downstream of it.
10. **`step7.runs` is non-empty in `ck.db`** — a test case has executed on tb470 and produced a
   verdict we believe, with expected-vs-observed TestCase counts recorded.
11. C4 and C5 are graded for the first time.
12. The offline pipeline-contract suite is in the gate, and the drafting prompts are no longer the
    untested half of the product.

---

## Appendix — audit provenance

12-stage adversarially-verified audit, 2026-08-03. Stages A/B/C/D/E complete (**109 findings**);
F/G/H/I/J/K/L still running — **expect Phases 7–13 to grow.** Verifier passes were still in
flight when this draft was written, so individual findings should be re-checked against code
before implementation, per this repo's own rule that a written-down claim is a hint, not a
guarantee.

**Two memories are superseded and must not be acted on:**
- `generator-cli-hallucination` ("the prompt shows zero sample output") — sample output *is*
  injected via `cli_lookup.prompt_block`. The real defect is Phase 4's de-hyphenation.
- `stale-session-connection-bug` (the `_pt_persist` swallow) — fixed 2026-07-28; it now raises.

**Housekeeping:** two audit probes imported `db.py`, which opens `ck.db` read-write; closing them
checkpointed the 4.5 MB WAL into the main file. Lossless — schema hash and 51 sessions unchanged —
but the LFS blob differs, so `ck.db` shows modified. **Do not `git checkout` it**; that would
discard real session traffic.

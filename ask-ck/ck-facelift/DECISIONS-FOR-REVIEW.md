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

## 5. Blocked / not done, and why

| Item | Status | Reason |
|---|---|---|
| Phase −1.7 Zephyr re-push | built, not executed | your instruction: dry-run only |
| Phase 11.4 first hardware run | not attempted | your instruction: read-only bench |
| Regenerating the 53 bundles | not done | needs your sign-off on the new steps prompt (D-12) |
| `git push` | **blocked** | the push was refused by the permission layer; commits are local. **You may need to push manually, or approve it.** |

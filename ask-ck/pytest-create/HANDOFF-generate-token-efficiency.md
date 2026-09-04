# HANDOFF — Generate-phase token efficiency & rework investigation

**Created:** 2026-09-04 (by Claude, model Fable 5.1) · **Status:** OPEN — data gathered, no
changes made. This is a briefing so the next session starts from measured numbers, not a
re-derivation.

**Why this exists:** Terrence stress-tested the PyTest Creator's **per-unit** generate on
`AWPTCM-T44297` (261 Management_LLDP, ~38 units). It works, but the run cost ~$44 on the
per-unit generate alone. He asked whether we can spend fewer tokens without losing quality,
and whether the Generate → Assemble → Review → Fix shape is the right one now that all its
features exist. **Read this before touching `routers/pytest_create.py`, `pt_generate_step.jinja`,
`pt_generate_script.jinja`, or `pt_fill_rules.jinja`.** Also read `PLAN-pytest-creator.md §9.5`
(the per-unit design) and memory `pytest-creator-askck`.

**Ground rule from Terrence (CLAUDE.md):** an observation opens a conversation. Everything
below is analysis for discussion. **Do not implement any of it before agreeing the change with
Terrence.**

---

## 1. What we measured (this stress-test session, whole debug log)

Source: `CK_server/debug-log/sess-wn1ql4ajvm-mt93mbg2.jsonl`, every record carrying a `usage`
block. Re-run the extractor in §7 to refresh.

| bucket | calls | input tok | output tok | cost $ |
|---|---:|---:|---:|---:|
| **generate per-unit** (`pt_generate_step`, logged as `(verbatim)`) | 108 | 3,736,507 | 667,113 | **43.55** |
| step match (`pt_match_scripts`) | 114 | 2,463,472 | 172,123 | 17.15 |
| **whole-script** (`pt_generate_script`) | 4 | 259,317 | 160,555 | 5.60 |
| fix (`fix_script`) | 2 | 263,529 | 137,963 | 5.53 |
| gather fragments | 4 | 152,050 | 96,356 | 3.66 |
| review (`review_script`) | 2 | 138,828 | 30,077 | 2.24 |
| extract sequence | 3 | 91,703 | 21,003 | 1.02 |
| **TOTAL** | 237 | 7,105,406 | 1,285,190 | **78.76** |

Two buckets are 77% of the bill: **per-unit generate (55%)** and **step match (22%)**. Input
tokens are ~85% of all tokens, so this is an *input*-dominated workload — the lever is what we
send, far more than what comes back.

The log spans several runs of the same case (a regenerate happened during the setup-unit-indent
fix). Per full 38-unit pass ≈ **$14–15** and ≈ **1.3–1.5M input tokens**.

## 2. The caching picture — CORRECTED (my first read was wrong)

`pt_generate_step.jinja` was **already reordered on 2026-09-02** to hoist everything invariant
across a case's units into one literal shared **prefix** (intro, Case, framework surface,
devices, fill rules), with per-unit content (the unit, its blank block, fragments, CLI
reference, output format) below the line. The template header documents the measurement and
`tests/test_pt_per_unit.py` pins the ordering. **This optimization is done and working — do not
"discover" it again.**

Measured shared prefix across a real full run (extractor in §7):

| run | units | shared prefix | avg prompt | prefix share |
|---|---:|---:|---:|---:|
| full run A | 30 | 11,143 chars | 51,459 chars | 22% |
| full run B/C | 38 | 10,934 chars | 40,422 chars | 27% |

(An early 8-unit exploratory run shows only 343 chars — disregard it; it is not a clean case
pass. My pre-compaction "shared prefix is 1%" note came from mis-sampling that run. It is wrong.)

**So the true state:** ~11K chars (~2,700 tokens) — about a quarter of each prompt — is a
cacheable prefix; the other ~73% is genuinely per-unit and re-sent every call.

**The open question that actually matters (my original supposition, restated correctly):**
*does the org vLLM discount that prefix, or do we pay full freight for it 38 times?* vLLM's
Automatic Prefix Caching (APC) reuses the prefill **compute** for a shared prefix — it cuts
**latency**, but whether it reduces the **billed input tokens** depends entirely on how this
deployment meters. The debug log stores the response as text, so `cache_read`/`cache_write`
token fields are **not recoverable from it.** This is the single highest-value unknown and
step one of any real work here:

- **Check the vLLM launch flags** for `--enable-prefix-caching` (APC).
- **Capture the raw usage object** from one live per-unit call (a dry-run won't do — needs the
  transport response) and look for cache token fields / a cached-tokens count.
- If billing is flat per-token regardless of cache hits, then **caching buys latency, not
  dollars**, and every token-cost lever below is really about *sending less*, not *caching more*.

## 3. Per-unit vs whole-script — the core trade (Q3 & Q4)

Both generators exist in the tree and share `pt_fill_rules.jinja`, so a comparison is cheap.

| | whole-script (`pt_generate_script`) | per-unit (`pt_generate_step`) |
|---|---|---|
| calls per script | 1 | ~38 |
| input tok / script | ~65K (one send of shared context) | ~1.3–1.5M (shared context re-sent ~38×) |
| cost / script | **~$1.40** | **~$14–15** |
| wall-clock | ~11 min (memory `pytest-creator-askck`: 672.9 s) | faster (parallel fan-out) |
| output risk | one long generation — truncation / attention dilution across 38 classes | each unit small, focused; the `verify` contract is front-and-centre |
| integration | model emits one coherent file — assembly trivial | must splice + re-check consistency (see Q5) |
| provenance | whole-file | per-unit tags, granular regeneration |

**The ~10× cost is bought almost entirely by re-sending shared context per unit.** That is the
crux of Q4 (is single-prompt worth revisiting?) and Q1 (save tokens without losing quality).
**What we do NOT yet have is a quality head-to-head.** `tool/pt_matrix_judge.py` exists for
exactly this. The honest next step is to judge the same case built both ways (the whole-script
artifact and the per-unit artifact) rather than assert which is better. Suspicion worth
testing, not asserting: per-unit likely wins on *adherence to each step's verify contract*
(narrow prompt), whole-script likely wins on *cross-case consistency* (shared imports, helper
reuse, naming) and cost. That would make the real answer a **hybrid**, not a winner.

## 4. Terrence's six questions — current read

1. **Save tokens without losing quality (existing flow).** Biggest input sink is the per-unit
   tail (~73% of each prompt: fragments + CLI reference + device reconciliation). Levers, in
   rough value order: (a) settle the APC billing question (§2) — it may already be cheaper than
   the log implies, or not at all; (b) **dedupe fragments** — the same reviewer-approved fragment
   is embedded in every unit prompt whose step maps to it; measure how much fragment text repeats
   across the 38 prompts; (c) trim the framework-surface dump if units don't use most of it;
   (d) the **step-match** bucket ($17, 114 calls) is a whole second front — likely per-step
   matching that re-sends a large corpus context; audit it the same way.

2. **Smarter re-arrangement to save rework/tokens (now that all features exist).** The flow grew
   feature-by-feature (per-unit generate → Assemble+lint → Review → Fix, plus the setup-unit
   reindent and the Summary Fix button). Worth asking whether some Review/Fix rework is
   *self-inflicted by parallelism* (Q5) and could move left into generate/assemble. See §5.

3. **Did parallelizing reduce or increase quality vs the single prompt?** OPEN — needs
   `pt_matrix_judge.py` on both artifacts. Do not guess. (See §3.)

4. **Return to single-prompt?** Not a straight yes/no — the numbers say single-prompt is ~10×
   cheaper and coherent-by-construction but slower and truncation-prone on big scripts. A
   **hybrid** (single-prompt for small cases / a token or class-count threshold; per-unit only
   above it, or per-unit only for units that fail a whole-script pass) is the shape to price out.

5. **Does omitting Assemble+Lint retain quality — or is that step itself a deviance source?**
   Assemble+Lint is **not optional overhead for the per-unit path** — it is the *integration*
   step that catches cross-unit inconsistency that parallel generation introduces. The
   setup-unit flush-left `def` bug (fixed this session) is the textbook example: an artifact of
   generating one unit in isolation, invisible until splice. So for per-unit, Assemble+Lint is
   mandatory and *catches* deviance, it doesn't create it. For whole-script, the model emits one
   coherent file and assembly is near-trivial — which is itself an argument for Q4. Framing for
   Terrence: the Assemble+Lint requirement is a **cost of choosing parallelism**, so it belongs
   in the per-unit-vs-single ledger, not evaluated on its own.

6. **Engineer Review so it won't need a Fix re-fire.** Two classes of finding:
   - **Deterministic / lint-catchable** (indent, imports, banned stdlib modules, missing markers).
     These should never reach the LLM Review at all — catch them in Assemble/lint and fix
     mechanically (as we now do for the setup-unit indent). Every such finding that reaches
     Review is a mechanization gap.
   - **Semantic** (wrong port, wrong device handle, verify contract not honoured). These need a
     model, but they are best *prevented at generate time* — the per-unit prompt already front-
     loads the verify contract and a device-name reconciliation block; tightening those is more
     reliable than a better Review prompt. "Engineer Review to pre-empt Fix" is really **shift
     left**: prevent at generate, mechanize the deterministic catches, and leave Review/Fix for
     genuine semantics. To do this concretely, tabulate the 7 findings from this run's Review by
     class and ask of each: could generate or lint have prevented it?

## 5. My additional ideas (for discussion, not a plan)

- **Fragment de-duplication / shared fragment block.** If N units reuse fragment X, we pay for
  X's text N times. A single shared fragment appendix (in the cacheable prefix, referenced by
  tag from each unit) could move a big chunk of the per-unit tail above the line. Measure repeat
  volume first — it may or may not be large.
- **Threshold-based hybrid generate.** Pick a class-count / token threshold: below it, one
  whole-script call ($1.40, coherent); above it, per-unit. Cheapest quality-preserving win if
  the matrix judge shows whole-script is fine for small cases.
- **Two-tier Review.** Run the cheap deterministic pass (lint + structural checks) to green
  *before* spending an LLM Review call; only escalate to the LLM for units that pass structure
  but may be semantically wrong. Cuts Review token spend and pre-empts a class of Fix.
- **Scope the Fix prompt (already flagged this session).** Fix is a whole-script rewrite
  (`max_tokens=32000`); the sanity check showed it changed 9/38 classes, 29 byte-identical. A
  per-unit or per-class-scoped Fix would cost far less and can't perturb untouched classes.
  This one is close to actionable but still needs Terrence's sign-off.
- **Audit the step-match bucket separately.** $17 / 114 calls is the quiet second-biggest cost
  and nobody has looked at it. It may re-send a large corpus context per step.

## 6. Recommended order of work (when Terrence green-lights)

1. **Settle APC billing (§2).** Everything else changes meaning based on the answer. Cheap.
2. **Matrix-judge whole-script vs per-unit on `AWPTCM-T44297`** (`pt_matrix_judge.py`). Turns
   Q3/Q4 from opinion into evidence.
3. **Classify this run's 7 Review findings** (deterministic vs semantic) → answers Q6, sizes the
   "shift-left" prize.
4. **Measure fragment-text repeat across the 38 prompts** → sizes the dedupe prize (Q1).
5. Only then propose concrete changes (hybrid threshold / fragment block / scoped Fix / two-tier
   Review), each as its own discussion with Terrence.

## 7. How to reproduce every number here

```bash
cd /media/terrenceb/mnt/testbox_home/claude/Test-cases
LOG=ask-ck/CK-main/CK_server/debug-log/sess-wn1ql4ajvm-mt93mbg2.jsonl
# token buckets: sum usage by template/endpoint  (see the extractor used 2026-09-04)
# shared prefix: cluster (verbatim) prompts by >10min ts gap, common_prefix across each run
```

The exact Python for both (bucket table and prefix measurement) is in the 2026-09-04 session
transcript; re-derive rather than trust these figures if the log has grown. **Note:** the
logged `prompt` field is the rendered template only — it does **not** include any server-side
system context or reasoning tokens, and billed `input_tokens` run higher than `len(prompt)/4`,
so treat char counts as structural evidence (prefix share) and token counts as cost evidence,
never interchangeably.

## 8. State of the tree at handoff

- Generate/Assemble/Review/Fix flow is **feature-complete and green** (gate passed at wrap).
  This session added: setup-unit reindent at assembly, reachable Fix (Summary + step-7 buttons),
  post-Fix review-clear + lint-persist, pep8 warnings collapsed, clearer step-5 UI.
- No token-efficiency change has been made. This document is the only artifact of the
  investigation so far.
- Relevant memories: `pytest-creator-askck` (per-unit design + the whole-script baseline
  numbers), `setup-unit-reindent-at-assembly`.

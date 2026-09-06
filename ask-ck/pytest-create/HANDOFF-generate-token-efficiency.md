# HANDOFF — Generate-phase token efficiency & rework investigation

**Created:** 2026-09-04 (by Claude, model Fable 5.1) · **Status:** INVESTIGATED AND PARTLY
ACTED ON, same day, second session — see **§9** for what was measured, what shipped
(transport fix + `device_note` move, both approved by Terrence), the whole-script vs per-unit
judgement and the smaller-model comparison. The full write-up for review is
[`TOKEN-EFFICIENCY-REPORT-2026-09-04.md`](../../TOKEN-EFFICIENCY-REPORT-2026-09-04.md) at the
repo root. §§1, 3–5, 7–8 below are the morning's analysis and still read correctly; **§2 and
§6 were rewritten** in the afternoon because step one turned out to be aimed at the wrong
backend.

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

## 2. The caching picture — REWRITTEN 2026-09-04 (afternoon), the vLLM question was moot

**No call in this run went to the org vLLM.** All 257 debug-log records are `provider: claude,
model: opus`, through two transports: the server-side `claude -p` CLI (`claude_code`, 76 unit
calls) and the browser-brokered agent on the user's machine (`claude_agent`, 30 unit calls).
So "does vLLM's APC discount the prefix" had no bearing on this bill. The right question is what
**Claude Code's CLI** does with the prefix, and the CLI's own transcripts under
`~/.claude/projects/` answer it — they carry the raw `usage` blocks (`cache_creation_input_tokens`,
`cache_read_input_tokens`) that `llm_debug.normalize_usage` folds into a single `input_tokens`.

**Measured: the shared prefix was never read from cache. Not once, on either transport.** Every
per-unit call wrote 14k–27k tokens to the **1-hour** cache tier and read back a constant ~2.5k
(the fixed head of Claude Code's own system prompt) or 0 — independent of call order, even with
38 calls inside five minutes. The 2026-09-02 template reorder was therefore inert. Cause: the
CLI's harness system prompt sits between that head and our prompt and contains per-invocation
content, so the prefix breaks before our text begins. Probe (same 39.7k-char unit prompt, two
identical calls per configuration, from the server's cwd):

| configuration | context/call | 2nd-call cache read | cost 1st → 2nd |
|---|---:|---:|---|
| production flags as they were | 32,378 | 0 | $0.37 → $0.37 |
| + `--exclude-dynamic-system-prompt-sections` | 32,269 | 1,059 | $0.34 → $0.34 |
| + `--system-prompt <one line>` | 29,676 | **29,674 (all)** | $0.42 → $0.14 |
| + neutral cwd + `--no-session-persistence` | **16,525** | **16,523 (all)** | $0.27 → $0.11 |
| `--bare` | fails — needs `ANTHROPIC_API_KEY`, never OAuth | | |

**The harness was more than half of every call.** A trivial prompt measured 16,104 tokens from
the repo cwd against 2,602 from a bare directory: the CLI folds every CLAUDE.md above its cwd
**and the project memory index** into every call (~13.5k tokens), and `--system-prompt` does
not remove those — only a cwd outside the tree does. The memory-index half only began on
2026-09-04 at 12:19 when the memory symlinks were repaired, which made every server call ~10.5k
tokens dearer than the day before (21,865 → 32,378 for the same prompt).

**The other cap on the prefix was inside our own template.** Across the 38 real prompts the
shared prefix ended at byte 10,934 — inside the fill rules — because the per-unit
`DEVICE NAME RECONCILIATION` note (6 variants) was interpolated at rules line 72, stranding
8,400 bytes of byte-identical rules after it. The deferred `device_note` decision, priced.

**Both are fixed (Terrence approved, same day):** the CLI now runs from `llm._cli_neutral_cwd()`
with `--system-prompt` replacing the harness prompt and `--no-session-persistence`, on both
transports (the agent additionally gained `--tools ""` and `stream-json`, and the steer now
rides with the job); the device note renders below the rules in both templates. Simulated on
the 38 real prompts the shared prefix is 19,447 chars (48%, was 27%). Details: §9.

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

## 6. Recommended order of work — REWRITTEN 2026-09-04 (afternoon); STATUS 2026-09-07

> **2026-09-07:** items 2–7 below are BUILT (see §10). Item 1 ran that morning and found zero
> cache reads, which added an eighth decision — the shared half must travel as the system
> prompt — also built. The list is left as written; §10 carries the outcome.


Steps 1–4 of the morning's list are **done** (§9 and the report). What remains, in the order I
would take it, each as its own discussion with Terrence:

1. **Run one real 38-unit pass on T44297 with the shipped transport fix** and read the debug
   log's per-call `input_tokens` and the CLI transcripts' cache fields. The probe numbers are
   two-call measurements; a real fan-out (8 concurrent workers) is where the first wave misses
   the cache. Expected per-call input: ~12k written + ~8k read, against 32k written before.
2. **Deterministic integration lint at Assemble** (Q5/Q6): (a) attribute names read off a
   bound handle that `init()` never binds (`dut.portB`, `tb.ethB`, `dut.portA` when the DUT
   is `dutA`); (b) `start_tcpdump`/`stop_tcpdump` call shape against the framework surface;
   (c) a capture stopped with no wait. Three of seven Review findings in this run were these.
3. **A "self-contained unit" rule in `pt_generate_step.jinja`**: every unit establishes its
   own precondition instead of relying on the previous unit's state, because every unit's
   `tear_down` undoes it. Two of seven findings (and the whole-script generation's biggest
   structural advantage) are this.
4. **Prime the fan-out**: dispatch one unit, then the other 37 once it is streaming, so the
   first wave of eight does not all miss the cache.
5. **Fragment appendix** (Q1): 27% of all prompt text is fragment re-sends; one 6.2k fragment
   goes to 32 of 38 units. Cacheable if hoisted above the line, but every unit then reads all
   38 fragments — needs a quality check, not a guess. Middle path: hoist only fragments used
   by more than half the units.
6. **Sonnet 5 for unit fills** — the comparison in the report says it is close on the units
   sampled at ~45% of the cost, with one fatal idiom error in the setup unit; Haiku 4.5 is
   not viable. Terrence's call; a 38-unit pass on Sonnet judged in-context is the next step if
   he wants it.
7. **Per-unit-scoped Fix** and **two-tier Review** — output-side levers, unchanged from §5.

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

## 9. What happened on 2026-09-04 (afternoon session) — measured, shipped, judged

Full write-up: [`TOKEN-EFFICIENCY-REPORT-2026-09-04.md`](../../TOKEN-EFFICIENCY-REPORT-2026-09-04.md)
(repo root). Headlines:

- **No vLLM in this run**; all Opus 4.8 via the CLI. §2 above was rewritten accordingly.
- **The cache never hit** because the CLI's harness prompt (per-invocation content) sat in front
  of ours; and the harness itself — core prompt + both CLAUDE.md files + the memory index — was
  16k of every 32k-token unit call. Probe: `--system-prompt` + a neutral cwd +
  `--no-session-persistence` → 16.5k tokens/call, full cache read on the second call,
  $0.37 → $0.11.
- **Shipped (Terrence approved):** that transport change on both transports (agent also gains
  `--tools ""`, `stream-json`, and the steer rides with the job); the `DEVICE NAME
  RECONCILIATION` note moved below the fill rules in both templates (shared prefix 27% → 48%
  on the 38 real prompts). Gate 1263 passed / 1 skipped; snapshot regenerated after a reviewed
  diff.
- **Judged in-context (per Terrence: the session model is the judge):** whole-script is the
  more coherent *script* (self-contained cases, known planted values, no handle errors) but
  observes the wire only through the neighbour display and has several false-green checks;
  per-unit produces markedly stronger *units* (real captures, TLV walks, OUI checks) with three
  systematic integration defects — handle confusion in ~30/38 units, cross-unit state
  dependence in ~6, idiom divergence in ~7 — all preventable by a deterministic lint plus a
  self-contained-unit rule. So: not back to single-prompt; per-unit + shift-left.
- **Smaller models, 5 units + 4 step-matches each:** Sonnet 5 ≈ Opus on 4/5 units at 59% of
  the cost, with one runtime-fatal `self.testSet` misuse in the setup unit; Haiku 4.5 not viable
  (API inventions / wrong TLV classes on every unit). Step match: Sonnet returns Opus's
  shortlist at ~45% of the cost and a third of the latency; Haiku is slower and no cheaper.
- **Not done:** a real 38-unit pass on the new transport (step 1 of §6), the lint, the
  self-contained rule, the fragment appendix, any model switch. All are Terrence's decisions.

## 10. What happened on 2026-09-07 — the pass, the probe, and seven decisions built

- **The 38-unit pass on the new transport (decision 1)**: input 23,278 → 16,396 median tokens
  per unit call, cost $0.369 → $0.304, and every call at $10.81/M input — the 1-hour cache-WRITE
  rate. Zero reads, although two live prompts shared their first 19,456 chars (52%).
- **Probe (4 calls, $0.25):** the real shared half (~7.9k tokens) as user-block prefix → 0 read
  on a sequential second call; as `--system-prompt` → 7,879 of 8,059 read at $0.0065 vs $0.081.
  Concurrency was not the cause; block boundaries were. Step matching does NOT have the
  fan-out shape (each per-step call is one step + its own candidates), so caching gives it
  nothing — a correction to the report's first draft of decision 8.
- **Built, in Terrence's order 6, 8, 4, 3, 5, 7, 2** — one commit each on branch
  `token-efficiency-2`, fast-forwarded into `main`: per-task model routing; shared half as
  system prompt (+ `system` and raw cache fields in the debug log); primed fan-out;
  self-contained-unit rule; shared appendix at ≥ 50%; per-unit Fix + hard lint gate on
  Review; bench-integration lint (unbound port attribute, call shape vs framework surface,
  capture with no wait — the port check fires on 24 classes of the real post-Fix T44297
  script). Gate at the end: all green (backend 1336 passed / 2 skipped, frontend 250).
- **Not done:** the combined re-run itself (Terrence's), and judging its artefact in-context
  against the 2026-09-04 Opus one. Terrence chose one pass for everything over attribution.


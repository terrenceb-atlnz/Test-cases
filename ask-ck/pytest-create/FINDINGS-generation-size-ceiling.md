# Script generation has a hard output ceiling of ~15 TestCase classes

**Found 2026-07-30** during the 10-case Opus autopilot batch. Everything here is measured on
real runs; the numbers are the point, and two earlier versions of this document had the
mechanism wrong, so the evidence for each claim is stated inline.

## The ceiling

| Quantity | Value | How it was measured |
|---|---|---|
| Output cap (thinking + answer, one budget) | **32,000 tokens** | `modelUsage.maxOutputTokens` from the CLI's own JSON envelope |
| Raisable? | **No** | `CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000` leaves it at 32,000 |
| Thinking cap now applied | 2,048 | `llm._CLI_MAX_THINKING_TOKENS` |
| Usable answer budget | ~29,952 tokens ≈ **86,561 chars** | 2.89 chars/token, below |
| Density of generated Python | **2.89 chars/token** | 86,644 chars delivered for 29,952 usable tokens |
| Filled code per TestCase class | **~4,700–5,500 chars** | 88,593/16 and 42,122/9 |
| Answer tokens actually left after interleaved thinking | **~14,500** | 42,122 chars / 2.89 |
| **Working ceiling** | **~9 TestCase classes** | 42,122 chars delivered before truncation |
| Safe target | **~6 verification steps** | |

Three successive measurements on the SAME case, which is the clearest way to see it:

| Sequence steps | Delivered | TestCase classes | Complete? |
|---|---|---|---|
| 44 | 86,644 chars | 21 of ~40 | no — truncated mid-string |
| 21 | 88,593 chars | 16 of 17 | no — truncated, but **parsed cleanly** |
| 15 | 42,122 chars | 9 of 11 | no — truncated mid-comment |

Note rows 1→2: **trimming the step count did not shrink the answer.** The model writes to fill
the budget, so it simply became more verbose per TestCase (4,126 → 5,537 chars each). The
ceiling therefore has to be expressed in TestCase classes, not steps. And note row 3: the
delivered size FELL to half the budget, because interleaved thinking consumed ~20,400 tokens
that run. The usable room is not a constant.

The batch's ten refined cases produce **44–78 sequence steps** each — every one is 4–8x over.

## Why it is not simply "the artefact is too big"

Four distinct defects stacked on top of the real limit, and each one masked the next. Fixing
them changed the outcome substantially — fragments went 0 → 56, generated code 13,183 →
88,593 chars — which is why they had to be fixed before the ceiling could even be seen.

1. **`claude -p` ran as an agent.** It is the Claude *Code* CLI: with tools enabled it loops.
   A 65k-token prompt consumed **2,670,565 input tokens over 23 minutes for $4.65 and
   returned an empty result**, with `is_error: false` — surfaced as
   `502 "LLM returned no python code block."` The retry cost **$5.24** the same way. Fixed
   with `--tools ""`.
2. **Thinking was eating the whole budget.** These are reasoning models and thinking shares
   the 32,000 with the answer. A live generate was observed at **31,100 thinking tokens with
   zero answer text emitted**. Mitigated with `--max-thinking-tokens 2048` — but only on long
   calls, because passing the flag at all TURNS EXTENDED THINKING ON: the same trivial prompt
   measured **2,242ms bare vs 16,426ms with it**, which made every small call ~7x slower and
   timed out the 30s health ping.

   ⚠️ **The flag caps a single thinking block, NOT the total.** Thinking is interleaved, so a
   long generation still accumulates many blocks. Measured with the cap in force: total output
   **34,966 tokens** of which the answer was only **~14,575** (42,122 chars) — so roughly
   **20,400 tokens went to thinking despite a 2,048 cap**. This is the single most important
   correction to make when reasoning about the budget: the cap reduces thinking but does not
   bound it, so the room left for the answer is **variable between runs** and cannot be
   computed in advance. Plan for the low end.
3. **The `result` field returns only the final assistant message.** On a long answer the
   earlier messages are dropped, so what arrives is the TAIL. Measured on the same prompt:
   concatenating the streamed `assistant` text blocks yields a script beginning correctly at
   `#!/usr/bin/python3`, while `result` alone begins **mid-class** at
   `    def tear_down(self):`. Fixed by reading `--output-format stream-json` and joining
   every text block (`llm._parse_cli_stream`).
4. **The system steer contradicted the parser.** `_JSON_SYSTEM_PROMPT` says "no markdown
   fences"; `pt_generate_script.jinja` asks for a fenced python block; `_parse_generated_blocks`
   has **no unfenced fallback**. Both script-emitting steps now pass `_CODE_SYSTEM_PROMPT`.
   Separately, the caller's system message was being **dropped entirely** on this transport.

## How the overflow presents — the dangerous part

It does not error. Three different masks observed on the same case:

- **Empty result** with `is_error: false` → "no python code block" (defect 1).
- **A script that starts correctly and stops mid-string**, e.g. ending inside a string literal
  at line 1464 → lints as `IndentationError`/`unterminated string literal`, which reads as a
  bad model rather than an oversized task.
- **A script that PARSES CLEANLY but is incomplete** — the truncation landed on a statement
  boundary, so `ast.parse` succeeded, 16 of 17 TestCase classes were present, and only the
  logging-contract lint (`TestCase_16.main() has no non-empty self.passed()/self.failed()`)
  and the missing `ts.run(sys.argv)` entry revealed it. **This is the one to fear**: valid
  Python that silently tests less than it claims.

The same overflow also corrupted the **fragments** step, and there it was completely silent:
the reply arrived truncated at the head, beginning mid-string
(`test-1332.1001.py", "symbol": ...`), so `extract_json_block` returned `None`,
`_parsed_list` turned that into `[]`, and the case recorded **zero reusable fragments** —
indistinguishable from the legitimate "no reuse" outcome, which `confirm_step` accepts by
design. Two cases (T43869, T44297) carried 0 fragments into generation while step 3 had
selected 12 scripts. `gather_fragments` now raises on a parse failure; `{"steps": []}` still
flows through the legitimate empty path.

## Trimming the step count does not shrink the answer proportionally

Worth stating because it is counter-intuitive and it cost a run to learn: **the model writes
to fill the budget it is given.** The same case at 44 sequence steps produced 86,644 chars;
trimmed to 21 steps it produced **88,593 chars** — slightly more, at ~5,537 chars per
TestCase instead of ~4,126. Fewer steps bought more verbosity per step, not a smaller file.
So the ceiling must be expressed in TestCase classes, and the fill factor measured against
the largest observation (`_FILL_EXPANSION = 1.95`, above both measured 1.65 and 1.79).

## What is now in place

`_size_overflow()` in `routers/pytest_create.py` runs on the server-rendered skeleton
**before** the LLM call, so an over-budget case is refused **instantly and for free** with the
numbers and the options spelled out, instead of costing ~25 minutes and a few dollars to
produce a `SyntaxError`. It is a 409 with an explicit `acknowledge_size_overflow` override,
matching this router's existing coverage-gate pattern — a reviewer may want the partial
artefact, but it has to be a recorded choice. Prediction was checked against reality: it says
20 where the observed value was 21.

## Options, in the order I would take them

1. **Chunked generation.** The only thing that removes the ceiling. The skeleton is rendered
   server-side and is authoritative, so the seams are known in advance and the model never has
   to track them — generate per-TestCase (or in groups) and assemble. Cost: real work.
2. **Split large refined cases into several smaller ones.** Preserves total coverage across
   the set, costs nothing architecturally, and each piece then fits. This is probably the best
   near-term answer, but how to split is a test-design decision, not a mechanical one.
3. **Cap steps per refined case in the Generator.** Cheapest, and the worst: it silently trades
   away objective coverage, which is exactly what the objective-coverage gate exists to
   protect. Needs Terrence's explicit call, not a quiet default.

Do **not** attack this with timeouts or `max_tokens`: the 32,000 is the CLI's hard cap and the
same number the router already passes.

## Related fixes made the same day (all mutation-tested)

`tests/test_llm_call_timeouts.py`, `tests/test_dependencies_declared.py`,
`tests/test_claude_cli_transport.py` — 36 mutations attempted, 36 caught.

- `extract_sequence` inherited `run_prompt`'s 180s default while every sibling asked 300–600s.
- Caller timeouts were all sized for the STREAMING vLLM path, where the number bounds the gap
  *between chunks*; a headless CLI subprocess gets one shot at the whole response. Floored in
  `llm._cli_timeout`, with `_is_long_call()` as the single predicate that also gates the
  thinking cap so the two cannot disagree.
- `paramiko` was declared in no requirements file, so PyTest Creator's "6. Run" step was dead
  on a fresh venv and reported it as an SSH failure. Declared; tb470 now probes
  `ssh/framework/sudo` all true.
- `lib2to3` was removed from the stdlib in Python 3.13 — the version this project targets — so
  D3 py2→py3 fragment translation had silently stopped working (`status: "unavailable"`, 1
  flagged fragment, 0 translated). Now falls back to the maintained fork `fissix`.

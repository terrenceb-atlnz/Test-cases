---
name: claude-code-cli-transport-contract
description: The claude_code (headless `claude -p`) transport needs --tools "" + stream-json + --system-prompt (REPLACE, not append — 2026-09-04) + a neutral cwd + --no-session-persistence + a thinking cap; AND the shared text must be in `system`, not a user-block prefix, or the cache never hits (2026-09-07); the "~9-20 TestCase class output ceiling" is REFUTED — it was a fence-parser defect discarding self-chunked replies
metadata:
  type: project
  verified: 2026-09-07
---

**Extended again 2026-09-07 — the cache matches only at CONTENT-BLOCK boundaries.** With the
harness gone, 38 unit prompts sharing their first 19,456 chars still read ZERO tokens from cache
(sequential and parallel alike — every call at the 1-hour write rate, inferred from price and
then probed). The CLI's breakpoints sit on the system prompt and on the user message; a shared
prefix inside one user block whose tail differs can never hit. Probe: shared half in the user
block → 0 read; the same half as `--system-prompt` → 7,879 of 8,059 read at 1/12 the price. So a
caller who wants caching must put the shared text in `system` and only the varying part in the
prompt — `routers.pytest_create._PT_PROMPT_SPLIT` / `_split_unit_prompt` do this for the unit
prompt; the debug log records `system` and the raw cache fields since the same day. See
[[prompt-cache-needs-block-boundaries]].

**Contract extended 2026-09-04 (measured, shipped, mirrored in `ask-ck/agent/ck_agent.py`):**
`claude -p` is a HARNESS. Left to its defaults it prepends its own ~2.6k-token system prompt
plus every CLAUDE.md above its cwd and the project memory index (~13.5k tokens from this repo),
writes all of it to the 1-hour cache tier on every call, and — because that harness prompt
carries per-invocation content — **no call ever reads the previous call's cache**. The
2026-09-02 template prefix reorder was inert until this was fixed. Three flags/settings, all
now unconditional in `_call_claude_code_headless` and pinned in `tests/test_claude_cli_transport.py`
+ `tests/test_ck_agent_transport.py`:

- **`--system-prompt <steer>`** REPLACES the harness prompt (the bullet below saying
  `--append-system-prompt` is the 2026-07-30 state and is superseded). With `--tools ""` there is
  nothing for the harness context to drive. Same prompt twice: appended $0.37 → $0.37, cache read
  0; replaced $0.42 → $0.14, all 29,674 tokens read.
- **cwd = `llm._cli_neutral_cwd()`** (system temp dir): nothing to auto-discover. Trivial prompt
  from the repo cwd 16,104 tokens, from a bare dir 2,602.
- **`--no-session-persistence`**: a completion is not a session (66 transcripts/day otherwise).
- **`--bare`** is NOT an option on a seat: it reads only `ANTHROPIC_API_KEY`, never OAuth.
- `--exclude-dynamic-system-prompt-sections` did NOT restore caching on its own (1,059 read).

Full numbers: `TOKEN-EFFICIENCY-REPORT-2026-09-04.md` (repo root).

**Transport runner changed 2026-08-26 (contract unchanged, re-verified same day):** the CLI
paths now run via **`llm._run_cli`** (Popen + stdin/stdout/stderr pump threads), not
`subprocess.run` — for live stream-json progress (llm_inflight) and a TRUE kill on user
cancel (process group, SIGTERM→SIGKILL). Semantics preserved exactly: same timeout-kill,
same >64 KiB stdin safety, same CompletedProcess shape. **Tests that fake the CLI must
monkeypatch `llm._run_cli` (kwargs `input_text`, `timeout`), not `llm.subprocess.run`** —
all 25 transport-contract pins passed unchanged after the fixture repoint. Everything below
still binds: it is about what reaches the CLI and how its reply parses, not how it is spawned.

`claude -p` is the Claude **Code** CLI — an agent, not a completion endpoint. Four things must
be true or it silently corrupts output (all found + fixed 2026-07-30, `llm.py`):

- **`--tools ""`** — without it the CLI loops. Measured: 2,670,565 input tokens / 23 min /
  **$4.65** returning an **empty result** with `is_error: false`, surfaced as the misleading
  `502 "LLM returned no python code block."`
- **`--output-format stream-json` + concatenate every `assistant` text block.** The `json`
  format's `result` field holds **only the final assistant message**, so a long answer loses
  its HEAD and you get a mid-class tail that lints as `IndentationError`.
- **Pass the caller's `system`** — as `--append-system-prompt` from 2026-07-30 (it used to be
  dropped entirely); **as `--system-prompt` since 2026-09-04**, see the top of this memory.
  Note `_JSON_SYSTEM_PROMPT` forbids markdown fences, which is wrong for the two
  script-emitting templates — they need `_CODE_SYSTEM_PROMPT`.
- **`--max-thinking-tokens`, but only on long calls.** Passing it at all TURNS THINKING ON:
  2,242ms → 16,426ms on a trivial prompt, which times out the 30s health ping.

## The "output ceiling" was REFUTED on 2026-08-03 — it is a parser defect

This memory previously asserted a hard ceiling of ~9–20 TestCase classes. **That is wrong.**
Replaying the five stored `pt_generate_script` / `pt_fix_script` replies in
`CK_server/debug-log/no-session.jsonl` through the real
`routers/pytest_create.py:883 _parse_generated_blocks` regex:

| reply | model emitted | parser kept | `ts.run(sys.argv)` in reply |
|---|---|---|---|
| 06:47:37 | 173,351 chars / **42 classes** | 86,656 / 21 | yes |
| 07:00:16 | 96,070 / 17 | 88,602 / 16 | yes |
| 07:25:59 | 48,702 / 12 | 42,331 / 9 | yes |
| 07:48:13 | 37,674 / 6 | 37,661 / 6 | yes |
| 07:56:58 (the "D15 regression") | 49,546 / 6 | 25,171 / **0** | yes |

**Every reply is complete.** Nothing truncated. The CLI splits a long answer across assistant
messages and each part re-opens a ```` ```python ```` fence; the non-greedy `(.*?)``` ` in the
regex stops at the *continuation's opening* fence, so everything after part 1 is discarded —
often mid-token, which is what made it look like model truncation. Verified seam at offset
25,181 of the 07:56:58 reply: it cuts inside `self.log('LLDP transmit interval in effect: {}`
and the next part re-emits that same partial line.

The model **cooperates**: it labels each part (`# ---- continuation … part 2: TestCase_21
onwards ----`) and closes with plain-English assembly instructions, including which duplicate to
discard. The parser throws that away too.

Consequences: **42 classes were delivered in one call**, so there is no ~20-class ceiling.
`_size_overflow`'s three constants are fitted to *parser output*, not model output, despite the
docstring claiming "ALL THREE CONSTANTS ARE MEASURED". D15 ("the fix pass made it worse") is the
same defect. Recovery is **not** uniform: a naive join fixes 07:00:16, line-level de-duplication
additionally fixes 07:56:58, and 06:47:37 re-emits a whole partial *class* — so assembly must
work at class granularity.

## FIXED 2026-08-03c — and two facts about this transport that cost a session to learn

Assembly now lives in `CK_server/gen_assembly.py` (`recover_script`), which recovers all five
replies **completely** — every class registered by `ts.add_testCase(...)` defined, carrying a
`main()`, and parsing. Generation **refuses** a reply that did not reassemble instead of
persisting a partial script behind an HTTP 200.

**1. 32,000 output tokens bounds ONE MESSAGE, not the answer.** Measured `output_tokens` on
the stored multi-message generations: **67,326 / 66,334 / 57,188 / 34,966** — all over the
"hard cap", all complete scripts. The size gate built on that premise is deleted. So there is
no ceiling to design around: a long answer simply continues into the next message.

**2. `stop_reason` is USELESS for detecting truncation here.** Captured live against CLI
2.1.207 with `CLAUDE_CODE_MAX_OUTPUT_TOKENS=200`: it is `null` on **every genuine assistant
message, including the ones that hit the cap**. The only truthy value in the stream sits on a
message the CLI *synthesizes* to carry the error, whose `id` is a UUID rather than `msg_…`,
and it reads `stop_sequence` — never `max_tokens`. The real signal is on the terminal
`result` event: `is_error` + `terminal_reason == "api_error"` + `"output token maximum"` in
the result text. That synthesized message's text also gets concatenated into the answer, so
it must be filtered out or English prose lands on the end of the generated script.
Structural captures are committed at `tests/fixtures/cli_stream_*.jsonl`.

**How to apply:** before blaming a model for short or broken generated output, **replay the
raw reply from `debug-log/*.jsonl` and count what the model actually sent** — any artefact
stored before 2026-08-03c is parser output, not model output. The debug-log is gitignored
(`.gitignore:70`), so that evidence is local-only and disposable; the committed fixtures are
not. The ceiling tables in `ask-ck/pytest-create/FINDINGS-generation-size-ceiling.md` and
`autopilot/RESULTS-2026-08-03.md` record parser output and carry that correction. Related:
[[vllm-reasoning-model-path]], [[workspace-llm-default-gotcha]], [[generator-cli-hallucination]],
[[mutate-before-you-claim]], [[silent-degradation-audit-2026-07-30]].

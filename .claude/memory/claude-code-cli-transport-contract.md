---
name: claude-code-cli-transport-contract
description: The claude_code (headless `claude -p`) transport needs --tools "" + stream-json + system passthrough + a thinking cap; the "~9-20 TestCase class output ceiling" is REFUTED — it was a fence-parser defect discarding self-chunked replies
metadata:
  type: project
---

`claude -p` is the Claude **Code** CLI — an agent, not a completion endpoint. Four things must
be true or it silently corrupts output (all found + fixed 2026-07-30, `llm.py`):

- **`--tools ""`** — without it the CLI loops. Measured: 2,670,565 input tokens / 23 min /
  **$4.65** returning an **empty result** with `is_error: false`, surfaced as the misleading
  `502 "LLM returned no python code block."`
- **`--output-format stream-json` + concatenate every `assistant` text block.** The `json`
  format's `result` field holds **only the final assistant message**, so a long answer loses
  its HEAD and you get a mid-class tail that lints as `IndentationError`.
- **Pass the caller's `system`** via `--append-system-prompt` (it used to be dropped entirely).
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

**How to apply:** before blaming a model for short or broken generated output, **replay the raw
reply from `debug-log/*.jsonl` and count what the model actually sent** — the stored artefact is
parser output, not model output, so every downstream measurement inherits the defect. Note the
debug-log is gitignored (`.gitignore:70`), so this evidence is local-only and disposable.
See `ask-ck/ck-facelift/PLAN-pipeline-end-to-end.md` Phase 7; the ceiling table in
`ask-ck/pytest-create/FINDINGS-generation-size-ceiling.md` and `autopilot/RESULTS-2026-08-03.md`
records parser output and should be read with that correction in hand. Related:
[[vllm-reasoning-model-path]], [[workspace-llm-default-gotcha]], [[generator-cli-hallucination]],
[[mutate-before-you-claim]].

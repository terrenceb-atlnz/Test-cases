---
name: claude-code-cli-transport-contract
description: The claude_code (headless `claude -p`) transport needs --tools "" + stream-json + system passthrough + a thinking cap; and generation is capped at ~9-20 TestCase classes because thinking shares the 32k output budget
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

**The output ceiling (the thing that actually blocks generation):** 32,000 tokens shared
between thinking and answer, not raisable. The thinking flag caps **one block, not the total** —
measured 20,400 thinking tokens under a 2,048 cap. Generated Python is ~2.89 chars/token and a
filled TestCase is 4,700–5,500 chars, so the working ceiling is **~9–20 TestCase classes and it
varies run to run**. Above it the script truncates *without erroring*, and sometimes truncates on
a statement boundary so it **parses cleanly while silently testing less than it claims**.

**Why:** four separate masks for one cause cost most of a session to unpick. `_size_overflow()`
in `routers/pytest_create.py` now gates it for free before the call.

**How to apply:** before blaming a model for bad generated output, check the artefact's SIZE
against the budget. See `ask-ck/pytest-create/FINDINGS-generation-size-ceiling.md` and
`autopilot/RESULTS-2026-08-03.md`. Related: [[vllm-reasoning-model-path]],
[[workspace-llm-default-gotcha]], [[generator-cli-hallucination]].

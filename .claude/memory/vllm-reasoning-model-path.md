---
name: vllm-reasoning-model-path
description: Org vLLM (vllm-fast/thinking) are REASONING models; llm.py hardened for their reasoning_content behavior
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6c4c3b5d-20a2-4e93-8a92-519e908e14e6
  modified: 2026-07-20T23:27:06.128Z
---

**The org vLLM models (`vllm-fast` AND `vllm-thinking`, at `http://vllm.ai.atlnz.lc/v1`, OpenAI-compatible, `auth_method=local_llm`) are reasoning models.** They spend completion tokens on hidden chain-of-thought returned in `message.reasoning_content` BEFORE emitting the real answer in `message.content`. This is the single biggest gotcha when working with Ask-CK's LLM path and caused three separate bugs (fixed 2026-07-21, commits `e6c0d64` + `1ccf1a7`, all in `CK_server/llm.py`):

1. **`max_tokens` must be generous.** The legacy 2000 was exhausted mid-reasoning → `content` came back `null` (`finish_reason=length`). Now 16000 for `local_llm`. If you see empty/`NoneType` LLM results, suspect the cap first.
2. **Never assume `content` is a non-null string.** The parser now guards null/empty/truncated content, raises a clear `finish_reason=length` error, and falls back to `reasoning_content`.
3. **Send a system message.** `resources.md` documents the vLLM usage as a **system + user** pair. `run_prompt` now prepends a default JSON-only steer (`_JSON_SYSTEM_PROMPT`) — this skips the model's scratchpad and cut completion tokens ~35% on real prompts (~22× on trivial ones), and made the model actually honor prompt rules it had been drowning in reasoning. OpenAI path uses a `system` role; Anthropic native uses the top-level `system` field. Override per call via `run_prompt(..., system=...)`; pass `""` for none (the health-ping sends none).

4. **The vLLM path STREAMS (2026-07-22b).** Because the reasoning phase emits `reasoning_content` for an arbitrarily long time before any answer bytes, a non-streaming call has nothing to reset its HTTP read clock and read-times-out on big-output steps (`vllm-thinking` × `generate_script` failed even at a 600s static floor). The OpenAI-compatible branch of `_call_llm_raw` now sends `stream:true` + `stream_options:{include_usage:true}` and consumes the SSE body, accumulating `content`/`reasoning_content` deltas + final `finish_reason`/usage into the SAME triplet the non-streamed path built (all guards + token badges unchanged). Effect: the `read` timeout now bounds the gap BETWEEN chunks, not the whole response — a reasoning pass of any length completes as long as chunks keep flowing (verified: a 30s-read-timeout call ran 21+ min). Also learned: **`vllm-fast` is ALSO a reasoning model** (it streamed `reasoning_content` for ~21s before the answer on a real prompt) — the fast/thinking difference is reasoning-phase *duration*, not reasoning-vs-not. Anthropic native path left non-streaming (no such failure). `max_tokens` is also now overridable per call (`generate_script`/`fix_script` request 32000).

**Why:** these facts aren't obvious from a glance at the code or the vLLM docs, and the tiny health-ping prompt masks all of them (it always fit under the cap and returns fast), so a headless vLLM run looked fine while every real templated call failed. A future session touching the LLM path or debugging "the vLLM returns nothing" / "the vLLM call times out" needs this.

**How to apply:** when adding LLM calls, go through `run_prompt` (gets the system steer + guards for free). When debugging empty vLLM output, check `finish_reason` and `reasoning_content` in the debug-log (`GET /api/llm/recent`) before assuming the backend is down. Related: [[pytest-creator-llm-config-bug]] (wrong-backend bug), [[db-only-single-source]].

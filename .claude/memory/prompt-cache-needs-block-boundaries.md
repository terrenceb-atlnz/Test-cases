---
name: prompt-cache-needs-block-boundaries
description: A shared PREFIX inside one user message never caches — the API matches only at content-block boundaries/breakpoints, so shared text must be the SYSTEM prompt (or its own block); measured 2026-09-07 on 38 calls (0 read) + a 4-call probe (0 vs 7,879 read)
metadata:
  type: project
  verified: 2026-09-07
---

**A shared prefix is not a cacheable prefix unless it ends at a content-block boundary.** On
2026-09-07 the first 38-unit pass on the harness-free CLI transport shared 19,456 chars (52%)
across its unit prompts and read **0** tokens from cache on every call — sequential or parallel,
first wave or last. Every call priced its input at exactly $10.81/M, the Opus 1-hour cache-WRITE
rate. Two probes, 5 s apart, same real shared half (~7.9k tokens): in the **user block** the
second call wrote 8,089 and read 0; as **`--system-prompt`** it wrote 180 and read 7,879, $0.081
→ $0.0065. Concurrency (decision 4, priming) explains the first wave only, never the rest.

**Why:** the API checks for a cache hit at the client's `cache_control` breakpoints and the
content-block boundaries before them. The Claude Code CLI places its breakpoints on the system
prompt and on the (single-block) user message. Our system prompt was a 30-token steer (below the
1,024-token minimum) and our whole prompt was one user block whose tail differed per unit, so
neither breakpoint could ever match. The 2026-09-04 "same prompt twice" probe passed only because
the entire block was identical.

**How to apply:** when N calls share text, render the shared part into `system` (≥ 1,024 tokens)
and send only the varying part as the user turn. In Ask-CK the per-unit prompt renders a visible
split marker (`_PT_PROMPT_SPLIT`) and `_unit_call_and_store` splits there; the per-unit Fix
reuses the same shared half so it reads the generation's cache. Verify with the debug log's
`cache_read_input_tokens` (recorded since 2026-09-07) — never infer from price again. Do NOT
expect it for call classes that lack the shape: per-step script matching sends one step + its own
candidates, so there is nothing shared to cache. Related: [[claude-code-cli-transport-contract]],
[[prompt-examples-are-the-spec]].

---
name: workspace-llm-default-gotcha
description: Headless curl to LLM endpoints 502s unless the _workspace_llm default is local_llm — the §9 re-sync makes the workspace default authoritative over per-case config
metadata: 
  node_type: memory
  type: project
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-07-27T01:10:33.063Z
---

Since the §9 stale-`llm_config` fix, the **workspace default (`_workspace_llm` row in
`ck.db` sessions) is authoritative** — it overwrites a case session's `llm_config` at
dispatch whenever the backends diverge. So a case row reading `local_llm`/`vllm-fast`
tells you nothing; dispatch may still re-sync it to the workspace value.

Symptom when the workspace default is a headless CLI mode (`claude_agent` etc.) and you
call an LLM endpoint by curl:
`502 {"detail":"ERROR: Claude-agent mode needs a browser session id but none was provided."}`
— instant (~0.07s), not an LLM timeout.

**Fix (the app's own supported path, no DB surgery):**
`curl -X POST localhost:8000/api/wizard/set_llm_config -H 'Content-Type: application/json' \
  -d '{"provider":"openai","auth_method":"local_llm","model":"vllm-fast"}'`

**Why:** this cost real debugging time and reads like the §7.3 bug returning, but it is
the §9 fix working as designed. Note it changes the default the browser UI sees too.

**How to apply:** before any headless/scripted LLM run, check the `_workspace_llm` row
first, not the per-case `llm_config`. See [[pytest-creator-llm-config-bug]] and
[[part3-grading-session]].

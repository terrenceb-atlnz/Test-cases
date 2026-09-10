---
name: workspace-llm-default-gotcha
description: Since 2026-09-10 the LLM choice is PER SEAT (X-CK-LLM header); a headless curl with no header gets the SITE DEFAULT (`_workspace_llm` row), which only POST /api/wizard/set_site_default_llm writes — plain set_llm_config writes nothing; a Claude-mode default 502s "needs a browser session id" for headless callers
metadata:
  type: project
  verified: 2026-09-10
---

**How dispatch resolves the backend (2026-09-10, PLAN-seat-setup-and-per-seat-llm.md §5):**
`llm_config.effective_llm_config` = the request's `X-CK-LLM` header (the seat's choice,
sent by the browser from `localStorage.draftingLLMConfig`) → else the **site default**
(the `_workspace_llm` row) → else the session's own stored copy. Nothing writes a session
any more. So a case row's `llm_config` tells you nothing about what a request will use.

**Symptom when the site default is a Claude mode and you call an LLM endpoint by curl
(no header):**
`502 {"detail":"ERROR: Claude-agent mode needs a browser session id but none was provided."}`
— instant (~0.07s), not an LLM timeout.

**Fix (the app's own supported path, no DB surgery) — either:**
- send the seat header on your curl: `-H 'X-CK-LLM: local_llm;vllm-fast'` (per request,
  changes nothing stored), or
- change the site default:
  `curl -X POST localhost:8000/api/wizard/set_site_default_llm -H 'Content-Type: application/json' \
    -d '{"provider":"openai","auth_method":"local_llm","model":"vllm-fast"}'`
  Note: `set_llm_config` no longer does this — it validates and echoes for the seat only.

**Why:** the old model (workspace row authoritative for everyone, `apply_workspace_llm`
re-syncing every session) is exactly how one seat flipped every seat on demo day; per-seat
closed it. This cost real debugging time twice, and reads like a bug both times.

**How to apply:** before any headless/scripted LLM run, decide which of the two above you
want. Check the site default with `GET /api/wizard/llm_config` (`scope: site_default`).
See [[claude-agent-is-the-release-transport]] and [[pytest-creator-llm-config-bug]].

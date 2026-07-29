---
name: llm-health-check-button
description: "Requested feature — a Health Check button next to the Local LLM \"key stored\" note that pings the endpoint for a hello"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1f9e36f4-a5b5-4411-a4d1-2f252538a06b
  modified: 2026-07-19T21:11:02.562Z
---

**Requested 2026-07-20 (not yet built):** Terrence wants a **Health Check button on the Configure page, on the second line next to the "key stored ✓" note** ([static/index.html:299](ask-ck/CK-main/CK_server/static/index.html#L299), the `#localLlmKeyState` span in `#localLlmRow`). Clicking it should ping the configured Local LLM endpoint and confirm it's up and returning a hello (or equivalent minimal completion), surfacing HTTP status / error inline.

**Why:** the vLLM endpoint (`http://vllm.ai.atlnz.lc/v1`) was returning 500s (`litellm.InternalServerError`) during testing even though Ask-CK's config resolved correctly — see [[pytest-creator-llm-config-bug]]. A one-click health check separates "my config is wrong" from "the backend is down" without having to fire a real synthesize and read the debug footer.

**How to apply (suggested design):** new backend endpoint (e.g. `POST /api/wizard/llm_health` or `/api/llm/health`) that server-side resolves the current workspace LLM config + `get_local_llm_key()`, sends a minimal `max_tokens`~8 "reply OK" completion via the same `_call_llm_with_meta` choke point (so it's recorded in debug-log too), and returns `{ok, http_status, model, latency_ms, error}`. Frontend: a small button in `#localLlmRow` next to `#localLlmKeyState`; wire via `registerActions` in `js/llm.js` (NOT window); show spinner → ✓ "up (Nms)" / ✗ error. Keep it provider-agnostic so it works for any auth_method, not just local_llm. Manual test per [[user-prefers-manual-ui-testing]].

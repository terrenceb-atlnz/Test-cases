---
name: pytest-creator-llm-config-bug
description: PyTest Creator was silently sending prompts to the wrong LLM backend; fixed by centralizing workspace-LLM apply into _llm_cfg
metadata: 
  node_type: memory
  type: project
  originSessionId: 1f9e36f4-a5b5-4411-a4d1-2f252538a06b
  modified: 2026-07-19T20:44:08.951Z
---

**Bug (found + fixed 2026-07-20):** PyTest Creator LLM endpoints (`extract_sequence`, `suggest_scripts`, `assess_fit`, `gather_fragments`, `generate_script`, `fix_script`) in `CK_server/routers/pytest_create.py` dispatched via `run_prompt(..., llm_config=_llm_cfg(sess))` but **`_apply_workspace_llm(sess)` was only called in `load_case`** (one place). A session with a stale/inactive persisted `llm_config` fell through to `run_prompt`'s default backend (`claude_agent` → api.anthropic.com), silently ignoring the user's configured `local_llm`/vLLM. Surfaced by the new LLM-transparency debug-log: a live T33233 `extract_sequence` recorded `auth_method=claude_agent`, `model=default`, error "local Claude agent did not respond in time" — while `/api/wizard/llm_config` said `local_llm`/`vllm-thinking`.

**Fix:** folded `if _apply_workspace_llm(sess): _pt_persist(sess)` into `_llm_cfg(sess)` itself ([pytest_create.py:106](ask-ck/CK-main/CK_server/routers/pytest_create.py#L106)), so every current/future endpoint gets the correct backend at dispatch — impossible to forget. Mirrors the wizard's per-call `_apply_workspace_llm_if_needed`. Verified: a no-config session now resolves to local_llm/vllm-thinking/openai. **Uncommitted** in working tree (Terrence commits himself).

**Why:** this is the danger pattern — a per-call "apply workspace login if session has none" step that's easy to place in the load path but forget on the dispatch path. The wizard does it right (inside each LLM handler); PyTest Creator originally didn't.

**Full audit (2026-07-20): the SAME bug class was latent in the wizard too.** `_session_llm_cfg` and three inline `session_dict.get("llm_config")` reads (suggest_atp, synthesize_objectives, synthesize_steps, legacy synthesize, coverage-gaps/export) all read raw config without applying the workspace LLM — only `load_case` (wizard.py:610) applied it. Worked in practice because the wizard's confirm-gated flow persists an active config before you reach a synthesize button, but it would break if you changed the Configure-page backend mid-session without reloading. **Fixed by hardening `_session_llm_cfg` to apply-and-persist** (wizard.py:1103) and routing all synthesize/suggest/coverage endpoints through it. `load_case`→analyze_atp (wizard.py:644) already safe (apply precedes read at 610). Both routers verified: a no-config session now resolves to local_llm/vllm-thinking/openai. Both routers' changes uncommitted.

**How to apply:** whenever adding a new LLM endpoint to any Ask-CK router, resolve the config through a helper that applies the workspace LLM (`_llm_cfg` in pytest_create, `_session_llm_cfg` in wizard), NEVER read `sess.llm_config`/`session_dict.get("llm_config")` raw. The transparency layer ([[pending-approved-plans]] LLM-observability) is the tool that catches regressions like this — check `auth_method`/`model` in the debug footer against the configured backend. See [[user-prefers-manual-ui-testing]].

# Ask-CK: LLM-Request Observability (debug footer, per-session log, token accounting)

> ## Session handoff (read first)
>
> **Status (2026-07-20): EXECUTED + committed** (Step 0 + Commit 1 + Commit 2 shipped in `66fb289`; the DB migration was then built on top). A 5-dimension adversarial review ran; its verify agents were killed by a session limit, so findings were adjudicated against live code by hand. **6 real fixes applied post-review:** (1) `secrets.local.json` written 0600 not 0644; (3/6) `recordLLMDebug` wired into `ptGatherFragments` (`pt-frag-btn`) and `exportBundle` (footer-only — export runs coverage-gaps LLM) — **12 LLM handlers wired total, not 10**; (4) `local_llm` added to `restoreLLMUI` sessionActive allow-list; (5) footer store keyed by `rec.panel` (server X-CK-Panel attribution) not `S.currentPanel` at resolve time; (7) key-state note restored on load, not only after Apply. Rejected: the "credential shadows case-key `key`" finding (speculative; no live URL-from-credential path).
>
> **Follow-on work (2026-07-20 later session — committed in `47833de`):** this observability layer immediately paid off — it caught the PyTest/wizard LLM-config bug (see `ask-ck/pytest-create/PLAN-pytest-creator.md` + memory `pytest-creator-llm-config-bug`). Three features grew out of it, documented in SERVER-README (earlier "UNCOMMITTED" note was superseded — all three shipped in `47833de` "Ask CK: Local LLM post-review fixes + cold-load status + admin panel + fast restart"):
> - **Health check button** (Configure page): `POST /api/wizard/llm_health` + `_health_ping` pings the selected model via the real path. Distinguishes bad-config from backend-down.
> - **LLM Provenance + dry-run** (permanent portability feature; debug-log stays dev-only): every LLM panel gets a copyable, live-`Refresh` prompt preview via a `dry_run` flag that renders 1-for-1 without sending (verified byte-identical + no-tokens). New `static/js/provenance.js`. Memory: `llm-provenance-portability`.
> - **Token badge format** relabelled `N in / M out (total)` (was the ambiguous `17→179 tok`) via one shared `fmtTokens`.
> Future: when the tool matures, the debug-log can be removed; Provenance (session-stored + dry-run) is the durable replacement.
>
> **Status (2026-07-16):** Plan approved by Terrence. **Step 0 (below) added 2026-07-16** — a new `local_llm` (org vLLM) auth method + Fast/Thinking toggle; execute it FIRST, then Commit 1, then Commit 2. No code written yet.
>
> - **The ES-module split has LANDED and is committed** (HEAD `3d8eced`, tree clean). `static/app.js` is GONE — the frontend is 14 ES modules under `static/js/` (entry `main.js`, loaded `type="module"` with `?v=N` cache-bust). So **all frontend line numbers in Commit 2 below are stale**; re-target onto modules per the map in `static/js/README.md`. Confirmed relocations: fetch patch → `js/session.js:16-32` (already sets `X-CK-Session`); `currentPanel` → `S.currentPanel` (`js/state.js`); `goToPanel` → `js/nav.js`; the new frontend section becomes its **own module `js/llm-debug.js`** registered in `main.js`; button wiring goes through `registerActions({...})` in the owning module (`generator.js` / `pytest.js`), NOT `window`. Bump `?v=1`→`?v=2` on the main.js tag when shipping Commit 2.
> - **Backend anchors re-verified against HEAD `3d8eced` (2026-07-16) — all unchanged:** llm.py:37 `current_session_id`, llm.py:250 `_call_llm_with_meta`, catch-all :376, main.py:57-67 `_bind_session_id`, includes :81-85, paths.py:16 `CK_SERVER_DIR`. Commit 1 lands as written.
> - **Requirements source:** Terrence's three asks, verbatim intent — (1) hideable per-page footer showing last LLM request incl. failures, updated every request, not persisted across browser sessions; (2) per-session LLM request log stored in `debug-log/`; (3) token counts on every log entry AND next to the pressed LLM button on success, to compare model efficiency/output quality.
> - **Settled decisions — don't re-litigate:** surface debug info via a separate `GET /api/llm/recent` endpoint, NOT embedded in existing responses (pytest error paths 502 before a body exists); per-page = per-`currentPanel`, attributed via a new `X-CK-Panel` header; token counts shown honestly as `— tok` where the transport doesn't report usage (Grok CLI plain output, agent bridge) — never estimate/fabricate; badge updates only on success; footer hidden on panels with no LLM activity.
> - **Sibling plans in this directory** (all approved, none executed): `PLAN-es-module-split.md` (app.js → ES modules) and `PLAN-db-migration.md` (SQLite). This plan is written against **current single-file app.js** — if the ES split lands first, put the frontend section in its own module (`js/llm-debug.js`) instead of a comment-fenced app.js section; the backend half is unaffected. If this lands first, the new app.js section is deliberately self-contained so the split lifts it cleanly. The SQLite plan may later absorb the JSONL log — schema kept flat on purpose; do not couple now.
> - **Environment:** server via `ask-ck/CK-main/run.sh` (uvicorn :8000); LLM calls need real credentials (`LLM_API_KEY` or claude/grok CLI logins) — for verification steps that exercise failures, an intentionally invalid api key is the cheapest path. Verification is **manual by preference** (no Playwright); curl steps for the backend commit are in the Verification section.
> - **Secrets rule:** the recorder must whitelist meta fields — `api_key` must never reach `debug-log/`; verification step 1 greps for it.

## Context

Ask-CK's frontend-triggered LLM prompts are opaque: no way to see what was sent, what came back, what it cost, or why a request failed (quota/rate-limit bodies are discarded today). This adds three things:

1. A **hideable footer** (cloning the existing `#session-debug` `<details>` pattern, [index.html:684-687](ask-ck/CK-main/CK_server/static/index.html#L684)) showing the last LLM request **per panel** — including failures — updated every request, not persisted across sessions.
2. A **per-session JSONL log** of all LLM requests in a new `CK_server/debug-log/` directory (gitignored).
3. **Token annotation**: every log entry carries tokens spent; a token badge appears next to the LLM button that was pressed after a successful request.

**Key verified facts:**
- All five LLM transports funnel through `_call_llm_with_meta` ([llm.py:250](ask-ck/CK-main/CK_server/llm.py#L250)), which **never raises** (catch-all at :376 returns `meta` with `error: True`) — safe to rename-and-wrap.
- Token usage is **already present but unread** in `raw_response` for: Anthropic HTTP (`usage.input_tokens/output_tokens`, llm.py:316-341), OpenAI/Grok HTTP (`usage.prompt_tokens/completion_tokens/total_tokens`, :343-374), Claude Code CLI JSON envelope (`usage`, `total_cost_usd`, :169-227). **Not available** for Grok CLI plain-text (:107-166) and the agent bridge (`{content,error}` contract, agent_jobs.py:83) — show `— tok`, never fabricate.
- HTTP 429/402 error bodies are discarded today (only `str(e)` kept at llm.py:376) — preserve them.
- `current_session_id` ContextVar (llm.py:37, set from `X-CK-Session` by middleware main.py:57-67) is the only session key available at the choke point.
- Wizard endpoints return 200-with-error-in-provenance; pytest endpoints raise HTTPException(502) — so surfacing debug info via a **separate GET endpoint** (not embedded in responses) works uniformly for both, including failures.
- `ptLintScript` and `ptValidate` are mechanical (no LLM) — excluded. `model` may pass through as literal `"default"` in some paths — cosmetic, note only.

## Step 0 — New `local_llm` auth method (org vLLM) + Fast/Thinking toggle

**Added 2026-07-16, execute before Commit 1.** A third LLM radio: the organization's self-hosted, API-driven vLLM endpoint. It is OpenAI-shaped, so it rides the existing OpenAI HTTP path (llm.py:343-374) with **no new transport** — and because that path reads `usage.prompt_tokens/completion_tokens`, this provider will show **real in→out token counts** in the Commit 2 badges (unlike grok_cli / claude_agent, which honestly show `— tok`).

**Settled decisions (don't re-litigate):**
- **auth_method = `local_llm`** → forces `provider="openai"`, `base_url="http://vllm.ai.atlnz.lc/v1"`.
- **Two modes via the `model` field:** `vllm-fast` (default) / `vllm-thinking`, chosen by a Fast/Thinking toggle shown only when the Local LLM radio is selected.
- **Credential = a gitignored, app-owned `CK_server/secrets.local.json`** (shape `{"local_llm_key": "sk-..."}`), with **env var `LOCAL_LLM_KEY` as fallback**. Resolved server-side only — it must NEVER be sent from the browser, stored on the session/`cfg`, or reach `debug-log/`. Because it lives in a file and is injected server-side (never in `cfg`), Commit 1's meta-key whitelist excludes it for free. Do NOT reuse the human-authored `secrets.md` — that stays user-owned and holds only `JIRA_KEY` (used by `tool/upload_refined.py`, not the server). This is why the app writes its own JSON file, not `secrets.md`.
- **Key is updatable from the Configure page** (keys expire): a key field + Save writes `secrets.local.json`. This satisfies "persist across server restart AND new browser session, without re-entering every time" while staying per-server. The key never rides a request.
- **UI label:** radio reads "Local LLM"; the sub-toggle reads "Fast / Thinking".
- Source of truth for the endpoint shape: `resources.md` (org example).
- **Future central-deploy extension (NOT built now, documented so it's not a surprise):** for true multi-seat/bring-your-own keys, the same Configure field flips to browser `localStorage` + a per-request `api_key`; at that point Commit 1's `debug-log` recorder must explicitly whitelist that field OUT. Today's single-user instance uses the server-side file, which is per-server-global by design (one seat).

**Backend edits:**
- **New tiny helper (put in a sensible existing module, e.g. `paths.py` or a new `local_llm_key.py`):**
  ```python
  LOCAL_LLM_SECRETS = CK_SERVER_DIR / "secrets.local.json"   # gitignored
  def get_local_llm_key() -> Optional[str]:
      try:
          import json
          if LOCAL_LLM_SECRETS.exists():
              k = json.loads(LOCAL_LLM_SECRETS.read_text()).get("local_llm_key")
              if k: return k
      except Exception: pass
      return os.environ.get("LOCAL_LLM_KEY")   # fallback
  def set_local_llm_key(key: str) -> None:
      import json
      LOCAL_LLM_SECRETS.write_text(json.dumps({"local_llm_key": key}))
  ```
- **`llm.py` — inject centrally in `_call_llm_with_meta` (:250), NOT at the ~6 call sites.** Right after the provider-defaults block (~:285), before the `meta = {...}` dict is built:
  ```python
  if auth_method == "local_llm":
      provider = "openai"
      base_url = "http://vllm.ai.atlnz.lc/v1"
      model = model or "vllm-fast"
      api_key = get_local_llm_key()   # file → env fallback; server-side only, never from cfg/browser
  ```
  It then falls straight through the existing OpenAI-compatible branch (:343-374). `model` (`vllm-fast`/`vllm-thinking`) flows through from `cfg.model` unchanged. This one edit covers every caller (:542, :595, :833, :865, :897, :929, and run_prompt :997) at once — none of them need touching. If `api_key` is None, the existing no-credential guard (:303-312) already errors cleanly.
- No change to the catch-all (:376) or the token normalizer (Commit 1's `normalize_usage` already handles the OpenAI `usage` shape).

**Router edits — `routers/wizard.py:set_llm_config` (:1595-1613):**
- Add `local_llm` to the auth_method allow-list at :1605: `("api_key", "account", "claude_code", "claude_agent", "grok_cli", "local_llm")`.
- Add a guard alongside the others (:1607-1610): `if auth_method == "local_llm" and provider != "openai": provider = "openai"` (coerce rather than 400 — the radio always pairs them, but be defensive).
- Model default (:1621-1629): when `auth_method == "local_llm"` and no model supplied, `cfg.model = "vllm-fast"`. **Never** put the key in `cfg` — it lives only in `secrets.local.json`, resolved at call time.
- **Accept a key on save:** if `auth_method == "local_llm"` and the body carries a `local_llm_key` (non-empty), call `set_local_llm_key(...)` to persist it, then **drop it from the body** — it must not land in `cfg`, the session, or the returned `safe_config`.
- `has_key`/status (:1649): treat `local_llm` as configured when `get_local_llm_key()` returns truthy; surface `local_llm_key_set: bool` in the returned config (mirroring the grok_cli `available` pattern) so the Configure page can show a clear "Local LLM key not set" warning and whether a key is already stored (never echo the key itself).

**Frontend edits (ES modules):**
- **`static/index.html`** (radio block ~:272-275): add a third radio `value="local_llm"` labelled "Local LLM", and a `#localLlmRow` (hidden by default) containing (a) the Fast/Thinking control — paired radio/segmented toggle `name="localLlmMode"`, values `vllm-fast` (checked) / `vllm-thinking`; and (b) an optional key field `#localLlmKey` (type=password, placeholder "Local LLM API key — leave blank to keep stored key") + note showing whether a key is already stored. Place near `#llmModel`.
- **`js/llm.js`** — `updateAuthMethodUI()` (:132-155): extend the show/hide to reveal `#localLlmRow` (and hide the grok/agent instruction panels) when `local_llm` is selected. In `setLLMConfig()` (:7): when the Local LLM radio is checked, set `provider='openai'`, `auth_method='local_llm'`, `body.model =` the checked `localLlmMode` value; and **only if** `#localLlmKey` is non-empty, `body.local_llm_key = <field>` (then clear the field on success so the key isn't left in the DOM). `updateLLMStatus()` (:81): add a branch, e.g. `Using Local LLM (vLLM — Fast|Thinking)`, and a warn state when `local_llm_key_set` is false. `restoreLLMUI()` (:157): restore the radio + Fast/Thinking toggle from saved `auth_method`/`model` (the key field always restores blank — it's write-only from the UI's perspective, like the old api_key never round-tripped).
- No `session.js` change for Step 0 (that fetch-patch edit belongs to Commit 2's `X-CK-Panel`).

**`.gitignore` (repo root):** add `ask-ck/CK-main/CK_server/secrets.local.json`.

**`run.sh` / SERVER-README:** no export needed — the key is read from `secrets.local.json` (set via the Configure page) with `LOCAL_LLM_KEY` env as an optional fallback for headless/CI. Add a one-line SERVER-README note: "Local LLM key is set on the Configure page (stored gitignored in `CK_server/secrets.local.json`); or export `LOCAL_LLM_KEY` for headless runs."

**Verification (manual + curl):**
- S0.1 — select Local LLM, enter the key once + Fast, apply → status "Using Local LLM (vLLM — Fast)"; `secrets.local.json` now exists with the key; a Generator synthesize returns real content.
- S0.2 — flip to Thinking, apply (key field left blank) → the stored key is reused (no re-entry) and the request uses `model=vllm-thinking` (confirm server log line `model=vllm-thinking`).
- S0.3 — **restart the server, open a fresh browser tab** → status still shows Local LLM configured (key persisted across restart + new session); synthesize works without re-entering the key.
- S0.4 — direct curl parity with the `resources.md` example against `http://vllm.ai.atlnz.lc/v1/chat/completions` returns `choices[].message.content` and a `usage` block (this is what Commit 2's badge will read).
- S0.5 — remove `secrets.local.json` (and unset `LOCAL_LLM_KEY`) → Configure shows "key not set" warning; a call errors cleanly via the normal error shape (no stack trace, no key leak).
- S0.6 — after a successful call, `grep -rn local_llm_key sessions/` and inspect the `/set_llm_config` JSON response → **the key appears in neither** (only `secrets.local.json` holds it). Re-run the `debug-log/` grep at Commit 1 verification step 1.

**Critical files (Step 0):** modified `CK_server/llm.py`, `CK_server/routers/wizard.py`, `CK_server/paths.py` (or new `CK_server/local_llm_key.py`), `CK_server/static/index.html`, `CK_server/static/js/llm.js`, repo-root `.gitignore`, `CK-main/SERVER-README.md`. New (runtime, gitignored): `CK_server/secrets.local.json`.

## Commit 1 — Backend: recorder + debug-log + /api/llm endpoints

**paths.py**: add `DEBUG_LOG_DIR = CK_SERVER_DIR / "debug-log"`.

**New `CK_server/llm_debug.py`**:
- `normalize_usage(auth_method, raw_response) -> dict | None` returning `{input_tokens, output_tokens, total_tokens, cost_usd}`: Anthropic shape (also covers claude_code envelope; fold `cache_read/creation_input_tokens` into input; `total_cost_usd` → cost_usd), OpenAI shape, tolerant `raw["usage"]` probe for agent-bridge, `None` for grok CLI (comment: future — investigate `grok --output-format json`). Everything try/except → None; telemetry must never break a call.
- `record(meta, duration_ms) -> dict`: builds record from a **whitelist** of meta keys (never api_key/llm_config), reads session from `llm.current_session_id`, panel from new `current_panel_id` ContextVar, endpoint from new `current_request_path` ContextVar; `request_id = uuid4().hex[:12]`; appends one line to `DEBUG_LOG_DIR/<session-id or 'no-session'>.jsonl` (lazy mkdir, `open(..., "a")` O_APPEND single-line writes); pushes into per-session in-memory ring buffer (`deque(maxlen=20)`, evict oldest sessions beyond ~50); wrapped try/except-print.
- `recent(session_id, limit) -> list[dict]`.

**JSONL record schema** (flat, deliberately columnar so the pending SQLite plan can absorb it later):
`ts, request_id, session_id, panel, endpoint, template, provider, auth_method, model, base_url, duration_ms, usage{...}|null, error, error_detail, prompt (full), response (full), content_chars`.

**llm.py**:
- Add ContextVars next to line 37: `current_panel_id`, `current_request_path`.
- Rename `_call_llm_with_meta` → `_call_llm_raw` (unchanged); new thin `_call_llm_with_meta(same signature, plus template="")`: time with `time.monotonic()`, call raw, set `meta["usage"] = normalize_usage(...)`, `meta["template"]`, call `llm_debug.record(meta, duration_ms)`. All existing callers (llm.py:48, :548, :638, :700, :848, :873, :906, :951, :997) untouched and auto-instrumented.
- Error-body preservation in the catch-all at :376: if `isinstance(e, requests.HTTPError) and e.response is not None`, set `meta["error_detail"] = e.response.text[:2000]` and append first ~300 chars to the `content` error message (quota/rate-limit reasons then surface in wizard provenance and pytest 502 details too).
- Template attribution: `run_prompt` (llm.py:997) passes `template=template_name`; the wizard-side call sites (:548, :638, :700, :848, :873, :906, :951) pass their phase/template names.

**Agent bridge (optional usage, server-tolerant)**: `agent_jobs.py:77` deliver gains `usage=None` param; line 83 → `job.result = {"content": content, "error": bool(error), **({"usage": usage} if usage else {})}`. `routers/agent_bridge.py:44` passes `body.get("usage")`. The out-of-repo ck-agent can adopt later; normalizer already probes `raw["usage"]`.

**New `routers/llm_debug.py`** mounted at `/api/llm` (main.py, next to the other includes at :81-85):
- `GET /recent?limit=20` — ring-buffer records for the caller's `X-CK-Session`, prompt/response truncated to ~20k chars each (full text lives in JSONL). Returning last-K (not last-1) lets the frontend pick the newest record matching its panel — handles concurrent calls in one session.
- `GET /log` — returns the session's JSONL contents (404 → `{"records": []}`); the per-session log viewable without shell access.

**main.py middleware** (:57-67): set/reset `current_panel_id` (from new `X-CK-Panel` header) and `current_request_path` (from `request.url.path`) in the same try/finally as the session ContextVar. ContextVar propagation into `run_in_threadpool` is safe — same mechanism `current_session_id` already relies on.

**.gitignore** (repo root): add `ask-ck/CK-main/CK_server/debug-log/`.

## Commit 2 — Frontend: footer, per-panel store, token badges

**index.html**:
- Footer as sibling directly after `#session-debug` (:687):
  ```html
  <details id="llm-debug" class="session-debug hidden">
    <summary class="session-debug-summary">Last LLM request (this page) <span id="llm-debug-tag" class="badge hidden"></span></summary>
    <pre id="llm-debug-view" class="session-pre"></pre>
  </details>
  ```
- Add ids to the five id-less wizard LLM buttons: `tl-suggest-llm-btn` (:323), `zp-suggest-llm-btn` (:340), `atp-suggest-llm-btn` (:357), `obj-synth-btn` (:382), `steps-synth-btn` (:406). PyTest buttons already have ids.

**app.js** — one new comment-fenced section (after the ptApi block ~:1571; keep self-contained except `currentPanel`/`goToPanel` refs, so the pending ES-module split lifts it cleanly):
- `const llmDebugByPanel = {};` — plain object; dies with the page (satisfies "not session-to-session").
- Fetch patch (:16-32): inside the existing `/api/` branch also set `X-CK-Panel: currentPanel`.
- `fmtTokens(usage)`: `null → '— tok'`, else `'1,234→356 tok'` (input→output; abbreviate ≥10k as `12.3k`).
- `setTokenBadge(btnEl, usage)`: reuse/insert sibling `span.badge.llm-token-badge` after the button; `.badge-success` when usage present, plain badge `'— tok'` when null (grok CLI / agent paths). **Badge only updates on success** — failures go to the footer + existing alert/statusEl paths.
- `async recordLLMDebug(btnEl)`: fetch `/api/llm/recent?limit=5`; pick newest record with `rec.panel === currentPanel` (else newest overall); skip if `request_id` already stored for this panel; store, `renderLlmDebugFooter()`; if `btnEl && !rec.error` → `setTokenBadge(btnEl, rec.usage)`.
- `renderLlmDebugFooter()`: no entry for `currentPanel` → hide `#llm-debug` (matches `#session-debug` precedent; non-LLM panels stay clean). Else unhide and fill `#llm-debug-view`: header line `ts · endpoint · template · provider/model via auth_method · duration · tokens`, `⚠ ERROR` line + `error_detail` on failure, then `--- PROMPT ---` / `--- RESPONSE ---` full texts; `#llm-debug-tag` shows token summary or `ERROR`.
- Hook `goToPanel` (:1433): after the session-debug toggle at :1453-1454, call `renderLlmDebugFooter()`.
- Call `recordLLMDebug(document.getElementById('<btn-id>'))` in the finally/after path of **10 handlers** (+1 optional): `suggestTestLinkWithLLM` (:2416), `suggestZephyrWithLLM` (:2478), `suggestATPWithLLM` (:2540), `synthesizeObjectives` (:1042), `synthesizeSteps` (:1065), `ptExtractSequence` (:1703, `#pt-seq-extract-btn`), `ptSuggestScripts` (:1792, `#pt-suggest-btn`), `ptAssessFit` (:1850, `#pt-fit-btn`), `ptGenerateScript` (:1965, `#pt-gen-btn`), `ptFixScript` (:2152, `#pt-fix-btn`); optional `loadCase` (:41, `null` btn — `analyze_atp_coverage` may run an LLM during case load, footer-only).

**styles.css** (near badge block :868): `.llm-token-badge { margin-left: 6px; vertical-align: middle; }` and `.llm-debug-error { color: var(--status-low, #ef4444); }`. Everything else reuses `.badge`, `.badge-success`, `.session-debug*`, `.session-pre`.

## Verification (manual — no Playwright)

Backend (commit 1, `./run.sh`, curl only):
1. POST an LLM endpoint with `-H 'X-CK-Session: sess-test1' -H 'X-CK-Panel: panel-pt-seq'` → `debug-log/sess-test1.jsonl` gains a line with ts/request_id/panel/endpoint/template/model/duration_ms/usage/prompt/response; **grep the file for the api key — must be absent**.
2. `GET /api/llm/recent` with the same session header returns the record.
3. Invalid api key → record has `error: true` + `error_detail` with the provider's 401/429 body; endpoint still returns its normal error shape (pytest 502 / wizard 200+provenance).
4. No session header → lands in `no-session.jsonl`, no server error.

Frontend (commit 2, hard reload, console open):
5. Press each button type (a wizard suggest, a synthesize, pt extract/suggest/fit/generate/fix) → token badge appears next to the exact pressed button on success.
6. API-key provider shows `in→out tok`; grok_cli / claude_agent shows `— tok`.
7. Per-panel isolation: LLM action on step-1, another on panel-pt-fit, switch between them → footer shows each panel's own request; panel-main shows no footer.
8. Broken key: wizard button (alert path) and pt button (statusEl path) → footer shows ERROR record with preserved provider body; no badge change.
9. Tab refresh → footer store empty (per-page state gone) while `debug-log/<session>.jsonl` retains history; new tab → new session file.
10. `git status` clean (debug-log gitignored); no console errors throughout.

## Risks / notes

- **JSONL growth**: full prompts run 10–50 KB (generate_script embeds fragments); a heavy session reaches a few MB. Acceptable for a debug aid; rotation out of scope (docstring note).
- **Secrets**: recorder whitelists meta fields; `meta` never contains the credential (verified at llm.py:287-293); verification step 1 double-checks.
- **Concurrency**: per-session files + O_APPEND single-line writes; `/recent` last-K + panel matching handles in-session concurrent calls.
- **Pending plans** (note, don't couple): ES-module split will lift the new app.js section into a module — keep it comment-fenced and self-contained. SQLite migration could later absorb the JSONL log as a table — schema is flat on purpose.
- Grok CLI / agent bridge report no usage — badge shows `— tok` honestly; bridge protocol extended server-side to *accept* optional usage when the ck-agent client adds it.

## Critical files

- Modified: `CK_server/llm.py`, `CK_server/main.py`, `CK_server/paths.py`, `CK_server/agent_jobs.py`, `CK_server/routers/agent_bridge.py`, `CK_server/static/index.html`, `CK_server/static/app.js`, `CK_server/static/styles.css`, repo-root `.gitignore`
- New: `CK_server/llm_debug.py`, `CK_server/routers/llm_debug.py` (+ runtime `CK_server/debug-log/`)

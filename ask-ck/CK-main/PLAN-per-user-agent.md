# PLAN — Per-User Local Agent for Ask CK LLM Calls

**Status:** IMPLEMENTED + end-to-end verified. 2026-07-14.

> **PARTLY SUPERSEDED 2026-08-26 — the UI half only; the mechanism below is untouched.**
> This plan removed server-local `claude_code` from the Configure UI and mapped a stored
> `claude_code` onto the `claude_agent` radio on restore (see the Frontend bullet below, and
> §"kept but relabelled"). That remap has been **deleted** and `claude_code` now has its own
> radio, *"Claude Code CLI (this server)"* — see
> [`PLAN-llm-mode-selection.md`](PLAN-llm-mode-selection.md) (Option A, decided by Terrence).
>
> Why: hiding the mode never stopped a server on `claude_code` from spending the server's
> seat; it only stopped the UI from saying so. The remap made the radio report
> `claude_agent` while the server ran `claude_code`, which also kept `ckBrokerLoop()` running
> in a mode that can never be handed a job — every tab long-polling `/api/agent/next` forever.
>
> **Everything else here still holds and is still the right design**: the agent, the job
> registry's per-session partitioning, the `127.0.0.1`-only bind, and `claude_agent` as the
> mode that keeps each user on their own seat. The reversal is about which modes the UI
> *offers*, not about how any of them work. Body text below is left as written — it is an
> accurate record of 2026-07-14.

## Implementation summary (all phases done)
- **Agent** (`ask-ck/agent/ck_agent.py`, stdlib): `/health` + `/run`, binds 127.0.0.1:8765, CORS to server origin, no token. + `run-agent.sh`, `README.md`.
- **Server**: `agent_jobs.py` (per-session job registry, blocking submit + timeout); `routers/agent_bridge.py` (`/api/agent/next` long-poll, `/result`, `/status`); `llm.py` gained `claude_agent` branch (`_call_claude_agent`), a `session_id` param, and a `current_session_id` ContextVar; `main.py` middleware binds the `X-CK-Session` header to that ContextVar + mounts the bridge router. Blocking LLM calls in `wizard.py`/`pytest_create.py` are now `await run_in_threadpool(...)` so the agent long-poll stays serviceable (no event-loop deadlock).
- **Frontend** (`static/index.html`): per-tab `CK_SESSION_ID` + `window.fetch` patch injecting `X-CK-Session` on `/api` calls; `claude_agent` Configure radio (replaces server-local `claude_code` in the UI) + "Check my local agent"; `ckBrokerLoop()` long-polls → local agent → posts result; legacy `claude_code` maps to `claude_agent` on restore.
- **Validation gaps fixed**: `set_llm_config`, `_llm_is_active`, model-default logic all accept `claude_agent`.
- **Verified**: real end-to-end on this machine — shared server → browser broker → local ck-agent → **real `claude`** → back, producing 10 sequence steps for AWPTCM-T33233 in 35s. Job-registry unit tests (round-trip, timeout, session-active) pass. All Python + JS syntax clean.

---

## Original design (as built)


## Goal

Let Ask CK run as **one shared local webpage** (e.g. `http://ck-box.lan:8000`) while
each user's LLM requests execute against **their own local Claude Code CLI login /
subscription seat** — never sharing a seat through the server. This keeps the tool
on-side with Anthropic's per-seat subscription terms for a multi-user deployment.

## Why the current design can't do this

Today `_call_claude_code_headless` ([llm.py:163]) runs `claude -p` as a subprocess on
the **server** host, as the **server's** OS user, against the **server box's** single
CLI login. A browser cannot hand its machine's CLI seat to a remote server. So on a
shared server the CLI path is inherently single-seat. (See PLAN discussion / SERVER-README
Claude section warning.)

## Architecture: browser-brokered local agent

The server never runs `claude` for `claude_code` sessions. Instead, the LLM call is
**executed on the user's own machine** and the result handed back through the browser
that is already talking to both.

```
        ┌─────────────────────────── user's laptop ───────────────────────────┐
        │                                                                      │
        │   ck-agent (localhost:8765)  ──runs──▶  claude -p  (user's own seat) │
        │        ▲                                                             │
        │        │ localhost fetch (prompt in / completion out)               │
        │   browser tab ──────────────────────────────────────────────────────┼──▶ shared Ask CK server
        │        │  (long-poll: "any prompts for me?" ── POST completion back) │      (UI, data, prompts,
        └────────┼─────────────────────────────────────────────────────────────      sessions; NO claude)
                 │
        The browser is the only thing that can reach BOTH the shared server
        and the user's own localhost agent, so it brokers between them.
```

### Components

1. **`ck-agent`** — a tiny local HTTP service the user runs on their own machine
   (`ask-ck/agent/ck_agent.py`, stdlib-only, ~120 lines). Endpoints:
   - `GET  /health` → `{ok, claude_cli: <found?>, logged_in_hint}` (used by the browser to confirm the agent is up before offering claude_code).
   - `POST /run` `{prompt, model, timeout}` → runs `claude -p --output-format json` on
     stdin exactly as the server does today, returns `{content, error}`.
   - CORS locked to the shared server's origin; binds `127.0.0.1` only (never `0.0.0.0`).
   - Optional shared secret (`CK_AGENT_TOKEN`) so only the intended page can drive it.
   The agent reuses the *exact* subprocess logic from `_call_claude_code_headless` so
   behaviour/JSON parsing is identical — factor that into a shared helper both import.

2. **Server: a new `auth_method` value `"claude_agent"`.**
   - When a session's config is `claude_agent`, the server does **NOT** call claude.
     Instead the LLM call becomes an **async job**: the server enqueues
     `{job_id, prompt, model}` against that session and returns "pending" to the caller.
   - New endpoints on a small `routers/agent_bridge.py`:
     - `GET  /api/agent/next?session=<sid>` — browser long-polls: returns the next
       queued prompt job for this session (or 204).
     - `POST /api/agent/result` `{job_id, content, error}` — browser posts the
       completion back; server resolves the pending job.
   - The existing synchronous callers (`run_prompt`, `synthesize_*`, `suggest_*`) block
     on an `asyncio.Event`/queue until the browser delivers the result (with the same
     `timeout` they already pass). No caller signatures change — only
     `_call_llm_with_meta`'s `claude_agent` branch changes *where* the work runs.

3. **Frontend: an agent-broker loop in `static/index.html`.**
   - When the user picks **"Claude Code CLI (my local machine)"** in Configure, the page
     first `fetch('http://127.0.0.1:8765/health')` to confirm their agent is running.
   - While that mode is active, a background loop long-polls `GET /api/agent/next`; on a
     job it `POST`s the prompt to `http://127.0.0.1:8765/run`, then `POST`s the result to
     `/api/agent/result`. Purely client-side; no seat data ever touches the server.
   - Per-session: the browser tab owns one `session_id`; the server routes each user's
     jobs only to that tab. Alice's prompts go to Alice's agent, Bob's to Bob's.

### Why this is genuinely per-user and unshared
- `claude -p` only ever runs on the **user's own machine** against **their own login**.
- The shared server sees prompts and completions (as it does today) but **never a
  credential, token, or seat** — there is nothing to share.
- No user can consume another user's seat: jobs are keyed to the originating session,
  and each browser only talks to its own `localhost` agent.

## Coexistence with existing modes
- `api_key` (per-session key) and `grok_cli` stay as-is. `grok_cli` has the *same*
  shared-seat caveat on a shared server — document that it's for single-user hosting
  or gets the same agent treatment later (out of scope for v1).
- `claude_code` (server-local CLI) is **kept** but relabelled in the UI as
  "Claude Code CLI (this server host) — single-user only" so shared deployments don't
  pick it by accident. `claude_agent` is the new shared-safe option.

## Files
- **New** `ask-ck/agent/ck_agent.py` — the local agent (stdlib http.server).
- **New** `ask-ck/agent/run-agent.sh` + `ask-ck/agent/README.md` — one-command start + setup.
- **New** `CK_server/routers/agent_bridge.py` — `/api/agent/next` + `/api/agent/result`, job queue.
- **New** `CK_server/agent_jobs.py` — in-memory per-session job registry + asyncio result plumbing.
- **Edit** `llm.py` — factor `claude -p` subprocess into a shared `_run_claude_subprocess()`
  (imported by both the agent and the server); add the `claude_agent` branch in
  `_call_llm_with_meta` that enqueues instead of running locally.
- **Edit** `main.py` — `include_router(agent_bridge_router, prefix="/api/agent")`.
- **Edit** `static/index.html` — Configure radio for `claude_agent` + the broker loop +
  agent health check; per-tab `session_id`.
- **Edit** `SERVER-README.md` — new "Shared deployment (per-user local agent)" section.

## Security notes
- Agent binds `127.0.0.1` only; CORS + optional token restrict who can drive it.
- Server still logs prompts/responses in provenance exactly as today (no new secret exposure).
- The shared server should still run behind the LAN only (nginx note already exists).

## Effort / phasing
- **Phase 1** — `ck_agent.py` + shared `_run_claude_subprocess()` refactor; prove the agent
  runs `claude -p` identically to the server. (No server behaviour change yet.)
- **Phase 2** — `agent_jobs.py` + `agent_bridge.py` + the `claude_agent` branch in `llm.py`;
  server enqueues and blocks for results.
- **Phase 3** — frontend broker loop + Configure UI + health check; relabel `claude_code`.
- **Phase 4** — docs, and an end-to-end test with two browsers / two agents on one server.

## Decisions (signed off 2026-07-14)
1. **Agent port `8765`; no shared-secret token.** Security = bind `127.0.0.1` only + CORS
   restricted to the shared server's origin. (Any local process on the user's own machine
   could call the agent — accepted, since it can only spend that same user's seat.)
2. **Remove server-local `claude_code` from the UI entirely.** New users see only
   `claude_agent` (shared-safe), `api_key`, and `grok_cli`. Legacy stored `claude_code`
   configs still deserialize (mapped gracefully) but are not offered to new users. The
   server-local `_call_claude_code_headless` code path stays for that back-compat but is
   never selected via the UI.
3. **Stdlib-only agent** (`http.server` + `subprocess`). User setup = run one script; no
   pip install. The shared `claude -p` subprocess logic is duplicated minimally rather than
   imported, to keep the agent dependency-free from the server package.

# PLAN — Honest LLM mode selection in the Configure panel

**Status: OPTION A IMPLEMENTED 2026-08-26.** Terrence chose **Option A** — `claude_code` is now
a first-class radio, *"Claude Code CLI (this server)"*. The diagnosis in §§1–3 was re-verified
against a live browser before any edit and reproduced **exactly**: server `auth_method` =
`claude_code`, radio checked = `claude_agent`, the "Check my local agent" button and the agent
instructions both visible, `/api/agent/next?wait=25` in flight, and the status line the only
element telling the truth. See §4 for what shipped and §5 for what was deliberately left.

Written 2026-08-20 after the active LLM mode was silently reverted to a non-working backend
**three times in one session** on a LAN-exposed server.

**Related design docs — read before changing anything here:**
[`PLAN-per-user-agent.md`](PLAN-per-user-agent.md) (why `claude_agent` exists and why
`claude_code` was kept out of the UI), and the `SUPPORTED_AUTH_METHODS` comment in
`CK_server/models.py`, which describes that set as *"a governance control rather than a
convenience list"*.

Line numbers below are **as of 2026-08-20** and are hints only — prefer the symbol names.

---

## 1. Symptom

On a shared server exposed to the LAN, a remote seat performing any LLM action gets:

```
ERROR: local agent unreachable - is ck-agent running? Type error: Failed to fetch
```

Observed on objective synthesis from `10.33.25.50`. The request itself returns **200** — the
error text *is* the LLM output, propagated honestly — so nothing looks broken server-side:

```
GET  /api/agent/next?session=sess-lfhgg3jue7n-…   200   job handed to that tab
POST /api/agent/result                             200   the error string sent back
POST /api/wizard/synthesize_objectives             200   "succeeded"; content = the error
```

## 2. Why it happens (working as designed)

The workspace was on `claude_agent`, which is **browser-brokered to the client's own
localhost**. The tab POSTs the prompt to `http://127.0.0.1:8765` — resolved on *that* machine.
A remote seat has no `ck-agent`, so the fetch is refused.

This is deliberate and correct. `ck_agent.py` binds `127.0.0.1` only ("never `0.0.0.0`", per
its signed-off plan), and jobs are partitioned per browser session in
`agent_jobs.AgentJobRegistry` (`_queues: Dict[str, Deque[_Job]]`, with `session_id` *"enforced
on deliver"*). So **no locally-run agent can service another seat's prompt** — not a limitation
to work around, but the mechanism that keeps each user on their own Claude seat.

The mode that works for a shared server is **`claude_code`**: the server runs `claude -p`
itself, no browser in the path, nothing to install on any client. It is fully supported in the
backend and in `SUPPORTED_AUTH_METHODS` — it is simply **not offered in the UI**.

## 3. Root cause of the recurrence

### 3a. The radio misreports the active mode

`restoreLLMConfigUI` in `static/js/llm.js` (**llm.js:299**) rewrites the value before it
touches the DOM:

```js
if (method === 'claude_code') method = 'claude_agent';  // server-local CLI removed from UI
```

Consequences for every tab while the server is on `claude_code`:

| Element | Shows | Reality |
|---|---|---|
| Radio | "Claude Code CLI (my local machine)" **checked** | server-side `claude_code` |
| "Check my local agent" button | visible, clickable | fails — no ck-agent on that box |
| Agent instructions panel | visible | irrelevant |
| Status line | "Using Claude (Claude Code CLI)" | **correct** — reads the real `auth_method` |

So the status line and the radio disagree, and only the radio is wrong.

### 3b. The lie defeats the broker-loop guard

Fixed in `b544f5e`, but **currently ineffective**:

1. `method` is remapped to `claude_agent` (3a).
2. **llm.js:345** — `if (method === 'claude_agent') ckBrokerLoop();` fires on the remapped
   value, starting the loop.
3. `ckAgentModeActive()` (**agent.js:31**) returns
   `am === 'claude_agent' || (radio && radio.value === 'claude_agent')`. The real
   `auth_method` is `claude_code`, so the first term is false — but the radio was just checked
   by the remap, so it returns **true** and the loop persists.

Every tab therefore long-polls `/api/agent/next` forever and is never handed a job. Five tabs
were observed doing exactly this. Fixing 3a fixes this at the same time; no separate change is
needed.

### 3c. Any seat's Apply rewrites the mode for everyone

`set_llm_config` in `routers/wizard/config.py` calls `save_global_llm(cfg)`
**unconditionally** (**config.py:212**), *before* the case-session branch:

```python
# Remember as workspace default so future case loads keep this LLM choice
save_global_llm(cfg)

# Also apply to the case session when one is loaded/known
if sess:
```

So the case-scoped form `POST /api/wizard/set_llm_config/{key}` also overwrites the **global**
workspace default. Combined with 3a, every Apply from any seat writes `claude_agent` — the
broken value — for all seats.

Evidence from `.ck-server.log`, two different remote seats:

```
1334  10.33.12.10   POST /api/wizard/set_llm_config/AWPTCM-T44318   200
1916  10.33.25.50   POST /api/wizard/set_llm_config/AWPTCM-T44318   200
2001  10.33.25.50   POST /api/wizard/set_llm_config/AWPTCM-T44318   200
```

The mode is persisted in `ck.db` (`sessions` row `id='_workspace_llm'`, via
`llm_config.save_global_llm` → `db.save_workspace_llm`), so a revert survives restarts. It is
**global, durable, and writable by any client** with no authentication.

### 3d. Net effect

Setting the working mode by API is a stopgap, not a fix:

```bash
curl -s -X POST http://127.0.0.1:8000/api/wizard/set_llm_config \
  -H 'Content-Type: application/json' \
  -d '{"provider":"claude","auth_method":"claude_code","model":"opus"}'
```

Verified working each time (`llm_health` → `ok: true`, ~3.6 s, real Opus completion,
`cost_usd` ≈ 0.064). It held **~18 minutes** on the last attempt before being overwritten. It
reverted three times on 2026-08-20.

## 4. The decision to make — **DECIDED: Option A (2026-08-26)**

> **Outcome.** Terrence chose **Option A**. Every row of its table below shipped, plus three
> items the table did not anticipate:
>
> - **3b needed no separate change.** `ckBrokerLoop()` is started off the same `method` value
>   the remap corrupted, so deleting the remap stopped the loop by construction. Measured
>   after the change: **0** requests to `/api/agent/next` on a `claude_code` workspace, where
>   before there was a 25-second long-poll per tab, forever.
> - **The model row's *restore* was gated on `claude_agent` too**, not just its visibility.
>   Showing the row under `claude_code` therefore exposed a second disagreement: the row read
>   **Sonnet** (the markup default) while the stored model was **opus**. That is the same
>   class of lie this plan exists to remove, so `restoreLLMConfigUI` now covers both Claude
>   modes. Verified: server `opus` → row `opus`.
> - **The panel's `section-description` was rewritten.** It asserted that the Claude option
>   "runs against **your own** Claude seat via the local agent — seats are never shared",
>   which stops being true the moment a second Claude mode exists. It now states plainly
>   which of the two spends whose seat.
>
> The reversal is recorded where §4 required it — the `claude_code` entry in `models.py` and
> the `auth_method` list in `routers/wizard/config.py` — and both records say *why*: hiding
> the mode never prevented the server-seat spend, it only stopped the UI from reporting the
> active mode honestly.
>
> **Half of §3c remains, and the distinction matters.** Option A closes the trap this plan was
> written about: Apply can no longer write a *broken* value, because the radio it reads is no
> longer a lie — that is the sense in which §4 below says both options "close the Apply trap".
> What is untouched is the structural half: `save_global_llm(cfg)` at `config.py:212` is still
> called unconditionally, so a **case-scoped** `POST /api/wizard/set_llm_config/{key}` still
> rewrites the **global** workspace default for every seat, with no authentication in front of
> it. A wrong value can no longer originate in the UI; any seat can still change the mode for
> everybody. Out of the chosen scope — see §5, still open.

The two options differ in whether they **reverse a signed-off design decision**. Both close the
Apply trap and both fix 3b. This is a judgement call about seat spending, not a technical
toss-up.

The decision being weighed is recorded in two places, and both would have to change under
Option A:

- `models.py:98` — *"NOT offered in the UI — interactive use would spend the SERVER's seat, the
  very thing claude_agent exists to avoid."*
- `routers/wizard/config.py:141` — *"single-user hosting only, not offered in the UI."*

### Option A — give `claude_code` its own radio

Makes it a first-class, round-trippable UI choice. Survives an Apply, needs no curl. **Reverses
the decision above**: server-seat spending becomes a normal affordance rather than a deliberate
out-of-band act.

| Where | Change |
|---|---|
| `static/index.html` | fourth radio, `value="claude_code"`, e.g. "Claude Code CLI (this server)" |
| `static/js/llm.js:299` | delete the remap |
| `static/js/llm.js:248` | model-toggle row is gated `method !== 'claude_agent'`; `claude_code` also carries a model (`opus`), so it must be included or the Haiku/Sonnet/Opus row disappears |
| `updateAuthMethodUI` (llm.js) | `claude_code` branch: hide the local-agent button and instructions; state plainly that it runs on the server and spends the server's seat |
| Apply handler (llm.js, ~line 76) | `claude_code` branch reporting `data.llm_config.claude_cli` (available / version / path), mirroring the `claude_agent` branch |
| `models.py:98`, `config.py:141` | record that the UI exclusion was reversed deliberately, and why |

### Option B — stop lying, still do not offer it

Keeps the design decision intact and only removes the false selection. Switching back to
`claude_code` still requires the API call.

| Where | Change |
|---|---|
| `static/js/llm.js:299` | delete the remap |
| `updateAuthMethodUI` (llm.js) | it reads only the *checked* radio and defaults to `local_llm` when none is checked — with nothing checked it would wrongly show the vLLM panels. Needs the real active mode (module-level value set on restore/apply) so it hides both CLI panels |
| `static/index.html` | a notice element inside the radio group |
| `static/js/llm.js` | populate that notice when the active mode is `claude_code`, warning that Apply will change it |

No `agent.js` change: with no radio checked, `ckAgentModeActive()` already returns false.

### Option C — narrowest

Fix only 3b, so the broker loop keys off the real `auth_method` rather than the remapped radio.
Leaves the false radio and the Apply trap exactly as they are.

## 5. Out of scope here, but related and unresolved

- **`set_llm_config` has no authentication and writes a global setting.** 3c is only a problem
  because any of five unauthenticated clients can change the mode for everybody. Narrowing the
  case-scoped form so it does *not* touch the workspace default would fix the blast radius
  independently of the UI. Not attempted.
- **The server has no authentication at all**, and `POST /api/wizard/push_to_zephyr/{key}?dry_run=false`
  spends the server's `JIRA_KEY` against live Zephyr. Pre-existing; called out in
  `ask-ck/CK-main/run.sh` where the loopback default is set.

## 6. Testing note — read before implementing

> **Corrected 2026-08-26 — this is host-specific, not repo-wide.** The claim below reads as a
> property of the repo; it is a property of *the host it was written on*. On Terrence's
> workstation the gate runs clean and always has: **1060 passed / 1 skipped, 92 Vitest across
> 8 files, both guards OK, `ck.db` signature unchanged**, in about 27 seconds — measured at
> session open, before and after the Option A change. So "revive the gate first" was **not**
> the prerequisite it appears to be, and a future session should not spend time on it before
> checking `./tool/run_tests.sh` where it actually sits. The observation is still true of a
> checkout whose `.venv` lacks `requirements-dev.txt` and which has no `node_modules/` — which
> is worth knowing, because it means **two checkouts of this repo are in use and they are not
> equivalently provisioned.** (A related divergence was found the same day: the LAN server's
> `_workspace_llm` reverts are not present in this checkout's `ck.db`, whose row still reads
> 2026-08-05 — and `_write_session` always stamps `updated_at`.)
>
> `bun` is also absent here; `node_modules/rolldown` was used for the equivalent
> whole-module-graph build check.

**The gate cannot run on this host.** `pytest` is absent from `.venv`, `npm` is off PATH and
`node_modules/` does not exist, so `./tool/run_tests.sh` exits 2 after the two guards.
`setup.sh` does not install `requirements-dev.txt` (it only names it in a hint) and does not
install Node.

Everything shipped on 2026-08-20 was verified by `bun build` over the full module graph, the
two invariant guards, `tool/run_scratch_server.sh`, and live serving — **not** by pytest or
vitest. Reviving the gate first is the safer order for this change.

`tests/test_llm_backend_allowlist.py` is **not** affected by either option: it pins the backend
set, and its header states the guarantee must be *"TRUE IN CODE, not merely true of the UI."*

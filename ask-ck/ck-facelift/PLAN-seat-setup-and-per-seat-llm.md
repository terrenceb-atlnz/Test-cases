# PLAN — Seat setup served from Ask-CK, a Windows-capable agent, and per-seat LLM mode

> ## Status (read first)
>
> **EXECUTED 2026-09-10 (evening) — §3, §4, §5, §6 shipped in five commits; only §9's
> Windows-seat demo remains.** §8b's decisions were reviewed with Terrence on 2026-09-11 and
> are resolved in place; the two that became work (Grok removal + tool retirement, and the
> one-time notice) are **§11, executed 2026-09-11** (three commits). Originally PROPOSED the same
> morning. Written at Terrence's request after the
> second Ask-CK demo day (2026-09-10, ~13:10–14:05 NZST), which ended in the RDP-to-localhost
> workaround again. Three failures were seen; all three are root-caused below with evidence
> from the debug log, the service journal and a reproduction under the live service's
> environment. One repair has already been applied outside this plan: **`claude update` on the
> server host, 2.1.207 → 2.1.267 (2026-09-10 15:00)**, which by itself clears failure #3.
>
> **Decisions already made by Terrence (2026-09-10) — settled, do not re-open:**
> - Seat browsers are Chrome and Edge, possibly Firefox. Chrome was used on demo day.
> - The setup scripts and the agent are **served from Ask-CK** and linked from the **splash
>   page**; a seat needs only the URL. A share-drive copy with a pointer in Ask-CK is the
>   fallback if serving proves awkward — try served first.
> - **No packaged `.exe`.** An unsigned executable fetched over HTTP trips SmartScreen on every
>   seat and needs a Windows build machine. The Windows agent is a **PowerShell script**;
>   Ubuntu keeps the existing Python agent (python3 is always present there).
> - **Per-seat LLM mode is the target.** Server-side Claude (`claude_code`, "this server") is
>   **retired immediately after per-seat works** — it was demo-only since 2026-09-07
>   (memory `claude-agent-is-the-release-transport`).
>
> **All decisions D1–D7 resolved by Terrence 2026-09-10 (later)** — see §8. Phase 1 is
> §3 + §4 (seat setup + Windows agent + CLI currency); §5 then §6 follow a demo on the
> Windows seat (memory `demo-windows-seat`). §6 is a **complete removal** of server-side
> Claude, code and current-state docs alike — see the D3 row for scope.
>
> **Execution 2026-09-10 (evening, autonomous on Terrence's instruction "execute the
> entirety of the plan"):** §3 + §4 SHIPPED (`277fbfc`, `a541495`, `2704ce7`; Ubuntu seat
> verified live on this host, Windows seat NOT yet — §9 remains for the demo seat). §5
> SHIPPED (per-seat via `X-CK-LLM`, `set_site_default_llm`, `apply_workspace_llm` removed;
> see §5 "as built"). §6 executed **ahead of the Windows demo** because the instruction was
> the entire plan — it is its own commit so `git revert` restores server-side Claude if the
> demo ever needs it, and nothing Terrence relies on today depends on it (his own agent on
> this host is `claude_agent`). Decisions that surfaced during execution: §8b.
>
> Authority for the agent's CLI invocation stays
> `PLAN-per-user-agent.md` + memory `claude-code-cli-transport-contract`; the backend
> allowlist stays a governance control (`models.SUPPORTED_AUTH_METHODS`,
> `tests/test_llm_backend_allowlist.py`). The ck.db invariant is untouched: nothing here adds
> a table or column.

---

## 1. What demo day exposed, and why

Three reports from Terrence, in his order, each with the cause found in code or logs.

**#1 — Claude CLI installs to a PATH the user does not have.** Confirmed against the official
docs (code.claude.com/docs/en/setup): the native installer writes `~/.local/bin/claude` on
Linux and `%USERPROFILE%\.local\bin\claude.exe` on Windows and **does not modify PATH** on
either. The user is expected to add the directory themselves. (On the server host `.profile`
does it, and the systemd user service's PATH already carries `~/.local/bin`, so the server
side was never affected.)

**#2 — a Windows seat's Claude is "not picked up".** The seat had **no agent**. A web page
cannot execute a program on the machine it is viewed from; the only bridge Ask-CK has is
`ck-agent` (`ask-ck/agent/ck_agent.py`) on the seat, and nothing delivers or starts it there:
the launcher is bash-only, the agent uses POSIX-only process code (`os.killpg`,
`start_new_session` — `ck_agent.py:133,172`), its fallback CLI path is Linux-only
(`~/.claude/local/claude`), and it needs Python. The demo expectation — "Ask-CK will find the
seat's CLI directly" — was reasonable and the UI never corrected it. The browser-side
"Local Network Access" hypothesis (Chromium ≥142 gating private-origin → loopback fetches)
was **not reproduced**: headless Chrome 153 on the server host, page served from
`http://10.33.22.17`, fetching `http://127.0.0.1:8765/health`, succeeded. Parked, see §7.

**#3 — "(this server)" applied green, then every call failed.** Root-caused by running the
server's exact `claude -p` argv under the live service's own environment:

```
returncode=1 in 2.5s, stderr empty; the stream's result event:
API Error: 400 Claude Code 2.1.207 does not support this model; version 2.1.251 or newer
is required. Run 'claude update', or update the Claude desktop app, then try again.
```

Three facts line up. (a) The server's binary was a symlink pinned to 2.1.207 (installed
2026-07-13); auto-update never ran because on this host the CLI only ever runs headless.
(b) All 8 failed calls that day were `claude_code` with `model=default`, which the CLI now
resolves to Fable 5.1; all 6 successful calls were `claude_agent` with `model=sonnet`, which
2.1.207 could still drive. Same binary, different alias. (c) Nothing said so, because
`llm._call_claude_code_headless` (llm.py ≈L594) sees the non-zero exit and reports
`stdout[:500]` — the **init** event — instead of parsing the stream for the **result** event
that carries the reason; `ck_agent.run_claude` (≈L192) has the same shape. The "verify on
apply" that looked green is `check_claude_cli()` (llm.py:74): it runs `claude --version`
only, and its own docstring says login cannot be verified without a real call.

Two cross-cutting facts from the code that shape everything below:

- **The LLM mode is workspace-global.** `llm_config.apply_workspace_llm` re-syncs every
  case session to the `_workspace_llm` row at dispatch; a per-case config is documented as
  "a STALE leftover, never an intentional override". One seat choosing vLLM or "this server"
  flips the transport for every other seat. `PLAN-llm-mode-selection.md` §5 already names
  the unauthenticated global write as unresolved.
- **The seat already owns its choice, client-side.** `static/js/llm.js` persists
  `draftingLLMConfig` in `localStorage` and the tab mints `CK_SESSION_ID`, sent as
  `X-CK-Session` on every `/api` call (main.py ≈L146). Per-seat mode has a home already.

## 2. Goals

1. A seat becomes Claude-ready from **one URL**: open Ask-CK, copy one line from the splash
   page, run it. Re-running it is the ritual; a clean re-run shows three green checks and
   opens Ask-CK.
2. Windows seats work without Git, Python, WSL or an installer beyond Claude Code's own.
3. **Health means truth**: "ready" is shown only when the agent is up, the CLI is found, the
   CLI is **logged in**, and the versions are known — on the seat and in the page.
4. One seat's LLM choice never changes another seat's.
5. Server-side Claude is gone from the UI and the backend set, with the batch/tooling
   consequences named, not discovered.

## 3. Served seat setup

### 3.1 What the server serves

> **As built 2026-09-10:** no `dist/` copies and no `StaticFiles` mount. An allowlisted
> route (`routers/agent_bridge.py` → `setup_router`, mounted at `/setup`) serves the four
> files straight from `ask-ck/agent/` — the single source of truth, so nothing can drift —
> and computes `manifest.json` on the fly. The server's own origin (from `Host` /
> `X-Forwarded-Host`) is templated into the setup scripts at serve time in place of
> `__CK_SERVER__`, so the one-liner needs **no argument** and the same file works if the
> host moves. `CK_SERVER` in the environment still overrides. Pinned by
> `tests/test_seat_setup_route.py`.

Source of truth is `ask-ck/agent/`. Served at **`/setup/…`** (allowlisted names only —
README, `__pycache__`, anything else in that folder is never served):

| Path | Content |
|---|---|
| `/setup/setup.ps1` | Windows seat setup (§3.3), origin templated in |
| `/setup/setup.sh` | Ubuntu seat setup (§3.3), origin templated in |
| `/setup/ck-agent.ps1` | Windows agent (§4), byte-identical to the repo file |
| `/setup/ck_agent.py` | Ubuntu agent, byte-identical to the repo file |
| `/setup/manifest.json` | `{agent_version, server, files: {name: sha256}, one_liners}` — the seat's update signal; hashes are of the bytes as served |

The agent's CORS lock (`CK_AGENT_ORIGIN`) is set from the same origin; both agents also
read `ck-agent.conf` beside themselves (`origin=`, `port=`, `autostart=`, written by the
setup script) so a Windows logon task, which has no environment, still locks CORS.

### 3.2 The splash page

A new `splash-section` "**Set up your seat for Claude (one time)**" at the top of the guides,
above the tool guides, saying plainly: *Ask-CK runs in your browser; it cannot run Claude on
your PC by itself. A small agent on your PC does that, using your own Claude seat. Run the
one line for your OS, then come back here.* Two copy-able one-liners:

```
Windows (PowerShell):  irm http://10.33.22.17:8000/setup/setup.ps1 | iex
Ubuntu (terminal):     curl -fsSL http://10.33.22.17:8000/setup/setup.sh | bash
```

plus a "download instead" link to each file, and the note that re-running the same line
later is how you update or repair. ("Runnable from the page" is not possible: a browser
cannot execute a downloaded script. The one-liner is the nearest thing.)

### 3.3 The setup script contract (both OSes, one behaviour)

Three stages, each printed as a line that ends `✔` or `✘ <reason + what to do>`; the script
exits non-zero at the first `✘` it cannot repair, and never asks for admin.

**Install ✔**
1. Find `claude`: on PATH, else at the documented install dir (`~/.local/bin`,
   `%USERPROFILE%\.local\bin`).
2. Absent → run the official installer (`irm https://claude.ai/install.ps1 | iex` /
   `curl -fsSL https://claude.ai/install.sh | bash`). Requires outbound HTTPS from the seat.
3. **PATH repair (issue #1):** Windows — add the dir to the **user** PATH via the registry
   (`HKCU\Environment`, `[Environment]::SetEnvironmentVariable(…, 'User')`) *and* to the
   current `$env:PATH` so this run continues; Linux — append the `export PATH=…` line to
   `~/.bashrc` (and `~/.profile` if present) only if absent, and export for this run. Tell
   the user new terminals see it, existing ones need reopening.
4. Present → `claude update` (idempotent; exits 0 when already latest). This is what would
   have prevented #3 on any seat. Print the version.

**Login ✔**
5. `claude auth status` (verified on 2.1.207 and 2.1.267: JSON, exit 0 logged in / 1 not).
   Not logged in → run `claude auth login` **interactively** (it opens the browser; a seat
   has one) → re-run `auth status`. Still not → `✘` with the message. Any logged-in account
   passes (D4: no org check); the result line still prints `orgName` so a personal login is
   visible.

**Agent ✔**
6. Fetch `manifest.json`; compare the local agent file's sha256; download when different or
   missing.
7. `GET http://127.0.0.1:8765/health`. Up and `agent_version` matches → keep it. Up and stale
   → ask it to stop (`POST /shutdown`, new, loopback-only like everything else) → start the
   new one. Down → start it **detached and hidden**: Windows `Start-Process powershell
   -WindowStyle Hidden -File ck-agent.ps1`; Ubuntu `systemd-run --user` or `nohup … &`.
8. **Autostart is the user's choice (D6).** On the **first** run the script asks once:
   *"Start the agent automatically when you log in? [Y/n]"*. Yes → Windows a per-user
   Scheduled Task "at logon" (`schtasks /Create /SC ONLOGON`, no admin); Ubuntu a
   `systemd --user` unit with `WantedBy=default.target`. No → nothing registered; the
   one-liner starts the agent each time. The answer is remembered in a small config file
   beside the agent (`ck-agent.conf`, `autostart=yes|no`) so re-runs do not ask again;
   `--autostart` / `--no-autostart` flags change it later and register/unregister
   accordingly. Both paths idempotent.
9. Re-probe `/health` and require `ok && claude_cli && logged_in`. Print the three versions.

**Finish.** Print the happy line and open `${CK_SERVER}/?seat-check=1` in the default
browser. That query flag makes the page run its own **Check my local agent** on load and
show the result in the LLM status area — this is the authoritative check (§3.4), the
script's curl is only the precondition. If the seat's stored `draftingLLMConfig` is not
`claude_agent`, the page offers to switch (it does not switch silently — §5).

**Windows specifics.** `irm | iex` runs in the caller's session, so no execution-policy
change is needed; a downloaded-then-double-clicked `.ps1` would need
`-ExecutionPolicy Bypass`, which the splash text mentions. PowerShell 5.1 is the floor.
Edge/Chrome both fine; Firefox has no Local Network Access gating (§7).

**Ubuntu specifics.** `python3` present by default; `curl` present on desktop images.
`setup.sh` refuses to run as root (the agent must run as the logged-in user whose seat it
is).

### 3.4 Why the page's check is the authority

The script's own probe of `127.0.0.1:8765` proves the agent answers *the script*. Only the
browser can prove the page reaches the agent (CORS, a browser policy, a stale tab-side
mode). So the script never prints a final "connected" of its own; it prints "agent up,
logged in" and hands the last word to the page via `?seat-check=1`.

## 4. A Windows agent in PowerShell

> **As built, addendum 2026-09-11 (before the Windows demo):** the PowerShell agent writes
> `agent.log` beside itself (startup, each job's start/outcome with seconds and sizes, updates,
> cancels, shutdown, a FATAL line if the port cannot be bound), rotated at 5 MB, and the setup
> script captures its stderr to `agent.err`. Until then a hidden agent that died left nothing
> to read on the seat but `/health` going dark — noticed while preparing the §9 demo. Pinned
> by a live pwsh run in `tests/test_ck_agent_transport.py`.

`ck-agent.ps1` implements the **same contract** as `ck_agent.py`, and only that:

- `System.Net.HttpListener` on `http://127.0.0.1:8765/` (never `0.0.0.0` — the bind is the
  security model, `PLAN-per-user-agent.md`). Same CORS headers, same `OPTIONS` handling,
  origin from `CK_AGENT_ORIGIN`.
- `GET /health` → `{ok, agent:"ck-agent", agent_version, claude_cli, claude_path,
  cli_version, logged_in, hint}`. `logged_in` from `claude auth status` (cached 60 s —
  it forks the CLI). **Both agents gain these fields**; today's `/health` reports
  `claude_cli` only, so an installed-but-logged-out seat shows "ready".
- `POST /run` `{prompt, model?, timeout?, job_id?, system?}` → runs
  `claude -p --output-format stream-json --verbose --tools "" --no-session-persistence
  --system-prompt <system> [--model <alias>]` from a neutral cwd (`$env:TEMP\askck-cli-cwd`),
  prompt on **stdin**, concatenating every `assistant` text block and dropping the
  synthetic non-`msg_` message — exactly the contract in memory
  `claude-code-cli-transport-contract`. Returns `{content, error, usage, total_cost_usd}`.
- `POST /cancel` `{job_id}` → kill the **process tree** (`taskkill /T /F` or
  `Stop-Process` on the child list) — the Windows equivalent of the POSIX process-group kill.
- `POST /shutdown` (new, both agents) so the setup script can replace a stale agent.
- **Error reporting fix (both agents, and `llm._call_claude_code_headless`):** on a non-zero
  exit, parse the captured stream first and prefer the `result` event's text; fall back to
  stderr; the init event is never the message. This is the defect that hid #3.
- Finding the CLI: PATH, then `%USERPROFILE%\.local\bin\claude.exe`. On Windows the
  `claude` on PATH may be a `.cmd` shim; call the resolved path.

### 4.1 Keeping the CLI current (decided 2026-09-10, all three layers)

**Why this is a design point and not a footnote.** The native install auto-updates only
when an *interactive* `claude` session starts. On a host where the binary is only ever
spawned as `claude -p` — the server host, and every seat whose user only ever uses Ask-CK —
nothing triggers an update, and the CLI rots until a model alias it does not know about
appears. That is failure #3 exactly (2.1.207 for two months). It is a property of headless
hosts, not of the "(this server)" mode. Three layers, each covering what the others miss:

1. **The agent updates at startup (both agents).** `claude update` runs once when the agent
   starts, before it begins listening; with autostart (§3.3 step 8) that is once per logon.
   `/health` reports `cli_version`. A failed update is logged and reported in `/health`
   as `update_error`, never fatal — an old CLI that works beats no agent.
2. **The "Check my local agent" button updates on demand.** A new agent endpoint
   **`POST /update`**, separate from `/health` so health stays instant (it is also probed at
   Apply time and by the broker; `claude update` reaches the network and can take a minute).
   The button calls `/health`, then `/update`, and its result line becomes: agent version ·
   CLI version, with "updated from x.y.z" when it changed · logged in as `<orgName>` ·
   ready verdict. **Skipped while a job is in flight** (`_RUNNING` non-empty): on Windows
   the executable in use cannot be replaced, and on Linux swapping the symlink under a live
   call is avoidable — the endpoint answers `{skipped: true, reason: "job in flight"}` and
   the button says so. On the server host this does double duty: Terrence's own agent runs
   the same `~/.local/bin/claude` the server spawns, so a click on his seat updates the
   server's CLI too.
3. **A daily user timer on the server host — interim, until §6.** Terrence, as the server
   host, will never run the seat script, and until server-side mode is retired the server is
   a Claude client in its own right whether or not his agent is up. A `systemd --user`
   `claude-update.timer` + `.service` running `claude update` daily (three lines each,
   alongside `ask-ck.service`, not in the repo — the service unit is not either, memory
   `askck-lan-hosting`). Deleted with the retirement in §6, at which point this host is
   just another seat covered by layers 1 and 2.

Not the gate and not `/orient`: both are meant to stay deterministic and offline, and an
update check reaches the network.

**Testing.** `tests/test_ck_agent_transport.py` already pins the Python agent against the
committed `tests/fixtures/cli_stream_*.jsonl`. The PowerShell parser should be pinned
against the **same fixtures**. `pwsh` is **not installed on the server host** (checked), so
either it is installed there and a gate test shells the PS parser over the fixtures, or the
PS side is verified by the manual checklist in §9 only (Terrence's stated preference is
manual UI testing — memory `user-prefers-manual-ui-testing`). Decision D5.

## 5. Per-seat LLM mode

> **As built 2026-09-10 (D1-A, D2).** `llm_config.py`: `SEAT_LLM_HEADER = "X-CK-LLM"`,
> `current_seat_llm` ContextVar, `parse_seat_llm` (allowlist-validated; retired methods
> named as retired; routing aliases normalised), `seat_llm_config`,
> **`effective_llm_config(sess)`** = seat → site default → session copy → `{}`, never
> writes a session. `apply_workspace_llm` is **deleted**; both routers' one-line wrappers
> (`_session_llm_cfg`, `_llm_cfg`) and `export._ensure_gaps` call the new resolver;
> `cfg_for_task` reads routing from the seat when present (a seat's "same" never falls back
> to the site default's alias). `main.py` middleware 400s a bad header and binds it.
> `set_llm_config` (with or without `{key}`) validates and echoes, **writes nothing**
> (**changed by D17 on 2026-09-11: it now also writes the site default row** — see §8b);
> new `POST /api/wizard/set_site_default_llm` writes the row alone (headless callers);
> `GET llm_config` and `llm_health` say/serve `scope: site_default` / the seat's backend.
> Browser: `session.js` sends the header from `localStorage.draftingLLMConfig` on every
> `/api` call (never to the agent or foreign hosts); `llm.js` stores routing fields too,
> prefers the seat's stored choice over the case session everywhere, shows "· this seat" /
> "· site default", and has a separate **Set as site default** button (confirm dialog)
> (**removed by D17 on 2026-09-11** — one button; Apply writes the default invisibly).
> Tests: `tests/test_per_seat_llm.py` (15), decoupling + routing pins re-homed,
> `js-tests/seat-llm-header.spec.js` (8). Gate 1473 / vitest 274.

**Design (recommended, D1-A):** the seat's choice rides with every request. `llm.js` already
holds it in `localStorage`; the `fetch` patch that adds `X-CK-Session` adds
**`X-CK-LLM: <auth_method>;<model>;<unit_model>;<match_model>`**. `main.py`'s middleware
binds it to a ContextVar next to the session id; `llm._resolve_llm_runtime` reads it in
preference to the session/workspace config, after validating `auth_method` against
`SUPPORTED_AUTH_METHODS` (an unknown value is a 400, exactly as `set_llm_config` does — the
governance guarantee stays true in code). Consequences:

- `_workspace_llm` stops being authoritative for the **backend**. `apply_workspace_llm`
  becomes a no-op or is deleted; `cfg_for_task` reads the routing aliases from the header
  when present (a seat pays for its own aliases, so they are per-seat too). The row can stay
  as the **default for a seat that has never chosen** (first visit), which keeps
  `local_llm` as the zero-config default the governance review saw.
- `set_llm_config` no longer writes the workspace row from a case-scoped call — the §5
  hazard in `PLAN-llm-mode-selection.md`. Whether it keeps writing the *default* at all is
  D2.
- The `_workspace_llm` local-LLM **key** is server-held and shared; unchanged. Only the
  *choice* moves to the seat.
- Tests to move with it: `tests/test_llm_task_routing.py` (8 refs), the 15
  `_workspace_llm` refs in `tests/test_shared_modules_decoupling.py`, `conftest.py`,
  `test_no_unguarded_session_write.py`. New pins: header parsed and validated; header
  absent → default; header with a retired method → 400; two concurrent sessions with
  different headers dispatch to different backends (the actual demo-day hazard).
- The agent broker (`agent.js ckBrokerLoop`) already keys jobs by `X-CK-Session`; nothing
  changes there. `ckAgentModeActive()` reads the seat's own stored mode, which it already
  does.

**Alternative (D1-B):** a server-side per-tab store keyed by `X-CK-Session` (in memory,
like `locks.py`; no schema). Rejected on grounds it dies with the tab and the process while
`localStorage` survives both, and it adds a second copy of a value the browser already owns.

**Identity.** This does **not** need `PLAN-auth-and-case-locking.md` Phase 2 (identity):
a "seat" here is a browser profile, which is what a Claude seat is bound to anyway. When
identity lands, the header value can be attributed; nothing here blocks that.

## 6. Retire server-side Claude (`claude_code`)

> **As built 2026-09-10 (commit `1afc74c`, self-contained — `git revert 1afc74c` restores
> the mode).** Executed ahead of the Windows demo on the "entire plan" instruction; see
> §8b D9. Everything below was done as written, with these specifics: the thinking cap
> moved to both agents (`--max-thinking-tokens 2048` when the job timeout ≥ 120 s;
> AGENT_VERSION 1.2.0); the two server transport test files were deleted and their pins
> re-homed (agents: `tests/test_ck_agent_transport.py`; server half:
> `tests/test_claude_agent_dispatch.py`) — only the removed server parser's forensic
> envelope fields (`message_count`, `text_block_boundaries`) were not re-homed, they had
> no consumer; `tool/enrich_script_index.py` is vLLM-only; the browser never sends a
> retired stored choice as `X-CK-LLM` and drops it (a seat that last applied "(this
> server)" would otherwise 400 on every call); the `claude-update.timer` on this host is
> **left in place** — §4.1 layer 3 said "until §6", but Terrence's own agent on this host
> is the one that depends on it staying current and autostart is off there (§8b D10).
> Gate 1450 / vitest 275.

After §3–§5 are verified on a Windows seat and an Ubuntu seat:

- `models.SUPPORTED_AUTH_METHODS` drops `claude_code`; `RETIRED_AUTH_METHODS` gains it with
  the reason ("shared the server's seat; retired 2026-09 once per-seat agents shipped").
  `set_llm_config` then 400s it; persisted sessions naming it are refused at call time,
  the existing pattern for `api_key`/`account`.
- UI: the radio (`index.html:273`), the help block (≈L337–345), the
  `claudeCodeStatusResult` branch in `llm.js` (15 refs) go. The `/claude_cli_status` route
  and `check_claude_cli` go with them.
- **Remove `llm._call_claude_code_headless` and everything that exists only for it (D3:
  "no evidence this existed").** The CLI contract it embodies does not disappear — it moves
  to where it is actually used: the two agents. `tests/test_claude_cli_transport.py` (18
  pins) and `tests/test_cli_truncation_signal.py` are **re-homed onto `ck_agent.run_claude`
  and the PowerShell parser** against the same `tests/fixtures/cli_stream_*.jsonl`, so no
  pin is lost, then deleted. `llm._parse_cli_stream`, `_cli_neutral_cwd`,
  `_DEFAULT_CLI_SYSTEM_PROMPT`, `_CLI_MAX_THINKING_TOKENS` and the `claude_code` branch of
  `_call_llm_raw` go with it; the `claude_agent` branch keeps its own steer/split code
  (`_PT_PROMPT_SPLIT` is about prompt caching on both routes and stays).
- **Named consequence, accepted:** headless tooling on this host has **vLLM only**.
  `tool/enrich_script_index.py` loses its `claude_code` option; the `llm_health` ping under
  a Claude mode needs a browser tab (already true for `claude_agent`).
- **Docs — current-state docs are scrubbed, records are not rewritten.** SERVER-README's
  "Claude on the server host" section, the README/CHANGELOG *current* feature lists, the
  Configure-panel help text, `models.py`'s allowlist comment and the `run.sh` banner lose
  every mention. `PLAN-llm-mode-selection.md` (whose Option A created the radio) gets a
  status line saying the mode was removed and points here. Dated history — CHANGELOG
  entries, SESSION_STATE, PROGRESS entries, git history, the `TOKEN-EFFICIENCY-REPORT` — is
  left as written: those are records of what happened, and git keeps them regardless. If
  Terrence wants those rewritten too, that is a separate, explicit ask (see the D3 row).
- Memories: `claude-agent-is-the-release-transport` is rewritten to state the release
  transport without reference to a retired alternative; `claude-code-cli-transport-contract`
  is retitled to the agents' contract (its content is what the agents implement).
- Remove the interim `claude-update.timer` on the server host (§4.1 layer 3) — its job
  passes to the agent's startup update and the button.

## 7. Parked: browser Local Network Access

Chromium ≥142 gates fetches from a non-loopback page to loopback behind a permission that
is only requestable from HTTPS, with Firefox not implementing it. Not reproduced on this
host (headless Chrome 153, see §1) and not needed to explain demo day. It stays parked
because the `?seat-check=1` flow will make it visible the moment it appears: the script's
curl passes, the page's check fails with a network error in DevTools naming local network
access. If that day comes the fixes are server-side — HTTPS for Ask-CK (already on the
auth plan as Phase 3 TLS) or the Chrome enterprise policy `LocalNetworkAccessAllowedForUrls`
for the Ask-CK origin — not seat-side.

## 8. Decisions (Terrence's)

| # | Question | Recommendation |
|---|---|---|
| D1 | Per-seat mode carried as a per-request header (A) or a server-side per-tab store (B)? | **DECIDED 2026-09-10: A** — in the browser, sent as `X-CK-LLM` on every request |
| D2 | Does "Apply" still write the workspace **default** for never-configured seats, or does the default become code-fixed `local_llm`? | **DECIDED 2026-09-10:** plain Apply is seat-only; a separate, clearly-labelled "set as site default" control writes the workspace row. **Revised by D17 (2026-09-11)** — one button, Apply writes the default invisibly |
| D3 | After retirement, keep `_call_claude_code_headless` callable for headless tooling? | **DECIDED 2026-09-10: REMOVE ENTIRELY.** Terrence: *"Claude Code CLI (my local machine) — this button will stay, usable by everyone, including myself, the same way I do today. Claude Code CLI (this server) — this button will go, and so will all associated code. I want no evidence this existed at any point."* Scope as implemented in §6: code, tests re-homed then deleted, UI, and current-state docs. Dated records and git history are left as written unless Terrence asks for that separately. Headless tooling on this host becomes vLLM-only |
| D4 | Should Login ✔ require `orgName` to be the team org? | **DECIDED 2026-09-10: no** — any logged-in account passes; `orgName` is printed, not enforced |
| D5 | Install `pwsh` on the server host so the PowerShell parser runs in the gate over the shared fixtures, or verify the Windows agent manually only? | **DECIDED 2026-09-10: installed** — `snap install powershell --classic`, 7.6.5 at `/snap/bin/pwsh`, resolves from the service's PATH too. The gate pins the PS parser against the shared fixtures; the test skips with a clear message where `pwsh` is absent |
| D6 | Agent autostart: Scheduled Task / systemd-user unit, or rely on re-running the one-liner after each reboot? | **DECIDED 2026-09-10: the user chooses** at the first run (*"some people may not want it to re-run on startup"*); remembered in `ck-agent.conf`; `--autostart`/`--no-autostart` to change |
| D7 | Order: ship §3+§4 (seat setup + Windows agent) first and demo it before touching §5? | **DECIDED 2026-09-10: yes** — §3+§4 first, demo on the Windows seat, then §5, then §6 |
| — | CLI currency: agent startup update + button `/update` + interim host timer | **DECIDED 2026-09-10 (Terrence): all three** — see §4.1; the timer can be installed now, ahead of the rest |

## 8b. Decisions surfaced during execution (2026-09-10 evening) — for Terrence

Recorded during the autonomous run, **reviewed with Terrence 2026-09-11** — the outcome of
each is in the last column, marked *Resolved*.

| # | What surfaced | What was done / recommendation |
|---|---|---|
| D8 | **The Windows demo (§9) is the one thing not done** — it needs a person at 10.33.25.50 (memory `demo-windows-seat`). | Run §9 steps 1–6 on that seat. If `?seat-check=1` shows "not reachable" while the script printed three ✔, that is the parked §7 browser policy; the fixes there are server-side. **Resolved 2026-09-11:** Terrence drives the seat, Claude watches the server side (journal, `/setup/` hits, broker). Still to run. |
| D9 | §6 (removal) executed **before** the Windows demo, against D7's ordering, because the instruction was the entire plan. | It is one commit (`1afc74c`). If the demo fails in a way that needs "(this server)" back: `git revert 1afc74c`. Nothing you use today depends on it (your agent on this host is `claude_agent`). **Resolved 2026-09-11: stands** — leave removed. |
| D10 | Your own agent on this host was replaced by the served setup (1.0 → 1.1.0 → 1.2.0) with **autostart = no** (no terminal to ask; D6 says the user chooses). | `CK_SETUP_AUTOSTART=yes curl -fsSL http://10.33.22.17:8000/setup/setup.sh \| bash` registers the systemd user unit. **Resolved 2026-09-11: autostart yes** — re-run done, `ck-agent.service` enabled and active, conf `autostart=yes`. The daily `claude-update.timer` stays. |
| D11 | "No evidence this existed": the removal commit message, a CHANGELOG entry, this plan, the two superseded plans' status notes and git history all **record** that the mode existed. Current-state docs are clean. | **Resolved 2026-09-11: leave records as records.** |
| D12 | The removed server parser's forensic fields (`message_count`, `text_block_boundaries`) were **not** re-homed to the agents. | **Resolved 2026-09-11: dropped.** Add to the agents only if a future truncation investigation wants them. |
| D13 | `tool/enrich_script_index.py` (headless corpus enrichment) is now **vLLM-only** by construction. | **Superseded 2026-09-11 by §11:** Grok is removed entirely and the creation-time tools (this one included) are retired. |
| D14 | Seats whose browser last applied "(this server)" carry a retired value in `localStorage`. | The page never sends a retired value and drops it (2026-09-10). **Resolved 2026-09-11: add a one-time notice** — §11.3. |
| D17 | **Two buttons → one** (Terrence, 2026-09-11, seeing them side by side: *"Theres no contextual cues in the UI for using the site default button, and i see no downside from applying its effects invisibly."*). | **Done, `Apply / Login` now sets this seat AND writes the site default**; the "Set as site default" button and its confirm dialog are gone; `set_site_default_llm` stays as a headless-only endpoint. **The one downside, on record:** every Apply by any seat — and the Haiku/Sonnet/Opus and Fast/Thinking toggles, which post the same request — silently changes what a seat that has *never* chosen starts from. Seats that chose are unaffected (their header wins), so this is a weaker form of the D2 concern, not the demo-day hazard. Revert = one commit. |
| D15 | The site default row still reads `claude_agent / sonnet` (units Sonnet, matching Opus) from demo day. A brand-new seat therefore starts on **Claude via agent**, which fails until that seat runs the one-liner. | Recommended Local LLM. **Resolved 2026-09-11: keep Claude agent as the site default** (Terrence). A bare seat is expected to run the one-liner first. |

## 9. Verification (manual, per Terrence's preference)

On a Windows seat with no Claude installed, from a fresh browser profile:
1. Open Ask-CK, copy the Windows one-liner, run it. Expect Install → installer runs → PATH
   repaired → Login opens the browser → Agent downloaded, started, task registered → three
   `✔` → Ask-CK opens and its status shows "Local agent ready" with versions.
2. Run the one-liner again. Expect three `✔` with no installer, no login prompt, no restart,
   and Ask-CK opens.
3. `claude auth logout`, run again. Expect Login `✘` → login prompt → `✔`.
3b. Pin the seat's CLI to an older build (`claude install <older>`), click **Check my local
   agent**. Expect the result line to read "updated from <older>" and the current version.
   Click again while a generate is running: expect "skipped, job in flight".
4. Bump `agent_version` in the manifest on the server, run again. Expect the old agent
   stopped and replaced.
5. Generate one objective on the Windows seat while a second seat is on vLLM. Expect the
   Windows seat's debug-log rows to read `claude_agent` and the other seat's `local_llm`
   (the demo-day hazard, closed by §5).
6. Reboot the seat, open Ask-CK. Expect the agent already up.
Ubuntu: steps 1, 2 and 6.

Gate: `./tool/run_tests.sh` before and after each phase; new pins listed in §4–§6.

## 10. Out of scope

- Authentication and user identity (`PLAN-auth-and-case-locking.md` Phases 2–3).
- HTTPS for Ask-CK (same plan, Phase 3) — only becomes necessary if §7 materialises.
- Any change to the vLLM (`local_llm`) path or its server-held key.
- A packaged executable or a share-drive distribution (fallback only, per the decision).

## 11. Two backends only: retire Grok and the creation-time tooling; tell a seat its old choice is gone (decided 2026-09-11)

> **Status: EXECUTED 2026-09-11** — `9bb4d77` (Grok removed), `691e4cc` (tools retired),
> `12822ae` (the notice); gate green after each. Decided in the D8–D15 review the morning
> after §3–§6 shipped. Supersedes the D13 and D14 rows in §8b.

**Terrence's words (2026-09-11), which set the scope:**

- *"I want the grok_cli tooling removed too. Every LLM call on Ask-CK should be runnable by
  both the vLLM and the Claude (your seat) options. If that is not the case, please map out
  what features need to be re-written."*
- On the headless `tool/` scripts: *"are these tools that only ran for the creation of ask-ck?
  If so, grok out and retire them. do any run today, with ask-ck? if so, grok out and give
  them a claude path."*
- `pt_autopilot.py`: **retire it too** (chosen over "keep with a headless Claude broker").
- D14: **yes, a one-time notice** under LLM → Configure for a seat whose stored choice was retired.

### 11.1 Grok — what goes

Grok had no radio in the UI since `4a769a8`; it survived as backend code, a status route, a
header value and a set of tests. All of it goes, the same way `claude_code` went in §6 (code and
current-state docs cleaned; dated records left as records, per D11):

| Where | What |
|---|---|
| `llm.py` | `check_grok_cli`, `_call_grok_cli_headless`, the `grok_cli` dispatch arm, the `grok` HTTP provider defaults (`api.x.ai`, `grok-beta`, the `x-api-key` header) and the unused `headless` flag in `analyze_atp_coverage`. `_run_cli` had only the Grok caller left after §6 — it goes with it, and with it the `shutil`/`subprocess`/`tempfile` imports it needed. The empty-provider fallback becomes `openai` (the vLLM path), not `grok`. |
| `models.py` | `SUPPORTED_AUTH_METHODS = ("local_llm", "claude_agent")`; `grok_cli` joins `RETIRED_AUTH_METHODS` so a persisted session naming it is refused **by name** at the transport, not as "unknown". `LLMConfig.provider` default `"grok"` → `"openai"`. |
| `llm_config.py` | `_PROVIDER_FOR` and `llm_is_active` lose the Grok entries. |
| `routers/wizard/config.py` | `GET /api/wizard/grok_cli_status` removed; provider validation is `("claude", "openai")`; the Grok model default and the Grok readiness branch in `_safe_llm_view` go. |
| `static/js/session.js` | `SEAT_LLM_METHODS = ['local_llm', 'claude_agent']` — a browser still holding `grok_cli` in `localStorage` is handled by the same guard as `claude_code` (§11.3). |
| Tests | `test_llm_backend_allowlist.py` (the set is **two**, and `grok_cli` is retired), `test_llm_call_timeouts.py` (the "floor is wired into the dispatch arm" pin had only `grok_cli` left — it is retired with the arm; `claude_agent`'s own pin stays), `test_per_seat_llm.py`, `test_shared_modules_decoupling.py`, `js-tests/llm-task-routing.spec.js`, `js-tests/agent-broker-liveness.spec.js` (comments only). |
| Docs | `SERVER-README.md` (two duplicated Grok sections, the radio list, the allowlist sentence, the quick-start step), `ARCHITECTURE.md`, `README.md`, `CK_server/README.md`, `run.sh` banner, `main.py` docstring, `llm_debug.py` and `llm-progress.js` comments. The governance wiki (`WIKI-Ask-ck.wiki`) rows naming Grok as a selectable backend are corrected — the allowlist tests exist to keep that page true. |

**Why the HTTP `grok` provider goes too, not only `grok_cli`:** the only auth methods that
could reach it (`api_key`, `account`) were retired 2026-08-04, so it has been unreachable code
for five weeks. Leaving a provider with no auth method is exactly the "capability we do not
want to imply we have" the allowlist comment warns about. Not asked for by name; recorded here
as the one scope call in this section (D16).

### 11.2 "Every LLM call runnable on both backends" — mapped

After §11.1 there are two backends and **every LLM call in the product originates in a
browser** and dispatches through `llm_config.effective_llm_config` → `_call_llm_raw`, which has
exactly two arms: `local_llm` (vLLM, streamed) and `claude_agent` (the seat's agent). Every
prompt template is sent unchanged to either. **Nothing needs re-writing.** The one asymmetry is
by design, not a gap: per-task routing (`unit_model` / `match_model`) is a set of Claude model
aliases, so under `local_llm` `cfg_for_task` returns the seat's Fast/Thinking choice for every
task — the vLLM equivalent of "same".

The headless tools were the other source of LLM calls. Classified by Terrence's criterion:

| Tool | Last real change | What it was for | Runs today? | Verdict |
|---|---|---|---|---|
| `tool/enrich_script_index.py` | created 2026-07; edited 2026-09-10 only to drop `claude_code` | Pass 2 of the script index build: LLM summaries/tags appended to a jsonl, merged by `build_script_index.py`, folded into `ck.db` by the DB migration | No — the jsonl it appends to was deleted with the migration; the index lives in `ck.db` | **Retire**, with the `--enrich` hook in `build_script_index.py` and the `enrich_script_index.jinja` template |
| `tool/pt_model_matrix.py` | 2026-07-22 | Part 2B: generate each case's script on every model, side by side | No | **Retire** |
| `tool/pt_judge.py` | 2026-07-27 | Part 3a: per-block LLM judge (Opus + vllm-fast) | No — Terrence prefers in-context judging (memory `terrence-prefers-session-model-as-judge`) | **Retire** |
| `tool/pt_matrix_judge.py` | 2026-07-29 | Companion of the two above; imports both | No | **Retire** |
| `tool/pt_autopilot.py` | 2026-08-03 | Headless batch driver through the running server; last batch 2026-08-03; its resume note (`autopilot/RESUME.md`) depends on the removed `claude_code` | No | **Retire** (Terrence, 2026-09-11) |
| `tool/upload_refined.py` | — | Zephyr upload; imports `validate_zephyr_payload` only | Yes, on request | **Untouched** — no LLM call |

`tool/pt_grade.py` and `tool/pt_preflight.py` make no LLM call and stay. The retired tools'
result directories (`ask-ck/pytest-create/autopilot/`, `comparison/`, `judging/`) are records
and stay; `autopilot/RESUME.md` gets a "⚠ Historical" banner because its instructions can no
longer be followed. `.claude/agents/genpop.agent.md` loses its `pt_autopilot` line; the two
memories that name these tools are corrected.

### 11.3 The one-time notice (D14)

`session.js` already drops a stored seat choice outside `SEAT_LLM_METHODS` (2026-09-10). Now it
also **remembers that it did** (`localStorage.ckSeatLlmRetired = <the dropped method>`), and
`llm.js` renders one line under LLM → Configure next to the status: *"Your previous LLM choice
for this seat is no longer available — this seat uses the site default until you Apply a new
one."* The wording names no retired mode (D3). **One-time** means: shown from the drop until
this seat next Applies (any `storeSeatLlm` clears the flag) — cleared on first render it would
be missed by a seat that lands on the splash page and never opens Configure that visit.
Pinned in `js-tests/seat-llm-header.spec.js` and a small llm.js spec.

### 11.4 Revert path

One commit per concern (grok removal; tool retirement; notice), so any one can be reverted alone.
The tools are recoverable from git history by path; nothing they produced is deleted.

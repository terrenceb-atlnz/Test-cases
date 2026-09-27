---
verified: 2026-09-28
---
# PLAN — `pt_agent_broker.py`: driving the PyTest Creator through `claude_agent` without a browser

> ## Status (read first)
>
> **DECIDED, PLAN ONLY — nothing built.** D-C of `PLAN-pt-followups-review-2026-09-24.md` §B:
> Terrence chose option (a) on 2026-09-28 (*"i think its a really good idea ... Go ahead and
> write the plan as-is, we will go over it in more detail later on"*). The design rule stands:
> **the browser brokers `claude_agent`** — this tool is a stand-in for the browser's poll loop
> on a seat, not a server-side mode. Proven once already: the scratch `broker.py` of
> 2026-09-24 drove T33235's generate (units 20–80 s each, 8 workers) and review (one
> 381k-character prompt) end to end.

## 1. What it is

Every prompt the PyTest Creator sends through the `claude_agent` backend goes into an
in-memory queue keyed by the caller's `X-CK-Session`. Normally the open tab long-polls that
queue, runs each job on the seat's local `ck-agent` (`127.0.0.1:8765`) and posts the result
back. The broker does exactly that from a terminal, for one session id, so a script — the
`test-composer` agent, a bench loop, a curl — can drive generate / review / fix with no tab.

## 2. The contract (from `routers/agent_bridge.py`, unchanged)

| step | call | notes |
| --- | --- | --- |
| claim | `GET /api/agent/next?wait=25`, header `X-CK-Session: S` | long-poll ≤ 55 s; `{job: null}` when empty; a job is `{job_id, prompt, model, timeout, system}` |
| run | `POST http://127.0.0.1:8765/run` with the job's fields | `timeout` is the SERVER's budget for the job — pass it through, add nothing |
| still wanted? | `GET /api/agent/job_wanted/{job_id}` while running | `{wanted: false}` → `POST /cancel` on the agent, drop the job (the browser does this; the scratch broker did not) |
| deliver | `POST /api/agent/result` `{job_id, content, error, usage, total_cost_usd}`, same `X-CK-Session` | a result from another session is refused (`delivered: false`) |

Two facts every user of the tool must know:

- **Same session, both sides.** The driver that calls the PyTest Creator API must send the
  `X-CK-Session: S` the broker polls with, and `X-CK-LLM: claude_agent` (LLM choice is per
  seat — memory `claude-agent-is-the-release-transport`, `workspace-llm-default-gotcha`).
- **Locks are the driver's.** A headless driver has no tab heartbeat. It acquires the case
  (`POST /api/locks/pt/{key}/acquire`), heartbeats every 5 min, releases at the end;
  otherwise the case reads locked to everyone for 15 min after the run. The broker does not
  lock — it is not editing anything.

## 3. The tool

`ask-ck/tools/pt_agent_broker.py --server http://10.33.22.17:8000 --session S [--workers 4]
[--agent http://127.0.0.1:8765] [--log PATH] [--once]`

- stdlib only (`urllib`, `threading`, `json`), like `ask-ck/agent/ck_agent.py`; runs on the
  SEAT where the agent is logged in, never on the server host (no seat there).
- N worker threads, each: claim → run (polling `job_wanted` every ~5 s) → deliver. Worker
  count is a plain CLI choice: the 6-per-origin ceiling (memory
  `browser-fanout-connection-ceiling`) is a browser rule, and `urllib` has none.
- JSON-lines log: `started`, `claimed` (job id, model, prompt size, timeout), `done`
  (seconds, content size, delivered, error head), `abandoned`, `poll_error`. **Never the
  prompt or the content** — the same rule as `agent.log`.
- `--once`: exit after N consecutive empty polls (scripted runs); otherwise run until SIGINT,
  finishing in-flight jobs.
- Exit codes: 0 clean; 2 the agent is unreachable at start (`/health`); 3 the server is.

## 4. Tests (gate) and the mutation check

- An in-process fake server and fake agent (`http.server` on threads) pin the four calls:
  claim → run → deliver round trip; `job_wanted: false` → agent `/cancel` and no delivery;
  a `delivered: false` reply is logged, not retried; the prompt never reaches the log.
- The request shapes are pinned against `agent_bridge.py` the way the CLI transport is pinned
  against shared captures (memory `claude-code-cli-transport-contract`).
- Mutation check before claiming any of it (memory `mutate-before-you-claim`).

## 5. Docs

- `SERVER-README.md`: a "Driving the PyTest Creator headless" section — the two facts of §2,
  the command line, and a worked example (acquire lock → start broker → POST generate → poll
  `gen_state` → release).
- `.claude/agents/test-composer.agent.md`: the recipe it uses, since generating scripts *"by
  driving the PyTest Creator"* is its stated job.
- `ask-ck/agent/README.md`: one pointer.

## 6. Not in scope

Option (b), a server-side headless mode (against the design). Any change to
`agent_bridge.py` or `ck_agent.py`. A driver script (`pt_drive.py`) — whether the driver is
the agent's own recipe or a repo tool is a separate decision for the review of this plan.

## 7. For the review with Terrence

- Default worker count (8 worked on 2026-09-24; 4 proposed).
- Whether the tool should refuse to start when the session id already has a live browser
  broker (two brokers on one session split the queue between them — harmless, but confusing).
- Where the driver lives (§6).

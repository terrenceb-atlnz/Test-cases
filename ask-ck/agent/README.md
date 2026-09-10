# ck-agent — Ask CK per-user local LLM agent

Run this on **your own machine** so your Ask CK LLM requests use **your own**
locally-logged-in Claude Code CLI seat — even when Ask CK itself is a shared
webpage hosted on another box. Your seat is never shared with other users; the
shared server never sees a credential.

See the design in [`../CK-main/PLAN-per-user-agent.md`](../CK-main/PLAN-per-user-agent.md).

## Prerequisites

- Python 3 (stdlib only — nothing to `pip install`).
- Claude Code CLI installed and logged in on this machine:
  ```bash
  # install per anthropic.com/claude-code, then:
  claude          # run once, then /login with your Claude account
  ```

## The easy way: the one-line seat setup

The shared Ask CK page serves a setup script for each OS that installs Claude Code, fixes
PATH, logs you in, downloads this agent and starts it — and, re-run, updates or repairs all
of that. Open the Ask CK home page and copy the line for your OS. Everything below is the
manual route it automates.

## Run it by hand

Ubuntu (Python 3, stdlib only):

```bash
./run-agent.sh
# or, to lock CORS to your shared Ask CK server:
CK_AGENT_ORIGIN=http://ck-box.lan:8000 ./run-agent.sh
```

Windows (PowerShell 5.1+, nothing to install) — `ck-agent.ps1` is the same contract, same
endpoints, same `claude -p` flags and parsing, pinned against the same captures by the
repo's gate through `pwsh`:

```powershell
powershell -ExecutionPolicy Bypass -File ck-agent.ps1
# lock CORS to your server:
$env:CK_AGENT_ORIGIN = 'http://10.33.22.17:8000'; powershell -ExecutionPolicy Bypass -File ck-agent.ps1
```

Leave it running. It binds **127.0.0.1:8765** (localhost only — never exposed to
the network). Then open the shared Ask CK page in your browser and choose
**LLM → Configure → Claude Code CLI (my local machine)**. The page checks that
your agent is up, and from then on your prompts run through it against your seat.

## How it works

The shared Ask CK server queues your prompt jobs but does **not** run `claude`.
Your browser tab (the only thing that can reach both the shared server and your
`localhost`) long-polls the server for your jobs, POSTs each prompt to this agent
at `http://127.0.0.1:8765/run`, and posts the completion back. `claude -p` only
ever runs here, on your machine, as you.

## Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `CK_AGENT_PORT` | `8765` | Port to bind on 127.0.0.1 |
| `CK_AGENT_ORIGIN` | `*` | Allowed browser origin (set to your Ask CK server URL) |
| `CK_AGENT_TIMEOUT` | `600` | Max seconds per `claude` call |

## Endpoints (for reference)

- `GET /health` → `{ok, agent_version, claude_cli, claude_path, cli_version, logged_in, org,
  jobs_in_flight, update_error, hint}` — is the agent up, is `claude` installed, **is it
  logged in** (from `claude auth status`, cached 60 s), and which versions are in play.
  Before agent 1.1.0 this reported only binary presence, so a logged-out CLI read as ready.
- `POST /update` `{}` (JSON content type required) → `{ok, updated, from, to, skipped, reason,
  error, health}` — runs `claude update`. Skipped, and says so, while a job is in flight.
  The page's **Check my local agent** button calls this after `/health`.
- `POST /shutdown` `{}` (JSON content type required) → stops the agent. Used by the seat
  setup script to replace a stale agent; the agent also runs `claude update` once at startup
  (`CK_AGENT_UPDATE_ON_START=0` disables that).
- `POST /run` `{prompt, model?, timeout?, job_id?, system?}` → `{content, error, usage?, total_cost_usd?}` —
  runs one `claude -p` completion exactly as the server's own transport does: `--tools ""`,
  `--system-prompt <system>` (replacing the CLI's harness prompt so a fan-out's shared prefix
  can hit the prompt cache), `--no-session-persistence`, `stream-json` with every assistant
  message concatenated, from a neutral cwd with no CLAUDE.md above it (2026-09-04).

## Security

Binds `127.0.0.1` only and restricts CORS to the Ask CK origin. No token: any
process on **your** machine could call the agent, but it can only ever spend
**your own** Claude seat, so there is nothing to share or steal. Do not change the
bind address to `0.0.0.0` — that would expose your seat to the network.

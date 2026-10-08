---
verified: 2026-10-09
---
# PLAN — Agent sessions: Ask-CK starts, watches and talks to a full Claude Code session

> ## Status (read first)
>
> **DRAFT — nothing built. Decisions D1–D5 (§10) taken 2026-10-09; the §4 launch option waits on
> P0.** Written 2026-10-09
> at Terrence's request: *"I think its worth another plan that we tackle outright that will be
> linked to this one, with that plan needing to be done first."* It is the **first** of three:
>
> 1. **this plan**: the foundation (A);
> 2. [`PLAN-test-validation.md`](PLAN-test-validation.md) (B): one script, probe → preflight → run → repair → review → Finalize;
> 3. [`PLAN-test-composer.md`](PLAN-test-composer.md) (C): a project's runnable cases on a topology template.
>
> B and C both launch device-testing's `/test-mode` through what this plan builds, so neither
> starts before this plan's Phase 1.
>
> Settled in the 2026-10-09 conversation, and NOT for re-litigation here:
> - the three-part split;
> - all new UI is written **in Svelte, in `current/`, on both the Classic and ATUI pages**, with ZTT
>   ported first as the pilot (PLAN-test-composer C-D1, C-D2);
> - Windows seats must eventually run this *"just as well as linux seats"* (meeting-room demos),
>   but that is deferred until everything else works (D1, §5);
> - email goes through the server host's postfix (§8).

## 0. The ask — Terrence, 2026-10-09

- Ask-CK launches the `/test-mode` agent (device-testing's skill) for both Validation and the
  Composer: *"called by ask-ck"*.
- **A window** in the page: *"a similar output as what we would see in the prompt window for a
  claude session in VS Code. I view this as a read-only status window, but if we can make it
  interactive i'd want to reuse that ability in other places to make this process easier
  throughout Ask-CK (even if we had a clippy-esque chat that would be helpful to drive the UI
  and help the user)."*
- **Questions answered in the page**: *"there are user-specific questions that need answering
  (PDU in mind)"*. Repair choices in Validation are also *"some conversation with the user"*.
- **Windows**: *"Windows seats should be able to run the solution we author just as well as
  linux seats. Assuming we use the ask-ck setup script and they obtain claude and have a local
  agent logged in, this tool (and all others) should be runnable."*
- **After hours**: *"a Cron option for things that need multiple restarts, so we can run them
  after-hours."*
- **Two-way window**: *"Bring this up in the plan, where we can figure out what a realistic
  expectation of features could look like and how it can be realistically implemented."*
- **Readouts**: the run time and the tokens used.

## 1. Constraints this plan inherits (settled decisions and measured facts)

| # | Constraint | Source |
|---|---|---|
| K1 | **Every Claude session runs on the user's own seat and login.** A shared server never pools users through one login and never sees a credential. | memory `claude-agent-is-the-release-transport` (2026-09-10); `archive/plans/PLAN-per-user-agent.md` |
| K2 | **The browser is the broker today.** Only the tab can reach both the shared server and the seat agent (`127.0.0.1:8765`, CORS-locked). Jobs are keyed by `X-CK-Session`. | `routers/agent_bridge.py`; `ask-ck/agent/README.md` |
| K3 | **The seat agent is stdlib Python on Linux and PowerShell 5.1+ on Windows, "nothing to install".** Both implement one contract, pinned by the gate. A design needing Python or Node on Windows adds a prerequisite there. | `ask-ck/agent/ck-agent.ps1`, memory `windows-seat-gotchas` |
| K4 | **One connection, not many.** HTTP/1.1 allows 6 connections per origin; a page that fans out starves the poll. A stream into the page is one request plus polling, or one long-lived stream. | memory `browser-fanout-connection-ceiling` |
| K5 | **`/test-mode` needs two things from the session's machine:** a device-testing working copy (its skills, `STANDING-ORDERS.md`, the sentinel kit) as the session's working directory, and SSH key access to the testbox. **It also commits** its queue file and per-case logs in that repo. A Linux seat has both through the NFS lab home. A Windows seat may have neither (§5). | device-testing `.claude/skills/test-mode/SKILL.md` §2–§4 |
| K6 | **Today's seat agent runs `claude -p ... --tools ""`**: a one-shot completion with every tool switched off. A full-tools session is a new kind of job, not a flag change. | `ask-ck/agent/ck_agent.py:422` |
| K7 | Stopgaps landed in device-testing `83c0880`, for this plan to replace: `--from-ask-ck <handoff>` only checks the file exists, and the run id is the hand-off's basename (§6). | peer session, 2026-10-09 |
| K8 | The working tree is production. `ask-ck/agent/` is outside the `--reload` watch; `CK_server/*.py` is not. | memory `editing-backend-restarts-production` |

## 2. What Claude Code offers — verified and unverified

**Verified on this host, 2026-10-09** (`claude --help`, Claude Code **2.1.294**). These flags exist:

- `--input-format stream-json` with `--output-format stream-json`: "realtime streaming input"
  and output, `--print` only.
- `--replay-user-messages`: re-emits stdin user messages on stdout as an acknowledgement.
- `--include-partial-messages`: partial chunks as they arrive.
- `--permission-prompts host|none`: "Who answers permission prompts with --print: host (the
  SDK host or --permission-prompt-tool) or none (… denied automatically)".
- `--permission-mode acceptEdits|auto|bypassPermissions|manual|dontAsk|plan`;
  `--allowedTools` / `--disallowedTools`.
- `--bg`: "Start the session in the background and return immediately". It prints an id that
  `claude attach`, `logs`, `stop` and `rm` take, and `claude agents` lists them; with `--resume`
  it continues that session in the background under the same id.
- `--resume`, `--continue`, `--session-id <uuid>`, `--fork-session`.
- `--remote-control [name]`: an interactive session with Remote Control.
- `--brief`: enables a SendUserMessage tool.
- `--settings`, `--add-dir`, `--bare`, `--agents`.

**All six were settled by P0 on 2026-10-09; see §9a for the results.** The table below is
the pre-P0 record. **Reported by the 2026-10-09 docs research but NOT yet verified here.** Each is a Phase 0 test
(§9). None is a fact until that test runs.

| # | Claim | Why it matters |
|---|---|---|
| U1 | `claude -p "/test-mode …"` expands a project skill; project subagents, background subagents, Monitor and CronCreate all work in `-p`. Background subagents get a smaller tool set (no AskUserQuestion). | `/test-mode` is built on every one of these. |
| U2 | With `--permission-prompts host`, **AskUserQuestion** and permission prompts go to the host and the run waits for an answer. The stdin answer format is not documented. | This is the whole "questions in the page" feature. |
| U3 | The `stream-json` **input** message schema (sending a user message mid-run). | Chat and repair conversation. |
| U4 | The final `result` line carries `total_cost_usd` and usage; whether subagent usage is included or itemised is **not documented**. | The token readout. |
| U5 | A `--bg` session survives the process that launched it. Whether it can be fed messages programmatically (not only through the interactive `attach`) is unknown. | Tab-close survival and after-hours runs. |
| U6 | The research also reported a policy line: third parties building on the **Agent SDK** may not offer claude.ai login to their users and should use an API key. **I have not read it at the source.** Whether and how it applies to an internal tool where each employee runs their own Claude Code is a governance question, not an engineering one. It does not obviously touch today's `claude -p` path. | It decides whether option C (§4) is even available. Read the source before choosing C. |

Reading a session's `~/.claude/projects/<slug>/<id>.jsonl` while it runs is how the sentinel kit
watches a peer today. The docs research says it is **not** a supported interface: the format
is internal and changes between releases. Use `stream-json` stdout for the window. The
transcript stays a fallback.

## 3. Words used below

- **Session**: one long-lived Claude Code process doing one job (a Validation run, a Composer
  campaign, or a helper chat).
- **Window**: the panel in the Ask-CK page that shows a session's progress and, from Phase 2,
  takes answers.
- **Launcher**: whatever starts the session on the seat. Today's candidate is the seat agent
  (`ck_agent.py` / `ck-agent.ps1`).
- **Hand-off**: the file Ask-CK writes describing what the session is to do (§6).

## 4. Where and how the session runs — options

All four keep K1: the session runs on the user's seat, under the user's login.

**A. Extend the seat agent with a "session" job (recommended to test first).**
- **How:** the agent spawns
  `claude -p --input-format stream-json --output-format stream-json --verbose --permission-prompts host …`
  in the right working directory. It keeps stdin open, buffers stdout events, and serves them
  to the page (`GET /session/{id}/events?after=N`, one poll at a time per K4). It writes the
  page's answers back to stdin (`POST /session/{id}/input`).
- **For:** no new install on either OS (K3); the same contract and gate-pinned captures as
  today; the browser stays the broker (K2).
- **Against:** the session lives inside the agent process. Closing the agent or rebooting the
  seat kills it (`/test-mode --resume` then picks up from the queue file, losing the case in
  flight). With the tab closed the session keeps running, but nobody sees its questions until
  a tab reattaches.

**B. A + `claude --bg` for survival.**
- **How:** the launcher starts the session with `--bg`, so it outlives the agent and the tab.
- **Depends on U5:** we need a non-interactive way to read its events and send it input. If
  only `claude attach` (a terminal) can talk to it, B gives survival but no window.

**C. Agent SDK on the seat (Python or TypeScript).**
- **For:** `canUseTool`-style callbacks would make the question relay first-class code instead
  of stdin plumbing.
- **Against:**
  - it needs Python or Node on Windows seats, which breaks K3;
  - it is gated by U6.
- **Status (Terrence, 2026-10-09): tested in P0 alongside A.** *"I think option C is incredibly
  interesting, we can add the download for windows if necessary as part of the setup script we
  run anyway."* So the Windows prerequisite is acceptable, provided the seat setup script
  installs it. U6 still has to be read at its source before C is chosen.

~~**D. Remote Control as the interactive fallback.**~~ **Ruled out (D2): Remote Control is
denied by company policy** (Terrence, 2026-10-09). The consequence: until W2 is built, a session
has nowhere to ask a question. So P1 collects every `/test-mode` setup answer (testbox,
consoles, PDU and outlets, constraints) in the page **before** launch and carries them in the
hand-off (§6). A session that still needs input follows **D5** (§8): it sends an
informative email and works past the question, or moves on to the next case. It never stops
the campaign to wait.

## 5. Windows seats — the working-copy problem

> **Decided (D1, Terrence 2026-10-09): OUT OF SCOPE until everything else works, then pursued
> as "remote mode" (route R below).** *"TBD Out of scope until everything ELSE works. We will
> need a way to run a demo in the future, and unfortunately all the meeting rooms use Windows
> seats."* And on reviving a shared login: *"we wont re-attach the shared login. thats a bad
> idea."* So Windows is required eventually, for demos, and a host-side shared session is
> never the answer. Until then, build nothing that assumes the session's working copy is
> local: the hand-off, the window and the server side stay OS-independent.
>
> **Route R — remote mode (the chosen future route).** The Ask-CK server can read device-testing
> (it is a sibling directory on the NFS lab home), but the session cannot: Claude Code loads
> skills and runs its tools on **its own** machine, and a symlink on the server means nothing
> on a Windows seat. In remote mode:
> - the seat's session gets the `/test-mode` skill text from Ask-CK;
> - it does every file write and every git commit **over SSH**, on a Linux box that mounts the
>   lab home (the testbox does: the repo is at `~/claude/device-testing` there).
>
> Still needed then:
> - a remote variant of `/test-mode`, which today assumes local paths throughout;
> - a per-user SSH key on the Windows seat. Today's server-side runs SSH as Terrence's own
>   user, which would be a shared identity for anyone else.
>
> Options 1–3 below are kept as the record of what was weighed.

`/test-mode` must run with a device-testing working copy as its working directory, and it SSHes
to the testbox and commits as it goes (K5). Today a Linux seat gets this from the NFS lab home.
For a Windows seat the options are:

1. **The Windows seat reaches the same tree.** The NFS export is reachable over SMB or a mapped
   drive, and an SSH key is provisioned by the setup script. This depends on whether a Windows
   seat can mount the lab home at all (unknown — **a question for Terrence or IT**). Git on a
   network share from Windows is slow and line-ending-prone.
2. **The session runs from a small local workspace and does every bench step over SSH.** The
   skills would need a copy on the seat, and the commits would land in a local clone that cannot
   push (Claude cannot push from these seats). This breaks "the queue file in the repo is the
   resume point".
3. **The user's own Linux account is "the seat" for bench work.** A Windows user's session
   runs under *their own* Unix account and Claude login on a lab Linux host. It is still their
   seat and their login (K1 holds), just not their desktop; the Windows page talks to it the
   same way. This needs every Test Engineer to have a lab account and a one-time `claude login`
   there.

Recommendation: **ask before designing**. Option 3 is the simplest way to make Windows "just
as good" without moving the repo, but whether it fits K1 in spirit — "your seat" meaning
your login, not your desktop — is Terrence's call.

## 6. The hand-off file (replaces the 83c0880 stopgap)

Ask-CK writes it **in its own repo**, under the run's record directory:
`ask-ck/functions/test-composer/runs/<YYYY-MM-DD>/<run_id>/handoff.json`. The session reads
it and never writes it. That respects the write boundary: Ask-CK writes only here, and
device-testing only reads it.

```json
{
  "schema": 1,
  "run_id": "2026-10-09T1430-ab12",
  "kind": "validation | composer",
  "seat": "<whoami>@<hostname>",
  "testbox": "tb470",
  "consoles": "u2,u4,u5",
  "pdu": {"ip": "…", "outlets": {"u2": 6}} ,
  "constraints": "…verbatim…",
  "template": "setup-a",
  "project": {"version": "5.5.6-2", "product": "IE570", "plans": ["AWPTCM-P3266"]},
  "cases": [
    {"key": "AWPTCM-T33235", "kind": "script", "script": "generated/9001_Port/…py", "cycle": "C8470"},
    {"key": "AWPTCM-T12589", "kind": "manual", "cycle": "C8470"}
  ],
  "options": {"email": "…", "start_after": null},
  "ui": {"session_endpoint": "…"}
}
```

- **`run_id`** replaces the stopgap "run id = the file's basename".
- **`cases[].kind`** replaces the stopgap "script case = one whose log names a `.py`".
- `/test-mode --from-ask-ck` reads the setup answers from here instead of asking. Anything
  missing is asked through the window.
- **To be agreed with the device-testing session:** the exact fields `/test-mode` reads, and
  that it validates `schema`.

## 7. The window — a realistic feature ladder

Each rung ships on its own and is useful alone. **All of it is Svelte, in `current/`, on both
Classic and ATUI.** It is one reusable component, so the Clippy-style helper later is the
same window bound to a different session.

| Rung | What the user gets | Built on | Risk |
|---|---|---|---|
| **W1 read-only stream** | Assistant text, each tool call as a collapsed row (name, short input, ok/error), subagent start/finish, `RESULT` lines highlighted, a running clock, tokens when the result arrives. Follows the tail; pauses when scrolled up (the ART Test Runner's "Follow" behaviour). | stdout `stream-json` (verified flags) | low |
| **W2 questions** | An AskUserQuestion appears as a card with its options as buttons plus "Other" (free text); a permission prompt as Approve / Deny with the exact command shown. The session waits until it is answered. | U2 | **medium — Phase 0 decides** |
| **W3 conversation** | A text box under the stream: send a message mid-run ("don't touch u3", "explain that failure"). | U3 | medium |
| **W4 helper anywhere** | The same window docked on any page, started with that page's context (the case, the script, the step). The "Clippy" idea. | W1–W3 + per-page context | design work, low tech risk |

"Drive the UI" (the helper clicking buttons for the user) is **not** on the ladder. A later
plan could add a small set of page actions the helper may call, but nothing here assumes it.

## 8. Lifetime, after-hours runs, email, readouts

- **Tab closed:** the session keeps running (A or B). A reopened page reattaches by `run_id`
  and replays events from the agent's buffer. A question asked while no tab was open waits.
  It is also emailed if the run asked for email.
- **Seat or agent restarted:**
  - with A, the session dies and the next launch is `/test-mode --resume` (already designed);
  - with B, it survives (U5).
- **After hours (cron):**
  - **Problem:** today nothing on a seat acts without an open tab, because the browser is the
    broker (K2). So an after-hours run needs one of:
    - (i) the seat agent polling the server for scheduled jobs itself, the role
      `PLAN-pt-agent-broker.md` already designs for a terminal;
    - (ii) the OS scheduler on the seat (cron / Task Scheduler) starting the launcher at the
      chosen time;
    - (iii) a session started in the evening that waits (CronCreate inside the session lives
      only as long as the session, per U1).
  - **Decided (D3, 2026-10-09): (i), the seat agent polls.** It is already planned, it is per
    seat, and it keeps the schedule visible in Ask-CK. The seat must be powered on and logged
    in, which the page must say.
- **Email (verified 2026-10-09):** the Ask-CK server sends it, not the seat.
  - **How:** `smtplib` to `localhost:25` (postfix on the server host), relayed by
    `int-smtp.atlnz.lc`, from `do-not-reply@alliedtelesis.co.nz`. This is the same mechanism
    as ART's `rtmt -m`.
  - **Test:** one test mail was sent and received (Terrence confirmed, 11:12, ~6 s).
  - **When:** on run finished, on run failed, and when the session hits something it needs a
    person for (D5, below).
- **Blocked on a person — D5 (Terrence, 2026-10-09):** *"i dont want the testing campaign to
  stop. Id say make it an informative email, with a small amount of detail, and then work past
  it if at all possible. if not, then move to the next test case."* So a campaign never waits on
  an answer:
  1. **The email is informative, not a request:**
     - which run and case;
     - what it needed;
     - what it did instead;
     - a link to the run in Ask-CK.
  2. **Work past it if at all possible.** Take the safe, standing-orders-consistent choice, and
     record it on the case's result row as the assumption made. Your re-grade in the results
     table can still overturn it (grading tier list).
  3. **If it cannot be worked past**, that case is BLOCKED with the reason, and the campaign
     moves to the next case.
  4. **A block that applies to every remaining case ends the campaign** with the same email.
     For example: no testbox access, or a probe MISMATCH that no case can run under. Moving on
     would only repeat it. (Terrence agreed to this edge case, 2026-10-09.)
  5. **Landed in device-testing as `/test-mode` §10 (`52cc64e`, 2026-10-09, not pushed).** The
     signal is `NOTIFY <case-id|campaign> -- <what it needed> -- <what it did instead>` plus the same
     text in the queue's `## Issues`. The assumption goes into the case's Results reason as
     `Assumed: …`. Until P0 defines the event channel, Ask-CK turns the `NOTIFY` lines into email.
  6. **"Work past it" never makes a decision STANDING-ORDERS §4 keeps for Terrence:** root on the
     box, `bench_probe.py apply`, a recable, a licence, resolving a USER-CONFLICT, or displacing a
     console holder. For those, the session runs every case that doesn't depend on the decision,
     BLOCKs the rest with a `NOTIFY`, and ends the campaign only if every remaining case is
     blocked. **A hand-off whose topology needs an `apply` blocks; it never self-applies.** The
     Composer's Validate step (probe vs template, green check before Start) is where a bench
     change is meant to happen, by a person, before launch.

  This matches the bench's own rule that bench-runner never raises a blocking prompt and sends
  its needs through the sentinel (STANDING-ORDERS). With W2 in place, the question also
  appears in the window, but the campaign still does not wait for it. Validation's repair
  conversation (PLAN-test-validation) is interactive by design and is not a campaign; whether
  D5 applies there is settled in that plan.
- **Time:** wall clock from the session's first event to its `result` line, plus per-case
  start/end from the `RESULT` lines.
- **Tokens:** the `result` line's usage and cost (U4). If subagent usage is not included,
  device-testing's `/create-logs` already measures per-case usage from the tester's transcript,
  which is the fallback.

## 9. Phases

| Phase | Content | Exit |
|---|---|---|
| **P0 — spike, no Ask-CK code** | On this host, from a scratchpad, with a throwaway script driving `claude -p` over stream-json both ways. First confirm U1–U5 against a harmless project skill: record the event schema (captured to a file, as the transport contract's captures are), the AskUserQuestion round trip, the input schema, `result` usage with a subagent, and `--bg` reattach. Read U6 at its source. **Repeat the U2/U3/U4 checks with the Agent SDK (option C)**, from a scratch virtualenv, to compare its question handling with A's stdin plumbing. **Then one real `/test-mode` TRIAGE on tb470 (D4)** through the same throwaway driver: occupancy check and probe, **no case runs**. It goes through the normal sentinel and bench-runner gates. It is not strictly read-only: the probe switches `lldp run` on for a device that had it off and leaves it on (since 2026-09-30). Windows is not in P0 (D1). | A short findings section added here, and the §4 choice made **with Terrence** |
| **P1 — launch + W1** | The seat agent's session job (both agents, same captures pinned in the gate); the hand-off file; a server run record; the Svelte window, read-only; reattach by `run_id`. | A real `/test-mode --from-ask-ck` TRIAGE run shown live in the page |
| **P2 — W2 questions** | The question/permission relay; the setup questions (testbox, consoles, PDU) answered in the page. | A `/test-mode` session asks its §1 questions in the page and proceeds on the answers |
| **P3 — W3 conversation** | Mid-run messages. | Validation's repair conversation (B) works end to end |
| **P4 — scheduling** | Seat-agent polling for scheduled runs; email on finish/fail/question. | A run scheduled for after hours starts with no tab open and emails its result |
| **P5 — W4 helper** | The docked helper on other pages. | Its own small plan when we get there |

### 9a. P0 findings (run 2026-10-09, Claude Code 2.1.294 → 2.1.295 mid-run)

Everything ran from the session scratchpad: throwaway drivers, a throwaway project with a
`p0probe` skill and a `p0helper` agent, and a scratch virtualenv with `claude-agent-sdk` 0.2.165.
No Ask-CK code changed.

| # | Result |
|---|---|
| U1 | **Confirmed.** `/p0probe` and `/test-mode` both expanded in `-p` with stream-json. Project agents ran (`p0helper`, `bench-runner` in the background). The init event lists Monitor, CronCreate, SendMessage and AskUserQuestion, and the TRIAGE session used Monitor, CronCreate, a background Agent and the subagent's SendMessage. |
| U2 | **Confirmed — the wire protocol, read from the SDK's source and exercised raw:** launch with `--permission-prompt-tool stdio` plus stream-json in and out. **(1)** Send `{"type":"control_request","request_id":…,"request":{"subtype":"initialize"}}`. **(2)** The CLI sends `{"type":"control_request","request":{"subtype":"can_use_tool","tool_name":…,"input":…}}`. **(3)** The host replies `{"type":"control_response","response":{"subtype":"success","request_id":…,"response":{"behavior":"allow","updatedInput":…}}}` or `{"behavior":"deny","message":…}`. **AskUserQuestion is answered by allowing it with `updatedInput.answers = {<question text>: <option label>}`**; Claude then gets *"Your questions have been answered: …"*. |
| U3 | **Confirmed.** A further `{"type":"user","message":{"role":"user","content":…}}` line on stdin starts a new turn in the same live process, with a `result` line per turn. |
| U4 | **Confirmed.** Each `result` line has a cumulative `modelUsage` per model (subagent tokens included), with `costUSD` marked `costBasis: list`, an estimate at list price on a subscription. Each subagent's `task_notification` carries its own `usage` (tokens, tool uses, duration). The P0 TRIAGE cost $3.97 at list (~6.7 M cache-read tokens, 48 k output) over 9 minutes. |
| U5 | **B ruled out.** A `--bg` session survives and is listed by `claude agents --json`. But `claude logs` returns raw terminal screen output (escape codes and spinner frames), there is no programmatic input (only interactive `attach`), and `--bg` refuses a folder not trusted interactively. Removed after the test. |
| U6 | **Read at the source** (code.claude.com/docs/en/agent-sdk/overview): *"Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK."* **Terrence's ruling, 2026-10-09:** *"This is not a product, it will not be bought or sold."* Ask-CK is an internal tool on each person's own Team-plan seat, so the restriction does not apply. That is the same basis as `ck-agent` since 2026-09-10, and A and C stand equally. |
| A vs C | **One protocol.** The SDK launches the same CLI with the same flags and adds typed callbacks. The probe gave identical results through both (≈13 s each). The SDK also bundles its own `claude` binary (`_bundled/claude`). P0 pointed it at the system one with `cli_path`; otherwise a seat runs two Claude versions. |

**Found by the real TRIAGE** (tb470, x230 as DUT, T33234 / T33235; device-testing `1ea546c`,
`333f06f`, `9978608`, not pushed):

- **D5 works end to end.** The session never asked. It emitted three `NOTIFY` lines, recorded
  them in the queue's Issues, and refused to work around denials (*"Doing them from this session
  would just get around the denial"*).
- **Verdict:** 0 of 2 runnable.
  - T33234 would mark all 14 cases UNSUPPORTED: the x230v2-28GS has no fixed copper port.
  - T33235 is blocked: **both scripts bind the DUT to `.setup` slot `swi_a`, which on tb470 is
    the IE520 stack member (u2), not the x230 (`swi_f`, u0).** The fix is a bench decision (swap
    the names in `tb470.static` + `apply`) or a Composer template with the slots swapped. This is
    the Composer's template step proving its worth on day one.
- **Permissions are the real design item.** In `--permission-mode auto`:
  - the classifier itself denied two commands, read-only console `show` commands with `?` help
    in config mode ("Remote Shell Writes"), **without asking the host**;
  - it sent only one command (a `ps` over ssh) to the host, which the driver denied.

  So:
  - **(a)** the window must show classifier denials (they arrive as tool results), not only
    host requests;
  - **(b)** an unattended campaign needs a **deliberate permission profile**, for example a
    device-testing allowlist for the probe, `ckcon.py` / `qmark.py` and the `ssh tbNNN` forms,
    or bench-runner gets stopped at its first console command. This joins §10 as an open item.
- **Lifetime:** the sentinel's Monitor (and its cron) keep the session alive after the campaign
  is done. The launcher needs an explicit stand-down: `/wrap-dt`, or a stop that also ends
  `sentinel.sh`. P0 stopped it by PID.
- **Left on the bench:** consoles u0–u5 still logged in after the probe. The session correctly
  would not log them out against a denial. For Terrence.

P1 onward changes the seat agents and the server. Server edits go through the
branch-and-merge procedure (SERVER-README, "Changing the backend of the hosted server").

## 10. Decisions

**Taken (Terrence, 2026-10-09):**
- **D1 — Windows: out of scope until everything else works; then remote mode (§5 route R).**
  Never a re-attached shared login. Windows is needed eventually for meeting-room demos.
- **D2 — Remote Control is denied by company policy.** Option D is gone; until W2, setup answers
  are collected before launch and a session that needs input stops (§4).
- **D3 — After-hours runs: the seat agent polls the server for scheduled jobs** (§8 (i)).
- **D4 — P0 includes one `/test-mode` TRIAGE on tb470** (probe only, no case runs; §9).

- **D5 — Blocked on a person: an informative email, then work past it; if impossible, BLOCKED and
  move to the next case.** A campaign never stops to wait (§8).

- **U6 (Terrence, 2026-10-09):** the SDK overview's third-party restriction does not apply.
  *"This is not a product, it will not be bought or sold."*

**Open (after P0, §9a):**
1. **§4 launch option: A or C.** B is ruled out. A and C share one wire protocol:
   - **A** = each seat agent speaks it directly: stdlib Python on Linux, PowerShell on Windows.
     Nothing new to install, but two implementations kept in step, as today.
   - **C** = the SDK, which needs Python on every seat. The setup script can install it on
     Windows (Terrence: acceptable). It also opens the option of **one Python agent for both
     OSes**, replacing `ck-agent.ps1`.
2. **Permission profile for unattended campaigns** (§9a): which bench commands a launched
   `/test-mode` may run without a person (allowlist in device-testing's settings, or a
   permission mode), and who owns that list.

## 11. Invariants

- K1: no credential, token or seat on the server; a session runs under the seat's own login.
- `ck.db` gains no table for this: run records and hand-offs are files under
  `ask-ck/functions/test-composer/runs/`.
- Ask-CK writes only in Test-cases; device-testing is read (queue files, logs) and is changed only by
  its own sessions (the 2026-09-11 write boundary).
- `/home/st-art/framework` stays read-only; the testbox scratch is `/tmp`.
- Every hardware run keeps `--noupdate --nodefaultcfg` (memory `framework-run-always-noupdate`) and the
  bench's standing orders: the sentinel and bench-runner gates are not bypassed by being launched from a page.
- Tests and smoke checks never write the permanent `ck.db` (scratch server).

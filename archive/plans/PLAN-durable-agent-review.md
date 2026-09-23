---
verified: 2026-09-23
---
# PLAN — A review that survives the tab (t44297 #6)

> ## Status (read first)
>
> **RETIRED 2026-09-23 → `archive/plans/`** (complete; the rule is
> `archive/plans/PLAN-restructure-2026-09-11.md` §1). Checked against the code the same day:
> the failure taxonomy, `current_late_handler`, `_late_review_handler`, `exclude_job_id` and the
> ck-agent caller watchdog are all live. D6b was scoped to assembly: the whole-script Fix path
> (`_apply_fix`) still drops `step6.review`, which SERVER-README records as deliberate ("the
> 2026-09-04 decision stands") — though that code's comment still says it mirrors assembly,
> which stopped dropping it here.
>
> **BUILT 2026-09-22 — A, C, D and E all shipped. The item is COMPLETE.** Terrence answered D6a–D6c in conversation and confirmed the
> reshaped scope (§4). The item is NOT the "durable jobs collected on reconnect" of 2026-09-09:
> it is **explicit failure attribution** — *"If it drops, list why. Be as explicit as possible
> with what part broke. I just want some basic error-handling."* Splits t44297 **#6** out of
> `PLAN-t44297-pass-followups.md`, which stays the authority for #1–#5 and points here.
>
> Written after reading the bridge rather than the 2026-09-09 item, and **the mechanism is not
> what that item describes**. #6 says "make the result durable: the agent completes the CLI call
> regardless, and the result is collected on reconnect". Verified today: there would be **no
> result to collect**. The browser kills the local `claude` process the moment the server stops
> wanting the job, and that happens the instant the caller gives up. So the durable-result half
> cannot be built on its own — §3 is the part the original item missed.

## 1. The defect, unchanged and still real

`review_script` runs on the workspace LLM, which for a seat is `claude_agent`: the prompt is
brokered through the browser to the user's own `ck-agent`. The call is therefore tethered to the
tab and the SSH session.

**2026-09-09.** A ~4-minute Opus review **failed twice** when the SSH session dropped mid-call.
The browser reported `NetworkError … local agent unreachable — is ck-agent running?` after
burning the full 228 s, and stored nothing. The prior review had already been discarded by a
re-assembly, so the script was left with **no review at all** until a manual re-fire.

Per-unit generate/fix calls are short enough to tolerate the browser path. The multi-minute
holistic review is the single call most exposed to a drop.

**Still true 2026-09-22:** `_assemble_and_store` does `step6_f.pop("review", None)` on every
re-assembly, so the review-less state is unfixed.

## 2. What is already built (verified, not assumed)

`agent_jobs.AgentJobRegistry` is considerably more developed than the 2026-09-09 item implies:

- **`submit()` blocks** the caller thread on a `threading.Event` in **two phases** — PICKUP
  (`_PICKUP_GRACE_SECONDS = 60`) then WORK (the caller's remaining budget, deliberately with no
  liveness check, because `agent.js` stops long-polling while it runs a job).
- **`session_present()`** tests two signals — polled recently, or holding a claimed job.
- **`deliver()`** wakes the caller, and **refuses a post whose `session_id` does not match** the
  job's owner.
- **A cancel is already distinguishable server-side**: `llm._call_claude_agent._on_start` stamps
  `job.result = {… "cancelled": True}` and sets the Event.
- The registry already carries **`max_idle_seconds = 1800`** (30 min) for its GC, driven from the
  long-poll via `_maybe_gc`.

**Half 2 is nearly free.** Slice B of `PLAN-generate-state-and-sequence-sanity.md` already ships
`review.code_hash`, `_gen_state.review_stale`, and a UI that renders a stale review collapsed
under a badge with per-finding evidence checks. A re-assembly moves the same script hash, so
"keep it, marked STALE" reduces to **not popping it**.

## 3. What the original item missed — the work is actively KILLED

`agent.js` polls `/api/agent/job_wanted/{job_id}` while it runs, and on `wanted === false` it
`ac.abort()`s the local run. `job_id` rides in the `/run` body specifically so the abort **kills
the local `claude` process**. Server side, `is_wanted(job_id)` is just `job_id in _inflight`, and
`_retire()` removes the job the instant `submit` returns — **including on timeout**.

So the 2026-09-09 sequence is:

1. `submit` gives up at the budget → `_retire` → the job leaves `_inflight`;
2. the browser's watcher sees `wanted === false` → aborts → **kills the local run**;
3. nothing is ever produced, so there is nothing to hold, TTL or no TTL.

**And that abandon behaviour is deliberate**, fixing a measured defect of its own (2026-09-02,
this same case): a server-side-only cancel left the broker stuck inside `await fetch(ck-agent/run)`
for the remaining budget — up to **half an hour of dead broker after every Stop** — while burning
the user's Claude seat on an answer already discarded.

**So #6 is in direct tension with a fix that exists for good reason, and the plan must not simply
undo it.** The distinction that resolves it: *why* did the caller go away?

| the caller went away because… | should the local run keep going? |
|---|---|
| the user pressed **Stop** | **No** — kill it. That is the 2026-09-02 fix, and it stays. |
| the call **timed out** | Open — see D6c |
| the **tab / SSH session dropped** | Open — see D6c |

Today all three collapse into "not in `_inflight`", so the browser cannot tell them apart. The
server already can (`cancelled: True`), which is why this is a plumbing question and not a
redesign.

## 4. Decisions — SETTLED 2026-09-22

**D6a — TTL for a held result: NONE.** Terrence asked whether 15 min was still too long, noting
most large calls have been split because of unreasonable turnaround. It is, and the number was
the wrong *kind*: a TTL here is bounded not by call duration but by how long a late answer stays
useful, which is far shorter — once the reviewer re-fires, a 12-minute-old review arriving is
noise. Under D6c a returned result is **saved into the session and displayed**, which needs no
expiry, so the parking lot disappears rather than shrinking. Nothing is held in memory awaiting a
poll.

**D6b — keep a superseded review, marked STALE: YES.** `_assemble_and_store` stops popping
`step6.review`; slice B's `review.code_hash` / `review_stale` / collapsed badge does the rest.

**D6c — what happens on a drop: SAVE WHAT EXISTS, AND NAME WHAT BROKE.** Terrence's words:
*"we should save what's in-place, and display the results as-is. If some things returned, save
and display that data; if no return from prompt and just a dead call then reflect that as well…
If SSH dropped, that should also be a unique failure result displayed as such. In a nutshell: if
it drops, list why."*

So the build is an **error taxonomy**, not a durability layer. Most signals already exist
server-side and are collapsed into two generic messages:

| what broke | detectable | today |
|---|---|---|
| nothing claimed the job | `unclaimed` | already explicit, and good |
| user pressed Stop | `cancelled` | explicit |
| the CLI itself errored | `error=True` | passed through |
| **claimed, then silent past budget** | yes | generic "did not respond in time" |
| **ck-agent unreachable from the tab** | browser only | `NetworkError` locally; server just times out |
| **tab / SSH dropped after claiming** | inferable (claimed, no result, session absent) | same generic message |

The bottom three are the gap: three different failures, one message.

**Scope confirmed by Terrence (2026-09-22): the taxonomy, saving late results, AND killing the
orphaned run.**

### A correction to the premise, recorded because it cost real money

Terrence's D6c assumed a dropped tab "won't stop the call from resolving (a non-issue)". Verified:
it does not stop the local run, but the result is lost anyway — the tab that would POST it is
gone, and a reloaded tab starts a fresh broker loop with no memory of the job. Meanwhile
`ck_agent.run_claude` bounds the child with `proc.communicate(timeout=timeout)`, so the orphan is
**not** unbounded: it runs to the budget and is then killed as a process group. With the 1800 s
floor that is up to **half an hour of the user's own Claude seat spent on a discarded answer** —
precisely the waste the 2026-09-02 `_RUNNING` comment describes for the cancel case, arriving by
a different route.

## 5. The build

**A. ✅ BUILT — taxonomy (server, `agent_jobs`).** Split the generic timeout by what is knowable at
the moment the wait ends: was the job ever claimed, and is the session still present? Each exit
carries a distinct, quotable reason rather than one sentence covering three causes.

**B. ✅ ALREADY BUILT — no change needed.** Written as work; reading `agent.js` showed it is
done. On a failed `fetch(CK_AGENT_URL + '/run')` the catch sets
`content = 'ERROR: local agent unreachable — is ck-agent running? ' + e` and the loop still POSTs
to `/api/agent/result`, so the caller already receives that exact sentence. The gap is only when
the BROWSER itself is gone and can report nothing — which is A.

**C. ✅ BUILT — a late result is saved (`agent_jobs` + `llm` + `review_script`).** `deliver()`
looked only in `_inflight`, and `_retire` had already dropped the job, so a reply that arrived
after the caller gave up was discarded and the seat that produced it wasted. Now `_retire` keeps
a job that carries a late handler, `deliver` recognises it and hands the result to that handler
immediately.

**Not a parking lot** (D6a): nothing waits in memory to be polled for, the result is applied on
arrival, and the retained entry — which exists only so `deliver` can still RECOGNISE the job —
expires on the registry's existing `max_idle`, not a new horizon.

The handler reached `_call_claude_agent` through a **ContextVar** (`current_late_handler`), the
pattern `current_session_id` / `current_llm_call_id` already use, rather than threading a
callback through `run_prompt` → `_call_llm_with_meta` → `_call_claude_agent` → `submit`. It is
attached to the job in `_on_start`, which already owns the job object for the cancel hook.

`_late_review_handler` captures everything at DISPATCH time — sequence, lint findings, the code
being reviewed — because the script may have moved on by the time it runs. The stored review is
bound to the code it actually read (`code_hash`), so slice B marks it stale rather than
pretending it describes the current file, and it carries `late: True`. Three guards, each with a
test: a **cancelled** job is never resurrected (a Stop must not have the answer appear anyway); a
late deliver from the **wrong session** is refused, exactly as the in-flight path is; and a review
the reviewer fired AFTER this one was dispatched is never clobbered — newer by intent beats newer
by arrival.

**D. ✅ BUILT — stop popping the review** (D6b).

**E. ✅ BUILT — kill the orphaned run (`ck_agent.py`).** The machinery already exists — `_RUNNING`,
`cancel_job()` killing the whole process group, and a `/cancel` route. What is missing is a
caller when the tab is gone. The server cannot reach the agent (the browser calls the agent, not
the reverse), so the only local signal is the requesting HTTP client going away: watch the
connection while the child runs and `cancel_job` on disconnect.

**Tests** fake `llm._run_cli` / the agent bridge — never a real CLI
(`[[claude-code-cli-transport-contract]]`). Backend + bridge + agent, so production reloads on
each backend save: one save.

## 6. Found while building — `session_present` had a latent trap

`session_present()` counts a CLAIMED job as proof its session is alive ("a broker that is BUSY
running a job is not polling either"). It used to carry an `exclude` parameter, removed as dead
with the note that *"the caller's own job cannot pollute this: only CLAIMED jobs count, and a
caller only asks while its job is unclaimed"* — true of the single call site that existed then.

A's taxonomy added a SECOND call site that asks about a job which IS claimed, so the job vouched
for its own session and every dropped tab read as present: `session_dropped` could never fire.
`exclude_job_id` is reinstated with that history recorded, and
`test_session_dropped_is_named_as_a_closed_tab_not_a_slow_model` is what caught it.

The lesson is in the removal note, not the code: "unreachable" was a property of the call sites,
not of the function, and nothing said so.

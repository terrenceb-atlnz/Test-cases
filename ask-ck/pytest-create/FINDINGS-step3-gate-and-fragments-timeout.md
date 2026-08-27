# FINDINGS — two blockers in the PyTest Creator pipeline (2026-08-27)

**Status:** BOTH FIXED. Fix 1 is committed **and pushed** (`23178e0`). Fix 2 is committed
locally and **deliberately not pushed** — it is awaiting review. Neither was verified by the
test suite; see §3 before trusting either.

Two independent defects, found in sequence while driving a real case (`AWPTCM-T44191`). The
first made step 3 impossible to confirm; the second made step 4 time out. Together they blocked
the pipeline from '3. Script Search' onward.

Line numbers are **as of 2026-08-27** and are hints — prefer the symbol names.

---

## 1. Step 3 could not be confirmed through the current UI

### Symptom

With 32/32 sequence steps covered, 34 scripts chosen across 32 steps, and *"Saved"* displayed,
**Confirm Step 3** returned:

```
409  Nothing to confirm yet for '3. Script Search' (missing matches).
```

### Root cause

`confirm_step` gated on two fields, neither of which a current session has:

```python
ran = bool(content.get("provenance")) or content.get(required_field) is not None
```

- **`step3.provenance` is never written.** Only `sess.step2`, `sess.step5`, step 6 and step 8
  record provenance. Step 3 never has.
- **`step3.matches` comes only from the whole-case `POST /suggest_scripts`** — and that endpoint
  **left the UI on 2026-08-20**, when the per-sequence-step picker replaced it. The frontend now
  calls `/suggest_scripts_step` exclusively (`pytest.js:606`, `:637`). The whole-case path
  survives at `pytest.js:430` only as a **label string** for a provenance panel that reads
  `st3.provenance` — a field nothing populates, so that panel can never render.

The replacement flow writes elsewhere and the gate was never taught about it:

| Writer | Writes |
|---|---|
| `suggest_scripts` (whole-case, **unreachable from the UI**) | `matches`, `user_inputs`, `mechanical_considered` |
| `_persist_step_matches` (per-step suggest) | `step_matches` only |
| `save_selections` | `selections`, `records`, `user_inputs` |

### Why it went unnoticed

**Every `pt-` session in `ck.db` predates the change** — all four carry `matches` and an empty
`step_matches`, so they all still pass. Only sessions created after 2026-08-26 hit it.

### Downstream impact

`gather_fragments` calls `_require_confirmed(sess, "step3", ...)`, so **step 4 was unreachable
behind it**. The pipeline was blocked from step 3 for every new case.

### The fix

`confirm_step` now also accepts the per-step flow's evidence that the step ran:

```python
if not ran and required_field == "matches":
    ran = bool(content.get("step_matches")) or bool(content.get("selections"))
```

- `step_matches` — written per sequence step by `_persist_step_matches` **even when that step
  matched nothing**, so it preserves the "an empty list is a legitimate, already-run answer"
  property the surrounding check exists for.
- `selections` — picks made by keyword search, which is reachable without ever invoking Suggest.

Scoped to `matches` only: step 5 writes real `provenance`, so `fragments` keeps the original
predicate untouched.

### Verification

Four shapes planted in a throwaway `ck.db` copy (`tool/ckdb_scratch.py`, `/health`
`is_permanent_db: false`) and driven through the real endpoint:

| step3 shape | before | after |
|---|---|---|
| `step_matches` only (the reported case) | 409 | **200** |
| nothing ran | 409 | **409** — still rejects |
| `selections` only (keyword-search picks) | 409 | **200** |
| legacy `matches` (pre-2026-08-26) | 200 | **200** — unchanged |

The counterfactual was **measured, not assumed**: the fix was stashed, `--reload` picked up the
reverted file, and the first and third returned 409; restoring it returned 200.

---

## 2. Step 4 (Fragments) timed out at exactly 300s on `claude_agent`

### Symptom

```
2026-08-27T03:23:43+00:00 · /api/pytest-create/gather_fragments/AWPTCM-T44191
· pt_gather_fragments.jinja · claude/opus via claude_agent · 300000ms · — tok
⚠ ERROR: local Claude agent did not respond in time.
         Is ck-agent running on your machine and this tab open?
```

`300000ms` is exactly the requested 300s, and no usage was returned.

### Root cause — two independent problems

**(a) `claude_agent` is the only transport that does not get the whole-response floor.**
`_call_llm_raw` passes the raw value for it, while the two branches directly below wrap
`claude_code` and `grok_cli` in `_cli_timeout()`:

```python
if provider == "claude" and auth_method == "claude_agent":
    return _call_claude_agent(..., timeout=timeout)              # raw
if provider == "claude" and auth_method == "claude_code":
    return _call_claude_code_headless(..., timeout=_cli_timeout(timeout))
```

With `_CLI_WHOLE_RESPONSE_FLOOR = 1800` and `_is_long_call(t) = t >= 120`, the same call gets:

| Transport | Effective wait |
|---|---|
| `claude_code` / `grok_cli` | **1800s** — `max(300, 1800)` |
| `local_llm` (vLLM) | **600s** — `read_timeout = max(300, 600)` |
| `claude_agent` | **300s** — the raw value |

**(b) The server's wait and the browser's allowance were set independently.** `registry.submit`
received the timeout but `_Job` had no field for it, `/api/agent/next` returned only
`{job_id, prompt, model}`, and so `agent.js` hard-coded `timeout: 600`. The server abandoned the
job at **300s** while the user's machine was allowed **600s** — finishing work whose job had
already been discarded.

### The error message blames the wrong component

It comes from `agent_jobs.py` and fires whenever the *server's* wait expires, saying nothing
about whether ck-agent was healthy. This has misled before: `routers/wizard/export.py` carries a
comment about the same message "blaming the user's ck-agent for a deadlock the server caused".
(That earlier case was a missing `run_in_threadpool`; `gather_fragments` does wrap its call, so
it is not that bug.)

### The fixes

**A — propagate the timeout, so one server-defined number governs both ends**

| File | Change |
|---|---|
| `agent_jobs.py` | `_Job` gains a `timeout` slot (defaulted, so existing 3-arg construction in tests still works); `submit` stores it |
| `agent_jobs.py` | `next_job` returns `(job_id, prompt, model, timeout)` |
| `routers/agent_bridge.py` | `/api/agent/next` includes `timeout` in the job payload |
| `static/js/agent.js` | sends `timeout: job.timeout \|\| 600` instead of a hard-coded `600`; the fallback covers a server older than this change |

**B — give the heaviest prompt a budget matching its siblings**

`gather_fragments` raised **300 → 600**, matching `generate_script` and `fix_script`. It carries
the whole sequence plus every chosen script's symbols and review notes — the largest context in
the pipeline — and had half their budget:

```
extract_sequence   600
suggest_scripts    300
suggest_step       300
gather_fragments   300  ->  600
generate_script    600
fix_script         600
```

### Verification

- **Registry round trip, run directly:** `next_job` returns 4 fields with `timeout=600`;
  `deliver` still wakes the blocked `submit`; legacy `_Job(session, prompt, model)` still
  constructs with `timeout=0`.
- `/api/agent/next` still serves on a scratch server (`{"job": null}`), proving the route
  unpacks the new tuple.
- `bun build` over the full JS module graph passes.
- Both invariant guards pass; the permanent `ck.db` was never written (mtime unchanged).

---

## 3. Testing caveat — read before trusting any of the above

**The gate cannot run on this host.** `pytest` is absent from `.venv`, `npm` is off PATH and
`node_modules/` does not exist, so `./tool/run_tests.sh` exits 2 after the two guards.
`setup.sh` installs neither (it only names `requirements-dev.txt` in a hint).

Everything here was verified by direct endpoint calls, an in-process registry test,
`bun build`, the two guards and `tool/run_scratch_server.sh` — **not** by pytest or vitest.

Two test facts were established by reading, not running, and should be confirmed when the gate
is revived:

- `tests/test_error_signals_batch_d.py` and `tests/test_security_batch2.py` construct
  `_Job(session, prompt, model)` with three arguments — preserved by the new parameter's default.
- `test_next_job_still_returns_a_queued_job` asserts `got[1] == "prompt-text"` by **index**, not
  by tuple unpacking, so the 4-tuple does not break it.

## 4. Deliberately not done

- **`claude_agent` still does not get `_cli_timeout()`** (option C was not taken). With A and B
  it now waits 600s rather than 300s, but it remains the only transport without the 1800s floor.
- **Server and agent now share the same number, which leaves a race**: the local `claude` run and
  the server's wait expire together, so the agent's own honest error ("claude CLI timed out
  after Ns") will usually lose to the registry's generic message. Giving the agent a slightly
  smaller budget than the server's wait would fix that; it was not done.
- **The dead provenance mount at `pytest.js:430`** still points at the retired whole-case
  endpoint and reads a field nothing writes, so that panel is permanently empty.
- **The whole-case `suggest_scripts` endpoint** remains, unreachable from the UI but still valid
  for headless/batch use — the same argument that keeps `claude_code` alive.

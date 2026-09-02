---
name: browser-fanout-connection-ceiling
description: "A page cannot fan out N blocking requests to Ask CK — HTTP/1.1 allows 6 connections per origin and they starve the agent broker's own poll; dispatch as ONE request + polling"
metadata:
  type: project
  verified: 2026-09-02
---

**Never fan out N blocking requests from the Ask CK page. The browser allows 6 connections
per origin (HTTP/1.1), and request 7 onward simply waits.** This is fatal here rather than
merely slow, because the `claude_agent` transport is *brokered by the same page*: the server
queues a job and the browser's `ckBrokerLoop` collects it over `GET /api/agent/next`. Saturate
the connection pool with work requests and the page can no longer collect the work it just
queued — it starves its own broker.

**Measured 2026-09-02** on the 30-unit PyTest Creator fan-out (AWPTCM-T44297). The symptom did
NOT look like a connection limit. Six units burned the full 1800 s budget and failed with
"local Claude agent did not respond in time"; the connections they released then let tc8/tc9
through normally. So it read as *sporadic LLM timeouts*, not as a ceiling — rolling starvation,
not a clean deadlock. The evidence that identified it: `/api/agent/status` showing
`pending: 5`, `session_active: false`, and **zero `claude` child processes** — jobs queued,
nobody able to fetch them.

**How to apply.** Any batch operation is ONE request plus polling, never N requests:
`POST /api/pytest-create/generate_units/{key}` queues everything server-side
(`asyncio.create_task` + `Semaphore(_PT_UNIT_DISPATCH_MAX)`, currently 8) and returns; the page
polls `GET /api/pytest-create/units_status/{key}`. That is the pattern to copy for any future
fan-out. Server-side concurrency is bounded separately by anyio's default 40-thread pool —
`run_in_threadpool` holds a thread for the whole blocking call, so the dispatch semaphore must
stay well under it.

The browser broker itself was made concurrent in the same change (`ckBrokerWorkers`, default 4,
`localStorage.ckBrokerWorkers`, clamped 1..16). Note `ckBrokerActive` exists so a worker that is
*inside* a long job is not judged stale — busy is alive. Related:
[[claude-code-cli-transport-contract]], [[pytest-creator-askck]], [[askck-lan-hosting]].

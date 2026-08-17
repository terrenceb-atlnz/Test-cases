---
name: auth-and-case-locking-plan
description: "Ask-CK's intended end-state is real multi-user (Terrence, 2026-07-27g) with a per-case session lockout so concurrent overwrites are impossible; PLAN-auth-and-case-locking.md, 6 decisions deferred"
metadata: 
  node_type: memory
  type: project
  modified: 2026-07-27T03:28:31.978Z
  originSessionId: 7daaa873-01d4-42ab-836d-65d158c2ca74
---

**Terrence's decision (2026-07-27g):** real multi-user is the **intended end-use** of Ask-CK —
not localhost-forever. He added a requirement the adversarial review had not raised:

> *"There should be a session-lockout for each test case selected so concurrent overwrites are
> impossible, both for the PyTest Creator and for the test-case generator."*

Captured as `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` (commit `94b98cf`). **Plan only —
no code written.** Supersedes the old "add auth before shared deployment" docs caveat, which was
never tracked work.

**The concurrency bug is LIVE TODAY and does not need a second user** — two browser tabs on one
case is enough. Sessions are keyed by case with **no owner column**; `db.py:918 _write_session` is
an unconditional whole-blob upsert (`ON CONFLICT DO UPDATE SET payload=excluded.payload`); 32 write
paths reach it (14 `_persist_session`, 18 `_pt_persist`). Second write silently wins, no error, no
trace. NOTE this does not contradict the review's refutation of the within-request race once
cited as `wizard.py:1648` (that file is now the `routers/wizard/` package — the line number is
dead) — the refutation was correct; this is read-modify-write across *separate* requests,
which event-loop serialisation cannot prevent.

**`X-CK-Session` is NOT a credential.** `static/js/session.js` invents it in the browser and the
server never verifies it. It correctly scopes agent-bridge jobs per TAB (deliberately per-tab, not
per-user — see [[llm-provenance-portability]] / PLAN-per-user-agent) and nothing more. Mistaking it
for auth would be a load-bearing error.

**Phases:** 1 locking (`case_locks` table; enforce at the TWO persist helpers, not 32 call sites,
plus a `rev` optimistic-concurrency backstop) · 2 identity (SSO/proxy strongly preferred over
app-managed credentials) · 3 attribution + TLS (both shipped nginx examples are plain `listen 80`
with zero auth/TLS and need replacing, not extending).

**Phase 1 is sequenced FIRST deliberately** and is not gated on auth: it can hold locks by session
id and upgrade to user id with no schema change. Sizing: 1 = M, 2 = M–L, 3 = S–M.

**How to apply:** next session, start by resolving the six open decisions in §3 of the plan —
especially D1 (where identity comes from), which is likely an org/IT call rather than ours. Do not
start Phase 2 before D1/D2 are settled. `case_locks` is an ADDITIVE migration applied in place —
`ck.db` is never rebuilt ([[db-is-permanent-source]]).

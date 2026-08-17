---
name: auth-and-case-locking-plan
description: "Ask-CK's intended end-state is real multi-user (Terrence, 2026-07-27g); Phase 1 per-case locking SHIPPED 2026-07-29 as an IN-MEMORY registry (no case_locks table — that would mutate the permanent ck.db); Phases 2-3 still planned, gated on D1/D2"
metadata: 
  node_type: memory
  type: project
  modified: 2026-08-17T00:00:00.000Z
  originSessionId: 7daaa873-01d4-42ab-836d-65d158c2ca74
---

**Terrence's decision (2026-07-27g):** real multi-user is the **intended end-use** of Ask-CK —
not localhost-forever. He added a requirement the adversarial review had not raised:

> *"There should be a session-lockout for each test case selected so concurrent overwrites are
> impossible, both for the PyTest Creator and for the test-case generator."*

Captured as `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` (commit `94b98cf`).

**Phase 1 (locking) SHIPPED 2026-07-29 — `CK_server/locks.py`.** The bug it closed: sessions are
keyed by case with **no owner column** and every persist is an unconditional whole-blob upsert, so
two tabs on one case each read, edit and save, and the second write silently won — no error, no
trace. That is read-modify-write across *separate* requests, which event-loop serialisation cannot
prevent. (It does **not** contradict the review's refutation of the within-request race once cited
as `wizard.py:1648` — that refutation was correct, and that file is now the `routers/wizard/`
package anyway, so the line number is dead.)

**How it was actually built — two deliberate deviations from the plan's §4 design.** Both were
forced by the `ck.db` invariant, and this is the part most likely to be got wrong later:

1. **Locks are an in-process dict, NOT a `case_locks` table.**
2. **`rev` rides inside the session payload JSON, NOT a column.**

A durable table or a new column would have been the repo's **first in-place schema mutation of the
permanent database** — `ck.db` is built once and `tool/build_db.py` refuses to run, so there is no
migration path. Terrence's call was to leave the schema untouched. Enforcement is at the **two
persist choke points**, not the 32 call sites.

**The load-bearing caveat:** the registry is authoritative **only because the server runs as one
process** (`uvicorn … --reload`, no `--workers`; the nginx example proxies a single upstream).
Running multi-worker without promoting it to a shared store **silently reintroduces the overwrite
bug**. `locks.py`'s module docstring says so; keep that warning wherever the registry goes.

Behaviour worth knowing: a tab that does **not** hold the lock gets a **read-only view** of the
last saved state, not an error, and the handler mutates nothing on that path — no backfill, no
hydration write (either would 409 against the holder's lock).

**`X-CK-Session` is NOT a credential.** `static/js/session.js` invents it in the browser and the
server never verifies it. It correctly scopes agent-bridge jobs per TAB (deliberately per-tab, not
per-user — see [[llm-provenance-portability]] / PLAN-per-user-agent) and nothing more. It is also
what holds a lock today; Phase 2 upgrades that to a real user id with **no schema change**, which
is exactly why Phase 1 was sequenced first and was never gated on auth.

**Still planned:** Phase 2 identity (SSO/proxy strongly preferred over app-managed credentials) ·
Phase 3 attribution + TLS (both shipped nginx examples are plain `listen 80` with zero auth/TLS and
need replacing, not extending). Sizing: 2 = M–L, 3 = S–M.

**How to apply:** Phase 1 is done — do not re-implement it, and **do not add a `case_locks` table**;
that option was considered and deliberately rejected ([[db-is-permanent-source]]). Before starting
Phase 2, resolve the open decisions in §3 of the plan, especially **D1 (where identity comes from)**,
which is likely an org/IT call rather than ours. If you ever add workers or a second process, fix
the lock registry first.

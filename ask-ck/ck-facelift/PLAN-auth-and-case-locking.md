# PLAN — Authentication + per-case session locking (multi-user Ask-CK)

> ## Status (read first)
>
> **PHASE 1 (case locking) — DONE 2026-07-29.** Phases 2 (identity) and 3 (attribution +
> TLS) remain PLANNED and are gated on the org identity decision (D1/D2). Captured
> 2026-07-27g at Terrence's direction after the adversarial review closed; Terrence chose
> **Option B (real multi-user)** as the intended end-state and added a hard requirement the
> review had not raised:
>
> ### Phase 1 as built — TWO deviations from §4, both forced by the ck.db invariant
>
> The §4 design wanted a durable `case_locks` table + a `rev` column. Investigation
> confirmed **ck.db is immutable by design** — `tool/build_db.py` refuses to rebuild, there
> is no runtime DDL and no migration framework — so adding a table/column would have been the
> repo's first in-place schema mutation of the permanent DB. Terrence's call was to leave the
> schema untouched. So Phase 1 shipped **with ZERO ck.db schema change**:
>
> 1. **Locks live in memory** (`CK_server/locks.py`), not in a table. Authoritative because
>    the server is single-process today (`uvicorn … --reload`, no `--workers`; nginx example =
>    one upstream). `locks.py` + SERVER-README carry a prominent caveat: going multi-worker
>    without promoting the registry to a shared store silently reintroduces the overwrite bug.
> 2. **`rev` rides inside the session `payload` JSON** (a field on both session models), not a
>    column. The optimistic compare-and-swap (`locks.next_rev`) runs at both persist choke
>    points and covers the one gap the in-memory lock cannot: a restart or a second process
>    (the window `pytest_create._pt_get` already documents) clobbering with a stale copy.
>
> Guard is at the two choke points only — `session_store.persist_session` +
> `pytest_create._pt_persist` (holder = the `X-CK-Session` ContextVar, no signature change) —
> raising `locks.LockError` → HTTP 409 via one app-wide handler. `load_case` acquires on load
> and serves a read-only snapshot when another holds it (D6a). Endpoints:
> `POST /api/locks/{kind}/{case_key}/acquire|heartbeat|release`. Frontend `static/js/locks.js`:
> acquire-on-load, 5-min heartbeat, `navigator.sendBeacon` release on `pagehide`, read-only
> banner + disabled inputs + "Take over" once idle. Tests: `tests/test_case_locks.py` (24) +
> `tests/test_no_unguarded_session_write.py` (structural — no write bypasses the guard) +
> `js-tests/locks.spec.js` (7). Decisions D3–D6 implemented as recommended; D1/D2 still open.
>
> **Original requirement (unchanged):**
>
> > *"There should be a session-lockout for each test case selected so concurrent overwrites
> > are impossible, both for the PyTest Creator and for the test-case generator."*
>
> This supersedes the standing "add auth before shared deployment" caveat in README /
> SERVER-README, which was a docs note and never tracked work.
>
> **Current posture (after `6eaa43e`):** binds `127.0.0.1` by default, so practical exposure
> today is zero. That converts this from a live risk into a **prerequisite for the next
> hosting step** — nothing here is urgent, but nothing here is optional either if the tool
> is going to be used by more than one engineer.

---

## 1. Why this is needed

Two separate problems that happen to share a solution — you cannot lock a case to a user
until you know who the user is.

### 1.1 There is no authentication of any kind

Verified during the review: no `Depends()` in any router does authentication, there is no
middleware that checks identity, and no endpoint inspects `request.client`. The only header
in play is `X-CK-Session`, and it is **not a credential**:

```js
// static/js/session.js
let id = sessionStorage.getItem('ckSessionId');   // the tab invents it
headers.set('X-CK-Session', CK_SESSION_ID);       // server never verifies it
```

It is a *correlation* id. It correctly scopes agent-bridge jobs to a browser tab (hardened
2026-07-27d), and that is all it does. **Anyone can send any value.** A future reader must
not mistake it for auth — that mistake would be load-bearing.

### 1.2 Concurrent edits silently destroy each other

This is the sharper problem and it is real **today**, even single-user across two tabs.

| Fact | Location |
|---|---|
| Sessions are keyed by case ONLY — no owner column | `sessions` table: `id`, `kind`, `case_key`, `payload`, `llm_config`, `updated_at` |
| In-memory stores are plain dicts keyed by case | `wizard.py:51 sessions`, `pytest_create.py:44 pt_sessions` |
| Every persist is an unconditional whole-blob overwrite | `db.py:918 _write_session` — `ON CONFLICT(id) DO UPDATE SET payload=excluded.payload` |
| 32 write paths reach it | 14 × `_persist_session` (wizard), 18 × `_pt_persist` (pt) |

So: two people (or one person in two tabs) open `AWPTCM-T33234`. Both read the session, both
edit, both save. **The second write silently wins and the first person's work is gone** — no
error, no conflict, no trace. The `updated_at` column records only that *something* wrote.

Note the review already refuted a *narrower* version of this (`wizard.py:1648`, "two session
objects race") on the grounds that FastAPI cannot interleave two `await`-free handlers. That
refutation was correct and is not contradicted here: **this is not a within-request race.**
It is a read-modify-write across *separate* requests, seconds or minutes apart, which no
amount of event-loop serialisation prevents.

---

## 2. Scope

**In scope**
- Real server-side identity: who is making this request
- Per-case locking for BOTH tools (Generator wizard + PyTest Creator)
- Ownership + attribution on the durable side effects (export, `push_to_zephyr`, testbox runs)
- TLS termination for a hosted deployment

**Out of scope (explicitly)**
- Per-field / operational-transform collaborative editing. The requirement is *"concurrent
  overwrites are impossible"*, not *"concurrent editing works"*. One editor at a time per
  case is the target.
- Role-based permissions. Every authenticated engineer is equally trusted; this is about
  attribution and collision, not privilege tiers.
- Replacing the per-user LLM seat model. `PLAN-per-user-agent.md` already solves seat
  isolation correctly and is unaffected — though §6 notes one interaction.

---

## 3. Decisions still open (need Terrence)

These change the shape of the work and should be settled before Phase 1.

| # | Question | Options | Notes / recommendation |
|---|---|---|---|
| D1 | **Where does identity come from?** | (a) org SSO / OIDC via an auth proxy; (b) nginx + LDAP/AD; (c) app-managed users + password hashes | **(a) or (b) strongly preferred.** (c) means Ask-CK owns credential storage, reset flows and hashing — a large, permanent liability for a lab tool. Prefer the org's existing identity. |
| D2 | **Proxy-trusted or app-verified?** | (a) trust a header (`X-Forwarded-User`) set by a trusted proxy; (b) verify a signed token in-app | (a) is far simpler and standard behind nginx — but the app MUST then refuse to start on `0.0.0.0` without the proxy, or the header is trivially spoofable. That guard is part of the work. |
| D3 | **Lock granularity** | (a) per case, per tool (a case can be in the Generator and PyTest Creator at once); (b) per case, both tools | **(a).** They edit different session rows (`wizard` vs `pt` kinds) and different artefacts; blocking both is friction with no safety gain. |
| D4 | **Lock expiry** | (a) heartbeat + idle timeout; (b) explicit release only; (c) hard TTL | **(a), ~15 min idle.** (b) strands cases behind closed laptops; (c) can yank a lock from someone actively typing. |
| D5 | **Steal/override** | (a) anyone may force-take a stale lock; (b) only after expiry; (c) admin-only | **(b) + a visible "held by X since HH:MM" banner.** Matches the existing hidden-admin-panel convention if an override is ever needed. |
| D6 | **Read-only viewing while locked** | (a) yes, banner + inputs disabled; (b) refuse to load | **(a).** Reading someone else's in-progress case is useful and harmless. |

---

## 4. Phases

Each phase is independently shippable and leaves the tree green. **Phase 1 delivers the
concurrency safety Terrence asked for and does not depend on auth landing first** — it can
use the existing per-tab session id as the holder identity, then upgrade to real users in
Phase 2 with no schema change.

### Phase 1 — Case locking (the concurrency requirement)

*Deliverable: two people cannot silently overwrite each other, in either tool.*

1. **Schema** — new `case_locks` table (additive; `ck.db` is the permanent source of truth,
   so this is a migration, not a rebuild):

   ```sql
   CREATE TABLE case_locks (
     lock_id     TEXT PRIMARY KEY,   -- '<kind>:<case_key>'  e.g. 'wizard:AWPTCM-T33234'
     kind        TEXT NOT NULL CHECK (kind IN ('wizard','pt')),
     case_key    TEXT NOT NULL,
     holder      TEXT NOT NULL,      -- session id in P1; verified user id from P2
     holder_label TEXT,              -- display name for the UI banner
     acquired_at TEXT NOT NULL,
     heartbeat_at TEXT NOT NULL
   );
   ```

2. **Guard at the choke point, not at 32 call sites.** Every write already funnels through
   `_persist_session` (wizard) and `_pt_persist` (pt). Enforce there:
   *hold the lock or raise 409.* Auditing 32 individual handlers would guarantee a miss —
   and the review's own lesson (§5 of the backlog) is to prefer one mechanical choke point
   plus a test that proves nothing bypasses it.

3. **Optimistic-concurrency backstop.** Add a monotonic `rev` to each session payload and
   make `_write_session` conditional (`WHERE rev = :expected_rev`), 409 on mismatch. Belt
   and braces: the lock prevents the *situation*, `rev` prevents the *write* even if a lock
   is somehow bypassed or force-stolen mid-edit.

4. **Endpoints** — `POST /api/locks/{kind}/{case_key}/acquire | heartbeat | release`,
   and lock state included in `load_case` responses.

5. **Frontend** — acquire on case load, heartbeat on a timer, release on unload
   (`navigator.sendBeacon`). When the lock is held by someone else: banner + disabled inputs
   (D6a), reusing the amber `.badge-warning` / `.pt-stale-warning` idiom already established.

6. **Tests** — second acquire is refused; write without the lock 409s; expiry frees it;
   heartbeat prevents expiry; **a structural test that every session write goes through the
   guarded helper** (same AST-sweep discipline as the batch-B event-loop test).

### Phase 2 — Identity

*Deliverable: the server knows who you are; the lock holder becomes a person.*

1. Resolve D1/D2. Assuming proxy-trusted SSO: read the trusted header, resolve to a stable
   user id, expose via a `current_user` dependency + ContextVar (mirroring the existing
   `current_session_id` pattern in `main.py`).
2. **Fail-closed startup guard**: refuse to bind `0.0.0.0` unless either a trusted-proxy
   mode is configured or auth is explicitly disabled for localhost dev
   (`CK_ALLOW_INSECURE=1`). Prevents the "header is spoofable" trap in D2a.
3. Migrate `case_locks.holder` from session id → user id. Same column, better value.
4. `X-CK-Session` **stays** as the per-tab correlation id for the agent bridge — it is
   correct at that job, and Phase 2 must not conflate the two. Document the distinction
   in SERVER-README so the trap in §1.1 cannot be re-introduced.

### Phase 3 — Attribution + transport

*Deliverable: durable side effects are traceable to a person; the deployment is encrypted.*

1. Stamp `created_by` / `last_modified_by` into session payloads and the exported
   `*-session.json`.
2. Record the acting user on the sharp endpoints — `push_to_zephyr` (already the highest-
   consequence action: it spends the shared `JIRA_KEY`), testbox `/run`, and admin resets.
3. nginx: TLS + auth in front. Both existing examples (`nginx.conf.example`,
   `nginx-drafting-server.conf.example`) are plain `listen 80` reverse proxies with no auth
   and no TLS — they need replacing, not extending, and they are currently the most likely
   thing someone would copy into a real deployment.

---

## 5. Sequencing note

**Phase 1 first, deliberately.** The concurrency bug is the one that destroys work, it is
live today (two tabs is enough), and it does not need identity to be fixed. Auth is the
bigger and slower piece and is gated on an org decision (D1) that may not be ours to make.
Shipping locking first means the data-loss risk closes even if identity stalls.

---

## 6. Interactions to watch

- **`PLAN-per-user-agent.md`** — the agent bridge is keyed by `X-CK-Session`, deliberately
  per-*tab*, not per-user (one engineer may legitimately run two tabs, each brokering to
  their own local `ck-agent`). Phase 2 must not "helpfully" re-key it to the user id.
- **Backfilled sessions** — `_backfill_from_refined` rehydrates Complete cases from disk
  and now marks reviews confirmed (batch A). A lock must not be required to *read* a
  backfilled case, or browsing finished work starts demanding locks.
- **Long testbox runs** — a PyTest run can exceed the idle timeout while the operator waits.
  The lock must heartbeat for the duration of an active run, not just on UI interaction, or
  a run will drop its own lock mid-flight.
- **`ck.db` is the permanent source of truth** (memory `db-is-permanent-source`). Adding
  `case_locks` is an additive migration applied in place — never a rebuild, never a courier
  file.

---

## 7. Rough sizing

| Phase | Size | Gated on |
|---|---|---|
| 1 — locking | ✅ **DONE 2026-07-29** — in-memory registry (no ck.db table), two choke points, frontend banner, 31 tests | nothing |
| 2 — identity | **M–L** | D1/D2 (likely an org/IT decision) |
| 3 — attribution + TLS | **S–M** | Phase 2 |

Phase 1 is the whole of what was asked for in the concurrency requirement and is not blocked
on anything.

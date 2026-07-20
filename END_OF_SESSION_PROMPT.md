# End-of-Session Doc-Sync Prompt (Ask-CK)

Paste this at the end of a session after doing work on Ask-CK. It tells Claude
exactly which docs to reconcile and how each one should be treated, so nothing
goes stale and nothing gets rewritten that shouldn't be.

---

**Prompt to paste:**

> We just finished a chunk of work on Ask-CK. Please update the documentation so it
> matches reality, following the rules below. First **read the actual current state**
> (code, `git status`, `git log` for this session's commits) — don't document from
> memory. Then reconcile each doc, sweep for stale claims, and finish by committing +
> pushing the doc changes to `main`.
>
> **1. Living reference docs — edit in place so they describe the CURRENT system:**
> - `README.md` — repo entry point (setup, getting started, feature status table, data-layer overview). Update the status table + any changed setup/behavior.
> - `ask-ck/CK-main/SERVER-README.md` — the deep technical reference (architecture, data layer, endpoints, admin panel, LLM config, workflow). This is where most substantive changes land.
> - `ask-ck/CK-main/CK_server/README.md` — thin pointer file; only touch if the pointers change.
> - `ask-ck/CK-main/CK_server/static/js/README.md` — front-end ES-module conventions; update if the JS module structure changed.
>
> **2. Dated logs — APPEND a new dated entry at the top; never rewrite old entries:**
> - `ask-ck/objective-drafting/PROGRESS.md` — the "current status / what shipped / how to continue" handoff log. Add a `## Latest session (YYYY-MM-DD…)` entry.
> - `SESSION_STATE.md` — long-form session history. Add a `## Session Close / Handoff (YYYY-MM-DD…)` entry at the end. If an old entry is now wrong, add a one-line "superseded by …" note pointing to the new entry — do NOT edit the old text (the log's value is that it's frozen).
>
> **3. Plan / provenance docs — update status headers, don't rewrite history:**
> - `ask-ck/ck-facelift/PLAN-*.md` and `ask-ck/pytest-create/PLAN-pytest-creator.md` — if a plan advanced or a decision changed, update its **status header** (mark phases done, add a "superseded/final-state" note). Leave the historical body intact; add banners rather than deleting.
> - Docs that describe retired pipelines or deleted files must carry a "⚠ Historical / superseded" banner pointing at the current source of truth (`ask-ck/var/ck.db`).
>
> **4. Persistent memory — update if a durable fact changed:**
> - Reconcile `MEMORY.md` and the relevant memory files (esp. `db-is-permanent-source`, `db-only-single-source`, `pending-approved-plans`) if this session changed a standing decision, finished pending work, or established a new constraint. These carry across sessions, so keep them accurate.
>
> **5. Guardrails to re-check (not docs, but verify they still hold):**
> - `tool/guard_db_only.py` still passes (no runtime JSON corpus reads crept in).
> - `ck.db` is still the single source of truth: no reintroduced courier files, no restored rebuild path, no new corpus API. `ck.db` stays committed via LFS, never re-gitignored.
>
> **Then do a staleness sweep** across all tracked `.md` + `setup.sh`: grep for anything
> claiming the server reads JSON at runtime, that the DB is rebuildable/gitignored, or
> that references a deleted courier file without a historical marker. Every such mention
> must be either (a) corrected in a living-reference doc, or (b) clearly flagged historical
> in a log/plan doc.
>
> **Finish:** show me the diff summary, confirm the guard is green and (if the server is
> up) `/health` is ok, then commit the doc changes with a clear message and push to `main`.

---

## Doc map (roles at a glance)

| Doc | Role | Update rule |
|---|---|---|
| `README.md` | Repo entry / setup / feature status | Edit in place |
| `ask-ck/CK-main/SERVER-README.md` | Deep technical reference | Edit in place (primary target) |
| `ask-ck/CK-main/CK_server/README.md` | Pointer stub | Rarely — only if pointers move |
| `ask-ck/CK-main/CK_server/static/js/README.md` | Front-end module conventions | Edit if JS structure changed |
| `ask-ck/objective-drafting/PROGRESS.md` | Current-status handoff log | Append dated entry |
| `SESSION_STATE.md` | Long-form session history | Append dated entry; never rewrite old |
| `ask-ck/ck-facelift/PLAN-*.md`, `pytest-create/PLAN-pytest-creator.md` | Design plans / trackers | Update status header; banner, don't rewrite |
| `MEMORY.md` + memory files | Cross-session persistent facts | Reconcile if a standing fact changed |

**Invariant to protect:** `ask-ck/var/ck.db` is the permanent single source of truth
(built once, shipped via Git LFS, no rebuild, no courier files, no corpus APIs). The
running server reads corpora only from it. Any doc implying otherwise is stale.

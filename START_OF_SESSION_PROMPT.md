# Start-of-Session Orientation Prompt (Ask-CK)

Paste this at the START of a session before doing any work on Ask-CK. It tells
Claude to read and understand the current state from the canonical docs first, so
work begins from reality — closing the loop with `END_OF_SESSION_PROMPT.md`, which
writes the same locations back at the end.

---

**Prompt to paste:**

> Before we do any work on Ask-CK, orient yourself by reading the current state — do
> NOT rely on memory or assumptions. Read these, then give me a short briefing and
> confirm the invariants hold.
>
> **1. Read the living reference docs (current system):**
> - `README.md` — repo entry, setup, feature-status table, data-layer overview.
> - `ask-ck/CK-main/SERVER-README.md` — deep technical reference (architecture, data layer, endpoints, admin panel, LLM config, workflow). Read this fully; it's the primary source.
> - `ask-ck/CK-main/CK_server/README.md` and `ask-ck/CK-main/CK_server/static/js/README.md` — pointer stub + front-end ES-module conventions.
> - `TESTBOX-ACCESS.md` — **read this before any work that touches lab hardware** (SSH to a testbox, driving a switch console, running a framework or legacy corpus script on a real DUT). It carries the non-obvious environment facts that cost real time to rediscover: the `SSH_AUTH_SOCK` gotcha, why the `.setup` console list cannot be trusted, and the fix set every legacy script needs against the current framework.
>
> **2. Read the current-status logs (most recent entries first):**
> - `ask-ck/objective-drafting/PROGRESS.md` — the handoff log: what shipped, what's pending, how to continue. The top (newest) entries are current truth.
> - `SESSION_STATE.md` — long-form history; skim the latest "Session Close / Handoff" entry at the end.
>
> **3. Read the plans relevant to what we're about to touch:**
> - `ask-ck/ck-facelift/PLAN-*.md` and `ask-ck/pytest-create/PLAN-pytest-creator.md` — check the **status header** of any plan tied to today's task (decisions already settled, phases done/remaining). Don't re-litigate settled decisions.
>
> **4. Load persistent memory:**
> - Review `MEMORY.md` and **the memory files it actually indexes** — read the index, don't assume a list. As at 2026-07-29 those are `pytest-creator-askck`, `testbox-console-access`, `setup-file-declares-topology` and `legacy-scripts-vs-framework`. These carry standing decisions and my working preferences across sessions.
> - Treat any memory name hardcoded in a prompt as a hint, not a guarantee: this step previously named four files (`db-is-permanent-source`, `db-only-single-source`, `pending-approved-plans`, `user-prefers-manual-ui-testing`) that no longer exist in the index. The DB-only invariant they carried is restated inline below, so nothing was lost — but verify before reporting a memory as missing.
>
> **5. Verify the live state (don't trust docs alone):**
> - `git status` + `git log --oneline -10` — is the tree clean? what landed recently?
> - `python3 tool/guard_db_only.py` — is the DB-only invariant still green?
> - If relevant to the task, start the server (`./run.sh --bg`) and check `/health`.
>
> **Then confirm these invariants still hold** (flag immediately if any is violated):
> - `ask-ck/var/ck.db` is the permanent single source of truth — shipped via Git LFS, NOT gitignored, NOT rebuildable. No courier/source JSON files, no corpus APIs, no re-fetch.
> - The running server reads corpora ONLY from `ck.db` (`db.py`); zero runtime JSON.
> - The LLM (org vLLM) is the one live external dependency and is core function, not an inter-dependency to remove. The embedding model is bundled + loads offline.
>
> **Finish orientation with a short briefing:** (a) where the project stands, (b) anything
> pending or uncommitted, (c) any invariant at risk, (d) your understanding of what we're
> about to work on. Then wait for me to direct the work. When we're done, we'll close the
> loop with `END_OF_SESSION_PROMPT.md`.

---

## Why this closes the loop

- **Start of session** (this file): READ the canonical locations → understand current state → confirm invariants → brief me.
- **End of session** (`END_OF_SESSION_PROMPT.md`): WRITE the same canonical locations back → sweep for staleness → commit + push.

Same doc map both directions, so the documentation is the single, trusted handoff
between sessions — never memory, never assumption.

## Doc map (read order)

| Order | Doc | Why read it |
|---|---|---|
| 1 | `README.md` | Fast orientation: what the project is, current feature status |
| 2 | `ask-ck/CK-main/SERVER-README.md` | Full technical picture (primary reference) |
| 2b | `TESTBOX-ACCESS.md` | **Only if the task touches hardware** — SSH/console/legacy-script mechanics that are expensive to rediscover |
| 3 | `ask-ck/objective-drafting/PROGRESS.md` | Newest handoff: what shipped / pending / next |
| 4 | `SESSION_STATE.md` (latest entry) | Recent session detail + any "superseded" notes |
| 5 | relevant `PLAN-*.md` status headers | Settled decisions + phase state for today's task |
| 6 | `MEMORY.md` + memory files | Standing decisions + working preferences |
| — | `git status/log`, `guard_db_only.py`, `/health` | Ground-truth the docs against the live repo |

**Invariant to protect:** `ask-ck/var/ck.db` is the permanent single source of truth
(built once, shipped via Git LFS, no rebuild, no courier files, no corpus APIs). The
running server reads corpora only from it. Flag anything that contradicts this.

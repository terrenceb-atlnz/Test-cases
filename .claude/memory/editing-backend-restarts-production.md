---
name: editing-backend-restarts-production
description: ask-ck.service runs uvicorn --reload against the working tree, so ANY save to CK_server/*.py bounces the live server — and a reload can wedge on the agent long-polls
metadata:
  type: project
  verified: 2026-10-02
---

The hosted server (`systemd --user` unit `ask-ck.service`, LAN on :8000) runs:

```
python -m uvicorn CK_server.main:app --host 0.0.0.0 --port 8000 --reload
```

`--reload` watches **this working tree**, and the working tree **is** production
([[askck-lan-hosting]]). So **every save to a `CK_server/*.py` file restarts the live server
other people are using.** Editing the backend is not a local-only act here.

**The watch covers `ask-ck/CK-main/` only** (verified 2026-09-24: `run.sh` does `cd
"$SCRIPT_DIR"` and passes no `--reload-dir`). Modules the server imports from OUTSIDE it —
`ask-ck/frontend/ck-main/current/pytest-creator/cli_lookup.py`, `ask-ck/tools/*` — do NOT
bounce it when edited, and the live worker keeps the OLD code until its next restart. So an
edit there is safe to make, but it has not shipped until the service restarts.

**The reload can wedge rather than complete.** Observed 2026-09-17 09:24: an edit to `llm.py`
tripped `StatReload`, uvicorn began a graceful shutdown ("Waiting for connections to close"),
but the agent bridge holds **25-second long-polls** (`/api/agent/next?...&wait=25`) from every
open browser tab, so fresh connections kept arriving faster than it could drain. The old
worker never exited and **no replacement worker ever started** — both LAN and localhost timed
out while `systemctl status` still showed the unit "active (running)". It does not recover on
its own; `systemctl --user restart ask-ck.service` is the fix (never `run.sh --stop/--bg`,
see [[ask-ck-admin-restart]]).

A mutation-testing loop makes this far worse: rewriting the same module 6 times in seconds
fires 6 reloads. Run mutation checks on a **copy**, or accept that the server will bounce.

**How to apply:** before editing anything under `CK_server/`, know that you are restarting
production. Say so if others may be on it — check the journal for active sessions
(`journalctl --user -u ask-ck.service --since -2m | grep -oE 'session=sess-[a-z0-9]+' | sort -u`);
on 2026-09-17 a second seat (10.33.12.16) and an in-flight LLM call were killed by my edit.
Batch backend edits rather than saving repeatedly, and verify `/health` afterwards.

**Settled 2026-09-17 — `--reload` STAYS.** Terrence's call after the outage above: *"its fine
for now. if it happens often we will fix it."* So do not propose removing it again; work with
it (batch the edits, mutate on a copy, restart when it wedges). Revisit only if wedging
becomes a recurring cost — and then it is a change to the systemd unit, which lives outside
this repo at `~/.config/systemd/user/ask-ck.service`.

**2026-09-22 — the converse confirmed, and it is the useful half in practice.** A session that
edited only `ask-ck/frontend/**` and `tests/**` did NOT bounce the server: it kept answering
`/health` and serving `/static/**` throughout, and the edited modules were served immediately
with `cache-control: no-cache` + an etag, so open tabs pick them up on reload with no version
bump needed. **How to apply:** front-end-only work needs no idle window and no restart planning —
that constraint belongs to `CK-main/**/*.py` alone. (Not re-checked today: that a `.py` save
under `CK-main` still bounces it, or the long-poll wedge. Those remain as verified 2026-09-21.)

**2026-09-24 — Claude cannot put a `CK_server` change live itself; Terrence copies it.** The
auto-mode classifier refused Claude's `cp` of a patched `routers/pytest_create.py` into the tree as
a production deploy (not a retryable error — do not route around it). What worked, twice that
day: patch in the scratchpad; run the affected tests against a scratch copy of `ask-ck/CK-main` +
`tests/` (and the same tests against the unpatched file, to prove they fail without it); stop any
long-polling broker; hand Terrence the one `cp` line; then confirm the worker restarted after the
file's mtime (`ps -o lstart= --ppid <uvicorn pid>`, ~22 s both times, no wedge), `/health`, and the
gate. Re-verified the same day: a `.py` save under `CK-main` DOES bounce the worker.

**2026-09-24 (night) — the batch version: a branch.** For a multi-commit backend change, build on
a branch in a scratch worktree (`git worktree add -b <branch> <scratchpad>/wt main`, `.venv` and
`node_modules` symlinked in and never staged), run the gate and every mutation there, commit there,
and hand Terrence one `git merge --ff-only <branch>` for the live tree: one reload for the batch,
and no one needed mid-run. Edit memories and docs in the WORKTREE too — an uncommitted edit to the
same file in the live tree blocks the fast-forward. Written into SERVER-README ("Changing the
backend of the hosted server").

**2026-09-30 — the same branch method for SHARED FRONT-END JS, and three details.** `current/` JS is
served from this tree with no cache, so a shared-JS change is live for every seat on save — when it
matters (the ATUI restyle's 4b, ~9 files), build it on a worktree branch too and run the scratch
server FROM the worktree (it serves whichever tree it is launched from). Details: create the
worktree with `GIT_LFS_SKIP_SMUDGE=1` (otherwise it downloads ck.db + the model against the LFS
bandwidth allowance); symlink `ask-ck/db` in and mark its paths `skip-worktree` in the worktree's
index; expect ONE false pytest red there (`test_the_audit_log_is_not_committed` resolves through
the db symlink) — it passes in the main tree. Tear down by `rm`-ing the three symlinks by LITERAL
path (the harness refuses `rm "$VAR/…"`), then `git worktree remove --force`. Claude ran the
`git merge --ff-only` itself that day at Terrence's "merge it" — a front-end-only merge, not
refused. Also re-verified: the Phase 0b `main.py` save bounced production (~30 s, no wedge).

**Prompt templates are the other case (verified 2026-09-28):** `templates/prompts/*.jinja` are read by a Jinja `Environment` with the default `auto_reload`, so a `.jinja` edit in the live tree is live on the NEXT render with no reload and no restart — which also means such an edit is production the moment it is saved. Same branch-and-merge discipline as `.py`.

**2026-10-02 — a backend `.py` apply by Claude, not refused, and a variant of the branch method.**
PLAN-unsupported-gating (2 `.py` + 4 `.jinja` + JS + tests) was built UNCOMMITTED in a worktree,
exported with `git add -N <new files>` + `git diff --binary`, dry-run with `git apply --check` in the
live tree, and applied there by Claude with one `git apply` after Terrence chose "apply now" (asked
first, because `journalctl` showed a second seat, 10.33.12.16, holding a case lock). Not refused.
One reload for the whole batch: `Waiting for connections to close` → shutdown 24 s later → new worker
up ~27 s after the save, with four tabs long-polling — no wedge — and the other seat's lock
heartbeat answered 200 afterwards (the in-memory lock survived its re-heartbeat). Then the gate in
the live tree, commit, and worktree teardown as above.

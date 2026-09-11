---
name: commit-and-push-on-session-end
description: "At the end of a session (the /wrap-ck skill) Claude COMMITS to main without asking and STOPS — it cannot `git push` from this seat (Terrence's company-set permissions deny it every time); Terrence pushes. Never chain, retry or work around a denied push. The name is historical: until 2026-09-10 this memory said push too."
metadata: 
  node_type: memory
  type: feedback
  verified: 2026-09-11
  originSessionId: fd3dcdc4-34c2-4084-99e5-a506a9647de6
  modified: 2026-09-11
---

**The contract (Terrence, 2026-09-11):** at the end-of-session doc-sync (`/wrap-ck`,
`.claude/skills/wrap-ck/SKILL.md` §7) Claude **commits** the session's changes to `main` —
explicit paths, clear message, the `Co-Authored-By:` line — and **stops at the commit.**
*"My company-based permissions do not allow you to push, so don't bother trying. Just commit,
and I will push."* Report the hashes and how far `main` is ahead of `origin/main`.

**Why:** the push denial is an organisational permission on the seat, not a per-prompt hiccup.
It was denied on 2026-09-10 and 2026-09-11 in this repo and three times the same day in
device-testing, including once right after Terrence had approved the step. A wrap that ends on a
push either stalls waiting for permission or misreports the branch as landed. `main` lagging
`origin/main` at session end is the normal state here, not an error. The sibling store's
`claude-cannot-push-terrence-pushes` (device-testing) records the same fact from that side.

**How to apply:**
- Commit at wrap without asking first — that authorisation (2026-07-22) stands. For mid-session
  commits, still confirm unless he says otherwise. Stage explicit paths; the tree is shared.
- Never `&& git push`, never retry a denied push, never propose `--force`, never touch the remote
  or credentials. `git fetch` / `pull --rebase --autostash` before committing on a remote that may
  have moved (Terrence also pushes from GitHub's UI) is fine.
- **Do NOT stage `ask-ck/db/ck.db` in a doc/code commit** — its working-tree modifications are
  runtime session-table writes, not part of the change. Leave it unstaged unless Terrence asks
  (`ck.db` is the permanent LFS source of truth — see [[db-is-permanent-source]]).

**Superseded history, kept so nobody re-derives it:** from 2026-07-22 to 2026-09-09 Claude did
push at wrap, and it worked from the Linux host (`1478952`, `a4435a8`) and from Mac-attached
Remote-SSH shells once `~/.bashrc` exported `SSH_AUTH_SOCK=$XDG_RUNTIME_DIR/keyring/ssh`. That
`SSH_AUTH_SOCK` fix is still what makes `ssh tbNNN` and Terrence's own pushes work
(`TESTBOX-ACCESS.md`); it is not a route around the permission denial.

---
name: commit-and-push-on-session-end
description: "During the end-of-session doc-sync (the /wrap skill), Claude SHOULD commit AND push to main — don't wait for Terrence"
metadata: 
  node_type: memory
  type: feedback
  verified: 2026-08-17
  originSessionId: fd3dcdc4-34c2-4084-99e5-a506a9647de6
  modified: 2026-07-28T20:28:39.197Z
---

When running the **end-of-session doc-sync flow** — now the **`/wrap` skill**
(`.claude/skills/wrap/SKILL.md`); the old `END_OF_SESSION_PROMPT.md` no longer exists —
Claude should **commit the changes and push to `main`** as the final step — do not stop at
"leaving the commit to you."

**Why:** Terrence explicitly removed the old standing preference on 2026-07-22b ("i DO want you to commit… and pushes"). The prior pattern — every handoff note reading "All uncommitted at session end — Terrence commits himself" — is **superseded**. Committing directly to `main` is the established workflow for this repo (all recent history is direct-to-main; no PR/branch dance).

**How to apply:**
- On the end-of-session doc-sync: `git add` the code+doc changes, commit with a clear message (end the body with the required `Co-Authored-By:` line), and `git push` to `main`. No need to ask first for this flow.
- **Scope:** this authorization is for the end-of-session flow. For mid-session commits, still confirm unless he says otherwise.
- **Push WORKS from the Linux host** (verified 2026-07-27 `1478952`, again 2026-07-29 `a4435a8`). Remote is SSH (`git@github.com:terrenceb-atlnz/Test-cases.git`). Do NOT assume "can't push."
- **Mac-attached VS Code Remote-SSH sessions CAN push too** — corrected 2026-07-29; the old "Mac seat lacks a key" story was incomplete. git runs on the LINUX host regardless of where the terminal is. The `Permission denied (publickey)` failure is because VS Code Remote-SSH forwards the Mac's ssh-agent, which is **empty**, and it *shadows* the authorized key held in the host's **gnome-keyring agent** (`$XDG_RUNTIME_DIR/keyring/ssh`, e.g. `/run/user/1971/keyring/ssh`); the on-disk `~/.ssh/id_rsa` is passphrase-encrypted so it's useless non-interactively. **Fix, made permanent 2026-07-29:** a guarded block in `~/.bashrc` exports `SSH_AUTH_SOCK=$XDG_RUNTIME_DIR/keyring/ssh` when that socket exists, so a fresh terminal pushes with no prefix. If a push in an ALREADY-OPEN shell still fails publickey, either `source ~/.bashrc` first or run `SSH_AUTH_SOCK=/run/user/$(id -u)/keyring/ssh git push origin main`. Verify the socket authenticates non-destructively with `ssh -T -o BatchMode=yes git@github.com` (expect `Hi terrenceb-atlnz!`) or `git push --dry-run`. The commit always lands locally regardless, so never invent credentials or switch the remote.
- **Do NOT stage `ask-ck/var/ck.db` in a doc/code commit** — its working-tree modifications are runtime session-table writes (transient state), not part of the change. Leave it unstaged unless Terrence asks. (`ck.db` is the permanent LFS source of truth — see [[db-is-permanent-source]].)

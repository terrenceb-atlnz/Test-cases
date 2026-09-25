---
verified: 2026-09-24
---
# PLAN — review and leftovers after executing the T33235 follow-ups (2026-09-24)

> ## Status (read first)
>
> **OPEN.** 2026-09-25 afternoon:
> - **C1 DONE.** Terrence merged the branch (`--ff-only`, after two rebases onto main); the gate is
>   green on the live tree. The scratch worktree is removed.
> - **C4 DONE.** `no duplex` is accepted, and both it and `duplex auto` remove the line.
> - **C5 attempted, not done.** The first runs showed the frame had to `init_all_devices()`, and
>   that the framework's default setup resets the whole bench. Runs now use
>   `--noupdate --nodefaultcfg` and go through device-testing's `bench-runner` agent; see PROGRESS
>   2026-09-25 afternoon. No TestCase has run yet.
> - In §B, the `genpop` agent is now named `test-composer`.
>
> Earlier on 2026-09-25: C6, C7, C8, C9 and C11 DONE on the same branch (commits `9dbe78a`
> `9efb2ad` `601f70a` `8246147` `6c0073c`, hashes before the rebase; C9 only as far as the last
> round's size — see it).
>
> Still open: §A (confirm), §B (D-C), C2, C3, C5 and C10 — each needs Terrence, the bench or a
> `ck.db` corpus edit. Written at the end of executing
> `archive/plans/PLAN-pt-drive-followups-2026-09-24.md` (every item of which landed on branch
> `pt-followups-2026-09-24`). §A are the decisions Claude took because they blocked work, for
> Terrence to confirm or reverse; §B is the one decision still open; §C is work still to do,
> smallest first. Nothing here blocks the branch from being merged.

## A. Decisions Claude took — confirm or reverse

- **X1 — how the branch reaches production.** Options: (a) edit the live tree directly (each
  `CK_server/*.py` save restarts the server others use; the auto-mode classifier refuses Claude's
  deploy); (b) patched files in the scratchpad plus one `cp` by Terrence per batch (what worked on
  2026-09-24 afternoon, but needs him mid-run); (c) a branch in a scratch worktree, gate and
  mutation checks there, and one `git merge --ff-only pt-followups-2026-09-24` by Terrence.
  **Chose (c).** The procedure is now in SERVER-README ("Changing the backend of the hosted
  server"). *To reverse:* say which of (a)/(b) and the README paragraph changes with it.
- **D-A — how many tool review rounds, and refuse or warn.** Options: (a) warn only; (b) hard
  refuse after N; (c) refuse after N unless the reviewer confirms (`extra_round`). **Chose (c),
  N = 2** — read from "we are already two-reviews past what i want" said at round 4. One constant,
  `_PT_REVIEW_ROUNDS_FREE`. *To change:* the number, or (a)/(b).
- **D-B — T33234's 8 UNSUPPORTED paths.** Options: (a) fix now by hand; (b) leave until it is next
  run; (c) regenerate those units. **Chose (a)** — plus the two real `show system pluggable`
  lookups in TC15/TC17 the new lint found. *Consequence:* only the FILE changed; T33234's `ck.db`
  session still holds the old code (C2).
- **R1 (from the first plan, still for review)** — on a copper SFP, the DUT's own accept/reject
  decides whether 10/100 is legal and that branch is verified; a fixed copper port must accept.

## B. Decision still open

- **D-C — is headless driving of `claude_agent` a supported use?** Options: (a) ship the
  scratchpad broker as `ask-ck/tools/pt_agent_broker.py` (polls `/api/agent/next` → local agent
  `/run` → `/api/agent/result`, with `X-CK-Session` / `X-CK-LLM`); (b) a server-side headless
  mode — against the "the browser brokers claude_agent" design; (c) a one-off. **Claude
  recommends (a):** the `genpop` agent's stated job is to generate scripts "by driving the PyTest
  Creator", which is exactly this path. Not built — a new tool is Terrence's call.

## C. Still to do

1. **Merge and verify the branch** (Terrence): `git merge --ff-only pt-followups-2026-09-24` in the
   live tree, then the worker restart time, `/health`, the gate. Then delete the scratch worktree
   (`git worktree remove`).
2. **Sync T33234's `ck.db` session with its file** (D-B) — open the case, Save the on-disk script
   through the UI (or `save_script` with the file's code). Until then that session's next lint
   carries 8 BLOCKING `unsupported:` errors and Review refuses.
3. **Other sessions may now lint BLOCKING** on the old UNSUPPORTED shape. Only two scripts are on
   disk and both are clean; a session holding an older generation needs Fix units (the error is
   per-unit, so Fix maps it) or a hand edit.
4. **Verify on tb470 whether AW+ accepts `no duplex`.** `cli_commands` documents only
   `duplex {auto|full|half}` (no `no` form), while `library_9001.configureDefaultPort` sends
   `no duplex` and tolerates a refusal. The fill rule §3e says "documented `no` form, else the
   default value"; whichever the device does decides whether T33234/T33235's teardowns satisfy
   `confCheck`.
5. **Run T33235 (and T33234) on tb470.** Both are preflight-RUNNABLE and lint-clean; neither has run.
6. **DONE 2026-09-25 (`6c0073c`)** — **A UI to add or edit a step's `publishes`.** Today only the extract writes it; the Sequence
   table shows it read-only. Needed before a reviewer can declare one the extract missed.
7. **DONE 2026-09-25 (`601f70a`, warning `published:`)** — **A lint that a consumer guards a published value against None** (G15's deterministic half).
   Prompt + review only today.
8. **DONE 2026-09-25 (`9efb2ad`)** — **A per-unit "Fix this unit" control** using the new `fix_units {"units": [...]}` filter (API
   only today).
9. **PARTLY DONE 2026-09-25 (`9dbe78a`: the button tooltip shows the LAST round's size; the first round's still needs the dry run — a render per page load is too heavy for gen_state)** — **A pre-send size for the FIRST review round.** The cap message shows the last round's size;
   the first round's is visible only through the provenance dry run.
10. **G9 for families without their own `checkLinkStatus`.** G7 covers 9001; marking the legacy
    fragment in the index would be a `ck.db` corpus edit, which this work did not make.
11. **DONE 2026-09-25 (`9dbe78a`, ⏳ grey dotted pill)** — **A distinct pill state for `limit: true`** (P3). The text says "seat limit"; the colour is the
    ordinary error red.

## Behaviour changes to know about

- Generation now reads `generated/<family folder>/library_<family>.py` at build time (G7), so two
  sessions of one group generated at different moments can see different family files. The save's
  tag-keyed merge reconciles them and the G3 clash guard is the backstop.
- A family with a library file now always gets `from library_<family> import *` in its frame, even
  when the script adds no helper (it ships the family file).

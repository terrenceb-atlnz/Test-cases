---
name: no-stray-scripts
description: "Throwaway scripts go in the SESSION SCRATCHPAD, never in Terrence's lab tree. A script is either worth keeping (-> the repo, as a flag on an existing tool) or it is not (-> scratchpad). There is no third category. Enforced by the no-stray-py PreToolUse hook, because the instruction alone failed 7 times in one session."
metadata:
  node_type: memory
  type: feedback
  modified: 2026-09-02T23:59:00.000Z
---

**Terrence, 2026-09-02:** *"You're polluting every directory i have, repeatedly,
every session."*

In one session I left **seven** one-off scripts in his run directories —
`probe.py`, `read_swib.py`, `hist.py`, `ports.py`, `poll.py`, `recheck.py`,
`check.py` — while `claude/Test-cases/CLAUDE.md` §3 already said *"I definitely
would prefer you to ask me about extra checks, metrics, file writes, etc."*

**Why:** the rule existed and instruction-following is what failed, so another
instruction cannot fix it. Two specific causes:

1. **A throwaway script does not feel like a file write.** Asked to check the
   stack, writing `check.py` feels like *how you check a stack*, not like
   creating an artifact — so the ask-first rule never fires. This is a category
   error I make reliably, which is why it needs a mechanism.
2. **A technical misconception did most of the damage.** The framework writes
   its logs into CWD, so a run needs a dated CWD — but the **script does not
   have to live there**. Script location and CWD are independent; invoke the
   canonical tool by absolute path with `cd` set to the run dir. Five of the
   seven existed only because of that confusion.

A third contributor: the canonical tool was genuinely insufficient (it could
not read a stack member that had fallen out of its stack). **Fix the tool; do
not write beside it.** That became `bench_probe.py --device/--cmd`.

**How to apply:**

- **Worth running twice → the repo**, `claude/Test-cases/ask-ck/test-composer/`,
  usually as a new **flag on an existing tool** rather than a new file.
- **Worth running once → the session scratchpad** (`/tmp/claude-*/…/scratchpad`),
  outside his tree and auto-cleaned. Invoke it by absolute path with cwd set to
  the run dir.
- **Neither → ask first**, and say why the two options above do not work.
- Never `cp` a scratchpad script into the lab tree "so it is next to the logs".
  That is the same pollution with an extra step.
- A dated run directory is discipline for **logs**, not a licence to put code
  there. The only code that belongs in an archived run dir is the driver a past
  campaign actually ran against, kept for reproducibility.

Enforced by `~/.claude/hooks/no-stray-py.py` (PreToolUse on `Bash|Write`). It
covers **Bash**, not just `Write`, because in auto mode files are created with
`cat > f <<'EOF'` — a Write-only hook would have caught **zero** of the seven.
If it blocks you, it is right: pick one of the two homes above. Do not route
around it by renaming the file or assembling the path from variables.

See [[tb470-topology-and-setup]] for the documentation twin of this rule —
one fact, one home; everywhere else links.

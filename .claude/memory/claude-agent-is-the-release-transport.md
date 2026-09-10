---
name: claude-agent-is-the-release-transport
description: "`claude_agent` (browser broker -> ck-agent on the user's seat) is the ONLY Claude transport as of 2026-09-10; seats install the agent from the Ask CK home page one-liner; the LLM choice is per seat (X-CK-LLM)"
metadata:
  type: project
  verified: 2026-09-10
---

**The Claude path is the per-user agent, and nothing else.** A browser tab brokers each call
to `ck-agent` on the user's own machine (`ask-ck/agent/ck_agent.py` on Ubuntu,
`ck-agent.ps1` on Windows — same contract, same captures in the gate), which runs `claude -p`
against that user's own seat. Terrence, 2026-09-10: *"Claude Code CLI (my local machine) —
this button will stay, usable by everyone, including myself, the same way I do today."*

**Why:** a Claude subscription seat is per person; a shared server must never pool users
through one login. Every design choice since (seat setup served from the splash page, the
Windows agent, `/health` reporting login + versions, per-seat LLM mode) exists to make that
the easy path rather than the RDP-to-localhost workaround of the two demo days.

**How to apply:**
- A seat needs only the Ask CK URL: the home page's one-liner (`/setup/setup.ps1` or
  `/setup/setup.sh`) installs Claude Code, fixes PATH, logs in, installs and starts the
  agent, and hands the final check to the page (`?seat-check=1`). Re-running it is the
  update/repair ritual. Plan: `ask-ck/ck-facelift/PLAN-seat-setup-and-per-seat-llm.md`.
- The LLM choice is **per seat**: the browser sends `X-CK-LLM` on every `/api` call;
  `llm_config.effective_llm_config` resolves seat → site default → session copy. Plain Apply
  writes nothing server-side; only **Set as site default** writes the `_workspace_llm` row.
  See [[workspace-llm-default-gotcha]] for what that means for headless curl.
- Headless tooling on the server host has the org vLLM only; there is no server-side Claude
  transport to reach for. The CLI contract the agents implement is in
  [[claude-code-cli-transport-contract]].

---
name: claude-agent-is-the-release-transport
description: "`claude_agent` (browser broker -> ck-agent on the user's seat) is the ONLY Claude transport as of 2026-09-10, and since 2026-09-11 Ask-CK has exactly TWO backends (org vLLM, claude_agent) — Grok is gone; seats install the agent from the home page one-liner; the LLM choice is per seat (X-CK-LLM)"
metadata:
  type: project
  verified: 2026-09-11
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
  update/repair ritual. Plan: `ask-ck/plans/PLAN-seat-setup-and-per-seat-llm.md`.
- The LLM choice is **per seat**: the browser sends `X-CK-LLM` on every `/api` call;
  `llm_config.effective_llm_config` resolves seat → site default → session copy. Apply
  stores the seat's choice in the browser AND writes the `_workspace_llm` site-default row
  (D17, 2026-09-11 — one button; the separate control is gone). A seat's own header always
  outranks the row, so an Apply elsewhere never changes a seat that has chosen.
  See [[workspace-llm-default-gotcha]] for what that means for headless curl.
- **Two backends, and only two (2026-09-11).** `models.SUPPORTED_AUTH_METHODS` is exactly
  `("local_llm", "claude_agent")`; `api_key`, `account`, `claude_code` and `grok_cli` are
  refused by name. Terrence: *"Every LLM call on Ask-CK should be runnable by both the vLLM
  and the Claude (your seat) options."* Every LLM call starts in a browser — the headless
  creation-time tools (enrich, model matrix, judges, autopilot) were retired the same day, so
  there is no server-side LLM CLI or subprocess runner to reach for. The CLI contract the
  agents implement is in [[claude-code-cli-transport-contract]]. Adding a backend is a
  governance decision: update the wiki, `SUPPORTED_AUTH_METHODS` and
  `tests/test_llm_backend_allowlist.py` together.

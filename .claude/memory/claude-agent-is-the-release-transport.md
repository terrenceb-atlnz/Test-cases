---
name: claude-agent-is-the-release-transport
description: "`claude_agent` (browser broker -> ck-agent on the user's seat) and the server-side CLI option are the SAME endpoint on Terrence's seat; the server-side option is DEMO-ONLY and will not ship — never ask whether a switch to claude_agent was deliberate"
metadata:
  type: project
  verified: 2026-09-07
---

Terrence, 2026-09-07: *"claude_agent/claude_server: They're the same endpoint, this seat. The
server option is for demo purposes only, and will not be a feature included when this is
released."*

**Why:** on 2026-09-07 the workspace `auth_method` read `claude_agent` for the 13:12
38-unit run and I asked whether the switch from the server-side CLI transport was deliberate.
It was not a switch worth asking about: both routes end at the same Claude Code seat, so
model, cost and cache behaviour are identical for Terrence's runs.

**How to apply:**
- Do not treat `claude_agent` vs the server-side CLI (`claude_code`) as a decision to
  confirm; report which one a run used only when it explains a difference.
- The server-side CLI option exists for DEMOS and is not part of the release. Do not build
  release features that depend on it, and do not document it as the primary path. The
  release transport is the browser-brokered agent on the user's own seat.
- The mechanics of the headless CLI call itself (flags, system-prompt split, streaming) still
  matter for both routes — see [[claude-code-cli-transport-contract]]; the per-task model
  routing applies to both — see [[workspace-llm-default-gotcha]].

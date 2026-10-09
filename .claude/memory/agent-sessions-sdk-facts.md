---
name: agent-sessions-sdk-facts
description: Measured 2026-10-09 (P0 + E2E) — how Ask-CK drives a full-tools Claude session from a page — stream-json control protocol (= what the VS Code extension uses), the classifier never reads tool results so a hand-off FILE authorizes nothing, Claude writing authorization in the user's name is blocked ("Auto-Mode Bypass"), `--bg` sessions are not drivable, a TRIAGE costs ~$2–4 list
metadata:
  type: project
  verified: 2026-10-09
---

**The wire.**
- **Launch:** `claude -p --input-format stream-json --output-format stream-json --verbose
  --permission-prompt-tool stdio` (the Agent SDK launches exactly this, and so does the VS Code
  extension).
- **Messages:**
  - an `initialize` control_request first;
  - user turns as `{"type":"user","message":{…}}` lines;
  - the CLI asks `{"type":"control_request","request":{"subtype":"can_use_tool",…}}`;
  - the host replies `control_response` with `behavior: allow|deny`.
- **AskUserQuestion:** answered by ALLOWING it with `updatedInput.answers = {question: label}`.
- **Results:** each `result` line has cumulative `modelUsage` (subagents included); each
  `task_notification` carries per-subagent usage. Code: `ask-ck/agent/ck_agent.py` (sessions,
  D7 = the SDK).

**Permissions in auto mode** (docs, code.claude.com/docs/en/permission-modes, read 2026-10-09):
- The classifier reads user messages, tool calls and CLAUDE.md, NEVER tool results. So a
  hand-off file read by a tool authorizes nothing, while the same work typed by Terrence in VS
  Code passed (14 console calls, 0 denials).
- Claude writing an authorization paragraph "in the user's name" for another session is itself
  denied ("Auto-Mode Bypass"). Don't try it.
- The fix (D6) is a launcher-passed `--settings` profile: narrow `Bash(tools/tb <action> *)`
  allow rules resolve BEFORE the classifier.
  - Project `.claude/settings.json` allow rules are ignored by `-p` unless the folder is trusted.
  - `autoMode` is never read from project settings.
  - Allow rules don't match past `VAR=` prefixes.
  - Consequence: hard_deny prose doesn't guard commands run through an allowed wrapper.

**Dead ends:** `claude --bg` sessions survive, but `claude logs` is raw terminal screen output,
there is no programmatic input, and they need interactive workspace trust. Remote Control is
denied by company policy (D2).

**Costs measured:** P0 TRIAGE $3.97 list (9 min); E2E Validation TRIAGE $2.07, 2.85M tokens
(5m50s); composer-validate with an empty template 48 s.

Plans: [[tb470-runs-go-through-test-mode]], `ask-ck/plans/PLAN-agent-sessions.md` §9a/§10.

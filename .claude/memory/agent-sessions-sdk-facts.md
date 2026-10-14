---
name: agent-sessions-sdk-facts
description: Measured 2026-10-09 (P0 + E2E), extended 2026-10-14 (mid-turn messages, reasoning text, empty system prompt) — how Ask-CK drives a full-tools Claude session from a page — stream-json control protocol (= what the VS Code extension uses), the classifier never reads tool results so a hand-off FILE authorizes nothing, Claude writing authorization in the user's name is blocked ("Auto-Mode Bypass"), `--bg` sessions are not drivable, a TRIAGE costs ~$2–4 list
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
  - A project's own settings-file allow rules (the generic Claude Code mechanism, not a file in
    this repo) are ignored by `-p` unless the folder is trusted.
  - `autoMode` is never read from project settings.
  - Allow rules don't match past `VAR=` prefixes.
  - Consequence: hard_deny prose doesn't guard commands run through an allowed wrapper.

**Dead ends:** `claude --bg` sessions survive, but `claude logs` is raw terminal screen output,
there is no programmatic input, and they need interactive workspace trust. Remote Control is
denied by company policy (D2).

**Costs measured:** P0 TRIAGE $3.97 list (9 min); E2E Validation TRIAGE $2.07, 2.85M tokens
(5m50s); composer-validate with an empty template 48 s.

**Talking to a running session (measured 2026-10-14, SDK 0.2.165, Claude Code 2.1.296).**
- **A message sent mid-turn is delivered:** the transcript logs `queue-operation … absorbed_mid_turn`,
  and the model sees it as a system-reminder telling it to address the message. It may still answer
  only in its reasoning (2 of 10 scratch sessions, and run 2026-10-13T1454-val-43dd).
- **Reasoning text is mostly absent:** most `ThinkingBlock`s arrive with `thinking == ""` and only a
  signature (20 of 23 in that run). The few with text are short lines addressed to the user. Agent
  1.3.5 passes them to the window; 1.3.4 dropped them.
- **No `system_prompt` means none at all:** the SDK then launches with `--system-prompt ""`
  (423 characters), not Claude Code's prompt. The preset (`{"type": "preset", "preset":
  "claude_code"}`) made no difference to replying (3 vs 3 sessions), so it was left unset.
- **A session started from a scratch cwd** leaves a `~/.claude/projects/<slug>/` directory, often with
  an empty `memory/` that `check_memory_links` reports as EMPTY_DIR.

Plans: [[tb470-runs-go-through-test-mode]], `ask-ck/plans/PLAN-agent-sessions.md` §9a/§10.

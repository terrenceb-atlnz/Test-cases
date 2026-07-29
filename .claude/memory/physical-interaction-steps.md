---
name: physical-interaction-steps
description: "Physical steps (plug/unplug, cable in/out) are IN scope — generate a wait-for-state-change pattern, do NOT skip them"
metadata: 
  node_type: memory
  type: project
  originSessionId: 05c21640-4b4b-4ca4-a470-32f6bfa5c600
  modified: 2026-07-23T01:56:58.537Z
---

Physical-interaction test steps (hot-remove/insert a pluggable, unplug/replug a cable, LED checks) are **in scope** for the PyTest Creator, NOT un-automatable. Terrence corrected this 2026-07-23: a physical action is done by an operator, and the script prompts + waits for the resulting port state change, then continues.

**Why:** the adversarial review flagged T33233 steps 3/4 (hot-remove/insert pluggable) as "un-automatable, should be skipped." Wrong — the SVT **3009 Pluggable Qualifications** suite is the canonical precedent for handling exactly this.

**How to apply — three real patterns from `svt/3009_pluggable_qualifications/libPluggableAutomate.py` (all reusable via ck.db `get_script_source`):**
1. **Event-driven (best):** `waitForHotswapEvent()` / `waitForBulkHotswapEvent()` — enable terminal monitoring, poll the console buffer for the device's own `"removed"`/`"inserted"` hotswap log messages, count removal+insertion events. The device tells the script when state changed; operator just does the physical act.
2. **Prompt-and-poll-status:** `waitForReplugEvent()` (lines ~1009-1067) — banner-print `"Waiting for removal of cable in pluggable in <port>"`, then poll `self.dut.cmd('sho int <port> status | grep -c connected')` for the link down→up (or up→down) transition, continue automatically on change. Self-contained, cleanest to model on.
3. **Explicit Y/N confirm** (for LED/visual checks the device can't report): module-level `yesNo(question)` — `sys.stdout.write('%s [y/n]\n')` + `strtobool(input())`; used as `yesNo("Press Y when leds have turned on")`.

So the fix for the generator is NOT to drop physical steps but to make the **Sequence extractor classify them as `physical`/`interactive`** and have **Generate emit the wait-for-state-change pattern** (prompt operator → poll for port state change → continue), preferably modeled on `waitForReplugEvent`. Do NOT tell the LLM to drive the removal via `.cmd()` (that's the current bug — fabricates a false CLI action).

Relates to the PyTest Creator artefact-review worklist ([[pending-approved-plans]] area). Ties to LOGGING-CONTRACT's UNSUPPORTED result only when the platform genuinely lacks the feature, NOT for physical steps.

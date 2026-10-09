---
name: tb470-runs-go-through-test-mode
description: "Since 2026-09-28 evening a tb470 test run is dispatched through device-testing's /test-mode (ONE session = sentinel + bench-runner subagents, TRIAGE then RUN, --resume). bench-runner gate 8 refuses a dispatch without `sentinel: parent` or a live peer sentinel — an Ask-CK session cannot just spawn bench-runner and go. STANDING-ORDERS.md holds Terrence's standing answers (log NAME = verdict)."
metadata:
  type: project
  verified: 2026-10-09
---

**What:** Terrence rejected the two-terminal sentinel design (*"coalesced into one
device-testing agent that does both parts equally"*). `/test-mode` (device-testing
`.claude/skills/test-mode/SKILL.md`, commit `33fcb18`) is that bundle: the invoking session is the
sentinel (Terrence's channel + rescuer), `bench-runner` subagents are the tester, one per queue
group; triage first (N runnable / M blocked by topology with the EXACT unblock / K other), then
the one gate question, then the runs. Standing answers a run must not re-ask are in
`../device-testing/STANDING-ORDERS.md` (`9ff73e1`): every unit in play incl. 4050 + x230, full
authority within a test, tidy configs between unrelated cases, **one log per case whose NAME is
the verdict** (`<id>.log` = PASS only; `-fail`/`-partial`/`-skip`).

**Why it matters here:** this repo's `test-composer` agent hands runs to `bench-runner`, and
`bench-runner` gate 8 (sentinel mandatory, Terrence 2026-09-28) refuses a dispatch that neither
says `sentinel: parent` nor names a live peer sentinel. **Open point (g) was answered on
2026-10-09:** Ask-CK launches `/test-mode` itself, with `--from-ask-ck <handoff>` (device-testing
`83c0880`). That writes `Driver: ask-ck` into the queue, allows `/create-logs --auto` for manual
cases, and (`52cc64e`, D5) never blocks on a question: it emits a `NOTIFY …` line, works past the
problem, or BLOCKs the case and moves on. How the session is started and watched is
`ask-ck/plans/PLAN-agent-sessions.md`; its users are `PLAN-test-validation.md` and
`PLAN-test-composer.md`.

**Built 2026-10-09 (branch `tc-build`, applied by Terrence):**
- **The launch:** the Validation and Test Composer pages launch `/test-mode --from-ask-ck`
  through the seat agent's SDK session (agent 1.3.0, D7), with device-testing's
  `.claude/ask-ck-campaign.settings.json` profile (D6) and the `tools/tb` wrapper.
- **Markers the pages read:** RESULT / NOTIFY / PROBE / REPAIRED / REVIEWED / ASKCK-DONE
  (test-mode §1, §8, §10, §11).
- **E2E:** passed on tb470 13:49 and 13:56 (TRIAGE only).

See [[agent-sessions-sdk-facts]].

**How to apply:** to run anything on tb470, start a session in `../device-testing` and use
`/test-mode <cases>` (or `--resume`); do not spawn `bench-runner` from here without the sentinel
wording, and do not rebuild the sentinel — the kit is in orient-dt §10 there
([[sentinel-kit-in-orient-dt]], a device-testing memory). Related: [[pytest-creator-askck]],
[[framework-run-always-noupdate]].

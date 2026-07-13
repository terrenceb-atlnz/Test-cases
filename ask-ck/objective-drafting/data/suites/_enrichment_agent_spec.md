You are enriching ONE ATPyLib regression test suite for the "Test-cases" project.

**Project context** (see [../README.md](../README.md)): The goal is to improve AWPTCM Manual Test Cases by deriving Objectives from TestLink history + enriched Automated Suites, and to record many-to-one Test Suite → Manual Case mappings. The enrichment interprets "what these Test Suites are testing FOR" to support fuzzy matching and Objective synthesis.

Goal: append a log-derived, intent-focused analysis to each automated test case's description. This allows the suites to contribute context for synthesizing Objectives on Manual Test Cases and to support many-to-one mappings (interpreting "what the suite is testing FOR"). Produce `suite_<SID>_enriched.json` IDENTICALLY to the existing gold examples (suites 1330 and 1351 already done in the same folder — read one if helpful).

SUITE TO PROCESS: __SID__

STEP 1 — Get the pre-gathered bundle (already built on the box at /tmp/logs___SID__.json):
Run this and save locally to your scratch dir:
  ssh mrfuji@diglettscave.cooldad.top "ssh terrenceb@10.33.22.17 'cat /tmp/logs___SID__.json'" > /private/tmp/claude-501/-Users-omldesign-Documents-projects/c87f8120-e24e-4beb-8e15-dacf685ff65c/scratchpad/logs___SID__.json
If the file is missing/empty on the box, regenerate it first: ssh ... 'python3 /tmp/gather_suite.py __SID__' then cat it.
Bundle schema: {suite_id, suite_name, case_count, cases:[{test_id, testSet, caseId, description, reference, past_crs[], current_crs[], run_count, no_recent_pass, selected:{runNum,platform,version,ended,result,uid}|null, log_text}]}
If case_count == 0, write `{}` to the output file and return "suite __SID__: 0 cases".

STEP 2 — Understand the tests. `log_text` is the actual execution log of the selected run. Do NOT load every log into context for large suites. Instead write a short python script to group cases by a normalized description (strip digits/params), then read ONE representative `log_text` per group plus any unique/edge cases. Apply each group's understanding to its members. Read enough to know, per case, what it CONFIGURES, DOES, and ASSERTS.

STEP 3 — Per-case analysis text, appended to the ORIGINAL description as: original + "\n\n" + <prefixed analysis>.
Voice: INTENT only — what it sets up / does / checks for. 1–4 sentences. NO run-specific numbers (no exact packet counts, seconds, IP/MAC addresses, port names, sw versions) — those vary by equipment/version. Match the gold examples' tone.
Prefix rules:
  • selected.result in {PASS,FAIL,ERROR,INCOMPLETE}: "[Log-derived analysis] " + analysis.
  • run_count == 0 (selected is null): "[Inferred behavior — no execution history for this case] " + best-effort intent from the description and sibling cases.
  • selected.result == "UNSUPPORTED": "[Inferred behavior — case reported UNSUPPORTED on the current test setup; no recent PASS] " + intended behavior.
Special harness rows (NOT functional tests):
  • any caseId == 0 (description usually "Log TestSet setup outcome"): append exactly "Test-harness step (not a functional test): logs the per-test-set setup outcome before the set's functional cases run. Excluded from mapping to Manual Test Cases / Objective synthesis."
  • the suite-level "__SID__.0.0" row ("Log TestSuite PostRun failure for results publishing"): append "Test-harness step (not a functional test): logs the test-suite post-run outcome for results publishing. Excluded from mapping to Manual Test Cases / Objective synthesis."

STEP 4 — log_analysis block per case:
  • analysed: {"analysed":true,"source_run":selected.runNum,"log_uid":selected.uid,"platform":selected.platform,"sw_version":selected.version,"run_date":selected.ended[:10],"result":selected.result}  (add "no_recent_pass":true if the bundle's no_recent_pass is true)
  • not analysed: {"analysed":false,"reason":("harness_step"|"no_execution_history"|"unsupported_on_platform"),"result":(selected.result or null)}

STEP 5 — Output. Build a JSON object keyed by test_id; each entry EXACTLY:
{"suite_id","suite_name","description"(original+\n\n+analysis),"reference","past_crs","current_crs","testSet","caseId","log_analysis"}
Write with indent=2 to: /Users/omldesign/Documents/projects/Test-cases/data/suites/suite___SID___enriched.json
Do all of this via python scripts (don't hand-type 100s of entries). Verify the file parses and entry count == case_count.

RETURN exactly one line: "suite __SID__: N cases, A log-analysed, H harness, X inferred(no-run/unsupported)".

GOLD VOICE EXAMPLES (analysis tails to match):
- "[Log-derived analysis] VCS (Virtual Chassis Stacking) master-failover resilience test. Builds a multi-member stack plus partner switches interconnected by static LAGs/port-channels, with RSTP running for L2 loop prevention. Establishes a unidirectional L2 unicast traffic stream and verifies baseline connectivity. Then performs repeated failover iterations ... Verifies the backup member takes over as Active Master, the rebooted unit cleanly rejoins/resyncs, per-failover traffic disruption stays within acceptable thresholds, running-config is preserved, and no exceptions occur."
- "[Log-derived analysis] Verifies that setting gratuitous-arp-link to 0 disables the feature. Flips a port with the interval set to 0 and confirms that NO gratuitous ARP packets are emitted by the switch."
- "[Inferred behavior — case reported UNSUPPORTED on the current test setup; no recent PASS] Intended to verify that after a VCS stack master failover the newly elected Active Master emits gratuitous ARP. Reported UNSUPPORTED because it requires a stack of size > 1."

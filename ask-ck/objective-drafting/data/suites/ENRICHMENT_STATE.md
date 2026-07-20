# ATPyLib log-enrichment — resume state (paused 2026-06-22)

> **⚠ Historical / superseded (2026-07-20).** This documents how the ATP suites were enriched.
> The outputs it describes (`suite_*_enriched.json`, `all_test_suites.json`,
> `test_id_description.json`/`.csv`) have been **retired and deleted** — the enriched ATP data now
> lives in **`ask-ck/var/ck.db`** (`atp_tests`), the permanent single source of truth. Kept as a
> record of the enrichment process only.

## Project Framing
**See [../../README.md](../../README.md) for the authoritative framing.**

The primary goal is to improve the Manual Test Cases (`AWPTCM-Txxxx`) by synthesizing proper **Objectives** (drawn from two sources):
- Historical TestLink test cases.
- Enriched Automated Test Suites (ATPyLib).

Additional goal: Explicitly map related Test Suites to Manual Test Cases (frequently **many-to-one**). Because Test Suites are more detailed, relationships are fuzzy; the enrichment's log-derived analysis in the Description helps interpret *"what these Test Suites are testing FOR"*.

## Goal (Enrichment Phase)
Enrich every ATPyLib automated test case's `description` with a log-derived, intent-focused
analysis (one `suite_<SID>_enriched.json` per suite) so the suites can be used to define Objectives for the Manual cases and support many-to-one mappings.
Scope: **all 120 suites EXCEPT 6003** (6003_AMF_Release_Interop, 78,579 auto-gen interop cases — dropped, not related).

## Access (all `.lc` hosts via terrenceb-dl over ATL-NZ VPN)
`ssh mrfuji@diglettscave.cooldad.top "ssh terrenceb@10.33.22.17 '<cmd>'"`
Intranet base: `https://intranet.atlnz.lc/systest/ATPyLib/regression`

## Assets (durable, in this folder)
- `_enrichment_agent_spec.md` — the subagent prompt spec (replace `__SID__`). Defines voice (intent only, NO run-specific numbers), prefixes, harness/no-run/UNSUPPORTED handling, output schema, provenance `log_analysis` block.
- Bundles pre-gathered for ALL 117 suites on box `/tmp/logs_<SID>.json` (present as of pause; regenerate with gather_suite.py if cleared).

> **Removed 2026-07-16 (repo scrub):** the enrichment working-scratch files `_gather_suite.py`
> (also on box at `/tmp/gather_suite.py`; selection rule: topmost run if PASS, else most-recent
> PASS within 12mo / CUTOFF 2025-06-22, else topmost flagged `no_recent_pass`), `_remaining_suites.txt`
> (105 remaining IDs), and `_todo_suites.json` (full 117 todo list) were deleted as vestigial —
> Phase 2 enrichment is complete (below). Recover from git history if a re-run is ever needed.

## ✅ Phase 2 COMPLETE: All 119 suites enriched & merged (2026-06-23 13:53 UTC)

**Enrichment**: 119 suites processed
- 116 non-empty suites: 1331–1372, 1399, 1501–1502, 2000–2036, 5009, 5049, 5500, 5700–5701, 5704–5708, 5710–5711, 5714, 6000–6012, 6100–6102, 6201, 6400, 6901, 6911–6914, 7000–7001, 8002–8003 + originals 1330, 1351, etc.
- 3 empty suites (0 cases): 1503, 6102, 6914
- **Total enriched files**: 119 × `suite_*_enriched.json`

**Final Merge** (fixed):
- **10,157 test cases** across 116 suites
- Master dicts: `all_test_suites.json` (nested), `test_id_description.json` (flat), `test_id_description.csv`
- All entries have complete metadata (`suite_id`, `suite_name`, `log_analysis`)
- Bug fixed: Schema variance handled; originally 12 suites were lost, now recovered

## How to resume (Phase 3: Mapping & Objective Synthesis)
Phase 2 (enrichment) is **COMPLETE**. Master dicts ready: `all_test_suites.json`, `test_id_description.json`, `test_id_description.csv`.

**Phase 3 focus** (per [../../README.md](../../README.md)): Use the enriched data (plus TestLink history) to:
- Synthesize Objectives for the 410 AWPTCM Manual Test Cases.
- Record explicit many-to-one mappings from Test Suites to Manual Cases.

Current workflow (data transformation & accuracy focus; Zephyr writes are final step):
1. Review pre-ranked candidates and decisions (in `data/review/batch_*.md` and `data/decisions/dec_*.json`).
2. Synthesize/define Objectives and capture many-to-one relationships.
3. Validate data accuracy (see VALIDATION_RESULTS.md and ENRICHMENT_QUALITY_ANALYSIS.md).
4. Later: Use outputs for Zephyr updates and final coverage reporting.

## Enriched entry schema (per test_id)
{suite_id, suite_name, description(original+"\n\n"+analysis), reference, past_crs[], current_crs[], testSet, caseId, log_analysis{analysed, source_run?, log_uid?, platform?, sw_version?, run_date?, result, no_recent_pass?, reason?}}

## Quality bar (verified on 1330/1351/wave1)
Intent voice, no run-specific numbers; prefixes `[Log-derived analysis]` / `[Inferred behavior — no execution history…]` / `[Inferred behavior — …UNSUPPORTED…]`; harness rows (caseId 0 and <sid>.0.0) marked not-a-functional-test, analysed:false.

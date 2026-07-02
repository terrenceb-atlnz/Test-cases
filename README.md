# Test-cases

This directory contains the data, tools, and analysis for a project to improve and contextualize manual test cases using historical and automated sources.

## Project Framing

The primary target is the **Manual Test Cases** (`AWPTCM-Txxxx`) in Zephyr (under the "New Platform Test (MASTER)" area in the AWPTCM project). These cases currently lack well-defined **Objectives** (and often preconditions), making it unclear what they are intended to verify.

To address this, two other silos of information are being analyzed:

- **Historical Test Cases** from TestLink (older, more detailed human-authored tests).
- **Automated Test Suites** from ATPyLib (current regression automation suites).

These sources serve two main purposes:

1. **Identify overlap** between the manual tests and the other sources.
2. **Provide context** for what the manual test cases *should be testing for*.

Because the Manual Test Cases lack Objectives, the work involves examining what the TestLink historical cases and the Automated Test Suites are actually testing, then re-defining and synthesizing that information as proper **Objectives** to attach to the relevant Manual Test Cases.

### Additional Goal: Mapping Test Suites to Manual Test Cases

In addition to defining Objectives, the project aims to **explicitly identify and record mappings** from related Test Suites to Manual Test Cases. This is often a **many-to-one relationship** (multiple detailed Test Suites can map to a single higher-level Manual Test Case).

Test Suites are frequently more granular and detailed in their testing than the Manual Test Cases. This leads to a **fuzzy logic relationship**. 

The objective of the `.json` enrichment process (specifically the log-derived, intent-focused analysis appended to the `description` field in the enriched suite data) is to **interpret what these Test Suites are testing FOR**. This enriched intent helps resolve the fuzziness and enables accurate mapping and context extraction.

## Data Sources

Note: Data is organized across `data/` and `data/suites/`.

- **Manual Test Cases** (`data/zephyr_master.json` for raw, `data/candidates.json` for pre-ranked): The ~410 AWPTCM-Txxxx cases (target) that need Objectives and mapping. See `data/suites/zephyr_master.json` copy if present.
- **Historical TestLink Cases** (`data/suites/testlink_awp.json` and related extraction tools in `tool/`): Older test definitions (AWP ids) used for overlap detection and context. The review/decisions pipeline (batches, decisions) currently operates primarily on this source.
- **Automated Test Suites** (`data/suites/`): ATPyLib suites (numeric suite ids like 1330+) that have been enriched with log analysis for intent interpretation (`suite_*_enriched.json`, `all_test_suites.json`, `test_id_description.*`, `suite_index.md`). These provide detailed "what is being tested FOR" via the enrichment process. Complementary to TestLink source for Objectives and mappings.

The two sources (TestLink historical + ATPyLib automated) are used together for the project goals.

## Key Artifacts

- `data/suites/` — Enriched automated suites (one JSON per suite), master files, state, and index.
- `data/decisions/` — Human decisions on matches (many-to-one capable).
- `data/review/` — Review batches for manual validation of candidates.
- `data/candidates.json` — Pre-ranked candidate mappings.
- `data/zephyr_api_updates.json` — (Legacy) In-progress synthesized objectives + Zephyr step-by-step testScript payloads. Current work uses the per-case `refined-cases/.../zephyr_payload.json` files.
- `tool/` — Scripts for extraction (TestLink, Zephyr), candidate building, review HTML generation, rendering batches, objective drafting support (`draft_stub.py`), and upload (`upload_refined.py`).
- `OBJECTIVE_DRAFTING_PROCESS.md` — Repeatable Steps 1-3 + generalized templates, worked examples (Port family), and traceability notes. The primary reference for refining/synthesizing Objectives.
- `ENRICHMENT_QUALITY_ANALYSIS.md`, `VALIDATION_RESULTS.md`, `findings.md` — Analysis and discovery notes.
- `review.html` — Interactive review sheet.

## Enrichment Focus

The enrichment of automated test case descriptions (via log analysis) is central to interpreting testing intent. This makes the detailed Automated Test Suites usable for:
- Defining Objectives for thin Manual Test Cases.
- Establishing fuzzy many-to-one mappings.

## Location and Workflow

The authoritative copy of this work lives on `terrenceb-dl` at:
`/media/terrenceb/mnt/testbox_home/copilot/Test-cases/`

This local directory is a synchronized mirror (see sync commands in root `AGENTS.md`).

Work (especially data gathering and heavy processing) is performed on `terrenceb-dl` via nested SSH:
`ssh mrfuji@diglettscave.cooldad.top "ssh terrenceb@10.33.22.17 '...' "`

Focus is on data transformation, enrichment accuracy, overlap identification, Objective synthesis, and relationship mapping. Writing updates back to Zephyr is the final step.

### Uploading Refined Cases
Once one or more cases have `refined-cases/<Category>/AWPTCM-Txxxx/zephyr_payload.json` (with objective + testScript), use the uploader:

```
cd copilot/Test-cases
JIRA_KEY=... python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235 AWPTCM-T33323
JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --verify
JIRA_KEY=... python3 tool/upload_refined.py --execute --groups "Port (7)" "QoS (22)"
```

See `tool/upload_refined.py --help` and `OBJECTIVE_DRAFTING_PROCESS.md` (Step 4). Always review with `--dry-run` first. The script follows the same JIRA_KEY + Bearer auth as the extract tools.

## Current Status (High-Level)

- Enrichment of Automated Suites largely complete (116+ suites, ~10k test cases).
- Candidate generation (from TestLink/AWP source) and review batches produced for the ~410 Manual Test Cases.
- Decisions recorded across 14 batches (supporting many-to-one).
- Analysis of enrichment quality and validation against source data performed.
- **Objective drafting process refined** (see OBJECTIVE_DRAFTING_PROCESS.md): now a clean reusable template with generalized steps. Standardized per-test-case output structure introduced under `refined-cases/<AWPTCM-Txxxx>/` containing `traceability.md` and `zephyr_payload.json`.
- ~30+ cases fully processed. A server-backed drafting tool implementation in `drafting-tool/` is now significantly advanced (see `drafting-tool/PROGRESS.md` for current status, backlog, and handoff notes; `drafting-tool/SERVER-README.md` for usage; and `drafting-tool/PLAN-server-backed.md` for the approved plan).
  - Real selectable data + justifications for Step 1 (TestLink) and Step 2 (Zephyr).
  - LLM-assisted pre-selection ("Suggest with LLM") for Step 3 (ATPyLib) using new prompt + retrieval.
  - Dynamic real case list with auto pre-filled demo for T33234 (steps 1-3) under MOCK.
  - Major UI compaction so tables fit on one page (no side scroll).
  - Human-readable formatted output (objectives + steps) in Step 4.
- ~30+ cases fully processed through the workflow across groups: Port (~7), IPv4 variants (ARP/DHCP/Static/BGP/VRF ~10+), PoE/LED/Sanity (~5), Switching (~4), Auth/Security (~4), Management (~2), Bootloader (~1).
- Recent focus (2026-06-29 session): IPv4 areas including T43849 (Local Proxy ARP), T43851 (DHCP ARP Probe), T43853 (120-day lease), T43854 (DNS Relay), T43855 (IPv4 Static), T43858 (BGPv4), T43859 (VRF-Lite traceroute). Includes thin TL cases, platform variation handling ("on some platforms if applicable"), and feature-family + ART cross-ref.
- Workflow validated on low/null-primary cases, VRF isolation/traceroute, BGP/unicast, long leases, and mixed TL/ART sources. User feedback incorporated for generalization.
- Ongoing focus on refining data accuracy, Objective synthesis, and capturing many-to-one mappings. Session state saved in SESSION_STATE.md.

See [data/suites/ENRICHMENT_STATE.md](data/suites/ENRICHMENT_STATE.md) for detailed phase status, [ENRICHMENT_QUALITY_ANALYSIS.md](ENRICHMENT_QUALITY_ANALYSIS.md) for enrichment specifics, and [data/suites/_enrichment_agent_spec.md](data/suites/_enrichment_agent_spec.md) for the enrichment prompt.

## Related Files

- [resources.md](resources.md) — Links to source systems (TestLink, Zephyr, ART).
- [findings.md](findings.md) — Phase 1 discovery notes (connectivity, target scope, early blockers).
- [ENRICHMENT_QUALITY_ANALYSIS.md](ENRICHMENT_QUALITY_ANALYSIS.md) — Analysis of enrichment script quality, schema fixes, and data completeness.
- [VALIDATION_RESULTS.md](VALIDATION_RESULTS.md) — Post-enrichment validation of automated suites against ART source pages.
- [data/suites/ENRICHMENT_STATE.md](data/suites/ENRICHMENT_STATE.md) — Detailed phase status, assets, and resume instructions.
- [data/suites/_enrichment_agent_spec.md](data/suites/_enrichment_agent_spec.md) — The AI agent prompt/spec used for log enrichment.
- `secrets.md` — API keys (JIRA, TestLink) — gitignored in some contexts.
- Root project [AGENTS.md](../AGENTS.md) — Broader context, access patterns, and Terrenceb-dl details.
- Drafting tool work: See `drafting-tool/PROGRESS.md` (status, backlog, technical debt, handoff), `drafting-tool/SERVER-README.md` (usage + architecture), `drafting-tool/LESSONS_LEARNED.md`. Recent progress: real data for Steps 1-3 + LLM pre-select in Step 3, dynamic cases + pre-fills for T33234 demo, UI compaction for one-page fit, human-readable Step 4 output. Always start with `drafting-tool/PROGRESS.md` + cross-ref root README + `SESSION_STATE.md`.

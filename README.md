# Test-cases

**Proprietary and Confidential — All Rights Reserved**

Copyright (c) 2026 terrenceb-atlnz. All rights reserved.

**No license is granted.** This repository and all contents (source code, data files, documentation, and tools) are the exclusive proprietary property of the copyright holder.

You may **not** copy, use, modify, distribute, sublicense, or create derivative works from any part of this work without prior express written permission.

Unauthorized access, use, or distribution is strictly prohibited.

---

Tools, data, and workflows for enriching and mapping **AWPTCM manual test cases** (Zephyr) using historical TestLink cases and enriched ATPyLib automated test suites.

## Getting Started

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases

# Required: materialize large source files
git lfs install
git lfs pull
```

**Requirements:** Python 3 + [Git LFS](https://git-lfs.com/).

Large Zephyr sources (`zephyr_cases.jsonl`, full XML export, related indexes) live in the repo via Git LFS. Prefer `data/zephyr_full/slim_index.json` for day-to-day work; see `data/zephyr_full/README.md`. The original Zephyr XML export remains the immutable source of truth.

## Project Goal

Manual cases (`AWPTCM-Txxxx` under New Platform Test (MASTER)) often lack clear **Objectives** (and sometimes preconditions). The project uses two other silos to define what those cases should verify and how they map to automation:

| Source | Role |
|--------|------|
| **TestLink (historical)** | Detailed human-authored cases (AWP-*) for artefact context and overlap |
| **ATPyLib (automated)** | Enriched suites describing what automation actually tests *for* |

Primary outcomes:

1. **Objectives** — declarative artefact lists (`<ul><li>…</li></ul>`) for each manual case  
2. **testScript steps** — Zephyr-ready verification steps (first step is usually a traceability note)  
3. **Traceability** — TestLink / Zephyr / ART mappings and gaps recorded per case  
4. **Many-to-one suite → case mappings** where automation is more granular than the manual case  

Authoritative process: **`OBJECTIVE_DRAFTING_PROCESS.md`**.

## Current Status

| Area | Status |
|------|--------|
| ATPyLib suite enrichment | Largely complete (~116+ suites, ~10k tests) |
| Candidate generation + decisions | ~410 AWPTCM cases; decisions across review batches |
| Refined case outputs | **~41** cases with `traceability.md` + `zephyr_payload.json` under `refined-cases/<Group>/` |
| Objective drafting process | Stable, documented, used in production workflow |
| Server-backed drafting tool | Advanced under `drafting-tool/` (primary way to run the process with LLM synthesis) |

**Refined-case groups present** (examples): Port, IPv4, Switching, QoS, Sanity Check, Authentication & Security, Management, Bootloader.

**Session history / working notes:** `SESSION_STATE.md` (long-form). Prefer `drafting-tool/PROGRESS.md` when continuing drafting-tool work.

## Objective Drafting Workflow

Repeatable steps (see `OBJECTIVE_DRAFTING_PROCESS.md`):

1. **TestLink + decisions** — review candidates, confirm primary/relevant list  
2. **Zephyr cross-reference** — related external cases (not the current managed Cases list)  
3. **ATPyLib** — map automation coverage and gaps  
4. **Synthesize** — objectives + testScript (LLM-assisted in the tool, always user-reviewed)  
5. **Export** — `refined-cases/<Group>/AWPTCM-Txxxx/{traceability.md,zephyr_payload.json}`  
6. **Upload** — optional push to Zephyr via `tool/upload_refined.py`

### Server-backed drafting tool (recommended)

Implementation lives entirely under **`drafting-tool/`**:

```bash
./drafting-tool/run.sh
# then open http://localhost:8000/
```

- FastAPI backend + wizard UI; server-side confirm gates before synthesis  
- LLM via **local subscription CLIs** (UI): Grok CLI (SuperGrok / X Premium+) or Claude Code CLI (Team)  
- Real data for TestLink / relevance-ranked Zephyr / ATPyLib; export downloads **and** auto-persists into `refined-cases/`  
- MOCK/demo paths removed — real CLI login (or server-side API key for legacy) required  

| Doc | Use for |
|-----|---------|
| [`drafting-tool/PROGRESS.md`](drafting-tool/PROGRESS.md) | **Start here** — status, backlog, handoff |
| [`drafting-tool/SERVER-README.md`](drafting-tool/SERVER-README.md) | Run, architecture, LLM modes, nginx |
| [`drafting-tool/PLAN-server-backed.md`](drafting-tool/PLAN-server-backed.md) | Approved design rationale |
| [`drafting-tool/LESSONS_LEARNED.md`](drafting-tool/LESSONS_LEARNED.md) | Prior decisions and pitfalls |

### Upload refined cases to Zephyr

```bash
JIRA_KEY=... python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235
JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --verify
JIRA_KEY=... python3 tool/upload_refined.py --execute --groups "Port (7)" "IPv4 (44)"
```

Always dry-run first. Auth matches the extract tools (JIRA_KEY + Bearer). Details: `tool/upload_refined.py --help` and Step 4 in `OBJECTIVE_DRAFTING_PROCESS.md`.

## Repository Layout

```
Test-cases/
├── OBJECTIVE_DRAFTING_PROCESS.md   # Process source of truth
├── SESSION_STATE.md                # Broader session history
├── refined-cases/                  # Per-case outputs (drop-in for upload)
│   └── <Group>/AWPTCM-Txxxx/
│       ├── traceability.md
│       └── zephyr_payload.json
├── drafting-tool/                  # Server-backed Objective Drafting Tool
├── data/
│   ├── zephyr_master.json          # ~410 target manual cases
│   ├── candidates.json             # Pre-ranked TestLink candidates
│   ├── decisions/                  # Human match decisions
│   ├── zephyr_full/                # slim_index + zephyr_cases.jsonl (LFS)
│   └── suites/                     # Enriched ATPyLib + TestLink extracts
└── tool/                           # Extract, candidates, review, upload scripts
```

### Key data & tools

- **`data/zephyr_master.json`** — Manual cases under refinement  
- **`data/candidates.json`** + **`data/decisions/`** — TestLink match pipeline  
- **`data/suites/`** — Enriched ATPyLib (`test_id_description.json`, `suite_*_enriched.json`, …) and TestLink extract  
- **`data/zephyr_full/`** — Full Zephyr DB working format (prefer slim index)  
- **`tool/`** — Extraction, candidate build, review HTML, `upload_refined.py`, etc.  
- **`data/zephyr_api_updates.json`** — Legacy aggregate payload; new work uses per-case `refined-cases/` only  

## Related Documentation

| File | Description |
|------|-------------|
| [OBJECTIVE_DRAFTING_PROCESS.md](OBJECTIVE_DRAFTING_PROCESS.md) | Repeatable drafting process + output shapes |
| [SESSION_STATE.md](SESSION_STATE.md) | Chronological work history |
| [resources.md](resources.md) | Links to TestLink, Zephyr, ART |
| [findings.md](findings.md) | Early discovery notes |
| [ENRICHMENT_QUALITY_ANALYSIS.md](ENRICHMENT_QUALITY_ANALYSIS.md) | Enrichment quality / schema |
| [VALIDATION_RESULTS.md](VALIDATION_RESULTS.md) | Suite validation vs ART |
| [data/suites/ENRICHMENT_STATE.md](data/suites/ENRICHMENT_STATE.md) | Enrichment phase resume notes |
| [data/suites/_enrichment_agent_spec.md](data/suites/_enrichment_agent_spec.md) | Log-enrichment agent spec |
| External [AGENTS.md](../AGENTS.md) | Environment, access patterns, CLI install (if present) |

`secrets.md` (API keys) is local/gitignored where configured — do not commit credentials.

> **Note:** Primary development is on an internal machine; this GitHub tree is a published copy. Some internal paths may appear in older notes.

## Copyright

See the notice at the top of this file and the `COPYRIGHT` file in the repository root.

All rights reserved. No permissions are granted to use, copy, or distribute this work.

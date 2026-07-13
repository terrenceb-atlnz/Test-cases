# Test-cases

<p align="center">
  <img src="ask-ck/ck-facelift/ckc.jpg" alt="Ask CK" width="140" style="border-radius:50%;" />
</p>

<h3 align="center">Ask CK — Test Tooling Workbench</h3>

**Proprietary and Confidential — All Rights Reserved**

Copyright (c) 2026 terrenceb-atlnz. All rights reserved.

**No license is granted.** This repository and all contents (source code, data files, documentation, and tools) are the exclusive proprietary property of the copyright holder.

You may **not** copy, use, modify, distribute, sublicense, or create derivative works from any part of this work without prior express written permission.

Unauthorized access, use, or distribution is strictly prohibited.

---

Tools, data, and workflows for enriching and mapping **AWPTCM manual test cases** (Zephyr) using historical TestLink cases and enriched ATPyLib automated test suites — delivered through **Ask CK**, a server-backed multi-tool test-engineering workbench.

## Getting Started

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases

# Required: materialize large source files
git lfs install
git lfs pull
```

**Requirements:** Python 3 + [Git LFS](https://git-lfs.com/).

Large Zephyr sources (`zephyr_cases.jsonl`, full XML export, related indexes) live in the repo via Git LFS under `ask-ck/objective-drafting/data/zephyr_full/`. Prefer `slim_index.json` for day-to-day work; see `ask-ck/objective-drafting/data/zephyr_full/README.md`. The original Zephyr XML export remains the immutable source of truth.

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

Authoritative process: **`ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`**.

## Current Status

| Area | Status |
|------|--------|
| ATPyLib suite enrichment | Largely complete (~116+ suites, ~10k tests) |
| Candidate generation + decisions | ~410 AWPTCM cases; decisions across review batches |
| Refined case outputs | **~42** cases with `traceability.md` + `zephyr_payload.json` under `ask-ck/objective-drafting/refined-cases/<Group>/` |
| Objective drafting process | Stable, documented, used in production workflow |
| **Ask CK workbench** | Multi-tool facelift complete (2026-07-13): Objective/Test Case Generator (full), sidebar LLM Configure panel, plus Test Composer and Zephyr Templating Tool (scaffolded) — see `ask-ck/objective-drafting/PROGRESS.md` |
| **PyTest Creator** | **Fully implemented (2026-07-14):** 8-step gated flow turning refined cases into runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test scripts, with a script-database index, testbox SSH execution, and an LLM fix loop to Final Validation — see `ask-ck/pytest-create/PLAN-pytest-creator.md` |

**Refined-case groups present** (examples): Port, IPv4, Switching, QoS, Sanity Check, Authentication & Security, Management, Bootloader.

**Session history / working notes:** `SESSION_STATE.md` (long-form). Prefer `ask-ck/objective-drafting/PROGRESS.md` when continuing Ask CK work.

## Ask CK Workbench

Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. This same welcome + per-tool guide is the **Main** splash page inside the app (sidebar → **Help → Main**).

```bash
./ask-ck/CK-main/run.sh
# then open http://localhost:8000/   (opens on the Main splash page)
```

- FastAPI backend (`ask-ck/CK-main/CK_server/`) + multi-tool sidebar UI; **server-side confirm gates** at every step.
- LLM via **local subscription CLIs** (sidebar **LLM → Configure**): Grok CLI or Claude Code CLI; the workspace login persists across cases. Set this up first — most tools need it. (MOCK/demo paths removed — real CLI login required.)

The tool guides below are in **inverse order of the sidebar list** (i.e. oldest/most-complete first), matching the Main splash page.

### Objective / Test Case Generator

The original Ask CK tool. Turns a sparse AWPTCM manual case into a refined case with declarative objectives, Zephyr-ready test steps, and traceability — with a review gate at every step. Authoritative process: `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`.

1. **Cases** — pick a case from the Open/partial or Complete dropdown and Load it.
2. **TestLink** — review the primary decision and candidate historical cases; Search or Suggest with the LLM, then Confirm your selections.
3. **Zephyr** — review related external Zephyr cross-references (not the managed Cases list); Confirm.
4. **ATPyLib (scored)** — review the scored automation-coverage candidates and Confirm which ART suites apply.
5. **Objectives (LLM)** — synthesize the declarative objective artefacts from the confirmed reviews; edit, then Confirm.
6. **Test Steps (LLM)** — synthesize the Zephyr test steps from the finalized objective, then **Export the Repeatable Bundle** — this writes `traceability.md` + `zephyr_payload.json` into `ask-ck/objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/`. A case becomes **Complete** once this exists.

Gaps for Traceability are synthesized by the LLM at the synthesize/export step (not user-edited mid-wizard). Optional final step: push a refined case to Zephyr with `tool/upload_refined.py` (see below).

### PyTest Creator

Turns a **Complete** case (one exported by the Generator above) into a runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test script, then runs it on real hardware and iterates until it passes. Each step has a Confirm gate.

1. **Cases** — pick a Complete case and Load it (use **↻ Refresh list** after exporting new cases in the Generator).
2. **Sequence** — the LLM extracts a prescriptive sequence of automatable steps from the refined case; edit the rows, Save, then Confirm.
3. **Script Search** — search the script databases (`testsuites_art` / `svt_scripts` / `test_scripts`) for scripts that do all, some, or none of the sequence; tick what to reuse, then Confirm.
4. **Fit Decision** — decide whether the sequence fits an existing script (reuse / extend) or needs a new one; Confirm.
5. **Fragments** — gather reusable code from the selected scripts (resolved to real source by line range), untick what you don't want, then Confirm.
6. **Generate** — the LLM composes the script from fragments + gaps; edit the Group/name, Lint, Save to `ask-ck/pytest-create/generated/<Group>/<Name>.py`, then Confirm.
7. **Run** — pick a stored testbox (or add one under **Testboxes**), choose the `.setup`, and run it over SSH; results are parsed into per-TestCase PASS/FAIL.
8. **Validate** — Final Validation passes when every TestCase is PASS with zero failures. On failures, **Fix with LLM** loops back to Generate; promotion into `testsuites_art/` is manual.

First-time setup — build the script index (re-run when the script repos change), and add a testbox under the **Testboxes** sidebar item:

```bash
cd tool
./build_script_index.py --mechanical-only    # AST scan of the 3 script DBs + framework surface
./enrich_script_index.py --limit 100          # optional resumable LLM tagging (uses the workspace CLI login)
./build_script_index.py                       # rebuild with enrichment merged
```

Stored testboxes live in the gitignored `secrets.testboxes.json` (passwords write-only; passwordless sudo on the box required).

### Test Composer

**TBD — scaffolded, not yet implemented.**

### Zephyr Templating Tool

**TBD — scaffolded, not yet implemented.**

### Documentation map

| Doc | Use for |
|-----|---------|
| [`ask-ck/objective-drafting/PROGRESS.md`](ask-ck/objective-drafting/PROGRESS.md) | **Start here** — status, backlog, handoff |
| [`ask-ck/CK-main/SERVER-README.md`](ask-ck/CK-main/SERVER-README.md) | Run, architecture, LLM modes, PyTest Creator, nginx |
| [`ask-ck/pytest-create/PLAN-pytest-creator.md`](ask-ck/pytest-create/PLAN-pytest-creator.md) | **PyTest Creator** plan + progress tracker |
| [`ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`](ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md) | Generator process source of truth |
| [`ask-ck/objective-drafting/PLAN-server-backed.md`](ask-ck/objective-drafting/PLAN-server-backed.md) | Approved design rationale (historical paths) |
| [`ask-ck/objective-drafting/LESSONS_LEARNED.md`](ask-ck/objective-drafting/LESSONS_LEARNED.md) | Prior decisions and pitfalls |
| [`ask-ck/ck-facelift/PLAN-facelift.md`](ask-ck/ck-facelift/PLAN-facelift.md) | 2026-07-13 multi-tool facelift plan (as executed) |

### Upload refined cases to Zephyr

```bash
JIRA_KEY=... python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235
JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --verify
JIRA_KEY=... python3 tool/upload_refined.py --execute --groups "Port (7)" "IPv4 (44)"
```

Always dry-run first. Auth matches the extract tools (JIRA_KEY + Bearer). Details: `tool/upload_refined.py --help` and Step 4 in `ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`. (If the script has not yet been repathed for the 2026-07-13 restructure, run it with paths pointed at `ask-ck/objective-drafting/refined-cases/`.)

## Repository Layout

```
Test-cases/
├── SESSION_STATE.md                # Broader session history
├── ask-ck/                         # Ask CK workbench (all tool code, data, docs)
│   ├── CK-main/                    # App: run.sh, SERVER-README.md, design assets
│   │   └── CK_server/              # FastAPI server (main.py, paths.py, routers/, static/, templates/, sessions/)
│   ├── objective-drafting/         # Generator data + docs + outputs
│   │   ├── OBJECTIVE_DRAFTING_PROCESS.md   # Process source of truth
│   │   ├── PROGRESS.md             # Primary handoff document
│   │   ├── data/                   # zephyr_master, candidates, decisions, suites, zephyr_full (LFS)
│   │   └── refined-cases/          # Per-case outputs (drop-in for upload)
│   │       └── <Group>/AWPTCM-Txxxx/{traceability.md, zephyr_payload.json}
│   ├── ck-facelift/                # Facelift plan (2026-07-13)
│   ├── pytest-create/              # PyTest Creator: PLAN-pytest-creator.md, data/ (index), generated/<Group>/<Name>.py
│   ├── test-composer/              # (future) Test Composer assets
│   └── zephyr-tool/                # (future) Zephyr Templating Tool assets
└── tool/                           # Extract, candidates, review, upload + build_script_index.py / enrich_script_index.py
```

### Key data & tools

- **`ask-ck/objective-drafting/data/zephyr_master.json`** — Manual cases under refinement  
- **`ask-ck/objective-drafting/data/candidates.json`** + **`data/decisions/`** — TestLink match pipeline  
- **`ask-ck/objective-drafting/data/suites/`** — Enriched ATPyLib (`test_id_description.json`, `suite_*_enriched.json`, …) and TestLink extract  
- **`ask-ck/objective-drafting/data/zephyr_full/`** — Full Zephyr DB working format (prefer slim index)  
- **`tool/`** — Extraction, candidate build, review HTML, `upload_refined.py`, etc.  
- **`ask-ck/objective-drafting/data/zephyr_api_updates.json`** — Legacy aggregate payload; new work uses per-case `refined-cases/` only  

## Related Documentation

| File | Description |
|------|-------------|
| [ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md](ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md) | Repeatable drafting process + output shapes |
| [SESSION_STATE.md](SESSION_STATE.md) | Chronological work history |
| [resources.md](resources.md) | Links to TestLink, Zephyr, ART |
| [ask-ck/objective-drafting/ENRICHMENT_QUALITY_ANALYSIS.md](ask-ck/objective-drafting/ENRICHMENT_QUALITY_ANALYSIS.md) | Enrichment quality / schema |
| [ask-ck/objective-drafting/VALIDATION_RESULTS.md](ask-ck/objective-drafting/VALIDATION_RESULTS.md) | Suite validation vs ART |
| [ask-ck/objective-drafting/data/suites/ENRICHMENT_STATE.md](ask-ck/objective-drafting/data/suites/ENRICHMENT_STATE.md) | Enrichment phase resume notes |
| [ask-ck/objective-drafting/data/suites/_enrichment_agent_spec.md](ask-ck/objective-drafting/data/suites/_enrichment_agent_spec.md) | Log-enrichment agent spec |
| External [AGENTS.md](../AGENTS.md) | Environment, access patterns, CLI install (if present) |

`secrets.md` (API keys) is local/gitignored where configured — do not commit credentials.

> **Note:** Primary development is on an internal machine; this GitHub tree is a published copy. Some internal paths may appear in older notes. On 2026-07-13 the repo was restructured: `drafting-tool/` → `ask-ck/CK-main/` (+ `CK_server/`), and root `data/`, `refined-cases/`, and process docs → `ask-ck/objective-drafting/`. Historical docs (SESSION_STATE entries, PLAN-server-backed.md, old traceability artefacts) may still reference the pre-move paths.

## Copyright

See the notice at the top of this file and the `COPYRIGHT` file in the repository root.

All rights reserved. No permissions are granted to use, copy, or distribute this work.

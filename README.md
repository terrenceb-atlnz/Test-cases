# Test-cases
=D
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

**Quick start (recommended):** the bootstrap script does all of the below in one go — LFS pull, virtual environment, dependency install — then offers to launch the server:

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases
./setup.sh          # idempotent; safe to re-run
```

<details>
<summary>Or do it manually</summary>

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases

# Required: materialize large source files
git lfs install
git lfs pull

# Recommended: isolate the Python dependencies in a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Required: install the Ask CK server dependencies
pip install -r ask-ck/CK-main/requirements.txt
```

</details>

**Requirements:** Python 3 + [Git LFS](https://git-lfs.com/) **≥ 3.3** + the Python packages in [`ask-ck/CK-main/requirements.txt`](ask-ck/CK-main/requirements.txt) (FastAPI, uvicorn, Jinja2, requests, python-multipart, pydantic). Installing these is mandatory — the server will not start without them (you'll get `ModuleNotFoundError: No module named 'fastapi'`).

> **Git LFS version matters on Ubuntu.** Older Git LFS (e.g. 3.0.2, the version in Ubuntu's apt repos) is incompatible with modern Git (2.38+) and fails `git lfs pull` on a fresh clone with `cannot add to the index - missing --add option?`. If you hit this, install a current Git LFS from its own repo rather than apt:
> ```bash
> curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
> sudo apt-get install git-lfs      # now installs 3.3+
> git lfs install
> ```

> **On the virtual environment:** the `venv` is recommended but optional — it only isolates *where* these packages are installed, it does not change how the project runs. If you skip it, install into your user site-packages instead with `pip install --user -r ask-ck/CK-main/requirements.txt`. `run.sh` **auto-activates a repo-local `.venv` if present**, so you don't need to activate it first to start the server. You still need to activate it yourself (`source .venv/bin/activate`) before running `tool/*.py` scripts directly.

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
| **Ask CK workbench** | Multi-tool facelift complete (2026-07-13): Objective/Test Case Generator (full), sidebar LLM Configure panel, plus Test Composer and Zephyr Templating Tool (scaffolded) — see `ask-ck/objective-drafting/PROGRESS.md`. **Frontend refactored to browser-native ES modules (2026-07-16)** — `static/app.js` → `static/js/` (see `static/js/README.md`). |
| **Generator review UX** | **Two-table "chosen shortlist" (2026-07-16)** on the TestLink/Zephyr/ATPyLib steps (candidates ↑ / chosen ↓, insertion-ordered; confirm reads the chosen table only), plus **relevance-ranked keyword search** (title-weighted scoring; each new search re-ranks the whole candidate pool) |
| **PyTest Creator** | **Fully implemented (2026-07-14):** 8-step gated flow turning refined cases into runnable Allied Telesis `framework` (ATTestSet/ATTestCase) test scripts, with a script-database index, testbox SSH execution, and an LLM fix loop to Final Validation — see `ask-ck/pytest-create/PLAN-pytest-creator.md` |

**Refined-case groups present** (examples): Port, IPv4, Switching, QoS, Sanity Check, Authentication & Security, Management, Bootloader.

**Session history / working notes:** `SESSION_STATE.md` (long-form). Prefer `ask-ck/objective-drafting/PROGRESS.md` when continuing Ask CK work.

## Ask CK Workbench

Ask CK is a server-backed test-engineering workbench for the AWPTCM test-case program. It brings the tools for enriching manual test cases, mapping them to automation, and turning them into runnable scripts into one place. This same welcome + per-tool guide is the **Main** splash page inside the app (sidebar → **Help → Main**).

```bash
# One-time: install the server dependencies (see Getting Started, or run ./setup.sh)
pip install -r ask-ck/CK-main/requirements.txt

./ask-ck/CK-main/run.sh        # auto-uses .venv; asks foreground or background
# then open http://localhost:8000/   (opens on the Main splash page)

./ask-ck/CK-main/run.sh --stop # stop a backgrounded server
```

`run.sh` automatically uses the repo-local `.venv` (if present) and, when run interactively, asks whether to run in the **foreground** (Ctrl-C to stop) or the **background**. Background mode prints the PID + log path and is stopped with `./ask-ck/CK-main/run.sh --stop` (or `./setup.sh --stop`). Background logs append to `.ck-server.log`.

> **Use `http://`, not `https://`.** Ask CK serves plain HTTP. If your browser forces HTTPS (Firefox HTTPS-Only mode, HSTS) you'll get a blank "Secure Connection Failed" / `SSL_ERROR_RX_RECORD_TOO_LONG` page. Browse to `http://localhost:8000/` explicitly and, if needed, exempt localhost from HTTPS-Only mode. Note the banner prints `http://0.0.0.0:8000` — `0.0.0.0` is the bind address; browse via `localhost` or `127.0.0.1`.

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

**Review steps 2–4 use a two-table "chosen shortlist" (2026-07-16):** the top **candidates** table holds Search / Suggest results (keyword Search is relevance-ranked — title matches outrank body-only hits, and each new search re-ranks the whole pool against the new terms); tick rows and click **↓ Choose selected** to move them into the bottom **chosen** table, which stays in the order you added them. **Clear selected contents** moves chosen rows back up. **Mark Reviewed + Confirmed reads only the chosen table.** LLM **Suggest** drops its picks straight into the chosen table. Loading a previously-confirmed case pre-populates the chosen tables.

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
│   ├── CK-main/                    # App: run.sh, requirements.txt, SERVER-README.md, design assets
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

---

## Setup & Maintenance Fix Log — 2026-07-15

This section records the setup/install fixes made on 2026-07-15 while walking the
Getting Started flow on a fresh Ubuntu machine, and *why* each was needed.

| # | Fix | Why it was needed |
|---|-----|-------------------|
| 1 | **Added `ask-ck/CK-main/requirements.txt`** and documented it as a mandatory install step. | The server crashed on startup with `ModuleNotFoundError: No module named 'fastapi'`. The app's Python dependencies (FastAPI, Jinja2, requests, …) were never listed anywhere, so a fresh clone had no way to know what to install. `uvicorn` starting but then failing to import the app was the confusing symptom. |
| 2 | **Added a virtual-environment step** (`python3 -m venv .venv` + activate) to Getting Started. | Isolates the dependencies from the user's global/site packages so versions can't collide with other projects. Optional but recommended — it does not change how the project runs, only *where* the packages live. |
| 3 | **Documented Git LFS ≥ 3.3** and how to install it from the git-lfs repo instead of apt. | On Ubuntu, apt ships Git LFS 3.0.2, which is incompatible with modern Git (2.38+). A fresh `git lfs pull` fails with `cannot add to the index - missing --add option?`. It only "worked" on the dev machine because the large files were already materialized, so the smudge step never ran. |
| 4 | **Documented HTTP-only access** (`http://`, not `https://`) and the `0.0.0.0` bind-address gotcha. | Browsers with HTTPS-Only mode (e.g. Firefox) auto-upgrade to `https://`, and the plain-HTTP server can't answer a TLS handshake — producing a blank `SSL_ERROR_RX_RECORD_TOO_LONG` page and a `WARNING: Invalid HTTP request` in the server log. A same-port https→http redirect is not possible (the failure is at the TLS layer, before any HTTP is exchanged). |
| 5 | **Added `setup.sh`** — an idempotent one-shot bootstrap (git-lfs check → LFS pull → venv → deps → offer to launch). | `run.sh` assumes everything is already set up and gives cryptic errors otherwise. `setup.sh` performs the full first-time setup in order and can be safely re-run. It also **detects a missing or too-old git-lfs (< 3.3) and offers to install/upgrade it** (via the packagecloud apt repo, with `sudo`, after asking) so fix #3 is handled automatically rather than left to the reader. To start the server it **delegates to `run.sh`** (which asks foreground/background — see #8); `./setup.sh --stop` also delegates to `run.sh --stop`. |
| 5a | **git-lfs upgrade installs an explicit version.** | On this machine the Ubuntu **ESM** repo pins git-lfs 3.0.2 at a *higher* apt priority (510) than packagecloud (500), so a plain `apt-get install git-lfs` kept the old version. `setup.sh` now installs the newest available version explicitly (`git-lfs=<latest>`) to bypass the pin. |
| 6 | **Corrected stale Git LFS paths in `.gitattributes`.** | After the 2026-07-13 restructure, `data/` moved under `ask-ck/objective-drafting/`, but the LFS rules still pointed at the old `data/zephyr_full/…` paths and so matched nothing. `zephyr_cases.jsonl` (53 MB), `index.json` (17 MB), and `suites/testlink_awp.json` (28 MB) were therefore committed as plain Git blobs instead of LFS objects. Rules were repathed to the real locations; the `Zephyr-Database-*.xml` rule was unaffected because it is a path-independent filename glob. |
| 7 | **Renormalized the three files into LFS** (`git add --renormalize`). | With the rules corrected, the already-committed plain blobs were re-run through the LFS filter so their tracked representation becomes ~130-byte LFS pointers instead of full content. This makes fix #6 actually take effect on the existing files (not just future edits). Working-tree contents are unchanged; this does **not** rewrite history, so old blobs remain in past commits. |
| 8 | **`run.sh` now auto-activates the venv and offers foreground/background, with `--stop`.** | Previously you had to `source .venv/bin/activate` before `run.sh`, and it only ran in the foreground (Ctrl-C). Now `run.sh` auto-uses the repo-local `.venv` if present; when interactive it asks **[F]oreground / [b]ackground**; background mode detaches the process (own session/process group), records the PID in `.ck-server.pid`, appends to `.ck-server.log`, and is stopped cleanly with `./ask-ck/CK-main/run.sh --stop`. Non-interactive/CI runs default to foreground with no prompt. The background/stop mechanics live only in `run.sh`; `setup.sh` delegates to it (see #5). |

> **Note on fixes #6–#7:** the renormalize was **staged locally, not committed or pushed** — commit it when ready. It does not rewrite history (old blobs stay in past commits; use `git lfs migrate import` + a force-push for that, which is best avoided on a published repo). After this lands, fresh clones must `git lfs pull` (or run `setup.sh`) to materialize these files — the same as the XML already requires. None of these files exceed GitHub's 100 MB limit today, so this is preventative, not urgent.

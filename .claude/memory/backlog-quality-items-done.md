---
name: backlog-quality-items-done
description: "The 4 reconciled quality-backlog items (error UX, output hardening, process-page, tests) all DONE 2026-07-27b"
metadata: 
  node_type: memory
  type: project
  verified: 2026-08-17
  originSessionId: 1bde0fea-252d-4064-957c-c1795f0b4689
  modified: 2026-07-26T20:30:20.701Z
---

2026-07-27b: after reconciling the stale PROGRESS.md backlog (see [[pytest-artefact-review-worklist]]),
all four genuinely-open quality items were implemented + adversarially reviewed. Uncommitted at write
time (Terrence commits).

- **Error/loading UX**: new `showStatus()` in `static/js/dom-helpers.js` + `.status-banner` CSS
  (success/warning/error/busy, theme-aware, escapeHtml'd). Wired into `generator.js` exportBundle +
  synthesizeObjectives + synthesizeSteps. Static banner divs `#export-status`/`#objective-status`/
  `#steps-status` in `index.html` (export-status made STATIC after review, not generated).
- **Output-gen hardening**: the wizard's `export` handler (now `routers/wizard/export.py:340`,
  after the 2026-07-29 package split) REFUSES to write the drop-in bundle when
  `validate_zephyr_payload` fails hard issues (previously printed + wrote anyway). New
  `ExportResponse.wrote_bundle` bool. Blocked message is stale-bundle-aware (a prior on-disk bundle
  still marks the case Complete via `_refined_complete_keys` — don't falsely claim "NOT Complete").
- **Process-page drift**: `main.py::process_page` links nav to the doc's own `## Step N:` headings via
  GitHub-style deduped slug ids (shared document-order counter used by BOTH the h2-id pass and the
  nav discovery, so nav slug == heading id). Removed broken `/#step-N` + `#Step N` anchors.
- **Tests**: first suite at repo-root `tests/` (14 tests: validator branches, /export refuse-to-write
  via FastAPI TestClient, /process anchors). `pytest.ini` (pythonpath = both CK-main + CK-main/CK_server;
  the flat `import llm_debug` needs the inner dir). Dev deps `pytest`+`httpx` in
  `ask-ck/CK-main/requirements-dev.txt`. **Run: `PYTHONNOUSERSITE=1 .venv/bin/pytest -q`** (the
  PYTHONNOUSERSITE is REQUIRED — an older fastapi/starlette in ~/.local otherwise shadows the venv's
  and TestClient errors asking for a bogus "httpx2"). Or `./tool/run_tests.sh` (guards + pytest).

Adversarial review (3 parallel reviewers) found + fixed: duplicate heading id, stale-bundle message,
export-status silent-no-op. Cleared: XSS (both title+items escaped). See [[commit-and-push-on-session-end]].

# Ask CK — Multi-Tool Facelift (Step 1 of single-use → multi-use)

## Context

The Objective Drafting Tool is becoming **"Ask CK"**, a multi-tool test-engineering workbench. Step 1 (this plan) is a UI reorganizational facelift plus scaffolding for three future tools: **Zephyr Templating Tool**, **Test Composer**, and **PyTest Creator**.

Mid-planning, the repo was restructured (untracked, clearly intentional — it mirrors the multi-tool vision):

```
Test-cases/
├── ask-ck/
│   ├── CK-main/                 # was drafting-tool/ (run.sh, SERVER-README.md, design files)
│   │   └── CK_server/           # was drafting_server/ (main.py, data.py, llm.py, routers/, static/, sessions/, templates/)
│   ├── objective-drafting/      # data/, refined-cases/, PROGRESS.md, LESSONS_LEARNED.md, PLAN-server-backed.md, OBJECTIVE_DRAFTING_PROCESS.md
│   ├── pytest-create/           # empty — pre-staged for PyTest Creator
│   ├── test-composer/           # empty — pre-staged for Test Composer
│   └── zephyr-tool/             # empty — pre-staged for Zephyr Templating Tool
├── tool/                        # extraction/upload scripts (unchanged)
└── README.md, SESSION_STATE.md, ...
```

`CK_server/static/index.html` is byte-identical to the pre-move file (2817 lines; uncommitted Export/Edit-steps work intact — keep it). The move broke **three path anchors**, so the plan starts by making the relocated app boot.

**User decisions (confirmed):** sidebar sections always expanded; PyTest Creator "Cases" wired to real case lists; LLM Configure opens as a main-area panel; include backend router stubs.

---

## Phase 0 — Repath the relocated app (must boot before facelift is testable)

Create `ask-ck/CK-main/CK_server/paths.py` — single source of truth:

```python
from pathlib import Path
CK_SERVER_DIR = Path(__file__).resolve().parent          # .../ask-ck/CK-main/CK_server
ASKCK_ROOT    = CK_SERVER_DIR.parent.parent              # .../ask-ck
OBJECTIVE_DRAFTING_ROOT = ASKCK_ROOT / "objective-drafting"
DATA_DIR    = OBJECTIVE_DRAFTING_ROOT / "data"
REFINED_DIR = OBJECTIVE_DRAFTING_ROOT / "refined-cases"
PROCESS_MD  = OBJECTIVE_DRAFTING_ROOT / "OBJECTIVE_DRAFTING_PROCESS.md"
```

Fix the three broken anchors to use it:
- `CK_server/data.py:16` — `BASE = "."` (CWD-relative `data/...` loads) → anchor on `DATA_DIR` (keep the `load_json_safe` helper; join against `DATA_DIR` instead of `BASE`; note line 40 `data/decisions` too).
- `CK_server/routers/wizard.py:741` and `:1152` — `refined_root = BASE_DIR.parent.parent / "refined-cases"` (now resolves to `ask-ck/refined-cases`, missing) → `REFINED_DIR`.
- `CK_server/main.py:88` — `process_path = BASE_DIR/../../OBJECTIVE_DRAFTING_PROCESS.md` (now `ask-ck/…`, missing) → `PROCESS_MD`.

`SESSIONS_DIR` / templates (wizard.py:45-53) are CK_server-relative and moved with the code — untouched.

Fix `ask-ck/CK-main/run.sh` (stale): `PYTHONPATH=ask-ck/CK-main`, uvicorn target `CK_server.main:app`, `cd` to repo root (PROJECT_ROOT is currently computed as parent-of-script-dir; make it two levels up or cd explicitly), and rebrand echo text to "Ask CK". Imports inside main.py (`from data import…`, `from routers.wizard import…`) are sys.path-based and need no change.

---

## Phase 1 — UI facelift + expansion (all in `ask-ck/CK-main/CK_server/static/index.html`)

Line numbers below are current and verified.

### 1a. Renames
- Line 5 `<title>` → `Ask CK`; line 933 `.sidebar-logo-text` → `Ask CK`.
- Line 950 section label `Steps` → `Objective/Test Case Generator`.
- Step-0 heading (991) `Cases + LLM Configuration` → `Cases`; description (992) → case-selection wording only.
- `main.py:48` FastAPI title → `Ask CK (Server-Backed)`.

### 1b. Navigation primitive (new) — `goToPanel(panelId)`
All switchable main-area cards (`#step-0..#step-5` + 7 new panels) gain a shared class `tool-panel`. New global `let currentPanel = 'step-0'` beside `currentStep` (~1182).

```js
function goToPanel(panelId) {
  currentPanel = panelId;
  document.querySelectorAll('.tool-panel').forEach(el => el.classList.toggle('hidden', el.id !== panelId));
  document.querySelectorAll('.sidebar-nav-item').forEach(item => {
    const target = item.dataset.panel || (item.dataset.step !== undefined ? 'step-' + item.dataset.step : null);
    item.classList.toggle('active', target === panelId);
  });
  updatePageHeader();
  if (panelId === 'panel-pt-creator') renderPtCreatorPanel();
}
```

`goToStep(step)` (2413-2434) becomes a thin wrapper: set `currentStep`, call `goToPanel('step-'+step)`, keep the step===4 (renderReviewSummary/renderObjectiveResult) and step===5 (renderStepsResult) hooks. Its 8 callers (sidebar onclicks, bootstrap 2394, 1655, 1684, 2139, 2149, 2170) work unchanged. Bootstrap `goToStep(0)` stays.

`updatePageHeader` (2436-2457): replace the numeric `stepDescs` map with `PANEL_META` keyed by panel id — generator panels keep existing descriptions + the `currentKey — title` heading logic; tool panels get static `{title, desc}` overrides (LLM Provider Login, Zephyr Templating Tool steps, Test Composer, PyTest Creator).

### 1c. Sidebar rebuild (lines 942-976) — order top→bottom, all always expanded
1. **LLM** (label 943-946 + `#llm-status-sidebar` 947 unchanged) + new nav item **Configure** → `goToPanel('panel-llm-config')`, `data-panel="panel-llm-config"`, gear icon, **no data-step**.
2. **Zephyr Templating Tool**: `1. Info` / `2. Test Plan / Cycle / Cases` / `3. Link Test Scripts` / `4. TBD` → `panel-zt-info|-plan|-link|-tbd`.
3. **Test Composer**: `1. TBD` → `panel-tc-tbd`.
4. **PyTest Creator**: `1. Cases` / `2. Creator` → `panel-pt-cases|-creator`.
5. **Objective/Test Case Generator**: wrap in `<div class="sidebar-steps" id="nav-generator">`; the six existing items keep `onclick="goToStep(N)"` and `data-step="0..5"` **unchanged** — only labels renumber: `1. Cases`, `2. TestLink`, `3. Zephyr`, `4. ATPyLib (scored)`, `5. Objectives (LLM)`, `6. Test Steps (LLM)`.

Sidebar already scrolls (`overflow-y:auto`, line 135) — no layout CSS needed. Reuse existing `.sidebar-section-label` / `.sidebar-nav-item` / `.sidebar-steps` styles.

### 1d. LLM chunk relocation
Cut lines **1023-1061 verbatim** (heading, description, `.radio-group` with `llmAuthMethod` radios, `#grokCliStatusBtn`, `#cliStatusBtn`, `#llmModel`, Apply/Login, `#llmStatus`, `#claudeCodeInstructions`/`#cliStatusResult`, `#grokCliInstructions`/`#grokCliStatusResult`) into a new `<div id="panel-llm-config" class="card tool-panel hidden"><div class="section">…</div></div>` inserted **in place of the dead `#llm-config-card`** (1065-1066, deleted). Every id/handler preserved; all LLM JS is id-addressed (verified: setLLMConfig 1841, updateLLMStatus 1946 dual-writes `#llmStatus` + `#llm-status-sidebar`, updateAuthMethodUI 2002, restoreLLMUI 2034), and the panel stays in static DOM so bootstrap (2392-2395) is unaffected. Add one description sentence: Apply/Login persists into the currently loaded case + workspace default (backend 404s "Load a case first" — existing behavior, keep).

**Cleanups bundled:** delete `showLLMConfig()` no-op (1996-2000, zero callers); delete the phantom `#llmCredential` lookup + dead block in `updateAuthMethodUI` (2005, 2011-2015).

### 1e. Visible renumber sweep (labels/strings ONLY — edit each individually, never bulk-replace)
**Must NOT change:** `data-step` values, panel ids `step-0..step-5`, badge ids `#step1-badge..#step5-badge`, session keys `step1..step5`, `confirmStep(1|2|3)` onclicks / `/confirm_step/{key}/{1|2|3}` (backend accepts only 1/2/3 — wizard.py:1346-1393).
- In-panel headings: `Step 1: TestLink`→`Step 2: TestLink`, … `Step 5: Test Step Synthesis (LLM)`→`Step 6: …` (lines ~1074, 1092, 1109, 1126, 1151).
- In-panel texts/buttons: review summary "from steps 1–3"→"2–4"; "Confirm Objectives → Step 5"→"→ Step 6"; "Finalized objective (from Step 4)"→"(from Step 5)"; etc. (~1129-1161).
- JS user-visible strings at ~1538, 1574, 1628, 1786, 1835, 2119, 2123, 2148 (alerts/empty-states referencing step numbers), +1 each.

### 1f. New panels (insert after `#step-5` close ~1170, before `#session-debug`)
Seven cards, `class="card tool-panel hidden"`:
- `panel-zt-info`, `panel-zt-plan`, `panel-zt-link`, `panel-zt-tbd`, `panel-tc-tbd`: section-heading + `.placeholder-panel` (icon, "Under construction", purpose blurb). `panel-zt-info` and `panel-tc-tbd` also fetch `/api/<tool>/status` into a status span via a small `loadToolStatus(apiName, elId)` helper (proves the tool↔router pairing end-to-end).
- `panel-pt-cases`: **wired** (below). `panel-pt-creator`: heading + `#pt-creator-case` div + placeholder body.

New CSS block after the uncommitted `.btn-export` rules (~line 388): `.placeholder-panel` (dashed `var(--border-strong)` border, centered, token colors — works in both themes) + `.placeholder-title/.placeholder-text/.placeholder-status`.

### 1g. PyTest Creator "Cases" wiring (independent of the Generator's active case)
- Markup mirrors step-0's selects with **new ids** `#ptCaseSelOpen` / `#ptCaseSelDone` (+ count labels), a "Continue to Creator" button → `goToPanel('panel-pt-creator')`, and `#pt-selected-summary` span.
- JS (parameterize, don't fork — reuse existing generic `fillCaseSelect` 2262):
  - Extract fetch: `fetchCaseBuckets()` from `refreshCaseSelects` (2330).
  - Generalize mutual-exclusivity out of `onCaseSelectChange` (2297) into `handleCasePairChange(openSel, doneSel, sourceSel, onSelect)`; existing behavior byte-equivalent via callback that sets `currentKey`/`syncHiddenCaseSel`/`updatePageHeader`.
  - New `onPtCaseSelectChange`: callback sets only a new global `ptCase = {key, title}` + summary text. **Never** touches `currentKey`, `#caseSel`, or `updatePageHeader` (would silently retarget Generator load/confirm/export).
  - `refreshCaseSelects` fills **both** pairs from one fetch (counts + optgroups + restore selection), so bootstrap `initCases` (2381) and `clearCurrentSession` (2218) keep both fresh for free; bind pt listeners under the existing `_caseSelectListenersBound` guard.
  - `renderPtCreatorPanel()`: shows `Case: KEY — Title` or "No case selected — pick one in PyTest Creator → 1. Cases" (link back), + placeholder noting future `POST /api/pytest-create/generate/{key}`.

### 1h. Badge scoping
`updateUI` nav-badge loop (1305-1322): scope query to `#nav-generator .sidebar-nav-item[data-step]` so ✓ badges can only ever attach to Generator items (today non-numeric items survive only by `parseInt(undefined)→NaN` luck).

---

## Phase 2 — Backend router stubs (names match the pre-staged tool dirs)

New modules in `ask-ck/CK-main/CK_server/routers/` (pattern mirrors wizard.py's plain `router = APIRouter()`):
- `zephyr_tool.py` — `GET /status` → `{tool, status:"stub", message}`.
- `test_composer.py` — same shape.
- `pytest_create.py` — `GET /status` + `POST /generate/{key}` → HTTP 501.

`main.py`: import the three routers next to line 46; `include_router` next to line 62 with prefixes **`/api/zephyr-tool`, `/api/test-composer`, `/api/pytest-create`** (matching `ask-ck/<dir>` names, which will later hold each tool's data the way `objective-drafting/` does for the Generator).

`wizard.py`, `models.py`, confirm-step validation: untouched.

---

## Out of scope / deferred (noted, not done now)
- PROGRESS.md / SERVER-README.md / LESSONS_LEARNED.md updates — per session rules, handled by the user's end-of-session update prompt (note: they now live under `ask-ck/objective-drafting/` and `ask-ck/CK-main/`).
- Root `README.md` paths are stale after the restructure — flag as follow-up.
- `/process` page's hardcoded "Step 1..4" anchor text (main.py:108-133) — cosmetic drift vs new numbering; follow-up.
- Hash-routing / deep-links (refresh currently always lands on Generator Cases — matches today's behavior).

## Verification (manual smoke, after `./ask-ck/CK-main/run.sh`)
1. Server boots; startup logs show real data counts (proves Phase 0 repathing); `/health` ok; `/docs` lists three new tool tags; `curl` each `/api/<tool>/status` → 200, `POST /api/pytest-create/generate/X` → 501.
2. Tab title + sidebar logo "Ask CK"; sections in order LLM(+Configure) / Zephyr Templating Tool / Test Composer / PyTest Creator / Objective-Test Case Generator, all expanded; Generator "1. Cases" active; step-0 panel has **no** LLM chunk; console clean.
3. Configure panel: radios toggle instruction panels; Check Grok/Claude CLI render results; Apply/Login (case loaded) updates `#llmStatus` **and** sidebar status; hard-refresh restores LLM state.
4. Generator E2E on an open case: Load → confirm visible steps 2/3/4 (POSTs still `/confirm_step/{key}/1|2|3` → 200) → ✓ badges appear only on Generator items → Objectives (visible 5) synthesize/confirm → Test Steps (visible 6) synthesize; "Edit / Revise Steps" guard + teal Export button intact (uncommitted work preserved); export writes into `ask-ck/objective-drafting/refined-cases/<Group>/`.
5. PyTest Creator: both buckets populated with counts matching Generator; selecting there does **not** change Generator's loaded case or page title; Creator shows selected case or the pick-a-case prompt.
6. Placeholder panels styled correctly in dark + light themes; exactly one panel visible / one nav item active across all cross-navigation; Clear All refreshes both select pairs.

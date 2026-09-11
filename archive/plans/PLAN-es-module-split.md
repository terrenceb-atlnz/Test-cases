# ES-Module Split of `CK_server/static/app.js`

## Context

Ask-CK's frontend is a single 2663-line vanilla-JS file, `ask-ck/CK-main/CK_server/static/app.js`, loaded as a classic script at the end of `static/index.html`. It hosts five tools (Generator wizard, PyTest Creator, three DB-search tools) plus shared plumbing (session/fetch patch, nav, LLM config, agent bridge, theme). Adding features is getting slow and regression-prone. Goal: split it into browser-native ES modules — **no bundler, no package.json** — as a mechanical, behavior-preserving refactor.

**The one hard constraint:** all UI wiring goes through a delegated click dispatcher (`app.js:2631–2650`) that resolves handlers by name via `window[el.dataset.action]`. There are **52 distinct `data-action` names** — 39 in `index.html`, 13 more only inside `innerHTML` template literals in `app.js` (e.g. `ptViewSource`, `removeSynthesizedStep`, `ptRemoveSeqRow`). Module scope removes functions from `window`, so a naive split kills every button. Solution: an explicit **action registry**.

Verified facts that shape the plan:
- Hidden **boot block mid-file at `app.js:1408–1431`** (initSidebarAccordion, initCases, goToPanel('panel-main'), loadToolStatus×2, auto-select-first-case setTimeout) → moves to `main.js`.
- `session.js` content (lines 1–32: session-ID IIFE + `window.fetch` monkeypatch injecting `X-CK-Session`) **must evaluate before any fetch** → first import in `main.js`.
- Five bare shared globals (`currentSession`, `currentKey`, `currentStep`, `currentPanel`, `ptCase`, ~143 use sites) are assigned from multiple future modules; ESM imported bindings are read-only → they move into a shared `S` state object.
- Explicit `window.*` bus (`window.currentTestLink/currentZephyr/currentATP/currentCaseTitle/lastLLMConfig`) **stays on `window` this pass** (documented debt) — every use is already `window.`-prefixed, so no rename is forced; migrating later is a trivial sed.
- Section-local state (`_editingObjective`, `_editingSteps`, `ckBrokerRunning`, `ptSession`, `ptCaseInfo`, `ptRunPoll`, `ptProfiles`) never crosses sections → stays module-private, zero renames.
- Strict-mode audit already done: no undeclared-variable assignments found.
- `type="module"` is deferred by default, so end-of-body DOM assumptions still hold.
- nav↔generator and nav↔pytest imports are circular but safe: all cross-module calls happen inside functions after graph evaluation; only `main.js` (and leaf `registerActions` calls) run imported code at top level.
- Legacy `ask-ck/CK-main/index.html` (root, 709 lines) is an unrelated standalone prototype — **do not touch**.

## Module layout (new `static/js/`, cut verbatim by line range from app.js)

| File | app.js lines | Contents |
|---|---|---|
| `js/session.js` | 1–32 | Session-ID + fetch patch (side-effect module); add `export { CK_SESSION_ID }` (used by agent.js) |
| `js/state.js` | 34–39 rewritten | `export const S = { currentSession: null, currentKey: null, currentStep: 0, currentPanel: 'step-0', ptCase: {...} }`; header comment documents the `window.*` bus debt |
| `js/dom-helpers.js` | 364–383 | `escapeHtml`, `truncateText`, `dataArgs` |
| `js/actions.js` | 2614–2621, 2631–2650 rewritten | Registry (`registerActions`) + delegated click dispatcher (`registry.get(...)` instead of `window[...]`, keep `fn.apply(el, args)` so `this === element`) + role=button keydown. Imports nothing from tools — no cycles |
| `js/tables.js` | 187–363 | `DESC_SOFT_MAX`, `renderTestLinkTable/ZephyrTable/ATPTable`, `folderLeaf`, `splitAtpTitleDescription` (shared by generator + db-search) |
| `js/generator.js` | 41–186, 384–703, 988–1181 | loadCase, updateUI, objective/steps render+edit, confirmStep, synthesize*, exportBundle, clearCurrentSession |
| `js/llm.js` | 704–766, 865–987 | setLLMConfig, normalizeLLMConfig, updateLLMStatus/Defaults, updateAuthMethodUI, restoreLLMUI |
| `js/agent.js` | 767–864 | CK_AGENT_URL, probeLocalAgent, ckBrokerLoop, checkLocalAgent, checkGrokCLIStatus |
| `js/cases.js` | 1182–1350 | Case-select plumbing shared by Generator & PyTest (fillCaseSelect … initCases, getActiveCaseKey) |
| `js/nav.js` | 1351–1407, 1433–1544 (**excluding boot block 1408–1431**) | Sidebar accordion, goToPanel, goToStep, updatePageHeader |
| `js/pytest.js` | 1545–2241 | Entire PyTest Creator (~45 `pt*` functions, private state) |
| `js/db-search.js` | 2255–2575 | merge*Candidates + search*/suggest*WithLLM for TestLink/Zephyr/ATP |
| `js/theme.js` | 2576–2613 | Theme IIFE verbatim (side-effect module) |
| `js/main.js` | 1408–1431, 2242–2254, 2653–2663 | Entry point: ordered imports (`session.js` first, then theme, actions, rest), `loadToolStatus`, boot block, form-control bindings |

`app.js` is deleted at the end of the split commit.

### Registry sketch

```js
// js/actions.js
const registry = new Map();
export function registerActions(map) {
  for (const [name, fn] of Object.entries(map)) {
    if (registry.has(name)) console.warn('duplicate data-action registration:', name);
    registry.set(name, fn);
  }
}
// dispatcher: fn = registry.get(el.dataset.action); warn if unknown; fn.apply(el, args)
```

Each tool module self-registers its own actions at the bottom of the file. Ownership of the 52 names: generator 15, pytest 26, db-search 6, nav 2 (`goToPanel`, `goToStep`), agent 2 (`checkLocalAgent`, `checkGrokCLIStatus`), llm 1 (`setLLMConfig`).

Rebuild the list mechanically before and after:
```
grep -ho 'data-action="[a-zA-Z_$][a-zA-Z0-9_$]*"' index.html app.js | sort -u
```
(52 names; exclude the doc-comment placeholder `fnName` at app.js:2625.) After the split, re-run against `index.html js/*.js` and diff against the union of `registerActions` keys.

## Commit staging

**Commit 1 — action registry inside the still-classic `app.js` (de-risks the contract).**
1. Build the 52-name list via the grep.
2. Add `CK_ACTIONS` + `registerActions` near the top of app.js; change dispatcher line 2634 to `CK_ACTIONS[el.dataset.action] || window[el.dataset.action]` (fallback keeps missed names working while the warn identifies them); register all 52 at the bottom.
3. Run the manual checklist; fix any `unknown data-action` warnings here.

**Commit 2 — the atomic module split.**
1. Create `static/js/` per the table: cut line ranges verbatim, add imports/exports + per-module `registerActions`; drop the `window` fallback in the dispatcher.
2. State rename in moved code only: word-boundary sed of the five bare globals → `S.` prefix (~143 sites), then eyeball the diff (template-literal hits like `` ${currentKey} `` → `${S.currentKey}` are correct).
3. `index.html` line 691: `<script src="/static/app.js">` → `<script type="module" src="/static/js/main.js?v=1">`. Delete `app.js`.
4. Syntax gate: `for f in js/*.js; do cp "$f" /tmp/ck-check.mjs && node --check /tmp/ck-check.mjs; done`.
5. Duplicate-name check: `grep -h '^async function\|^function' js/*.js | sort | uniq -d` (must be empty).
6. Full manual checklist with devtools console open — any strict-mode/TDZ issue surfaces as a loud ReferenceError/TypeError.

**Commit 3 — cleanup (small).** Short `static/js/README.md` documenting: the `window.current*`/`lastLLMConfig` bus as known debt, the rule "no top-level cross-module calls outside main.js / registerActions", and the `?v=` bump convention.

**Cache-busting:** FastAPI StaticFiles sends ETag but no Cache-Control; bump `?v=N` on the main.js tag when shipping and announce one hard refresh. (Optional later: `Cache-Control: no-cache` middleware for `/static/js/*` — not this pass.) No `main.py` changes required otherwise.

## Risks

- **Missed action name → dead button.** Covered by: grep includes template literals; commit-1 fallback surfaces misses non-fatally; dispatcher warns forever.
- **Circular imports (nav↔generator/pytest).** Safe because cross-calls are function-body-only; fallback if ever needed: panel-renderer registry in nav.js.
- **sed collateral on the `S.` rename.** Scoped to moved chunks + diff review.
- **Stale cache serving old index+app pair.** app.js deleted → stale index 404s its script loudly; `?v=` + hard refresh.

## Verification (manual — per user preference, no Playwright)

Run after commit 1 AND commit 2, devtools console + network open throughout; **zero new console errors/warnings is part of the pass criteria**:

1. **Session header:** every `/api/...` request carries `X-CK-Session`; agent-broker requests to `127.0.0.1:8765` do not.
2. **Theme toggle** flips and persists across reload.
3. **Sidebar nav:** each accordion section expands/collapses; every panel reachable; exactly one visible; page header updates.
4. **Generator full flow:** load case → tables render → confirm steps 1–3 → review summary → synthesize objectives → edit/save/confirm → synthesize steps → edit (add/remove/apply/cancel) → export bundle → clear session.
5. **Keyboard:** Enter and Space activate `role="button"` nav items.
6. **DB search tools ×3:** manual search + LLM suggest; merged rows appear; buttons on runtime-injected rows still dispatch.
7. **LLM config/status:** auth-method radios react; setLLMConfig; status/defaults update; reload restores UI.
8. **Agent bridge:** check-local-agent messaging in both stopped/running states; broker long-poll visible in Network when active.
9. **PyTest Creator, all panels:** cases → sequence (add/remove rows) → search (Enter key in `#pt-search-q`) → fit (decision change fires) → fragments → generate/lint/fix/save → run (profile change fires, poll updates) → validate → testbox profiles (edit/check/delete via injected row buttons).
10. **Cross-tool case selects** stay in sync; auto-select of first open case fires ~200 ms after load.
11. **Dispatcher hygiene:** no `unknown data-action` warnings after the full pass.

## Critical files

- `ask-ck/CK-main/CK_server/static/app.js` — source of every extraction (dispatcher 2631–2650, boot block 1408–1431)
- `ask-ck/CK-main/CK_server/static/index.html` — line 691 script tag; 39 static data-action names
- `ask-ck/CK-main/CK_server/static/js/actions.js` (new) — registry + dispatcher, the contract keystone
- `ask-ck/CK-main/CK_server/static/js/main.js` (new) — import order, boot block, form bindings
- `ask-ck/CK-main/CK_server/static/js/state.js` (new) — shared `S` object replacing the five bare globals

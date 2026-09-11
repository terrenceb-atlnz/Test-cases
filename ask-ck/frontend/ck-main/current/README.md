# `ask-ck/frontend/ck-main/current/` — the current Ask CK front-end

**Layout (2026-09-11):** `index.html`, `styles.css` and the assets sit here; the ES modules are
sorted into **page directories** — `generator/`, `pytest-creator/`, `llm-config/`, `admin/` — plus
`shared/` for modules more than one page imports. The server mounts this directory at `/static`.
The Svelte rewrite lives beside it at `../svelte/`.

The Ask CK frontend used to be one 2663-line classic script (`static/app.js`).
It is now browser-native ES modules — **no bundler, no build step, no
package.json**. `index.html` loads a single entry point:

```html
<script type="module" src="/static/shared/main.js?v=1"></script>
```

`type="module"` is deferred by default, so end-of-body DOM is ready when the
graph evaluates.

## Module map

| Dir | File | Responsibility |
|-----|------|----------------|
| `shared/` | `main.js` | Entry point: ordered imports, `loadToolStatus`, boot block, form-control bindings |
| `shared/` | `session.js` | Per-tab session id + `window.fetch` monkeypatch injecting `X-CK-Session` / `X-CK-Panel` (side-effect) |
| `shared/` | `state.js` | Shared mutable `S` state object (see below) |
| `shared/` | `actions.js` | Action registry (`registerActions`) + delegated click/keydown dispatch |
| `shared/` | `dom-helpers.js` | `escapeHtml`, `truncateText`, `dataArgs`, `showStatus` (in-page `.status-banner` helper), `setButtonBusy`/`flashButtonDone` (LLM-button press/spinner/disable + ✓/✗ feedback) |
| `generator/` | `tables.js` | Candidate-table renderers shared by Generator + DB-search |
| `generator/` | `generator.js` | Objective / Test Case Generator wizard |
| `llm-config/` | `llm.js` | LLM Configure panel + status |
| `llm-config/` | `agent.js` | Local ck-agent bridge (broker long-poll, CLI status probes) |
| `shared/` | `cases.js` | Case-select plumbing shared by Generator + PyTest Creator |
| `shared/` | `nav.js` | Sidebar accordion + panel/step navigation |
| `pytest-creator/` | `pytest.js` | PyTest Creator (7 visible steps; internal session keys still `step2`–`step8` — see `_step_label` / PLAN-pytest-creator.md 2026-07-23 flow revision) |
| `shared/` | `session-restore.js` | Refresh-safe UI state (sessionStorage, per tab): remembers active panel + each tool's loaded case so F5 doesn't dump the user at panel-main; `main.js` captures the snapshot BEFORE the boot default panel overwrites it |
| `generator/` | `db-search.js` | merge + manual-search + LLM-suggest for TestLink/Zephyr/ATP |
| `shared/` | `llm-progress.js` | Live LLM-button state: elapsed / ~typical / streamed counters polled from `/api/llm/inflight/{id}`, the 2px fill bar, and click-to-STOP (true server-side cancel via `/api/llm/cancel/{id}` — routed in actions.js before data-action so a busy button can't re-fire itself) |
| `shared/` | `llm-debug.js` | LLM observability: per-panel "last LLM request" footer + token badges (`/api/llm/recent`) |
| `admin/` | `admin.js` | Hidden admin panel (double-click CK's face): reset sessions, restart server (`/api/admin/*`). (DB/embeddings rebuild was removed once `ck.db` became the permanent committed source of truth.) |
| `shared/` | `theme.js` | Light/dark toggle (side-effect) |

## Conventions

**1. UI wiring goes through the action registry — not `window`.**
Buttons declare `data-action="handlerName"` (and optional `data-args='[...]'`).
Each tool module registers its own handlers at the bottom of the file:

```js
import { registerActions } from './actions.js';
registerActions({ loadCase, confirmStep, /* ... */ });
```

The delegated dispatcher in `actions.js` resolves the name from the registry and
calls `fn.apply(el, args)` (so `this === the clicked element`). Adding a button
means adding its handler to the owning module's `registerActions({...})` call —
nothing touches `window`. An unknown name logs
`data-action refers to unknown function:` and is otherwise a no-op.

To audit the contract, the registered keys must equal the `data-action` names in
markup + runtime templates:

```sh
grep -ho 'data-action="[a-zA-Z_$][a-zA-Z0-9_$]*"' index.html */*.js | sort -u
```

**2. No top-level cross-module calls outside `main.js` (and `registerActions`).**
Modules may `import` freely, but must only *call* imported functions from inside
their own functions — never at module top level. This keeps the (intentional,
safe) `nav ↔ generator` / `nav ↔ pytest` import cycles from blowing up during
graph evaluation: by the time any handler runs, the whole graph is loaded.
`main.js` is the one place that runs imported code at top level (the boot block),
and it imports `session.js` **first** so the fetch patch is installed before any
other module can fire a request.

**3. Shared state lives in `S` (`state.js`), not bare globals.**
ESM imported bindings are read-only, so the five values that multiple modules
write (`currentSession`, `currentKey`, `currentStep`, `currentPanel`, `ptCase`)
are properties of the exported `S` object: read/write `S.currentKey`, etc.
Section-local state (e.g. `_editingObjective`, `ptSession`, `ptProfiles`) stays
module-private.

**4. Cache-busting: bump `?v=N` on the `main.js` tag when shipping.**
FastAPI `StaticFiles` sends `ETag` but no `Cache-Control`, so browsers may serve
a stale module. On a shipped change, bump the `?v=` query on the `<script>` tag
in `index.html` and tell users to hard-refresh once. `main.py` also sends
`Cache-Control: no-cache` for every `/static/**/*.js`, so child modules revalidate on each load.

## Known debt

- **`window.*` bus.** A second cross-module channel still lives on `window`:
  `window.currentTestLink`, `currentZephyr`, `currentATP`, `currentCaseTitle`,
  `lastLLMConfig`. Every use is already `window.`-prefixed, so migrating these
  into `S` (or a dedicated module) later is a mechanical rename. Left as-is this
  pass to keep the split behavior-preserving.

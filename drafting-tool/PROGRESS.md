# PROGRESS.md — Drafting Tool (Server-Backed)

**Purpose**: This file exists so future Grok sessions can quickly understand exactly where we are, what has been built, what the priorities are, and how to continue seamlessly.

**Last Updated**: 2026-07-03 (by Grok)
**Current Session Theme**: 
- Removal of all MOCK/demo fallbacks and hardcodes for real-only usage (CLI subscription modes or API keys required; no silent demo data or pre-fills).
- Output generation advanced: `/export` now writes drop-in artifacts directly to `refined-cases/<Group>/AWPTCM-Txxxx/` (traceability.md + zephyr_payload.json + session; folders created as needed) using improved group resolution matching existing structure, in addition to client downloads. Validation and server note construction reinforced.
- Frontend polish: removed multiple inline styles (switched to .hidden class + utility classes for visibility, panels, buttons); enhanced review summary for richer previews (more items, justifications, counts); improved post-synthesis editor with better classes; generalized remaining demo pre-select logic and comments/strings.
- Cross-references and handoff updates.

MOCK and demo pre-fills fully removed from code. Output persistence addresses key drop-in requirement. Frontend closer to design components.

---

## 1. High-Level Status

| Area                        | Status          | Notes |
|----------------------------|------------------|-------|
| Architecture Decision      | Complete        | Server-backed (FastAPI) chosen over single-file |
| Project Structure          | Good            | All new work consolidated under `drafting-tool/` |
| Core Backend               | State Machine + Persistence + Data/LLM Assist | FastAPI + routers with gating, file-based JSON sessions, suggest_atp endpoint, _build_atp_query + candidate retrieval |
| LLM Integration            | Subscription CLI modes primary + real-only | Multi-provider via local CLIs for subscriptions (Grok CLI for SuperGrok/X Premium+ and Claude Code CLI for Team) — UI is now *only* the two subscription radios (no provider dropdown, no API Key option visible). Full backend + CLI integration; MOCK/demo fallbacks removed entirely (real credentials or logged-in CLI required). Legacy api_key supported server-side for old. Provenance, suggest_atp.jinja. |
| Data Integration for Steps 1-3 | Implemented     | Real TestLink candidates from candidates.json, Zephyr refs from zephyr_master/slim (external only), ATP from test_id_desc with LLM pre-select/analysis |
| Repeatable Outputs         | Advanced (key parts complete) | Jinja templates + structured parsing + server note; human-readable in Step 4; export now persists drop-in to refined-cases/<Group>/ (traceability.md, zephyr_payload.json); validation reinforced |
| Process Enforcement        | Implemented     | Server-side gates for confirms (selections+flags persisted); synthesis blocked until all 3 |
| Frontend UI                | Data-driven + Polished | Sidebar+main, dynamic case list (real AWPTCM cases, no T33234 auto/demo), compact tables for 1-3 (external Zephyr only), real data only (no pre-fills), human-readable synth output, LLM suggest, restoration, review summary, reduced inline styles (class-based) |
| Documentation              | Strong          | PROGRESS/LESSONS/SERVER-README updated; synced with root SESSION_STATE/README |
| Hosting / nginx            | Ready           | Example config provided |
| Real LLM Wiring            | Complete        | Grok/Claude via env or per-session config (real-only, no MOCK); CLI headless primary |
| Persistence                | File-based      | JSON per session (confirms, selections, LLM config+creds, provenance, step4); export also writes to refined-cases |
| Polish & Completeness      | Advanced        | UI compaction done; output persistence + frontend polish (previews, editor, styles, no demo) progressed; more needed |

**Overall Phase**: Foundation / Early Implementation

---

## 2. Key Decisions & Rationale (Carry Forward)

- **Server-backed is required** because:
  - LLM must directly generate Objectives and Steps from user selections.
  - Data volume will keep growing.
  - Tool will be hosted (local IP + nginx).
  - Future extensibility is expected.

- **Repeatability strategy**: 
  - Prompt templates (Jinja) for consistent inputs to the LLM.
  - Structured parsing + output templates for consistent artifacts (even if LLM output varies).

- **Process gates must be real**: User must explicitly confirm review of TestLink, Zephyr, and ATPyLib **before** synthesis is allowed. This should be enforced server-side.

- **File organization**: Everything related to this tool (code, docs, plan, examples) should stay under `drafting-tool/`.

---

## 3. Current File Structure (drafting-tool/)

```
drafting-tool/
├── PROGRESS.md                      ← You are here (handoff file)
├── SERVER-README.md                 ← Primary instructions & usage
├── PLAN-server-backed.md            ← The approved full plan
├── LESSONS_LEARNED.md               ← Captured insights from this session
├── README.md                        ← High-level overview
├── nginx-drafting-server.conf.example
├── drafting_server/                 ← The actual application
│   ├── main.py
│   ├── data.py
│   ├── llm.py
│   ├── models.py
│   ├── routers/
│   │   └── wizard.py
│   ├── static/
│   │   └── index.html
│   ├── templates/
│   │   ├── prompts/
│   │   │   ├── generate_objectives.jinja
│   │   │   └── generate_steps.jinja
│   │   └── outputs/
│   │       └── traceability.md.jinja
│   ├── sessions/                    ← file persistence
│   └── README.md
└── (legacy + design files: showcase.html, design-tokens.css, etc.)
```

---

## 4. What Is Currently Implemented (Working)

- Data loading from the three databases (`data.py`): zephyr_master, candidates (with dict), decisions, slim_index, test_id_desc. Enhanced for review steps.
- Zephyr Step 2: `load_case` now strictly omits any Zephyr case whose key is in the "current Cases list" (or is the primary key itself). `zrefs` contains *only* external related cases (filtered + on-demand full steps enrichment for those). Primary case's own Zephyr data is still included in traceability notes via server-side `build_traceability_note`.
- LLM layer with:
  - Jinja2 prompt templates (generate_objectives, generate_steps, suggest_atp)
  - Multi-provider support via **local CLI subscription modes** (primary path):
    - `grok_cli`: local `grok` CLI after `grok login --oauth` (SuperGrok/X Premium+). Uses `--prompt-file`, `--output-format plain`, `--no-memory --no-plan`.
    - `claude_code`: local `claude` CLI (`claude -p --output-format json`).
  - Full `check_*_cli()`, `_call_*_cli_headless()`, status endpoints, and integration in `synthesize_*`, `suggest_*`, `analyze_*`.
  - Real end-to-end testing of Grok subscription path performed (CLI detection, direct calls, full synthesize).
  - Legacy `api_key` still supported in backend/models for old sessions or direct use; **completely removed from current UI** (no radio, no credential field, no dropdown).
  - Provider selection is now implicit in the chosen radio (no separate dropdown).
  - Full prompt/response + provenance capture (auth_method recorded correctly).
  - Improved parsing for real LLM (preamble stripping). No MOCK.
  - suggest_relevant_atp for Step 3.
- Backend with:
  - Proper step gating/state machine (`routers/wizard.py`): confirm_step stores selections+confirmed flags+timestamps; synthesize enforces all 3 confirms server-side using authoritative session state
  - File-based persistence (`sessions/<key>.json`): full WizardSession including step states, LLM config (provider/auth_method/creds), step4, provenance
  - set_llm_config endpoint for login flows (api_key, claude_code, or grok_cli; rejects claude_code for non-Claude and grok_cli for non-Grok providers); new GET /claude_cli_status and GET /grok_cli_status endpoints
  - load_case returns enriched data (testlink_candidates, zephyr_refs) + restores from disk
  - /cases endpoint for dynamic list (neutral sort, no T33234 priority)
  - /search_atp and /suggest_atp/{key} for Step 3 (LLM-assisted pre-selection)
  - _build_atp_query and _get_atp_candidates helpers
- Frontend (`static/index.html`):
  - Restructured to design guidelines: .layout .sidebar (full top, 240px) + .main; .sidebar-logo, .sidebar-section-label, .sidebar-nav-item (with gray SVGs); no outer top header bar
  - Dynamic case selector populated from real data (AWPTCM-Txxxx; neutral, no auto/demo pre-select)
  - LLM section in Step 0: **only two radio options** for subscription CLIs — "Grok CLI (SuperGrok / X Premium+ subscription)" (default) and "Claude Code CLI (Team subscription)". No provider dropdown. No "API Key (developer)" option. Credential field removed. "Check ... CLI" buttons + contextual instructions panels. Model input remains. Provider/auth_method derived from selected radio in JS.
  - Vertical steps nav with active states; dynamic .page-header updates per view
  - Step content uses .card + .section/.section-heading/.section-description
  - Buttons use .btn .btn-primary/.btn-secondary
  - Compact tables (.table-container + .table styles...): real selectable TestLink (1), Zephyr cross-refs (2 — *only external cases*; current Cases list and the primary case itself are omitted), ATP (3) with search + Suggest
  - Real data only (no pre-fills); review summary with richer previews (items + justifications)
  - Badges for confirmed states
  - Form elements use .form-*
  - Light/dark via .light class + design tokens
  - Human-readable synthesized output in Step 4
  - Case selection, step navigation, confirms, synthesize, export
- Output templating + direct FS persistence (`traceability.md.jinja` + export writes to refined-cases/<Group>/AWPTCM-Txxxx/); human-readable + editable in Step 4; validation implemented
- Custom scrollbar for sidebar (thin with border effect)
- nginx example + run instructions documented
- Session persistence now includes LLM config + full provenance for audit/repeatability
- Real-only flow (post MOCK removal): load any case → review real data in 1-3 (LLM suggest/analysis) → confirm gates → synthesize (real LLM or error) → human-readable/editable Step 4 → export (downloads + auto-persist to refined-cases/<Group>/)

---

## 5. What Is Not Yet Implemented (Priorities)

From the approved plan + implementation gaps:

### High Priority (Next Session Focus)
**Critical (start here first thing next session)**:
- **Bug: NameError: name 'f' is not defined in load_case (routers/wizard.py:241)** when building zrefs for certain cases (e.g. AWPTCM-T44210). Caused 500 Internal Server Error on POST /api/wizard/load_case/AWPTCM-T44210. Full traceback logged in session. Must be verified/fixed first.

1. **Complete output generation** (llm + routers + export)
   - Full correct `zephyr_payload.json` (incl. proper first traceability note step using selected items)
   - Validation against expected schema
   - Consistent use of output templates

2. **Frontend polish + remaining enhancements**
   - Dynamic case list from server
   - Richer previews of selections
   - Better post-synthesis editor
   - Visual confirmed states + review summary panel (use badges etc.)
   - Full use of design components (more .btn variants, badges, form polish, no remaining inline where possible)

### Medium Priority
- Serve and enhance Process Reference page with full markdown + deep links (S-M)
- Add server-side indexing for full zephyr_cases.jsonl + suites (M)
- Create `requirements.txt` + simple setup / Docker (S)
- Improve error handling, loading states, UX (M)
- Full design component integration (e.g. more subsections, consistent forms)

### Lower / Future
- Authentication / multi-user (L)
- Advanced LLM features (L)
- Full test suite + CI (M)
- One-command setup (S-M)

---

## 6. How to Resume Work (For Future Grok Sessions)

1. **Start here**: Read this `PROGRESS.md` first.
2. Read `SERVER-README.md` for how to run and use the current tool.
3. Read `PLAN-server-backed.md` if you need the full original design and trade-off reasoning.
4. Run the server (recommended):
   ```bash
   ./drafting-tool/run.sh
   ```
   Or with options:
   ```bash
   LLM_API_KEY=sk-... ./drafting-tool/run.sh
   PORT=9000 ./drafting-tool/run.sh
   ```
5. Manual alternative (from project root):
   ```bash
   LLM_API_KEY=MOCK PYTHONPATH=drafting-tool python3 -m uvicorn drafting_server.main:app --host 0.0.0.0 --port 8000 --reload
   ```

**Recommended first actions in a new session**:
- Read this PROGRESS.md + SERVER-README.md fully.
- Pick next high-priority (frontend polish: previews, editor, styles, ATP merge; validate real logins).
- Test current flows with real setup: use `LLM_API_KEY=sk-...` or (preferred) logged-in `grok` / `claude` CLI; load case (real data, no auto/demo), review/confirm 1-3 (use Suggest with LLM), view/edit human-readable in Step 4.
- Verify compact tables fit on one page, no side scroll.
- Test Step 2 Zephyr table: it should contain *only* external cross-refs (no AWPTCM cases that have TestLink candidates, and no entry for the case itself).
- LLM UI: only two radios (Grok CLI subscription default + Claude Code CLI). No dropdown. No API Key option. Use "Check Grok CLI" / "Check Claude CLI" + Apply. Model optional. Export now also saves server-side to refined-cases.
- If touching auth: both paths shell out to local CLI after its own `grok login --oauth` or `claude /login`. Status endpoints available. Legacy api_key still works server-side for old sessions.
- Verify export persists to correct refined-cases/<Group>/ (creates folders).
- Update this PROGRESS.md at end (status, backlog, lessons).
- Keep SERVER-README + LESSONS_LEARNED current.

---

## 9. Technical Debt & Known Issues

### Technical Debt
- **Bug logged (high priority for next)**: NameError 'f' in load_case zrefs (discovered via 500 on AWPTCM-T44210). Fixed by restoring folder assignment, but must be first task next session to verify with real cases.
- **Output generation**: Direct persistence to refined-cases added (drop-in); full edge validation and artifact fidelity can be hardened further.
- **Hardcoded paths / module imports**: Still some assumptions; ensure BASE_DIR consistently (progress made).
- **No full validation layer**: Outputs templated + validated on export; can be stricter pre-write.
- **Frontend polish remaining**: Some inline styles linger in dynamic JS (status results); rich previews enhanced, editor improved, review summary added, inline reduced via classes. Continue design component adoption.
- **LLM parsing improved but**: Regex+JSON fallback + preamble stripping for real LLM; could add more robust Pydantic/instructor for production.
- **Missing full data loading**: Only lightweight; full zephyr_cases.jsonl + suites not streamed/indexed (search limited).
- **No automated tests**: Zero for server, templates, API, UI flows.
- **No requirements.txt / Docker**: Still assumed via --user.
- **Audit trail**: Provenance now captured in persisted sessions + export; no separate logging yet.
- **Demo-specific code**: Largely removed (MOCK fallbacks, T33234 pre-fills/auto, demo filters); remaining docstring/comments to clean.
- **Headless subscription CLI paths (claude_code + grok_cli) should be validated against real logins**: Grok path exercised; full UI + real subscription smoke test recommended. Claude previously via fake.
- **Grok CLI is agent/build-oriented**: It can prepend "thinking" / project-check text even with flags. Output usable but preamble stripping added.
- **Headless mode has no deployment guard**: Intended for per-user local hosting; shared instances would pool logins (documented in SERVER-README).

### Known Issues / Limitations (Current)
- Server requires running from project root for paths/imports (improved with persistence but still).
- UI elements (esp. dynamic tables from backend) may need class="table" etc. for full styling.
- LLM config per-session works; real credentials/CLI required (no fallback).
- No handling for edge "None" selections fully stress-tested.
- /process page basic (enhanced rendering added; more interactive features pending).
- Dependencies no requirements.txt/pyproject yet.
- nginx prefix handling needed if not root.
- Sidebar fixed positioning requires header height awareness (top:60px + main padding).
- Tables compact but long titles can still wrap; no truncation yet.
- Real CLI validation (Grok/Claude logins) recommended for full confidence.

---

## 10. Prioritized Backlog with Rough Effort Estimates

Estimates are in "sessions" (assuming a typical Grok coding session of focused work). S = Small, M = Medium, L = Large effort.

### High Priority (Do These First)
1. **Complete output generation** - M effort (progress this session)
   - Export now writes drop-in to refined-cases/<Group>/ (traceability.md, zephyr_payload.json; folders auto-created via group matching).
   - Validation against schema + server note construction done.
   - Consistent templates used. (Persistence + real-only done; full polish/edge cases may remain.)

2. **Frontend remaining polish + enhancements** - M effort (1-2 sessions; in progress)
   - Richer previews of selections (review summary enhanced).
   - Better post-synthesis editor (classes improved).
   - Visual confirmed states + review summary panel (badges + richer).
   - Full use of design components; remove remaining inline styles (multiple removed, .hidden + utils added).
   - Improve ATP search results merging with LLM suggestions (pre-compute on load; further client merge possible).

3. **Generalize demo pre-fills and flows** - S effort (largely complete)
   - MOCK/demo fallbacks + T33234 hardcodes/pre-fills/auto-load removed from code.
   - Real data only; neutral flows.
   - (Clean remaining comments/docs if needed.)

### Medium Priority
- Serve and enhance Process Reference page with full markdown + deep links to wizard steps (S-M).
- Add server-side indexing for full zephyr_cases.jsonl and test suites (M).
- Create `requirements.txt` + simple setup script / Docker (S).
- Improve error handling, loading states, and UX polish (M).
- Make human-readable Step 4 output editable before export.
- **Validate Claude Code headless auth against a real Team-subscription login** (S effort, 0.25 session) - so far only exercised via a scripted fake CLI. Install/log in a real `claude` CLI on a test machine, run Step 3 suggest + Step 4 synthesize, confirm provenance and error messages (e.g. session expiry) look right in practice.
- **Validate Grok CLI subscription path end-to-end against a real SuperGrok/X Premium+ login** (S effort, 0.25 session) - backend + direct CLI calls fully tested this session; full UI flow (radio + check + apply + synthesize) should be exercised with a real logged-in `grok` CLI.
- (Completed this session) UI for Grok CLI + removal of provider dropdown + complete removal of visible API Key option.

### Lower / Future
- Authentication / multi-user (L)
- Advanced LLM features: critique loop, few-shot from past cases, versioned prompts (L)
- Full test suite + CI (M)
- One-command local setup with nginx (S-M)

**Suggested Order for Next Session**:
1. Frontend remaining polish (previews, editor, design components, remove inlines, ATP merge) — current focus.
2. Polish human-readable Step 4 + make output editable (if not covered)
3. Requirements + setup improvements, error handling, full tests.
4. Validate real CLI logins end-to-end (Grok + Claude on machines with logins).
5. Serve/enhance Process Reference page (interactive, deep links).
6. (Lower) advanced LLM, auth, etc.

---

## 11. Cross-References to Higher-Level Project Docs

This drafting tool work is part of the larger Test-cases project. All drafting-tool-specific state, backlog, lessons, and handoff notes are consolidated under the `drafting-tool/` directory.

**Higher-level references**:
- Root `README.md` — Project framing (synced with latest UI simplification, Grok CLI completion, Zephyr Step 2 omission).
- Root `SESSION_STATE.md` — Overall history (detailed entry appended for this session).
- `OBJECTIVE_DRAFTING_PROCESS.md` — Source of truth for the repeatable workflow (tool implements it; process itself unchanged).
- External `AGENTS.md` (referenced from root README) — Consult for local environment details, CLI installation, and `grok login` / `claude /login` commands.

**How this component ties in**:
- The server tool is the implementation vehicle for synthesis (and the full repeatable workflow) of `OBJECTIVE_DRAFTING_PROCESS.md`.
- It consumes the same data artifacts.
- Outputs feed into `refined-cases/`.

**Discovery recommendation for future sessions**:
- Always start by reading `drafting-tool/PROGRESS.md` + `SERVER-README.md` + `LESSONS_LEARNED.md`.
- Then root `SESSION_STATE.md` + `README.md`.
- Re-read `OBJECTIVE_DRAFTING_PROCESS.md` for process rules.
- Inspect current UI (only two subscription CLI radios, no dropdown/API key) + `llm.py` + `routers/wizard.py` (real-only, no MOCK).
- Run with real setup (LLM_API_KEY or grok/claude CLI login), verify Step 2 Zephyr omits current cases, exercise the radios + Check CLI buttons + export (persists to refined-cases).
- Inspect `static/index.html` + `llm.py` + `routers/wizard.py` + `suggest_atp.jinja` for current flows (real data tables for 1-3, LLM suggest/analysis in 3, compact UI, human-readable/editable Step 4, review summary, reduced inlines).
- Verify tables are compact (fit one page, no side scroll); real flows only (no demo pre-fills).

---

## 12. Session Handoff Checklist (Expanded)

When starting a new session:
- [ ] Read `drafting-tool/PROGRESS.md` (this file) completely.
- [ ] Read `drafting-tool/SERVER-README.md`.
- [ ] Skim latest in root `SESSION_STATE.md`.
- [ ] Re-read root `README.md`, `OBJECTIVE_DRAFTING_PROCESS.md`.
- [ ] Check `drafting-tool/drafting_server/` (ls, run server with real LLM_API_KEY or CLI login).
- [ ] Test current real flow: load case (neutral data) → review/confirm 1-3 (LLM suggest) → gates → synthesize (real) → edit Step 4 → export (check downloads + auto-persist to refined-cases/<Group>/AWPTCM-Txxxx/).
- [ ] Specifically load new cases (e.g. AWPTCM-T44210) to ensure no NameError in zrefs folder population (bug was fixed but verify first).
- [ ] Verify Step 2 Zephyr shows only external cases (no members of the current Cases list, and no primary case entry).
- [ ] Test LLM UI: only Grok CLI (default) + Claude Code CLI radios; Check buttons; no dropdown; no API Key visible. Export persists artifacts server-side.
- [ ] Test flows: gating (confirms block synth), persistence (restart survives), LLM subscription CLI modes (Grok + Claude; real only), provenance, dynamic case list, compact UI, review summary.
- [ ] Decide next from backlog (frontend polish).
- [ ] At end: Update `PROGRESS.md`, `SERVER-README.md`, `LESSONS_LEARNED.md`. Append to root `SESSION_STATE.md` if impact.

---

## 7. Important Context to Remember

- The **main goal** is not just to make a tool that works — it is to enforce a **repeatable process** and produce **repeatable outputs** using LLM as the synthesis engine, with strong user review gates.
- The original single-file version is now considered legacy/reference. New development should happen in `drafting_server/`.
- All documentation the user cares about should live in or be referenced from `drafting-tool/`.

---

## 8. Session Handoff Checklist (for the AI)

When starting a new session on this project, the AI should:

- [ ] Read `drafting-tool/PROGRESS.md` + `SERVER-README.md` + `LESSONS_LEARNED.md`
- [ ] Check `drafting-tool/drafting_server/` code + run server (real LLM_API_KEY or logged-in grok/claude CLI; no MOCK)
- [ ] Test flows: gating/persistence, LLM subscription modes (Grok CLI radio default + Claude Code CLI; Check status; no dropdown or API Key visible; real calls), Zephyr Step 2 omission behavior, sidebar nav, design UI (tokens, icons, layout, toggle, reduced inlines), review summary, export (persists to refined-cases)
- [ ] First: load several new cases (incl. AWPTCM-T44210) to confirm load_case succeeds (zrefs fix)
- [ ] Decide on next (frontend polish per updated backlog)
- [ ] At end: update PROGRESS + SERVER-README + LESSONS; append root SESSION_STATE if needed

---

**This file is the primary handoff document.**  
Keep it updated after every significant session. Future Grok instances will thank you.
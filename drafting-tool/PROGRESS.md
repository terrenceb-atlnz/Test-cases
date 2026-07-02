# PROGRESS.md — Drafting Tool (Server-Backed)

**Purpose**: This file exists so future Grok sessions can quickly understand exactly where we are, what has been built, what the priorities are, and how to continue seamlessly.

**Last Updated**: 2026-07-02 (by Grok, end of session)
**Current Session Theme**: Real data integration for Steps 1-3 (TestLink candidates + Zephyr refs + ATPyLib), LLM pre-selection for ATPyLib (suggest button + backend), dynamic case dropdown with demo pre-fills for T33234, UI compaction for one-page fit (reduced table padding, input widths, section/card margins), human-readable formatted output in Step 4 (objectives + steps list, removed "Action:" label), selection restoration on reload, auto-populate/search for demo.

---

## 1. High-Level Status

| Area                        | Status          | Notes |
|----------------------------|------------------|-------|
| Architecture Decision      | Complete        | Server-backed (FastAPI) chosen over single-file |
| Project Structure          | Good            | All new work consolidated under `drafting-tool/` |
| Core Backend               | State Machine + Persistence + Data/LLM Assist | FastAPI + routers with gating, file-based JSON sessions, suggest_atp endpoint, _build_atp_query + candidate retrieval |
| LLM Integration            | Functional (real) + Step 3 Assist | Multi-provider (Grok/Claude), auth modes, provenance, suggest_relevant_atp (MOCK + real), new suggest_atp.jinja template |
| Data Integration for Steps 1-3 | Implemented     | Real TestLink candidates from candidates.json, Zephyr refs from zephyr_master/slim, ATP from test_id_desc with LLM pre-select |
| Repeatable Outputs         | Partially Implemented | Jinja templates + structured parsing; human-readable render in Step 4; full zephyr_payload + export still pending |
| Process Enforcement        | Implemented     | Server-side gates for confirms (selections+flags persisted); synthesis blocked until all 3 |
| Frontend UI                | Data-driven + Compacted | Sidebar+main, dynamic case list (real AWPTCM cases, T33234 prioritized + auto-load), compact tables for 1-3 (small padding, narrow inputs), pre-filled selections for demo, human-readable synth output, LLM suggest button in Step 3, restoration of selections |
| Documentation              | Strong          | PROGRESS/LESSONS/SERVER-README updated; synced with root SESSION_STATE/README |
| Hosting / nginx            | Ready           | Example config provided |
| Real LLM Wiring            | Complete        | Grok/Claude via env or per-session config; MOCK fallback with rich pre-fills |
| Persistence                | File-based      | JSON per session (confirms, selections, LLM config+creds, provenance, step4) |
| Polish & Completeness      | Advanced        | UI compaction done for one-page fit; output gen + full polish (previews, editor) still needed |

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
- LLM layer with:
  - Jinja2 prompt templates (generate_objectives, generate_steps, suggest_atp)
  - Multi-provider support (Grok OpenAI-compatible + Claude native)
  - API key and account login modes (per-session config)
  - Full prompt/response + provenance capture returned and persisted
  - Improved parsing (JSON attempts + regex fallbacks)
  - MOCK mode for testing (with deterministic pre-fills for demo)
  - suggest_relevant_atp for Step 3 ATP pre-selection
- Backend with:
  - Proper step gating/state machine (`routers/wizard.py`): confirm_step stores selections+confirmed flags+timestamps; synthesize enforces all 3 confirms server-side using authoritative session state
  - File-based persistence (`sessions/<key>.json`): full WizardSession including step states, LLM config (provider/auth_method/creds), step4, provenance
  - set_llm_config endpoint for login flows
  - load_case returns enriched data (testlink_candidates, zephyr_refs) + restores from disk
  - /cases endpoint for dynamic list (prioritizes T33234)
  - /search_atp and /suggest_atp/{key} for Step 3 (LLM-assisted pre-selection)
  - _build_atp_query and _get_atp_candidates helpers
- Frontend (`static/index.html`):
  - Restructured to design guidelines: .layout .sidebar (full top, 240px) + .main; .sidebar-logo, .sidebar-section-label, .sidebar-nav-item (with gray SVGs); no outer top header bar
  - Dynamic case selector populated from real data (AWPTCM-Txxxx), T33234 at top + auto-load for mock demo
  - LLM status + "Configure" in sidebar; full config card (toggled in main) with API key vs Account, in-page instructions panel + explicit "Open Tab Now" (no popup race)
  - Vertical steps nav with active states; dynamic .page-header (.page-title + .page-description) updates per view
  - Step content uses .card + .section/.section-heading/.section-description
  - Buttons use .btn .btn-primary/.btn-secondary (plus legacy support)
  - Compact tables (.table-container + .table styles, reduced padding/fonts/widths for one-page fit): real selectable TestLink candidates (step 1), Zephyr refs (step 2) with checkboxes + editable justifications; ATPyLib results (step 3) with search + "Suggest with LLM (pre-select)" button
  - Pre-filled realistic selections for T33234 (auto-negotiation) across steps 1-3 on mock load
  - Badges (.badge-success) for confirmed states
  - Form elements use .form-input/.form-select/.form-textarea
  - Light/dark via .light class + design tokens
  - Human-readable synthesized output in Step 4 (renderSynthesized: formatted Objective + numbered Test Steps list; provenance in <details>)
  - Case selection, step navigation, confirms, synthesize, export
- Output templating started (`traceability.md.jinja`); human-readable display implemented
- Custom scrollbar for sidebar (thin with border effect)
- nginx example + run instructions documented
- Session persistence now includes LLM config + full provenance for audit/repeatability
- Demo flow: load T33234 → steps 1-3 pre-filled with real-ish data + LLM suggest → confirm → Step 4 human-readable

---

## 5. What Is Not Yet Implemented (Priorities)

From the approved plan + implementation gaps:

### High Priority (Next Session Focus)
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
4. Run the server:
   ```bash
   python -m uvicorn drafting_tool.drafting_server.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. For testing without real LLM keys:
   ```bash
   LLM_API_KEY=MOCK python -m uvicorn ...
   ```

**Recommended first actions in a new session**:
- Read this PROGRESS.md + SERVER-README.md fully.
- Pick next high-priority (output generation + Step 4 polish).
- Test current flows with MOCK: load AWPTCM-T33234 (auto-pre-filled), review/confirm steps 1-3 (use Suggest with LLM in Step 3), view human-readable in Step 4.
- Verify compact tables fit on one page, no side scroll.
- Update this PROGRESS.md at end (status, backlog, lessons).
- Keep SERVER-README + LESSONS_LEARNED current.

---

## 9. Technical Debt & Known Issues

### Technical Debt
- **Incomplete output generation**: zephyr_payload.json is partial (no full first traceability step or validation yet). Export still placeholder.
- **Hardcoded paths / module imports**: Still some assumptions; ensure BASE_DIR consistently (progress made).
- **No full validation layer**: Outputs templated but not strictly validated vs Zephyr schema before export.
- **Frontend polish remaining**: Some inline styles linger; rich previews of selections, post-synthesis editor, visual review summary pending. Demo pre-fills are hardcoded (not general).
- **LLM parsing improved but**: Regex+JSON fallback; could add more robust Pydantic/instructor for production.
- **Missing full data loading**: Only lightweight; full zephyr_cases.jsonl + suites not streamed/indexed (search limited).
- **No automated tests**: Zero for server, templates, API, UI flows.
- **No requirements.txt / Docker**: Still assumed via --user.
- **Audit trail**: Provenance now captured in persisted sessions, but no separate logging yet.
- **Demo-specific code**: Pre-filled selections + auto-search for T33234; ATP suggest results may need merging with live search.

### Known Issues / Limitations (Current)
- Server requires running from project root for paths/imports (improved with persistence but still).
- UI elements (esp. dynamic tables from backend) may need class="table" etc. for full styling.
- LLM config per-session works but MOCK fallback always available.
- No handling for edge "None" selections fully stress-tested.
- `zephyr_payload.json` export incomplete (focus on objective; full steps + traceability note pending).
- /process page still placeholder.
- Dependencies no requirements.txt/pyproject yet.
- nginx prefix handling needed if not root.
- Sidebar fixed positioning requires header height awareness (top:60px + main padding).
- For demo case T33234, ATP pre-fills use specific IDs that may not always match live search results exactly; user must review.
- Tables compact but long titles can still wrap; no truncation yet.

---

## 10. Prioritized Backlog with Rough Effort Estimates

Estimates are in "sessions" (assuming a typical Grok coding session of focused work). S = Small, M = Medium, L = Large effort.

### High Priority (Do These First)
1. **Complete output generation** - M effort (1 session)
   - Full correct `zephyr_payload.json` (including proper first traceability step using selected items + ATP).
   - Validation against expected schema.
   - Consistent use of output templates (traceability.md.jinja) in export.
   - Update export to produce drop-in refined-cases artifacts.

2. **Frontend remaining polish + enhancements** - M effort (1-2 sessions)
   - Richer previews of selections (show summary from prior steps).
   - Better post-synthesis editor (edit objective/steps before export).
   - Visual confirmed states + review summary panel (use badges etc.).
   - Full use of design components; remove remaining inline styles.
   - Improve ATP search results merging with LLM suggestions.

3. **Generalize demo pre-fills and flows** - S effort (0.5 session)
   - Remove/hide T33234-specific hardcodes for general use.
   - Better handling of Step 3 selections on reload (merge with search).

### Medium Priority
- Serve and enhance Process Reference page with full markdown + deep links to wizard steps (S-M).
- Add server-side indexing for full zephyr_cases.jsonl and test suites (M).
- Create `requirements.txt` + simple setup script / Docker (S).
- Improve error handling, loading states, and UX polish (M).
- Make human-readable Step 4 output editable before export.

### Lower / Future
- Authentication / multi-user (L)
- Advanced LLM features: critique loop, few-shot from past cases, versioned prompts (L)
- Full test suite + CI (M)
- One-command local setup with nginx (S-M)

**Suggested Order for Next Session**:
1. Complete output generation (full zephyr_payload + validation + proper export)
2. Polish human-readable Step 4 + make output editable
3. Frontend remaining polish (previews, editor, design components, generalize demo pre-fills)
4. Requirements + setup improvements, error handling, merge ATP suggestions better

---

## 11. Cross-References to Higher-Level Project Docs

This drafting tool work is part of the larger Test-cases project.

**Higher-level references you should check every session**:
- Root `README.md` — Project framing, data sources, current high-level status, links to `SESSION_STATE.md` and `AGENTS.md` (external).
- Root `SESSION_STATE.md` — Overall project history and session notes (this drafting work has an entry).
- `OBJECTIVE_DRAFTING_PROCESS.md` — The source of truth for the process this tool implements (always re-read the repeatable workflow and checklist sections).
- `data/suites/ENRICHMENT_STATE.md` — Status of the automated test data the tool relies on.
- External `../AGENTS.md` (mentioned in root README) — Broader context, access, and environment details for terrenceb-dl work.

**How this component ties in**:
- The server tool is the implementation vehicle for Step 4 (and the full repeatable workflow) of `OBJECTIVE_DRAFTING_PROCESS.md`.
- It consumes the same `data/`, `candidates.json`, `decisions/`, `zephyr_full/`, and `suites/` artifacts.
- Outputs feed directly into `refined-cases/` and `tool/upload_refined.py`.

**Discovery recommendation for future sessions**:
- Always start by reading `PROGRESS.md` (this) + `SERVER-README.md` + `LESSONS_LEARNED.md`.
- Then root `SESSION_STATE.md` + `README.md`.
- Re-read `OBJECTIVE_DRAFTING_PROCESS.md` for process rules.
- Inspect `static/index.html` + `llm.py` + `routers/wizard.py` + new `suggest_atp.jinja` for current flows (real data tables for 1-3, LLM suggest in 3, compact UI, human-readable Step 4 renderSynthesized).
- Run with MOCK (`LLM_API_KEY=MOCK`) — auto-loads T33234 with pre-filled selections for steps 1-3; use "Suggest with LLM" in Step 3; view formatted output in Step 4.
- Verify tables are compact (fit one page, no side scroll).

---

## 12. Session Handoff Checklist (Expanded)

When starting a new session:
- [ ] Read `drafting-tool/PROGRESS.md` (this file) completely.
- [ ] Read `drafting-tool/SERVER-README.md`.
- [ ] Skim latest in root `SESSION_STATE.md`.
- [ ] Re-read root `README.md`, `OBJECTIVE_DRAFTING_PROCESS.md`.
- [ ] Check `drafting-tool/drafting_server/` (ls, run server with MOCK).
- [ ] Test current demo: load T33234 → steps 1-3 pre-filled with real data + LLM suggest in Step 3 → human-readable Step 4. Verify tables fit one page.
- [ ] Test flows: gating (confirms block synth), persistence (restart survives), LLM (Grok/Claude key+account flows, provenance, MOCK pre-fills), dynamic case list, compact UI.
- [ ] Decide next from backlog (output gen first).
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
- [ ] Check `drafting-tool/drafting_server/` code + run server (MOCK)
- [ ] Test flows: gating/persistence, LLM key+account (Grok/Claude), sidebar nav, design UI (tokens, icons, layout, toggle)
- [ ] Decide on next (output gen / frontend polish per updated backlog)
- [ ] At end: update PROGRESS + SERVER-README + LESSONS; append root SESSION_STATE if needed

---

**This file is the primary handoff document.**  
Keep it updated after every significant session. Future Grok instances will thank you.
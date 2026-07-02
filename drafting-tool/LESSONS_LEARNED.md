# Lessons Learned — Drafting Tool Server-Backed Session

**Date:** 2026-07-01 (end of extended session)

## Key Decisions
- Migrated from single-file static HTML to server-backed (FastAPI + frontend) architecture.
- LLM integration is mandatory for creating Objectives and Steps.
- Repeatability achieved primarily through Jinja prompt templates + structured output parsing, not just model behavior.
- All related files (code, plan, docs, nginx config) consolidated under `drafting-tool/`.
- Adopted external design system (from design-guidelines-showcase.html + tokens) as UI template: sidebar+main layout, tokens, components, SVG icons, no top header, full-to-top sidebar.
- Solved browser popup/focus issues for login with in-page instructions panel + explicit "Open tab now" button (instead of alert + immediate open).
- Per-session LLM config (provider + auth_method + creds) + full provenance now persisted for auditability.

## Lessons

1. **Future requirements should drive architecture early.**  
   Single-file worked for v1 but became a blocker once direct LLM calls, growing datasets, and persistent hosting were required.

2. **Templating > raw LLM output for consistency.**  
   To make outputs repeatable and match the exact format in `OBJECTIVE_DRAFTING_PROCESS.md`, prompts must be templated and responses must be post-processed with templates/validators.

3. **Enforce the process gates in the backend.**  
   User confirmation after reviewing each of the three databases must be a server-enforced state, not just client-side UI state.

4. **Self-contained components are easier to maintain.**  
   Moving the plan, all server code, and consolidated documentation into the `drafting-tool/` directory (instead of root-level `server/`) improves discoverability and ownership.

5. **Preserve history while moving forward.**  
   Legacy single-file code and design system files were kept. They serve as reference and prevent loss of prior work.

6. **One authoritative documentation file beats scattered READMEs.**  
   `SERVER-README.md` was created as the single place for "all instructions for use and details."

7. **Explicit session summaries help future context.**  
   Writing this `LESSONS_LEARNED.md` + the summary section in `SERVER-README.md` captures decisions and rationale that would otherwise be lost.

8. **Browser security makes "silent" tab opening tricky.**  
   Modern browsers (esp. Chrome) focus new tabs aggressively and may navigate early. Solved reliably with in-page instructions panel + explicit user-controlled "Open tab now" button (no alert race, user reads first).

9. **Matching external design system exactly matters.**  
   Using the showcase as template (full tokens, sidebar full-to-top no separate header, small gray SVGs not emojis, custom scrollbar with border, page-header/sections, consistent components) greatly improves fidelity, perceived quality, and long-term maintainability over partial adoption.

10. **Persisting complex per-session state (incl. LLM config + provenance) is high value.**  
    File-based JSON for full WizardSession (confirms+selections + LLM creds/auth + step4 + prompts/responses) enables restart survival and audit without heavy DB. Lightweight and sufficient for local hosted tool.

## Artifacts Saved This Session
- `PLAN-server-backed.md` (full plan)
- `SERVER-README.md` (primary documentation, updated)
- `drafting_server/` (gating+persistence+real LLM+UI)
- `LESSONS_LEARNED.md` (this file, extended)
- `static/index.html` (restructured + design integration + login flows + toggle + spacing)
- Updated `PROGRESS.md`
- Design integration (tokens, components, sidebar/main, SVGs, etc.) from showcase applied

## New Insights from 2026-07-02 Session
- Pre-filling realistic demo data (selections from candidates + decisions) + auto-load + auto-search for a flagship case (T33234) makes the tool immediately usable for demos and validation without manual setup each time.
- LLM shines for "intelligent pre-selection / ranking" assistance in Step 3 (ATPyLib) when paired with keyword retrieval (`_build_atp_query` + `_get_atp_candidates`); user approval gate remains essential.
- Aggressive compaction of tables (cell padding 2-3px, input widths 70-100px, section/card margins 8px, font 10-11px) was required to make multi-row selection UIs fit on one page without side-scroll or excessive vertical space.
- Removing verbose labels like "Action:" from human-readable step output, combined with clean <ol> + Expected, significantly improves scannability of synthesized results.
- Dynamic case list + server-enriched load_case (testlink_candidates, zephyr_refs) + session restoration logic closes the loop on "review previous work" use case.
- Keeping demo overrides (T33234 pre-fills) isolated in JS loadCase + searchATP makes it easy to generalize later.

## Recommended Future Practices
- After any significant development session, append to or update this file and the session summary in SERVER-README.md.
- Keep prompt templates and output templates under version control with clear examples.
- Test repeatability explicitly (same inputs → consistent structured outputs) when changing LLM behavior.
- When adopting external design system, audit for exact matches (icons, layout offsets, scrollbar, component classes, no leftover inline) rather than partial.
- Use in-page flows for sensitive actions (like login) to avoid browser popup/focus pitfalls.
- For demo-heavy tools, invest early in pre-filled realistic data paths + auto-trigger flows.

This file serves as persistent memory for the drafting tool project.

See also `PROGRESS.md` (in this directory) for current implementation status, backlog, and handoff notes for future sessions.

Higher-level cross-references: Root `SESSION_STATE.md`, root `README.md`, and `OBJECTIVE_DRAFTING_PROCESS.md`. The external `AGENTS.md` (referenced from root) provides broader context.
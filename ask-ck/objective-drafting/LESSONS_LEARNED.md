# Lessons Learned — Ask CK / Objective Drafting (Server-Backed)

> Entries are chronological; paths in older entries reflect the pre-2026-07-13 layout (`drafting-tool/drafting_server/` → now `ask-ck/CK-main/CK_server/`; root `data/`+`refined-cases/` → now `ask-ck/objective-drafting/`).

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

## New Insights from 2026-07-03 Session — Replacing Fictional Claude Auth with Headless CLI Mode

**Context**: The "Subscription Account" Claude login (pasting a claude.ai "session token" and sending it as `x-api-key` to `api.anthropic.com`) was discovered to be non-functional — there is no session token a user can copy from claude.ai that authenticates the public Messages API; that endpoint only accepts a real developer API key. The UI's own instructions (describing a "Session token" field on claude.ai that doesn't exist) were fictional.

- **Verify an auth mechanism is technically real before building UI/instructions around it.** It's easy to write a plausible-sounding login flow ("open claude.ai, find your session token, paste it here") that never actually works because the target endpoint doesn't accept that kind of credential. When in doubt, trace exactly what header/value the server sends and confirm the receiving API documents that as valid.
- **Claude Code's own OAuth login (`claude /login`) is a distinct credential from Anthropic Developer Platform auth (`ant auth login` / `ANTHROPIC_API_KEY`).** The former is tied to a consumer Pro/Team/Max subscription and is scoped to the Claude Code product surface; the latter is pay-per-token workspace billing. They can coexist on one machine and can conflict if both are configured.
- **Headless mode (`claude -p`) is the sanctioned way to script Claude Code**, and it authenticates with whatever login the local CLI already has. Shelling out to it from this server is legitimate specifically because the intended deployment is "each user runs the tool locally, using their own Claude Code login" — not a shared multi-tenant backend serving many users off one credential. That distinction is the whole ballgame for whether this kind of integration is appropriate.
- **Don't let "no credential" fall through to a MOCK fallback that doesn't apply to the current auth mode.** `suggest_relevant_atp` and `analyze_atp_coverage` originally treated "no stored api_key/token" as "use MOCK," which would have silently ignored real headless-mode calls. Fixed by explicitly checking for the `claude_code` auth method before applying that fallback.
- **Prompt via stdin, not argv, when shelling out to a CLI.** Templated prompts (with full case data + process principles) can be large; passing them as a `subprocess` argument risks hitting OS argument-length limits. Piping via `input=` on `subprocess.run` avoids this entirely.
- **Distinguish CLI failure modes when parsing subprocess output**: "binary not found" (a install-time problem, checkable in advance via `shutil.which`), "not logged in" (a runtime problem, only visible from stderr/exit-code on an actual call attempt), and "timeout" all need different user-facing messages. A generic "LLM call failed" loses information the user needs to self-serve a fix.
- **A scripted fake CLI binary is an effective test double for subprocess integrations.** Writing a tiny shell script that mimics `claude --version` and `claude -p --output-format json`'s JSON wrapper let the full gated flow (load → confirm 1-3 → synthesize) be exercised end-to-end, including error paths (missing binary, login failure), without needing a real Claude Code installation or spending any tokens.
- **Test cleanup can collide with demo state.** Running the full flow against the real T33234 session file (rather than a scratch session) dirtied it; it had to be `git checkout`'d back. For future sessions, prefer testing auth/plumbing changes against a throwaway case key rather than the flagship demo case, to avoid needing to revert real state.

## Recommended Future Practices
- After any significant development session, append to or update this file and the session summary in SERVER-README.md.
- Keep prompt templates and output templates under version control with clear examples.
- Test repeatability explicitly (same inputs → consistent structured outputs) when changing LLM behavior.
- When adopting external design system, audit for exact matches (icons, layout offsets, scrollbar, component classes, no leftover inline) rather than partial.
- Use in-page flows for sensitive actions (like login) to avoid browser popup/focus pitfalls.
- For demo-heavy tools, invest early in pre-filled realistic data paths + auto-trigger flows.
- Before documenting or coding a "login" flow for a third-party AI provider, confirm the credential type actually works against the endpoint you're calling — don't assume a subscription implies a pastable session token.
- When adding a new LLM auth mode, audit every place that currently falls back to MOCK "if no credential" — the condition usually needs to become mode-aware.
- Use a throwaway case key (not the flagship demo case) when testing changes that exercise the full confirm→synthesize flow, to avoid dirtying demo session state.

This file serves as persistent memory for the Ask CK / objective drafting project.

See also `PROGRESS.md` (in this directory) for current implementation status, backlog, and handoff notes for future sessions. Operational docs: `../CK-main/SERVER-README.md`.

Higher-level cross-references: Root `SESSION_STATE.md`, root `README.md`, and `OBJECTIVE_DRAFTING_PROCESS.md` (this directory). The external `AGENTS.md` (referenced from root) provides broader context.

## New Insights from 2026-07-03 Session — Zephyr Step 2 Omission + Full Grok Subscription CLI + UI Simplification

**Zephyr Step 2 strict omission**:
- User repeatedly confirmed that "current Cases list" entries (AWPTCM keys that have TestLink candidate data) must not appear in the Step 2 Zephyr cross-ref table.
- Initial filter skipped them in the related loop. Later strengthened: the primary case's own Zephyr entry was also removed from `zrefs` returned by `load_case`. Step 2 is now *purely* for external cross-references. The primary case is still referenced in the server-built traceability note.
- Lesson: when the user says "omit any test cases that are included in our current Cases list" on a review step, be literal and also consider whether the primary itself belongs in that review table.

**Grok / xAI subscription path is real and testable**:
- Unlike the earlier fictional "paste token from grok.x.ai" account flow, xAI provides a first-class local CLI (`grok`) that authenticates via OAuth (`grok login --oauth`) against SuperGrok or X Premium+ subscriptions.
- The CLI supports excellent headless single-turn use: `--single`, `--prompt-file` (critical for long templated prompts), `--output-format plain|json`, `--no-memory --no-plan --verbatim`.
- Direct testing on the machine (where the CLI was already logged in) proved end-to-end functionality: detection, clean text/JSON output for objectives and steps arrays, and full integration into `synthesize_objectives_and_steps` + ATP paths.
- Lesson: always exercise the actual CLI binary (subprocess, parsing its wrapper, temp files for prompts) before declaring support. The `grok` CLI is agent/build-oriented, so it can emit preamble text; flags help but output quality is different from pure `api.x.ai`.

**UI simplification when radios suffice**:
- Once the two subscription CLI modes (Grok CLI + Claude Code CLI) became the intended primary (and only) paths, the provider `<select>` dropdown became redundant.
- The "API Key (developer)" radio was also removed from the visible UI (per user request). This focuses the tool on the subscription experience the user cares about.
- All derivation of `provider` + `auth_method` now happens from the selected radio value in `setLLMConfig`. `restoreLLMUI`, `update*`, clear/reset, and init paths were updated. Credential field + related account logic removed.
- Lesson: when the choice set is small and each radio fully describes the mode, collapse the selector. Removing dead paths (API key UI) reduces confusion and maintenance.

**General**:
- Consolidate auth mode handling in one place (radio value → provider/auth pair).
- Keep CLI status checks and instruction panels contextual to the chosen radio.
- Legacy `api_key` support is kept server-side (old sessions, power users) but not advertised in current UI.
- Direct Python testing of `_call_*_cli_headless` and full `synthesize_*` paths (before/after UI changes) was invaluable for confidence.

**Bug: NameError in load_case zrefs (high priority)**:
- When loading AWPTCM-T44210 (a case not previously tested), POST /api/wizard/load_case/... returned 500.
- Root cause: In zrefs building loop (after removing demo-specific filter code), `f = z.get("folder"...)` assignment was dropped, but `"folder": f` in append remained.
- Lesson: When refactoring loops for generalization (e.g. removing demo area filters), ensure all variables used in appends are still defined. Always test with fresh/new case keys beyond the usual T332xx.

## New Insights from Recent Session — MOCK/Demo Removal + Direct refined-cases Persistence + Frontend Polish

**MOCK and demo removal for real testing**:
- All fallback logic (MOCK responses, T33234 pre-fills, demo area filters, auto-load/pre-select) removed from llm.py, routers, index.html, run.sh, main.py.
- Tool now strictly requires real auth (LLM_API_KEY or local grok/claude CLI login after `grok login --oauth` / `claude /login`).
- Lesson: Demo/MOCK aids early dev but must be excised for production-like use; "if no credential" must never silently succeed. Pre-computed LLM analysis on load replaces demo data.

**Direct file persistence in export**:
- `/export` now calls `_get_refined_group` (matches zephyr folder last-segment to existing refined-cases dirs like "Port (7)") and writes traceability.md + zephyr_payload.json (plus session) to `refined-cases/<Group>/AWPTCM-Txxxx/` (mkdir -p).
- Client downloads remain for convenience; server-side ensures drop-in without manual steps.
- Lesson: For tools that produce artifacts for downstream (refined-cases + upload), auto-persist in backend is essential for repeatability and UX. Group resolution must fuzzy-match existing layout.

**Frontend polish (inline removal, review summary, editor, generalization)**:
- Multiple style= removed (replaced by .hidden, .instructions-panel, btn-compact-*, form-*-small, etc.); step visibility now class-based.
- renderReviewSummary enhanced: shows up to 4+ selections per step with titles/justifications/counts, confirmed badges.
- Post-synth editor uses more form classes; dynamic HTML cleaned.
- Last demo pre-select logic neutralized; comments/strings updated (pre-filled → pre-computed).
- Lesson: Incremental class-based refactoring + richer summary panels improve maintainability and user review (aligns with repeatable process). Removing demo code also cleans UI assumptions.

**General**:
- Prioritize real paths early; update docs/handoffs in sync with code (MOCK refs linger in docs).
- Export persistence + polished summary advance "repeatable outputs" and process enforcement.
- Continue design component adoption to eliminate remaining inlines.

## New Insights from 2026-07-13 Session — UX Hardening, Gaps Ownership, Case Lists, LFS Push

**load_case zrefs NameError (verified fixed)**:
- The `f` folder assignment was already restored; verified via direct `load_case` on T44210 and others. No further code change needed beyond verification.
- Lesson: log “fixed but verify next session” bugs at the top of PROGRESS and actually re-run load on the failing key first.

**Step 2 relevance ranking**:
- Taking the first N external slim_index entries always returned AWPTCM-T1…T5. Ranking by title/folder/decision tokens + hard anchors (arp, dhcp, mdi, …) produces useful cross-refs.
- Generic tokens alone (port, ipv4, log) create noise; multi-keyword and hard-anchor requirements matter.
- Decision field `m` (AWP-####) must not inflate “must match N specific tokens” penalties — prefer rationale `w` for extra tokens.
- Enrich only top hits with a **batch** jsonl scan; per-key full-file scans are too slow.

**Infinite recursion (RangeError: Maximum call stack size exceeded)**:
- `updateAuthMethodUI()` called `updateLLMDefaults()` which called `updateAuthMethodUI()` again.
- Surfaced only after load when `restoreLLMUI` ran (browser stack overflow). Instrument load steps to find mutual recursion quickly.
- Lesson: placeholder helpers must not call full UI refreshers that call them back.

**Table layout zero-width column**:
- CSS assumed 5 columns summing to 100%; Zephyr/ATP have 6. Last column got ~0 width under `table-layout: fixed` + `break-all` → one character per line and a huge empty-looking row.
- Lesson: column width rules must match actual column count (use explicit classes per table shape). Cap description max-height.

**Workspace LLM vs per-case session**:
- Per-case default `auth_method: api_key` made every new case look “logged out” after Apply on another case.
- Fix: persist last Apply to `sessions/_workspace_llm.json` and copy onto cases without an active CLI/key config.
- Clear-session must not wipe workspace LLM preference.

**Gaps ownership**:
- User does not want an editable gaps box mid-wizard. Gaps are part of the **Traceability artefact** and should be LLM-generated when completing the process (synthesize/export).
- Step 3 is selections-only; `analyze_atp_coverage` ranks only; `generate_gaps.jinja` runs at completion.
- Lesson: align UI fields with *when* in the process a human must intervene vs when the tool synthesizes.

**Dual case dropdowns**:
- Complete = has `refined-cases/**/zephyr_payload.json`. Open = everything else. Partials (session progress) first in Open list.
- After export, refresh lists so cases can move to Complete.

**Search/Suggest on Steps 1–2**:
- Same UX pattern as ATP (keyword search + LLM suggest + merge into table) improves discovery without pre-filling claims.
- Keep omit-rules for Zephyr (no current Cases list members) on search endpoints too.

**GitHub push / LFS**:
- `.gitattributes` LFS tracking is not enough if **early commits** still store full blobs. GitHub rejects any history object &gt; 100 MB.
- `git lfs migrate import --include=... --everything` rewrites all commits to pointers; required before first successful push of the Zephyr XML (119 MB).
- Lesson: after enabling LFS, always verify max blob sizes across *all* history (`git rev-list --objects --all` + sizes), not only HEAD.

**Docs**:
- Root README had become a session changelog; rewrite to status + how-to, point to drafting-tool PROGRESS for tool detail.

## New Insights from 2026-07-13 Session (later) — Repo Restructure + Ask CK Multi-Tool Facelift

**Context**: The tool was renamed **Ask CK** and generalized from single-use to a multi-tool workbench. The user restructured the repo mid-session (`drafting-tool/` → `ask-ck/CK-main/` with `drafting_server/` → `CK_server/`; root `data/` + `refined-cases/` + process docs → `ask-ck/objective-drafting/`; per-tool dirs `pytest-create/`, `test-composer/`, `zephyr-tool/` pre-staged). See `ask-ck/ck-facelift/PLAN-facelift.md` for the executed plan.

**Restructure / repathing**:
- Moving a served app breaks silently in three kinds of places: CWD-relative data loads (`BASE = "."` in data.py), `__file__`-relative escapes (`BASE_DIR.parent.parent / "refined-cases"` in wizard.py, `../../OBJECTIVE_DRAFTING_PROCESS.md` in main.py), and launcher scripts (run.sh `PYTHONPATH`/module target).
- Lesson: centralize filesystem anchors in one module (`CK_server/paths.py`) derived from `__file__`, so future moves are a one-file fix and the working directory never matters.
- Lesson: when directories move mid-session, re-verify paths with `ls`/`git status` before every phase — two exploration passes in the same session saw two different layouts.
- Boot-verify with real data counts (410 cases: 368 open / 42 complete) rather than just `/health` — an app can boot "ok" while silently loading zero data.

**Display renumbering vs load-bearing identifiers**:
- Sidebar labels were renumbered 1–6, but the internal scheme is untouched: `data-step` 0–5, panel ids `step-0..5`, badge ids `#step1-badge..#step5-badge`, session keys `step1..step5`, and `confirm_step/{key}/{1|2|3}` (backend 400s anything else).
- Lesson: renumber **strings only, individually** — never bulk-replace "Step N" in a file where the same numbers appear in ids, session keys, and API paths.

**Relocating a DOM chunk wholesale**:
- The LLM login block moved from Step 0 to a new Configure panel with **zero JS changes** because every access was by `getElementById`/`name` (no positional traversal) and the chunk stayed in the static DOM (bootstrap calls `updateAuthMethodUI`/`updateLLMStatus` before any user interaction).
- Lesson: id-addressed DOM + static markup makes UI restructures cheap; audit for positional coupling before moving, and keep relocated panels in the initial DOM (not lazily injected).

**Multi-tool navigation pattern**:
- One generic `goToPanel(panelId)` (toggles `.tool-panel` cards; section-aware active state via `data-panel` or `'step-' + data-step`) + a thin `goToStep()` wrapper preserved all 8 existing numeric callers.
- Page header became a `PANEL_META` registry keyed by panel id (tool panels get static titles; Generator keeps `KEY — Title`).
- Badge loop scoped to `#nav-generator .sidebar-nav-item[data-step]` — previously new nav items were badge-free only by `parseInt(undefined) → NaN` luck.
- Lesson (new-tool recipe): card div + `PANEL_META` entry + sidebar item + router module; invariant: card id === `data-panel` === registry key.

**Independent selection state per tool**:
- PyTest Creator's Cases step reuses `fillCaseSelect` + the single `/api/wizard/cases` fetch (via a shared `handleCasePairChange` helper) but stores selection in its own `ptCase` global — it must never touch `currentKey`, `#caseSel`, or the page header, or it would silently retarget the Generator's load/confirm/export.
- Lesson: when a second tool reuses a data source, parameterize the existing machinery (don't fork it) and keep selection state strictly per-tool.

**Cleanup while you're there**: `showLLMConfig()` no-op, empty `#llm-config-card`, and the phantom `#llmCredential` handling were removed as part of the relocation — restructures are the right moment to delete vestigial code you must read anyway.

**Docs after a restructure**: every doc layer (root README, PROGRESS, SERVER-README, BoS/EoS prompts, per-dir READMEs) carried stale paths; historical entries (SESSION_STATE, old session summaries, PLAN-server-backed) keep their original paths with a banner note instead of rewriting history.

# PROGRESS.md — Drafting Tool (Server-Backed)

**Purpose**: This file exists so future Grok sessions can quickly understand exactly where we are, what has been built, what the priorities are, and how to continue seamlessly.

**Last Updated**: 2026-07-13 (by Grok)  
**Current Session Theme**:
- Verified load_case zrefs fix; relevance-ranked external Zephyr cross-refs (no more first-N slim_index noise).
- Major UI/UX: dual case dropdowns (Open/partial vs Complete), Search+Suggest on Steps 1–3, table layout fix, stack-overflow fix, workspace LLM persistence.
- Process change: **no editable Gaps field in Step 3** — gaps are LLM-generated at **synthesis/export** for Traceability.
- Docs/README cleanup; favicon; GitHub push unblocked via `git lfs migrate` history rewrite.

---

## 1. High-Level Status

| Area | Status | Notes |
|------|--------|-------|
| Architecture Decision | Complete | Server-backed (FastAPI) |
| Project Structure | Good | All tool work under `drafting-tool/` |
| Core Backend | Strong | Gates, file sessions, search/suggest for TL/Zephyr/ATP, relevance zrefs, workspace LLM file |
| LLM Integration | Complete (CLI primary) | Grok CLI + Claude Code CLI in UI; workspace default in `sessions/_workspace_llm.json`; real-only (no MOCK) |
| Data Integration Steps 1–3 | Implemented | Real TL candidates; external Zephyr ranked; ATP scored; Search/Suggest merge on all three steps |
| Repeatable Outputs | Advanced | Templates + note construction; export → `refined-cases/`; gaps generated at synth/export |
| Process Enforcement | Implemented | Server-side confirms 1–3 before synthesize |
| Frontend UI | Advanced | Dual case lists; toolbars; compact tables (cols-5 / cols-6-*); editor; review summary |
| Documentation | Strong | PROGRESS / SERVER-README / LESSONS / README updated this session |
| Hosting / nginx | Ready | Example config |
| Persistence | File-based | Per-case `sessions/<key>.json` + workspace LLM JSON + refined-cases export |
| Polish & Completeness | Good | Critical UX bugs fixed; more output edge validation / Process page still open |

**Overall Phase**: Usable mid-implementation (workflow runnable end-to-end; packaging/tests/Process page still thin)

---

## 2. Key Decisions & Rationale (Carry Forward)

- **Server-backed is required** (LLM synthesis, growing data, nginx host, extensibility).
- **Repeatability**: Jinja prompt templates + structured parse/output templates + server-built first testScript note.
- **Process gates must be real** (server-side confirms before synthesis).
- **All drafting-tool work stays under `drafting-tool/`**.
- **Gaps are not a Step 3 form field**: user confirms ATP selections only; LLM writes Gaps for Traceability at synthesize/export (`generate_gaps.jinja`).
- **LLM preference is workspace-scoped**: Apply/Login writes `sessions/_workspace_llm.json`; load_case copies onto cases without active config (switching cases must not reset CLI login).
- **Complete vs open cases**: Complete = `refined-cases/**/AWPTCM-Txxxx/zephyr_payload.json` exists; Open/partial = all other candidate keys; partials (session progress) listed first in Open dropdown.

---

## 3. Current File Structure (drafting-tool/)

```
drafting-tool/
├── PROGRESS.md
├── SERVER-README.md
├── PLAN-server-backed.md
├── LESSONS_LEARNED.md
├── README.md
├── run.sh
├── nginx-drafting-server.conf.example
├── drafting_server/
│   ├── main.py                 # + /favicon.ico|svg
│   ├── data.py
│   ├── llm.py                  # gaps gen, suggest TL/Zephyr/ATP, analyze rank-only
│   ├── models.py
│   ├── routers/wizard.py       # load_case, dual /cases, search_*, suggest_*, export
│   ├── static/index.html       # wizard UI
│   ├── static/favicon.svg
│   ├── templates/prompts/
│   │   ├── generate_objectives.jinja
│   │   ├── generate_steps.jinja
│   │   ├── generate_gaps.jinja
│   │   ├── analyze_atp_coverage.jinja   # ranked only (no gaps)
│   │   ├── suggest_atp.jinja
│   │   ├── suggest_testlink.jinja
│   │   └── suggest_zephyr.jinja
│   ├── templates/outputs/traceability.md.jinja
│   └── sessions/
│       ├── _workspace_llm.json          # workspace LLM default (not a case)
│       └── AWPTCM-Txxxx.json
└── (legacy static + design system files)
```

---

## 4. What Is Currently Implemented (Working)

### Backend
- Data load: zephyr_master, candidates, decisions, slim_index, test_id_desc, testlink.
- **Step 2 zrefs**: relevance scoring over slim_index (keywords, hard anchors, omit current Cases list + primary); batch JSONL enrichment for top hits; returns `score` + `justification`.
- **load_case NameError (`f` undefined)**: fixed and verified (e.g. T44210 + other keys).
- LLM: CLI modes `grok_cli` / `claude_code`; Jinja prompts; provenance; no MOCK.
- **generate_coverage_gaps** at synthesize (+ export if gaps empty).
- **Workspace LLM**: `_workspace_llm.json` on Apply/Login; applied on load when case has no active config.
- **GET /api/wizard/cases**: dual lists — `incomplete` (in_progress first, then not_started by folder) + `complete` (refined payload present); counts.
- Search: `/search_testlink`, `/search_zephyr`, `/search_atp`.
- Suggest: `/suggest_testlink/{key}`, `/suggest_zephyr/{key}`, `/suggest_atp/{key}`.
- Export: downloads + write to `refined-cases/<Group>/AWPTCM-Txxxx/`; validation hooks.

### Frontend
- Step names: **1. TestLink**, **2. Zephyr**, **3. ATPyLib (scored)**, **4. Synthesize**.
- **Dual case dropdowns**: Open/partial (partials at top) vs Complete; mutual exclusivity; refresh after export.
- Search + Suggest toolbars on **all three** review steps; client merge preserves checkboxes.
- Table CSS: explicit `cols-5` / `cols-6-zephyr` / `cols-6-atp` (fixes zero-width description → huge row height).
- Fixed infinite recursion: `updateAuthMethodUI` ⇄ `updateLLMDefaults`.
- No Step 3 gaps textarea; gaps only after synth (review summary note).
- Step 4 human-readable + editor (objective + steps + expected); session debug collapsed.
- Favicon served (`/favicon.ico`, `/favicon.svg`).

### Repo / ops (this session)
- Root + drafting-tool README cleaned.
- Git LFS history migrate for Zephyr XML + jsonl + index (GitHub push unblocked after rewrite).

---

## 5. What Is Not Yet Implemented (Priorities)

### High Priority (Next Session Focus)
1. **Output generation hardening** — M  
   - Edge cases: empty selections, thin ATP, re-export after edit.  
   - Stricter pre-write validation vs real `refined-cases` exemplars.  
   - Confirm first-step note + Gaps section quality after new gaps-at-synth flow.

2. **Real CLI smoke on full UI path** — S (0.25–0.5 session)  
   - Grok + Claude: Load → confirm 1–3 (search/suggest) → synthesize → export → open refined-cases.  
   - Claude Team previously often only faked CLI; validate live.

3. **Error handling + loading UX** — M  
   - load_case ATP rank can be slow (LLM); clearer spinners/timeouts.  
   - Surface synthesis/export errors in-page (not only alert/console).

### Medium Priority
- Process Reference page: full markdown + deep links to wizard steps (S–M).
- `requirements.txt` / pyproject + simple setup (S).
- Server-side indexing for full jsonl/suites search quality (M).
- Optional: refresh case lists after clear-session without full page reload (already partially covered).

### Lower / Future
- Multi-user auth (L).
- Advanced LLM (critique loop, few-shot from past refined cases) (L).
- Automated tests + CI (M).
- One-command nginx setup (S–M).

**Suggested order for next session**:
1. Smoke full real-CLI path on 1–2 open cases (verify gaps land in traceability.md).  
2. Output hardening vs Port/IPv4 exemplars.  
3. requirements.txt + error UX.  
4. Process page enhancements.

---

## 6. How to Resume Work (For Future Grok Sessions)

1. Read this **PROGRESS.md** completely.  
2. Read **SERVER-README.md** (run + workflow).  
3. Skim **LESSONS_LEARNED.md** (esp. 2026-07-13).  
4. Start server from repo root:
   ```bash
   ./drafting-tool/run.sh
   # → http://localhost:8000/
   ```
5. Apply LLM once (Grok or Claude CLI) — preference persists in `_workspace_llm.json`.  
6. Use **Open / partial** for unfinished work; **Complete** for refined payloads.  
7. Do not reintroduce Step 3 gaps editing or MOCK paths.

---

## 7. Important Context to Remember

- Main goals: **repeatable process** + **repeatable outputs** with user review gates and templated LLM.  
- Legacy single-file tool is reference only.  
- Gaps belong in Traceability artefact (LLM-authored at completion), not as a mid-wizard free-text gate.

---

## 8. Technical Debt & Known Issues

### Technical Debt
- LLM parsing still regex/JSON fallback — could use stricter structured output later.
- Full zephyr_cases.jsonl not fully indexed for search (keyword scan + slim_index scoring only).
- No automated tests / requirements.txt.
- zrefs scoring ~1.5s over 45k slim_index — acceptable but not optimized.
- load_case still runs ATP LLM ranking (latency); gaps no longer on load (good).

### Known Issues / Limitations
- Shared multi-tenant server pooling one CLI login is unsupported (per-user local host intended).
- Grok CLI may still emit preamble; stripping helps but is imperfect.
- GitHub: large sources must stay LFS in **all** history commits (use `git lfs migrate` if reintroducing big files).
- Process page remains basic.
- Some older session JSON may still hold stale Step 3 gap text; synth/export overwrites for Traceability.

---

## 9. Prioritized Backlog with Effort Estimates

| Priority | Item | Effort | Notes |
|----------|------|--------|-------|
| High | Output generation hardening | M | Post gaps-at-synth validation |
| High | Real Grok+Claude E2E UI smoke | S | Provenance + refined-cases check |
| High | Error/loading UX | M | Especially load_case + synthesize |
| Medium | Process page + deep links | S–M | |
| Medium | requirements.txt / setup | S | |
| Medium | Full data indexing | M | |
| Low | Tests/CI, multi-user, advanced LLM | M–L | |

**Completed this session (removed from active high backlog)**:
- load_case NameError verify/fix  
- Step 2 zrefs relevance  
- Frontend polish batch (tables, editor, dual cases, search/suggest 1–3)  
- Workspace LLM persistence  
- Gaps moved to synth/export  
- Stack overflow + table layout bugs  
- Favicon  
- README cleanup  

---

## 10. Cross-References

- Root `README.md` — project framing; drafting tool summary  
- Root `SESSION_STATE.md` — broader history (2026-07-13 entry)  
- `OBJECTIVE_DRAFTING_PROCESS.md` — process source of truth (tool implements it; gaps still part of Traceability, authorship path is tool-side)  
- External `AGENTS.md` — machine/CLI environment if present  

---

## 11. Session Handoff Checklist

When starting a new session:
- [ ] Read `drafting-tool/PROGRESS.md` (this file)
- [ ] Read `drafting-tool/SERVER-README.md`
- [ ] Skim `drafting-tool/LESSONS_LEARNED.md` (2026-07-13)
- [ ] Run `./drafting-tool/run.sh`; hard-refresh browser
- [ ] Confirm dual case dropdowns + partials at top of Open
- [ ] Apply LLM once; switch cases — status must stick
- [ ] Load open case → Search/Suggest steps 1–3 → confirms → synthesize → check Gaps in traceability → export
- [ ] Step 3 has **no** gaps textarea
- [ ] At end: update PROGRESS + LESSONS + SERVER-README; append root SESSION_STATE if impactful

---

**This file is the primary handoff document.** Keep it updated after every significant session.

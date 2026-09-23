---
verified: 2026-09-23
---
# PLAN — Generate state gating, review↔code binding, sequence sanity, library-aware review

> ## Status (read first)
>
> **RETIRED 2026-09-23 → `archive/plans/`** (complete; the rule is
> `archive/plans/PLAN-restructure-2026-09-11.md` §1). Re-checked the same day: `_code_hash`,
> `_gen_state`, `_require_units_current`, `_rechunk_from_script`, `/rechunk`, `/reset_generate`
> and the `_pt_domain_facts.jinja` include are live. **The tests landed under different names
> than the slices below propose:** reset_generate in `tests/test_pt_gen_state.py` and
> `tests/js/pt-gen-state.spec.js`; slice C in `tests/test_pt_sequence_sanity.py` and
> `tests/js/pt-seq-claims.spec.js`. `test_pt_reset_generate.py`, `pt-reset-generate.spec.js`,
> `test_pt_sequence_sanity_prompt.py` and `test_pt_extract_sequence_claims.py` never existed.
>
> **BUILT 2026-09-21 — every slice shipped the same day** (D `56c7022`; A + B + reset_generate `fc8348b`; C `f75581b`; docs in the wrap commit). Gate 1634 passed / 2 known reds. One deviation from the order below: A, B and reset_generate landed in ONE backend save and ONE commit, to bounce production once instead of three times. Found and fixed on the way: `save_sequence` dropped `kind` on every Save Edits.
>
> **Originally:** APPROVED 2026-09-21, IN PROGRESS. Terrence: "Please build them." The four designs (A–D) were
> agreed during the T33234 repair (2026-09-17/18) and recorded in memory `frame-binds-two-roles-only`;
> this file is the executable plan. Decisions taken 2026-09-21: edit the working tree directly
> (production reloads accepted); Re-chunk snapshots the FRAME too; domain facts live in a prompt
> include template; sanity flags WARN, never block Confirm. Slices land as separate commits in the
> order below; each slice's section is marked SHIPPED with its commit hash as it lands.
>
> Progress: D ☑ 56c7022 · reset_generate ☑ fc8348b · A ☑ fc8348b · B ☑ fc8348b · C ☑ f75581b · docs/wrap ☑


## Context

During the T33234 repair (2026-09-17/18) four defects in the PyTest Creator's *process* were
found and designed but not built. They are recorded in memory `frame-binds-two-roles-only`
(sections A–D, "FIRST TASK"). Terrence asked on 2026-09-21: "Please build them."

- **A.** Two truths: `step6.chunks` (units) and `step6.files.test.code` (assembled script).
  `save_script`/`fix_script` edit only the script; every splice path (`assemble_script`,
  `assemble_and_settle`, `fix_units`, `apply_held`) re-splices from stale chunks via
  `_assemble_and_store` and silently discards the repair. The UI shows nothing (all pills green).
  T33234 today holds 19 fresh, unassembled units beside the saved script — one Assemble click
  from losing the repair.
- **B.** Review findings stay on screen after a Fix/Save changed the code they describe.
- **C.** The step-5 physics error and the step 6-vs-7 contradiction were born at Extract
  Sequence and treated as axioms downstream. Terrence's shape: the extraction call also checks
  the sequence against a maintained domain-facts block + the CLI reference, and the Sequence
  page shows a per-step claims table. Warn, don't block.
- **D.** `review_script`/`fix_script` never see `library_awptcm_*.py`; 4 of 5 final T33234
  findings were false because of it (`waitForLinkState 'down'`, `checkCurrentPort 'auto'`,
  `expect_value`).

Decisions taken with Terrence (2026-09-21): edit the working tree directly (accept the
production reloads); Re-chunk snapshots the **frame too**; domain facts live in a **prompt
include template**; sanity flags **warn, don't block**.

Constraints: `ck.db` never written outside the server; every `CK_server/*.py` save restarts
production (memory `editing-backend-restarts-production`) — two seats connected; gate is
`./ask-ck/tools/run_tests.sh`; stage explicit paths; Terrence pushes.

Key files: `ask-ck/CK-main/CK_server/routers/pytest_create.py` (all endpoints),
`ask-ck/CK-main/CK_server/templates/prompts/pt_*.jinja`,
`ask-ck/frontend/ck-main/current/pytest-creator/pytest.js`, `ask-ck/frontend/ck-main/current/index.html`,
tests in `tests/` (pytest, pattern `tests/test_pt_load_fresh.py`) and `tests/js/` (vitest, pattern
`tests/js/pt-load-fresh.spec.js`, `tests/js/pt-review-panel.spec.js`).

## Order of work (one commit per slice)

1. **D** — library into the review/fix prompts (smallest, standalone).
2. **reset_generate** — drop units, keep steps 1–4 and the saved script.
3. **A** — hash-bound state: divergence detection, 409 gating, Re-chunk with frame snapshot,
   `fix_script` re-chunks itself, UI pills + greyed buttons.
4. **B** — review bound to a code hash; stale findings collapsed; per-finding evidence check.
5. **C** — domain-facts include, sanity pass in Extract Sequence, claims table on the Sequence page.
6. Docs + memory + gate + wrap.

## Slice D — library context for Review and Fix

Backend `pytest_create.py`:
- `review_script`: pass `library_name`/`library_code` from `step6["files"].get("library")`
  (empty when absent) into `run_prompt("pt_review_script.jinja", …)`.
- `fix_script`: confirm the template's existing `library` variable is fed the same way; add if not.

Templates:
- `pt_review_script.jinja`: new `## Helpers this script imports (authoritative)` block, fenced code,
  only `{% if library_code %}`; a rule under `## Rules`: a symbol, keyword argument or documented
  behaviour defined in that module is in scope and correct — do not report it.
- `pt_fix_script.jinja`: same block if missing.

Tests: `tests/test_pt_prompt_library_context.py` — render both templates with/without a library
(pattern: `tests/test_prompt_layer_boundaries.py` loads templates via `_prose`); endpoint test
monkeypatching `run_prompt` to capture the context (pattern: `tests/test_pt_review_pass.py`).

## Slice reset_generate

Backend: `POST /reset_generate/{key}` — `_pt_get`; 409 if no `step6.files.test`; new step6 =
`{files, lint, naming, confirmed: False, reset_at}` (drops chunks, review, assembly, assembled_at,
settle, fix_units, iterations, lint_history, frame); `_invalidate_from(sess, 5)`; `_pt_persist(sess)`
(lock-gated). Returns `{dropped_units: [...], kept: [...]}`.

UI (`pytest.js` + `index.html` Summary page): button "Reset Generate (drop units)" with
`confirm()`, then `ptRefreshSession(); renderPtGenPanel(); ptRenderUnits()`.

Tests: `tests/test_pt_reset_generate.py` (offline, monkeypatched persistence as in
`test_pt_load_fresh.py`); `tests/js/pt-reset-generate.spec.js` (confirm + endpoint hit).

## Slice A — hash-bound state

Backend helpers (new, near `_assemble_and_store`):
- `_code_hash(code) -> str` (sha1, 16 hex).
- `_gen_state(step6) -> dict`: `{script_hash, assembled_hash, units: n, diverged: bool, reason: str,
  review_stale: bool (slice B)}`. `diverged` = script hash ≠ `assembled_hash`, or no units at all while a
  script exists. Reason in plain words ("The script was edited after the last assembly — Fix whole
  script or Save. Re-chunk before any unit operation, or the assembly would discard those edits.").
- `_require_units_current(sess)` → `HTTPException(409, reason)` when diverged. Called first in
  `assemble_script`, `assemble_and_settle`, `fix_units`, `apply_held`, `generate_units`, `generate_step`.
- `_assemble_and_store._apply`: set `step6["assembled_hash"] = _code_hash(stamped)`.
- **Frame snapshot**: `_rechunk_from_script(step6, ctx) -> (step6, changed_ids)`:
  `code = files.test.code`; `units = _skeleton_units(code)` (existing); 409 if empty (frame not
  parseable — say so); `chunks = _resync_chunks(chunks, _chunks_from_code(code, ctx))` (both existing);
  `step6["frame"] = {"code": code, "hash": h}`; `assembled_hash = h`.
- `_pt_generation_context`: when `step6.frame` exists use `frame.code` as `ctx["skeleton"]` and
  `_skeleton_units(frame.code)` as `ctx["units"]`, so `_assemble_units` splices into the real frame and
  per-unit prompts embed it. Verify `_restamp_provenance` is idempotent on an already-stamped script
  (test); if not, skip re-stamping when the frame is a snapshot.
- `POST /rechunk/{key}`: lock-gated; runs `_rechunk_from_script`; returns `{changed: [...], state}`.
- `fix_script`: after `_apply_fix`, run `_rechunk_from_script` in the same persist → never diverged
  after a Fix. `save_script` does **not** auto-rechunk (an identical push from `ptPushCodeEdits`
  leaves the hash unchanged; a real hand edit shows the pill until the user Re-chunks).
- `reset_generate` also drops `frame`.
- Expose: `load_case`, `get_session`, `save_script`, `rechunk`, `reset_generate`, `fix_script`,
  `assemble_*` responses carry `"gen_state": _gen_state(step6)`.

UI (`pytest.js`): store `ptGenState`; `ptRenderUnitPills` + `renderPtGenPanel`: when diverged →
`disabled` on `#pt-assemble-btn`, `#pt-assemble-only-btn`, `#pt-fix-units-btn`, `#pt-apply-held-btn`,
the Generate-all button and the unit-page Generate/Apply buttons, with `title` = reason; pill
`⚠ units stale` (red) vs `units ⇄ script` (green); new local button "Re-chunk from script" →
`/rechunk/`. `ptApi` already surfaces a 409 `detail` in the status element.

Tests: `tests/test_pt_gen_state.py` — assemble sets hash/in-sync; changed `save_script` → diverged,
`assemble_script`/`fix_units`/`generate_units` → 409; `rechunk` → in sync, chunk codes equal the
script's classes, frame stored; assemble after rechunk reproduces the script **byte-identically**;
`fix_script` (monkeypatched LLM) leaves state in sync; `reset_generate` drops chunks+frame.
`tests/js/pt-gen-state.spec.js` — disabled buttons + pill text when diverged; Re-chunk hits endpoint.

## Slice B — review bound to code

Backend: `review_script` stores `review["code_hash"]`; `_gen_state` adds `review_stale`.
`fix_script` keeps findings (no pop) — staleness is shown, not erased.

UI: `ptRenderReview(review, code, stale)`: when stale → badge "review is for an earlier version of
the script", findings inside a collapsed `<details>`; per finding `_ptEvidencePresent(code, evidence)`
(whitespace-insensitive substring, same normalisation idea as `_unit_diff_scope` anchors) → tag
"evidence still present" (amber) or "evidence gone" (muted, struck).

Tests: `tests/js/pt-review-stale.spec.js`; extend `tests/test_pt_review_pass.py` with `code_hash`.

## Slice C — sequence sanity in Extract Sequence

Templates:
- New `templates/prompts/_pt_domain_facts.jinja` (Jinja include): crossover vs straight-through
  pairing; an **auto-MDI partner adapts to any forced DUT role over either cable** (so "forced DUT vs
  auto partner" is never a negative — a negative needs BOTH ends forced); fibre has no MDI/MDI-X;
  `configured` vs `current` lines in `show interface`; half duplex impossible ≥ 1 Gig; `show interface
  status` tokens (`a-full`, `connected`). Sourced from memories `awplus-speed-duplex-constraint`,
  `configured-vs-current-show-interface`, and Terrence's 2026-09-18 rulings.
- `pt_extract_sequence.jinja`: `{% include "_pt_domain_facts.jinja" %}` (confirm `run_prompt`'s
  loader supports includes — templates dir is a FileSystemLoader; verify), plus a `## Sanity pass
  (before you output)` section: for each step that forces a role/speed/duplex or changes cable/link
  state, emit `claim: {cable, dut, partner, expect}`; compare claims pairwise (same cable+roles ⇒ same
  expect) and against the facts; list contradictions as `sanity: [{steps:[n,m], issue}]`. Output shape
  extended accordingly. Move the existing half-duplex / Configured-vs-Status prose into the include.
- `pt_review_script.jinja`: include the same facts, so Review applies the same physics.

Backend: `extract_sequence` keeps `claim` on each step and stores `step2["sanity"]`;
`save_sequence` preserves `claim` and `kind` from the stored step (matched by `n`) when the UI row
lacks them.

UI: `ptRenderSequence`: "Claim" column (`crossover · DUT mdix · partner auto → down`), rows named
by a sanity flag get a red marker with the issue as `title`; a `#pt-seq-sanity` box above the table
lists the flags. `_ptSeqCache` also carries `claim` and `kind` so a Save round-trip keeps them.
Confirm stays enabled.

Tests: `tests/test_pt_sequence_sanity_prompt.py` (include renders; sanity section + output shape
present; `test_prompt_layer_boundaries.py` still green); `tests/test_pt_extract_sequence_claims.py`
(monkeypatched `run_prompt` → claims/sanity stored; `save_sequence` preserves claim/kind);
`tests/js/pt-seq-claims.spec.js`.

## Production-restart handling (Terrence chose in-place edits)

Batch edits so each backend file is saved as few times as possible. After every backend save poll
`GET http://localhost:8000/api/version` until 200 (≤ 30 s). If it does not return, report it and use
the admin-panel restart (memory `ask-ck-admin-restart`); never `run.sh --stop/--bg`. Tell Terrence
before the first backend save so the other seat can be warned.

## Docs, memory, wrap

- `ask-ck/CK-main/SERVER-README.md`: new endpoints (`reset_generate`, `rechunk`), `gen_state`, the
  frame snapshot rule, sequence `claim`/`sanity` fields.
- `CHANGELOG.md` (product changed: gate + contract), `PROGRESS.md` top entry, `SESSION_STATE.md` tail,
  `PLAN-self-healing-generation.md` status note.
- Memory `frame-binds-two-roles-only`: mark A–D and FIRST TASK **SHIPPED (date)**; keep the frame
  two-role limitation as the remaining deferred item; update `MEMORY.md` line.
- Commits per slice, explicit paths, Fable attribution; Terrence pushes.

## Verification

1. Gate: `./ask-ck/tools/run_tests.sh` before and after each slice (known reds: preflight name test,
   zephyr corpus floor).
2. Manual checklist for Terrence on the live UI, case **T33234**:
   - Load Case & Continue → 5. Generate: pill reads `⚠ units stale`; Assemble/Fix units/Apply held greyed.
   - Click **Re-chunk from script** → pill green; unit pills show the repaired classes.
   - Click **Assemble** → code box unchanged (`# DELIBERATE` still at line 74, `force_partner_polarity`
     present); server file byte-identical to git HEAD's copy.
   - Review panel shows the 2026-09-18 findings collapsed as stale with per-finding evidence tags.
   - 2. Sequence: claims column visible after a fresh Extract on a **scratch** case (not T33234's
     confirmed sequence); flags render as warnings only.
   - Summary → **Reset Generate** on a scratch case drops the units, keeps steps 1–4 and the script.

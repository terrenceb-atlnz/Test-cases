# Backend Module Split of `CK_server/routers/wizard.py` (+ uniform deferred step loading)

> **Status (2026-07-29): COMPLETE — all 11 commits DONE (commit 6 dropped by decision).**
> Commit 10, the atomic `routers/wizard.py` → `routers/wizard/` move, landed this session;
> `wizard.py` (1972 lines) is now the package `reviews`/`config`/`synthesis`/`export` +
> `_shared` + `__init__`, with every function body moved BYTE-IDENTICAL (proven by diff of
> the reassembled slices against the original). Everything in Part A and Part B has shipped.
>
> | | commit | state |
> |---|---|---|
> | Part A | 1-5 | ✅ `4578030` (+`0c06586`), `9178659`, `91d86ef`, `77cb383`, `0b47926` |
> | | 6 | 🚫 DROPPED (user decision) — `SURVEY-step4-step5.md` |
> | Part B | 7 | ✅ `591dbb9` `refactor: extract wizard/descriptions.py` |
> | | 8 | ✅ `104d3e6` `extract llm_config.py + case_registry.py` — **the coupling fix** |
> | | 9 | ✅ `e15c360` `extract session_store.py + wizard/{gates,backfill}.py` |
> | | **10** | ✅ **DONE (2026-07-29)** — `routers/wizard.py` → `routers/wizard/` package |
> | | 11 | ✅ `77ab960` `decompose export()` — taken BEFORE 10, deliberately |
>
> **Commit 10 as executed.** Four route modules split on the file's existing concern order
> (reviews 148–981 / config 982–1190 / synthesis 1191–1497 / export 1498–EOF), shared
> `get_data` + `OUTPUTS_ENV` in `_shared.py` (a leaf, so no import cycle), and `__init__.py`
> mounts the four sub-routers and re-exports the surface main.py + the tests import. The two
> cross-module private helpers (`_session_llm_cfg` reviews→synthesis, `_authoritative_session`
> synthesis→export) use RELATIVE imports so the decoupling suite does not read them as a
> cross-router reach. The six hardcoded `routers/wizard.py` source-path reads across the test
> suite now resolve through one helper, `tests/_wizard_src.py` (`wizard_router_paths()` /
> `wizard_router_source()`), which raises if it finds nothing — a stale glob that silently
> stopped matching was the exact failure mode the plan warned about. Gate: **584 pytest + 85
> Vitest**, both guards, ck.db signature unchanged.
>
> **`wizard.py` is 2515 → 1971 lines** (2515 → 1907 by commit 9; commit 11 added back ~64
> lines of named helpers + docstrings while removing the 351-line monolith).
>
> **Two things changed shape since this plan was written:**
> - **`CK_server/wizard/` was renamed to `CK_server/generator/`** (`03a0aac`), because
>   commit 10 makes `routers/wizard/` and two packages called `wizard` is unreadable. Every
>   reference to `wizard/descriptions.py`, `wizard/gates.py`, `wizard/backfill.py` in the
>   tables below means `generator/…` now.
> - **Commit 11 was done before commit 10.** The plan sequenced it last so it would not be
>   attempted *during* the move; doing it first honours that and makes the move easier —
>   commit 10 now relocates six short functions instead of one 351-line handler.
>
> Read *What A1 taught* below before continuing — one of this plan's core assumptions was
> falsified by measurement. A2 added two more corrections of its own; see its section.
> **A4 corrected three wrong items in its own plan entry — see the A4 section; verify
> dead-code claims by AST scan before trusting any list in this document.** Commits 7-9 and
> 11 each added their own corrections; see *Part B — as executed*.
>
> **Original status line, kept for context:** PLANNED, nothing implemented. Written 2026-07-28 from a full read of all
> 2439 lines; revised the same day after the "all data steps must load identically"
> decision, which replaced an optimize-the-scan approach with delete-the-scan.
> **11 commits, all in scope.** Part A (perf/correctness) is independent of Part B (the
> split) — do A first. Part 0 (Python 3.13 venv) was executed in the authoring session.
> See *Handover state* for what is settled and where to resume.

## Context

`ask-ck/CK-main/CK_server/routers/wizard.py` is 2439 lines: **69 functions, 24 `@router`
decorators (23 endpoints — `set_llm_config` carries two)**. It is the Generator (objective
drafting) backend: three DB-review gates (TestLink / Zephyr / ATPyLib), two LLM synthesis
steps, export of the drop-in `refined-cases/` bundle, and `push_to_zephyr`. It is also,
accidentally, the app's shared library.

The trigger for this plan was "is it too monolithic?" The answer is yes, but **size is not
the real defect and splitting is not the highest-value work.** Two measured performance
bugs and one silent-data-loss bug matter more, and none of them require the refactor.

### Verified facts that shape the plan

Measured on this seat (2026-07-28), `ask-ck/var/ck.db`: zephyr_cases **45,427** rows,
testlink_cases 21,620, atp_tests 10,157.

```
                                py3.10     py3.13    (re-measured after the 032f521 cutover)
_select_related_zephyr_refs():  3769.8 ms  2707.8 ms  <- ON the event loop, every load_case
load_all_data():                  70.0 ms    47.3 ms  <- per REQUEST, x10 endpoints
_refined_complete_keys():         14.9 ms    13.9 ms  <- on the event loop, /cases
```

3.13 bought ~28 % on the scan for free. **Both bugs still reproduce**; use the 3.13 column.

- **`load_case` blocks the event loop for ~3.8 s.** `wizard.py:813` calls
  `_select_related_zephyr_refs` directly from an `async def`. It streams all 45,427 slim
  Zephyr rows through `_score_zephyr_candidate` in Python. Twelve lines below,
  `wizard.py:824-825` *does* wrap the ~100 ms ATP search in `run_in_threadpool` with a
  comment explaining that a cold model "stalls the very first thing a user does". The
  guarded call is 100 ms; the unguarded one above it is 3.8 s. This freezes every
  concurrent request, including the agent-bridge long-poll that `wizard.py:2121-2130`
  documents as a **self-deadlock** risk in `claude_agent` mode.

- **The three data steps have three different load-time behaviours — and Step 2 is the
  outlier on every axis.** This is the framing that matters (user decision, 2026-07-28:
  *"all data steps should be identical in startup behavior… unless there's an explicit
  advantage, I don't see why they should be doing anything different from each other
  (besides getting different sets of data)"*).

  | Step | Source | Mechanism | Cost | Scorer |
  |---|---|---|---|---|
  | 1 TestLink | `candidates_dict[key]`, pre-scored in ck.db | dict lookup, first 8 | ~0 ms | none needed |
  | 2 Zephyr | `db.iter_zephyr_slim()` — **full 45,427-row scan** | Python loop, **bare on the event loop** | **3770 ms** | `_score_zephyr_candidate` — bespoke, 94 lines |
  | 3 ATP | `db.search_atp` via `_get_atp_candidates` | **FTS index**, `run_in_threadpool` | ~100 ms | `db._relevance_score` — shared |

  The *on-demand* endpoints are already symmetric (`search_*` + `suggest_*` for all three).
  Only the load path is asymmetric.

- **`db.search_zephyr` already does what Step 2's load needs.** `db.py:489` — FTS-indexed
  (`zephyr_fts`), scored by the shared `db._relevance_score` (`db.py:143`), and it applies
  the identical "omit the current Cases list + primary key" semantic via `exclude_keys`. It
  is *already* wrapped by `_search_zephyr_external` (`wizard.py:1082`) and *already*
  threadpooled for the `/search_zephyr` endpoint (`:1130`). So the load-time scan is a
  parallel, slower, hand-tuned reimplementation of a function that already exists one
  screen away.

- **The ranking that 2.7 s buys is 81 % arbitrary.** Baseline captured across 10 cases in 10
  distinct folder leaves (80 refs): **65 of 80 refs (81 %) sit inside the largest score-tie
  group of their case**, and 3 of the 10 cases return all 8 refs at a *single identical
  score* (T33241 IPv4 @20.80, T44318 Advanced-Management @42.80, T45102 Issue-Placeholder
  @8.96). Ties break **alphabetically by title** (`wizard.py:722`
  `sort(key=lambda x: (-x[0], title))`), so for those cases "the 8 most relevant Zephyr
  cross-refs" is really "8 alphabetically-first cases that cleared a low bar."
  Two concrete quality failures in the baseline:
  - T45102 (*Issue Placeholder* — no distinctive feature noun): all 8 tied at 8.96, and all
    8 are noise (ACL class-maps, BGP4+ routemaps, a webgui preference file).
  - T33233 (*Port*, about status/speed/duplex/negotiation): one excellent hit at 20.30
    (`interface: port status, speed, duplex and negotiation`), then **7 tied at 12.80 that
    matched only the word "negotiation"** — IPsec transforms, ISAKMP IKEv2, LACP bonding,
    PROFINET. `negotiation` is absent from `_ZREF_GENERIC_TOKENS`, so a mid-specificity word
    drags crypto tests into a physical-layer port case.

  **This materially de-risks A1.** The 94 lines of hand-tuned heuristics perform far worse
  than their apparent sophistication, so `db._relevance_score` has a low bar to clear. Do
  still diff — but expect the change to be an improvement, not a regression to defend.

- **The whole Step-2 scan cluster has exactly ONE entry point** (`load_case:813`), so
  retiring it makes all of this dead:
  `_select_related_zephyr_refs` (685-756, 1 caller) → `_score_zephyr_candidate` (462-555,
  1 caller) → `_ZREF_WEAK_ALONE` (431, 1 use) → `db.iter_zephyr_slim` (`db.py:313`, 1
  caller) → the private `_ZREF_GENERIC_TOKENS` (407-428). **~150 lines in wizard.py + 11
  in db.py.** Note `wizard.py:1053-1057` claims the module "no longer keeps a private copy"
  of the relevance scorer — half true: `_ZREF_GENERIC_TOKENS` is duplicated **verbatim**
  into `db.py:123` (117 tokens, byte-identical today — verified — but two copies is a live
  drift risk, exactly the one that comment says was eliminated).
- **`get_data()` rebuilds the whole reference set per request.** `wizard.py:402-404` is
  `def get_data(): return load_all_data()` with the comment *"Would be from app.state in a
  fuller implementation"*. `main.py:132` already builds this once into
  `app.state.app_data`, and `pytest_create.py:583,1799` reads it correctly via
  `request.app.state` — **only wizard doesn't, across 10 `Depends(get_data)` sites.**
  Because `get_data` is sync, FastAPI threadpools it, so this is *waste, not a freeze*:
  70 ms CPU + a threadpool worker per request, plus `load_all_data` **prints 3 lines to
  stdout on every call** (`data.py:57,88-93`) — the source of log spam during normal use.
  It also means two dependencies in one request can see different snapshots.
- **`confirm_step` silently discards malformed selections.** Three identical blocks at
  `wizard.py:1457-1482`: `except Exception: pass` around
  `[Selection(**s) for s in body["selections"]]`, then `confirmed = True` unconditionally.
  One bad selection drops the whole list, the step is still marked confirmed, and the
  response returns `can_synthesize: true`. The user then synthesizes against the
  *previous* selections. Same family as HEAD's `9afdf97 "fix a silent session data-loss
  bug"`. There are **5 `except Exception: pass` and 18 bare `except Exception`** in the file.
- **The real structural defect is cross-router private imports.** `pytest_create.py:33-36`:
  ```python
  from routers.wizard import (
      _load_global_llm, _llm_is_active, _same_backend,
      _refined_complete_keys, _build_case_groups, _is_hidden_case,
  )
  ```
  A sibling router imports **six underscore-private helpers** from another router. Renaming
  any of them silently breaks a different feature. `pytest_create._apply_workspace_llm`
  (`:280`) is already a hand-maintained *copy* of `wizard._apply_workspace_llm_if_needed`
  whose docstring says "Mirrors wizard…" — drift risk by construction.
- **Environment:** pydantic **2.13.4**, so the
  `sess.dict() if hasattr(sess, "dict") else sess.model_dump()` hedge — repeated **13×** —
  is both dead (`.dict()` always exists in v2) and deprecated (it always warns). 9×
  `datetime.utcnow()`, deprecated from 3.12 and on a removal path — **now live**, since the
  seat gained Python 3.13.14 (see Part 0).
- **Tests constrain the split, in two different ways.** 7 of 20 test files reference wizard.
  - *By import:* `tests/test_export_gate.py:38` imports `sessions, _clear_persisted`;
    `test_export_authority_batch_a.py:29` imports 6 pure helpers
    (`_backfill_from_refined`, `_can_synthesize`, `_invalidate_downstream`,
    `_selection_fingerprint`, …); `test_security_hardening_batch_e.py:80` imports
    `push_to_zephyr`. Fixed by re-exports in `routers/wizard/__init__.py` or updated imports.
  - *By file path* — the sharper one. Three files read the module as **text**:
    `test_event_loop_blocking_batch_b.py:57,72,80`,
    `test_security_hardening_batch_e.py:62`, `test_export_authority_batch_a.py:367,378`.
    Turning `routers/wizard.py` into `routers/wizard/` makes `(_ROUTERS / "wizard.py")`
    a `FileNotFoundError` — loud, fine. **But `:57` is
    `@pytest.mark.parametrize("router", sorted(_ROUTERS.glob("*.py")))`, which would simply
    stop matching the wizard handlers and keep passing green — a silent coverage loss.**
    It must become `rglob("*.py")` in the same commit as the move.
- **There is already an AST invariant test for event-loop blocking** —
  `test_event_loop_blocking_batch_b.py:31-67` asserts no `async def` in any router calls a
  member of `_BLOCKING` without `run_in_threadpool`. **`_select_related_zephyr_refs` is not
  in that set**, which is exactly why the 3.8 s block survived adversarial-review batch B:
  the sweep enumerated LLM round-trips and sentence-transformer entry points, and a
  pure-Python 45k-row scan is neither. Adding it to `_BLOCKING` is part of A1, and it
  generalizes the invariant from "don't block on I/O" to "don't block, period".
- **`setup.sh` will NOT upgrade the venv.** `setup.sh:280` reuses an existing `.venv` whose
  Python meets `PY_MIN`; 3.10 passes, so it never recreates. It also rebuilds `ck.db`,
  which must **never** happen (ck.db is the permanent source of truth). Any interpreter
  migration is manual.
- **Dead code confirmed:** `_get_full_zephyr_case` (`:208`) has **zero** call sites.
  `slim_by_key = {}` (`:656`) is never populated, so every `.get()` on it returns `None`
  (leftover from Commit B). `test_id_desc` (`:828`) is assigned and unused in `load_case`.
  `_CASE_KEY_RE` is defined at `:2375` but first used at `:2051` — works (module import
  precedes requests) but reads as a bug.
- **Out of scope, already tracked:** the global mutable `sessions: Dict[str, WizardSession]`
  (`:51`) with no locking. Concurrent-overwrite risk is captured in
  `PLAN-auth-and-case-locking.md`; do not re-raise it here.

---

## Part 0 — Python 3.13 venv ✅ DONE (superseded by commit `032f521`)

> **Resolved, no action needed.** A parallel stream landed
> `032f521 chore(env): move the venv to Python 3.13 to match the testbox, and say why`.
> `.venv/bin/python -V` now reports **3.13.14**. The `.venv313` staging build described
> below was consumed by that cutover and **no longer exists**; there is also **no
> `.venv310-backup`**, so there is no rollback venv — a revert means rebuilding from
> `requirements-dev.txt`. Everything from here down is retained as the rationale record
> only. Post-cutover re-measurement is in the Context section (3.13 column).

The seat gained `/usr/bin/python3.13` (**3.13.14**); `.venv` was on 3.10.12.

**The reload was deliberately built alongside, not in place.** At the time, `lsof` showed
PID 591168 (`uvicorn CK_server.main:app --reload`) with workers holding **mmap'd `.so`
files from `.venv/lib/python3.10/site-packages`** (sklearn, safetensors — the embedding
model), a second uvicorn (PID 524955, port 8991, up 24 days), and a `git push origin main`
in flight. Deleting `.venv` would have broken the next `--reload` re-import.

So: **`.venv313/` was created new; `.venv/` was left untouched.** Built with
`python3.13 -m venv`, then the CPU torch wheel
(`--index-url https://download.pytorch.org/whl/cpu`) followed by
`ask-ck/CK-main/requirements-dev.txt`, mirroring `setup.sh:296-306` **but skipping its
`ck.db` rebuild**. Note pip resolves against the org mirror `pypi.atlnz.lc` by default.

All pinned versions support 3.13 (torch 2.13.0+cpu, numpy 2.2.6, scikit-learn 1.7.2,
scipy 1.15.3, sentence-transformers 5.6.0, sqlite-vec 0.1.9, pydantic 2.13.4).
`.venv313`'s stdlib sqlite3 is 3.37.2 **with** `enable_load_extension` — sqlite-vec's
prerequisite. A 3.10 freeze is preserved at `/tmp/claude-1971/freeze-py310.txt` (56 pkgs);
regenerate with `.venv/bin/pip freeze` if that scratch file is gone.

**Cutover (a deliberate step, when no server is running):**
1. `ps -eo pid,cmd | grep -E "uvicorn|pytest"` — confirm nothing is live on `.venv`.
2. `PYTHONNOUSERSITE=1 .venv313/bin/pytest -q tests` — full suite must be green on 3.13.
3. `mv .venv .venv310-backup && mv .venv313 .venv`
4. `./run.sh --restart`, then `/health` and one real case load.
5. Keep `.venv310-backup` until the suite has been green for a session; then delete.

No `.gitignore` change is needed: Python 3.11+ `venv` writes `.venv313/.gitignore`
containing `*`, so the directory self-ignores (the repo `.gitignore:26-27` only lists
`.venv/` and `venv/`). Verify with `git status --short` after the rename — if
`.venv310-backup/` shows up untracked, it kept its own self-ignore file too; delete rather
than add a pattern.

---

## What A1 taught — read before commit 2

A1 is the only commit in this plan that has actually been executed, so it is the only
evidence about how good the plan's reasoning is. Three corrections that apply to the
remaining ten commits:

1. **"Use the shared implementation instead of the bespoke one" is a hypothesis, not a
   conclusion.** This plan asserted, in Risks, *"expect the change to be an improvement, not a
   regression to defend."* That was **wrong**. Swapping the bespoke Step-2 scorer for
   `db.search_zephyr` silently dropped the best cross-ref for the Generator's flagship case
   type out of the results entirely. The bespoke code was worse on average AND better in a
   specific way that mattered, and only measurement found it. **Every remaining commit that
   consolidates two implementations into one needs a before/after comparison on real data, not
   a green test suite.** Part B commits 7-9 are all of that shape.

2. **"Mechanical, no behaviour change" is a claim to verify, not to assert.** Part B's commits
   are described as "import-only motion". A1's supposedly-mechanical query builder introduced
   two real behaviour changes (leaking analyst prose into ranking; double-filtering that
   starved a downstream tier). Neither was caught by the 295-test suite — both needed
   hand-inspection of actual output. Budget for that on each extraction.

3. **Widening an invariant finds bugs; expect them and keep them separate.** Adding three names
   to `_BLOCKING` immediately surfaced a genuine pre-existing offender in a file this plan
   never mentioned (`pytest_create.pt_cases`). It shipped as its own commit, `0c06586`, before
   A1 — the pattern to repeat. Related: a `lambda` passed to `run_in_threadpool` satisfies the
   runtime requirement while hiding the call from that AST check. **Always dispatch a named
   function.** Two helpers exist for this now: `wizard._cases_index`, `pytest_create._pt_cases_index`.

A fourth, smaller one: **A1 came in far larger than planned** (10 files, +972/−261, spanning
backend, frontend, and two new test suites, versus "delete the scan and call the existing
function"). The estimates for commits 2-11 should be read as lower bounds.

## Part A — perf + correctness (independent of the split; do first)

Individually testable, no file *moves* (A1 does delete ~160 lines and touches the frontend).
**Land these before touching structure** so Part B stays a pure no-behaviour-change refactor.

### A1. Defer all three data steps off case load ✅ SHIPPED as `4578030` (+ `0c06586`)

> **Done, gated, pushed.** `4578030` — 10 files, +972/−261. The pre-existing `pt_cases`
> blocker that widening `_BLOCKING` exposed shipped first as `0c06586`, verified green in an
> isolated worktree so the split is bisectable. Gate at the staged state: guards OK,
> 295 pytest, 85 Vitest; Playwright 15/15 (14 new + the golden path).
>
> **Result: step 2 went 2708 ms → 175 ms mean (15×), and all three steps together are
> ~235 ms — none of it at case load, none of it on the event loop.** Confirmed on the live
> server: `/health` answers in 3-215 ms while a step-2 fetch is in flight.
>
> Both new test suites were **mutation-checked** rather than assumed: removing the fetch-once
> memo fails 3 tests, removing the search-clobber guard fails 1.
>
> | | before | after |
> |---|---|---|
> | step 1 TestLink | ~0 ms (at load) | 16 ms (on open) |
> | step 2 Zephyr | **2708 ms, event loop, every load** | 175 ms mean / 716 ms max (on open) |
> | step 3 ATP | ~440 ms (at load, hybrid) | 44 ms (on open, keyword) |
>
> Step 2 cold-start is 1693 ms on the broadest query (cold `zephyr_fts` page cache),
> settling to ~280 ms; the frontend memoizes per `(case, step)`, so that is paid at most
> once per case per step and never on load.
>
> **Three things were learned that the plan had wrong — all now fixed in the code:**
>
> 1. **A naive swap REGRESSED the flagship case.** For `AWPTCM-T33233 "Port - Auto
>    Negotiation"`, both "port" and "auto" are in `_ZREF_GENERIC_TOKENS`, so `rank_words`
>    collapsed to `["negotiation"]`, all 12 matches scored an identical **0.7683**, and
>    ordering fell back to key order. The best cross-ref (`interface: port status, speed,
>    duplex and negotiation`) landed **9th and fell out of the top 8** — replaced by
>    *"Test modem support. TPS says Japan only"* and *"ROCO-22 Switch containers to the
>    upstream kernel"*. The retired scorer ranked it **1st**, via `area_support`:
>    `12.0 (negotiation) + 8.0 (area "port") + 0.8 = 20.3` vs `12.8` for the rest.
>    **So the plan's "expect an improvement, not a regression to defend" was wrong.**
>    Fix — the load-bearing heuristic the plan anticipated, ported to shared code as it
>    prescribed: `db._relevance_score` gained an **opt-in `area_words` third tier**
>    (`db._AREA_WORDS`), contributing at 0.35 weight and **only when specific overlap is
>    thin (`len(matched) <= 1`)** — precisely when results degenerate into a big tie.
>    It defaults to `()`, and only `search_zephyr` opts in, so `search_testlink` /
>    `search_atp` / `search_scripts` are **provably bit-for-bit unchanged** (verified:
>    1 call site, and `_relevance_score(...) == _relevance_score(..., area_words=())`).
>    `search_zephyr_hybrid` delegates to `search_zephyr`, so both modes agree.
>    Result: the good ref is **rank 1 at 0.8103**, cleanly above the 0.7683 tie.
>
> 2. **Hybrid is the wrong default for a panel-open view.** `_search_zephyr_external`
>    defaults to hybrid when `db.HAS_VEC`, which runs sentence-transformer inference.
>    Measured warm: step 2 **763 ms mean / 2692 ms max** — *no better than the 2.7 s scan
>    being deleted* — plus a ~11.8 s cold model construction that would land on a plain
>    panel open. Keyword is 8× faster for step 2, 20× for step 3. So the step builders
>    pin `_STEP_SEARCH_MODE = "keyword"`; hybrid stays the default for `/search_zephyr`
>    and `/search_atp`, i.e. for a query the user actually typed. (This also changed
>    step 3, which was implicitly hybrid at load — in scope, since uniformity is the goal.)
>
> 3. **Two query-construction bugs, both mine.**
>    - *Process prose leaked into ranking.* `_build_zephyr_query` fed the decision
>      rationale in raw, so `"Auto/Auto negotiation; Zephyr says covered by auto-test"`
>      injected `zephyr says covered` and FTS ranked *"TPS **says** Japan only"* as a top
>      cross-ref. But the rationale must NOT be dropped wholesale — it is what moves the
>      QoS case's best ref from rank 20 → 4 ("cos map queues") and the DHCPv6 case's from
>      143 → 3 ("range"). Fix: `_DECISION_META_TOKENS` strips only the coverage-status
>      vocabulary (`zephyr/says/covered/suite/tbd/…`), keeping the feature words.
>    - *Double filtering broke the new area tier.* The builder stripped
>      `_ZREF_GENERIC_TOKENS` before db saw the query, so "port" never arrived and the
>      area tier could not fire. Fix + the rule going forward: **wizard decides which
>      TEXT is relevant; db decides how to WEIGHT it.** The builder no longer pre-strips
>      generics.
>
> **Verified end state:** 4/4 hand-picked best cross-refs in top-8 (was 2/4 mid-fix);
> tie concentration **81% → 59%**; all error paths correct (400 on step 0/4/99, 404 on
> unknown key); `load_case` returns only `{session, case_title, message}`.
> Baselines: `/tmp/claude-1971/step2-ranking-{baseline,after}.json`.

#### Original plan (retained for rationale)

> **Directive:** all three data steps must behave identically at startup — no expensive work
> at case load; each step fetches its own data when the user navigates to it. *"Unless there's
> an explicit advantage, I don't see why they should be doing anything different from each
> other (besides getting different sets of data)."*

**Correction to the record, verified before planning this** — the belief that Zephyr is
already deferred is not what the code does:
- `goToPanel`/`goToStep` (`static/js/nav.js:64,102`) do **no fetching**; they show/hide DOM.
- All three datasets arrive in the single `POST /load_case` response
  (`static/js/generator.js:27`, assigned at `:45-47`). **Nothing is deferred today.**
- The ~60 s LLM prefetch that *was* removed was **ATP's** `analyze_atp_coverage`, not
  Zephyr's (`wizard.py:815-821`). A stale leftover still says so:
  `static/js/generator.js:71` — `// load_case may run analyze_atp_coverage (LLM) — footer
  only`. **Delete that comment as part of this commit.**
- So Zephyr is the *only* step still doing heavy work at load. "Do what Zephyr does" would
  adopt the slowest path; the directive's intent is the opposite — defer all three.

**Target state.** `load_case` returns session + `case_title` only. Each step's initial
candidate payload is fetched on first navigation to that panel and cached client-side.

Backend — the three endpoints needed already exist or are trivial:
| Step | On-navigation source | Status |
|---|---|---|
| 1 TestLink | `candidates_dict[key]` + `_build_testlink_description` (currently `wizard.py:798-810`) | new thin endpoint, e.g. `GET /step_candidates/{key}/1` |
| 2 Zephyr | `_search_zephyr_external(query, …)` — FTS + shared scorer | **already exists** (`:1082`), already threadpooled at `:1130` |
| 3 ATP | `_get_atp_candidates(_build_atp_query(…), …)` | **already exists** (`:1180`), already threadpooled |

Prefer **one** endpoint shaped `GET /step_candidates/{key}/{step}` over three bespoke ones —
uniform behaviour is the whole point of the directive, and one handler makes the symmetry
structural rather than a convention three call sites have to remember.

For Step 2's query, preserve the signal the retired scorer used: case title + the primary
decision rationale (`sess.primary['w']` / `data['decisions'][key]['w']`) + Step-1 selection
titles. `suggest_zephyr:1389-1395` already builds exactly this — reuse it, don't re-derive.

**Then delete the Step-2 scan cluster** (single entry point, so all of it is dead):
`_select_related_zephyr_refs` (685-756), `_score_zephyr_candidate` (462-555),
`_ZREF_WEAK_ALONE` (431), `_ZREF_GENERIC_TOKENS` (407-428, the duplicate of `db.py:123`),
`_normalize_zephyr_text`/`_zephyr_tokens`/`_specific_tokens` (437-459) **if** nothing else
uses them — `_build_atp_query:1148` currently does, so keep those three and move them to
`descriptions.py` in Part B. **Correction (A4):** only TWO survived. `_build_atp_query`
filters generics inline and needs an ORDER-PRESERVING list for its `[:24]` slice, which
the set-returning `_specific_tokens` could not supply — so nothing called it and A4
deleted it. `descriptions.py` gets `_normalize_zephyr_text` + `_zephyr_tokens` only. Also delete `db.iter_zephyr_slim` (`db.py:313`, 1 caller).
**~150 lines from wizard.py + 11 from db.py.**

Frontend (`static/js/`): `nav.js` gains a per-panel first-visit fetch hook; `generator.js`
stops reading `testlink_candidates`/`zephyr_refs`/`atp_candidates` from the load response.
There is a Vitest/jsdom layer in `js-tests/` — add coverage for the fetch-once-then-cache
behaviour there.

Fold in: wrap `_refined_complete_keys()` (`:928`, 15 ms `rglob` on the loop in `/cases`).

**Add `_select_related_zephyr_refs` and `_refined_complete_keys` to `_BLOCKING` in
`tests/test_event_loop_blocking_batch_b.py:31-37`.** The existing AST test then catches the
next pure-CPU offender, which the current LLM/embedding-only list cannot. (`_select_related…`
is being deleted, but list it anyway — it costs nothing and pins the name against revival.)

**Scope note:** this is no longer a one-line unblock. It spans `wizard.py`, `db.py`,
`static/js/{nav,generator}.js` and `js-tests/`. Ship it as its own commit, ahead of A2, and
verify with checklist items 1-3 below. **A1b (the SQL prefilter) is removed from the plan** —
`db.search_zephyr` already *is* the FTS prefilter it was going to build.

### A2. Stop reloading data per request ✅ SHIPPED

> **Done.** `get_data` now serves `request.app.state.app_data`, matching
> `pytest_create._data`. Two deviations from the plan below, both deliberate:
> - **11 `Depends(get_data)` sites, not 10** — A1's `step_candidates` added one.
> - **No `load_all_data()` fallback.** The plan suggested `or load_all_data()`; the house
>   pattern (`pytest_create._data`) instead raises **503**, and that is better: a silent
>   fallback would restore the per-request cost invisibly *and* mask a boot failure. Verified
>   safe — `conftest.py:32` uses the `with TestClient(...)` form, so startup fires in tests.
>
> Also removed the now-dead `from data import load_all_data` import.
>
> Verified rather than assumed: `app_data` is one shared object across requests; **5 requests
> emit 0 chars of stdout** (was 3 lines each — the "Loading lightweight references…" noise);
> a missing `app_data` yields a clean `503 Server data not loaded yet.`, not a 500; live
> reloaded server serves all four sampled endpoints 200. +7 tests
> (`tests/test_app_data_dependency.py`), **mutation-checked**: reverting to a per-request
> rebuild with a silent fallback fails 4 of them.

#### Original plan (retained for rationale) — `wizard.py:402-404`

```python
def get_data(request: Request):
    return request.app.state.app_data
```

Matches `pytest_create.py:583`. Kills 70 ms × 10 endpoints, the per-request stdout spam,
and the snapshot inconsistency. **Check first:** `tests/conftest.py` may construct the app
without running the startup event — if `app_data` is `None` under TestClient, either keep a
`or load_all_data()` fallback or have conftest populate `app.state.app_data`. Verify before
assuming.

### A3. Make `confirm_step` reject bad input — `wizard.py:1457-1482`

Replace the three `except Exception: pass` blocks with a 400. Collapse the three
near-identical step branches into one loop over `(step, state)` while there — the only real
differences are step 3's `art_string` handling and step 1's `none_selected`.

Then audit the other 4 silent swallows; the ones that corrupt state are these three.

### A4 + A5. ✅ DONE — logging, dead code, pydantic v2

Shipped together as commit 4. **Three items in the original list below were wrong.** They
are kept verbatim, struck through, with what was actually true — the lesson is that this
document's line refs and dead-code claims were written from a read-through, and a
read-through cannot tell a dead helper from a live one.

- ~~9× `datetime.utcnow()`~~ → **7 sites, DEFERRED to commit 5** as planned (see Risks).
- ~~Collapse the 13× `.dict()`/`model_dump()` hedge to `model_dump()`.~~ **19 sites, in
  3 files** (`wizard.py` 14, `pytest_create.py` 3, `models.py` 2), and the diagnosis was
  wrong in an important way: the hedge is not merely verbose, it is **inverted**. On
  pydantic v2 `BaseModel.dict()` still exists as a deprecated alias, so
  `hasattr(obj, "dict")` is always True and **every site took the v1 path** — the `else`
  branches were unreachable. Fixed with one shared `models.model_to_dict`, which tries
  `model_dump` first and keeps `.dict()` as a genuine last-resort v1 fallback.
  ⚠️ Deleting that fallback outright broke `safe_session_dict`'s llm_config **redaction**
  for `.dict()`-only objects; `tests/test_security_fixes.py` caught it.
- ~~Delete `_get_full_zephyr_case` (`:208`), `slim_by_key` (`:656`), `test_id_desc` (`:828`).~~
  **`slim_by_key` and `test_id_desc` are LIVE local variables, not dead code** — deleting
  them would have broken Step 2 enrichment and ATP descriptions. The real dead set, found
  by AST scan rather than reading:
  `_get_full_zephyr_case`, `_session_objectives_confirmed`, `_session_test_script`,
  `_specific_tokens` (wizard) + `_score_script_candidate` (pytest_create).
- ~~Move `_CASE_KEY_RE` (`:2375`) to the top of the module.~~ Done (it sat *below* the two
  handlers it guards; legal, but read as a forward reference).
- Normalize `confirmed_at` → **DROPPED with commit 6.** Two reasons: `step4/step5.confirmed_at`
  has **zero readers**, and unifying on `UtcDatetime` would change the published
  `*-session.json` twice over (offset added AND the `T` separator lost).

**A5 (`print()` → `logging`): 14 sites in wizard.py, not 18.** All converted, with levels
matched to consequence rather than uniformly `warning`:
- `_persist_session` failure → **`log.error(..., exc_info=True)`**. A swallowed failure
  there loses the user's confirmed selections while the handler still returns 200 — the
  wizard-side twin of the stale-thread-local-connection bug. It was a `print("Warning:")`.
- Jinja render failure and `_load_persisted` failure also carry `exc_info=True`: both
  silently degrade, and only the traceback names the template line / offending field.
- Routine bookkeeping (`cleared persisted session`, `[export] Saved …`) → `log.info`.

**The non-obvious part of A5**: there was **no logging configuration anywhere in the
codebase**, so the root logger sat at `WARNING` and converting a `print()` to `log.info()`
would have **silently deleted** operator-visible output (notably `[export] Saved drop-in
bundle to …`). Commit 4 therefore also adds `logging.basicConfig(level=CK_LOG_LEVEL or
INFO, …, force=True)` to `main.py`. `force=True` matters because uvicorn installs its own
root handlers — without it the format depends on which ran first.

**Still on `print()` (not in scope for A4, follow-up):** `llm.py` 24, `pytest_create.py` 8,
`main.py` 4, `data.py` 4, `db.py` 3, `pt_exec.py` 2, `llm_debug.py` 2.

**Found while scanning, fixed here:** `pytest_create._score_script_candidate` was a full
copy of `db._score_script_candidate` that referenced `_PT_GENERIC_TOKENS` /
`_PT_AREA_SUPPORT` — names defined **only in `db.py`**. It raised `NameError` on any call
and nothing reached it. The comment directly above it already claimed the scorer lived in
db with "no private copy here". Deleted, and the comment now says what is true.

**New invariant test** (`tests/test_pydantic_v2_and_logging.py`, 29 tests, all 10
mutations verified red): no `.dict()` call sites; `model_dump` preferred over `.dict()`;
secrets still redacted; no `print()` in wizard.py; lost writes logged at ERROR with a
traceback; `main.py` configures logging with `force=True`; the five deleted helpers stay
deleted; **and no unreferenced private module-level function in either router** — the
generalization of this commit's four deletions, which is what would have caught them
without a manual scan. Opt out per-helper with `# keep: <reason>` on the line above.

---

## Part B — the module split

> ⚠ **Names in the tables below are as-planned, not as-shipped.** `CK_server/wizard/…`
> became **`CK_server/generator/…`** in `03a0aac`, and every extracted helper lost its
> underscore (a name another module imports is not private). The tables are kept as the
> record of what was planned; see *Part B — as executed* for what actually landed.

Extract in dependency order, **leaves first**. The first three modules land at package
root (`CK_server/`), *not* in `routers/` — that is what actually fixes the
`pytest_create → wizard` coupling.

| New file | wizard.py lines | Contents | Notes |
|---|---|---|---|
| `CK_server/llm_config.py` | 93-173, 1288-1300 | `_llm_is_active`, `_same_backend`, `_load_global_llm`, `_save_global_llm`, `_apply_workspace_llm_if_needed`, `_preview_from` | **Kills 3 of the 6 pytest_create imports.** Drop the `_` prefixes — these are public API now. `pytest_create._apply_workspace_llm` (`:280`) collapses into the shared one |
| `CK_server/case_registry.py` | 53-80, 867-910, 1190-1210, 2374-2375 | `HIDDEN_CASE_KEYS`, `HIDDEN_CASE_FOLDERS`, `_is_hidden_case`, `_refined_complete_keys`, `_session_progress_map`, `_build_case_groups`, `_get_refined_group`, `_CASE_KEY_RE`, `_refined_payload_path` (324-334) | **Kills the other 3.** After this, `pytest_create` imports nothing from `routers.wizard` |
| `CK_server/session_store.py` | 50-51, 176-230 | the `sessions` dict, `_persist_session`, `_load_persisted`, `_clear_persisted`, `_mark_updated`, `_authoritative_session` (1736-1743) | Generic over `kind='wizard'\|'pt'` — `db.py` already is. Where per-case locking lands later (`PLAN-auth-and-case-locking.md`) |
| ~~`CK_server/wizard/scoring.py`~~ | ~~407-555~~ | **CANCELLED by A1** — `_score_zephyr_candidate`, `_ZREF_WEAK_ALONE` and the duplicate `_ZREF_GENERIC_TOKENS` are *deleted*, not extracted. Only **two** tokenizers survive (`_normalize_zephyr_text`, `_zephyr_tokens`) because `_build_atp_query` still uses them → they go to `descriptions.py`. `_specific_tokens` was deleted by A4 (unreferenced; wrong return type for its only would-be caller) | A1 turns this from "move 150 lines" into "delete 150 lines". Strictly better |
| `CK_server/wizard/descriptions.py` | 437-459, 558-682, 1135-1187 | the two surviving tokenizers, `_build_testlink_description`, `_build_zephyr_case_description`, `_enrich_zephyr_rows`, `_build_atp_query`, `_split_atp_title_description`, `_get_atp_candidates`, `_hybrid_on` (1060-1064) | Pure. `_get_atp_candidates`/`_hybrid_on` are thin db wrappers — fine here. **Now the first extraction**, since scoring.py is gone |
| `CK_server/wizard/gates.py` | 225-321 | `_can_synthesize`, `_session_objective`, `_session_has_objective`, `_can_synthesize_steps`, `_selection_fingerprint`, `_invalidate_downstream`, `_migrate_legacy_step4_to_step5` | The state machine. Pure predicates over a session — unit-testable, currently not. **Two fewer than planned:** `_session_objectives_confirmed` and `_session_test_script` were deleted in commit 4 (born unused in `05b194a`, never called). Do not re-add them here |
| `CK_server/wizard/backfill.py` | 337-399 | `_backfill_from_refined` | Depends on `case_registry._refined_payload_path` |

Then the routes, `routers/wizard.py` → `routers/wizard/`:

| New file | wizard.py lines | Endpoints |
|---|---|---|
| `routers/wizard/reviews.py` | 759-1132, 1213-1270, 1303-1513 | `load_case`, `get_cases`, `search_atp`, `search_testlink`, `search_zephyr`, `suggest_atp`, `suggest_testlink`, `suggest_zephyr`, `confirm_step`, + `_select_related_zephyr_refs` (685-756), `_search_testlink`, `_search_zephyr_external` |
| `routers/wizard/synthesis.py` | 1725-2021 | `synthesize_objectives`, `save_objective`, `confirm_objectives`, `save_steps`, `synthesize_steps`, `synthesize`, + `_session_key_from_req` |
| `routers/wizard/export.py` | 2023-2440 | `export`, `push_to_zephyr` |
| `routers/wizard/config.py` | 1516-1723 | `clear_session`, `claude_cli_status`, `grok_cli_status`, `get_llm_config`, `llm_health`, `set_llm_config` |
| `routers/wizard/__init__.py` | 48, 82-90, 402-404 | `router = APIRouter()`, includes the four sub-routers, `get_data`, `OUTPUTS_ENV`, **plus back-compat re-exports for the 7 test files** |

Routers land at ~300-500 lines each.

**`export()` is ~350 lines in one function** (`:2023-2371`) — gating, an LLM call, payload
assembly, validation, Jinja templating, staged atomic writes. Break it up **within
`export.py`**, as a separate commit after the move: `_build_payload`, `_render_traceability`,
`_write_bundle`. Do not attempt it during the move.

---

## Commit staging

Each commit is independently revertable and leaves the suite green.

**All of Part A and Part B are in scope** (user decision, 2026-07-28: *"I think we should be
doing all the commits suggested in A and B. Improving this code flow is important."*).

**Part A (do first, in order):**
- **0. ✅ `0c06586` `fix(pytest-create): pt_cases blocked the event loop on two reads`** — not
  in the original plan; surfaced by A1 widening `_BLOCKING`, shipped ahead of it so each commit
  stays green on its own.
1. **✅ `4578030` `perf(generator): defer all three data steps off case load`** — A1. Came in at
   10 files / +972-261, well beyond the "delete the scan" estimate; see *What A1 taught*.
2. **✅ `perf(wizard): serve app.state.app_data instead of reloading per request`** — A2.
3. **✅ `fix(wizard): confirm_step silently dropped malformed selections`** — A3. Shipped with
   `_parse_selections` (validates before mutating; 400 naming index + field), the three
   near-identical branches collapsed to one path, and the invalid-step guard moved to the top.
   +25 tests, mutation-checked (accepting a partial payload fails 7). **Original notes:**
   Targets `wizard.py:1459/1468/1476` (three `except Exception: pass` blocks that drop the
   whole selection list, then set `confirmed = True` and report `can_synthesize: true`).
   Collapse the three near-identical step branches while there; the only real differences are
   step 3's `art_string` handling and step 1's `none_selected`.
4. `chore(wizard): logging, dead code, pydantic v2` — A5 + the non-`utcnow` half of A4.
5. **✅ `fix: tz-aware UTC timestamps`** — A4's `utcnow` half. **21 sites across 5 files**
   (wizard 7, pytest_create 10, db 1, pt_exec 3), not the 9 the plan estimated; `tool/`
   deliberately excluded (build scripts, and ck.db is built once and never rebuilt).
   The `TypeError` the plan predicted **did fire** — `test_persist_stamps_updated_at` went
   red on the first attempt. Fixed at the MODEL boundary rather than per comparison: a new
   `models.UtcDatetime` (`BeforeValidator`) coerces every stored stamp to aware UTC on
   validation, so a session loaded from a pre-cutover row cannot carry a naive value and
   no comparison anywhere can raise. New `CK_server/timeutil.py` holds `utc_now()` +
   `as_utc()`. Naive stamps are read as UTC — reading them as local would silently shift
   every pre-cutover timestamp by the seat's offset (UTC+12 here).
   **Scope claim corrected by measurement:** `_pt_get`'s anti-clobber check was switched
   from a string compare to a parsed one, but enumeration over the 8 shapes the
   `sessions.updated_at` column can hold shows string and parsed comparison **agree
   everywhere once the cached stamp is coerced** — so that half is defence-in-depth, not a
   bug fix, and the commit message and docstrings say so. Drop the coercion and exactly one
   case diverges (spurious reload every request). +38 tests; 4 of 6 mutations red, and the
   2 that stayed green revealed a genuinely UNREACHABLE branch (pydantic resolves `None` on
   the `Optional` union before the annotated validator runs) which was then deleted.
6. ~~`refactor(models): type step4/step5`~~ — **🚫 DROPPED. User decision, 2026-07-28.
   Do not re-raise this.** Full evidence: `ask-ck/ck-facelift/SURVEY-step4-step5.md`
   (21-agent survey; 11 of 13 hazards survived adversarial verification, 4 blockers).

   **Why it was dropped — the commit had no remaining purpose:**
   - Its stated goal was normalizing `confirmed_at`, and **`step4/step5.confirmed_at` has
     ZERO readers** — 6 write sites (`wizard.py:298, 1855, 1901, 1906, 1931, 2075`), no
     Python reader, no JS reader. The whole motivation was a field nothing consumes.
   - `provenance` is inert and stays a dict (see below), so there was nothing to model there.
   - `testScript` is **350/350 uniform** in real data, so validation would catch nothing that
     has ever occurred.
   - What remained was editor completion and typo-safety.

   **Why it was actively dangerous — verified, not argued:**
   - **17 `isinstance(..., dict)` guards** on these fields. A pydantic model is not a dict, so
     every one silently takes its `else` branch. Worst: `wizard.py:2241` makes **export write
     the placeholder `"<ul><li>Objective not yet synthesized</li></ul>"` into the published
     bundle**; `wizard.py:2219-2220` empties the exported testScript; `wizard.py:296-348`
     kills the invalidation cascade and the Step-5 gate; `db.py:1024-1035` makes the case
     list report nothing done.
   - **The `stale` key is invisible to any data census.** Written `wizard.py:298,303`, popped
     at `:1897, 1934, 1963, 2034`, read ONLY by `generator.js:163,185`. It is **0 of 35** in
     ck.db and **0 of 2** on disk because it is transient — so no survey of stored data can
     see it, including the ck.db census above. Default `extra='ignore'` drops it, killing the
     stale badge that `generator.js:158-161` documents as the guard that stops a contradictory
     bundle reaching export.
   - **FALSE GREEN: the whole 393-test suite passes with these fields typed.** No test can
     see any of the above. This is the real reason the commit was not attempted on judgement.
   - `_backfill_from_refined` would re-fire on every `/load_case` for all 43 Complete cases
     and clobber the session's objective/confirmed_at/provenance.
   - `PtSession.step4/step5` (`models.py:183,184`) hold a **completely different live shape**
     under the same names — one shared model drops 8 keys; `extra='forbid'` fails to load all
     3 pt sessions.

   **Ancillary conclusions worth keeping (these stand independently of the drop):**
   - **`provenance` must stay `Dict[str, Any]`.** It is inert: all 14 sites in `wizard.py` are
     WRITES, zero Python reads any key, no template touches it. Only `provenance.js:89` and
     the `pytest.js` panels read it, purely to DISPLAY (the paste-into-another-LLM feature),
     plus `pytest_create.py:1961` `bool(content.get("provenance"))` — presence-only,
     PtSession-only. *(User: "why do we actually care about it at all? it's a non-functional
     set of data… a blackhole." Correct.)* On-disk proves it is multi-generational: T33373
     carries a 10-key legacy combined shape, T33233 a 4-key one, and current code emits
     `objective_used` which appears in 0 of 35 rows. Persisted provenance is neither a subset
     nor a superset of what the code can produce — do not try to model it.
   - **`REFINED_DIR` is `ask-ck/objective-drafting/refined-cases/`**, NOT `ask-ck/refined-cases/`.
     43 `zephyr_payload.json` + only 2 `*-session.json`. `_backfill_from_refined`
     (`wizard.py:375-380`) copies `testScript` verbatim from the payloads, so **those 43 files
     — not the 9 non-empty sessions — are the step-shape contract**: wrapper keyed by
     `AWPTCM-Txxxx` 43/43, inner keys exactly `{objective, testScript}` 43/43, `testScript`
     keys exactly `{type, steps}` 43/43, **276/276 steps exactly
     `{description, expectedResult}`** (3-15 each). With ck.db's 74 that is 350/350.
   - `confirmed_at` normalization stays dropped for the same reason (zero readers), and
     because unifying on `UtcDatetime` would change the published `*-session.json` twice over
     — adding the offset AND losing the `T` separator.
   - Pydantic 2.13.4 facts, executed: raw-dict assignment is **not** validated (so typing is
     cosmetic across 19 assignment sites); `validate_assignment=True` then breaks **13**
     in-place mutation sites with `TypeError: does not support item assignment`;
     `extra='ignore'` silently drops undeclared keys; `model_dump` fills defaults, which
     changes the browser JSON and the exported artefact.

   **Superseded scope notes from before the drop, kept for context:**

   Measured from `ck.db` (read-only, 35 wizard sessions):

   | | step4 | step5 |
   |---|---|---|
   | present | 35 | 10 |
   | **non-empty** | **7** | **5** |

   ```
   step4:  objective 7(str) | provenance 6(dict) | confirmed 5(bool)
           confirmed_at 4(str x3, null x1) | testScript 4(dict x3, null x1) | backfilled 1(bool)
   step5:  testScript 5(dict) | provenance 1(dict) | confirmed 1(bool) | backfilled 1(bool)
   ```

   **`provenance` STAYS `Dict[str, Any]` — do not model it.** It looks like the hard case
   (13 sparse, partly-nullable keys) and it is the opposite: it is **inert**. All 14
   `provenance` sites in `wizard.py` are WRITES; there are **zero** reads of any provenance
   key in Python, and no Jinja template touches it. The only reads anywhere are
   `static/js/provenance.js:89` and the `pytest.js` panels, which merely DISPLAY it (the
   paste-into-another-LLM feature), plus `pytest_create.py:1961`
   `bool(content.get("provenance"))` — presence-only, PtSession-only. Nothing branches on
   its contents, so its irregularity costs nothing, and a `Dict[str, Any]` field preserves
   whatever keys arrive. Modelling it would buy nothing and risk silently dropping keys the
   provenance panel displays. *(User called this out directly: "why do we actually care
   about it at all? it's a non-functional set of data… a blackhole." Correct.)*

   **Type these instead** — small and regular: `objective` (str), `confirmed` (bool),
   `backfilled` (bool), `testScript`. `testScript` is the tightest of all: 74/74 step
   entries across 8 testScripts are exactly `{description, expectedResult}`, so
   `{type: str, steps: [TestStep]}` is safe. Note `step4.testScript` is **nullable**
   (1 row holds null) — it is the legacy location, `step5` is current.

   **`confirmed_at` is a BEHAVIOUR change, not a typing change — split it out.** step1-3
   use a real aware `datetime` (`models.UtcDatetime`, added in commit 5) while step4/step5
   hold a naive **string in two different formats**, both present in live data:
   `'2026-07-15T00:42:37.575327'` (T) and `'2026-07-13 03:11:37.604091'` (space — this is
   what `json.dumps(default=str)` writes). Unifying on `UtcDatetime` makes them serialize
   as `+00:00`, which flows into the exported `*-session.json`. That is a data-format change
   to a published artefact and does not belong in "add types".

   **The on-disk population is the real shape contract, and it is airtight.**
   `REFINED_DIR` is `ask-ck/objective-drafting/refined-cases/` (NOT `ask-ck/refined-cases/`).
   It holds **43 `zephyr_payload.json`** plus only **2 `*-session.json`** (T33233, T33373).
   `_backfill_from_refined` (`wizard.py:375-380`) copies `testScript` **verbatim** out of
   `zephyr_payload.json` into `sess.step5`, so those 43 files — not the 9 sessions — define
   the shape. Measured across all 43: wrapper keyed by `AWPTCM-Txxxx` 43/43; inner keys
   exactly `{objective, testScript}` 43/43; `objective` non-empty 43/43; `testScript` a dict
   43/43 with keys exactly `{type, steps}`; **276/276 step entries exactly
   `{description, expectedResult}`**, 3-15 steps each. With ck.db's 74 that is
   **350/350 uniform** — `TestScript`/`TestStep` can be typed tightly with real confidence.

   🛑 **BUT: typing these fields is NOT a typing change. Executed on pydantic 2.13.4:**

   | fact | result |
   |---|---|
   | `s.step4 = {"objective": "x", "junk": 1}` (default config) | stays a **plain dict** — `type after assign: dict` |
   | same, with `validate_assignment=True` | becomes `Step4`; `junk` **dropped** |
   | `model.step4["confirmed"] = True` | `TypeError: 'Step4' object does not support item assignment` |
   | `extra='ignore'` (the default) on an undeclared key | **silently dropped** → data loss on re-persist |
   | `extra='allow'` | preserved |
   | `model_dump()` of `{"objective": "o"}` | `{"objective": "o", "confirmed": False}` — absent keys become explicit defaults |

   Consequences, counted:
   - **19 raw-dict assignments** to `step4`/`step5` (17 in `wizard.py` — `:298, 303, 314,
     375, 380, 1851, 1907, 1935, 1964, 1968, 2006, 2025, 2035, 2070, 2077` — plus
     `pytest_create.py:2417, 2445`). Because pydantic v2 does not validate on assignment,
     **the typing is cosmetic unless `validate_assignment=True`**.
   - Turn that on and the **13 in-place mutation sites break** with `TypeError`:
     `wizard.py:1894, 1900, 1901, 1905, 1906, 1927, 1930, 1931, 1961, 1967, 2005, 2031, 2032`.
     The prevailing idiom is `s4 = stored.step4 or {}` → mutate → `stored.step4 = s4`; every
     one of those needs rewriting to model construction or `model_copy(update=...)`.
   - `model_dump` gaining explicit defaults changes the JSON the browser sees **and** the
     exported `*-session.json`.

   **So commit 6 as originally specified was a ~32-site refactor plus a serialization change
   to a published artefact — not "add types".** Two options were put to the user: drop it, or
   reduce it to `TestScript`/`TestStep` as validators at the backfill boundary.
   **The user chose: drop, with no boundary validator** (2026-07-28). The backfill path keeps
   copying `testScript` verbatim from `zephyr_payload.json`, which is acceptable because all
   43 payloads are uniform and the server writes them itself — but note it is an unvalidated
   read of on-disk JSON, so it is the place to look first if a malformed bundle ever appears.

**Part B (leaves first — each is import-only motion, no logic change):**
7. ✅ `591dbb9` `refactor: extract wizard/descriptions.py` (pure; add unit tests in the same
   commit). Now the first extraction — A1 deleted what used to be commit 5's `scoring.py`.
8. ✅ `104d3e6` `refactor: extract llm_config.py + case_registry.py; drop pytest_create's
   wizard imports` — the coupling fix, and the highest-value commit in Part B. Verify with
   `grep -rn "from routers.wizard import" --include=*.py .` → only `main.py` and tests.
   **Holds as of 2026-07-28f.**
9. ✅ `e15c360` `refactor: extract session_store.py + wizard/{gates,backfill}.py`.
10. ✅ **DONE (2026-07-29).** `refactor: split routers/wizard.py into routers/wizard/` — the
    atomic move. Bodies moved byte-identical; the hardcoded `wizard.py` path reads now resolve
    through `tests/_wizard_src.py` (see *Commit 10 — what it now faces*).
11. ✅ `77ab960` `refactor: decompose export()` — done BEFORE 10, not after; see the status
    header. Six named steps + a 115-line orchestrator, verified byte-identical to HEAD
    through the write path.

### Part B — as executed (corrections the commits themselves produced)

Each extraction found something the plan did not anticipate. Recorded here because the
pattern is the point: *the tests that broke were more informative than the ones that passed.*

- **Two duplicate definitions were retired into `db`, not carried into the new module**
  (commit 7). `_ZREF_GENERIC_TOKENS` was byte-identical in `db.py` and `wizard.py` — as the
  plan predicted — but `_split_atp_title_description` ALSO existed twice, which the plan did
  not mention; `db.py`'s copy was labelled "Verbatim from wizard.py" and was proven
  structurally identical. Both now live in `db` (the leaf, and `search_atp` calls one of
  them itself), as `db.GENERIC_TOKENS` / `db.split_atp_title_description`.
- **Public names, not underscore-private ones.** The plan says this only for `llm_config`;
  it applies everywhere. A name another module imports is not private, and cross-module
  imports of underscore-privates are the defect Part B exists to remove.
- **That rename has a trap, and it is the sharpest thing in commit 7.**
  `tests/test_event_loop_blocking_batch_b.py` matches an unwrapped blocking call by
  `ast.Name`, so `from generator import descriptions` + `descriptions.get_atp_candidates(…)`
  would satisfy the invariant **without being covered by it** — the suite stays green while a
  handler silently loses its threadpool guarantee. Three defences now: routers import the
  names directly, `_BLOCKING` lists old and new spellings, and
  `test_blocking_helpers_are_imported_by_name` fails on any attribute-style call.
- **Module-level constants are bound per importing module** (commit 8). Three tests in
  `test_export_authority_batch_a.py` patched `wizard.REFINED_DIR` while the reader had moved
  to `case_registry`. Two went red; the third **kept passing for the wrong reason** — its key
  has no bundle in the real tree either, so "backfill did nothing" was true whether or not
  the redirect worked, while it silently read the production `refined-cases/`. One
  `_redirect_refined_dir` helper now patches every binding, and that test asserts the
  redirect is in force before drawing a conclusion from a not-found.
- **`session_store` is NOT generic over `kind='wizard'|'pt'`, and `pytest_create` is NOT
  rewired to it** (commit 9) — a deliberate deviation. `_pt_persist` RAISES on a failed
  write; `_pt_get` reloads when the DB is ahead so a stale process cannot clobber newer
  work. There is no wizard equivalent of the latter. Merging them would be a behaviour
  change wearing a refactor's clothes.
  *(The persist asymmetry WAS then closed on purpose, as its own decision — see below.)*
- **`_authoritative_session` stayed in the router** (commit 9). It raises
  `HTTPException(404)`, so moving it would drag fastapi into the leaf and cost the
  framework-free property that makes the rest unit-testable. It is an HTTP gate, not storage.
- **Moving code moved its logger, and that broke two tests usefully** (commit 9).
  `test_pydantic_v2_and_logging.py` asserted "no `print()` in wizard.py" and watched logger
  `"routers.wizard"`; the persist-failure ERROR it exists to pin now comes from
  `"session_store"`. Both checks are parametrized over every extracted module now — grepping
  one file would have silently stopped covering the exact site the suite was written for.
- **A source-grep test went red and became stronger** (commit 11).
  `test_complete_marker_is_written_last` split on `files_written = [`, a variable the
  decomposition renamed away. Replaced by a behavioural test that drives the real
  `_write_bundle` with a failing second commit (induced with no patching — `os.replace` onto
  a non-empty directory raises) and requires that `zephyr_payload.json` never landed, plus an
  AST check that the one call site passes the marker last.
- **Equivalence on the error path is not equivalence** (commit 11). Comparing export
  responses through the live server gave an identical 400 for `AWPTCM-T33233` — Complete on
  disk, but its session already carries step4/step5 so backfill does not fire and the reviews
  are unconfirmed. Identical, and it never reached the write. The real check loaded HEAD's
  `wizard.py` as a second module (`exec` into a module object with `__file__` set so
  `BASE_DIR` resolves) and compared both `export()`s over the same session with `REFINED_DIR`
  in tmp: artefacts byte-identical, whole `ExportResponse` equal, `wrote_bundle=True`.
  **That harness is the technique to reuse for commit 10** — it was deleted rather than
  committed because it pins HEAD.

### Two decisions taken after commit 11 (2026-07-28f, user)

- **A lost session write now fails the request.** `session_store.persist_session` logged
  ERROR and returned, so a confirm or export answered **200 with the user's work gone**.
  It now raises `SessionWriteError` — a DOMAIN error, so the module stays framework-free —
  and `main.py` has one app-wide handler turning it into a 500. This closes the asymmetry
  with `_pt_persist` noted in commit 9.
- **Case ids sort numerically.** `build_case_groups` sorted on `k.split("-T")[-1]`, a string,
  so `AWPTCM-T100` came before `AWPTCM-T9`. Invisible while every real key is `AWPTCM-T` +
  five digits. `_case_sort_key` separates numeric from non-numeric so `pt-AWPTCM-Txxxx` and
  malformed rows still sort instead of raising `TypeError`.

### Commit 10 — what it now faces

Smaller than the plan assumed (11 is done, so `export()` is already six short functions),
but the *test* surface grew, because commits 7-9 added files that read the router as text.

**Every hardcoded `routers/wizard.py` path read must be handled in the same commit:**

| file | what it does |
|---|---|
| `test_event_loop_blocking_batch_b.py` | `_ROUTERS.rglob("*.py")` — **already widened in commit 7**, so the parametrized sweep survives the move. But `test_export_gaps_call_is_wrapped`, `test_search_endpoints_are_wrapped` and `test_blocking_helpers_are_imported_by_name` read `(_ROUTERS / "wizard.py")` |
| `test_pydantic_v2_and_logging.py` | `_WIZARD = _SERVER / "routers" / "wizard.py"` — feeds `_HEDGE_FILES`, `_LOGGING_FILES`, the deleted-helper sweep and the unreferenced-private sweep |
| `test_export_authority_batch_a.py` | two reads, incl. the `_write_bundle` AST call-site check |
| `test_security_hardening_batch_e.py` | one read |
| `test_shared_modules_decoupling.py` | `routers/wizard.py` in the private-import and single-definition checks |
| `test_generator_descriptions.py` | `"routers/wizard.py"` in `_module_defines` |

The right move is **one shared helper** that returns the wizard router's source (all files
concatenated when it is a package), rather than six independent fixes — otherwise the next
move breaks them all again. A `FileNotFoundError` is loud and fine; a `glob` that quietly
stops matching is not.

Test imports to keep working (via `routers/wizard/__init__.py` re-exports or updated
imports): `sessions` and `_parse_selections`, `confirm_step`, `push_to_zephyr`,
`_authoritative_session`, plus `import routers.wizard as wizard` in five files.
`sessions` must stay the same dict object `session_store` holds — a test already asserts
`wizard.sessions is session_store.sessions`.

## Risks

- ~~**A2 breaks tests if `conftest.py` skips the startup event.**~~ **Checked and cleared:**
  `tests/conftest.py:32` uses `with TestClient(main.app) as c:` — the context-manager form
  *does* run startup, so `app.state.app_data` is populated. No test invokes a
  `Depends(get_data)` endpoint directly (the direct imports are all pure helpers). A2 is
  low-risk; still keep the `or load_all_data()` fallback for non-TestClient callers.
- ~~**A4's `utcnow` → tz-aware** meets naive datetimes already persisted in `ck.db`. Mixed
  comparison raises `TypeError`. Not mechanical — own commit, test the round-trip.~~
  **RESOLVED in commit 5, and the risk was real** — the `TypeError` fired in the suite on
  the first attempt. Resolved by coercing at the model boundary (`models.UtcDatetime`), not
  by hardening each comparison, so the failure class is gone rather than patched.
- **A1 changes Step-2 ranking output** — deliberately. The bespoke `_score_zephyr_candidate`
  (hard anchors, weak-alone tokens, area-support boosts) is replaced by `db._relevance_score`,
  so the top-8 refs a case shows *will* differ. This is convergence onto the shared scorer,
  not drift, and it is the point of the uniformity directive — but **capture the current
  top-8 for ~10 representative case keys before the change** so the diff is a reviewed
  decision rather than a surprise. If a specific heuristic turns out to be load-bearing
  (the `hard_anchors` guard against e.g. "ARP Logging" matching generic 802.1X
  "Authentication Log" cases is the most likely candidate), port it into
  `db._relevance_score` where **all three** corpora benefit — never back into wizard.
- **A1 is the one commit that spans backend + frontend.** A missed frontend call site shows
  as an empty review table, not an error. Checklist items 1-3 cover it; the Vitest layer in
  `js-tests/` should pin fetch-once-then-cache.
- **7 test files couple to wizard.** Commit 8 must keep `__init__.py` re-exports (or update
  imports) **and** fix the 5 hardcoded `routers/wizard.py` path reads. The one that matters:
  `test_event_loop_blocking_batch_b.py:57`'s `glob("*.py")` → `rglob("*.py")`, or the AST
  event-loop invariant silently stops covering the wizard handlers while the suite stays
  green. Verify after the move by asserting the parametrized test still generates a
  wizard case: `pytest --collect-only -q tests/test_event_loop_blocking_batch_b.py`.
- **Circular imports:** `session_store` ← `llm_config` (needs `_llm_is_active` for
  `_apply_workspace_llm_if_needed`). Keep `llm_config` a leaf that imports only
  `models`/`db`; `session_store` imports `llm_config`, never the reverse.
- **The shared tree moves under you.** Another stream edits this repo concurrently
  (a `git push` was in flight while this plan was written). Re-run `git status` and the
  test gate before *and* after each commit; stage explicit paths, never `git add -A`.
- **Do not touch:** `ask-ck/var/ck.db` (permanent source of truth, never rebuild),
  `/home/st-art/framework` (read-only), `sessions/*.json` (frozen pre-migration backups).

## Verification

Gate after **every** commit:
```
PYTHONNOUSERSITE=1 .venv/bin/pytest -q tests     # or ./tool/run_tests.sh (adds Vitest)
```
20 test files / 3506 lines today. Playwright E2E (`npm run e2e`) is **not** in the gate.

Manual checklist (per user preference — no Playwright), after Part A and after commit 8:
1. **Case load is fast and non-blocking:** load a case; it should return in well under 3.8 s
   (target: near-instant, since all three step payloads are now deferred). Confirm a second
   request (`/health` in another tab) answers *during* a load.
2. **All three steps behave identically** — the directive's acceptance test. Open each of the
   three review panels in turn: each fetches its own candidates on **first** visit (visible in
   the Network tab), renders them, and does **not** re-fetch on a second visit. No panel does
   work at case-load time; no panel is slower than the others by an order of magnitude.
3. **No stdout spam:** server log shows no "Loading lightweight references…" on ordinary requests.
4. **Full Generator flow:** load case → visit each of steps 1-3 (tables populate on arrival) →
   confirm steps 1-3 → synthesize objectives → edit/save/confirm → synthesize steps → export.
5. **Step-2 ranking sanity:** the deferred Zephyr refs are still *relevant* — spot-check
   against the pre-change top-8 snapshot for the ~10 sampled keys.
4. **Bad-selection rejection:** POST `confirm_step` with a malformed selection → 400, and
   the step is **not** marked confirmed.
5. **Downstream invalidation:** re-confirm step 1 with a *different* TestLink case → step 4
   goes unconfirmed/stale. Re-confirm with the *same* shortlist → objective survives.
6. **Export gate:** a case with unconfirmed reviews 400s; a backfilled Complete case exports.
7. **Export atomicity:** bundle written with `zephyr_payload.json` last; `wrote_bundle`
   matches reality.
8. **`push_to_zephyr` dry-run** on a Complete case; invalid key (`../etc/x`) → 400.
9. **LLM config:** apply a provider → `/llm_config` reports it on cold load → `/llm_health`
   pings → switch case, config persists.
10. **PyTest Creator still works** — it is the consumer of the extracted shared modules.
    Exercise it after commits 6 and 7 specifically.

## Critical files

Line numbers below were **re-verified after `4578030`** (wizard.py is now 2436 lines). They
drift on every commit — grep the symbol rather than trusting the number, and re-verify this
block when it next goes stale. A confidently-wrong line ref is worse than no line ref.

- `ask-ck/CK-main/CK_server/routers/wizard.py` — the subject. Remaining hot spots:
  `:402` `get_data` (per-request reload → **A2**), `:1459/1468/1476` the three silent
  `except Exception` swallows in `confirm_step` (→ **A3**), `:2021` `export` (350 lines,
  → commit 11), `:2372` `_CASE_KEY_RE` (misplaced, used ~320 lines earlier).
  New in A1 and now the reference pattern: `:753` `_STEP_BUILDERS`, `:761` `step_candidates`,
  `:815` `_cases_index` (named-helper threadpool dispatch).
- `ask-ck/CK-main/CK_server/routers/pytest_create.py` — `:33` the 6 private `routers.wizard`
  imports to kill (→ commit 8); `:280` the duplicated `_apply_workspace_llm`; `:1856`
  `_pt_cases_index`; `:583,1799` the correct `app.state.app_data` pattern A2 should copy
- `ask-ck/CK-main/CK_server/main.py` — `:132` builds `app_data`; `:154` mounts the router
  (unchanged by the split if `__init__.py` still exports `router`)
- `ask-ck/CK-main/CK_server/data.py` — `:47` `load_all_data`, `:57,88-93` the per-call prints
- `ask-ck/CK-main/CK_server/models.py` — `:98,102` untyped `WizardSession.step4`/`step5`
  (→ commit 6, DROPPED — leave both untyped; `PtSession.step4/step5` hold a DIFFERENT live
  shape under the same names, so a shared model would have dropped 8 keys)
- `ask-ck/CK-main/CK_server/db.py` — `:123` `_ZREF_GENERIC_TOKENS` (still duplicated in
  wizard; Part B consolidates), `:147` `_AREA_WORDS` (**new in A1**), `:150`
  `_relevance_score` with its opt-in `area_words` tier — **the place any future scoring
  heuristic goes**, never a router — `:520` `search_zephyr`. `iter_zephyr_slim` is gone.
- `ask-ck/CK-main/CK_server/static/js/generator.js` — `loadStepCandidates` and the
  `_stepFetched` memo (A1's deferred-load core); `nav.js` `goToStep` holds the first-visit hook
- `tests/conftest.py` — `:32` uses `with TestClient(...)`, so startup DOES run and
  `app.state.app_data` is populated. **A2's main risk is already cleared.**
- `js-tests/step-candidates.spec.js`, `e2e/deferred-step-load.spec.js` — A1's regression net;
  both mutation-checked. `e2e/pages/generator.page.js` owns all E2E selectors.
- `tests/test_export_gate.py:38`, `tests/test_export_authority_batch_a.py:29`,
  `tests/test_security_hardening_batch_e.py:80` — the internal imports that constrain commit 8
- `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` — owns the `sessions`-dict concurrency
  work; `session_store.py` is where it lands
- `ask-ck/ck-facelift/PLAN-es-module-split.md` — the frontend analogue; same staging philosophy

## Handover state

**Done 2026-07-28 (all pushed to `origin/main`):** the review, all measurements, Part 0's
venv work, and **A1 shipped** — `0c06586` (`pt_cases` event-loop fix, split out and verified
green in an isolated worktree) then `4578030` (A1 proper, 10 files, +972/−261). Gate green at
the staged state; Playwright 15/15. Docs synced in the follow-up commit.

**Superseded — see the status header.** All 11 commits have shipped (commit 6 dropped);
commit 10 landed 2026-07-29. What follows was written when 7 was next; read *What A1 taught*
first — one of this plan's stated expectations was falsified by measurement, and it changes
how the consolidation commits (7-9 especially) should be approached. Then read the **A4+A5**
section: three of its own planned items turned out to be wrong, so treat every line ref and
dead-code claim in this document as a hypothesis to verify by AST scan, not a fact.

**Decisions taken (do not re-litigate):**
- Defer **all three** data steps off case load; uniform startup behaviour across steps is a
  requirement, not an optimization. One `/step_candidates/{key}/{step}` endpoint preferred
  over three bespoke ones.
- Retire `_score_zephyr_candidate` in favour of `db._relevance_score`; ranking changes are
  accepted, with a before-snapshot for review.
- All 11 commits (Part A + Part B) are in scope, including the full route split.

**Pre-flight ritual — repeat before EVERY commit.** It caught real movement twice in one
session (the venv cutover landed mid-session as `032f521`; the parallel stream committed this
very plan file as `3ea6a61`), and it is cheap:
1. `git fetch && git status --short && git log --oneline -3` — the tree moves under you.
2. `ps -eo pid,cmd | grep -E "uvicorn|pytest"` — **is a parallel stream running tests?**
   Wait for idle. ~~concurrent pytest runs write throwaway session keys to `ck.db`~~
   **No longer true as of `ac760fd`:** `tests/conftest.py` copies ck.db to a temp file at
   import time and points `CK_DB_PATH` there, so the suite cannot write the real DB at all.
   `7e80289` adds two fail-closed layers behind that. Still wait for idle, because the
   live server's thread-local connection can go stale on any external write.
3. Re-verify the line numbers you are about to rely on (see *Critical files*).
4. Stage **explicit paths**, never `git add -A` — another stream's work is often in the tree.
5. **Never verify "ck.db untouched" with a file hash or mtime.** ck.db is WAL-mode: a
   committed write lands in `ck.db-wal` and can leave the main file's bytes AND mtime
   unchanged. `md5sum ask-ck/var/ck.db` reported "identical" while a mutated test had in fact
   DELETED a real session row (2026-07-28; recovered from a snapshot — see the incident write-up
   in `SESSION_STATE.md` 2026-07-28e). Use `tool/ckdb_signature.py`, which asks SQLite and
   therefore reads main+WAL together; `./tool/run_tests.sh` now runs it before and after and
   fails on any change.
   Related trap: **`db.sqlite3 is not sqlite3`** — db.py binds pysqlite3 when installed
   (db.py:34-38), so monkeypatching the stdlib module alone does not affect db.py's connect.

**A1's before/after ranking baselines** lived in session scratch
(`/tmp/claude-1971/step2-ranking-{baseline,after}.json`, generated by
`snapshot_step2_ranking.py` / `compare_step2.py`) and are **gone with the session**. They are
no longer needed — A1 shipped — but if a future commit revisits Zephyr ranking, that
before/after harness is the pattern to rebuild: sample ~10 cases across distinct folder leaves,
capture top-8 per case, diff, and separately check hand-picked known-good refs land in top-8.
Tie-concentration alone was a misleading metric (keyword mode scored *better* on ties than
hybrid while ranking the flagship case's best ref out of the results entirely).

**Next session starts here (2026-07-28f):** run the pre-flight ritual above, then
**commit 10** — the atomic `routers/wizard.py` → `routers/wizard/` move. Read
*Commit 10 — what it now faces* for the six test files that read the router as text, and
*Part B — as executed* for what each of the finished extractions got wrong. Reuse commit
11's HEAD-vs-new equivalence harness (described there) to prove the move byte-for-byte
rather than trusting a green suite.

~~**Next session starts here:** run the pre-flight ritual above, then **commit 2 / A2**~~ —
done, `9178659`.

Two loose ends carried forward, neither blocking:
- **No `.venv310-backup`.** The 3.13 cutover (`032f521`) kept no rollback venv, so a revert
  means rebuilding from `requirements-dev.txt`. Everything is green on 3.13, so this is
  theoretical.
- **The E2E suite is not in `./tool/run_tests.sh`.** `e2e/deferred-step-load.spec.js` adds ~35 s.
  A frontend change can pass the gate and still break the golden path, so run `npm run e2e`
  deliberately for anything touching `static/` — **and ask first**; the user does not want
  Playwright run unprompted.

# Backend Module Split of `CK_server/routers/wizard.py` (+ uniform deferred step loading)

> **Status:** PLANNED, nothing implemented. Written 2026-07-28 from a full read of all
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

## Part A — perf + correctness (independent of the split; do first)

Individually testable, no file *moves* (A1 does delete ~160 lines and touches the frontend).
**Land these before touching structure** so Part B stays a pure no-behaviour-change refactor.

### A1. Defer all three data steps off case load ✅ WRITTEN 2026-07-28 (test gate pending)

> **Implemented, not yet gated.** Code is written across `wizard.py`, `db.py`,
> `static/js/{generator,nav}.js`, `static/index.html`, and
> `tests/test_event_loop_blocking_batch_b.py`. The pytest gate was deliberately NOT run
> — a parallel stream was mid-work running `pytest tests/test_prompt_examples.py` and
> had `ck.db` modified; concurrent runs write throwaway session keys and trip the known
> stale-connection bug. **Run the gate before committing.**
>
> **Result: step 2 went 2708 ms → 175 ms mean (15×), and all three steps together are
> ~235 ms — none of it at case load, none of it on the event loop.**
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
`descriptions.py` in Part B. Also delete `db.iter_zephyr_slim` (`db.py:313`, 1 caller).
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

### A2. Stop reloading data per request — `wizard.py:402-404`

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

### A4. Deprecations + dead code (mechanical)

- 9× `datetime.utcnow()` → `datetime.now(timezone.utc)`. **Now live** on 3.13.
  ⚠️ Check persistence round-trips: `db.save_session`/`load_session` and the
  `confirmed_at` comparisons must tolerate tz-aware values, and existing rows in `ck.db`
  hold **naive** datetimes. Mixed naive/aware comparison raises `TypeError` — this one is
  not purely mechanical.
- Collapse the 13× `.dict()`/`model_dump()` hedge to `model_dump()`.
- Delete `_get_full_zephyr_case` (`:208`), `slim_by_key` (`:656`), `test_id_desc` (`:828`).
- Move `_CASE_KEY_RE` (`:2375`) to the top of the module.
- Normalize `confirmed_at`: `datetime` in `StepState` vs `.isoformat()` strings in
  `step4`/`step5` (`:1827`, `:1857`). Root cause is untyped `step4`/`step5: Dict[str, Any]`
  in `models.py:98,102`; both have a stable enough shape to become real models. That
  typing change is **its own commit** — it touches persisted session shape.

### A5. Replace `print()` with `logging` (18 sites)

No `logging` anywhere in the file, so there is no level control and no timestamps —
failed-persistence warnings are indistinguishable from boot noise.
`log = logging.getLogger(__name__)`, `print(f"Warning: …")` → `log.warning(…)`,
`print(f"[export] …")` → `log.info(…)`. Highest hygiene-per-line change in the file.
Do it **after** A2 (which removes the noisiest source).

---

## Part B — the module split

Extract in dependency order, **leaves first**. The first three modules land at package
root (`CK_server/`), *not* in `routers/` — that is what actually fixes the
`pytest_create → wizard` coupling.

| New file | wizard.py lines | Contents | Notes |
|---|---|---|---|
| `CK_server/llm_config.py` | 93-173, 1288-1300 | `_llm_is_active`, `_same_backend`, `_load_global_llm`, `_save_global_llm`, `_apply_workspace_llm_if_needed`, `_preview_from` | **Kills 3 of the 6 pytest_create imports.** Drop the `_` prefixes — these are public API now. `pytest_create._apply_workspace_llm` (`:280`) collapses into the shared one |
| `CK_server/case_registry.py` | 53-80, 867-910, 1190-1210, 2374-2375 | `HIDDEN_CASE_KEYS`, `HIDDEN_CASE_FOLDERS`, `_is_hidden_case`, `_refined_complete_keys`, `_session_progress_map`, `_build_case_groups`, `_get_refined_group`, `_CASE_KEY_RE`, `_refined_payload_path` (324-334) | **Kills the other 3.** After this, `pytest_create` imports nothing from `routers.wizard` |
| `CK_server/session_store.py` | 50-51, 176-230 | the `sessions` dict, `_persist_session`, `_load_persisted`, `_clear_persisted`, `_mark_updated`, `_authoritative_session` (1736-1743) | Generic over `kind='wizard'\|'pt'` — `db.py` already is. Where per-case locking lands later (`PLAN-auth-and-case-locking.md`) |
| ~~`CK_server/wizard/scoring.py`~~ | ~~407-555~~ | **CANCELLED by A1** — `_score_zephyr_candidate`, `_ZREF_WEAK_ALONE` and the duplicate `_ZREF_GENERIC_TOKENS` are *deleted*, not extracted. Only the three tokenizers survive (`_normalize_zephyr_text`, `_zephyr_tokens`, `_specific_tokens`, 437-459) because `_build_atp_query:1148` still uses them → they go to `descriptions.py` | A1 turns this from "move 150 lines" into "delete 150 lines". Strictly better |
| `CK_server/wizard/descriptions.py` | 437-459, 558-682, 1135-1187 | the three tokenizers, `_build_testlink_description`, `_build_zephyr_case_description`, `_enrich_zephyr_rows`, `_build_atp_query`, `_split_atp_title_description`, `_get_atp_candidates`, `_hybrid_on` (1060-1064) | Pure. `_get_atp_candidates`/`_hybrid_on` are thin db wrappers — fine here. **Now the first extraction**, since scoring.py is gone |
| `CK_server/wizard/gates.py` | 225-321 | `_can_synthesize`, `_session_objective`, `_session_has_objective`, `_session_objectives_confirmed`, `_session_test_script`, `_can_synthesize_steps`, `_selection_fingerprint`, `_invalidate_downstream`, `_migrate_legacy_step4_to_step5` | The state machine. Pure predicates over a session — unit-testable, currently not |
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
1. `perf(generator): defer all three data steps off case load` — A1. The largest commit in
   Part A: backend + frontend + ~160 deleted lines. Everything else in A is small by
   comparison, so land this while attention is on it.
2. `perf(wizard): serve app.state.app_data instead of reloading per request` — A2.
3. `fix(wizard): confirm_step silently dropped malformed selections` — A3.
4. `chore(wizard): logging, dead code, pydantic v2` — A5 + the non-`utcnow` half of A4.
5. `fix(wizard): tz-aware timestamps` — A4's `utcnow` half, **its own commit**: `ck.db` holds
   naive datetimes and mixed naive/aware comparison raises `TypeError`.
6. `refactor(models): type step4/step5` — A4's last item, own commit (touches persisted shape).

**Part B (leaves first — each is import-only motion, no logic change):**
7. `refactor: extract wizard/descriptions.py` (pure; add unit tests in the same commit).
   Now the first extraction — A1 deleted what used to be commit 5's `scoring.py`.
8. `refactor: extract llm_config.py + case_registry.py; drop pytest_create's wizard imports`
   — the coupling fix, and the highest-value commit in Part B. Verify with
   `grep -rn "from routers.wizard import" --include=*.py .` → only `main.py` and tests.
9. `refactor: extract session_store.py + wizard/{gates,backfill}.py`.
10. `refactor: split routers/wizard.py into routers/wizard/` — the atomic move. Must also fix
    the 5 hardcoded `wizard.py` path reads, incl. `glob`→`rglob` (see Risks).
11. `refactor: decompose export()` — the 350-line handler, after 10 is proven.

## Risks

- ~~**A2 breaks tests if `conftest.py` skips the startup event.**~~ **Checked and cleared:**
  `tests/conftest.py:32` uses `with TestClient(main.app) as c:` — the context-manager form
  *does* run startup, so `app.state.app_data` is populated. No test invokes a
  `Depends(get_data)` endpoint directly (the direct imports are all pure helpers). A2 is
  low-risk; still keep the `or load_all_data()` fallback for non-TestClient callers.
- **A4's `utcnow` → tz-aware** meets naive datetimes already persisted in `ck.db`. Mixed
  comparison raises `TypeError`. Not mechanical — own commit, test the round-trip.
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

- `ask-ck/CK-main/CK_server/routers/wizard.py` — the subject. Hot spots: `:813` (3.8 s
  block), `:402-404` (per-request reload), `:1457-1482` (silent swallow), `:2023-2371`
  (350-line `export`), `:2375` (`_CASE_KEY_RE`, misplaced)
- `ask-ck/CK-main/CK_server/routers/pytest_create.py` — `:33-36` the 6 private imports to
  kill; `:280` the duplicated `_apply_workspace_llm`; `:583,1799` the correct
  `app.state.app_data` pattern to copy
- `ask-ck/CK-main/CK_server/main.py` — `:132` builds `app_data`; `:154` mounts the router
  (unchanged by the split if `__init__.py` still exports `router`)
- `ask-ck/CK-main/CK_server/data.py` — `:47` `load_all_data`, `:57,88-93` the per-call prints
- `ask-ck/CK-main/CK_server/models.py` — `:98,102` untyped `step4`/`step5`; `:90` `WizardSession`
- `ask-ck/CK-main/CK_server/db.py` — `:313` `iter_zephyr_slim` (the 45k scan source, **deleted
  by A1**); `:489` `search_zephyr` (the FTS replacement Step 2 adopts); `:143`
  `_relevance_score` (the shared scorer; where any load-bearing heuristic gets ported);
  `:123` the duplicate `_ZREF_GENERIC_TOKENS` that becomes the single copy
- `ask-ck/CK-main/CK_server/static/js/nav.js` — `:64,102` `goToPanel`/`goToStep`, where A1's
  per-panel first-visit fetch hook lands
- `ask-ck/CK-main/CK_server/static/js/generator.js` — `:27` the `load_case` call; `:45-47` the
  three payload assignments A1 removes; `:71` the stale `analyze_atp_coverage` comment to delete
- `tests/conftest.py` — check for the startup event before A2
- `tests/test_export_gate.py:38`, `tests/test_export_authority_batch_a.py:29`,
  `tests/test_security_hardening_batch_e.py:80` — the internal imports that constrain commit 8
- `ask-ck/ck-facelift/PLAN-auth-and-case-locking.md` — owns the `sessions`-dict concurrency
  work; `session_store.py` is where it lands
- `ask-ck/ck-facelift/PLAN-es-module-split.md` — the frontend analogue; same staging philosophy

## Handover state

**Done in the authoring session (2026-07-28):** the review, all measurements above, and
Part 0's `.venv313` build. Nothing in Part A or B is implemented — **no source file was
edited**; the only new file is this plan.

**Decisions taken (do not re-litigate):**
- Defer **all three** data steps off case load; uniform startup behaviour across steps is a
  requirement, not an optimization. One `/step_candidates/{key}/{step}` endpoint preferred
  over three bespoke ones.
- Retire `_score_zephyr_candidate` in favour of `db._relevance_score`; ranking changes are
  accepted, with a before-snapshot for review.
- All 11 commits (Part A + Part B) are in scope, including the full route split.

**Commit-1 pre-flight — COMPLETE as of 2026-07-28 (all verified, nothing had moved):**
- Part 0 done by a parallel stream (`032f521`); `.venv` is 3.13.14. See Part 0.
- **`wizard.py` untouched** — still 2439 lines, no uncommitted changes, last modified by
  pre-session commit `6eaa43e`. Same for `db.py`, `data.py`, `static/js/`. **Every line
  number cited in this plan is still valid** (spot-checked `:402`, `:813`, `:1457-1482`,
  `:2375`).
- Both perf bugs re-measured on 3.13 and still present (Context section, 3.13 column).
- **Step-2 ranking baseline captured:** 10 cases / 10 distinct folder leaves / 80 refs →
  `/tmp/claude-1971/step2-ranking-baseline.json`, generated by
  `/tmp/claude-1971/snapshot_step2_ranking.py`. Both live in session scratch, so **if the
  session ended, regenerate** — the script is self-contained, read-only, documents its own
  invocation, and reproduces the same baseline from any unlanded-A1 checkout in ~1 min.
  The 81 %-tie analysis it produced is summarized in Context.

**Concurrency note (2026-07-28):** a parallel stream is mid-work on the PyTest Creator —
uncommitted edits to `routers/pytest_create.py`, `templates/prompts/pt_extract_sequence.jinja`,
`pt_generate_script.jinja`, `tests/test_prompt_examples.py`, and it was running
`pytest tests/test_prompt_examples.py` live. **No A/B commit had a full-suite gate run
against it yet for that reason** — concurrent pytest runs write throwaway session keys to
`ck.db`, and per the known stale-connection bug an external write makes the live server's
thread-local connection go stale. Run the gate when that stream is idle, and stage explicit
paths only.

**Next session starts here:** re-run the pre-flight (it is cheap, and the tree moves —
`032f521` landed *during* the authoring session), then **commit 1 / A1**.

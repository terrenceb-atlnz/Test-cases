# Ask-CK Adversarial Review — Findings Backlog (CLOSED)

> ## ✅ COMPLETE — historical record (closed 2026-07-27g)
>
> **All 62 candidate findings are resolved.** Nothing is outstanding. This file is now a
> `ck-facelift` historical record — the reasoning behind each verdict, kept so a future
> session does not re-investigate settled ground.
>
> | | |
> |---|---|
> | Candidates raised | 62 across 14 risk domains |
> | **Fixed** | **31** — 10 in batches c/d/e, 19 in batches A–D, 2 accepted-risk items (§4) |
> | **Dismissed as not-real** | **31** — 17 in the original partial pass, 14 in the completion pass |
> | Unadjudicated | **0** |
> | Commits | `1340d9b` `a1608d5` (c/d/e) · `6b50f80` `40ec299` `ba69e22` `be9149d` (A–D) · `e54fdd2` (data) · `4a9e0d6` (§4) |
> | Test suite | 48 → **190** pytest · 47 → **72** Vitest |
>
> *Plus 2 defects found by skeptics while refuting other claims (§1, "Found while refuting") —
> not among the original 62.*

**Origin.** Generated 2026-07-27c from the full-review workflow (`askck-adversarial-review`,
run `wf_f53aa173-a88`): 14 domain reviewers produced 62 candidates (2 critical / 21 high /
19 medium / 20 low), with adversarial verification (3 refuting skeptics each, majority-real
survives). That run was **paused at ~50% verification**, leaving 35 rows unadjudicated.

**Completion.** 2026-07-27g re-fired verification over exactly those 35 rows
(run `wf_f4fcd274-366`, 40 agents): one verifier per file-cluster reading live code, then a
dedicated refuting skeptic per confirmed finding, then synthesis. Outcome: **21 survived,
14 dismissed** (10 refuted at verify, 4 killed by the skeptic), 0 unclear. Of the 21
survivors, **19 were fixed** across four themed batches; the remaining 2 were the
documented accepted-risk security rows, taken to the owner and since actioned (§4).

> **Why dismissals are recorded rather than deleted.** A dismissed row is not "unchecked" — it
> is a finding that was traced against live code and shown to be unreachable or misread.
> Keeping the reasoning is what stops the next reviewer re-raising it. The review's own gate
> refuted about half of all candidates, which is the expected shape for this method.

---

## 1. Fixed — completion pass (batches A–D, 2026-07-27g)

19 findings, each verified against live code before fixing, each with regression tests.
(The other two survivors are the accepted-risk rows, actioned separately in §4.) Severities shown are the
**post-verification** re-assessment, which sometimes differs from how the row was filed —
see the last method note in §5.

### Batch A — export authority (`6b50f80`)
*One theme: the bundle that MARKS A CASE COMPLETE could be written from state that never authorized it.*

| Sev | Location | Finding | Resolution |
|-----|----------|---------|------------|
| ~~medium~~ FIXED | `wizard.py:1939` | export fell back to the client-supplied `req.session`, so a stale tab could resurrect a deleted session and re-mark the case Complete | resolves via `_authoritative_session(key)`; 404 when no server session exists |
| ~~medium~~ FIXED | `wizard.py:1936` | no `_can_synthesize` gate, so a hand-pasted objective + steps exported as Complete with zero DB reviews confirmed | 400 gate matching the three sibling synthesis endpoints |
| ~~high~~ FIXED | `wizard.py:1381` | `confirm_step` never invalidated step4/step5, so changed selections left a bundle whose payload contradicted its own traceability.md, with both still showing green | `_selection_fingerprint` + `_invalidate_downstream`; amber "Stale" badges; fires only on a real change |
| ~~medium~~ FIXED | `wizard.py:2125` | the Complete marker was written before the largest, most failure-prone write, so an I/O error left a case Complete while the API said `wrote_bundle: False` | stage to `.tmp` → `os.replace`, payload **last**, partials unlinked |

**Migration guard.** `_backfill_from_refined` now marks the three reviews confirmed from the
Complete on-disk bundle (flagged `backfilled`), or the new gate would have 400ed every legacy
re-export. Verified across all 43 real bundles.

### Batch B — event-loop blocking (`40ec299`)
*One theme: blocking work bare on the event loop where the same file wraps it everywhere else.*

| Sev | Location | Finding | Resolution |
|-----|----------|---------|------------|
| ~~low~~ FIXED | `wizard.py:1964` | `generate_coverage_gaps` — the only unwrapped LLM call site. In `claude_agent` mode a **guaranteed 180s self-deadlock**: `submit()` blocks on `Event.wait(180)` and that event is only set by a POST the blocked loop cannot serve, so it then blames the user's ck-agent | `await run_in_threadpool(...)` |
| ~~low~~ FIXED | `wizard.py:1047` | search handlers ran sentence-transformer inference inline; cold model load **measured 16.2s** (the review estimated ~8.5s) | all wrapped + background daemon-thread warmup at startup |

**The review's list was incomplete.** An AST sweep of every router found **four more** sites with
the identical defect — `load_case`'s ATP prefetch (runs on *every* case load) and the three
`suggest_*` endpoints. All seven fixed; the sweep is now a permanent test.

### Batch C — silent content loss (`ba69e22`)
*One theme: content deleted or corrupted by a too-loose match, where the right idiom sat nearby.*

| Sev | Location | Finding | Resolution |
|-----|----------|---------|------------|
| ~~medium~~ FIXED | `llm.py:941` | unanchored `"Traceability" in ...` deleted legitimate first steps ("Verify Traceability of the ART logs…"); `validate_zephyr_payload` still passed, so the case exported a step short with **no warning anywhere** | anchored `_is_traceability_note`, matching the validator; prefix literal unified from 3 copies |
| ~~high~~ FIXED | `pt_script_template.py.jinja:108` | 13 slots interpolated step text into hand-quoted Python literals sanitized only with `replace("'","")`; a typed newline or trailing backslash produced an **uncompilable skeleton**, shown straight to the user and fed to the model as the structure to copy | new `pyliteral` filter (repr) on all 13; verified over 18 hostile-input × step-kind combinations |
| ~~medium~~ FIXED | `pytest_create.py:743` | `_restamp_provenance`'s identity fallback mapped a SETUP step onto whichever TestCase shared its number, overwriting that class's correct tag — provenance pointed at the wrong source script | setup steps skipped, matching the preview path |
| ~~medium~~ ~~low~~ FIXED | `pytest_create.py:765` ×2 | the echo regex stripped **any** leading comment mentioning ART/SVT/legacy/AI, deleting real reviewer rationale from the saved and executed script | strict echo-shape match + 2-line cap per TestCase — one fix closed both rows |
| ~~low~~ FIXED | `pt_generate_script.jinja:54` | rule 4 told the model Py2 fragments are "marked ⚠ PYTHON 2", but the marker was only emitted in the skeleton — never in the prompt's fragments section, so the steer was inert | marker now emitted per flagged fragment |

> **Note on the suggested fix.** The review proposed reusing `_PROVENANCE_TAG_RX` for the echo
> match. That does **not** work — it is a loose lint check that also matches prose opening with a
> family word, so it deleted the same comments. Caught by the tests, not by inspection.

### Batch D — error signals (`be9149d`)
*One theme: failing to signal, or actively MIS-signalling, a state already observed.*

| Sev | Location | Finding | Resolution |
|-----|----------|---------|------------|
| ~~medium~~ FIXED | `provenance.js:75` | no `res.ok` check — an HTTP error rendered as a **green success** reading "(empty)", discarding the server's `detail` | `admin.js:41` idiom; error routes to the existing red-flash catch |
| ~~low~~ FIXED | `generator.js:480` | no `res.ok` check — an error body set `S.currentSession = undefined`, silently wiping the session while the UI carried on | guard before any state write; only adopts a payload carrying a session; surfaces batch A's `invalidated` |
| ~~medium~~ FIXED | `llm.py:425` | Claude branch had no empty-content guard, unlike the OpenAI branch | mirrored, incl. the thinking/reasoning fallback |
| ~~medium~~ FIXED | `llm.py:428` | Claude branch never checked `stop_reason`, so a truncated answer was accepted as complete and the downstream JSON parse failed looking like "the LLM found nothing" | mirrored `max_tokens` guard |
| ~~medium~~ FIXED | `db.py:816` | `_rrf_merge` truncated to `limit` with no pinning, silently violating the `keep_ids` contract the keyword layer honours — a kept pool item vanished on re-search | `keep_ids` threaded through all three `*_hybrid` entry points; two-pass emit |
| ~~medium~~ FIXED | `pytest_create.py:2068` | the restart-orphan sweep lived only in `load_case`, so `run_status` reported the persisted `running` forever and the UI polled indefinitely | extracted `_sweep_stale_runs`, called from both; poll also stops on `active === false` |
| ~~low~~ FIXED | `agent_jobs.py:111` | `gc()` was dead code (zero call sites); `_queues`/`_session_seen` grew for the process lifetime, keyed by an unvalidated header | driven from the long-poll, rate-limited; empty deques dropped; `X-CK-Session` length-capped |

### Found while refuting — not on the original list

| Sev | Location | Finding | Resolution |
|-----|----------|---------|------------|
| medium FIXED | `llm.py:523` (SSE) | While disproving the chunk-boundary claim, the skeptic found a **worse** bug: SSE is `text/event-stream`, and requests maps any `text` type to ISO-8859-1, so `decode_unicode` built a latin-1 decoder. Every non-ASCII byte on the live vLLM streaming path mojibaked — `port — 1 µs` → `port â 1 Âµs` — silently (no replacement char), still valid JSON, flowing into stored objectives/steps and on to Zephyr | `resp.encoding = "utf-8"` before iterating |
| — FIXED | `AWPTCM-T37861` data | the bundle shipped a Python-style `\'` escape (invalid per RFC 8259) since its first commit, so it could not be backfilled and 400ed on re-export — the only one of 43 | one backslash removed (`e54fdd2`); +2 guards over the whole refined-cases tree |

---

## 2. Fixed — earlier batches (2026-07-27c/d/e)

10 rows, commits `1340d9b` (c+d) and `a1608d5` (e). Per-batch detail in PROGRESS.md
sessions 27c/27d/27e and SERVER-README → *Security Posture*.

| Sev | Location | Resolution |
|-----|----------|------------|
| ~~high~~ FIXED | `agent_bridge.py:38` | deliver enforces `X-CK-Session` job ownership; `/next` + `/result` bind to the header |
| ~~medium~~ FIXED | `agent_bridge.py:18` | `/next` binds to the header (query param legacy fallback only) |
| ~~high~~ FIXED | `main.py:56` | CORSMiddleware, localhost allowlist, `CK_ALLOWED_ORIGINS` to widen |
| ~~high~~ FIXED | `pytest_create.py:1150` | library-filename traversal — full basename validated before the path is built |
| ~~high~~ FIXED | `wizard.py:2122` | export `case_key` traversal — `_CASE_KEY_RE` at the top of `export()` + resolved-path check |
| ~~high~~ FIXED | `llm.py:1329`, `llm.py:1347` | routed through the hardened string-aware `extract_json_block` |
| ~~medium~~ FIXED | `llm.py:618`, `llm.py:1218` | same shared extractor |
| ~~low~~ FIXED | `llm.py:1013` | same shared extractor |

Also landed in batch c, never tabled above: SSH command injection (`shlex.quote` + metachar
validation), framework-guard bypass (redirection / inline interpreters / command substitution /
`rsync` / `install` / `cp -t`), stored XSS (`html_sanitize.py` allowlist at every objective store
point), secret leak (`redact_llm_config` / `safe_session_dict`), admin reset missing PT sessions,
and export destroying a real first step.

---

## 3. Dismissed — verified NOT real (completion pass)

Traced against live code and shown to be unreachable, misread, or already prevented.
**Do not re-raise without new evidence.**

*(15 rows for 14 dismissed findings — `wizard.py:1936` appears here as a duplicate framing
of the batch-A export row, and in §1 as the row that was actually fixed.)*

*(15 rows for 14 dismissed findings — `wizard.py:1936` appears once here as a duplicate
framing of the batch-A export row and once in §1 as the row that was actually fixed.)*

| Location | Filed as | Why it is not real |
|----------|----------|--------------------|
| `wizard.py:1648` | two `WizardSession` objects race; one clobbers the other | No suspension point exists. Both handlers are `async def` with **zero** `await` anywhere in their bodies, and uvicorn runs no `--workers`, so FastAPI cannot interleave them. |
| `wizard.py:2165` | `push_to_zephyr` can ship a bundle predating the ≥3-`<li>` validation | Mechanism real, consequence false. Dumped step 0 of every affected case — the traceability note is present in all of them. |
| `wizard.py:1998` | inconsistent ART caps (8 vs 6) truncate IDs | The `[:6]` path needs `step3.selections` populated while `art_string` is empty, which `confirm_step` structurally prevents. Reachable only via the client-session fallback — i.e. it was really the batch-A export row, now fixed. |
| `wizard.py:1936` (dup) | no confirm gate on export | Duplicate framing of the batch-A row; closed by that fix. |
| `db.py:821` | `HAS_VEC` true but no embeddings → wasted model load | Architecturally unreachable: `build_db.py` refuses corpora builds (the source couriers were retired), so a keyword-only DB cannot exist in this product. Cost claim also overstated by ~2 orders of magnitude. |
| `db.py:54` | thread-local WAL connection races | The run thread does touch the DB off the loop, but the claimed lost update cannot occur — its mechanism requires an interleaving the write path does not permit. |
| `pytest_create.py:1097` | lint misses the physical-step marker, so a tautological verdict passes | `if want in output:` is **not** tautological — `output` is really populated by `dut.cmd(...)` in the poll loop and is False on operator timeout, so the branch genuinely passes/fails correctly. |
| `pytest_create.py:106` | `_translate_py2` fails on indented fragments | No trigger: both index paths emit only column-0 starts. The failure would be benign anyway (wrapped in try/except, ships the original). |
| `llm.py:494` | `iter_lines` splits multi-byte sequences | The incremental decoder buffers split sequences by design — verified empirically, zero replacement chars. **But tracing it exposed the real SSE-encoding bug, now fixed (§1).** |
| `upload_refined.py:132` | nested-paren titles get mangled | Arithmetically true in isolation, not reachable in practice: ran the regex over all 45,427 real Zephyr titles — none has the required shape. |
| `upload_refined.py:554` | string `majorVersion` raises TypeError | Consequence accurate, premise false — the API's contract does not return it as a string. |
| `upload_refined.py:523` | a clone landing as v1.1 defeats the idempotency guard | The premise contradicts the documented `newversion` behaviour; a minor bump is not a reachable outcome. |
| `pt_generate_script.jinja:10` | corpus text injects instructions into prompts | No write surface: `ck.db` is built once offline and the entire runtime write path is a single `INSERT OR REPLACE INTO sessions`; every corpus accessor is a bare SELECT. The one "corpus" field cited is actually this app's own step-5 output. |
| `traceability.md.jinja:29` | brackets in keys/titles break the markdown link | Title/justification are never inside `[]` or `()` — 8,673 bracket-containing DB titles already render correctly — and every real key matches `AWPTCM-T\d+`. |
| `agent_bridge.py:44` | oversized/malformed `content` stored verbatim | Unreachable: storing anything requires a live unguessable `job_id` **and** a matching session; both checks reject before `job.result` is ever assigned. |

Seventeen further candidates were refuted during the original partial pass (2026-07-27c) and
never entered this table.

---

## 4. Accepted risks — reviewed and actioned (2026-07-27g)

Both were **documented accepted risks** (`README.md:145`, `SERVER-README.md:573-575`,
`SESSION_STATE.md:1578`), so neither was fixed unilaterally. Taken to the owner with two
facts the original acceptance did not account for; **all three actions approved and
implemented** (`4a9e0d6`).

| Location | Accepted risk | What the review added | Action taken |
|----------|---------------|-----------------------|--------------|
| `main.py:261` / `run.sh:70` | server binds `0.0.0.0` with no auth — justified by the localhost/single-user model | Verified **live**: the box was reachable on its LAN IP and an unauthenticated `POST /api/wizard/push_to_zephyr/{key}` returned 200. `dry_run` is a plain query param defaulting `true`; CORS does not constrain `curl`, and the UI `confirm()` is client-side only | **Binds `127.0.0.1` by default.** LAN exposure is now an explicit `HOST=0.0.0.0`. Also fixed the `__main__` entrypoint, whose module path had been dead since the 2026-07-13 restructure |
| `wizard.py` push handler | *(not previously identified)* | **`--force` was hardcoded**, disabling `upload_refined.py:947`'s own "already appears refined in Zephyr — SKIP" guard on **every** push. The UI had no way not to force, so that protection was dead code and any push could overwrite an already-refined live case | **Force is opt-in per request** (`?force=true`); the UI does not send it |
| `pt_exec.py:281` | paramiko `AutoAddPolicy`, no host-key verification anywhere in the repo | **The localhost rationale does not apply.** The connection is *outbound* to a lab testbox, so exposure is independent of the web UI being single-user. Two items had been bundled under one justification and the second did not follow | **`load_system_host_keys()` before the policy** — a known testbox is pinned, so a changed key raises instead of being accepted. New hosts still connect with no prompt; `CK_SSH_TRUST_ANY=1` to opt out |

**Still accepted, unchanged: there is no authentication on any endpoint.** These changes
align the defaults with the documented single-user model; they do not make the server safe
to expose. Add auth (and TLS) before any shared deployment.

Regression tests: `tests/test_security_hardening_batch_e.py` (14), including that the CLI-side
protection `--force` would bypass still exists, that the UI does not send `force`, and that
`known_hosts` loads *before* the policy (the ordering is the whole fix).

---

## 5. Method notes (for the next review)

- **Verify before fixing.** About half of all candidates were refuted. Applying the suggested
  fixes unverified would have produced churn and, in at least one case (the provenance regex),
  a fix that did not work.
- **The finding lists were incomplete more than once.** Batch B named three blocking call sites;
  a mechanical AST sweep found seven. Prefer a sweep over the filed list wherever the defect has
  a machine-checkable shape — and leave the sweep behind as a test.
- **Skeptics find things while refuting.** The SSE-encoding bug — the most consequential
  correctness issue in the completion pass — came from an agent disproving a narrower claim.
  Read the refutations, not just the verdicts.
- **Prefer structural tests to timing ones.** The event-loop and provenance work is pinned by AST
  and source assertions that catch the *next* regression, not only the one filed.
- **Severity moves in both directions.** Three original "high" rows were downgraded on inspection;
  two "low" rows were raised (the 180s deadlock, and the export confirm gate).

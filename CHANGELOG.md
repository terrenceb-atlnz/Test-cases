# Changelog — Ask CK

Feature history for the Ask CK workbench, newest first. This file was split out of
`README.md` on 2026-08-17: the README's *Current Status* table had grown into a changelog
held inside table cells (one row ran to ~7,000 characters), which made both jobs harder.
The README now says what the system **is**; this file records how it **got there**, and
in particular *why* each decision was made.

For session-by-session narrative see [`SESSION_STATE.md`](SESSION_STATE.md); for the
current working thread see
[`ask-ck/objective-drafting/PROGRESS.md`](ask-ck/objective-drafting/PROGRESS.md).

---

## 2026-08-17 — The venv stopped being relocatable, loudly and silently

The working tree moved from `copilot/Test-cases` to `claude/Test-cases`. A Python venv is
**not relocatable**: `pip` bakes an absolute shebang into every console script, and
`activate` hardcodes the absolute `VIRTUAL_ENV` it was built with. 30 files carried the
dead path (29 scripts in `.venv/bin/` plus `pyvenv.cfg`).

- **The gate failed loudly.** `tool/run_tests.sh` invoked `.venv/bin/pytest` directly, which
  died with `bad interpreter`. Fixed by running everything as `"$PY" -m <tool>` — `-m` reads
  the module out of site-packages and never consults a shebang, so the gate now survives any
  future move.
- **`setup.sh` failed *silently*, which was worse.** Its reuse check probes
  `.venv/bin/python3` — a *relative* symlink that still resolved — so it reported "Reusing
  existing virtual environment", sourced the stale `activate`, and then ran bare
  `python3 -m pip install`. With the venv's `bin/` missing from `PATH`, that resolved to
  the **system** Python 3.10 and would have installed the entire dependency set into the
  user's site-packages while printing success at every step. The sqlite-vec (§4b) and
  `ck.db` (§4c) checks had the same fault, so they were reporting on the wrong interpreter.
- **`run.sh` had it too**: the server would have started on system 3.10 with a `fastapi`
  from `~/.local` and **no `sentence-transformers`** — the exact "boots but silently
  degrades to keyword-only search" trap the setup docs warn about.

Fixes: the baked paths were rewritten in place; `setup.sh` gained a **§3b relocation
detector** that repairs a moved venv or fails loudly; and `setup.sh`/`run.sh`/`run_tests.sh`
now all call the venv interpreter **explicitly** rather than trusting an activated `PATH`.

## 2026-08-05 — The blank-`expectedResult` push rule was removed

The rule refused all 53 bundles on a false premise. A Zephyr **manual** step is *designed*
to leave `expectedResult` empty, so the tester produces evidence of function rather than
reproducing a stated result. `synthesize_steps` now forces the field empty at generation.
See memory `expected-results-deliberately-absent`; this was reversed circularly once before
and must not be re-litigated.

## 2026-08-04 — Lint gate split by authority

19 lint rules split into two classes with different powers:

- **14 blocking errors** — the artefact provably cannot work (syntax, missing structure, a
  surviving `>>> FILL` marker, a device the fixed `init()` frame never bound, a bad import,
  the truncation detector). **Not overridable.**
- **5 policy errors** — the script runs but breaks a house rule (the logging contract, a
  direct `setup.init_portlink()`). Overridable with
  `{"acknowledge_lint_policy": "<why>"}`, recorded on the session.

Unrecognised errors are treated as blocking. Also: **Run results** report one outcome per
case (PASS / FAIL / UNSUPPORTED, plus ERROR for a case that reached no verdict) with both
tallies labelled — `cases: … ; assertions: …` — and `results_complete` states whether the
results are *trustworthy*, which is a separate question from whether the test passed.

## 2026-08-03c — Multi-message generation: there is no output ceiling

The 32,000-token cap bounds one **message**, not the answer; a long reply simply continues
into further assistant messages. Measured `output_tokens` of 67,326 / 66,334 / 57,188 /
34,966 — every one a complete script. `CK_server/gen_assembly.py` reassembles the
continuation seams and resolves classes a continuation re-emits. A reply that does not
reassemble cleanly is **refused** rather than persisted (the full reply is saved under
`step6.failed_generations`), and a script covering fewer steps than the approved sequence
is a lint **error** that blocks confirmation.

The earlier "9–20 `TestCase` class ceiling" and its `_size_overflow()` gate were a defect in
`_parse_generated_blocks`, which stopped at the first *continuation* fence and discarded the
rest. Both are gone. `ask-ck/pytest-create/FINDINGS-generation-size-ceiling.md` carries a ⚠
banner because it records **parser** output, not model output.

## 2026-08-03 — Zephyr push validates before it writes; preflight stops guessing

- The push now **validates before it writes** (server shape rules, imported from
  `validate_zephyr_payload` — one owner, no second copy) and **fails closed**. A real write
  requires a per-case `{"confirm": "<key>"}` token.
- Fixed a heading mismatch that silently dropped **84 of 86 Zephyr web-links**.
- Every `--execute` appends to `ask-ck/var/zephyr-push-audit.jsonl` **before** the first
  network call; a case whose audit record cannot be written is refused.
- `tool/pt_preflight.py` now resolves a topology-**contract** role
  (`misc.get('ck_role_dut', …)`) rather than giving up. A script written to the new contract
  names no device literally, so preflight previously reported `UN-RUNNABLE (0/2 links)` — a
  confident wrong negative where the honest answer was "cannot determine".

## 2026-07-30 — Topology contract + minimality; pre-flight topology check

Generated scripts no longer name devices or leave the port link to a FILL slot. `init()`
resolves the DUT from the bench's own role contract (`[misc] ck_role_dut`, read at run time)
and binds its single link through a fixed-frame `_ck_bind_link()` that resolves
`ck_link_<role>`, refuses a silent `(None, None)` portlink, and **asserts the bound port's
media**.

That media assertion matters because the CLI is media-blind: on a 1000BASE-SX port
`speed ?` still offers `10…400000` and `duplex ?` still offers `half`, so a matrix bound to
fibre would record "DUT failed to set speed 100" — a false failure blamed on the product.

**Generation itself reads no bench file.** It targets a *contract*, because a bench-reading
generator silently weakens a test to fit whatever hardware happens to be present. The bound
device set is now a **consequence** of the topology — one link ⇒ exactly one partner, and
the partner *is* that link's far end — so over-declaration is structurally impossible rather
than merely discouraged. (T33235 previously bound 4 devices and 2 links while referencing 1
of each, making the script demand cabling for nothing.)

Also added `tool/pt_preflight.py`, which matches a script's `init_swi`/`init_portlink`
demands (via `ast`) against a bench's `.setup`. `Setup.init_portlink()` returns
`(None, None)` **silently** when a link is undeclared, so a missing *cable* would otherwise
grade as a *script* defect on hardware. Verdicts move with the bench: with only testbox↔DUT
declared it found all three Port (7) scripts un-runnable; declaring the two verified
`swi_a`↔`swi_b` links took that to 2 of 3.

Spec: `ask-ck/pytest-create/TOPOLOGY-PROFILES.md`. Checkers: `tool/pt_profiles.py`,
`tool/pt_preflight.py`, `tool/pt_media.py`.

## 2026-07-29 — Backend module split complete; the objective reaches Generate

**Module split (all 11 commits; commit 6 dropped by decision).** `routers/wizard.py` (2515
lines) became the `routers/wizard/` package — four route modules (`reviews` / `config` /
`synthesis` / `export`) plus `_shared.py`, function bodies moved byte-identical — with
shared concerns extracted to `llm_config.py`, `case_registry.py`, `session_store.py`, and
the `generator/` package.

The coupling fix that motivated it: `pytest_create.py` used to import **six
underscore-private helpers** out of `routers/wizard.py`, so renaming any one silently broke
a different tool. It now imports nothing from there. `export()` decomposed from a 351-line
handler into six named steps, verified byte-identical through the write path. A failed
session write now returns **500** instead of 200-with-work-lost.

**Objective in Generate.** The refined objective is baked into the generated script as a
`# ==== OBJECTIVE ====` header and carried into the Generate prompt, so the model grounds
each verdict in the declarative outcome instead of per-step action/verify text alone. A
5-model comparison judged by opus + vllm-fast (`tool/pt_matrix_judge.py`) confirmed the fix,
and isolated the next bottleneck as sequence-step **`kind` misclassification**.

## 2026-07-28 — Prompts are tested; test traffic stops writing the permanent DB

- `tests/test_prompt_examples.py` **executes the LLM prompts' own code examples** against
  real harvested CLI output in `ck.db`. Where prose and an example disagree, the model
  implements the **example** — several generated-script defects traced back to wrong
  examples in our own files. `tests/_prose.py` keeps such checks from firing on their own
  advice text (that happened 4 times).
- E2E and smoke checks now run against a **throwaway `ck.db` copy** on port 8123 via
  `tool/run_scratch_server.sh`. `ck.db` going dirty is correct when a *person* operates the
  app, but test traffic writing the permanent LFS-committed database is worthless data — the
  old Playwright `webServer: './run.sh --bg'` + `reuseExistingServer: true` attached to the
  real dev server on 8000 and did exactly that. `/health` now reports `db.db_path` +
  `db.is_permanent_db`.

## 2026-07-27 — CLI grounding, fragment-resolver hardening, security review, the test gate

**CLI grounding.** Both the sequence-extraction and generate prompts are grounded in the
real AlliedWare Plus command reference, harvested from `docs.atlnz.lc` into `ck.db`
(`cli_commands` / `cli_command_products`). Root cause it fixes: the prompts demanded "exact
CLI fields" while showing **zero examples**, so *every* model — Opus included — invented a
`speed=1000`/`state=up` schema the switch never prints (real output is `current duplex full,
current speed 1000, current polarity mdix`). Fabricated tokens went **13→0** in sequences
and **57→0** in scripts.

**Fragment-resolver hardening.** The resolver bounds every symbol by exact index `loc` —
else next-unit-start−1, else `loc_total` — replacing a blind `loc[0]+60` fallback that
over/under-captured ~18% of `test_case` entries. Legacy Python-2 fragment code is
deterministically modernized at resolve time via stdlib `lib2to3`; `status="translated"`
guarantees valid Py3 (tab/space normalized + `ast`-verified), untranslatable code ships
as-is with a ⚠ banner, and translated blocks carry a `(py2→py3)` provenance suffix.

**Security posture, full adversarial review.** Server-side objective-HTML sanitizer
(stored-XSS), `llm_config` secret redaction from all browser/disk serializations,
`shlex`-quoted + metachar-validated SSH run command, extended framework-read-only guard,
path-traversal guards on export `case_key` + generated filenames, session-bound agent
bridge, CORS lockdown. **Network defaults corrected (2026-07-27g):** binds `127.0.0.1`
(LAN exposure is now an explicit `HOST=0.0.0.0`), `push_to_zephyr` no longer hardcodes
`--force` (it was disabling the CLI's own "already refined — skip" guard on every push),
and SSH host keys are pinned trust-on-first-use.

**Three-layer test suite + one gate.** Backend pytest (in-process; no mocks, network or
testbox) + frontend Vitest/jsdom + a sparingly-run Playwright E2E, with
`./tool/run_tests.sh` as the single gate. Several backend tests are **structural** — an AST
sweep proves no async handler calls a blocking function unwrapped — so they catch the *next*
regression rather than only the one filed.

**Objective-coverage gate.** Every Zephyr step must map to ≥1 sequence step, enforced on the
Confirm button for *2. Sequence* and *5. Generate*, with an error quoting each untested step
(override: `acknowledge_coverage_gap`).

## 2026-07-23 — PyTest Creator UX + correctness revision

Script Search and Fragments became per-step carousels (one step per screen, step-pill nav);
Cases split into Open/Partial + Complete. The step sequence is classified **setup / verify /
physical / manual**, so physical plug/unplug/hot-swap steps generate an operator-prompt +
wait-for-state-change pattern (the SVT 3009 model) and manual checks generate a `yesNo()` —
**physical steps are in scope, not skipped**.

Also fixed: device-name reconciliation (bind the names fragments actually use), a
**provenance mis-attribution bug** (setup-step renumbering stamped the wrong fragment on the
wrong TestCase), fragment `maps_to` validation, and a positive **NO REUSE** gap marker. The
former **Fit Decision** step was removed — the fixed skeleton made it moot (8 steps → 7).

## 2026-07-22 — Zephyr push button, streaming transport, agent token reporting

- **(22c) Push to Zephyr** button in the Generator's step-6 export actions, with a dry-run
  Preview. Strips a leading `(N)` title group, ensures **version 2.0** (idempotent — bumps
  1.0→2.0, never beyond), uploads objective + steps + `traceability.md` + ART web-links.
  Shells out to `tool/upload_refined.py`, so the server never holds the JIRA token;
  attachments use replace-semantics. All 43 Complete cases pushed + audited to v2.0.
- **(22b) Streaming transport.** The vLLM path now streams (`stream:true` +
  `stream_options.include_usage`), so the HTTP read timeout bounds the gap *between* chunks
  rather than the whole response — the structural fix for `vllm-thinking` read-timing-out on
  the largest-output step (a 30s-read-timeout call ran 21+ minutes without timing out).
- **(22d) Claude agent tokens + model.** The per-user agent lifts `usage`/`total_cost_usd`
  from the `claude -p --output-format json` envelope, so the badge shows real `N in / M out`
  instead of "— tok" (a transport that reports nothing still shows "— tok" honestly). Added
  a Haiku / Sonnet / Opus selector for that mode.

## 2026-07-21 — Standardized generation; vLLM reasoning-model hardening

Generate fills a fixed skeleton template (`templates/pt_script_template.py.jinja`) — one
`TestCase` per verification step with a mandatory per-step logging contract, suite +
per-case `tear_down`, data-driven topology — and lint enforces template conformance.

The OpenAI-compatible path now handles the org models' chain-of-thought: 16k `max_tokens`,
null/truncated-`content` guards with clear errors, and the documented **system+user** message
shape with a JSON-only steer (−35% tokens on real prompts). These are *reasoning* models —
they emit `reasoning_content` before `content`.

## 2026-07-20 — Local LLM, observability, provenance, strict DB-only search

- **Local LLM** login mode (org vLLM, OpenAI-compatible; Fast/Thinking toggle; server-stored
  key in gitignored `secrets.local.json`) became the default, with a **Health check** button.
- **Observability** (dev scaffolding): per-panel debug footer, `N in / M out` token badges,
  per-session log in `CK_server/debug-log/`.
- **LLM Provenance** (permanent): every LLM panel can show/copy the exact prompt and
  **Refresh** it live via a no-send `dry_run` render — 1-for-1 with a real send, zero
  tokens — for pasting into a competing LLM.
- **Strict DB-only search**: literal script code + all semantic vectors ingested; the
  embedding model is bundled and loads offline. The server reads **zero** corpus JSON,
  enforced by `tool/guard_db_only.py`; startup fails fast without `ck.db`. Fixed 3 latent
  bugs (the embed guard never ran; sqlite-vec KNN silently returned nothing; a HuggingFace
  load-time ping).
- Hidden **admin panel** (double-click CK's face) — reset sessions + restart server.
- **(20b) The courier corpora were retired.** `ck.db` became the permanent committed source
  of truth, so the intermediate build inputs (`suite_*_enriched.json`,
  `all_test_suites.json`, `zephyr_cases.jsonl`, the script index/sidecars) were **deleted**
  and the rebuild paths removed. Only the raw Zephyr XML is kept, as a provenance root.
  `tool/build_db.py` remains as provenance and **refuses to run**.

## 2026-07-16 — Data layer moves to SQLite; two-table review UX; ES modules

- **Migration complete (committed A–D):** corpora + sessions served from `ask-ck/var/ck.db`
  with FTS5 keyword + sqlite-vec hybrid/semantic search.
- **Two-table "chosen shortlist"** on the TestLink / Zephyr / ATPyLib steps — candidates
  above, chosen below in insertion order; Confirm reads the **chosen** table only. Keyword
  search is relevance-ranked (title matches outrank body-only hits) and each new search
  re-ranks the whole candidate pool.
- Frontend refactored to browser-native **ES modules** (`static/app.js` → `static/js/`).
- **Repo hygiene:** removed a stray root `zephyr-auto_negotiation.xml` and completed-phase
  enrichment scratch files. (The build-input corpora were *deliberately kept* at the time as
  `build_db.py` input — superseded four days later by 2026-07-20b above, which retired them.)

## 2026-07-15 — Setup and maintenance fixes, from a fresh-machine walkthrough

Found by walking Getting Started on a clean Ubuntu box:

| Fix | Why it was needed |
|-----|-------------------|
| Added `ask-ck/CK-main/requirements.txt` as a mandatory install step | The server crashed with `ModuleNotFoundError: No module named 'fastapi'`. The Python dependencies were never listed anywhere, so a fresh clone had no way to know what to install. |
| Added a virtual-environment step | Isolates dependencies from global/site packages. Optional but recommended — it changes *where* packages live, not how the project runs. |
| Documented Git LFS ≥ 3.3, installed from the git-lfs repo rather than apt | Ubuntu apt ships LFS 3.0.2, incompatible with Git 2.38+; a fresh `git lfs pull` fails with `cannot add to the index - missing --add option?`. It only "worked" on the dev machine because the large files were already materialized, so the smudge step never ran. |
| Documented HTTP-only access and the `0.0.0.0` bind gotcha | Browsers with HTTPS-Only mode auto-upgrade to `https://`, and a plain-HTTP server cannot answer a TLS handshake — a blank `SSL_ERROR_RX_RECORD_TOO_LONG` page. A same-port redirect is impossible: the failure is at the TLS layer, before any HTTP is exchanged. |
| Added `setup.sh`, an idempotent one-shot bootstrap | `run.sh` assumes everything is set up and gives cryptic errors otherwise. It also detects a missing/too-old git-lfs and offers to fix it. **The git-lfs upgrade installs an explicit version** — Ubuntu ESM pins 3.0.2 at a *higher* apt priority (510) than packagecloud (500), so a plain `apt-get install git-lfs` kept the old one. |
| Corrected stale Git LFS paths in `.gitattributes`, then renormalized | After the 2026-07-13 restructure the LFS rules still pointed at the old `data/zephyr_full/…` paths and matched nothing, so `zephyr_cases.jsonl` (53 MB), `index.json` (17 MB) and `suites/testlink_awp.json` (28 MB) were committed as plain Git blobs. `git add --renormalize` re-ran them through the LFS filter. This does **not** rewrite history — old blobs remain in past commits. |
| `run.sh` gained venv auto-activation, foreground/background, and `--stop` | Previously you had to activate the venv by hand and it only ran in the foreground. Background mode detaches into its own session/process group, records `.ck-server.pid`, and appends to `.ck-server.log`. |

## 2026-07-13 — Multi-tool facelift and repository restructure

Renamed to **Ask CK**; the single-purpose drafting tool became a multi-tool workbench with a
sidebar (Generator, PyTest Creator, Test Composer, Zephyr Templating Tool) and a relocated
LLM Configure panel. The repo was restructured at the same time: `drafting-tool/` →
`ask-ck/CK-main/` (+ `CK_server/`), and root `data/`, `refined-cases/` and the process docs
moved under `ask-ck/objective-drafting/`. Historical documents may still reference pre-move
paths.

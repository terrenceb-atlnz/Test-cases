---
verified: 2026-10-19
---
<p align="center">
  <img src="ask-ck/frontend/ck-main/current/ckc.jpg" alt="Ask CK" width="140" style="border-radius:50%;" />
</p>

<h1 align="center">Ask CK</h1>
<h3 align="center">Test Tooling Workbench</h3>

> **Proprietary and Confidential — All Rights Reserved.** Copyright (c) 2026
> terrenceb-atlnz. **No license is granted.** This repository and all contents (source code,
> data files, documentation, and tools) are the exclusive proprietary property of the
> copyright holder. You may **not** copy, use, modify, distribute, sublicense, or create
> derivative works from any part of this work without prior express written permission.
> Unauthorized access, use, or distribution is strictly prohibited. See
> [`COPYRIGHT`](COPYRIGHT).

---
**Please don't clone this without contacting first! **

Ask CK is a server-backed test-engineering workbench for the **AWPTCM** test-case program. It
carries a test from the project paperwork to a result on a real bench, with a person confirming
every stage:

1. **Zephyr Templating Tool** — from a project's wiki page, choose which template test plans,
   cycles and cases the project needs, and clone them into Zephyr.
2. **Objective / Test Case Generator** — enrich a sparse Zephyr manual case into a refined case
   with declarative objectives and reviewable steps.
3. **PyTest Creator** — turn a refined case into a runnable Allied Telesis `framework` script.
4. **Test Composer** — run that script on a testbox, make it run end to end, review it, finalize
   it, and later run finalized scripts or whole projects.

To decide what a case *should* verify, it draws on two historical silos:

| Source | Role |
|---|---|
| **TestLink** (historical) | Detailed human-authored cases (`AWP-*`) for artefact context and overlap |
| **ATPyLib** (automated) | Enriched suites describing what automation actually tests *for* |

**Authoritative process for the Generator:**
[`ask-ck/functions/generator/OBJECTIVE_DRAFTING_PROCESS.md`](ask-ck/functions/generator/OBJECTIVE_DRAFTING_PROCESS.md).

## Quick start

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases
./setup.sh          # idempotent; safe to re-run
```

`setup.sh` runs a preflight and prompts before each fix (needs `sudo` for installs): base
toolchain (`git`, `git-lfs`, `curl`) → **Python ≥ 3.10** → **Git LFS ≥ 3.3** + `git lfs pull`
→ virtual environment + dependencies → verify `ask-ck/db/ck.db` → offer to launch.

After the first successful setup you almost always just want `run.sh`:

```bash
./run.sh            # foreground (asks fg/bg the first time)
./run.sh --bg       # background, no prompts
./run.sh --restart  # stop + background start
./run.sh --stop     # stop the background server
```

Then open **`http://localhost:8000/`**. Root `./run.sh` is a thin wrapper around the real
launcher at `ask-ck/CK-main/run.sh`; either works.

> These flags are for a checkout you run yourself. The hosted LAN server of record runs as
> the systemd user unit `ask-ck.service` — manage it with `ck` or the admin panel, **never**
> `run.sh --stop` / `--bg` (see SERVER-README → *Running the Server* → hosted deployment).

> **Use `http://`, not `https://`.** Ask CK serves plain HTTP. Browsers with HTTPS-Only mode
> (Firefox, HSTS) auto-upgrade and show a blank `SSL_ERROR_RX_RECORD_TOO_LONG` page — the
> failure is at the TLS layer, so a same-port redirect is impossible. Exempt localhost.

**`setup.sh` vs `run.sh`:** `setup.sh` is the superset — prerequisites, LFS pull, venv, and a
`ck.db` sanity check, then it delegates to `run.sh` to launch. Use it for first-time setup or
when the toolchain changed. `run.sh` does none of that; it only starts the server. The server
runs with `--reload`, so **backend code edits restart it automatically** — restart by hand only
for environment or dependency changes.

**Set up your seat (one time).** Claude, and every Test Composer page, run on *your own* PC
through a small agent that uses your own Claude seat — the server never runs Claude and never
sees a credential. The Ask CK home page shows the one line to paste (PowerShell on Windows, a
shell on Linux); it installs Claude Code if needed, logs you in, installs the agent and starts
it. Re-run the same line to update or repair. Details: [`ask-ck/agent/README.md`](ask-ck/agent/README.md).

<details>
<summary>Requirements, manual setup, and the Python-version rule</summary>

**Python ≥ 3.10** (`fastapi>=0.139` drops 3.9) + [Git LFS](https://git-lfs.com/) **≥ 3.3** +
`curl`, plus [`ask-ck/CK-main/requirements.txt`](ask-ck/CK-main/requirements.txt). On
Debian/Ubuntu `python3 -m venv` also needs `python3-venv`.

```bash
git lfs install && git lfs pull                       # materialize ck.db + large sources
python3 -m venv .venv && source .venv/bin/activate    # use python3.13 if available
pip install -r ask-ck/CK-main/requirements.txt
```

**Use Python 3.13 if you can.** The PyTest Creator lints every *generated* script with
`py_compile` using the venv's interpreter, while those scripts execute under the **testbox's**
`python3` (tb470 is on 3.13.5). When the two differ the lint checks the wrong language
version. That is not hypothetical: the skeleton once shipped `from distutils.util import
strtobool`, valid on 3.10 and a hard `ImportError` on 3.12+, so every generated script with a
manual step would have died on import. `py_compile` cannot catch a missing module — only an
import can — so the lint also rejects stdlib modules removed in 3.12/3.13.

**A venv is not relocatable.** `pip` bakes an absolute shebang into every console script and
`activate` hardcodes its absolute `VIRTUAL_ENV`, so **moving the repo breaks the venv**.
`setup.sh` detects this and repairs the baked paths; to do it by hand:

```bash
command grep -rl '<old-path>' .venv/bin .venv/pyvenv.cfg \
  | xargs sed -i 's|<old-path>|<new-path>|g'
```

> `sentence-transformers` is **required** — semantic/hybrid search and the offline embedding
> model need it. A hand-built venv without a full `-r requirements.txt` install boots but
> silently degrades to keyword-only search. Verify with
> `PYTHONNOUSERSITE=1 .venv/bin/python -c "import sentence_transformers"` and check `/health`
> reports `sqlite_vec_loaded: true` with a non-zero `embeddings` count.

**Git LFS on Ubuntu:** apt ships 3.0.2, which fails `git lfs pull` on a fresh clone against
modern Git. Install from the git-lfs repo instead:
`curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash`

</details>

## The four invariants

Flag immediately if any of these is violated — they are load-bearing, and one is enforced by a
guard in the test gate.

1. **`ask-ck/db/ck.db` is the permanent single source of truth.** Built **once**, shipped via
   Git LFS, **not** gitignored, **not** rebuildable. A fresh clone gets a complete, populated,
   semantically-searchable database with no build step. `ask-ck/tools/build_db.py` is kept only as
   provenance and refuses to run. **It is committed deliberately, never routinely** — every
   version moves ~465 MB against the account's monthly LFS bandwidth allowance, so it carries
   `git update-index --skip-worktree` and does not appear in `git status`. See CLAUDE.md
   invariant 1 for how to take a snapshot, and why `.gitignore` is the wrong tool.
2. **The server reads corpora only from `ck.db`** — zero runtime JSON. Guard:
   `ask-ck/tools/guard_db_only.py`. (The Zephyr Templating Tool's live read of a project's wiki
   pages is an accepted exception: it is per-project input, not a corpus.)
3. **`/home/st-art/framework` is read-only.** Never write, edit or redirect into it; copy to a
   local staging path instead. This holds by construction: since 2026-10-12 the server has no
   code path to a testbox — runs go through the seat agent's `/test-mode` session and
   device-testing's bench-runner, whose own rules carry this.
4. **The org vLLM is the one live external dependency, and it is core function** — not an
   inter-dependency to remove. Its models are *reasoning* models. The embedding model is
   bundled and loads fully offline.

Tests, smoke checks and E2E must **not** write the permanent `ck.db` — use
`ask-ck/tools/run_scratch_server.sh`. `md5`/`mtime` cannot detect a write to it (WAL);
`tests/test_db_isolation.py` is the authority. Real user traffic *should* dirty it.

## The gate

```bash
./ask-ck/tools/run_tests.sh     # the guard + backend pytest + frontend Vitest + a ck.db signature check
```

Run it before and after a change. Three layers: **backend** (`tests/`, in-process — no mocks,
network or testbox; several are *structural*, e.g. an AST sweep proving no async handler calls
a blocking function unwrapped), **frontend units** (`tests/js/`, Vitest + jsdom, with DOM
fixtures lifted from the real `index.html` so they detect drift), and **E2E** (`tests/e2e/`, one
Playwright golden path) — which is deliberately **not** in the gate and is run sparingly via
`npm run e2e`. There is no CI runner.

## The data

Everything lives in `ask-ck/db/ck.db` (SQLite; FTS5 keyword + sqlite-vec semantic/hybrid
search, including literal script-code chunks):

| Corpus | Rows |
|---|---|
| Zephyr cases | 45,427 |
| TestLink cases | 21,620 |
| ATPyLib tests | 10,157 |
| AlliedWare Plus CLI commands | 3,535 (one combined docs zip since 2026-09-08; renewable) |
| Indexed scripts | 830 (5,782 code chunks) |
| Semantic embeddings | 83,816 |
| Zephyr template set | 14 plans / 15 cycles / 396 cases (refreshed from Zephyr on demand) |

(Counts read from the live server's `/health` on 2026-10-19; the CLI count was last read
2026-09-23 and the template set at its 2026-10-05 refresh.) The former on-disk courier corpora
were retired into `ck.db` and **deleted** — do not look for them on disk.

**Outputs:**
- **Refined cases** — `ask-ck/functions/generator/refined-cases/<Group>/AWPTCM-Txxxx/`, as
  `traceability.md` + `zephyr_payload.json`. A case is **Complete** once that bundle exists.
  Every case was rewound to square one on 2026-09-16; four have been re-exported since
  (T33233–T33236, Port).
- **Generated scripts** — `ask-ck/functions/pytest-creator/generated/<family>/`.
- **Run records** — `ask-ck/functions/test-composer/runs/<date>/<run id>/`, one per Test
  Composer run.

## The tools

Pick a backend first under **LLM → Configure** — most tools need it: **Local LLM** (the org
vLLM; Fast/Thinking toggle, Health check button) or **Claude Code CLI (my local machine)** (your
own seat through the agent; Haiku/Sonnet/Opus selector, reports tokens and cost). The choice is
**per seat**; a seat that never chose starts from the site default, which any seat's Apply
rewrites (Claude via the agent, Sonnet, on 2026-10-19). Every LLM panel has a **Provenance**
block that copies the exact prompt, or re-renders it live without sending (`dry_run`, zero
tokens) for use in another LLM.

The sidebar lists the tools in this order:

**Zephyr Templating Tool** — one page, **Organize Templates**. Paste a project's wiki page: the
tool reads its Test Strategy, TPS and Feature Page, and the model proposes which template plans,
cycles and cases the project can leave out, each with a cited source. Everything starts ticked,
and the server keeps a proposal only if it names a real key, a reason and a source, so a bad
answer can only fail to untick. You review the ticks and Confirm. **API Upload** then clones the
ticked plans and cycles into the project's folder for its AW+ version in Zephyr, after a
confirmation that names the product and version (the server re-checks both). An audit line is
written before every write; it stops at the first failure and never undoes automatically. The template set itself is snapshotted from Zephyr
into `ck.db` by *Refresh templates*. For a new feature with no template to clone,
`ask-ck/tools/zt_create.py` (command line, `--dry-run` / `--apply`) creates its cases, plan and
cycle under the same safety rules. Plan: [`ask-ck/plans/PLAN-zephyr-templating.md`](ask-ck/plans/PLAN-zephyr-templating.md).

**Test Composer** — three pages. Each one starts device-testing's `/test-mode` as a full Claude
Code session **on your own seat** (through the agent and the Claude Agent SDK) and streams it
into the page; results are read only from agreed marker lines, never from prose.
- **Validate a Script** — one saved script: probe the bench, check it can run the script, run
  it, repair a *copy* until the run is clean (the original is overwritten only with your
  approval), review it, then **Finalize** it.
- **Compose a Run** — a project's runnable cases on a template bench, with results by cycle.
- **Run Scripts** — finalized scripts, several at once, in the order you tick them, now or at
  a one-off start time; a shareable link refills the page (never the email, never a launch). No repair
  or review.

**PyTest Creator** — turns a Complete case into a runnable `framework` (ATTestSet / ATTestCase)
script over five gated steps: *Cases* → *Sequence* (the LLM extracts automatable steps,
classified **setup / verify / physical / manual**) → *Script Search* → *Fragments* (reusable
symbols resolved to real source by line range) → *Generate* (the LLM fills a fixed skeleton;
lint enforces conformance). Confirming *Generate* saves the script to `generated/` and offers to
test it in **Validate a Script**. Physical steps are **in scope**: they generate an operator
prompt plus a wait-for-state-change poll, and manual checks generate a `yesNo()`. Scripts are
hardware-agnostic — the frame discovers its topology from the bench through the framework.

**Objective / Test Case Generator** — the original tool. Turns a sparse manual case into a
refined one over six gated steps: *Cases* → *TestLink* → *Zephyr* → *ATPyLib (scored)* →
*Objectives (LLM)* → *Test Steps (LLM)*, then **Export the Repeatable Bundle**. Review steps
2–4 use a two-table "chosen shortlist": search/suggest results land in the top candidates
table, and **Confirm reads only the bottom chosen table**. A seventh action pushes the exported
bundle to the live Zephyr case (dry-run Preview first; takes the case to version 2.0, never
higher; shells out to `ask-ck/frontend/ck-main/current/generator/upload_refined.py` so the
server never holds the Jira token).

Before touching lab hardware, read [`TESTBOX-ACCESS.md`](TESTBOX-ACCESS.md) in full.

## Repository layout

```
Test-cases/
├── CHANGELOG.md                    # Feature history (newest first)
├── SESSION_STATE.md                # Long-form session history
├── TESTBOX-ACCESS.md               # Read before touching lab hardware (symlink → ../device-testing/)
├── TB470-HOST-NETWORKING.md        # The tb470 Linux host itself: DHCP, routing, packet capture
├── docs/                           # Repo-level documents: reviewer onboarding, reports, the ATUI design system
├── tests/                          # The whole test layer: pytest at tests/, Vitest at tests/js/, Playwright at tests/e2e/
├── archive/                        # Retired tools, completed plans, closed records — kept, not live
└── ask-ck/
    ├── ARCHITECTURE.md             # Executive summary — read before the deep reference
    ├── CK-main/                    # Backend: run.sh, requirements.txt, SERVER-README.md
    │   └── CK_server/              # FastAPI server (main.py, paths.py, routers/, templates/)
    ├── frontend/ck-main/
    │   ├── current/                # Classic, served at /classic: index.html, styles.css, one directory per page
    │   │                           #   (generator/, pytest-creator/, test-composer/, validation/,
    │   │                           #   zephyr-tool/, llm-config/, admin/, shared/)
    │   │   ├── svelte-src/         #   Svelte source for the Test Composer and ZTT pages
    │   │   └── islands/            #   …and its built bundles, committed (no build step on the server)
    │   ├── restyle/                # The ATUI restyle — UNSERVED since 2026-10-30 (files kept); own HTML + CSS, current/'s JS
    │   └── svelte/                 # The Svelte app served at / (Trent's); dist/ committed — ask-ck/tools/build_svelte_app.sh
    ├── functions/                  # One directory per page: its data, results and docs
    │   ├── generator/              # PROGRESS.md, OBJECTIVE_DRAFTING_PROCESS.md, refined-cases/
    │   ├── pytest-creator/         # Specs (TOPOLOGY-PROFILES, TEMPLATE-SPEC, …) and generated/
    │   ├── test-composer/          # runs/ (run records), templates/ (bench topologies + configs), ART chain doc
    │   └── zephyr-tool/            # README (the tool's data lives in ck.db; its page is current/zephyr-tool/)
    ├── tools/                      # Every script not called by a page button: gate, guard, checkers,
    │                               #   corpus loaders, the zt_* Zephyr tools
    ├── plans/                      # Active plans (PLAN-*.md) + DECISIONS-FOR-REVIEW.md
    ├── agent/                      # The seat agent (Linux + Windows), served at /setup/
    └── db/                         # ck.db — THE permanent database (Git LFS) + the embedding model
```

## Documentation map

| Doc | Use for |
|---|---|
| [`ask-ck/functions/generator/PROGRESS.md`](ask-ck/functions/generator/PROGRESS.md) | **Start here** — status, backlog, handoff (newest entry at the top) |
| [`ask-ck/ARCHITECTURE.md`](ask-ck/ARCHITECTURE.md) | Executive summary — system shape, the invariants, where the risk sits |
| [`ask-ck/CK-main/SERVER-README.md`](ask-ck/CK-main/SERVER-README.md) | The deep technical reference — run, architecture, LLM modes, agent sessions, nginx |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed, when, and **why** |
| [`ask-ck/functions/generator/OBJECTIVE_DRAFTING_PROCESS.md`](ask-ck/functions/generator/OBJECTIVE_DRAFTING_PROCESS.md) | The Generator's authority (Steps 1–2) |
| [`ask-ck/plans/PLAN-pytest-creator.md`](ask-ck/plans/PLAN-pytest-creator.md) | PyTest Creator plan + progress tracker |
| [`ask-ck/functions/pytest-creator/TOPOLOGY-PROFILES.md`](ask-ck/functions/pytest-creator/TOPOLOGY-PROFILES.md) | What a bench must cable, and how a generated script discovers its topology |
| [`ask-ck/functions/pytest-creator/SETUP-FILE-REFERENCE.md`](ask-ck/functions/pytest-creator/SETUP-FILE-REFERENCE.md) | `.setup` topology schema + a worked example |
| [`ask-ck/plans/PLAN-agent-sessions.md`](ask-ck/plans/PLAN-agent-sessions.md) | How Ask CK starts and talks to a `/test-mode` session on a seat |
| [`ask-ck/plans/PLAN-test-validation.md`](ask-ck/plans/PLAN-test-validation.md) | Validate a Script: run, repair, review, Finalize |
| [`ask-ck/plans/PLAN-test-composer.md`](ask-ck/plans/PLAN-test-composer.md) | Compose a Run: a project's cases on a template bench |
| [`ask-ck/plans/PLAN-run-scripts.md`](ask-ck/plans/PLAN-run-scripts.md) | Run Scripts: finalized scripts, several at once, from a link |
| [`ask-ck/plans/PLAN-zephyr-templating.md`](ask-ck/plans/PLAN-zephyr-templating.md) | The Zephyr Templating Tool: design, decisions, the upload's requests |
| [`ask-ck/agent/README.md`](ask-ck/agent/README.md) | The seat agent: install, update, what it runs |
| [`ask-ck/functions/generator/LESSONS_LEARNED.md`](ask-ck/functions/generator/LESSONS_LEARNED.md) | Prior decisions and pitfalls |
| [`docs/resources.md`](docs/resources.md) | Links to TestLink, Zephyr, ART |
| [`ask-ck/plans/PLAN-svelte-cutover.md`](ask-ck/plans/PLAN-svelte-cutover.md) | The 2026-10-30 cutover: the Svelte app at `/`, Classic at `/classic`, the restyle unserved; decisions D1–D9, the known-issue checklist |
| [`archive/plans/PLAN-atui-restyle.md`](archive/plans/PLAN-atui-restyle.md) | The ATUI restyle (unserved since 2026-10-30): settled decisions S1–S16, wording + icon lists |
| [`docs/ATUI Design System/`](<docs/ATUI Design System/readme.md>) | Allied Telesis UI guidance from governance (received 2026-09-30). Also the `atui-design` skill, linked from `.claude/skills/` |
| [`docs/`](docs/) | Repo-level documents: reviewer onboarding, the token-efficiency report, the memory-split inventory, captured prompts |

**Session workflow:** run **`/orient-ck`** at the start of a working session and **`/wrap-ck`** at
the end — project skills in [`.claude/skills/`](.claude/skills/). `/orient-ck` ground-truths the
live repo (git, guard, gate), reads the newest handoff, and confirms the invariants before any
work begins; `/wrap-ck` reconciles the docs against what actually shipped and commits. Both are
plain Markdown with no tool-specific syntax — paste a `SKILL.md` body into any other assistant if
you are not using Claude Code.

**Security posture:** there is **no authentication**. The server binds `127.0.0.1` by default
(LAN exposure is an explicit `HOST=0.0.0.0`), but the hosted server of record has run on the LAN
since 2026-08-26, open admin panel included — accepted for now on 2026-09-23, with LDAP or
similar to come later. **Per-case locking** (2026-07-29): `CK_server/locks.py` holds a lock per
(tool, case), so a second tab gets a read-only view instead of silently overwriting the first,
with an optimistic `rev` compare-and-swap as backstop. The registry is **in memory on purpose**
(a durable table would have been the first in-place schema change to the permanent `ck.db`), so
a server restart clears every lock until the page holding it reloads, and running multi-worker
would silently bring back the overwrite bug — `locks.py` says so prominently. Identity and
attribution remain planned in
[`ask-ck/plans/PLAN-auth-and-case-locking.md`](ask-ck/plans/PLAN-auth-and-case-locking.md).
Never commit credentials — `secrets.md`, `secrets.local.json` and `secrets.testboxes.json` (the
retired testbox profiles) are gitignored.

> **Note:** primary development is on an internal machine; this GitHub tree is a published
> copy. On 2026-07-13 the repo was restructured (`drafting-tool/` → `ask-ck/CK-main/`; root
> `data/` and `refined-cases/` → `ask-ck/functions/generator/`), and again on 2026-09-11
> (`archive/plans/PLAN-restructure-2026-09-11.md`), so historical documents may still reference
> pre-move paths.

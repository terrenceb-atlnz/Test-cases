<p align="center">
  <img src="ask-ck/CK-main/CK_server/static/ckc.jpg" alt="Ask CK" width="140" style="border-radius:50%;" />
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

Ask CK is a server-backed test-engineering workbench for the **AWPTCM** test-case program.
It takes a sparse Zephyr manual test case, enriches it into a refined case with declarative
objectives and reviewable steps, and then turns that into a runnable Allied Telesis
`framework` test script — with a human confirm gate at every stage.

It draws on two historical silos to decide what a case *should* verify:

| Source | Role |
|---|---|
| **TestLink** (historical) | Detailed human-authored cases (`AWP-*`) for artefact context and overlap |
| **ATPyLib** (automated) | Enriched suites describing what automation actually tests *for* |

**Authoritative process:**
[`ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`](ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md).

## Quick start

```bash
git clone https://github.com/terrenceb-atlnz/Test-cases.git
cd Test-cases
./setup.sh          # idempotent; safe to re-run
```

`setup.sh` runs a preflight and prompts before each fix (needs `sudo` for installs): base
toolchain (`git`, `git-lfs`, `curl`) → **Python ≥ 3.10** → **Git LFS ≥ 3.3** + `git lfs pull`
→ virtual environment + dependencies → verify `ask-ck/var/ck.db` → offer to launch.

After the first successful setup you almost always just want `run.sh`:

```bash
./run.sh            # foreground (asks fg/bg the first time)
./run.sh --bg       # background, no prompts
./run.sh --restart  # stop + background start
./run.sh --stop     # stop the background server
```

Then open **`http://localhost:8000/`**. Root `./run.sh` is a thin wrapper around the real
launcher at `ask-ck/CK-main/run.sh`; either works.

> **Use `http://`, not `https://`.** Ask CK serves plain HTTP. Browsers with HTTPS-Only mode
> (Firefox, HSTS) auto-upgrade and show a blank `SSL_ERROR_RX_RECORD_TOO_LONG` page — the
> failure is at the TLS layer, so a same-port redirect is impossible. Exempt localhost.

**`setup.sh` vs `run.sh`:** `setup.sh` is the superset — prerequisites, LFS pull, venv, and a
`ck.db` sanity check, then it delegates to `run.sh` to launch. Use it for first-time setup or
when the toolchain changed. `run.sh` does none of that; it only starts the server. The server
runs with `--reload`, so **code edits hot-reload** — restart only for environment or
dependency changes.

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

Flag immediately if any of these is violated — they are load-bearing, and two are enforced by
guards in the test gate.

1. **`ask-ck/var/ck.db` is the permanent single source of truth.** Built **once**, shipped via
   Git LFS, **not** gitignored, **not** rebuildable. A fresh clone gets a complete, populated,
   semantically-searchable database with no build step. `tool/build_db.py` is kept only as
   provenance and refuses to run.
2. **The server reads corpora only from `ck.db`** — zero runtime JSON. Guard:
   `tool/guard_db_only.py`.
3. **`/home/st-art/framework` is read-only.** Never write, edit or redirect into it; copy to a
   local staging path instead. Guard: `tool/guard_framework_readonly.py`.
4. **The org vLLM is the one live external dependency, and it is core function** — not an
   inter-dependency to remove. Its models are *reasoning* models. The embedding model is
   bundled and loads fully offline.

Tests, smoke checks and E2E must **not** write the permanent `ck.db` — use
`tool/run_scratch_server.sh`. `md5`/`mtime` cannot detect a write to it (WAL);
`tests/test_db_isolation.py` is the authority. Real user traffic *should* dirty it.

## The gate

```bash
./tool/run_tests.sh     # both guards + backend pytest + frontend Vitest
```

Run it before and after a change. Three layers: **backend** (`tests/`, in-process — no mocks,
network or testbox; several are *structural*, e.g. an AST sweep proving no async handler calls
a blocking function unwrapped), **frontend units** (`js-tests/`, Vitest + jsdom, with DOM
fixtures lifted from the real `index.html` so they detect drift), and **E2E** (`e2e/`, one
Playwright golden path) — which is deliberately **not** in the gate and is run sparingly via
`npm run e2e`. There is no CI runner.

## The data

Everything lives in `ask-ck/var/ck.db` (SQLite; FTS5 keyword + sqlite-vec semantic/hybrid
search, including literal script-code chunks):

| Corpus | Rows |
|---|---|
| Zephyr cases | 45,427 |
| TestLink cases | 21,620 |
| ATPyLib tests | 10,157 |
| AlliedWare Plus CLI commands | 6,323 |
| Indexed scripts | 830 |
| Semantic embeddings | 83,816 |

The former on-disk courier corpora were retired into `ck.db` and **deleted** — do not look for
them on disk. What remains under `ask-ck/objective-drafting/data/` is the immutable Zephyr XML
export (LFS) that `ck.db` was built from, enrichment *docs*, and review scratch.

**Output:** refined cases are exported to
`ask-ck/objective-drafting/refined-cases/<Group>/AWPTCM-Txxxx/` as `traceability.md` +
`zephyr_payload.json`. A case is **Complete** once that bundle exists. There are currently
**53** across Port, IPv4, Switching, QoS, Sanity Check, Authentication & Security, Management,
Bootloader and Other.

## The tools

Pick a backend first under **LLM → Configure** — most tools need it: **Local LLM** (org vLLM,
default; Fast/Thinking toggle, Health check button), **Claude Code CLI** (per-user local
agent, Haiku/Sonnet/Opus selector, reports tokens + cost), or **Grok CLI**. Every LLM panel
exposes a **Provenance** block that copies the exact prompt, or re-renders it live without
sending (`dry_run`, zero tokens) for use in a competing LLM.

**Objective / Test Case Generator** — the original tool. Turns a sparse manual case into a
refined one over six gated steps: *Cases* → *TestLink* → *Zephyr* → *ATPyLib (scored)* →
*Objectives (LLM)* → *Test Steps (LLM)*, then **Export the Repeatable Bundle**. Review steps
2–4 use a two-table "chosen shortlist": search/suggest results land in the top candidates
table, and **Confirm reads only the bottom chosen table**. A seventh action pushes the
exported bundle to the live Zephyr case (dry-run Preview first; ensures version 2.0; shells
out to `tool/upload_refined.py` so the server never holds the JIRA token).

**PyTest Creator** — turns a Complete case into a runnable `framework` (ATTestSet /
ATTestCase) script over seven gated steps: *Cases* → *Sequence* (LLM extracts automatable
steps, classified **setup / verify / physical / manual**) → *Script Search* → *Fragments*
(reusable symbols resolved to real source by line range) → *Generate* (the LLM fills a fixed
skeleton; lint enforces conformance) → *Run* (over SSH on a stored testbox) → *Validate*.
Physical steps are **in scope**: they generate an operator prompt plus a wait-for-state-change
poll, and manual checks generate a `yesNo()`.

**Test Composer** and **Zephyr Templating Tool** — scaffolded, not yet implemented.

Stored testboxes live in the gitignored `secrets.testboxes.json`. Before touching lab
hardware, read [`TESTBOX-ACCESS.md`](TESTBOX-ACCESS.md) in full.

## Repository layout

```
Test-cases/
├── CHANGELOG.md                    # Feature history (newest first)
├── SESSION_STATE.md                # Long-form session history
├── TESTBOX-ACCESS.md               # Read before touching lab hardware
├── ask-ck/
│   ├── ARCHITECTURE.md             # Executive summary — read before the deep reference
│   ├── CK-main/                    # App: run.sh, requirements.txt, SERVER-README.md
│   │   └── CK_server/              # FastAPI server (main.py, routers/, static/js/, templates/)
│   ├── objective-drafting/         # Generator: process docs, PROGRESS.md, data/, refined-cases/
│   ├── pytest-create/              # PyTest Creator: plans, specs, generated/<Group>/<Name>.py
│   ├── ck-facelift/                # Subsystem plans (PLAN-*.md)
│   └── var/ck.db                   # THE permanent database (Git LFS)
└── tool/                           # Guards, the test gate, upload_refined.py, checkers
```

## Documentation map

| Doc | Use for |
|---|---|
| [`ask-ck/objective-drafting/PROGRESS.md`](ask-ck/objective-drafting/PROGRESS.md) | **Start here** — status, backlog, handoff (newest entry at the top) |
| [`ask-ck/ARCHITECTURE.md`](ask-ck/ARCHITECTURE.md) | Executive summary — system shape, the invariants, where the risk sits |
| [`ask-ck/CK-main/SERVER-README.md`](ask-ck/CK-main/SERVER-README.md) | The deep technical reference — run, architecture, LLM modes, nginx |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed, when, and **why** |
| [`ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md`](ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md) | The Generator's authority (Steps 1–2) |
| [`ask-ck/pytest-create/PLAN-pytest-creator.md`](ask-ck/pytest-create/PLAN-pytest-creator.md) | PyTest Creator plan + progress tracker |
| [`ask-ck/pytest-create/TOPOLOGY-PROFILES.md`](ask-ck/pytest-create/TOPOLOGY-PROFILES.md) | Topology contract that generated scripts target |
| [`ask-ck/pytest-create/SETUP-FILE-REFERENCE.md`](ask-ck/pytest-create/SETUP-FILE-REFERENCE.md) | `.setup` topology schema + a worked example |
| [`ask-ck/objective-drafting/LESSONS_LEARNED.md`](ask-ck/objective-drafting/LESSONS_LEARNED.md) | Prior decisions and pitfalls |
| [`resources.md`](resources.md) | Links to TestLink, Zephyr, ART |

**Session workflow:** run **`/orient`** at the start of a working session and **`/wrap`** at
the end — project skills in [`.claude/skills/`](.claude/skills/). `/orient` ground-truths the
live repo (git, guards, gate), reads the newest handoff, and confirms the invariants before
any work begins; `/wrap` reconciles the docs against what actually shipped and commits. Both
are plain Markdown with no tool-specific syntax — paste a `SKILL.md` body into any other
assistant if you are not using Claude Code.

**Security posture:** designed for **localhost / single user**. The server binds `127.0.0.1`
by default (LAN exposure is an explicit `HOST=0.0.0.0`) and there is still **no
authentication**. **Per-case locking is DONE** (Phase 1, 2026-07-29): `CK_server/locks.py`
holds a lock per (tool, case) so a second tab gets a read-only view instead of silently
overwriting the first — the whole-blob session write that made that possible is still there,
with an optimistic `rev` compare-and-swap as backstop. The registry is **in-process on
purpose** (a durable table would have been the first in-place schema change to the permanent
`ck.db`), so running multi-worker would silently reintroduce the overwrite bug — `locks.py`
says so prominently. Multi-user **identity** (Phase 2) and attribution + TLS (Phase 3) remain
planned in
[`ask-ck/ck-facelift/PLAN-auth-and-case-locking.md`](ask-ck/ck-facelift/PLAN-auth-and-case-locking.md),
gated on an organisational decision. Never commit credentials — `secrets.md`,
`secrets.local.json` and `secrets.testboxes.json` are gitignored.

> **Note:** primary development is on an internal machine; this GitHub tree is a published
> copy. On 2026-07-13 the repo was restructured (`drafting-tool/` → `ask-ck/CK-main/`; root
> `data/` and `refined-cases/` → `ask-ck/objective-drafting/`), so historical documents may
> still reference pre-move paths.

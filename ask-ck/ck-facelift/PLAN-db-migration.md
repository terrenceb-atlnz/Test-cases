# Ask-CK Data Layer: JSON/JSONL/XML → SQLite (FTS5 + sqlite-vec)

> ⚠ **Superseded premise (2026-07-20c):** this plan describes `ck.db` as a "derived,
> rebuildable cache" built from JSON/JSONL/XML couriers (rebuild `build_db.py --fresh
> --verify`). That flipped — **`ck.db` is now the PERMANENT single source of truth**:
> built once, committed via Git LFS, NOT rebuildable, with the courier/source files
> DELETED and the rebuild path removed. The migration steps below are accurate history;
> the "rebuildable cache" framing is not the current model. Current source of truth:
> `ask-ck/var/ck.db` — see `PLAN-db-only-search.md` and the `db-is-permanent-source` memory.

> ## Session handoff (read first)
>
> **Status (2026-07-16): ✅ COMPLETE — all four commits landed** (A `6cb97ca`, B `bdb2043`, C `14cf4ad`, D `1a0ef2a`). Corpora + sessions are served from `ask-ck/var/ck.db` (rebuild: `python3 tool/build_db.py --fresh --verify`). Note: some scoring formulas below are stale — the live parity target is `_relevance_score`. **Follow-on direction:** strict DB-only search → `PLAN-db-only-search.md`.
>
> **Status (2026-07-15):** Plan approved by Terrence; **no code written yet**. Execution starts at Commit A below.
>
> - **All decisions in this plan are settled** — engine, scope, hybrid search, and score-preservation were agreed interactively. Don't re-litigate them; if something proves wrong during implementation, surface it.
> - **Line numbers were verified against the working tree at planning time** (commit `269acc4`). If files have changed since, re-locate by function name (`_get_full_zephyr_cases_batch`, `_persist_session`, `_search_testlink`, `_score_script_candidate`, …), not by line.
> - **Sibling plan:** `PLAN-es-module-split.md` (same directory) is also approved and pending. The two are **independent** — this one touches only server/Python (`CK_server/*.py`, `tool/`), that one touches only `CK_server/static/`. Either order works with no conflicts.
> - **Environment:** server runs via `ask-ck/CK-main/run.sh` (uvicorn, port 8000, needs `LLM_API_KEY` or local CLI logins); repo venv at `.venv/`. Data dirs anchored in `CK_server/paths.py`. Live session files in `CK_server/sessions/` — treat as production data, never delete (Commit C keeps them as frozen backup).
> - **Verification is manual by preference** — no Playwright. Each commit stage below has its own verify steps; the search-parity comparison script belongs in the session scratchpad, not the repo.
> - **Before Commit D:** the embedding model must be pre-fetched into `ask-ck/var/models/` on a machine with huggingface.co access (internal network may not have it). Check reachability first; if absent, ask Terrence to provide the model dir rather than stalling.

## Context

Ask-CK's two data-heavy tools — the TestCase Generator (wizard) and PyTest Creator — currently run on flat files: ~53 MB of JSON corpora loaded into RAM at every server boot (45,427 Zephyr cases, 21,624 TestLink cases, 10,157 ATP suite tests, 830 indexed scripts), a 54 MB `zephyr_cases.jsonl` that is **linearly scanned on every case-load request** ([wizard.py:159-190](ask-ck/CK-main/CK_server/routers/wizard.py#L159), via a CWD-relative path), and per-case session JSON files. "Free search" is in-memory substring token counting. The code already flags the fix ("replace with DB later", `wizard.py:42`, `pytest_create.py:36`; `extract_zephyr_xml.py` docstring anticipates "zephyr.db: SQLite + FTS").

**Feasibility: high.** The LLM layer never reads files — routers retrieve top-N candidates mechanically and pass trimmed lists into prompts — so swapping the retrieval layer doesn't touch `llm.py` or the frontend.

**Decisions (agreed with user):** SQLite + FTS5 (single file, WAL, zero ops; Postgres only if multi-instance ever needed). Scope = corpora + sessions. Refined-case exports, generated .py scripts, and `secrets.testboxes.json` stay files. Search = FTS5 BM25 keyword **and** semantic vector search (sqlite-vec + local sentence-transformers; swappable, resumable, keyword-only degrade). DB is a **derived, rebuildable cache** — XML/extractor JSON outputs remain source of truth.

**Score constraint (verified):** app.js renders absolute scores and merges LLM vs. search rows by comparing raw score values (app.js:2272-2289) — existing score formulas must be preserved for retrieved rows.

## Layout

- DB: `ask-ck/var/ck.db`; model cache `ask-ck/var/models/`. Add to [paths.py](ask-ck/CK-main/CK_server/paths.py): `VAR_DIR`, `DB_PATH`, `EMBED_MODEL_DIR`. Gitignore `ask-ck/var/`.
- New files: `CK_server/schema.sql`, `CK_server/db.py` (no FastAPI imports — tool/ scripts already sys.path-insert CK_server, see `tool/enrich_script_index.py:28`), `tool/build_db.py`.
- Retire later (stop reading now, delete in a future cleanup): `zephyr_full/slim_index.json`, `scripts_slim_index.json`, `suites/all_test_suites.json` + `.csv`.

## Schema (DDL sketch — full DDL in schema.sql)

Normalization policy: normalize what is searched/filtered; keep rarely-individually-queried nested data as JSON1 columns (`steps`, `labels`, `helpers`, `test_cases`, `log_analysis`). Steps get a flattened `steps_text` column feeding FTS — no child step tables (nothing queries a single step).

```sql
PRAGMA journal_mode=WAL;
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);  -- schema_version, source sha1/mtimes, counts

CREATE TABLE zephyr_cases (          -- 45,427 xml + 410 api-target merged; api wins on conflict
  id INTEGER PRIMARY KEY, key TEXT NOT NULL UNIQUE, src TEXT NOT NULL,  -- 'api'|'xml'
  is_target INTEGER NOT NULL DEFAULT 0,          -- 1 = the 410 zephyr_master cases
  title TEXT NOT NULL DEFAULT '', folder TEXT NOT NULL DEFAULT '',
  objective TEXT, precondition TEXT, priority TEXT, status TEXT,
  labels TEXT, script_type TEXT, script_text TEXT, steps TEXT,          -- JSON
  steps_text TEXT NOT NULL DEFAULT '', num_steps INTEGER NOT NULL DEFAULT 0,
  has_objective INTEGER NOT NULL DEFAULT 0, content_sha1 TEXT NOT NULL);

CREATE TABLE testlink_cases (id TEXT PRIMARY KEY, internal_id TEXT, title TEXT NOT NULL DEFAULT '',
  suite_top TEXT, suite TEXT, summary TEXT, preconditions TEXT, importance TEXT, status TEXT,
  steps TEXT, steps_text TEXT NOT NULL DEFAULT '',   -- first 20 steps (matches wizard.py:966 blob)
  content_sha1 TEXT NOT NULL);

CREATE TABLE atp_tests (tid TEXT PRIMARY KEY,        -- "suite.testSet.caseId"
  suite_id TEXT NOT NULL, suite_name TEXT NOT NULL,  -- NOT NULL: past schema drift silently dropped 12 suites
  test_set TEXT, case_id TEXT, description TEXT NOT NULL DEFAULT '', reference TEXT,
  past_crs TEXT, current_crs TEXT, log_analysis TEXT,
  is_functional INTEGER NOT NULL DEFAULT 1,          -- precomputed "(not a functional test)" filter
  content_sha1 TEXT NOT NULL);

CREATE TABLE scripts (id TEXT PRIMARY KEY, db TEXT, path TEXT NOT NULL, suite_dir TEXT, kind TEXT,
  sha1 TEXT NOT NULL, mtime REAL, loc_total INTEGER, parse_error TEXT,
  title TEXT, summary TEXT, docstring TEXT,
  feature_tags TEXT, covered_actions TEXT, imports TEXT, testset TEXT, test_cases TEXT, helpers TEXT,
  tags_text TEXT NOT NULL DEFAULT '', dir_text TEXT NOT NULL DEFAULT '');

CREATE TABLE candidates (case_key TEXT PRIMARY KEY REFERENCES zephyr_cases(key), payload TEXT NOT NULL);
CREATE TABLE decisions (key TEXT PRIMARY KEY, matched_id TEXT, confidence TEXT, rationale TEXT,
  source_file TEXT NOT NULL);
CREATE TABLE json_docs (name TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT);  -- framework_surface, meta

CREATE TABLE sessions (id TEXT PRIMARY KEY,          -- 'AWPTCM-Txxxx' | 'pt-…' | '_workspace_llm'
  kind TEXT NOT NULL CHECK (kind IN ('wizard','pt','workspace')), case_key TEXT,
  payload TEXT NOT NULL,          -- model dump MINUS llm_config
  llm_config TEXT,                -- separate column: never selected by logs/progress queries
  updated_at TEXT NOT NULL);
```

**FTS5 — external-content** (one copy of text, `bm25()` weights, `snippet()`, `('rebuild')` support):

```sql
CREATE VIRTUAL TABLE zephyr_fts USING fts5(key, title, folder, objective, steps_text,
  content='zephyr_cases', content_rowid='id',
  tokenize="unicode61 remove_diacritics 2 tokenchars '._+'", prefix='2 3');
-- likewise: testlink_fts(id,title,summary,steps_text), atp_fts(tid,description,suite_name),
--           scripts_fts(id,title,summary,tags_text,dir_text,docstring)
```

Tokenizer keeps `test_id`/`10.1.2` tokens intact (matches existing regex `[a-z0-9][a-z0-9._+-]{1,}`) but excludes `-` so `auto-negotiation` → `auto`,`negotiation`; query side splits hyphens identically. Sync via standard external-content triggers, plus `('rebuild')` at end of every ingest (corpora only written by build script anyway).

**Vectors (sqlite-vec, 384-dim):** `vec_zephyr/vec_testlink/vec_atp/vec_scripts USING vec0(embedding float[384])`, rowid-keyed to base tables; `embeddings_meta(entity, base_rowid, content_sha1, model, embedded_at)` for resumability (the `enrich_script_index.py` sha1 pattern). Embedded text: zephyr `title+objective` (fallback title+folder), testlink `title+summary`, atp `description`, scripts `title+summary+feature_tags`.

## db.py access layer

Plain **sync sqlite3** (queries are ms-scale; no async ceremony): module-level `threading.local()` connections, `row_factory=sqlite3.Row`, PRAGMAs WAL / `synchronous=NORMAL` / `busy_timeout=5000` / `mmap_size=256MB`. sqlite-vec loaded in try/except → `HAS_VEC` flag drives keyword-only degrade; server never fails startup over embeddings.

**Connection layer — single factory, no exceptions.** One public `get_connection() -> sqlite3.Connection` is the *only* place `sqlite3.connect()` is called anywhere in the codebase; every router and every `tool/` script goes through it, so PRAGMAs, WAL mode, and `enable_load_extension`/sqlite-vec loading are applied identically in one spot (never re-opened ad hoc). Location resolves as `os.getenv("CK_DB_PATH", str(DB_PATH))` — `paths.py` default, env-overridable, matching the existing `CK_EMBED_MODEL`/`SENTENCE_TRANSFORMERS_HOME` convention. Unlike a networked-service connector (fresh connection per call + `close()`), SQLite is an embedded file so the factory **reuses one connection per thread** via `threading.local()` — re-opening and re-applying PRAGMAs/extension-load on every retrieval call would be pure waste. Callers still never touch a cursor directly; they call the domain functions below, which call `get_connection()` internally.

API surface (return shapes identical to today's `_search_*` outputs incl. score/justification):

```python
get_target_cases(); get_case(key); get_zephyr_cases_batch(keys)   # kills the JSONL scan
get_candidates(key); get_current_case_keys(); get_decisions(); get_decision(key)
get_testlink_case(id); get_atp_test(tid); get_script(id); iter_scripts_slim(); get_json_doc(name)
search_testlink(q, limit=20); search_zephyr(q, exclude_keys, limit=20)
search_atp(q, limit=20); search_scripts(query_tokens, db_filter="", limit=40)
rank_zephyr_candidates(primary, extra_tokens, k=200)   # Step-2 pre-ranker feed
search_*_hybrid(...)            # Stage D; falls back to keyword when not HAS_VEC
embed_texts(texts)              # lazy model load; CK_EMBED_MODEL env swappable
save_session(kind,key,payload); load_session(kind,key); delete_session(kind,key)
list_session_progress()         # json_extract over step confirmed flags
startup_check()                 # meta mtimes vs source files → stale warning (no auto-rebuild)
```

Routers keep their private wrappers (`_search_testlink` etc.) with unchanged signatures; bodies become one-line delegations — endpoints and app.js untouched.

## tool/build_db.py

Idempotent full rebuild (~1–2 min; embeddings are the only incremental part). Streams the 54 MB JSONL line-by-line; `executemany` batches of 1,000; per-source transaction; prints counts. Ingests: zephyr_cases.jsonl (`src='xml'`) → zephyr_master.json upsert (`src='api', is_target=1`) → testlink_awp.json → test_id_description.json (**abort loudly if suite_id/suite_name missing** — the historical silent-drop bug becomes a named error) → scripts_index.json (enrichment already merged in) → candidates.json, decisions/*.json, framework_surface.json, scripts_index.meta.json. Then FTS `('rebuild')` × 4 and source sha1/mtimes into `meta`.

Flags: `--fresh`, `--embed [--batch 64] [--limit N]` (resumable, Ctrl-C-safe), `--sessions` (one-shot import), `--verify` (counts vs sources + spot lookups).

**Extractors unchanged this pass** — refresh recipe becomes "run extractor(s), then `python3 tool/build_db.py --embed`". Update `extract_zephyr_xml.py` docstring only.

## Sessions

One-shot import: `AWPTCM-*.json` → `kind='wizard'`, `pt-*.json` → `kind='pt'`, `_workspace_llm.json` → `kind='workspace'`. **Files stay in place as frozen backup.** Rewrite: `wizard.py:116/130/142` persist/load/clear, `pytest_create.py:64/74` `_pt_persist`/`_pt_load`, workspace-LLM helpers, `wizard.py:757 _session_progress_map` → `db.list_session_progress()`. `llm_config` (may hold plaintext api_key) stored as-is but in its own column so payload queries never leak it — encryption-at-rest noted as debt. **Refined-case detection stays a glob** (`_refined_complete_keys`, `_find_refined_case`) — refined cases stay files; a tracking table would drift.

## Search parity

Pattern for all four searches — **FTS retrieves, Python re-scores with the existing formulas**:
1. Tokenize with existing regexes (+ hyphen split), drop `_ZREF_GENERIC_TOKENS` as today.
2. FTS MATCH with OR-of-tokens + prefix variants (`tok*`); rank by weighted `bm25()`; fetch top ~200 rowids. BM25 weights approximate current heuristics (scripts `tags_text:12, dir_text:10, title/summary:6, docstring:2`; zephyr `key:5,title:4,folder:3,objective:2,steps:1`; testlink `id:5,title:4,summary:2,steps:1`; atp `tid:5,description:2,suite_name:2`).
3. Re-score retrieved rows with **unchanged** logic: `min(0.95, 0.4+0.1*hits)` testlink (wizard.py:977), `0.4+0.12*hits` zephyr (:1025), `0.45+0.1*hits` ATP (:1136), `_score_script_candidate` 12/10/6 weights verbatim (pytest_create.py:278) — scores and justification strings bit-identical wherever recall overlaps.
4. Keep zephyr title-stem dedup + exclusion set as post-filters. `_score_zephyr_candidate` (wizard.py:317) keeps its scoring verbatim, fed by `rank_zephyr_candidates` FTS pre-filter (~500 rows instead of 45k iteration).

Known delta (document in commit message): no mid-word substring recall (`egotiation` won't match; `negot*` will). Hybrid semantic search compensates.

**Hybrid merge (Stage D):** Reciprocal Rank Fusion `Σ 1/(60+rank)` across keyword+vector lists. Keyword rows keep formula scores; vector-only rows get `min(0.95, round(0.35 + 0.5*cos_sim, 2))`, `justification="Semantic match (cos N.NN)"`, `source="search"` — app.js merge keeps working. Endpoints gain `mode=keyword|hybrid|semantic`, default hybrid when `HAS_VEC` else keyword.

## Embeddings

Model: **`sentence-transformers/all-MiniLM-L6-v2`** (384-dim, ~90 MB, CPU-fast, no query-prefix conventions). Swappable via `CK_EMBED_MODEL`; `embeddings_meta.model` + `content_sha1` key vectors so a model switch auto-invalidates. Volume ~78k texts → **~3–8 min full CPU pass**, incremental re-runs seconds. requirements.txt: `sqlite-vec`, `sentence-transformers`, `torch` (comment: install CPU wheel via `--index-url https://download.pytorch.org/whl/cpu`). **Internal-network note:** first run downloads from huggingface.co — pre-fetch model into `ask-ck/var/models/`, set `SENTENCE_TRANSFORMERS_HOME`; document in build_db.py --help + SERVER-README.

## Commit staging

**A — schema + build + read API (no server changes).** paths.py, schema.sql, db.py (reads + session CRUD, no vec), build_db.py (no embed), .gitignore. Verify: `build_db.py --verify` counts = 45,427 / 410 / 21,624 / 10,157 / 830 / 14 decision files; scratchpad parity script runs ~20 real queries ("auto-negotiation", "mdix", "igmp snooping", …) through old `_search_*` vs `db.search_*` and diffs top-10 ids + scores.

**B — swap corpora read paths.** `main.py` startup → `db.startup_check()`; shrink `load_all_data()`; router wrappers delegate to db (incl. `_get_full_zephyr_cases_batch`). RAM −53 MB; JSONL scan gone. Verify manually: /health; one wizard case end-to-end (load → Step 1 search → Step 2 related → Step 3 ATP → synthesis gate); one PyTest case through script search; re-run parity script against live endpoints.

**C — sessions to DB.** `--sessions` import; rewrite the six persist/load/delete helpers + progress map. Verify: dashboard progress matches pre-migration; edit a step → restart uvicorn → state survives; `SELECT id,kind FROM sessions` shows no llm_config inside payload.

**D — semantic + hybrid.** requirements, embed pass, hybrid functions, `mode` param, `/health` reports `vector_search`. Verify: `--embed` completes and resumes after Ctrl-C; "link speed negotiation fails" in hybrid vs keyword shows sensible semantic-only rows; rename model dir → keyword-only degrade proven.

## Risks

- **sqlite-vec loading:** needs `enable_load_extension`; some CPython builds lack it → detect, degrade to keyword, `pysqlite3-binary` as escape hatch. Never a startup failure.
- **Concurrency:** WAL + current single worker trivially safe; `--workers>1` fine for reads (busy_timeout serializes rare session writes) — note the routers' in-memory session caches were already multi-worker-unsafe, pre-existing.
- **Tokenizer semantics:** substring→token/prefix recall delta, mitigated above.
- **Ingest memory:** streamed JSONL, batched writes — peak RSS well below today's 53 MB startup load.
- **Staleness / git:** `var/` gitignored; startup mtime warning; one-command rebuild.

## Critical files

- New: `CK_server/schema.sql`, `CK_server/db.py`, `tool/build_db.py`
- Modified: `CK_server/paths.py`, `CK_server/data.py`, `CK_server/main.py`, `CK_server/routers/wizard.py`, `CK_server/routers/pytest_create.py`, `CK-main/requirements.txt`, `.gitignore`, `SERVER-README.md`
- Pattern reference: `tool/enrich_script_index.py` (resumable sha1-keyed enrichment loop)

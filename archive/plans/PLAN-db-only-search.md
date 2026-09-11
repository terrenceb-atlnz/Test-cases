# PLAN — Strict DB-Only Search (retire JSON as a runtime/search source)

> ## Status (read first)
> **Phase 1 ✅ DONE 2026-07-20** — runtime is strictly DB-only. `data.py` + `pytest_create.py`
> source every corpus/reference from `db.*`; `main.py` fails fast if `ck.db` is absent (no JSON
> fallback); `tool/guard_db_only.py` fails if a corpus JSON read reappears under `CK_server/`.
> Also landed the same day: literal script-code ingest (5,782 chunks) and the full semantic embed
> pass (~84k vectors), model bundled + loading fully offline; three latent bugs fixed.
>
> **FINAL STATE ✅ DONE 2026-07-20b — `ck.db` is the PERMANENT single source of truth.** Terrence's
> decision superseded the "keep couriers as build input / remote snapshots" framing that the rest
> of this doc (below) describes. What actually happened:
> - `ck.db` (+ its ~84k vectors + the offline model) is **committed to the repo via Git LFS**. A
>   fresh clone gets a populated, searchable DB with **no build step**.
> - **All courier/intermediate source files were DELETED** — `zephyr_cases.jsonl`, `index.json`,
>   `slim_index.json`, `zephyr_master.json`, `testlink_awp.json`, `test_id_description.json`+`.csv`,
>   `candidates.json`, `decisions/*`, the ~120 `suite_*_enriched.json` + `all_test_suites.json`,
>   `scripts_index.json`, `scripts_slim_index.json`, `scripts_sources.jsonl`,
>   `scripts_index_enrich.jsonl`, `framework_surface.json`, `scripts_index.meta.json`. The one raw
>   original kept is the Zephyr XML export (immutable provenance root).
> - **No rebuild, no corpus APIs, no re-fetch.** `tool/build_db.py` is provenance-only and refuses
>   to run (would delete the committed DB, can't repopulate). The admin panel's Rebuild-DB /
>   Rebuild-embeddings actions were removed (endpoints + UI). `setup.sh` now *verifies* the shipped
>   DB instead of building it.
>
> The Phase-2/3/4/5 material and the source-classification table below are **historical** — they
> planned a gentler "eliminate local couriers, keep remote snapshots" path that the final decision
> overtook. Kept for design context; the FINAL STATE above is what shipped.

**Decision (2026-07-16):** `ck.db` becomes the **single source for all search and all
runtime reference lookups**. The running server reads **zero JSON**. Original sources are
ingested **directly into the DB**; JSON survives only as a **build-time courier for
physically-remote sources**, and is **never** a search source.

This plan folds in the two feature branches already staged but uncommitted:
- **scripts literal-code** (`source_text` + `script_chunks` + `chunks_fts` + `vec_chunks`)
- **Zephyr enrichment** (details→`script_text` fix, step `testData` fix, `issues`,
  `attachments`, FTS recall)

---

## The invariant (what "strict" means)

1. Nothing under `ask-ck/CK-main/CK_server/` reads a `.json`/`.jsonl` at request or boot
   time. All data comes from `db.*`.
2. There is exactly **one** search path per corpus (the `db.search_*` functions). No
   parallel JSON-scan or `LIKE`-in-Python search anywhere in the product.
3. If `ck.db` is missing/empty the server **fails fast with a clear message** — there is no
   JSON fallback to silently diverge to.
4. A guard test fails CI if a runtime JSON read reappears in `CK_server/`.

## The reconciliation (search layer vs. build layer)

"Omit JSON everywhere" is 100% achievable at the **search/runtime layer** (Phase 1).
At the **build layer**, sources split by *where they physically live*:

| Original source | Location | Direct-to-DB path |
|---|---|---|
| Zephyr XML export | in-repo (LFS) — **local** | `build_db` streams XML → `zephyr_cases` directly. No `zephyr_cases.jsonl`. |
| Framework scripts (`.py`) | **testbox** (remote) | extract on testbox → minimal courier → `build_db` pipes into DB. Courier is never searched. **(deferred — see checklist)** |
| TestLink / ATP / Zephyr-API | **live systems** (remote) | extractor writes to DB where the API is reachable; snapshot courier otherwise. |

So local originals lose their JSON entirely; remote originals keep a **thin build courier**
(unavoidable across a host boundary) that the DB ingests and no one ever searches.

---

## Current state (Phase 1 done 2026-07-20)

The schema/ingest feature work (scripts source_text + code chunks in `build_script_index.py` /
`build_db.py` / `schema.sql` / `db.py`; Zephyr enrichment in `extract_zephyr_xml.py`) is built and
the DB rebuilt against it. The Phase-1 repoint below is **complete** — all six runtime JSON reads
now go through `db.*`:

| `data.py` / router read | Was | Now |
|---|---|---|
| `zephyr_master` | `zephyr_master.json` | ✅ `db.get_target_cases()` (shape parity verified) |
| `candidates` / `_dict` | `candidates.json` | ✅ `db.all_candidates()` |
| `decisions` | `data/decisions/*.json` | ✅ `db.get_decisions()` |
| `framework_surface` | `framework_surface.json` | ✅ `db.get_json_doc("framework_surface")` |
| `scripts_index_meta` | `scripts_index.meta.json` | ✅ `db.get_json_doc("scripts_index_meta")` |
| `framework_surface` (pytest_create validate) | `framework_surface.json` | ✅ `dbx.get_json_doc(...)` |

Dead `load_json_safe`/`load_json_abs` removed from `data.py`; `main.py` fails fast without `ck.db`;
`tool/guard_db_only.py` locks the invariant. Phase 1 was a **repoint, not new schema** — every
target already had a DB home + getter.

---

## Phased plan

### Phase 1 — Runtime becomes strictly DB-only  *(host-agnostic; needs a built ck.db to verify)*
1. Rewrite `data.py:load_all_data()` to source the 5 references from `db.*`:
   - `zephyr_master` ← `{c["key"]: c for c in db.get_target_cases()}`
   - `candidates` / `candidates_dict` ← `db.all_candidates()`
   - `decisions` ← `db.get_decisions()`
   - `framework_surface` ← `db.get_json_doc("framework_surface")`
   - `scripts_index_meta` ← `db.get_json_doc("scripts_index_meta")`
2. Repoint `routers/pytest_create.py:419` `framework_surface.json` → `db.get_json_doc`.
3. Delete `load_json_safe` / `load_json_abs` from the runtime path (keep only if a build
   tool imports them; otherwise remove).
4. `grep -rn "json.load\|open(" CK_server/` → zero runtime hits (excluding session-file
   backups managed by `db`).
5. Fail-fast: `main.py` startup aborts with a clear message if `db.startup_check().ok` is
   false (no JSON fallback exists anymore).
6. **Verify shape parity**: `get_target_cases()` records vs. the old `zephyr_master.json`
   records — confirm every field consumers read still exists (title/folder/objective/
   steps/priority/status/labels + the new issues/attachments). Fix `_zephyr_row_to_case`
   if any master-only field is missing.

---

# Phase 2 — Retire the intermediate JSON couriers (SCOPED 2026-07-20)

**Goal.** Today `build_db.py` ingests from ~7 intermediate JSON/JSONL files. Some of those are
*derived middle-men* over a raw original that lives right here; those can be **eliminated** —
`build_db` reads the raw original directly. Others are the only local copy of a **remote** system's
data; those cannot be eliminated (you can't ingest "straight from the API" on a host that can't
reach the API), but they can be **honestly reclassified** as documented remote snapshots.

This phase is about the **build** pipeline only. The runtime is already strictly DB-only (Phase 1);
nothing here touches `CK_server/` request paths.

## Source classification (the whole point of Phase 2)

| Source | Raw original | Where | Courier today | Phase-2 action |
|---|---|---|---|---|
| Zephyr XML cases | `Zephyr-Database-*.xml` (125 MB) | **local, in-repo (LFS)** | `zephyr_cases.jsonl` (54M) | **ELIMINATE** — stream XML→DB directly |
| Zephyr `index.json` / `slim_index.json` | — | in-repo | (already unused) | **DELETE** — dead, no reader |
| Scripts source+chunks | `.py` files | **local NFS mount** (testbox) | `scripts_sources.jsonl` (35M) | **ELIMINATE** — `build_db` drives `build_script_index` in-process |
| Scripts mechanical index | `.py` files | local mount | `scripts_index.json` (2.4M) | **ELIMINATE** — same in-process path |
| Zephyr API targets | JIRA/Zephyr Scale API | **remote** (`extract_zephyr.py`, `JIRA_KEY`) | `zephyr_master.json` | **KEEP** as remote snapshot (relabel) |
| TestLink | TestLink XML-RPC | **remote** (`extract_testlink.py`, `TESTLINK_DEVKEY`) | `testlink_awp.json` | **KEEP** as remote snapshot |
| ATP descriptions | enriched-suites pipeline | remote/derived | `test_id_description.json` | **KEEP** as remote snapshot |
| candidates / decisions | matching pipeline outputs | **derived here** (`build_candidates.py`) | `candidates.json`, `decisions/*.json` | **OPTIONAL** — could write straight to DB; low value, defer |

So Phase 2's real deliverable: **the two local originals (Zephyr XML, scripts) ingest with no
intermediate file.** The three remote snapshots stay, clearly documented as *"remote-source
build snapshots — refresh by re-running the extractor where the API/host is reachable"*, never
read at runtime (already guaranteed by `guard_db_only.py`).

## Steps

**2a. Zephyr XML direct-to-DB (host-agnostic — XML is in-repo).**
- `extract_zephyr_xml.py` already exposes `parse_testcase(elem)` → normalized `rec` dict. Import it.
- Rewrite `build_db.ingest_zephyr` to `ET.iterparse` the XML (keep `elem.clear()` for O(1) memory)
  and feed each `rec` through the *existing* row-builder — byte-identical rows to the jsonl path.
- `build_db` gains `--xml PATH` (default = the in-repo `Zephyr-Database-*.xml`); the `.jsonl`
  becomes a fallback only if `--xml` is absent, then removed once proven.
- **Verify:** `--fresh --verify` counts unchanged (45,427 xml + 410 api); a spot-diff of 20 case
  rows (xml-direct vs old jsonl) is identical.

**2b. Scripts direct-to-DB (needs the testbox NFS mount — present on the build host).**
- `build_script_index.py` already produces records + chunks in-memory before it writes
  `scripts_index.json` / `scripts_sources.jsonl`. Expose that as an importable
  `build_records() -> (records, sources)` and have `build_db` call it directly, ingesting from
  the returned objects instead of re-reading the two files.
- Keep `build_script_index.py` runnable standalone (writing the files) for debugging, but
  `build_db` no longer depends on the files existing.
- **Verify:** `scripts` count 830, `script_chunks` 5,782, `search_code` returns real code.

**2c. Relabel the remote snapshots (documentation + a guard, no code move).**
- Add a `meta` row per remote source recording extractor + fetch time (already partly there via
  `src_mtime:*`). Rename/clarify in `build_db --help` + SERVER-README: these three JSON files are
  **remote-source snapshots**, refreshed by `extract_zephyr.py` / `extract_testlink.py` / the ATP
  pipeline where reachable — build input only, never a runtime or search source.

**2d. Delete dead artifacts.**
- Remove `data/zephyr_full/index.json` + `slim_index.json` (no reader after 2a).
- Retire the legacy offline tools that only ever consumed the old JSON (`build_drafting_tool.py`,
  `build_review_html.py`, `build_refined_viewer.py`, `render_batches.py`, `draft_stub.py`) →
  `tool/legacy/` or delete. Confirm none are imported by `CK_server/` or `build_db` first.

**2e. (optional, defer) candidates/decisions to DB.** `build_candidates.py` could write rows to
the `candidates` table instead of `candidates.json`. Low payoff (small files, derived here, already
DB-backed at runtime); list as a nice-to-have, not blocking.

## What Phase 2 does NOT do
- It does **not** make the build runnable with zero files — the three remote snapshots remain
  (that's a physics limit, not debt). "No source docs at all" is only achievable if the build
  always runs where JIRA/TestLink/ATP are reachable; that's a separate operational decision.
- It does **not** touch the runtime (Phase 1 already made that DB-only) or the schema.

## Risks / notes
- **Row parity** is the main risk in 2a/2b — the XML-direct and script-direct rows must be
  byte-identical to today's. Mitigation: keep the existing row-builders; only change *where the
  input dict comes from*, diff spot rows before deleting the couriers.
- **iterparse memory**: keep `elem.clear()` (extractor already does).
- **Build host must have the testbox NFS mount** for 2b (it does today — repo lives on it). If a
  build ever runs off-testbox, 2b degrades to "scripts code empty" exactly as the sidecar-absent
  path does now — non-fatal.
- Everything except 2b is host-agnostic; 2a/2c/2d/2e verify on the dev/server host.

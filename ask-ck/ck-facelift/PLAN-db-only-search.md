# PLAN — Strict DB-Only Search (retire JSON as a runtime/search source)

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

## Current state (staged, uncommitted)

Modified, not committed (Terrence commits):
- `tool/extract_zephyr_xml.py` — Zephyr enrichment (details/testData/issues/attachments)
- `tool/build_script_index.py` — scripts source_text + code chunks + sidecar
- `ask-ck/CK-main/CK_server/schema.sql` — new columns, `script_chunks`, `chunks_fts`,
  rewired `zephyr_fts` + triggers
- `tool/build_db.py` — sidecar ingest + Zephyr issues/attachments + embed specs
- `ask-ck/CK-main/CK_server/db.py` — `search_code`/`_hybrid`, `get_script_source/chunks`,
  Zephyr issues/attachments

Runtime JSON reads still present (the Phase-1 targets):

| `data.py` / router read | File | Already in DB as |
|---|---|---|
| `zephyr_master` | `zephyr_master.json` | `zephyr_cases` `is_target=1` → `db.get_target_cases()` |
| `candidates` / `_dict` | `candidates.json` | `candidates` table → `db.all_candidates()` |
| `decisions` | `data/decisions/*.json` | `decisions` table → `db.get_decisions()` |
| `framework_surface` | `framework_surface.json` | `json_docs` → `db.get_json_doc("framework_surface")` |
| `scripts_index_meta` | `scripts_index.meta.json` | `json_docs` → `db.get_json_doc("scripts_index_meta")` |
| `framework_surface` (again) | `framework_surface.json` | `pytest_create.py:419` — repoint too |

All targets already have DB homes and getters. Phase 1 is a **repoint, not new schema**.

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

### Phase 2 — Fold the LOCAL original (XML) directly into the DB  *(host-agnostic; XML is in-repo)*
1. Turn `extract_zephyr_xml.py` into an importable parser (`parse_testcase`, `norm_script`
   already are) and have `build_db.ingest_zephyr` **stream the XML** via `ET.iterparse`
   straight into `zephyr_cases` — no `zephyr_cases.jsonl` write/read.
2. `build_db` gains an `--xml PATH` (default to the in-repo export) and the jsonl becomes
   optional/removed. Keep the XML as the immutable original.
3. Retire `zephyr_cases.jsonl`, `index.json`, `slim_index.json` as pipeline inputs.

### Phase 3 — Integrate the staged feature work  *(rides the same rebuild)*
- scripts literal-code + Zephyr enrichment are already coded; they land in the Phase-4
  rebuild. No extra work beyond making sure ingest order is right.

### Phase 4 — Single coordinated rebuild + verification  *(spans testbox + API hosts — see checklist)*
- One `python3 tool/build_db.py --fresh --verify`, then `--embed`.
- Verify: server boots reading **only** the DB; every search endpoint 200; counts match;
  scripts `search_code` returns chunks; Zephyr plain bodies + issues populated; `/health`
  green; `grep` shows no runtime JSON reads.

### Phase 5 — Prune + guard  *(host-agnostic)*
- Remove/quarantine legacy JSON-consuming **offline** tools that are not the product
  (`build_drafting_tool.py` — the retired single-file tool; `build_review_html.py`;
  `build_refined_viewer.py`; `render_batches.py`; `draft_stub.py`). Move to `tool/legacy/`
  or delete.
- Delete dead artifacts with no reader (zephyr `index.json`, `slim_index.json`).
- Add a tiny test that greps `CK_server/` for runtime JSON reads and fails if any exist.
- Update `README` + `main.py` docstring (drop "single-file static approach" lineage).

---

## TESTBOX / REMOTE-HOST CHECKLIST  *(do these when physically on the testbox / API host)*

- [ ] On the testbox (`TESTBOX_HOME` reachable): run `python3 tool/build_script_index.py`
      to produce the scripts **source + chunks** courier (`scripts_sources.jsonl`).
- [ ] **Decide the scripts courier→DB mechanism** (deferred design choice): thin transport
      file piped into `build_db` (never searched) vs. build the DB on the testbox and ship
      the binary `.db` vs. remote DB write. Then wire it.
- [ ] If fresh corpora wanted: re-pull TestLink / ATP / Zephyr-API where the APIs are
      reachable, writing **directly into the DB** (or refresh the snapshot couriers).
- [ ] Add the script sources into the DB (`source_text` + `script_chunks`).
- [ ] Run the single `build_db --fresh --verify` then `--embed` (vectors incl. `vec_chunks`).
- [ ] Confirm server boots DB-only and `search_code` / hybrid returns real code.

---

## Risks / notes
- **Shape parity** (Phase 1.6) is the main correctness risk — the RAM `zephyr_master.json`
  dict and the DB row form must expose the same fields to consumers.
- **XML streaming in build_db** (Phase 2) must keep `iterparse` + `elem.clear()` for O(1)
  memory (the extractor already does this).
- The **only** JSON that legitimately survives is the remote-source build courier; it must
  be documented as build-input-only and excluded from any search code path.
- Everything except the testbox/API steps is host-agnostic and can be built + verified on
  the dev/server host against a local `--fresh` rebuild.

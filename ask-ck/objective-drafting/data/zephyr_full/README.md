# Zephyr Full Database — raw XML archive (provenance root)

**File**: `Zephyr-Database-30_Jun_2026.xml` (~120 MB XML export)
**Exported**: 2026-06-30 · **Total cases**: 45,427 (across many projects/folders, not just AWPTCM MASTER)

This directory holds **only the raw Zephyr XML export**, kept as an immutable **provenance root**.
Nothing in the product reads it.

## Where the Zephyr data actually lives now

All Zephyr cases (and every other corpus) live in **`ask-ck/var/ck.db`** — the permanent single
source of truth, shipped via Git LFS. The server reads them from the DB via `db.py`
(`db.get_case`, `db.search_zephyr`, …); there is **no JSON/JSONL** and no runtime file parsing.

The intermediate extracts that used to live here — `zephyr_cases.jsonl`, `slim_index.json`,
`index.json` — have been **deleted**. They were build-time couriers between the XML and the DB;
now that the DB is the source of truth, they are redundant. (They remain recoverable in git
history if ever needed.)

## Why the XML is kept

It is the single raw original everything descended from — retained as an archival provenance root,
never modified, never loaded at runtime. There is **no rebuild step** in the product; `tool/build_db.py`
is provenance-only and refuses to run. Reconstructing a DB from this XML would be a deliberate,
out-of-band act (restore the retired extractors first), not part of normal operation.

## Data model (normalized, as ingested into `zephyr_cases`)
- key, title, folder, objective (cleaned text), precondition
- priority, status, labels[]
- script_type ("STEP_BY_STEP" | …), steps: [{description, testData, expected}], script_text

---
name: db-is-permanent-source
description: "ck.db is the PERMANENT single source of truth, built ONCE — commit it via LFS, delete couriers, no rebuild"
metadata: 
  verified: 2026-09-30
  node_type: memory
  type: project
  originSessionId: af1ba771-27d5-4322-ab94-c73bbe631619
  modified: 2026-07-20T02:32:37.154Z
---

**Terrence's definitive data-architecture decision (2026-07-20).** `ck.db` is the **permanent single source of truth**, constructed **once** from the data he provided. It is NOT a rebuildable cache. This SUPERSEDES the earlier "ck.db is a derived cache, keep it gitignored" reasoning in [[db-only-single-source]] — that was correct only while the DB was rebuildable; the premise has now flipped, so the conclusion flips too.

Consequences (all agreed explicitly):
1. **Courier / intermediate files are scaffolding → DELETE them** once their contents are in the DB: `zephyr_cases.jsonl`, `zephyr_full/index.json` + `slim_index.json`, `zephyr_master.json`, `testlink_awp.json`, `test_id_description.json`, `candidates.json`, `decisions/*.json`, `scripts_index.json`, `scripts_sources.jsonl`, `framework_surface.json`, `scripts_index.meta.json`. No in-between data may obfuscate the DB.
2. **No APIs, no re-fetch, no extractors as part of the product.** `extract_*.py` (extract_zephyr.py→JIRA, extract_testlink.py→TestLink RPC, ATP pipeline) were HOW the data was captured originally — they are NOT part of the living system. The corpus data is NOT live and must never be re-fetched. TestLink/JIRA/ATP reachability is irrelevant to the product.
3. **`build_db.py` is a ONE-SHOT constructor** — run once, done. Remove the rebuild affordances: the admin panel "Rebuild DB" + "Rebuild embeddings" buttons (`routers/admin.py`, `frontend/ck-main/current/admin/admin.js`) and the `--fresh` re-ingest path. Keep `build_db.py` in `ask-ck/tools/` only as provenance of how the DB was made; nothing live may wipe/refill the DB.
4. **Commit `ck.db` to git via Git LFS** (it's 393 MB). It IS the data now — a fresh clone must get a working, populated database with zero build step. Remove `ask-ck/db/` (and `ck.db`) from `.gitignore`; add an LFS rule. Terrence pushed back on gitignoring it earlier for exactly this reason.
5. **Searches query the DB directly and live** (against the DB, not any external system). Caching common searches is a LATER efficiency option, not now.

**Why:** the DB is the deliverable. Anything that lets the DB be regenerated or that keeps a parallel copy of its data is obfuscation/risk. See [[db-only-single-source]] (runtime already DB-only, guard in place) and [[pending-approved-plans]].

**COMMIT IT DELIBERATELY, NOT ROUTINELY (2026-09-30).** Consequence 4 above is still right —
it is committed, not gitignored — but "commit it" was read as "commit it whenever it changes",
and live traffic dirties it constantly. **Every commit of it moves ~465 MB against the
account's monthly Git LFS bandwidth allowance** (upload and download) — Terrence, 2026-09-30,
after GitHub warned "90% of the Git LFS bandwidth". It is bandwidth, not storage: an earlier
reading that session ("LFS bills every version ever pushed, ~7 GB of a 10 GB quota") was the
wrong premise. Terrence's decisions: no GitHub Support purge, no re-push of `ck.db`, leave it
as it is and revisit only if a problem recurs. It now carries
`git update-index --skip-worktree`, so it cannot be swept into a wrap; CLAUDE.md invariant 1
holds the snapshot procedure. `.gitignore` is NOT the alternative: the file is tracked, so
ignoring it does nothing until `git rm --cached`, which records a deletion and leaves a fresh
clone with no database — the exact failure consequence 4 exists to prevent.

**How to apply:** never re-gitignore `ck.db`; never restore a rebuild button or `--fresh` re-ingest; never add a live corpus API; if asked to "refresh corpora" push back — that's out of scope by decision. The `models/` dir under `var/` (embedding model, 88 MB) is bundled too — keep it available (LFS or documented) so semantic search loads offline.

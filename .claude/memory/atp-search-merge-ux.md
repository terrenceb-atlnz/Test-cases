---
name: atp-search-merge-ux
description: "ATP manual keyword search \"looks broken\" but works — results merge low and sorted by score"
metadata: 
  node_type: memory
  type: project
  originSessionId: 44eaefa5-0d37-409d-9546-d1d1a4aec6a6
---

In the Generator's Step 4 (ATPyLib), manual keyword **Search ATP** works correctly but can look like it did nothing: `mergeATPCandidates` (CK_server/static/app.js) merges new matches into the existing candidate set and sorts by score descending, so pre-loaded high-score LLM rows (0.95–0.96) stay pinned at the top while new keyword matches land lower in the table. From the top of the panel it reads as "table never changed."

Verified 2026-07-16 with case AWPTCM-T43865: searching IGMP then PIM grew the table 12 → 32 → 52 rows, HTTP 200 each, zero console errors. Not a bug, and not caused by the [[pending-approved-plans]] ES-module-split action-registry change.

**Why:** Terrence reported it as "manual ATP search doesn't work." It's a UX rough edge (no result count/toast, new rows off-screen), not a functional defect.

**How to apply:** If asked to "fix ATP search," the likely real ask is a result-count/toast or highlight-new-rows affordance, not the fetch/render path. Terrence chose to defer this and continue the module split on 2026-07-16.

**RESOLVED 2026-07-16** by two changes (staged, not committed):
1. **Two-table "chosen shortlist"** on Generator steps 2/3/4 (TestLink/Zephyr/ATPyLib): top candidates table + bottom insertion-ordered chosen table. `Choose` moves ticked rows down (they leave the top); `Clear selected contents` moves them back. Confirm reads ONLY the bottom table. Search results land on top (no longer merged-and-buried); LLM `Suggest` drops picks straight into the chosen table. New module `static/js/chosen.js`; `Selection.order` added to `models.py` to persist click order. This killed the "burying" half of the quirk.
2. **Weighted relevance scoring** — new `_relevance_score()` in `routers/wizard.py` replaced the flat `0.45+0.1*hit` (which gave every single-keyword hit an identical 0.55). Now: title>body field weighting, term frequency, whole-word bonus, phrase bonus, coverage. Wired into `_get_atp_candidates`, `_search_testlink`, `_search_zephyr_external`. Verified: ATP "IGMP" now ranks IGMP-titled rows on top instead of a body-only "IPv4 VRRP" row. Score spread left bunched near cap on purpose (Terrence: ordering is what matters). Duplicate-title rows in the ATP corpus are now visible-but-unaddressed (pre-existing data issue, deferred).
3. **Pool re-scoring on subsequent searches** — a new search now sends the current pool's ids as `keep_ids`; the three search endpoints re-score those pooled rows against the NEW query (returning them even at score 0) so a second search re-ranks the whole visible pool instead of leaving the previous search's rows pinned at stale scores. Rows relevant to both queries stay up; non-matching ones sink but are not discarded. Frontend passes `keep_ids` via `poolIds()` in `db-search.js`. **All of items 1-3 tested by Terrence and confirmed working 2026-07-16.**

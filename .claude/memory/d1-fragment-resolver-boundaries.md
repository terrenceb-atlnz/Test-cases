---
name: d1-fragment-resolver-boundaries
description: "D1 DONE (2026-07-27, uncommitted) — hardened single _resolve_symbol_code (_resolve_end: exact loc / next-unit-start / loc_total; helpers via real loc; drops loc[0]+60). 27 adversarial checks green."
metadata: 
  node_type: memory
  type: project
  originSessionId: bb0cc757-a099-46f9-a0ca-b4fd8f3fbd36
  modified: 2026-07-26T19:55:56.412Z
---

D1 (fragment granularity, from [[pytest-artefact-review-worklist]] / NEXT_SESSION_DECISIONS.md) is **DECIDED: Option B** — keep ONE resolver (`_resolve_symbol_code` in `routers/pytest_create.py`), harden its boundary logic. Rejected per-library resolvers (art/svt/legacy) — the DB (`db.py`) already normalized all three source DBs into one `test_cases`/`helpers`/`testset` schema, so there is no shape-specific logic to duplicate; the difference is in data, not code.

**Why the original decision-doc framing was wrong:** it assumed "a fragment IS the whole class" (an ART-only assumption). Corpus reality (measured against ck.db): ~423 of 830 scripts are NOT ART-class-structured. Legacy/SVT libraries decompose into **helpers with exact locs**; monolithic tools (e.g. `svt/3007_ixnetwork/ixNetworkTestBase.py`, 3767 loc) decompose into nothing.

**The monolith-blob fear is NOT live:** the fragment symbol list (`gather_fragments`, ~line 1449) is built only from `testset`/`test_cases[]`/`helpers[]`. A monolith has all three empty → contributes zero symbols → the LLM cannot name it → it never reaches the resolver. Every in-scope symbol is a TestSet / TestCase class / helper fn, all carrying a real `loc`.

**The real defect = the `loc[0]+60` blind fallback** at line 230 (`loc[1] or loc[0] + 60`). It fires on **650/3517 test_case entries (~18%), ALL in the `legacy` DB**. Those 650: 0 have per-unit chunks (single coarse `file` chunk only), 0 are AST-parseable (Python 2 source — ties to D3). So chunk-derivation and AST-derivation are BOTH out.

**Boundary fallback chain (all derivable from the index alone, verified over all 650):**
1. `loc[1]` present → use it (ART/SVT common path, unchanged)
2. else next unit's `loc[0]` − 1 (573 of 650) — compute over sorted starts of testset+test_cases+helpers in the same rec
3. else `loc_total` (77 of 650 — last unit in file)
4. else clamped defensive bound (0 in corpus)

**Also fix in the same pass:** the helper branch (line 231-236) claims "helpers carry no loc" and regex-slices — but helpers DO carry exact `loc` (e.g. `get_wrong_platform [84,109]`). Use the helper `loc` via the same chain; the regex stop-at-next-`def`/`class` mis-slices nested defs.

**Constraints honored:** no `ck.db` rebuild, no schema change, no dispatch layer. ~25-line boundary helper + unit test over the 650 null-end cases. This is a CORRECTNESS fix (ends over/under-capture) that reduces prompt weight as a side effect; it does NOT shrink a legitimately-large ART class (correct to keep whole). Per-unit structuring deferred until a measured case demands it.

---
name: generator-steps-uniform-deferred-load
description: "Generator's three data steps must have IDENTICAL startup behavior — deferred/on-demand load, never work at case-load time"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5eff94ba-b305-4e2c-8e60-efda5ba8e420
  modified: 2026-07-27T22:31:01.104Z
---

All three Test Case Generator data steps (TestLink / Zephyr / ATPyLib) must behave
**identically at startup**: no expensive work at case load, each step fetches its own
candidates when the user navigates to that panel. Per the user, 2026-07-28: *"unless
there's an explicit advantage, I don't see why they should be doing anything different
from each other (besides getting different sets of data)."*

**Why:** load-time prefetching for panels the user hasn't opened yet has bitten this tool
twice — ATP's `analyze_atp_coverage` LLM call added ~60s to every case load (removed), and
Zephyr's 45k-row scan added a measured 3.8s **on the event loop** (still present as of
2026-07-28). Both did work for a step the user might never visit, then the panel's own
search/suggest button did it again.

**How to apply:** when touching Generator step data, don't add anything to `load_case`.
Prefer ONE `/step_candidates/{key}/{step}` endpoint over per-step bespoke handlers so the
symmetry is structural, not a convention three call sites must remember. Watch for the
inverse mistake too: the code's own comments are unreliable here — a comment in the wizard
claimed the module keeps no private copy of the relevance scorer while
`_ZREF_GENERIC_TOKENS` + `_score_zephyr_candidate` are exactly that, and
`static/js/generator.js:71` still references the long-removed load-time LLM call.

> **Paths re-checked 2026-08-17.** `routers/wizard.py` no longer exists — it became the
> `routers/wizard/` **package** on 2026-07-29 (`reviews` / `config` / `synthesis` / `export`
> + `_shared.py`), so every `wizard.py:NNNN` line number in this memory is dead. The
> review/search handlers are now in `routers/wizard/reviews.py`; the shared scorer is
> `CK_server/db.py:155`. Re-grep for the symbol rather than trusting a line number.

Corollary: **prefer `db.*` search + `db._relevance_score` over bespoke per-step scorers.**
`db.search_zephyr` (FTS-indexed, shared scorer, same exclude semantics) already did what
Zephyr's hand-rolled 45k scan did, one screen away. If a heuristic is genuinely
load-bearing, port it INTO `db._relevance_score` where all three corpora benefit — never
back into a router.

Full plan: `ask-ck/ck-facelift/PLAN-backend-module-split.md` (11 commits, all approved).
See also [[shared-tree-status-has-short-shelf-life]], [[pt-step-numbering-divergence]].

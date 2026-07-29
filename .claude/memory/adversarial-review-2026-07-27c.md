---
name: adversarial-review-2026-07-27c
description: "Ask-CK adversarial review — CLOSED 2026-07-27g. 62 candidates → 31 fixed / 31 dismissed / 0 open. Record + refutation reasoning in ADVERSARIAL-REVIEW-BACKLOG.md; do NOT re-raise dismissed rows or re-run the review"
metadata:
  node_type: memory
  type: project
  originSessionId: 1bde0fea-252d-4064-957c-c1795f0b4689
  modified: 2026-07-27T03:28:01.002Z
---

**STATUS: CLOSED (2026-07-27g). Nothing outstanding. Do not re-open or re-run.**

Started 2026-07-27c (`Workflow` "askck-adversarial-review", run wf_f53aa173-a88): 14 risk
domains → 3-skeptic verify → synthesis. **62 candidates** (2 critical / 21 high / 19 med /
20 low). Verification paused at ~50%, leaving 35 rows unadjudicated. Finished 2026-07-27g with
a FRESH workflow over exactly those 35 (`wf_f4fcd274-366`, 40 agents) — the original run was
NOT resumable (prior session, no saved script). 21 survived, 14 dismissed.

**Final: 31 fixed · 31 dismissed as not-real · 0 open.**

Batches c/d/e (`1340d9b`, `a1608d5`): SSH command injection, framework-guard bypass, stored XSS
(`html_sanitize.py`), secret leak (`redact_llm_config`/`safe_session_dict`), admin-reset PT bug,
export destroying a real first step, 2 path-traversals, agent-bridge job ownership, CORS, and
5 llm.py JSON-parse sites unified behind one string-aware `extract_json_block`.

Batches A–D (2026-07-27g): **A** `6b50f80` export authority (no client-session fallback, confirm
gate, downstream invalidation + "Stale" badges, atomic write w/ Complete marker last, backfill
migration guard); **B** `40ec299` event-loop blocking (7 sites; a *guaranteed* 180s claude_agent
self-deadlock; model warmup — cold load measured 16.2s); **C** `ba69e22` silent content loss
(anchored traceability-note strip, `pyliteral` jinja filter over 13 slots, provenance fixes);
**D** `be9149d` error signals (Claude empty/truncated guards, 2 missing `res.ok`, keep_ids
pinning, stale run status, dead `gc()`). Plus `e54fdd2` (AWPTCM-T37861's unparseable bundle —
one `\'`, the only bad one of 43) and `6eaa43e` (security, below).

**The two "accepted risk" security items are ACTIONED, no longer accepted-as-was** (`6eaa43e`,
Terrence approved all three): binds `127.0.0.1` by DEFAULT (LAN = explicit `HOST=0.0.0.0`);
`push_to_zephyr` no longer hardcodes `--force` (it was disabling upload_refined.py's own
"already refined — SKIP" guard on EVERY push); SSH host keys pinned trust-on-first-use
(`CK_SSH_TRUST_ANY=1` opts out). **Still true: NO authentication on any endpoint** — and
`X-CK-Session` is NOT a credential (the tab invents it). See [[auth-and-case-locking-plan]].

**Method notes for the next review:**
- Verify before fixing — ~half of all candidates were refuted, and one *suggested fix* was also
  wrong (reusing `_PROVENANCE_TAG_RX`; it matches prose too). Tests caught it, inspection didn't.
- Finding lists were incomplete more than once — batch B named 3 blocking sites, an AST sweep
  found 7. Prefer a mechanical sweep, and leave the sweep behind as a test.
- Skeptics find things while refuting: the SSE latin-1 mojibake (the pass's worst correctness
  bug) came from an agent disproving a narrower claim. Read refutations, not just verdicts.

**`ask-ck/pytest-create/ADVERSARIAL-REVIEW-BACKLOG.md` is now a historical record, not a
worklist** — every dismissal is kept WITH its refutation reasoning precisely so it is not
re-raised. Tests 48 → 190 pytest, 47 → 72 Vitest ([[testing-suite-3-layer]]).
See also [[backlog-quality-items-done]].

---
name: opus-for-per-unit-fix
description: Terrence's standing call (2026-09-09) — run the PyTest Creator's per-unit Fix on Opus, not Sonnet, because a plausible-but-wrong fix costs a full Opus re-review; and verify a fix at ATTRIBUTE level (do the symbols exist), not by its shape
metadata:
  type: feedback
  verified: 2026-09-09
---

Run **Fix units (LLM) on Opus**. The lever is the **unit-model dropdown** (`claudeUnitModel`) —
it drives per-unit *generation* AND per-unit *fix* via the `unit_fill` task route
(`_llm_cfg_for(sess, "unit_fill")`); there is **no separate fix-model slot**. Review already runs
on Opus through the workspace config (`_llm_cfg(sess)`), so the split today is: Sonnet drafts
units, Opus fixes and reviews.

**Why:** an Opus fix costs *more* per call, not less — the saving is net. The recurring cost of
the loop is the **Opus re-review** (~90k input over a 212 KB script) that polices each fix. On
T44297 (2026-09-09) Sonnet's re-fix of tc6 was plausible-but-broken — it read `port_desc` /
`sys_name` / `sys_desc` off `lldp_basic`, attributes no scapy layer in the suite has, so the
"all five TLVs present" verdict could never be true — while it got tc12 right *in the same run*
(bytes-containment). That one regression bought a whole extra review→fix cycle. The Opus run
that followed was **5/5 correct** at attribute-level; Sonnet's had been 2/3. Terrence: *"the Fix
run being opus is our best bet to reduce token usage."* 6 of 8 review/fix runs that day were
rework.

**How to apply:**
- Before a fix run, set the unit dropdown to Opus; set it back to Sonnet afterwards if the next
  *generation* should stay cheap (same knob).
- **Verify a fix at attribute level, not shape.** Claude "verified" the tc6 fix by confirming it
  checked all five TLV *names* — and missed that three were phantom attributes. Confirm each
  symbol/field/layer the fix uses actually exists (grep the library, the sibling units, the
  framework contrib); the contrast case (a sibling that does the same thing correctly) is the
  fastest oracle. A structure-only check is how a regression reaches a paid review.
- This is a per-*unit* question; it does not change which model generates or reviews. The
  durable fix for the rework itself is `ask-ck/plans/PLAN-fix-units-guardrails.md`.

Related: [[terrence-prefers-session-model-as-judge]] (judge in-context — but judge *deeply*),
[[mutate-before-you-claim]], [[prompt-cache-needs-block-boundaries]] (why a fix reads the
generation cache).

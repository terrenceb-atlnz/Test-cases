---
name: objective-grounding-scope-and-agnosticism
description: Objective/step grounding has NO scope-boundary model → cross-case scope bleed; grounding on product-specific corpus cases breaks platform-agnosticism (absolute); Phase 2.4 must be HYBRID + scope-filtered, not autonomous regeneration
metadata:
  type: project
---

Proven on **T33233 (Port - Auto Negotiation)** 2026-08-05b, driving the full wizard (load_case →
suggest_testlink/zephyr/atp → confirm_step → synthesize_objectives/steps, Opus/claude_code):

1. **Regenerating from empty selections bypasses the tool.** The three pilot sessions
   (T33233/4/5) have empty Steps 1–3, so a "regenerate" is just the LLM writing from the case
   title — no grounding, no traceability. Not worth the tool.
2. **The tool has NO scope-boundary model.** Its relevance scoring can't distinguish "this case
   is *about* X" from "*mentions* X while testing Y", so grounding bleeds in **sibling test
   cases' scope**. For T33233 it pulled: MDI/MDIX → **T33234** (literal next-door sibling in the
   same Port template), LLDP TLVs → **T44297**, EcoMode/LPI → **T33383**, fixed speed/duplex →
   **T33235/T33236**. The `AWP-12283` "ecofriendly/lpi" hit that looked like "recovering EcoMode"
   was this bug. Check a case's sibling folder (`zephyr_cases.folder`) to find who really owns a
   concern before grounding drags it in.
3. **Platform-agnosticism is an ABSOLUTE (Terrence), and grounding breaks it.** TestLink corpus
   cases are product-specific ("Copper SFP-10Gig-…"), so the synthesized objective enumerated
   media and named the LLDP-TLV mechanism — and it drifted straight into the steps. Naming a
   medium/rate/mechanism in the objective heavily drifts everything downstream. See
   [[scripts-must-be-hardware-agnostic]] (same value, script layer).

**Consequence — regeneration ≠ improvement.** The correct model is **HYBRID + scope-filtered**:
the tool surfaces *evidence + candidate artefacts* (e.g. it genuinely added a negative-failure
artefact and renegotiation); a human enforces **scope** (filter grounding against the sibling
cases) and **agnosticism** (no media/rate/mechanism in the objective). T33233 was finished this
way — a 9-bullet objective + 6 steps that **pass `OBJECTIVE_DRAFTING_PROCESS.md` Steps 1 & 2**
(incl. L208 platform-reusable, which the grounded version failed). Note the doc's own worked
T33233 example itself scope-creeps (an LPI step) — the doc is not a clean scope authority.

This is the standing method for Phase 2.4 (regenerate the 53): not autonomous. See
[[pipeline-layer-contract]], [[autonomous-judgement-divergence]], and PROGRESS §2026-08-05b.

**Trio done at the wizard layer (2026-08-06).** T33234 + T33235 finished the same way. Two
scope-line lessons worth keeping: (1) **T33234 (MDI/MDI-X)** — naming the medium is NOT always an
agnosticism violation. MDI/MDIX only exists on twisted-pair **copper**, so framing it around
"copper straight-through / copper crossover cables" *describes the feature*; contrast T33233 where
naming media was a violation because auto-neg spans media. The tell: does the feature exist on other
media? If no, name it. Also dropped the inherited "insert a pluggable" storyline (that's SFP/optical
language wrongly carried from T33233) and added one explicit copper-1000BASE-T-SFP artefact. (2)
**T33235 (Fixed Speed)** — duplex belongs to sibling T33236, so stripped to speed-only; specific
rates (10/100/1000) are non-agnostic → "each supported fixed speed". All three persisted to both the
git bundle and the `ck.db` wizard session; `traceability.md` left untouched. Next layer is PyTest
Creator — see [[pytest-creator-askck]].

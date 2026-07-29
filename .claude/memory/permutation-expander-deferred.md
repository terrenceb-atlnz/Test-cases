---
name: permutation-expander-deferred
description: "deterministic CLI-bounded permutation-expander is a WANTED subsystem, deferred to its own planning session; brief at ck-facelift/PLAN-permutation-expander.md"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2a141e3e-5a6e-4153-b006-2e724f5ec026
  modified: 2026-07-29T03:40:40.566Z
---

Terrence explicitly wants a **deterministic, CLI-bounded permutation-expander subsystem**
built — just not in the 2026-07-29 session. It expands a vague objective axis ("all supported
speeds", auto/full/half, autoneg, mdi/mdix) to the **full CLI-valid permutation cross-product**,
each cell a best-effort test case, bounded by the `cli_commands.tables` validity data — never
by fuzzy inference of what a port supports. It must be CODE, not a prompt rule, because the
whole point is determinism + completeness, which a sampling model cannot give (the LLM
re-enumerates differently each run — see [[cli-fabrication-originates-step2]]).

**Why:** this is the robust fix for the run-to-run sequence-extraction instability that has
repeatedly blocked the PyTest Creator's generation. Terrence: fuzzy "which speeds exist" logic
is a waste of time; include all permutations and check each as best-effort.

**How to apply:** resume from `ask-ck/ck-facelift/PLAN-permutation-expander.md` (full brief +
7 open design decisions + the T33234 worked-evidence section). First step is a 20-min read of
`cli_commands.tables` JSON shape across ~5 varied devices. Honour [[awplus-speed-duplex-constraint]]
(half-duplex≥1G prune is the one place hardware knowledge enters, as a deterministic rule) and
the "no silent caps" rule. The complementary half — objective wired into Generate + baked into
the `.py` header — was DONE 2026-07-29 (Generate prompt rule 1a + skeleton `==== OBJECTIVE ====`).

**KEY EVIDENCE (2026-07-29 model matrix):** a 5-model × 3-case generation matrix + opus/vllm-fast
holistic judging showed the objective fix worked on the GENERATION half (T33233/T33235 → "good"
from sonnet/opus), but **T33234 (MDI/MDI-X) was 10/10 "bad" — both judges, all 5 models incl.
opus-as-generator.** Root cause is NOT model quality: it is sequence-extraction `kind`
MISCLASSIFICATION — per-case partner reconfigs marked `setup` (collapse into one-time
configure(), matrix cancels) + physical cable-swaps marked `verify` (models fake them via
DUT-side CLI = false green). So the expander must own a **`kind`-classification contract** (per-
case reconfig belongs inside its TestCase; a physical/cable dimension is `physical` or recast as
partner-polarity forcing), not just a value cross-product. This is a SECOND shit-in, downstream
of the objective fix. MDI/MDI-X is functionally SIMPLER than autoneg; it only breaks because it
is a cable-wiring + link-partner feature and the classifier mishandles that shape.

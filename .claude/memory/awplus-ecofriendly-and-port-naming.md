---
name: awplus-ecofriendly-and-port-naming
description: "AW+ domain facts — ecofriendly vs ecomode slang, LPI is deprecated but still required, and port1.1.x is chassis/slot not \"legacy\""
metadata: 
  node_type: memory
  type: reference
  originSessionId: 14818525-5627-4f16-882d-6bbbef6aed41
  modified: 2026-07-27T19:28:17.595Z
---

Domain terminology Terrence corrected during the 2026-07-28 ecofriendly grounding work.
Not derivable from the repo or the harvested docs, and I got two of these wrong before
being corrected — verify against him rather than re-inferring.

**`ecofriendly` is the proper CLI terminology; "ecomode" is SLANG.** Zephyr/TestLink case
authors and conversation use "EcoMode"; the CLI never does. So slang belongs on the INPUT
side only (recognition), never in generated code.

**`lpi` is DEPRECATED terminology.** Modern diagnostics say EEE (`show platform port`
prints `EEE Admin Status`, `EEE Mode (In Hardware)`). `lpi` survives in exactly one command
name. It nonetheless must stay a first-class match term because:
- `ecofriendly lpi` / `no ecofriendly lpi` is the only spelling the CLI accepts;
- it is the live `Configured`/`Status` VALUE in `show ecofriendly`;
- **TestLink cases are several years old and almost unanimously use LPI**, and TestLink is
  the corpus reused fragments come from.
Deprecated-as-terminology does not make a string wrong to match on.

**`port1.1.x` is NOT legacy or old-platform.** The first index is the **chassis/slot**:
- It tracks **chassis vs standalone**, not firmware age. x8100/x908gen2/x908gen3 are one
  generational *family* — x908gen3 is current, x8100 is the old one. Don't call the family
  "old".
- **An x950 with a populated card slot also uses `port1.1.x`.** So port naming is a RUNTIME
  hardware property, not inferable from the model name.
Consequence: never hardcode a port name. Take it from the `.setup` topology via the
attribute `init_portlink()` binds (the ART corpus does this 10,578 times vs 125 literals,
and those literals are mostly deliberately-invalid negative-test inputs).

Related: [[awplus-speed-duplex-constraint]] (another cross-command physical rule absent
from the docs), [[atlnz-docs-cli-reference]], [[cli-fabrication-originates-step2]].

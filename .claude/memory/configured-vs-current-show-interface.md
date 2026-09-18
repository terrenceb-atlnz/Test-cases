---
name: configured-vs-current-show-interface
description: DEFERRED prompt rule — AW+ `show interface` prints BOTH `configured <attr>` and `current <attr>`; models assert on the configured line when the step wants the operational one, which passes lint and proves nothing
metadata:
  type: project
  verified: 2026-09-18
---

**Deferred work, agreed with Terrence 2026-09-17: add a prompt rule for this in a later
session.** The evidence is already collected — do not re-derive it.

## The fact (verified against `ck.db`, `int_cmd/show_interface.html`)

AlliedWare Plus `show interface <port>` prints the configured setting and the operational
result as **two separate lines**, both naming the same attribute:

```
configured duplex auto, configured speed auto, configured polarity auto
current duplex half, current speed 100
current polarity mdix
```

`show interface <port> status` makes the same distinction with the `a-` prefix — the command
reference states the value is *"preceded by a- if it has autonegotiated"*. So `a-1000` is a
negotiated result and a bare `1000` is a forced configuration.

## The failure it causes

A generated script asserts on the **configured** line when the objective/step requires the
**operational** one. It compiles, satisfies the logging contract, passes PEP 8 and the lint
reports `ok: True` — and proves nothing, because the configured value is just what was typed
in. It is a silently-green defect, the worst class.

Measured on **AWPTCM-T33234** (2026-09-17, the first family script generated after the
objective rewrite). `Assemble + settle` found **0 errors**; LLM Review found 15 findings, of
which two are exactly this:

- `TestCase_8.main` (step 9) — step requires `show interface` to report **`current polarity
  mdix`** (the resolved operational role); the code asserts on **`configured polarity mdix`**.
- `TestCase_10.configure` (step 11) — the verify hinges on the previously applied polarity
  being unchanged, but the check reads the configured value, which cannot move.

Same trap appeared in the objective work on this family: the raw synthesis conflated the two.

## How to apply

The verdict is written in the generated script's `main()`, so the rule belongs in the
script-fill layer — `templates/prompts/pt_fill_rules.jinja` and/or `pt_generate_script.jinja`
(check which one owns assertion phrasing before editing; read the design docs first per
[[pipeline-layer-contract]]). Shape of the rule: *when a step's verify names an operational
outcome, assert on the `current <attr>` line or the `a-`-prefixed status column — never on
`configured <attr>`, which only echoes what was set.* Worth an EXAMPLE, since
[[prompt-examples-are-the-spec]] and this distinction is invisible in prose.

Two sibling findings from the same review are **lint** candidates rather than prompt rules,
and are deterministic enough to be worth doing: a port-handle outlier check (one case using a
different port handle than every sibling) and an attribute-read-with-no-writer dataflow check
(`getattr(self.testSet, 'straight_dut_polarity', ...)` that nothing ever assigns — also
silently green). Related: [[generator-cli-hallucination]],
[[cli-fabrication-originates-step2]], [[awplus-ecofriendly-and-port-naming]].

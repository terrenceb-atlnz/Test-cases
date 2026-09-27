---
name: dut-decides-every-port-every-device
description: Terrence 2026-09-28 — a script never decides from a port type, module type or product whether a value is legal; it sends the command and the DUT's accept/reject IS the result (a rejection is verified, never failed); the sweep MAPS capabilities into a published record later steps consult. "Every device gets the same treatment" too.
metadata:
  type: feedback
verified: 2026-09-28
---

**The DUT decides — every port and every device gets the same treatment.** Terrence, 2026-09-28,
reversing R1 ("a fixed copper port must accept 10/100"): *"no. some devices we produce dont go
that slow. ALL ports on the DUT should decide whether ANY speed is legal, thats the point of the
first speed steps going through all available commands. It maps the device's capabilities."*
And: *"That idea extends to 'every device gets the same treatment' too."*

**Why:** the reference's legal-values table is keyed by port TYPE and is not what the device
enforces (a copper SFP reads `1000BASE-T` whether tri-speed or 1000-only; some fixed copper ports
do not go below 1000). A script that classifies a port and then fails the DUT for disagreeing is a
FALSE RED on correct hardware, and a product-specific rule breaks the script on every other
product ([[scripts-must-be-hardware-agnostic]]).

**How to apply:** a sweep step SENDS the command; accepted → verify the accepted state; rejected
with an error indication → verify the rejection (running-config and state unchanged). Each sweep
step RECORDS the answer in a published value (T33235: `self.testSet.speedMap`
`{port: {value: accepted}}`) and later steps consult the record — never a table, never
`show system pluggable` as a verdict. The rule is in `pt_extract_sequence.jinja` ("THE DUT
DECIDES"), the fact in `_pt_domain_facts.jinja`; T33235 is the first script written to it. When
hand-editing a script, an `expect_supported` / `legal_<n>` classification is the smell.
Related: [[expected-results-deliberately-absent]] (verify text is the contract),
[[negative-tests-may-unset-suite-config]].

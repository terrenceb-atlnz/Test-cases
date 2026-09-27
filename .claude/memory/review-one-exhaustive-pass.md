---
name: review-one-exhaustive-pass
description: Terrence 2026-09-28 — the tool review must sweep EVERY unit against EVERY kind in ONE pass; findings trickling in over rounds ("never finding them all at once to be fixed as a batch") is the failure; the 2-round cap (D-A) only stops the bleeding
metadata:
  type: feedback
verified: 2026-09-28
---

**One exhaustive review pass, not a trickle.** Terrence, 2026-09-28, confirming D-A (two free
tool review rounds, then an explicit extra round): *"The issue lie with the Reviewer infinitely
finding more and more script issues, and never finding them all at once to be fixed as a
batch."* On being asked whether the prompt should sweep every unit for every finding category in
one pass: *"Of course i want it to do that! Thats pretty dang frustrating for it to have such a
user-unfriendly default behavior."*

**Why:** the reviewer fixes findings as a batch; a defect the model could have reported this
round and did not costs a whole round (each ~355–375k prompt characters on Opus for T33235).
Evidence: the three 2026-09-24 rounds returned 19 / 15 / 17 findings with the same units
(TC25, TC28, TC29, TC30, TC14) re-appearing each time with new defects.

**How to apply:** `pt_review_script.jinja` §"Coverage — ONE exhaustive pass" (2026-09-28) asks
for every unit in file order against every kind, never stopping at a unit's first finding. When
the review still trickles, the next lever is mechanical: ask the reply for a per-unit coverage
list and check it server-side — not another prompt sentence. Related: [[opus-for-per-unit-fix]],
[[mutate-before-you-claim]].

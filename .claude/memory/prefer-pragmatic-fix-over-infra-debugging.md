---
name: prefer-pragmatic-fix-over-infra-debugging
description: When incidental infrastructure breaks mid-task, take the deterministic pragmatic fix and move on rather than deep-debugging it
metadata:
  type: feedback
---

Terrence, 2026-09-03: after the DoS test campaign's repeated port1.0.1 flaps wedged the
4050/x230 AW+ DHCP clients, I kept deep-debugging why DHCP wouldn't recover (dhcpd logs,
tcpdump, link bounces, service restart). He interrupted: *"we dont need leases now. just
assign static ip's and lets move on."*

**Why:** DHCP was incidental infrastructure, not the task. Time spent perfecting it was drift
off the actual goal, and a static IP restores a working bench deterministically.

**How to apply:** when incidental infrastructure (addressing, a flaky client, a convenience
service) breaks and a simple deterministic fix (static IP, hardcode, skip the feature) restores
progress, take it and move on — don't rabbit-hole trying to make the "proper" mechanism work.
Pairs with his earlier "executive decision: shut the 4050↔x230 port so there's no tough choices
to make" — he favours decisive, pragmatic moves over exhaustive debugging. See also
[[dont-ceremonialize-a-clear-fix]].

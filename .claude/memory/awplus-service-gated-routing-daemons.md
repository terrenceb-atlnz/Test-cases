---
name: awplus-service-gated-routing-daemons
description: "On IE520 awplus_main, OSPF/RIP/VRRP/PIM-SM reject with \"daemon is not running or feature license is not available\" until `service ospf|rip|vrrp|pim` is issued — NOT a licence problem; never declare a feature unavailable from one rejected command"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 49dcf692-ded5-46ac-ab73-fffb9e6ddec8
  modified: 2026-09-09T03:31:58.822Z
---

**What happened (2026-09-09, tb470):** `router ospf`, `router rip`, `router vrrp`, `ip pim sparse-mode`
all failed with `% <X> protocol daemon is not running or feature license is not available`. I read the
second clause, called OSPF/RIP/VRRP/PIM "license-gated / unavailable" and triaged 9 of 13 cases as
blocked. Terrence checked `show license` (all features present, incl. `AT-IE520-FL01` on u2) and then
asked whether I had run the **`service *` enablers first** — I had not.

**The fact:** on IE520 `awplus_main-20260905` the routing daemons are gated behind
`service ospf | service rip | service vrrp | service pim | service pim6 | service ospf6 | service ripng |
service isis`. `service X` starts the daemon **immediately** (no restart needed; the protocol config is
accepted straight after). Only **`no service X`** says "Save the config and restart for this change to
take effect" — the daemon keeps running until reboot. Licence is irrelevant (u4 without FL01 behaves
the same as u2 with it). **PIM-DM has no `service` command in the corpus and stays rejected** after
`service pim` — treat as unavailable on this build. `ip pim sparse-mode` additionally needs
`ip multicast-routing` ("IP Multicast Routing not activated").

**Why:** the "or feature license" clause is a generic catch-all; the first clause was literally true.
Rebooting is NOT an option on tb470 (IE520s TFTP-boot and have no dongle → hang), so an answer that
ends in "reboot to activate" is no answer.

**How to apply:** when an AW+ protocol command says "daemon is not running", check
`show running-config | include service` and the corpus for `service <daemon>` BEFORE concluding
anything about licences or the image; verify with one accept/reject probe. Never build a triage
verdict on a single rejected command. Related: [[ie520-mcast-l3-test-method]],
[[awplus-cli-confirmations-need-enter]].

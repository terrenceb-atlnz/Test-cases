---
name: scripts-must-be-hardware-agnostic
description: Generated test scripts must run on ALL platforms interchangeably — .setup supplies ports/devices; never tune grounding or code to one platform
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 14818525-5627-4f16-882d-6bbbef6aed41
  modified: 2026-07-27T19:51:39.974Z
---

Generated PyTest Creator scripts **must be hardware-agnostic and run on all platforms
interchangeably**. Terrence, 2026-07-28, correcting me for framing platform-specific
grounding as "hardware-accurate rather than best-guess":

> "These scripts should be Hardware-Agnostic, should run on all platforms. The CLI doesn't
> deviate too terribly much between platforms, and as such the scripts should be robust
> enough to be used interchangeably."

**Why:** the AW+ CLI barely deviates across platforms, so a script tuned to one is strictly
worse — it loses reuse and gains nothing. "Agnostic" is the design goal, not a fallback for
missing platform data.

**How to apply:**
- Do **NOT** pass `product=` into `cli_lookup.prompt_block()`. Breadth-based variant
  selection (what most families share) is CORRECT. Relevance ranking may only break ties
  toward a variant that shows the field under test.
- Never name a port in generated code. `.setup` `[portlink]` resolves them at runtime —
  that is what makes the same source work on an x930/AR4050S/x530 and yield `port1.1.x` on
  a chassis or populated-slot x950. See [[awplus-ecofriendly-and-port-naming]].
- `.setup` device binding is **two layers** — conflating them broke the first generated
  scripts. The lookup STRING is the `[switch]`/`[stack]` key; the local VARIABLE carries the
  role:
      dutA   = setup.init_swi('swi_a')     # swi_a/swi_b/... = 621 of ~650 corpus calls
      swiSrc = setup.init_swi('swi_c')     # stk_a for stacks (191/191)
      (swiSrc.portTB, tb.ethSrc) = setup.init_portlink(swiSrc, tb, type1='port')
  Emitting `init_swi('dut')` from a role name fails against any real `.setup`.
- In `init()`, use the LOCAL variables for `init_portlink` — `self.<dev>` is not assigned
  until the block below, so `self.` there is an AttributeError at runtime (lint error now).
- `.setup` notes: `[stack]` takes a member list (`stk_a = swi_a, swi_b`); non-default
  stackports need a `[configured_stackport]` section above `[portlink]`; empty
  `[boot_from_flash]` when booting over TFTP. tb470 configs live in
  `/home/st-art/st-art/configs/` (see [[part3-grading-session]]).

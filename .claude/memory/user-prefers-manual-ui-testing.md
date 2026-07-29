---
name: user-prefers-manual-ui-testing
description: "Terrence prefers to do UI testing themselves — skip browser automation, provide a manual test checklist instead"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7b099baa-982b-422b-b526-185d1f362884
---

When changes touch the Ask CK web UI, don't set up Playwright/browser automation to verify. Terrence tests the UI by hand.

**Why:** During the 2026-07-15 webpage cleanup they interrupted a Playwright verification loop with "i can do the UI testing myself, no need for playwright, just give me a list at the end."

**How to apply:** After UI changes, do static checks (syntax, tag balance, curl smoke tests) yourself, then end with a numbered manual test checklist highlighting the highest-regression-risk areas. Quick curl/HTTP checks are fine; driving the browser is not wanted.

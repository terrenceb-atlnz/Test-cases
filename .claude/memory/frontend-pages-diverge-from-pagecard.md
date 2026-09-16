---
name: frontend-pages-diverge-from-pagecard
description: LlmPage/SettingsPage/ToolPage currently reuse PageCard as a stand-in but will get distinct page-specific content — don't treat that reuse as settled
metadata:
  type: project
---

`PageCard` (`ask-ck/frontend/ck-main/svelte/src/lib/components/PageCard.svelte`) is a genuinely
shared component — used by `HomePage`, `ToolPage`, `LlmPage`, and `SettingsPage` — which is why it
lives under `lib/components/` rather than beside a single page.

**Why:** Trent confirmed (2026-09-15) that `LlmPage`, `SettingsPage`, and `ToolPage` reusing
`PageCard`'s generic tool-card layout today is a placeholder, not the final design — those pages
are expected to get distinct, page-specific content later. This came up while deciding whether the
Help page's accordion row should also be promoted to `lib/components/`: it shouldn't, since (unlike
`PageCard`) it's only reused twice inside one file (Tool Guides + FAQs on the same page), so a
Svelte `{#snippet}` is the right-sized tool there.

**How to apply:** don't treat the current `PageCard` usage on `Llm`/`Settings`/`Tool` pages as a
fixed constraint when proposing changes to those pages — expect it to be replaced or extended with
page-specific markup. Conversely, don't extract a component out of a single page file (like the
Help accordion) just because it's used more than once *within* that page — only promote to
`lib/components/` when a second page actually needs the same thing.

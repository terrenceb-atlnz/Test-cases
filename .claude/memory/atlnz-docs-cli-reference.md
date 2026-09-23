---
name: atlnz-docs-cli-reference
description: "AlliedWare Plus CLI reference in ck.db: since 2026-09-08 built from ONE combined docs zip (ss-on-<product> classes), not 37 per-device zips; renewable tables, stop→load→start"
verified: 2026-09-24
metadata: 
  node_type: memory
  type: reference
  originSessionId: da9b3bee-f2e0-4c80-972d-0db43518083d
  modified: 2026-09-09T00:00:00.000Z
---

**https://docs.atlnz.lc/preview/** — internal Allied Telesis CLI documentation (marvin-builder.atlnz.lc,
HTTP 200 from the Linux seat, no auth). WebFetch's markdown conversion DROPS the `<pre>`
sample-output blocks — use `curl` + a `<pre>` regex. The real content of each ~630 KB page is
its `<pre>` blocks (~0.3%); extract those, never store raw pages.

**Source shape changed 2026-09-08.** The docs team now ships ONE **combined build**
(`awplus-cmdref-combined.zip`, a single `<group>_cmd/<page>.html` tree with every family in
it) instead of the July **37 per-device zips**. The old per-device harvester
(`ask-ck/tools/harvest_cli_docs.py`, `meta.cli_docs_harvest`) is superseded by
`ask-ck/tools/load_cli_docs_from_zips.py --combined-zip …` (stamps `meta.cli_docs_load`).

- **Per-product differences are `ss-on-<product>` CSS classes** — on a block, or on the
  `<div>`/`<section>` that CONTAINS it. The combined build is MORE informative, not less.
  Since 2026-09-24 the loader reads a block's scope from its container too, and emits one
  `cli_commands` row per group of products that see the same blocks (`duplex` → `{auto|full}`
  on 8 chassis families; `show interface` → 8 per-family variants).
- **CORRECTED 2026-09-24:** this memory used to say "only chassis print `current ecofriendly
  lpi`" was GONE from the source. It was never gone: the scope sat on the output blocks'
  containers, which the loader did not read. `show interface` is per-family again, and only
  the x8100/x908gen2/x908gen3 variant prints LPI (see [[awplus-ecofriendly-and-port-naming]]).
- Live corpus (2026-09-24): 4,665 content rows / 3,415 commands / 39 products; 77,752
  product×page rows; 1,442 rows carry sample output.

**Reloading is stop→load→start** — `cli_lookup`'s `_PROBE_CACHE`/`_ALIAS_CACHE` key on the DB
path, so a load under a running server strands it on the old probe set (~30 s LAN downtime).
The loader `DROP`s/recreates only `cli_commands`/`cli_command_products`/`cli_commands_fts` — the
documented RENEWABLE tables, so this does NOT violate the ck.db invariant. Combined-zip SHA-256
(2026-09-07 build): `d6abc0c13d821349afefb5457907a9634dbc55d9d44fc9d00b33d187b247c4a9`.
The 2026-09-24 build (developer: "up to date as of today"; 7,323,003 bytes, SHA-256
`34710c23d56572a2a0f9194f6d8bf3d9a2f893dfb3b1b8fec01a0eeeff53cc4e`) parses to the SAME
3,535 content rows, every `content_sha` identical — no new content. It WAS loaded the same
day, for a loader fix (B2): table elements shown to no product (`ss-on-none`, "[Not available
on any product]") are now dropped — 25 rows' tables changed, nothing else. A load needs the
zip; Terrence keeps it OUTSIDE the repos and supplies it on request. A newer zip is worth
loading only if a census shows a content change or the loader changed.

**Since the second 2026-09-24 load** (details in the SERVER-README "CLI command reference" section):
- `cli_commands` has a `pre_sections` column (each block's page-section heading). Only a
  Syntax-titled section yields syntax; `harvest_cli_docs.classify` and `cli_lookup.reclassify`
  are pinned to agree.
- Tables scoped to a product subset carry an "[On …]" first row. Scope comes from the table or
  an enclosing div/section — 454 tables had lost it.
- Rows with sample output: 1,442 (after the third load, which split rows by container scope).
- `prompt_block` has no caps except `max_output_lines`, and shows per-variant and per-scope
  DIFFERENCES ("has … | lacks …"), never reprints.

**Why it exists:** the generate/extract prompts demanded exact CLI fields while showing zero
real output, so every model invented a `speed=1000`/`state=up` schema the switch never prints
(real: `current duplex full, current speed 1000, current polarity mdix`; ports are `port1.0.1`).
Two matchers feed grounding: `detect_commands()` (lexical) and `feature_commands()` (semantic,
`FEATURE_ALIASES` prose). **Short ambiguous tokens (any 3-letter; specific 2-letter like `ap`)
are gated to context — never raw, never dropped** (Terrence 2026-09-09): a bare `tlv` can't open
a feature at the trigger layer (`prose_weak`), but inside the `management address` shared-prose
disambiguation (`disambiguate_shared`/`_SHARED_PROSE`) the spelling supplies scope so `tlv`→LLDP,
`ap`/`awc`→wireless. See [[part3-grading-session]] and [[generator-cli-hallucination]].

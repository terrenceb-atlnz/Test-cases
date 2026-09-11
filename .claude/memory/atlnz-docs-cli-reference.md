---
name: atlnz-docs-cli-reference
description: "AlliedWare Plus CLI reference in ck.db: since 2026-09-08 built from ONE combined docs zip (ss-on-<product> classes), not 37 per-device zips; renewable tables, stop→load→start"
verified: 2026-09-09
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

- **Per-product differences are `ss-on-<product>` CSS classes on the `<pre>` blocks**, so the
  combined build is MORE informative, not less. The loader emits one `cli_commands` row per
  distinct product-specific **syntax** group (`duplex` → `{auto|full}` on 8 chassis families,
  `{auto|full|half}` on 25); uniform-syntax pages stay one row.
- **Some per-family facts are GONE from the source and cannot be parsed back:** `show interface`
  now shows every output form on ONE unattributed variant, so "only chassis print
  `current ecofriendly lpi`" is no longer derivable — it survives only in
  [[awplus-ecofriendly-and-port-naming]].
- Live corpus (2026-09-09): 3,535 content rows / 3,415 commands (0 lost vs July) / 39 products;
  847 rows carry sample output.

**Reloading is stop→load→start** — `cli_lookup`'s `_PROBE_CACHE`/`_ALIAS_CACHE` key on the DB
path, so a load under a running server strands it on the old probe set (~30 s LAN downtime).
The loader `DROP`s/recreates only `cli_commands`/`cli_command_products`/`cli_commands_fts` — the
documented RENEWABLE tables, so this does NOT violate the ck.db invariant. Combined-zip SHA-256
(2026-09-07 build): `d6abc0c13d821349afefb5457907a9634dbc55d9d44fc9d00b33d187b247c4a9`.

**Why it exists:** the generate/extract prompts demanded exact CLI fields while showing zero
real output, so every model invented a `speed=1000`/`state=up` schema the switch never prints
(real: `current duplex full, current speed 1000, current polarity mdix`; ports are `port1.0.1`).
Two matchers feed grounding: `detect_commands()` (lexical) and `feature_commands()` (semantic,
`FEATURE_ALIASES` prose). **Short ambiguous tokens (any 3-letter; specific 2-letter like `ap`)
are gated to context — never raw, never dropped** (Terrence 2026-09-09): a bare `tlv` can't open
a feature at the trigger layer (`prose_weak`), but inside the `management address` shared-prose
disambiguation (`disambiguate_shared`/`_SHARED_PROSE`) the spelling supplies scope so `tlv`→LLDP,
`ap`/`awc`→wireless. See [[part3-grading-session]] and [[generator-cli-hallucination]].

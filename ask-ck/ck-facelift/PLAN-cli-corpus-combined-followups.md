# PLAN — CLI corpus from the combined docs zip: follow-ups A–F

> ## Status (read first)
>
> **PROPOSED 2026-09-09 — nothing below is built. Awaiting Terrence's decisions** (listed at
> the end). Written at his request after the corpus swap itself landed: the live
> `ask-ck/var/ck.db` holds the combined-zip CLI corpus as of 2026-09-08 16:20 (see the
> 2026-09-08 entry in `ask-ck/objective-drafting/PROGRESS.md` for the before/after table and
> the two loader defects fixed on the way). The loader (`tool/load_cli_docs_from_zips.py`)
> and ck.db are **uncommitted** until this plan's gate is green.
>
> Authority: `cli_commands` / `cli_command_products` / `cli_commands_fts` are the documented
> RENEWABLE tables; replacing them does not violate the ck.db invariant. Tests must never
> write ck.db; dry-runs go against a scratch copy (`--db`). The service must be stopped for a
> load and started after it — `_PROBE_CACHE` / `_ALIAS_CACHE` key on the DB path.

## Why these six

The combined build (`awplus-cmdref-combined.zip`, docs build 2026-09-07) is ONE
`<group>_cmd/<page>.html` tree instead of July's 37 per-device zips. Loading it hard-overwrote
the CLI tables with 3,462 rows / 3,415 commands / 39 products (0 commands lost, 118 new,
0 samples lost). The gate then went red on five corpus-premise tests, and the load exposed
four things worth deciding rather than assuming.

Two findings shape the plan more than anything else:

1. **Per-product information IS in the combined build, as CSS classes.** Each `<pre>` (and
   some table cells) that applies to a subset of products carries `ss-on-<product>` classes,
   e.g. on `swi_cmd/duplex_ak.html`:
   `<pre class="… zccmdnamesyntax ss-block ss-on-xs900mx ss-on-x930 …">duplex {auto|full}</pre>`
   then `<pre class="… ss-on-ar1050 … ss-on-x560">duplex {auto|full|half}</pre>`.
   Census over the zip (2026-09-09): **48 pages** carry ≥2 product-specific SYNTAX groups
   (37 with 2, 7 with 3, 3 with 4, 1 with 13); **167 pages** carry product-specific example
   or output `<pre>` blocks; **387 pages** carry product-specific table cells; 153 pages have a
   "Syntax (VRF-lite)" section (a licence feature, not a product — no classes). The loader
   currently flattens all of it, so every product sees both `duplex` forms.
2. **`int_cmd/show_interface.html` carries NO per-product markup.** It shows every output form
   (port1.0.1, port1.1.1, eth0, eth1, lo, vlan1, br1) unattributed. The July fact "only the
   chassis families print `current ecofriendly lpi`" is therefore no longer in the source and
   cannot be restored by any parser.

Two facts settle E and F: with `feature_terms` containing "management address", the 14-line
budget already keeps the `Management Address` line of the local-info block (verified against
the live corpus); and `detect_commands` misses `lldp management-address` only when prose spells
it with a SPACE — `_probes` knows the slug `lldp managementaddress` and the hyphenated real
spelling, not the spoken form, so the text falls through to the shorter AWC wireless-controller
`management address`.

## Order

B changes the corpus, so A is judged against the final corpus. D, E, F do not touch the
corpus. Docs and the commit close it. **The gate runs after each numbered step.**

### Step 1 — B: per-product rows from the class markup (loader only)

- `parse_page`: read each `<pre>` block's `ss-on-*` set. No classes ⇒ visible to every product
  on the page ("This command is available on …"). Group the page's products by identical
  visible-block set; each group becomes its own content row (own `content_sha` over its
  blocks + tables + notes, same `page` / `command`), and `cli_command_products` maps each
  product to its group's row. Pages with one group are unchanged. `PRIMARY KEY (page,
  product)` still holds (one row per product per page).
- Reproduces July's shape for `duplex`: an 8-product row without `half`, a 25-product row
  with it.
- **Read path untouched.** `lookup()` already returns every row for a command with its
  `products`; `prompt_block()` already prints `(on x930, x950…: duplex {auto|full})` when
  rows disagree on syntax.
- VRF-lite sections stay as today (both forms on the row).
- Dry-run on a fresh copy of the pre-load backup with the existing checks (zero NEW all-prompt
  samples; no commands / samples lost; local-info labelled; `show lldp interface` keeps
  `PdSnSdScMa`) **plus**: `lookup("duplex")` returns two variants with 8 and 25 products;
  report the number of pages that split.
- Then `systemctl --user stop ask-ck.service` → load → start → `/health`. ~30 s of LAN
  downtime — needs a go-ahead on timing.
- **Decision B2:** per-product TABLE cells (387 pages) — the legal-values matrix, i.e. the
  `speed` fibre-vs-copper case the tables exist for. Recommendation: defer until a real case
  needs it (the criterion `FEATURE_ALIASES` already sets for itself). Terrence's call.

### Step 2 — A: the five red tests, against the step-1 corpus

| test | disposition |
|---|---|
| `test_cli_docs.py::test_duplex_variants_are_recorded_per_product` | passes unchanged once B lands. Keep. |
| `test_cli_feature_grounding.py::test_show_interface_does_report_lpi_on_some_families` | premise gone for good (finding 2). Rewrite: the field IS present in the sample the prompt uses; drop the `< len(variants)` half; docstring records why. |
| `test_cli_feature_grounding.py::test_family_specific_field_is_flagged` | invert to pin the new truth: with ONE variant no family-specific note is emitted (a false flag is wrong grounding). Keep the flag's code path covered with a synthetic two-row in-memory fixture. |
| `test_cli_grounding_phase4.py::test_reclassify_recovers_output_at_scale` | premise (stored column stale) gone: the loader stores the Phase-4.5 classification. Rewrite as: stored `sample_output` agrees with `reclassify(pre_blocks)` on every row. |
| `test_cli_grounding_phase4.py::test_atmf_link_gains_its_output` | same facts, new premise: the non-awplus-hostname row (`Node_1(config-if)#`) HAS output stored and `lookup` returns it. The "fixture drifted" assertion goes. |

- **Decision A2:** the two LPI rewrites accept that the prompt can no longer tell the model
  LPI is chassis-only. The `awplus-ecofriendly-and-port-naming` memory still records the fact
  and `show ecofriendly` grounds the feature on every family. Recommendation: accept.
- Hygiene, optional (a file removal, so ask): one traceback cited the old `copilot/` tree path
  — a stale compiled cache under `tests/`. Harmless; trivially deleted.

### Step 3 — D: `cli_lookup.stats()` reads the wrong stamp

- Reads `meta.cli_docs_harvest` only (July: 37 products, 73,006 fetches) and ignores
  `meta.cli_docs_load`. No server code calls it — only ad-hoc reports are wrong.
- Change: read both; report `"load"` when present, keep `"harvest"` as the fallback; `main()`
  prints the load source. One test on an in-memory db with a load stamp.

### Step 4 — E: an LLDP entry in `FEATURE_ALIASES`

Same shape as the `ecofriendly` and `spanning-tree` entries (a real case surfaced the need:
AWPTCM-T44297 units 10/11).

- `prose`: "lldp", "link layer discovery", "lldp-med".
- `commands`: `show lldp localinfo`, `show lldp interface`, the neighbours show command,
  `lldp tlvselect`, `lldp managementaddress` — each checked to carry output or examples worth
  grounding (real CLI only; slug spellings as stored; `display_name()` renders them).
- `output_terms`: "management address", "port description", "system name",
  "system description", "chassis id", "port id".
- Tests: LLDP prose resolves to the command tree; unrelated text does not fire; the
  `Management Address` line survives the 14-line budget on the REAL local-info block; a
  T44297-style step reaches `pc._cli_reference_block` with it.
- **Decision E1:** should the bare word "tlv" trigger? Recommendation: no — near-unambiguous
  in this corpus, but the table's own rule keeps three-letter tokens out.

### Step 5 — F: the spoken spelling in the probe set

- `_probes()`: add a third form per command — the real (hyphenated) spelling with hyphens
  replaced by spaces (`lldp management address`). Longest-first matching then claims the span
  before the AWC `management address` probe runs, so the wireless command is not returned
  for LLDP prose.
- Pins: LLDP prose detects `lldp managementaddress` and NOT `management address`;
  wireless-controller prose still detects its own command; the existing hyphenated and slug
  pins unchanged.
- **Decision F2:** the residual trap — a step saying only "management address" with LLDP
  named elsewhere in the case still pulls the AWC command. Suppressing it when the LLDP
  alias fires is a heuristic. Recommendation: leave it out, watch the next real pass.

### Step 6 — C: where the zip lives, then docs and commit

- **Decision C:** recommendation — track `awplus-cmdref-combined.zip` (15,867,926 bytes) in
  Git LFS at the loader's own zip directory `ask-ck/var/cli_zips/` with a `.gitattributes`
  line, and add its SHA-256 to the `cli_docs_load` stamp. Reason: the renewable tables must
  be reproducible from a source we HOLD; the invariant forbids re-fetching. Alternative:
  keep it on the lab share and record only path + hash. Check first whether that directory
  is gitignored (the July per-device zips lived there untracked).
- Docs: CHANGELOG entry (corpus swap + A–F, with the why); SERVER-README "CLI command
  reference" section rewritten for the combined source, the row counts, the reload rule
  (stop → load → start); memory `atlnz-docs-cli-reference` updated + `verified:` stamped;
  `MEMORY.md` index line; PROGRESS.md handoff.
- Green gate (`./tool/run_tests.sh` — both guards, pytest, vitest, ck.db-untouched check),
  then ONE commit with explicit paths: loader, `tool/cli_lookup.py`, tests, docs, `ck.db`,
  and the zip + `.gitattributes` if C is in-repo. **No push** (Terrence pushes).

## Decisions needed before starting

| # | decision | recommendation |
|---|---|---|
| — | timing of the ~30 s reload window (step 1) | any time Terrence is not generating |
| B2 | parse per-product TABLE cells (387 pages)? | defer until a real case needs it |
| A2 | accept that "LPI is chassis-only" leaves the prompt? | accept |
| E1 | bare "tlv" as an LLDP trigger? | no |
| F2 | suppress AWC `management address` when the LLDP alias fires? | no; watch the next pass |
| C | zip location | LFS at `ask-ck/var/cli_zips/`, SHA-256 in the stamp |
| — | delete the stale `copilot/`-path compiled cache under `tests/`? | yes, trivial |

Everything else is settled by the code or by Terrence's earlier direction ("most commands
should be platform-agnostic, as long as the platform supports that feature … just hard
overwrite that section of the db").

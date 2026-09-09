---
name: ckdb-cli-command-hyphen-collapse
description: ck.db cli_commands.command mangles hyphenated CLI tokens (config-check→"configcheck", common-segments→"common segments"); trust syntax/examples or the device's own ? — a wrong token reads as a MISSING command
metadata:
  type: reference
---

The `command` column of ck.db's `cli_commands` table is a **human label, not the exact CLI
token** — it silently mangles hyphens. Measured 2026-09-09 on the EPSR family:

| ck.db `command` | real token | what typing the ck.db form does |
| --- | --- | --- |
| `show epsr configcheck` | `show epsr config-check` | `configcheck` parsed as an INSTANCE name → `% The EPSR specified does not exist` |
| `show epsr common segments` | `show epsr common-segments` | `common` parsed as instance WORD, `segments` rejected → `% Invalid input` |

Both reads made a **present** command look **missing**, twice in one session (a third time counting
the earlier config-check slip). The failure is insidious because the error is plausible ("does not
exist" / "invalid input"), not an obvious typo.

**Rule:** for the exact token, read the `syntax` or `examples` JSON fields (they carried
`"show epsr [<instance>] config-check"` and the hyphenated forms correctly), or ask the **device's
own `?`** context help — never the `command` label. This is the ck.db-table cousin of
[[prompt-examples-are-the-spec]] and [[atlnz-docs-cli-reference]]: the authoritative token lives in
the structured/sample fields, not the prose name.

Corollary that also bit: driving `?` help over the console — abort the pending line with **Ctrl-U
(kill-line)**, NOT Ctrl-C. Ctrl-C at a `(config...)#` prompt **exits config mode**, so every
subsequent per-instance probe silently runs at exec `#` and returns `% Unrecognized command` —
a false "missing" for the whole set. See [[read-the-transcripts-before-driving-hardware]].

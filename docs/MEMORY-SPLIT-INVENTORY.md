# Memory split inventory — 2026-09-11

**Purpose.** Terrence asked (2026-09-11) for an inventory of the 88 memories in
`claude/Test-cases/.claude/memory/` to separate what the **Ask-CK** stream needs from what
other streams (IE520 / tb470 / 5700 lab campaigns) wrote into the same store. This file is
the hand-off to the other Claude so the split can be finalised. Written by the Ask-CK session;
nothing was moved or edited when it was written.

**Method.** Judged from each memory's frontmatter, its description, whether the repo already
records the same fact, and inbound `[[links]]` from other memories. Note: `/orient-ck`
auto-loads only `MEMORY.md` (the index); it does not open memory bodies, so "was it read at
orient" is not a usable criterion.

Bucket totals: 40 + 14 + 3 + 18 + 13 = 88.

## A. Ask-CK keeps — architecture and project facts (40)

- askck-lan-hosting
- ask-ck-admin-restart
- claude-agent-is-the-release-transport
- claude-code-cli-transport-contract
- workspace-llm-default-gotcha
- windows-seat-gotchas
- demo-windows-seat
- db-is-permanent-source
- ckdb-wal-and-test-isolation
- ckdb-corrupt-wal-recovery
- stale-session-connection-bug
- atlnz-docs-cli-reference
- ckdb-cli-command-hyphen-collapse
- vllm-reasoning-model-path
- prompt-cache-needs-block-boundaries
- browser-fanout-connection-ceiling
- testing-suite-3-layer
- grep-shim-honors-gitignore
- auth-and-case-locking-plan
- art-suite-shape
- setup-unit-reindent-at-assembly
- pt-step-numbering-divergence
- pytest-creator-askck
- topology-profiles-contract
- preflight-topology-check
- permutation-expander-deferred
- pipeline-layer-contract
- objective-grounding-scope-and-agnosticism
- generator-cli-hallucination
- cli-fabrication-originates-step2
- llm-provenance-portability
- generator-steps-uniform-deferred-load
- expected-results-deliberately-absent
- physical-interaction-steps
- scripts-must-be-hardware-agnostic
- setup-file-declares-topology
- opus-for-per-unit-fix
- terrence-prefers-session-model-as-judge
- awplus-speed-duplex-constraint — AW+ domain fact the generator needs; not in the CLI corpus
- awplus-ecofriendly-and-port-naming — same

## B. Ask-CK keeps — how Terrence wants Claude to work (14)

- autonomous-judgement-divergence
- mutate-before-you-claim
- checks-must-not-match-their-own-advice
- old-sessions-are-not-coverage
- prompt-examples-are-the-spec
- scoped-directives-stay-scoped
- shared-tree-status-has-short-shelf-life
- user-prefers-manual-ui-testing
- commit-and-push-on-session-end
- no-stray-scripts
- dont-ceremonialize-a-clear-fix
- silent-degradation-audit-2026-07-30
- read-the-whole-function-before-judging — learned on hardware; the lesson is general
- prefer-pragmatic-fix-over-infra-debugging — same

These probably belong to BOTH streams; a split should link them into each store rather than
pick one.

## C. Terrence's call — needed only when a generated script runs on tb470 (3)

- testbox-console-access
- legacy-scripts-vs-framework — TESTBOX-ACCESS.md already covers most of it
- read-the-transcripts-before-driving-hardware

Part 3b execution (running a generated script on the bench) is part of the PyTest Creator,
so these may belong to Ask-CK as well as the hardware stream.

## D. Not Ask-CK — lab campaign knowledge (18)

- bootloader-media-parse-bug
- x230v2-5700-control-corpus
- run-attribution-5700-campaign
- ie520-4stack-flashprep
- ie520-bootloader-console-driving — POINTER to `.claude/skills/orient-ie520/SKILL.md`, which does not exist in Test-cases
- ie520-dos-test-method
- ie520-mcast-l3-test-method
- ie520-release-naming-and-drift
- ie520-silent-reboot-watch-2026-09-02
- ie520-spiflash-goes-dark
- ie520-tftp-boot-needs-usb-nic
- ie520-two-bootloaders
- i2c-stress-tooling
- tb470-ie520-flash-boot-reboots-ok
- tb470-topology-and-setup — routing memory; points to `bench-state.md` and the `orient-ie520` skill, neither in Test-cases
- log-is-the-deliverable
- awplus-service-gated-routing-daemons — BORDERLINE: a CLI fact a generated script could get wrong (`service ospf|rip|vrrp|pim` first)
- awplus-cli-confirmations-need-enter — BORDERLINE: same (`y` + Enter on CLI confirmations)

The two borderline rows could instead join the AW+ domain-fact pair in bucket A if the
generator should know them.

Related dead pointers found during the sweep (not memories): `TESTBOX-ACCESS.md:49` and
`TB470-HOST-NETWORKING.md:14` in Test-cases also cite `.claude/skills/orient-ie520/SKILL.md`.
The device-testing repo now has `orient-dt` / `wrap-dt`; if `orient-ie520` moved there under a
new name, these five citations need re-pointing.

## E. Not needed by either — closed work the repo already records (13)

- adversarial-review-2026-07-27c — only job is "do not re-raise the 31 dismissed rows"; the one hesitation in this bucket
- backlog-quality-items-done
- atp-search-merge-ux
- llm-health-check-button — BUILT 2026-07-20
- pending-approved-plans — all three plans executed and committed
- pytest-creator-llm-config-bug — fixed 2026-07-20
- pytest-artefact-review-worklist
- d1-fragment-resolver-boundaries
- d3-py2-fragment-translation
- part3-grading-session
- run-thread-contextvar-lock — fixed 2026-08-03
- db-only-single-source — says in its own hook it is superseded by db-is-permanent-source
- testbox-framework-readonly — duplicates invariant 3 in CLAUDE.md and the gate guard

PROGRESS.md, CHANGELOG.md and the plans hold the same facts.

## Two things any split must handle

1. **`MEMORY.md` is one index.** The harness loads the index from the store a session links
   to. If a store holds a subset of files, its index must list only that subset, or every
   session is told about memories it cannot open.
2. **`tool/check_memory_links.py` assumed one store — REPAIRED 2026-09-11 (same day).** It
   now knows every sibling repo with a `.claude/memory/MEMORY.md` as a legitimate store, requires
   each repo's slugs to link to that repo's own store (`CROSS_LINK` otherwise), reports a slug
   outside every repo that links anywhere as `STRAY_LINK` (sessions start only from a repo root
   since 2026-09-11; `--fix` removes the link), and checks the relative shared symlinks in the
   store resolve (`DEAD_SHARED_LINK`). `tool/check_memory_refs.py` (dead-path check) walks
   whichever directory it is pointed at and needed no change.

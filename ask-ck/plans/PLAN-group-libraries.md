# PLAN — R1(b): one library per GROUP, merged by provenance tag

> ## Status (read first)
>
> **BUILT 2026-09-22 — then PARTLY SUPERSEDED the same day.** Approved with the three decisions
> below and shipped; gate at close EXIT=0, pytest 1683 / 1 skipped (+13), vitest 335.
>
> **Read `PLAN-art-family-numbering-and-prune.md` alongside this one.** It supersedes **D1**: the
> stem is now `library_<family>` (`library_9001.py`), which is ART's own `library_<suite>` — the
> convention §"Why `library_<group>`" below rejected *because* every script shared suite 9000.
> One suite number per mother folder removes that reason, so the departure recorded here is
> retired, not overruled. It also **closes §5 (PRUNE)**, which shipped there as an explicit
> preview-then-apply action. Everything else on this page — the merge-by-tag contract, the
> one-derivation-two-paths rule, the migration method — stands unchanged; only the stem moved.
>
> Splits R1(b) out of
> `PLAN-self-healing-generation.md`, where it was deferred on 2026-09-15 because it "changes the
> library naming CONTRACT (filename, the frame's import, persistence)" and the suite naming
> convention was not settled. It is settled now — decision D1 below.
>
> | decision | answer |
> |---|---|
> | **D1 — the convention** | ~~`library_<group>` from the mother folder~~ — **superseded 2026-09-22** by `library_<family>` (`9001_Port/` → `library_9001.py`) |
> | **D2 — the existing T33234 library** | **Migrate now, explicitly** — rename the file and fix the script's import |
> | **D3 — scope of this pass** | **Merge + mark now; PRUNE deferred** to its own pass — **built 2026-09-22**, `PLAN-art-family-numbering-and-prune.md` §4 |
>
> Prune is deliberately NOT in this pass: merge and mark only ever ADD, while prune deletes
> members from a file shared across a group. It gets its own plan once real group libraries have
> accumulated members to prune. §5 records what it will need.

## Why `library_<group>` and not ART's `library_<suite>`

ART ships one `library_<suite>.py` per numeric suite — `library_1332.py` for `1332_lldp_med`.
That convention does **not** transfer: every script we generate is `test-9000.<case>.py`, on our
one assigned suite number **9000** (`PT_ART_SUITE`, 2026-09-17), so a faithful `library_<suite>`
would be a single `library_9000.py` for the entire output. The mother folder is the grouping that
actually carries meaning here, which is what D4 of the self-healing plan proposed. **This is a
deliberate departure from ART, recorded so nobody "corrects" it later.**

Today's `library_<case>` (`_library_stem`, keyed on the case key) gives one library per case, so
two scripts in the same group that need the same helper each carry their own copy — exactly the
duplication R1(a)'s dependency closure makes more likely, since it now auto-ships dependencies.

## The contract as it stands (verified 2026-09-22)

`_library_stem(case_key)` → `library_awptcm_t44297`. That stem reaches four places:

| where | what it does |
|---|---|
| `_build_library` | returns `{name: stem + ".py", stem, code, members, tags, …}` |
| `pt_script_template.py.jinja:124` | emits `from {{ lib_stem }} import *` into the frame |
| `_persist_generated_files` | writes `<stem>.py` beside the script, **overwriting** |
| lint + Review/Fix prompts | recognises the library module; ships `library_code`/`library_name` |

**The group is already in hand where it is needed.** `generate_script` resolves it with
`_validate_naming` at line 5041, *before* it calls `_build_library` at line 5076.

**Library file format.** `_build_library` emits a docstring, sorted imports, then per member:
a blank line, a blank line, the **tag line**, optional `# why` comment lines, then the code.
Tags are `# ART <path> lines a-b` (`_fragment_tag`) or `# AI: dependency \`name\` of <tag>` for a
member R1(a)'s closure pulled in. One tag = one member: that is the merge key.

## 1. Two call sites must derive the stem IDENTICALLY

`_build_library` is called from `generate_script` (5076) and `_pt_generation_context` (5540).
The latter's docstring is explicit: it *"deliberately mirrors generate_script's own derivation …
If these two ever diverge, the units stop fitting the file."* A divergent stem changes the frame,
which changes `assembled_hash`, which makes slice A's gating 409 on every splice.

`generate_script` resolves `group` as `body.get("group") or naming.get("group") or
_group_display(sess.group)` and **persists it to `step6.naming` before the LLM call** — except on
a dry run, which must not write the session. So:

- add `_effective_group(sess)` = `naming.get("group") or _group_display(sess.group)`;
- `generate_script` keeps its body override: `body.get("group") or _effective_group(sess)`;
- `_build_library` takes `group` as an explicit argument from both paths — never re-derived
  inside, so the two cannot drift apart silently.

## 2. `_group_library_stem(group)`

Group names are NOT module names: `_GROUP_RX` admits spaces, parens and hyphens, and
`_group_display` can emit `Authentication_Security`. Sanitise exactly as `_library_stem` already
does (`[^a-z0-9]+` → `_`, strip `_`), so `Port` → `library_port`.

**Known, accepted collision class:** `Port A` and `Port-A` both fold to `library_port_a`. It did
not exist under `library_<case>`. Two groups that differ only in punctuation would share a
library — noted, not guarded, because the generated tree has one group today and a collision is
visible the moment it happens (both scripts import the same module).

The library docstring changes with it: "helpers shared by the **<Group>** group", not "the
<case_key> suite", because that sentence stops being true the moment a second case merges in.

## 3. Merge, never overwrite (`_persist_generated_files`)

Today: `lib_path.write_text(lib["code"])`. Two scripts in one group would now write the same
path, so the second would silently destroy the first's members.

**New:** when the target exists, merge.

1. Split the existing file into a **preamble** (everything before the first tag line) and its
   tagged members.
2. **A file with no recognisable tag lines is preserved WHOLE as preamble** — this is the real
   case, not a hypothetical: the T33234 library on disk today came from `3c680c9` and is an
   LLM-authored helper module with **zero** provenance tags. New members append after it.
3. A member whose tag is already present is left **byte for byte** — never re-rendered, so a
   reviewer's hand edit to a merged member survives the next save.
4. Imports are unioned into the preamble's import block; existing lines keep their position.
5. Members new to the file are appended in `_build_library` order.

**Merge is additive in this pass.** Nothing is ever removed — that is D3.

## 4. Migration (D2) — done explicitly, once

`generated/Port/library_awptcm_t33234.py` → `generated/Port/library_port.py`, and
`test-9000.33234.py:32` `from library_awptcm_t33234 import *` → `from library_port import *`.
A `git mv` plus a one-line edit, done in the open rather than by a silent rewrite on next save.
This is the file R1(a)'s closure would merge into, so it must carry the new name before any
merge can be exercised against it.

## 5. Deferred to its own pass — PRUNE

What it will need, recorded now so the next session does not re-derive it: after review, an
auto-added member (`# AI: dependency …`, and ONLY those) that no script in the group folder
references is removed — that member only, nothing else in the file moves. It needs the
unbound-names walk run in **reverse** over every script in the group directory, and it is the
only part of R1(b) that can delete a reviewer's working code, which is why it is separated.

**BUILT 2026-09-22** — `PLAN-art-family-numbering-and-prune.md` §4, `POST /library_prune`.
The precondition recorded here was never met and still is not: `generated/9001_Port/library_9001.py`
has **zero** tagged and **zero** `# AI: dependency` members, so a real prune is a no-op today.
That is asserted as the correct behaviour rather than worked around, and the destructive path is
exercised against libraries `_build_library` itself produced, so the tags under test are the tags
the generator emits. It is **explicit only** (preview, then apply) — nothing triggers it on a save.

## 6. Tests

- `_group_library_stem`: `Port` → `library_port`; spaces/parens/hyphens fold; the documented
  collision is asserted as KNOWN, not as correct.
- Both generation paths produce the **same** stem for one session — the byte-identical-frame
  guarantee of §1, pinned directly rather than trusted.
- Merge: a tagged member already present is byte-identical after a second save; a new tag is
  appended; an **untagged** existing file is preserved whole; imports union without duplicating.
- The frame emits `from library_<group> import *`.
- 15 existing assertions across `test_pt_art_shape.py`, `test_pt_lint_unbound_and_owner.py`,
  `test_pt_prompt_library_context.py` and `test_lint_error_classes.py` pin `library_awptcm…` and
  move with the contract.

## 7. Method

All backend edits land in **ONE** save. `ask-ck.service` runs `uvicorn --reload` on the working
tree, so every `CK-main/**/*.py` write bounces production and a reload can wedge on the 25 s
agent long-polls — the same reason `PLAN-generate-state-and-sequence-sanity` put A, B and
reset_generate in one commit. Gate before and after.

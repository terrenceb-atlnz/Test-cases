# PLAN — ART family numbering (`900x.yyyy.zzzz`) + the deferred library PRUNE

> ## Status (read first)
>
> **IN BUILD 2026-09-22.** Two things ship together because the prune's unit of work — a
> group's library — is exactly the thing the numbering renames. Doing them separately would
> migrate the same files twice.
>
> | decision | answer |
> |---|---|
> | **D1 — family width** | **9001–9999.** `900x` is the 9000 *block*, not a literal single digit |
> | **D2 — library name** | **`library_<family>.py`** — ART's own `library_<suite>` shape, restored |
> | **D3 — on-disk shape** | **`9001_Port/` AND a registry file**; the registry is authoritative |
> | **D4 — prune trigger** | **Explicit only** — preview, then remove on confirmation |
>
> Supersedes `PLAN-group-libraries.md` D1 (`library_<group>`) and its §5 deferral. That plan's
> merge/mark work stands unchanged; only the *stem* moves.

## The convention — Terrence, 2026-09-22

```
900x . yyyy . zzzz
 │      │      └── the TestCase inside the script
 │      └───────── the Zephyr case the script maps FOR (AWPTCM-T33234 → 33234)
 └──────────────── the family: one per mother folder. 9000 is RESERVED for libraries.
```

`9001.33234.1` is the first TestCase of the Port script for T33234. It is a reference, and
(pending the check in §6) the operand for running that one case.

## What already exists — verified 2026-09-22, do not rebuild

**`zzzz` is not new work.** `ATTestCase` composes
`testCaseName = '%s.%s.%d' % (testSuiteNum, testSetNum, testCaseNum)`, and `testCaseNum` comes
from the `TestCase_<N>` class name — **231 of the 239** ART scripts never assign it by hand. The
run log already writes `>> test-5700.2001.10` per case and `pt_exec._CASE_START` (line 238)
already parses it. Our generated scripts have `TestCase_1 … TestCase_18`. The only thing
missing was a per-*group* number in the first position.

**The triple is already ART's house convention.** From the corpus:
`testCaseRef = 'CR-52769, 1331.1001.52769'`, `'CR-80881, 1353.1001.80881'`,
`'SYST-6225, CR-80760, 1343.001.80760'`; and `library_1330.py` builds
`testId = '.'.join([testSuiteNum, testSetNum, str(testCaseNum)])`. We are adopting a
convention we had half-inherited, not inventing one.

**The 9000 block is entirely free in ART.** The corpus uses 1330–1399 and 6000–6101 across 51
suite dirs. Nothing occupies 9001–9999.

**Why not a single digit (D1).** The AWPTCM target set is 410 cases across **20** distinct
folder leaves (Switching 75, Management 71, IPv4 44, Authentication & Security 42, IPv6 32,
QoS 22, Other 17, Advanced Management 17, Bootloader 17, Sanity Check 15, XEM 11, Uncategorized
Features 11, Redundancy 9, GRUB Bootloader 8, Port 7, …). With 9000 reserved, `900x` runs out
at the tenth. `9001–9999` keeps every example Terrence gave literally true and adds 990 spare
slots.

**Why `library_<family>` is a restoration, not a new departure (D2).** `PLAN-group-libraries.md`
rejected ART's `library_<suite>.py` for one stated reason: *every* script sat on suite 9000, so
a faithful `library_<suite>` would collapse the whole output into one `library_9000.py`. Giving
each group its own family removes that reason exactly — ART's convention and "one library per
mother folder" now name the same file. 9000 stays permanently unallocated, so `test-9000.*`
never exists and the reserved block cannot collide with a family's library.

## 1. Allocation

```
PT_LIBRARY_SUITE = "9000"      # reserved; never handed to a group
PT_FAMILY_MIN, PT_FAMILY_MAX = 9001, 9999
FAMILY_REGISTRY = PT_GENERATED_DIR / ".families.json"
```

`_family_for_group(group)` returns the group's family, allocating on first use:

1. Registry hit → return it. **The registry is authoritative** (D3): a group that has a number
   keeps it even if its folder was renamed or deleted.
2. Miss → take the lowest free number ≥ 9001, where "free" excludes both the registry's values
   **and** every `^(\d+)_` prefix found in the generated tree. Scanning disk as well is what
   stops a retired folder's number being handed to a different group later — the failure that
   would silently re-point old logs at new work.
3. Persist atomically (tmp + `replace`) under a process lock, and return.

The registry is not a corpus, so it does not touch the DB-only invariant (`guard_db_only.py`
flags named corpus JSON and retired anchors; a state file under `PT_GENERATED_DIR` is the same
class as the per-case `provenance.json` it already allows).

## 2. What the number renames

| before | after |
|---|---|
| `PT_ART_SUITE = "9000"` | `PT_LIBRARY_SUITE` + `_family_for_group(group)` |
| `_art_script_name(key)` → `test-9000.33234` | `_art_script_name(key, family)` → `test-9001.33234` |
| `generated/Port/` | `generated/9001_Port/` |
| `generated/.meta/Port/` | `generated/.meta/9001_Port/` |
| `_group_library_stem(group)` → `library_port` | `_family_library_stem(family)` → `library_9001` |
| `testCaseRef = 'AWPTCM-T33234'` | `testCaseRef = 'AWPTCM-T33234, 9001.33234.<n>'` |

The last row is the reference surface Terrence asked for: `ATTestCase._preRun` writes
`testCaseRef` into the log's `TEST_CASE_REFERENCES` block, so the triple lands in the artifact
a reader actually has. It matches ART's `'CR-52769, 1331.1001.52769'` byte-shape.

**Both generation paths must agree**, exactly as for the group (`PLAN-group-libraries.md` §1):
`generate_script` and `_pt_generation_context` each resolve the family at their own top and pass
it in. `_build_library` and `_render_skeleton` never re-derive it, because the stem is part of
the frame and a divergence 409s every splice through `assembled_hash`.

## 3. Migration — done explicitly, once

`Port` is the first allocation, so it takes **9001**:

- `generated/Port/` → `generated/9001_Port/`
- `test-9000.33234.py` → `test-9001.33234.py`
- `library_port.py` → `library_9001.py`, and the script's `from library_port import *` with it
- `generated/.meta/Port/test-9000.33234/` → `.meta/9001_Port/test-9001.33234/`, including the
  archived `history/iter-1/test-9000.33234.py`
- `.families.json` seeded `{"Port": 9001}`

Done with `git mv` and named edits rather than by a silent rewrite on the next save, for the
same reason `PLAN-group-libraries.md` D2 did it that way: the file is the one real artifact and
a rename it cannot explain is worse than no rename.

## 4. PRUNE (the deferred R1(b) pass)

**What it removes.** A library member whose tag is `# AI: dependency \`name\` of <tag>` — a
member R1(a)'s closure auto-added — and *only* those. A member carrying an `# ART` / `# SVT` /
`# legacy` tag was selected by a human and is never touched, and untagged preamble (the whole
of an LLM-authored library) is never touched.

**When a member is dead.** No `.py` in the group's folder, other than the library itself,
Loads any name the member binds — *and* no retained member of the library does either. The
second half needs a fixed point: dropping a member can make the member it alone called dead in
turn, so the walk repeats until a pass removes nothing.

**Explicit only (D4).** `POST /library_prune` with `{group, apply}`. With `apply` false it
reports what it would remove and changes nothing; with `apply` true it writes. This is the only
operation in R1(a)/R1(b) that can delete a reviewer's working code, and there is no automatic
trigger anywhere.

**Why it is safe to build now although the precondition is still unmet.** `library_9001.py` on
disk has **zero** tagged members and zero `# AI: dependency` members, so a real prune is a
no-op today — which is the correct behaviour and is asserted as such. The destructive path is
exercised against libraries built by `_build_library` itself from real fragment records, not
against hand-written fixtures, so the tags under test are the tags the generator emits.

## 5. Tests

- Allocation: first group gets 9001; a second gets 9002; the registry wins over disk; a number
  seen on disk is never reallocated; 9000 is never handed out; exhaustion at 9999 raises.
- `_art_script_name(key, family)` → `test-9001.33234`, and the framework's own
  `test-(\d+).(\d+).*\.py` still matches it (the whole point of the filename).
- `library_9001` is the stem, and the frame emits `from library_9001 import *`.
- Both generation paths derive the same family and the same stem for one session.
- `testCaseRef` carries `<family>.<case>.<n>` and keeps the case key.
- Prune: an `# AI: dependency` member no script references is removed; one a script references
  is kept; an `# ART` member is kept even when unreferenced; a member referenced only by another
  auto-added member that is itself being removed is removed too (the fixed point); a library
  with no tagged members is returned unchanged; `apply=false` writes nothing.
- The 15 existing assertions pinning `library_port` / `test-9000.*` move with the contract.

## 6. Open — needs the bench, not a decision

The single-case operand. The legacy py2 `ATPylib/ATTestSet.py` (read out of `ck.db`) selects
with `if (str(testCase.testCaseNum) in args)`, which is where the convention comes from. The
current py3 framework at `/home/st-art/framework` was **not mounted on the dev host on
2026-09-22**, and it parses `-s <setup> -v` flags the legacy stub has no parser for, so its
selection syntax may differ. `zzzz` is therefore shipped as a *reference* that is certainly
correct (it is what the log already prints) and as an operand that is **unverified**. Confirm
on tb470 before documenting it as a way to run one case.

## 7. Method

All backend edits land in **ONE** save — `ask-ck.service` runs `uvicorn --reload` on the working
tree, so each `CK_server/**/*.py` write bounces production and a reload can wedge on the 25 s
agent long-polls. Gate before and after.

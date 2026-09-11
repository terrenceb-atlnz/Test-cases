#!/usr/bin/env python3
"""Check that the harness loads each repo's `.claude/memory/` — and only its own.

WHY THIS EXISTS
---------------
Memories live in a repo at `.claude/memory/`. Claude Code does not read them from there.
It reads `~/.claude/projects/<slug>/memory/`, where `<slug>` is the session's launch
directory with every non-alphanumeric character turned into `-`. Those per-slug entries
are SYMLINKS into a repo store.

The links are absolute paths. When the tree moved from `…/copilot/Test-cases` to
`…/claude/Test-cases` (some time before 2026-08-17) every link died, and the new slug had
no entry at all — so the harness quietly created an EMPTY REAL DIRECTORY there. From
2026-08-17 to 2026-09-04 every session ran with zero auto-loaded memories. Nobody noticed,
because `/orient-ck` §4 checked `ls .claude/memory/*.md` — the REPO side, which was fine —
and never the harness side. Any memory written through the harness in that window landed
in the empty directory, uncommitted and invisible to the next session.

TWO STORES, NOT ONE (policy since 2026-09-11)
---------------------------------------------
There are two sibling repos under the same parent, each with its own store — this one and
`device-testing`. Sessions launch ONLY from a repo root, never from the lab home or `~`,
expressly so the two streams stop polluting each other's memories. The rules that follow:

  * a slug that belongs to a repo (the repo root or any directory inside it) must link
    to THAT repo's store — a link into the other repo's store is CROSS_LINK, the
    cross-pollution this policy exists to stop;
  * a slug that belongs to no repo (the lab home, `~`, the old copilot path) must not
    link into any store — that is a STRAY_LINK, reported as a warning; `--fix` removes
    the link (a symlink is not content);
  * the shared memories this store keeps as relative symlinks into the sibling store
    must resolve — a DEAD_SHARED_LINK is the 2026-08-17 failure in a new coat.

    ./ask-ck/tools/check_memory_links.py          # report; exit 1 if anything needs attention
    ./ask-ck/tools/check_memory_links.py --fix    # re-point/remove links, replace EMPTY dirs

`--fix` never deletes content. A real directory that contains files is reported and left
alone: merge those files into the owning store by hand, then run `--fix` again. A link
into an UNKNOWN store that holds files is likewise left for a human.

Deliberately NOT in `ask-ck/tools/run_tests.sh`: it inspects the developer's home directory, not
the repo, and the gate must stay a statement about the repo. `/orient-ck` and `/wrap-ck`
run it.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

REPO = Path(__file__).resolve().parents[2]  # ask-ck/tools/ -> repo root
MEM_DIR = REPO / ".claude" / "memory"


def slug_for(launch_dir: Path) -> str:
    """Claude Code's project slug: the absolute path, non-alphanumerics → '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(launch_dir.resolve()))


def expected_launch_dirs(repo: Path, also: Iterable[Path] = ()) -> List[Path]:
    """Where a session is meant to start: the repo root, plus anything passed with --also.
    The lab home two levels up used to count when it carried a CLAUDE.md; since 2026-09-11
    sessions start only in a repo, so it no longer does."""
    return [repo, *(Path(p) for p in also)]


def known_stores(repo: Path) -> Dict[Path, Path]:
    """{repo_root: its memory store} for this repo and every sibling repo under the same
    parent that has a store of its own (a `.claude/memory/MEMORY.md`)."""
    stores: Dict[Path, Path] = {repo.resolve(): (repo / ".claude" / "memory").resolve()}
    parent = repo.resolve().parent
    if parent.is_dir():
        for sib in sorted(parent.iterdir()):
            store = sib / ".claude" / "memory"
            if sib.resolve() != repo.resolve() and (store / "MEMORY.md").is_file():
                stores[sib.resolve()] = store.resolve()
    return stores


def owner_of(slug: str, stores: Dict[Path, Path]) -> Optional[Path]:
    """The repo a slug's launch directory lies in (its root or any directory beneath it),
    or None for a launch directory outside every known repo."""
    best: Optional[Path] = None
    for root in stores:
        rs = slug_for(root)
        if slug == rs or slug.startswith(rs + "-"):
            if best is None or len(rs) > len(slug_for(best)):
                best = root
    return best


@dataclass
class Finding:
    slug: str
    kind: str          # OK | MISSING | EMPTY_DIR | STRANDED | DEAD_LINK | WRONG_TARGET |
                       # CROSS_LINK | STRAY_LINK | DEAD_SHARED_LINK | UNLINKED
    detail: str
    fixable: bool = False
    fatal: bool = False
    expected: bool = False           # one of the launch dirs a session is meant to start from
    target: Optional[Path] = None    # where --fix should point the link (None = just remove)


@dataclass
class Report:
    findings: List[Finding] = field(default_factory=list)

    @property
    def fatal(self) -> List[Finding]:
        return [f for f in self.findings if f.fatal]

    @property
    def fixable(self) -> List[Finding]:
        return [f for f in self.findings if f.fixable]


def _inspect_entry(slug: str, entry: Path, stores: Dict[Path, Path], expected: bool) -> Finding:
    """One slug's `memory` entry against the two-store rules."""
    owner = owner_of(slug, stores)
    own_store = stores[owner] if owner else None
    store_of = {v: k for k, v in stores.items()}
    f = _inspect_entry_inner(slug, entry, own_store, store_of, expected)
    f.expected = expected
    return f


def _inspect_entry_inner(slug: str, entry: Path, own_store: Optional[Path],
                         store_of: Dict[Path, Path], expected: bool) -> Finding:
    if entry.is_symlink():
        target = os.readlink(entry)
        if not entry.exists():
            if own_store:
                return Finding(slug, "DEAD_LINK", f"symlink -> {target} (target gone)",
                               fixable=True, fatal=True, target=own_store)
            return Finding(slug, "DEAD_LINK", f"symlink -> {target} (target gone; the slug "
                           f"belongs to no repo, so --fix removes the link)", fixable=True)
        resolved = entry.resolve()
        if own_store and resolved == own_store:
            return Finding(slug, "OK", f"symlink -> {target}")
        if resolved in store_of:
            other = store_of[resolved].name
            if own_store:
                return Finding(slug, "CROSS_LINK",
                               f"symlink -> {target}: the {other} store — a session started "
                               f"here would load and WRITE the other repo's memories "
                               f"(cross-pollution); --fix re-points it to this repo's store",
                               fixable=True, fatal=True, target=own_store)
            return Finding(slug, "STRAY_LINK",
                           f"symlink -> {target}: the {other} store, from a launch directory "
                           f"outside every repo — sessions no longer start here "
                           f"(2026-09-11); --fix removes the link", fixable=True)
        holds = list(resolved.glob("*.md")) if entry.is_dir() else []
        if holds:
            return Finding(slug, "WRONG_TARGET",
                           f"symlink -> {target}: an UNKNOWN store holding {len(holds)} .md "
                           f"file(s) — merge them into a repo store by hand, then --fix",
                           fixable=False, fatal=True)
        return Finding(slug, "WRONG_TARGET", f"symlink -> {target} (not a known store)",
                       fixable=bool(own_store), fatal=True, target=own_store)
    if entry.is_dir():
        contents = sorted(p.name for p in entry.iterdir())
        if contents:
            where = own_store or "the owning repo's .claude/memory/"
            return Finding(slug, "STRANDED",
                           f"REAL directory with {len(contents)} file(s): {', '.join(contents[:6])}"
                           f"{' …' if len(contents) > 6 else ''} — memories written here never "
                           f"reached a repo; merge into {where} by hand, then --fix",
                           fixable=False, fatal=True)
        if expected and own_store:
            return Finding(slug, "EMPTY_DIR", "REAL empty directory (the harness made it because "
                           "nothing was here) — memories do NOT load", fixable=True, fatal=True,
                           target=own_store)
        # A probe or a one-off `claude -p` from some temp directory leaves a slug with an
        # empty memory dir behind. Nothing launches there on purpose, so the fix is to
        # remove the empty directory, not to link a throwaway slug into a store.
        return Finding(slug, "EMPTY_DIR", "REAL empty directory on a slug no session is meant "
                       "to start from — --fix removes it (nothing is linked)",
                       fixable=True, fatal=True)
    if entry.exists():
        return Finding(slug, "WRONG_TARGET", "exists but is neither a symlink nor a directory",
                       fixable=False, fatal=True)
    if expected and own_store:
        return Finding(slug, "MISSING", "no memory entry for an expected launch directory",
                       fixable=True, fatal=True, target=own_store)
    return Finding(slug, "UNLINKED", "has sessions but no memory entry (a session started "
                   "here loads nothing; pass --also <dir> to link it)")


def _inspect_shared_links(mem_dir: Path) -> List[Finding]:
    """The memories this store keeps as symlinks (relative, into the sibling store) must
    resolve. A dead one is the 2026-08-17 failure again: the name is in the index, the file
    is not there, and nothing else says so."""
    out: List[Finding] = []
    for p in sorted(mem_dir.glob("*.md")):
        if p.is_symlink() and not p.exists():
            out.append(Finding("(repo)", "DEAD_SHARED_LINK",
                               f".claude/memory/{p.name} -> {os.readlink(p)} (target gone) — "
                               f"restore the file in the sibling store, or replace the link "
                               f"with a copy", fatal=True))
    return out


def scan(projects: Path, mem_dir: Path, launch_dirs: Iterable[Path],
         stores: Optional[Dict[Path, Path]] = None) -> Report:
    rep = Report()
    if not (mem_dir / "MEMORY.md").is_file():
        rep.findings.append(Finding("(repo)", "STRANDED",
                                    f"{mem_dir}/MEMORY.md is missing — the store itself is gone",
                                    fatal=True))
        return rep
    stores = stores or known_stores(mem_dir.parent.parent)
    rep.findings.extend(_inspect_shared_links(mem_dir))
    expected = {slug_for(d): d for d in launch_dirs}
    seen = set()
    for slug, d in expected.items():
        seen.add(slug)
        rep.findings.append(_inspect_entry(slug, projects / slug / "memory", stores, True))
    if projects.is_dir():
        for slug_dir in sorted(projects.iterdir()):
            if not slug_dir.is_dir() or slug_dir.name in seen:
                continue
            entry = slug_dir / "memory"
            has_sessions = any(slug_dir.glob("*.jsonl"))
            if not entry.exists() and not entry.is_symlink() and not has_sessions:
                continue
            rep.findings.append(_inspect_entry(slug_dir.name, entry, stores, False))
    return rep


def fix(projects: Path, mem_dir: Path, rep: Report) -> List[str]:
    """Apply the safe fixes. Never removes anything that has content: a symlink is
    unlinked (never followed), an EMPTY directory is rmdir'd after a re-check."""
    done: List[str] = []
    for f in rep.fixable:
        entry = projects / f.slug / "memory"
        if entry.is_symlink():
            entry.unlink()
        elif f.kind == "EMPTY_DIR":
            if any(entry.iterdir()):        # re-check: never rmdir content
                continue
            entry.rmdir()
        elif f.kind == "MISSING":
            entry.parent.mkdir(parents=True, exist_ok=True)
        if f.target is None:
            done.append(f"{f.slug}: {f.kind} removed (slug is not a launch directory of any repo)")
            continue
        entry.symlink_to(f.target)
        done.append(f"{f.slug}: {f.kind} -> symlink to {f.target}")
    return done


def _print(rep: Report, projects: Path, stores: Dict[Path, Path]) -> None:
    print(f"this store:   {MEM_DIR}")
    for root, store in stores.items():
        if store != MEM_DIR.resolve():
            print(f"sibling store: {store}")
    print(f"harness side: {projects}")
    for f in rep.findings:
        tag = "OK  " if f.kind == "OK" else ("FAIL" if f.fatal else "warn")
        where = f.slug if f.slug == "(repo)" else f"{f.slug}/memory"
        print(f"  {tag}  {where}  [{f.kind}] {f.detail}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fix", action="store_true",
                    help="re-point/remove dead, cross and stray links; replace EMPTY dirs")
    ap.add_argument("--also", action="append", default=[], metavar="DIR",
                    help="another launch directory that must be linked (repeatable)")
    ap.add_argument("--projects", default=None,
                    help="override ~/.claude/projects (tests)")
    args = ap.parse_args(argv)

    projects = Path(args.projects) if args.projects else Path.home() / ".claude" / "projects"
    launch = expected_launch_dirs(REPO, (Path(a) for a in args.also))
    stores = known_stores(REPO)
    rep = scan(projects, MEM_DIR, launch, stores)

    if args.fix and rep.fixable:
        for line in fix(projects, MEM_DIR, rep):
            print(f"fixed  {line}")
        rep = scan(projects, MEM_DIR, launch, stores)

    _print(rep, projects, stores)
    warns = [f for f in rep.findings if f.kind != "OK" and not f.fatal]
    if rep.fatal:
        print(f"\n{len(rep.fatal)} problem(s). Memories are NOT loading correctly for those slugs.")
        if any(f.fixable for f in rep.fatal):
            print("  run:  ./ask-ck/tools/check_memory_links.py --fix")
        if any(not f.fixable for f in rep.fatal):
            print("  and merge the stranded/foreign files into a repo store by hand first —"
                  " --fix will not delete content.")
        return 1
    print("\nOK — every slug that belongs to a repo links to that repo's own store."
          + (f" ({len(warns)} warning(s) above; --fix clears the fixable ones.)" if warns else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

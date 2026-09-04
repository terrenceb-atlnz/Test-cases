#!/usr/bin/env python3
"""Check that the harness is actually loading `.claude/memory/` — and fix the links.

WHY THIS EXISTS
---------------
Memories live in the repo at `.claude/memory/`. Claude Code does not read them from
there. It reads `~/.claude/projects/<slug>/memory/`, where `<slug>` is the session's
launch directory with every non-alphanumeric character turned into `-`. Since
2026-07-30 those per-slug entries have been SYMLINKS into the repo, so one store loads
whichever directory a session starts in.

The links are absolute paths. When the tree moved from `…/copilot/Test-cases` to
`…/claude/Test-cases` (some time before 2026-08-17) every link died, and the new slug
had no entry at all — so the harness quietly created an EMPTY REAL DIRECTORY there.
From 2026-08-17 to 2026-09-04 every session ran with zero auto-loaded memories. Nobody
noticed, because `/orient` §4 checked `ls .claude/memory/*.md` — the REPO side, which
was fine — and never the harness side. `/orient` then read `MEMORY.md` by hand, which
hid the symptom. Any memory written through the harness in that window would have
landed in the empty directory, uncommitted and invisible to the next session.

WHAT IT CHECKS
--------------
For the launch directories a session is expected to start from (the repo root, and the
lab home two levels up when it carries its own CLAUDE.md — add more with `--also`):
the slug's `memory` entry must be a symlink resolving to `<repo>/.claude/memory`.
For EVERY slug under `~/.claude/projects/`: no dead symlinks, no real directory holding
`.md` files (those are stranded memories), no link into some other memory store.

    ./tool/check_memory_links.py          # report; exit 1 if anything needs attention
    ./tool/check_memory_links.py --fix    # re-point dead links, replace EMPTY dirs with links

`--fix` never deletes content. A real directory that contains files is reported and
left alone: merge those files into `.claude/memory/` by hand, then run `--fix` again.

Deliberately NOT in `tool/run_tests.sh`: it inspects the developer's home directory,
not the repo, and the gate must stay a statement about the repo. `/orient` and `/wrap`
run it.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

REPO = Path(__file__).resolve().parent.parent
MEM_DIR = REPO / ".claude" / "memory"


def slug_for(launch_dir: Path) -> str:
    """Claude Code's project slug: the absolute path, non-alphanumerics → '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(launch_dir.resolve()))


def expected_launch_dirs(repo: Path, also: Iterable[Path] = ()) -> List[Path]:
    dirs = [repo]
    lab_home = repo.parent.parent
    if (lab_home / "CLAUDE.md").is_file():          # the lab home documents this repo
        dirs.append(lab_home)
    dirs.extend(Path(p) for p in also)
    return dirs


@dataclass
class Finding:
    slug: str
    kind: str          # OK | MISSING | EMPTY_DIR | STRANDED | DEAD_LINK | WRONG_TARGET | UNLINKED
    detail: str
    fixable: bool = False
    fatal: bool = False


@dataclass
class Report:
    findings: List[Finding] = field(default_factory=list)

    @property
    def fatal(self) -> List[Finding]:
        return [f for f in self.findings if f.fatal]

    @property
    def fixable(self) -> List[Finding]:
        return [f for f in self.findings if f.fixable]


def _inspect_entry(slug: str, entry: Path, mem_dir: Path, expected: bool) -> Finding:
    mem_dir = mem_dir.resolve()
    if entry.is_symlink():
        target = os.readlink(entry)
        if not entry.exists():
            return Finding(slug, "DEAD_LINK", f"symlink -> {target} (target gone)",
                           fixable=True, fatal=True)
        if entry.resolve() == mem_dir:
            return Finding(slug, "OK", f"symlink -> {target}")
        holds = list(entry.resolve().glob("*.md")) if entry.is_dir() else []
        if holds:
            return Finding(slug, "WRONG_TARGET",
                           f"symlink -> {target}: a DIFFERENT store holding {len(holds)} .md "
                           f"file(s) — merge into {mem_dir} by hand, then --fix",
                           fixable=False, fatal=True)
        return Finding(slug, "WRONG_TARGET", f"symlink -> {target} (not the repo store)",
                       fixable=True, fatal=True)
    if entry.is_dir():
        contents = sorted(p.name for p in entry.iterdir())
        if contents:
            return Finding(slug, "STRANDED",
                           f"REAL directory with {len(contents)} file(s): {', '.join(contents[:6])}"
                           f"{' …' if len(contents) > 6 else ''} — memories written here never "
                           f"reached the repo; merge into {mem_dir} by hand, then --fix",
                           fixable=False, fatal=True)
        return Finding(slug, "EMPTY_DIR", "REAL empty directory (the harness made it because "
                       "nothing was here) — memories do NOT load", fixable=True, fatal=True)
    if entry.exists():
        return Finding(slug, "WRONG_TARGET", "exists but is neither a symlink nor a directory",
                       fixable=False, fatal=True)
    if expected:
        return Finding(slug, "MISSING", "no memory entry for an expected launch directory",
                       fixable=True, fatal=True)
    return Finding(slug, "UNLINKED", "has sessions but no memory entry (a session started "
                   "here loads nothing; pass --also <dir> to link it)")


def scan(projects: Path, mem_dir: Path, launch_dirs: Iterable[Path]) -> Report:
    rep = Report()
    if not (mem_dir / "MEMORY.md").is_file():
        rep.findings.append(Finding("(repo)", "STRANDED",
                                    f"{mem_dir}/MEMORY.md is missing — the store itself is gone",
                                    fatal=True))
        return rep
    expected = {slug_for(d): d for d in launch_dirs}
    seen = set()
    for slug, d in expected.items():
        seen.add(slug)
        rep.findings.append(_inspect_entry(slug, projects / slug / "memory", mem_dir, True))
    if projects.is_dir():
        for slug_dir in sorted(projects.iterdir()):
            if not slug_dir.is_dir() or slug_dir.name in seen:
                continue
            entry = slug_dir / "memory"
            has_sessions = any(slug_dir.glob("*.jsonl"))
            if not entry.exists() and not entry.is_symlink() and not has_sessions:
                continue
            rep.findings.append(_inspect_entry(slug_dir.name, entry, mem_dir, False))
    return rep


def fix(projects: Path, mem_dir: Path, rep: Report) -> List[str]:
    """Apply the safe fixes. Never removes anything that has content."""
    done: List[str] = []
    for f in rep.fixable:
        entry = projects / f.slug / "memory"
        if f.kind in ("DEAD_LINK", "WRONG_TARGET") and entry.is_symlink():
            entry.unlink()
        elif f.kind == "EMPTY_DIR":
            if any(entry.iterdir()):        # re-check: never rmdir content
                continue
            entry.rmdir()
        elif f.kind == "MISSING":
            entry.parent.mkdir(parents=True, exist_ok=True)
        entry.symlink_to(mem_dir.resolve())
        done.append(f"{f.slug}: {f.kind} -> symlink to {mem_dir.resolve()}")
    return done


def _print(rep: Report, projects: Path) -> None:
    print(f"memory store: {MEM_DIR}")
    print(f"harness side: {projects}")
    for f in rep.findings:
        tag = "OK  " if f.kind == "OK" else ("FAIL" if f.fatal else "warn")
        print(f"  {tag}  {f.slug}/memory  [{f.kind}] {f.detail}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fix", action="store_true",
                    help="re-point dead/wrong links and replace EMPTY dirs with links")
    ap.add_argument("--also", action="append", default=[], metavar="DIR",
                    help="another launch directory that must be linked (repeatable)")
    ap.add_argument("--projects", default=None,
                    help="override ~/.claude/projects (tests)")
    args = ap.parse_args(argv)

    projects = Path(args.projects) if args.projects else Path.home() / ".claude" / "projects"
    launch = expected_launch_dirs(REPO, (Path(a) for a in args.also))
    rep = scan(projects, MEM_DIR, launch)

    if args.fix and rep.fixable:
        for line in fix(projects, MEM_DIR, rep):
            print(f"fixed  {line}")
        rep = scan(projects, MEM_DIR, launch)

    _print(rep, projects)
    if rep.fatal:
        print(f"\n{len(rep.fatal)} problem(s). Memories are NOT loading for those slugs.")
        if any(f.fixable for f in rep.fatal):
            print("  run:  ./tool/check_memory_links.py --fix")
        if any(not f.fixable for f in rep.fatal):
            print("  and merge the stranded/foreign files into .claude/memory/ by hand first —"
                  " --fix will not delete content.")
        return 1
    print("\nOK — every expected launch directory links to the repo memory store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

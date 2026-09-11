"""ask-ck/tools/check_memory_links.py — the harness-side memory check.

The 2026-08-17 → 2026-09-04 outage: the tree moved, the absolute symlinks died, the
harness created an empty real directory for the new slug, and every session ran with
no auto-loaded memories while `ls .claude/memory/*.md` kept looking fine. These tests
pin each state the checker must name, and that `--fix` never deletes content.

Since 2026-09-11 there are TWO sibling stores (this repo and device-testing) and sessions
launch only from a repo root. The second half pins the two-store rules: a repo's slugs link
to its own store (a link into the other store is CROSS_LINK), a slug outside every repo
links nowhere (STRAY_LINK), and the shared memories kept here as relative symlinks resolve.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "ask-ck" / "tools" / "check_memory_links.py"
spec = importlib.util.spec_from_file_location("check_memory_links", TOOL)
cml = importlib.util.module_from_spec(spec)
sys.modules["check_memory_links"] = cml          # dataclasses resolves the module by name
spec.loader.exec_module(cml)  # type: ignore[union-attr]


@pytest.fixture
def world(tmp_path: Path):
    repo = tmp_path / "lab" / "claude" / "Test-cases"
    mem = repo / ".claude" / "memory"
    mem.mkdir(parents=True)
    (mem / "MEMORY.md").write_text("# Memory Index\n")
    projects = tmp_path / "home" / ".claude" / "projects"
    projects.mkdir(parents=True)
    return repo, mem, projects


@pytest.fixture
def sibling(world):
    """A second repo beside the first with a store of its own — the device-testing shape."""
    repo, mem, projects = world
    other = repo.parent / "device-testing"
    omem = other / ".claude" / "memory"
    omem.mkdir(parents=True)
    (omem / "MEMORY.md").write_text("# device-testing index\n")
    (omem / "shared-fact.md").write_text("---\nname: shared-fact\n---\nboth streams need me\n")
    return other, omem


def kinds(rep):
    return {f.slug: f.kind for f in rep.findings}


def link(projects: Path, slug: str, target: Path) -> Path:
    (projects / slug).mkdir(exist_ok=True)
    (projects / slug / "memory").symlink_to(target)
    return projects / slug / "memory"


# ── the original single-store states ────────────────────────────────────────────────────

def test_slug_matches_claude_code_convention():
    p = Path("/media/terrenceb/mnt/testbox_home/claude/Test-cases/ask-ck/CK_main")
    assert cml.slug_for(p) == "-media-terrenceb-mnt-testbox-home-claude-Test-cases-ask-ck-CK-main"


def test_missing_entry_for_expected_dir_is_fatal_and_fixable(world):
    repo, mem, projects = world
    rep = cml.scan(projects, mem, [repo])
    slug = cml.slug_for(repo)
    assert kinds(rep) == {slug: "MISSING"}
    assert rep.fatal and rep.fixable
    cml.fix(projects, mem, rep)
    entry = projects / slug / "memory"
    assert entry.is_symlink() and entry.resolve() == mem.resolve()
    assert kinds(cml.scan(projects, mem, [repo])) == {slug: "OK"}


def test_empty_real_dir_is_the_silent_failure_and_is_replaced(world):
    """The exact 2026-09-04 state: the harness made an empty dir, nothing loaded."""
    repo, mem, projects = world
    slug = cml.slug_for(repo)
    (projects / slug / "memory").mkdir(parents=True)
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep) == {slug: "EMPTY_DIR"} and rep.fatal
    cml.fix(projects, mem, rep)
    entry = projects / slug / "memory"
    assert entry.is_symlink() and entry.resolve() == mem.resolve()


def test_dead_symlink_after_a_tree_move_is_repointed(world):
    repo, mem, projects = world
    slug = cml.slug_for(repo)
    link(projects, slug, repo.parent.parent / "copilot" / "Test-cases" / "mem")
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep) == {slug: "DEAD_LINK"} and rep.fatal
    cml.fix(projects, mem, rep)
    assert (projects / slug / "memory").resolve() == mem.resolve()


def test_stranded_memories_are_never_deleted_by_fix(world):
    repo, mem, projects = world
    slug = cml.slug_for(repo)
    stranded = projects / slug / "memory"
    stranded.mkdir(parents=True)
    (stranded / "lost-fact.md").write_text("---\nname: lost-fact\n---\nimportant\n")
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep) == {slug: "STRANDED"}
    assert rep.fatal and not rep.fixable
    assert cml.fix(projects, mem, rep) == []
    assert (stranded / "lost-fact.md").read_text().endswith("important\n")
    assert not stranded.is_symlink()


def test_other_slugs_are_scanned_for_dead_links_and_stranded_dirs(world):
    """A dead link on a slug that belongs to NO repo (the old copilot path) is removed, not
    re-pointed here — since 2026-09-11 nothing launches there, and linking it in would be
    the cross-pollution the policy exists to stop."""
    repo, mem, projects = world
    good = cml.slug_for(repo)
    link(projects, good, mem)
    link(projects, "-old-copilot-slug", repo.parent / "nowhere")
    (projects / "-subdir-slug").mkdir()
    (projects / "-subdir-slug" / "s.jsonl").write_text("{}")
    (projects / "-inert-slug").mkdir()
    rep = cml.scan(projects, mem, [repo])
    k = kinds(rep)
    assert k[good] == "OK"
    assert k["-old-copilot-slug"] == "DEAD_LINK"
    assert k["-subdir-slug"] == "UNLINKED"
    assert "-inert-slug" not in k
    dead = next(f for f in rep.findings if f.slug == "-old-copilot-slug")
    assert dead.fixable and not dead.fatal and dead.target is None
    unlinked = next(f for f in rep.findings if f.slug == "-subdir-slug")
    assert not unlinked.fatal and not unlinked.fixable
    cml.fix(projects, mem, rep)
    dead_entry = projects / "-old-copilot-slug" / "memory"
    assert not dead_entry.exists() and not dead_entry.is_symlink()


def test_a_dead_link_on_a_subdirectory_of_this_repo_is_repointed_here(world):
    """A slug for a directory INSIDE the repo belongs to the repo: its store is this one."""
    repo, mem, projects = world
    sub = cml.slug_for(repo / "ask-ck" / "CK-main")
    link(projects, sub, repo.parent / "gone")
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep)[sub] == "DEAD_LINK"
    cml.fix(projects, mem, rep)
    assert (projects / sub / "memory").resolve() == mem.resolve()


def test_an_empty_dir_on_a_junk_slug_is_removed_not_linked(world):
    """A probe run from a temp directory (2026-09-04) left a slug with an empty memory dir.
    Nothing launches there on purpose, so linking it into the repo store would be wrong;
    the fix is to remove it. An empty dir on an EXPECTED slug is still replaced by a link."""
    repo, mem, projects = world
    link(projects, cml.slug_for(repo), mem)
    junk = projects / "-tmp-some-probe-scratchpad"
    (junk / "memory").mkdir(parents=True)
    (junk / "s.jsonl").write_text("{}")
    rep = cml.scan(projects, mem, [repo])
    f = next(x for x in rep.findings if x.slug == junk.name)
    assert f.kind == "EMPTY_DIR" and f.fatal and f.fixable and not f.expected
    cml.fix(projects, mem, rep)
    assert not (junk / "memory").exists() and not (junk / "memory").is_symlink()
    assert kinds(cml.scan(projects, mem, [repo]))[junk.name] == "UNLINKED"   # now just a warning


def test_link_into_an_unknown_store_with_content_is_not_auto_repointed(world):
    repo, mem, projects = world
    slug = cml.slug_for(repo)
    other = repo.parent / "other-store"          # not a sibling REPO store: no .claude/memory
    other.mkdir()
    (other / "MEMORY.md").write_text("# other\n")
    link(projects, slug, other)
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep) == {slug: "WRONG_TARGET"}
    assert rep.fatal and not rep.fixable


def test_the_lab_home_is_no_longer_an_expected_launch_dir(world):
    """Before 2026-09-11 the lab home counted when it carried a CLAUDE.md. Sessions now
    start only in a repo, so a CLAUDE.md there changes nothing."""
    repo, mem, projects = world
    (repo.parent.parent / "CLAUDE.md").write_text("# lab home\n")
    assert cml.expected_launch_dirs(repo) == [repo]
    assert cml.expected_launch_dirs(repo, [repo / "x"]) == [repo, repo / "x"]


# ── two stores (2026-09-11) ─────────────────────────────────────────────────────────────

def test_known_stores_finds_every_sibling_repo_with_its_own_index(world, sibling):
    repo, mem, projects = world
    other, omem = sibling
    (repo.parent / "raw-data").mkdir()           # a sibling directory with no store
    stores = cml.known_stores(repo)
    assert stores == {repo.resolve(): mem.resolve(), other.resolve(): omem.resolve()}


def test_owner_of_picks_the_repo_a_slug_lies_in(world, sibling):
    repo, mem, projects = world
    other, omem = sibling
    stores = cml.known_stores(repo)
    assert cml.owner_of(cml.slug_for(repo), stores) == repo.resolve()
    assert cml.owner_of(cml.slug_for(repo / "ask-ck" / "agent"), stores) == repo.resolve()
    assert cml.owner_of(cml.slug_for(other), stores) == other.resolve()
    assert cml.owner_of(cml.slug_for(repo.parent.parent), stores) is None       # lab home
    assert cml.owner_of("-home-terrenceb", stores) is None


def test_a_sibling_slug_linked_to_its_own_store_is_ok_not_wrong_target(world, sibling):
    """The state that made the single-store checker report 2 FAIL after the split."""
    repo, mem, projects = world
    other, omem = sibling
    link(projects, cml.slug_for(repo), mem)
    link(projects, cml.slug_for(other), omem)
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep) == {cml.slug_for(repo): "OK", cml.slug_for(other): "OK"}
    assert not rep.fatal and not rep.fixable


def test_cross_links_are_the_pollution_and_are_repointed_to_the_owners_store(world, sibling):
    """Each direction: this repo's slug on the sibling store, the sibling's slug on ours."""
    repo, mem, projects = world
    other, omem = sibling
    mine, theirs = cml.slug_for(repo), cml.slug_for(other)
    link(projects, mine, omem)
    link(projects, theirs, mem)
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep) == {mine: "CROSS_LINK", theirs: "CROSS_LINK"}
    assert len(rep.fatal) == 2 and len(rep.fixable) == 2
    cml.fix(projects, mem, rep)
    assert (projects / mine / "memory").resolve() == mem.resolve()
    assert (projects / theirs / "memory").resolve() == omem.resolve()
    assert (omem / "shared-fact.md").exists()          # nothing in either store was touched
    assert kinds(cml.scan(projects, mem, [repo])) == {mine: "OK", theirs: "OK"}


def test_a_stray_link_from_outside_every_repo_is_a_warning_that_fix_removes(world, sibling):
    """The lab home and `~` slugs after the split: a session started there would load (and
    write) one repo's memories. Not fatal — nothing launches there any more — but --fix
    removes the link. The store it pointed at is untouched."""
    repo, mem, projects = world
    other, omem = sibling
    link(projects, cml.slug_for(repo), mem)
    lab = cml.slug_for(repo.parent.parent)
    link(projects, lab, omem)
    link(projects, "-home-terrenceb", mem)
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep)[lab] == "STRAY_LINK" and kinds(rep)["-home-terrenceb"] == "STRAY_LINK"
    assert not rep.fatal and len(rep.fixable) == 2
    cml.fix(projects, mem, rep)
    for s in (lab, "-home-terrenceb"):
        e = projects / s / "memory"
        assert not e.exists() and not e.is_symlink()
    assert (omem / "shared-fact.md").exists() and (mem / "MEMORY.md").exists()
    assert kinds(cml.scan(projects, mem, [repo])) == {cml.slug_for(repo): "OK"}


def test_a_dead_shared_symlink_in_the_store_is_fatal(world, sibling):
    """The 12 shared memories are relative symlinks into the sibling store. If that file
    goes, the index still names it and nothing else says so."""
    repo, mem, projects = world
    other, omem = sibling
    link(projects, cml.slug_for(repo), mem)
    (mem / "shared-fact.md").symlink_to(Path("../../../device-testing/.claude/memory/shared-fact.md"))
    assert (mem / "shared-fact.md").exists()
    assert kinds(cml.scan(projects, mem, [repo])) == {cml.slug_for(repo): "OK"}
    (omem / "shared-fact.md").unlink()
    rep = cml.scan(projects, mem, [repo])
    f = next(x for x in rep.findings if x.kind == "DEAD_SHARED_LINK")
    assert f.fatal and not f.fixable and "shared-fact.md" in f.detail
    assert cml.fix(projects, mem, rep) == []            # nothing safe to do mechanically


def test_main_exit_codes(world, sibling, capsys):
    repo, mem, projects = world
    other, omem = sibling
    cml.REPO, cml.MEM_DIR = repo, mem
    link(projects, cml.slug_for(other), mem)             # a cross link: fatal, fixable
    link(projects, cml.slug_for(repo.parent.parent), mem)   # a stray link: warning only
    assert cml.main(["--projects", str(projects)]) == 1
    assert cml.main(["--projects", str(projects), "--fix"]) == 0
    assert cml.main(["--projects", str(projects)]) == 0
    out = capsys.readouterr().out
    assert "sibling store:" in out
    assert "OK — every slug that belongs to a repo links to that repo's own store" in out
    assert (projects / cml.slug_for(other) / "memory").resolve() == omem.resolve()

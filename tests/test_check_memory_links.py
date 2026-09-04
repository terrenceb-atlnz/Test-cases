"""tool/check_memory_links.py — the harness-side memory check.

The 2026-08-17 → 2026-09-04 outage: the tree moved, the absolute symlinks died, the
harness created an empty real directory for the new slug, and every session ran with
no auto-loaded memories while `ls .claude/memory/*.md` kept looking fine. These tests
pin each state the checker must name, and that `--fix` never deletes content.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tool" / "check_memory_links.py"
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


def kinds(rep):
    return {f.slug: f.kind for f in rep.findings}


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
    (projects / slug).mkdir()
    (projects / slug / "memory").symlink_to(repo.parent.parent / "copilot" / "Test-cases" / "mem")
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
    repo, mem, projects = world
    good = cml.slug_for(repo)
    (projects / good).mkdir()
    (projects / good / "memory").symlink_to(mem)
    # an old slug whose launch dir is gone: dead link, still fixable
    (projects / "-old-copilot-slug").mkdir()
    (projects / "-old-copilot-slug" / "memory").symlink_to(repo.parent / "nowhere")
    # a slug with sessions but no memory entry at all: warn only
    (projects / "-subdir-slug").mkdir()
    (projects / "-subdir-slug" / "s.jsonl").write_text("{}")
    # a slug with neither sessions nor an entry: ignored
    (projects / "-inert-slug").mkdir()
    rep = cml.scan(projects, mem, [repo])
    k = kinds(rep)
    assert k[good] == "OK"
    assert k["-old-copilot-slug"] == "DEAD_LINK"
    assert k["-subdir-slug"] == "UNLINKED"
    assert "-inert-slug" not in k
    unlinked = next(f for f in rep.findings if f.slug == "-subdir-slug")
    assert not unlinked.fatal and not unlinked.fixable
    cml.fix(projects, mem, rep)
    assert (projects / "-old-copilot-slug" / "memory").resolve() == mem.resolve()


def test_link_into_a_foreign_store_with_content_is_not_auto_repointed(world):
    repo, mem, projects = world
    slug = cml.slug_for(repo)
    other = repo.parent / "other-store"
    other.mkdir()
    (other / "MEMORY.md").write_text("# other\n")
    (projects / slug).mkdir()
    (projects / slug / "memory").symlink_to(other)
    rep = cml.scan(projects, mem, [repo])
    assert kinds(rep) == {slug: "WRONG_TARGET"}
    assert rep.fatal and not rep.fixable


def test_lab_home_is_expected_only_when_it_documents_the_repo(world):
    repo, mem, projects = world
    assert cml.expected_launch_dirs(repo) == [repo]
    (repo.parent.parent / "CLAUDE.md").write_text("# lab home\n")
    assert cml.expected_launch_dirs(repo) == [repo, repo.parent.parent]


def test_main_exit_codes(world, capsys):
    repo, mem, projects = world
    cml.REPO, cml.MEM_DIR = repo, mem
    assert cml.main(["--projects", str(projects)]) == 1
    assert cml.main(["--projects", str(projects), "--fix"]) == 0
    assert cml.main(["--projects", str(projects)]) == 0
    out = capsys.readouterr().out
    assert "OK — every expected launch directory" in out

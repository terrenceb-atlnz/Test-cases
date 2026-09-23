"""Plan 12.4 (2026-09-23): the DB-only guard must be able to FAIL.

WHY. `guard_db_only.py` only ever scanned a clean tree, so "GUARD OK" was printed whether it
worked or was broken — and it had a one-comment bypass: its allow-list carried "# ", so any
line with a trailing comment was skipped whole. Adding `# legacy` to a corpus read defeated
invariant #2. Now comments are stripped by the tokenizer before matching, and these tests run
the guard over a throwaway tree that DOES violate it.
"""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("guard_db_only", _REPO / "ask-ck" / "tools" / "guard_db_only.py")
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def _tree(tmp_path, body):
    root = tmp_path / "ask-ck" / "CK-main" / "CK_server"
    root.mkdir(parents=True)
    (root / "data.py").write_text(body, encoding="utf-8")
    return root


def test_a_corpus_read_is_caught(tmp_path):
    root = _tree(tmp_path, 'import json\nz = json.load(open("zephyr_master.json"))\n')
    assert guard.scan(root)


def test_a_trailing_comment_does_not_hide_a_corpus_read(tmp_path):
    root = _tree(tmp_path, 'import json\nz = json.load(open("zephyr_master.json"))  # legacy\n')
    assert guard.scan(root)


def test_a_mention_inside_a_comment_is_not_a_read(tmp_path):
    root = _tree(tmp_path, 'x = 1  # we used to json.load(open("zephyr_master.json"))\n')
    assert guard.scan(root) == []


def test_the_real_tree_is_clean():
    assert guard.scan(guard.CK_SERVER) == []

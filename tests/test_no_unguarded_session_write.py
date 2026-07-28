"""Structural: every wizard/pt SESSION write funnels through a lock-guarded choke point.

Case locking (PLAN-auth-and-case-locking.md Phase 1) enforces the per-case lock and the
`rev` optimistic backstop inside exactly two functions — `session_store.persist_session`
and `pytest_create._pt_persist`. If any other module calls `db.save_session` directly, it
writes a session with NEITHER guard, silently reintroducing the overwrite bug the lock
exists to prevent. So this asserts, against the AST (not a text grep — the same discipline
as test_event_loop_blocking_batch_b.py), that:

  1. `save_session(...)` is called ONLY from the two choke-point files.
  2. `_write_session(...)` (db.py's private upsert) is called ONLY from db.py.
  3. Both choke points actually invoke the guard (`require_can_write`) and the backstop
     (`next_rev`) — checked on the function body so a stray comment can't fake a pass.

`save_workspace_llm` is deliberately out of scope: the workspace LLM config is not a case
session and takes no case lock.
"""
import ast
import pathlib

_CK = pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"

_SAVE_SESSION_ALLOWED = {"session_store.py", "pytest_create.py"}
_WRITE_SESSION_ALLOWED = {"db.py"}


def _call_names(node):
    """Names of every function CALLED anywhere under `node` (id or attribute tail)."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            out.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None))
    return out


def _call_lines(path, target):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if name == target:
                lines.append(n.lineno)
    return lines


def _fn_call_names(path, fnname):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fnname:
            return _call_names(n)
    return set()


def test_save_session_only_called_by_the_two_choke_points():
    offenders = []
    for py in sorted(_CK.rglob("*.py")):
        if py.name in _SAVE_SESSION_ALLOWED:
            continue
        for ln in _call_lines(py, "save_session"):
            offenders.append(f"{py.relative_to(_CK)}:{ln}")
    assert not offenders, (
        "a session write bypasses the lock-guarded choke points "
        "(session_store.persist_session / pytest_create._pt_persist):\n  "
        + "\n  ".join(offenders))


def test_write_session_only_called_by_db():
    offenders = []
    for py in sorted(_CK.rglob("*.py")):
        if py.name in _WRITE_SESSION_ALLOWED:
            continue
        for ln in _call_lines(py, "_write_session"):
            offenders.append(f"{py.relative_to(_CK)}:{ln}")
    assert not offenders, "\n  ".join(offenders)


def test_both_choke_points_invoke_guard_and_backstop():
    persist = _fn_call_names(_CK / "session_store.py", "persist_session")
    assert {"require_can_write", "next_rev"} <= persist, (
        "session_store.persist_session must call locks.require_can_write and locks.next_rev; "
        f"found calls: {sorted(c for c in persist if c)}")
    pt = _fn_call_names(_CK / "routers" / "pytest_create.py", "_pt_persist")
    assert {"require_can_write", "next_rev"} <= pt, (
        "pytest_create._pt_persist must call locks.require_can_write and locks.next_rev; "
        f"found calls: {sorted(c for c in pt if c)}")

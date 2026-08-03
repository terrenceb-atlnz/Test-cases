"""The run thread must inherit the initiating session's context.

PHASE 11.0. This is the defect that meant no test case had ever executed on hardware.
`RunManager.start` spawned a bare `threading.Thread`, which begins with a fresh
`contextvars.Context`. `locks.current_holder()` reads `llm.current_session_id`, a
ContextVar, so the run thread's holder was `''` while the browser tab held a live lock on
the same case — and the thread's first `on_update` was refused by its own initiator. The
refusal happened inside the connect `try/except`, so it surfaced as
"SSH connect failed: … the case is locked" and sent five sessions to look at the bench.

The first test here fails against a bare `threading.Thread` and passes with
`contextvars.copy_context()`. The last one is the generalisation: no module in the server
may spawn a thread without carrying the context, because the failure is silent and the
symptom always points somewhere else.
"""
import ast
import contextvars
import os
import threading

import pytest

import llm
import locks
import pt_exec

SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "ask-ck", "CK-main", "CK_server")


@pytest.fixture
def held_case():
    """A case locked by a simulated browser tab, as during a real run."""
    key = "TEST-CONTEXTVAR-CASE"
    token = llm.current_session_id.set("browser-tab-abc")
    locks.acquire("pt", key, holder="browser-tab-abc")
    try:
        yield key
    finally:
        try:
            locks.release("pt", key, holder="browser-tab-abc")
        except Exception:
            pass
        llm.current_session_id.reset(token)


def test_bare_thread_loses_the_holder(held_case):
    """The defect itself, pinned. If this ever passes, ContextVar propagation changed."""
    seen = {}

    def worker():
        seen["holder"] = locks.current_holder()

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert seen["holder"] == "", "a bare thread must NOT inherit the ContextVar"
    assert locks.current_holder() == "browser-tab-abc"


def test_run_manager_thread_inherits_the_holder(held_case):
    """The fix. The run thread must see the tab that started it as the lock holder."""
    seen = {}
    done = threading.Event()

    def fake_run(*args):
        seen["holder"] = locks.current_holder()
        try:
            locks.require_can_write("pt", held_case)
            seen["can_write"] = True
        except Exception as exc:
            seen["can_write"] = False
            seen["error"] = f"{type(exc).__name__}: {exc}"
        done.set()

    mgr = pt_exec.RunManager()
    original = mgr._run
    try:
        mgr._run = fake_run
        mgr.start(held_case, {"run_id": "r1"}, {}, {}, "setup", None, lambda r: None)
        assert done.wait(5), "run thread never started"
    finally:
        mgr._run = original

    assert seen["holder"] == "browser-tab-abc", (
        "the run thread did not inherit the initiating session — this is the defect that "
        "made every browser-initiated run report 'SSH connect failed: the case is locked'")
    assert seen["can_write"] is True, seen.get("error")


def test_run_thread_can_persist_while_the_initiator_holds_the_lock(held_case):
    """End-to-end shape of the bug: the first status update must not be locked out.

    `RunManager._run` sets status='connecting' and calls `on_update` BEFORE `_connect`.
    That call is what used to raise.
    """
    errors = []
    done = threading.Event()

    def on_update(run):
        try:
            locks.require_can_write("pt", held_case)
        except Exception as exc:
            errors.append(str(exc))
        finally:
            done.set()

    mgr = pt_exec.RunManager()
    original = mgr._run
    try:
        mgr._run = lambda run, *a: on_update(run)
        mgr.start(held_case, {"run_id": "r2"}, {}, {}, "setup", None, on_update)
        assert done.wait(5)
    finally:
        mgr._run = original
    assert not errors, f"first status update was locked out by its own initiator: {errors}"


def test_context_copy_is_taken_on_the_calling_thread(held_case):
    """The copy must happen in `start()`, not inside the thread.

    `main.py` resets the ContextVar in a `finally` when the request ends. A copy taken on
    the calling thread keeps the value; a lookup performed later inside the thread would
    race that reset.
    """
    ctx = contextvars.copy_context()
    llm.current_session_id.set("")          # simulate the request ending
    seen = {}
    t = threading.Thread(target=ctx.run, args=(lambda: seen.__setitem__("h", locks.current_holder()),))
    t.start()
    t.join()
    assert seen["h"] == "browser-tab-abc", "the copy must survive the request's reset"


# --------------------------------------------------------------------------- 11.2 sweep

def _thread_constructions(path):
    """(lineno, target_source, exempt) for every threading.Thread(...) built in `path`.

    `exempt` is True when a `# context-free: <reason>` comment sits on or just above the
    construction. An explicit marker with a stated reason, rather than a list of allowed
    files here: a list rots silently, and the whole point of this guard is that the
    failure it catches is invisible at run time.
    """
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    lines = source.splitlines()
    tree = ast.parse(source, filename=path)

    def exempt_at(lineno):
        window = lines[max(0, lineno - 5):lineno]
        return any("context-free:" in line for line in window)

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (func.attr if isinstance(func, ast.Attribute)
                else func.id if isinstance(func, ast.Name) else "")
        if name != "Thread":
            continue
        target = next((kw.value for kw in node.keywords if kw.arg == "target"), None)
        found.append((node.lineno,
                      ast.unparse(target) if target is not None else "",
                      exempt_at(node.lineno)))
    return found


def test_no_server_thread_is_spawned_without_its_context():
    """Generalisation of 11.0 — every background thread must carry the request context.

    A thread whose target is `ctx.run` (of a copied Context) propagates. A bare function
    target does not, and the resulting failure is silent and misattributed. A thread that
    genuinely has no request context to inherit — one started at app startup — declares
    itself with a `# context-free: <reason>` comment, so the exemption is stated where the
    thread is created rather than in a list here that would rot.
    """
    offenders = []
    for root, _dirs, files in os.walk(SERVER_DIR):
        if "__pycache__" in root or "/static/" in root or "/debug-log" in root:
            continue
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            for lineno, target, exempt in _thread_constructions(path):
                if not target.endswith(".run") and not exempt:
                    rel = os.path.relpath(path, SERVER_DIR)
                    offenders.append(f"{rel}:{lineno} target={target or '<positional>'}")
    assert not offenders, (
        "background thread(s) spawned without contextvars.copy_context() and without a "
        "`# context-free: <reason>` marker — the run thread lost its lock holder this way "
        "and nothing executed on hardware for months:\n  " + "\n  ".join(offenders))


def test_the_context_free_marker_is_not_a_blanket_exemption():
    """The escape hatch must require the words, so it cannot be granted by accident."""
    import tempfile
    src = ("import threading\n"
           "def f(): pass\n"
           "threading.Thread(target=f).start()\n")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(src)
        path = fh.name
    try:
        assert _thread_constructions(path) == [(3, "f", False)]
        with open(path, "w") as fh:
            fh.write(src.replace("threading.Thread(target=f)",
                                 "# context-free: startup only\nthreading.Thread(target=f)"))
        assert _thread_constructions(path)[0][2] is True
    finally:
        os.unlink(path)

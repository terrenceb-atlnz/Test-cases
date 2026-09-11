#!/usr/bin/env python3
"""Guard + tests: the testbox framework dir is READ-ONLY for this project.

The testbox 'framework_path' (default /home/st-art/framework) must never be written,
edited, or mutated by PyTest Creator. Files there may be READ (and copied locally for
editing as an explicit exception), but nothing in the tool may write into that tree.

This runs the runtime guards in CK_server/pt_exec.py against a table of allowed/blocked
operations, so a regression that lets a mutation through (or that breaks the legitimate
read/copy/run path) fails here.

Usage:  python3 tool/guard_framework_readonly.py     # exit 0 = all pass, 1 = a case failed
"""
import sys
from pathlib import Path

CK_SERVER = Path(__file__).resolve().parent.parent / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(CK_SERVER))

import pt_exec as p  # noqa: E402

PROFILE = {"framework_path": "/home/st-art/framework",
           "remote_workdir": "/home/st-art/pytest-create"}


def _write_blocked(target: str) -> bool:
    try:
        p._assert_write_allowed(target, PROFILE)
        return False
    except p.FrameworkReadOnlyError:
        return True


def _cmd_blocked(cmd: str) -> bool:
    try:
        p._assert_command_allowed(cmd, PROFILE)
        return False
    except p.FrameworkReadOnlyError:
        return True


# (label, callable, expect_blocked)
CASES = [
    # WRITES — workdir allowed, framework refused (incl. traversal + root)
    ("write workdir file",         lambda: _write_blocked("/home/st-art/pytest-create/T33234/r1/x.py"), False),
    ("write framework file",       lambda: _write_blocked("/home/st-art/framework/ATTestSet.py"),        True),
    ("write framework via ..",     lambda: _write_blocked("/home/st-art/pytest-create/../framework/x"),  True),
    ("write framework root",       lambda: _write_blocked("/home/st-art/framework"),                     True),
    # COMMANDS — the legit run path + read/copy-from must pass
    ("legit run command",          lambda: _cmd_blocked(
        "cd /home/st-art/pytest-create/T33234/r1 && ln -sfn /home/st-art/framework framework && "
        "sudo -n PYTHONPATH=/home/st-art python3 ./test.py -s a.setup -v"),                              False),
    ("cp FROM framework local",    lambda: _cmd_blocked("cp /home/st-art/framework/ATTestSet.py ./local.py"), False),
    ("cp -r framework tree local", lambda: _cmd_blocked("cp -r /home/st-art/framework ./fw_copy"),        False),
    ("read test -d framework",     lambda: _cmd_blocked("test -d /home/st-art/framework && echo yes"),    False),
    # COMMANDS — every mutation of the framework must be refused
    ("mv INTO framework",          lambda: _cmd_blocked("mv ./x.py /home/st-art/framework/x.py"),         True),
    ("cp INTO framework",          lambda: _cmd_blocked("cp x.py /home/st-art/framework/x.py"),           True),
    ("rm under framework",         lambda: _cmd_blocked("sudo rm -rf /home/st-art/framework/ATDrivers"),  True),
    ("sed -i framework file",      lambda: _cmd_blocked("sed -i s/a/b/ /home/st-art/framework/ATTestSet.py"), True),
    ("touch in framework",         lambda: _cmd_blocked("touch /home/st-art/framework/new.py"),           True),
    ("tee into framework",         lambda: _cmd_blocked("echo x | tee /home/st-art/framework/f.py"),       True),
    ("chained cp then rm fw",      lambda: _cmd_blocked("cp a b && rm /home/st-art/framework/z"),          True),
]


def main() -> int:
    failures = []
    for label, fn, expect_blocked in CASES:
        got = fn()
        verdict = "BLOCKED" if got else "allowed"
        want = "BLOCKED" if expect_blocked else "allowed"
        if got != expect_blocked:
            failures.append(f"  {label}: expected {want}, got {verdict}")
    if failures:
        print("FRAMEWORK-RO GUARD FAIL — framework read-only invariant broken:")
        print("\n".join(failures))
        return 1
    print(f"FRAMEWORK-RO GUARD OK — {len(CASES)} cases pass; framework dir is write-protected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

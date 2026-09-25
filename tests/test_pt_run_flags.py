"""Every Ask-CK hardware run launches with `--noupdate --nodefaultcfg` (Terrence, 2026-09-25).

WHY. Without them the framework's TestSet setup resets every device a script binds: a generated
default.cfg written through start-shell, licences loaded and stripped, a reboot, and a TFTP copy of
`<platform>-<host>.rel` into flash as the boot image. The first framework run of a generated script
on tb470 (T33235, 2026-09-25) did exactly that to all four devices, then hung on the copy. The bench
now pre-loads each topology's own config, and the framework only runs configure() and tear-down.

Pinned: the launch line carries both flags after `-v`; it still passes the read-only-framework
guard; the -s argument stays quoted; and the run thread builds its line through `run_command`, so
the flags cannot be bypassed by a second hand-built command.
"""
import ast
import shlex
from pathlib import Path

import pt_exec

_PROFILE = {"framework_path": "/home/st-art/framework", "remote_workdir": "/home/st-art/pytest-create"}


def _cmd(setup="/tmp/run/tb470.setup"):
    return pt_exec.run_command("/home/st-art/pytest-create/AWPTCM-T1/r1", "/home/st-art/framework",
                               "/home/st-art", "test-9001.1.py", setup)


def test_the_launch_line_skips_the_framework_reset_and_software_update():
    argv = shlex.split(_cmd().split("&&")[-1])
    assert argv[-3:] == ["-v", "--noupdate", "--nodefaultcfg"]
    assert pt_exec.FRAMEWORK_RUN_FLAGS == ("--noupdate", "--nodefaultcfg")


def test_the_launch_line_still_passes_the_framework_guard():
    pt_exec._assert_command_allowed(_cmd(), _PROFILE)


def test_the_setup_argument_stays_quoted():
    argv = shlex.split(_cmd("/tmp/x; rm -rf ~").split("&&")[-1])
    assert argv[argv.index("-s") + 1] == "/tmp/x; rm -rf ~"


def test_the_run_thread_builds_its_line_through_run_command():
    src = Path(pt_exec.__file__).read_text()
    run = next(n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "_run")
    calls = {n.func.id for n in ast.walk(run)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "run_command" in calls
    literals = [n.value for n in ast.walk(run) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("python3" in s for s in literals), "a second, hand-built launch line in _run"

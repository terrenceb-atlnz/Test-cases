"""PyTest Creator execution engine.

Three concerns, all hardware-adjacent (see ask-ck/pytest-create/PLAN-pytest-creator.md §2):
- Testbox profiles: named SSH/testbox records stored in the gitignored
  secrets.testboxes.json (same discovery convention as tool/upload_refined.py).
- parse_framework_log(): pure parser for the ATTestSet/ATTestCase log format —
  unit-testable offline.
- run_script_on_testbox(): paramiko SSH+SFTP round trip, driven from a
  threading.Thread so runs survive the HTTP request and are pollable.
"""

import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Testbox profiles (secrets file)
# ---------------------------------------------------------------------------

# Test-cases repo root: CK_server -> CK-main -> ask-ck -> Test-cases
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SECRETS_TESTBOXES = _REPO_ROOT / "secrets.testboxes.json"

PROFILE_REQUIRED = ("tb_number", "host")
PROFILE_DEFAULTS = {
    "port": 22,
    "user": "st-art",
    "auth": "key",             # "key" | "password"
    "key_path": "~/.ssh/id_rsa",
    "password": None,
    "framework_path": "/home/st-art/framework",
    "remote_workdir": "/home/st-art/pytest-create",
    "setups": {},               # name -> remote path of a .setup file
    "sudo": "passwordless",
    "timeout_s": 1800,
}


# ---------------------------------------------------------------------------
# Framework read-only invariant
# ---------------------------------------------------------------------------
# The testbox framework dir (profile 'framework_path', default /home/st-art/framework)
# is READ-ONLY for this project. Nothing here may write into it, edit a file under it,
# or run a mutating command against it. If a framework file ever needs changing, it is
# copied into the run workdir first and edited there — an explicit exception, never the
# default path. These guards fail LOUDLY (RuntimeError) rather than let a mutation run.

class FrameworkReadOnlyError(RuntimeError):
    """Raised when a remote operation would write into the read-only framework dir."""


def _framework_root(profile: dict) -> str:
    fw = (profile.get("framework_path") or "/home/st-art/framework").rstrip("/")
    return fw or "/home/st-art/framework"


def _norm_remote(path: str) -> str:
    """Normalize a POSIX remote path for prefix comparison (no FS access)."""
    # collapse redundant separators / '.' and resolve '..' textually
    parts: List[str] = []
    for seg in str(path).replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    lead = "/" if str(path).startswith("/") else ""
    return lead + "/".join(parts)


def _assert_write_allowed(target: str, profile: dict) -> str:
    """Guard a remote WRITE target: reject anything under the framework dir."""
    fw = _norm_remote(_framework_root(profile))
    t = _norm_remote(target)
    if t == fw or t.startswith(fw + "/"):
        raise FrameworkReadOnlyError(
            f"Refusing to write to '{target}': the testbox framework dir '{fw}' is "
            f"READ-ONLY for this project. Copy the file into the run workdir and edit "
            f"there instead.")
    return target


# Mutating shell verbs whose target-under-framework we must reject in exec commands.
_MUTATING_RX = re.compile(
    r"""(?x)
    (?:^|\s|&&|\|\||;)\s*
    (?:sudo\s+(?:-\S+\s+)*)?                       # optional sudo prefix
    (rm|mv|cp|touch|mkdir|rmdir|chmod|chown|chgrp|
     ln|dd|truncate|tee|sed\s+-i|patch)\b
    """)


def _under_fw(path: str, fw: str) -> bool:
    n = _norm_remote(path)
    return n == fw or n.startswith(fw + "/")


# copy/link verbs where the framework path is legitimately the READ-ONLY SOURCE
# (first operand) and only the DESTINATION (last operand) is a write target.
_SRC_DEST_VERBS = ("cp", "mv", "ln")


def _assert_command_allowed(cmd: str, profile: dict) -> str:
    """Guard a remote exec string: reject a mutating verb whose WRITE TARGET is under
    the framework dir. Read-only references are allowed — `test -d <fw>`, `PYTHONPATH=<fw>`,
    copying/symlinking FROM the framework (fw as source), and `ln -s <fw> <name>`
    (pointing a workdir symlink AT the framework). Only a mutation whose destination
    sits inside the framework dir is refused. Splits on &&/||/; so each sub-command is
    judged on its own operands."""
    fw = _norm_remote(_framework_root(profile))
    for sub in re.split(r"&&|\|\||;", cmd):
        sub = sub.strip()
        if not sub or not _MUTATING_RX.search(sub):
            continue
        toks = re.findall(r"\S+", sub)
        operands = [t for t in toks if not t.startswith("-")]  # drop flags
        verb = next((t for t in toks if not t.startswith("-")), "")
        fw_toks = [t for t in toks if _under_fw(t, fw)]
        if not fw_toks:
            continue
        # For cp/mv/ln, the framework path as SOURCE (any operand except the last)
        # is a read-only reference and allowed; only the last operand is the write
        # destination. For all other verbs (rm/sed -i/touch/tee/dd/…) any framework
        # operand is a mutation of the framework and is refused.
        if verb in _SRC_DEST_VERBS and len(operands) >= 2:
            dest = operands[-1]
            if not _under_fw(dest, fw):
                continue  # framework appears only as source — fine
        raise FrameworkReadOnlyError(
            f"Refusing remote command that writes under the READ-ONLY framework dir "
            f"'{fw}': {sub!r}. Copy into the workdir and operate there instead.")
    return cmd


def load_profiles() -> Dict[str, dict]:
    if not SECRETS_TESTBOXES.exists():
        return {}
    try:
        raw = json.load(open(SECRETS_TESTBOXES, encoding="utf-8"))
        return raw.get("profiles", {})
    except Exception as e:
        print(f"Warning: failed to read {SECRETS_TESTBOXES}: {e}")
        return {}


def save_profiles(profiles: Dict[str, dict]) -> None:
    SECRETS_TESTBOXES.write_text(
        json.dumps({"profiles": profiles}, indent=2), encoding="utf-8")
    try:
        SECRETS_TESTBOXES.chmod(0o600)  # credentials: owner-only
    except OSError:
        pass


def redact_profile(p: dict) -> dict:
    """Profile as safe to return from the API (never the password itself)."""
    out = {k: v for k, v in p.items() if k != "password"}
    out["has_password"] = bool(p.get("password"))
    return out


def normalize_profile(body: dict) -> dict:
    """Merge submitted fields over defaults; keep only known keys."""
    prof = dict(PROFILE_DEFAULTS)
    for k in list(PROFILE_DEFAULTS) + list(PROFILE_REQUIRED):
        if k in body and body[k] is not None:
            prof[k] = body[k]
    missing = [k for k in PROFILE_REQUIRED if not prof.get(k)]
    if missing:
        raise ValueError(f"profile missing required fields: {', '.join(missing)}")
    return prof


# ---------------------------------------------------------------------------
# Framework log parsing (pure, offline-testable)
# ---------------------------------------------------------------------------

_TS_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}:\s?")
_CASE_START = re.compile(r"^>> test-(.+?)\s*$")
_CASE_END = re.compile(
    r"^<< test-(.+?):\s*(PASS|FAIL|ERROR|UNSUPPORTED)\s*"
    r"\(numPassed:\s*(\d+)\s*numFailed:\s*(\d+)\)")
_PASS_LINE = re.compile(r"^PASS:\s*(.*)$")
_FAIL_LINE = re.compile(r"^!!FAIL:\s*(.*)$")


def parse_framework_log(text: str) -> Dict[str, Any]:
    """Parse an ATTestSet log into per-case results.

    Returns {cases: [{name, result, pass_msgs, fail_msgs, log_lines: [start, end]}],
             numPassed, numFailed, unparsed_fails}
    log_lines are 0-based indexes into the stripped-line list, used to pull
    excerpts for the LLM fix prompt.
    """
    lines = text.splitlines()
    cases: List[dict] = []
    current: Optional[dict] = None
    unparsed_fails = 0

    for i, raw in enumerate(lines):
        line = _TS_PREFIX.sub("", raw).rstrip()
        m = _CASE_START.match(line)
        if m:
            if current is not None:  # previous case never closed (crash/abort)
                current["result"] = current.get("result") or "ERROR"
                current["log_lines"][1] = i - 1
                cases.append(current)
            current = {"name": m.group(1), "result": None,
                       "pass_msgs": [], "fail_msgs": [], "log_lines": [i, None]}
            continue
        m = _CASE_END.match(line)
        if m:
            if current is None or m.group(1) != current["name"]:
                # footer without matching header — record standalone
                current = current or {"name": m.group(1), "result": None,
                                      "pass_msgs": [], "fail_msgs": [], "log_lines": [i, None]}
            current["result"] = m.group(2)
            current["numPassed"] = int(m.group(3))
            current["numFailed"] = int(m.group(4))
            current["log_lines"][1] = i
            cases.append(current)
            current = None
            continue
        m = _PASS_LINE.match(line)
        if m:
            if current is not None:
                current["pass_msgs"].append(m.group(1))
            continue
        m = _FAIL_LINE.match(line)
        if m:
            if current is not None:
                current["fail_msgs"].append(m.group(1))
            else:
                unparsed_fails += 1

    if current is not None:  # log ended mid-case
        current["result"] = current.get("result") or "ERROR"
        current["log_lines"][1] = len(lines) - 1
        cases.append(current)

    return {
        "cases": [{k: v for k, v in c.items()} for c in cases],
        "numPassed": sum(c.get("numPassed", len(c["pass_msgs"])) for c in cases),
        "numFailed": sum(c.get("numFailed", len(c["fail_msgs"])) for c in cases),
        "unparsed_fails": unparsed_fails,
    }


def failure_excerpts(text: str, parsed: Dict[str, Any], context: int = 15,
                     max_chars: int = 4000) -> List[dict]:
    """Bounded log excerpt per failing case, for the fix prompt."""
    lines = text.splitlines()
    out = []
    for c in parsed.get("cases", []):
        if c.get("result") in ("PASS", None):
            continue
        start, end = c.get("log_lines", [0, 0])
        end = end if end is not None else min(start + 80, len(lines) - 1)
        lo = max(0, start)
        hi = min(len(lines), end + context + 1)
        excerpt = "\n".join(lines[lo:hi])
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars // 2] + "\n... [truncated] ...\n" + excerpt[-max_chars // 2:]
        out.append({"case": c["name"], "text": excerpt})
    return out


# ---------------------------------------------------------------------------
# Remote execution
# ---------------------------------------------------------------------------

def _connect(profile: dict):
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {
        "hostname": profile["host"],
        "port": int(profile.get("port", 22)),
        "username": profile.get("user", "st-art"),
        "timeout": 20,
    }
    if profile.get("auth") == "password" and profile.get("password"):
        kwargs["password"] = profile["password"]
        kwargs["allow_agent"] = False
        kwargs["look_for_keys"] = False
    else:
        key_path = str(Path(profile.get("key_path") or "~/.ssh/id_rsa").expanduser())
        kwargs["key_filename"] = key_path
    client.connect(**kwargs)
    return client


def check_profile(profile: dict) -> Dict[str, Any]:
    """SSH connect + framework presence + passwordless sudo probe."""
    result = {"ok": False, "ssh": False, "framework": False, "sudo": False, "detail": ""}
    try:
        client = _connect(profile)
    except Exception as e:
        result["detail"] = f"SSH connection failed: {e}"
        return result
    result["ssh"] = True
    try:
        fw = profile.get("framework_path", "/home/st-art/framework")
        _, out, _ = client.exec_command(f"test -d {fw} && echo yes || echo no", timeout=15)
        result["framework"] = out.read().decode().strip() == "yes"
        _, out, _ = client.exec_command("sudo -n true && echo yes || echo no", timeout=15)
        result["sudo"] = "yes" in out.read().decode()
        _, out, _ = client.exec_command("hostname && python3 --version", timeout=15)
        result["detail"] = out.read().decode().strip()
        result["ok"] = result["ssh"] and result["framework"] and result["sudo"]
        if not result["framework"]:
            result["detail"] += f" | framework not found at {fw}"
        if not result["sudo"]:
            result["detail"] += " | passwordless sudo unavailable (required to run tests)"
    finally:
        client.close()
    return result


class RunManager:
    """One background run at a time per case key; state persisted via callback."""

    def __init__(self):
        self._threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def is_running(self, key: str) -> bool:
        t = self._threads.get(key)
        return bool(t and t.is_alive())

    def start(self, key: str, run: dict, profile: dict, files: Dict[str, str],
              setup_remote: str, local_run_dir: Path, on_update) -> None:
        """Launch the run thread. `files` = {filename: code}. `on_update(run)` persists."""
        with self._lock:
            if self.is_running(key):
                raise RuntimeError("a run is already active for this case")
            t = threading.Thread(
                target=self._run, name=f"pt-run-{key}",
                args=(run, profile, files, setup_remote, local_run_dir, on_update),
                daemon=True)
            self._threads[key] = t
            t.start()

    def _run(self, run: dict, profile: dict, files: Dict[str, str],
             setup_remote: str, local_run_dir: Path, on_update) -> None:
        test_name = run["test_file"]
        workdir = f"{profile.get('remote_workdir', '/home/st-art/pytest-create')}/{run['case_key']}/{run['run_id']}"
        timeout_s = int(profile.get("timeout_s", 1800))
        try:
            run["status"] = "connecting"
            on_update(run)
            client = _connect(profile)
        except Exception as e:
            run.update({"status": "error", "error": f"SSH connect failed: {e}",
                        "finished_at": datetime.utcnow().isoformat()})
            on_update(run)
            return

        try:
            run["status"] = "uploading"
            on_update(run)
            # Guard: the run workdir must never be under the read-only framework dir.
            _assert_write_allowed(workdir, profile)
            client.exec_command(f"mkdir -p {workdir}")[1].channel.recv_exit_status()
            sftp = client.open_sftp()
            for fname, code in files.items():
                target = f"{workdir}/{fname}"
                _assert_write_allowed(target, profile)   # never write into framework
                with sftp.open(target, "w") as f:
                    f.write(code)
            sftp.close()

            # framework resolves via the box's symlink; PYTHONPATH covers boxes
            # where the symlink lives elsewhere (profile framework_path parent).
            fw_parent = str(Path(profile.get("framework_path", "/home/st-art/framework")).parent)
            cmd = (f"cd {workdir} && ln -sfn {profile.get('framework_path')} framework && "
                   f"sudo -n PYTHONPATH={fw_parent} python3 ./{test_name} -s {setup_remote} -v")
            _assert_command_allowed(cmd, profile)   # no mutation of the framework dir
            run["status"] = "running"
            run["command"] = cmd
            on_update(run)

            _, out, err = client.exec_command(cmd, timeout=timeout_s, get_pty=True)
            deadline = time.time() + timeout_s
            chunks = []
            while not out.channel.exit_status_ready():
                if time.time() > deadline:
                    raise TimeoutError(f"run exceeded {timeout_s}s")
                while out.channel.recv_ready():
                    chunks.append(out.channel.recv(65536).decode(errors="replace"))
                time.sleep(2)
            while out.channel.recv_ready():
                chunks.append(out.channel.recv(65536).decode(errors="replace"))
            exit_code = out.channel.recv_exit_status()
            stdout_text = "".join(chunks)

            # Retrieve the framework log (named after the script basename)
            local_run_dir.mkdir(parents=True, exist_ok=True)
            (local_run_dir / "stdout.txt").write_text(stdout_text, encoding="utf-8")
            log_name = Path(test_name).with_suffix(".log").name
            log_text = ""
            sftp = client.open_sftp()
            try:
                remote_logs = [f for f in sftp.listdir(workdir) if f.endswith(".log")]
                preferred = log_name if log_name in remote_logs else (remote_logs[0] if remote_logs else None)
                if preferred:
                    local_log = local_run_dir / preferred
                    sftp.get(f"{workdir}/{preferred}", str(local_log))
                    log_text = local_log.read_text(encoding="utf-8", errors="replace")
                    run["log_file"] = str(local_log)
            finally:
                sftp.close()

            run["exit_code"] = exit_code
            run["parsed"] = parse_framework_log(log_text or stdout_text)
            run["status"] = "done"
            run["finished_at"] = datetime.utcnow().isoformat()
            on_update(run)
        except Exception as e:
            run.update({"status": "error", "error": str(e),
                        "finished_at": datetime.utcnow().isoformat()})
            on_update(run)
        finally:
            client.close()


run_manager = RunManager()

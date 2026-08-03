"""PyTest Creator execution engine.

Three concerns, all hardware-adjacent (see ask-ck/pytest-create/PLAN-pytest-creator.md §2):
- Testbox profiles: named SSH/testbox records stored in the gitignored
  secrets.testboxes.json (same discovery convention as tool/upload_refined.py).
- parse_framework_log(): pure parser for the ATTestSet/ATTestCase log format —
  unit-testable offline.
- run_script_on_testbox(): paramiko SSH+SFTP round trip, driven from a
  threading.Thread so runs survive the HTTP request and are pollable.
"""

import ast
import contextvars
import json
import os
import re
import shlex
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from timeutil import utc_now

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
     ln|dd|truncate|tee|sed\s+-i|patch|
     rsync|install|mktemp|chattr|setfacl|shred|link)\b
    """)

# Shapes that can write/execute WITHOUT a recognizable mutating verb — these bypass a
# verb denylist entirely, so they are refused outright whenever the framework path is
# referenced anywhere in the sub-command:
#   - output/append redirection ( > file, >> file )   → writes an arbitrary target
#   - an inline interpreter that can open() files      ( python/perl/ruby/sh -c … )
# Command substitution and backticks are ALSO refused whenever the sub-command touches
# the framework, since their contents aren't parsed by this guard.
_REDIRECT_RX = re.compile(r">>?")
_INTERP_EXEC_RX = re.compile(
    r"(?:^|\s|&&|\|\||;|\|)\s*(?:sudo\s+(?:-\S+\s+)*)?"
    r"(?:python[0-9.]*|perl|ruby|bash|sh|zsh|node|awk)\b[^|;&]*\s-c\b")
_CMD_SUBST_RX = re.compile(r"\$\(|`")


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
    # Split on pipes too, so a piped stage (e.g. `... | tee <fw>/f`) is judged on its own.
    for sub in re.split(r"&&|\|\||;|\|", cmd):
        sub = sub.strip()
        if not sub:
            continue
        touches_fw = any(_under_fw(t, fw) for t in re.findall(r"\S+", sub)) or (fw in sub)

        # (A) Verb-less write/exec shapes that a denylist can't see. If this sub-command
        # references the framework AND contains a redirection, an inline interpreter -c,
        # or a command substitution, refuse it — we cannot prove it's read-only.
        if touches_fw and (
            _REDIRECT_RX.search(sub) or _INTERP_EXEC_RX.search(sub) or _CMD_SUBST_RX.search(sub)
        ):
            raise FrameworkReadOnlyError(
                f"Refusing remote command that may write/execute against the READ-ONLY "
                f"framework dir '{fw}' via redirection/interpreter/substitution: {sub!r}.")

        if not _MUTATING_RX.search(sub):
            continue
        toks = re.findall(r"\S+", sub)
        operands = [t for t in toks if not t.startswith("-")]  # drop flags
        verb = next((t for t in toks if not t.startswith("-")), "")
        fw_toks = [t for t in toks if _under_fw(t, fw)]
        # A `-t DIR` / `--target-directory=DIR` destination is a flag, not a positional —
        # so a framework path can hide there and evade the "last operand" dest check.
        tgt_dir = None
        for i, t in enumerate(toks):
            if t in ("-t", "--target-directory") and i + 1 < len(toks):
                tgt_dir = toks[i + 1]
            elif t.startswith("--target-directory="):
                tgt_dir = t.split("=", 1)[1]
        if tgt_dir and _under_fw(tgt_dir, fw):
            raise FrameworkReadOnlyError(
                f"Refusing remote command whose --target-directory writes under the "
                f"READ-ONLY framework dir '{fw}': {sub!r}.")
        if not fw_toks:
            continue
        # For cp/mv/ln, the framework path as SOURCE (any operand except the last)
        # is a read-only reference and allowed; only the last operand is the write
        # destination. For all other verbs (rm/sed -i/touch/tee/dd/…) any framework
        # operand is a mutation of the framework and is refused.
        if verb in _SRC_DEST_VERBS and len(operands) >= 2 and not tgt_dir:
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


def parse_framework_log(text: str, expected_cases: Optional[int] = None) -> Dict[str, Any]:
    """Parse an ATTestSet log into per-case results.

    Returns {cases: [{name, result, pass_msgs, fail_msgs, log_lines: [start, end]}],
             numPassed, numFailed, unparsed_fails, status, expected_cases, verdict}
    log_lines are 0-based indexes into the stripped-line list, used to pull
    excerpts for the LLM fix prompt.

    PHASE 11.1 — EMPTY MUST NOT EQUAL SUCCESS. A run that never started parses to zero
    cases, zero passed and zero failed, which is indistinguishable from a clean sweep by
    every downstream check: `numFailed == 0` reads as green. That matters because the most
    likely first-run outcome is exactly this shape — `_ck_bind_link` aborting correctly on
    a bench problem produces a log with no case results at all.

    So the parser now states a `status` rather than leaving it to be inferred from counts:

        empty_log   nothing to parse
        no_results  the log has content but not one case result  <- the dangerous one
        short       fewer case results than the script registered
        ok          every expected case reported

    `expected_cases` comes from the script's own `ts.add_testCase(...)` registrations, so
    "short" is measured against what the script meant to run, not against a guess. This
    must be in place before the first hardware run or the first verdict is untrustworthy
    by construction.
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

    num_passed = sum(c.get("numPassed", len(c["pass_msgs"])) for c in cases)
    num_failed = sum(c.get("numFailed", len(c["fail_msgs"])) for c in cases)

    if not (text or "").strip():
        status = "empty_log"
    elif not cases:
        status = "no_results"
    elif expected_cases is not None and len(cases) < expected_cases:
        status = "short"
    else:
        status = "ok"

    # One line a human or a grader can act on. NEVER "0 failed" for a run that did not
    # produce results — that is the sentence this whole function exists to stop printing.
    if status == "empty_log":
        verdict = "NO RESULTS — the run produced no log output at all."
    elif status == "no_results":
        verdict = ("NO RESULTS — the log has content but not one test case reported. "
                   "The script almost certainly aborted before its first case (a bench or "
                   "binding problem), so this is NOT a pass.")
    elif status == "short":
        verdict = (f"INCOMPLETE — {len(cases)} of {expected_cases} registered test cases "
                   f"reported. The run stopped early; the missing cases are untested, not "
                   f"passing.")
    else:
        verdict = f"{num_passed} passed, {num_failed} failed across {len(cases)} case(s)."

    # A case that crashed mid-way has result ERROR and contributes NO numFailed, so a
    # failure count alone still reads clean. `ok` therefore requires every case to have
    # reached a verdict, not merely an absence of failures. UNSUPPORTED is a legitimate
    # outcome (the feature does not apply to this platform) and is reported, not failed.
    errored = [c["name"] for c in cases if c.get("result") in (None, "ERROR")]
    unsupported = [c["name"] for c in cases if c.get("result") == "UNSUPPORTED"]
    if errored and status == "ok":
        verdict = (f"{num_passed} passed, {num_failed} failed, and {len(errored)} case(s) "
                   f"did not reach a verdict ({', '.join(errored[:5])}) — those are "
                   f"errors, not passes.")

    return {
        "cases": [{k: v for k, v in c.items()} for c in cases],
        "numPassed": num_passed,
        "numFailed": num_failed,
        "unparsed_fails": unparsed_fails,
        "parsed_cases": len(cases),
        "expected_cases": expected_cases,
        "errored_cases": errored,
        "unsupported_cases": unsupported,
        "status": status,
        "ok": (status == "ok" and num_failed == 0 and unparsed_fails == 0 and not errored),
        "verdict": verdict,
    }


def expected_case_count(code: str) -> Optional[int]:
    """How many test cases the script registers, from its own `ts.add_testCase(...)` calls.

    Read from the AST rather than by regex so `add_testCase(X('arg'))` counts too. Returns
    None when the script cannot be parsed, so a caller can tell "no expectation" apart from
    "expected zero".
    """
    try:
        tree = ast.parse(code or "")
    except (SyntaxError, ValueError):
        return None
    count = 0
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_testCase"):
            count += 1
    return count


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
    # Trust-on-first-use, not trust-anything. Loading the operator's known_hosts FIRST
    # means a testbox we have seen before is PINNED: if its host key changes — which is
    # what a MITM on the lab network looks like — paramiko raises instead of silently
    # accepting the impostor. AutoAddPolicy still handles genuinely new hosts, so no
    # existing profile breaks and there is no prompt to answer.
    #
    # This matters because the connection is OUTBOUND to a testbox across the lab
    # network: its exposure is independent of the web UI being single-user on localhost.
    # A MITM otherwise receives the SFTP-uploaded test files and the `sudo` command
    # stream, plus a reusable credential whenever the profile uses password auth.
    #
    # Opt out with CK_SSH_TRUST_ANY=1 (e.g. a reimaged testbox whose key legitimately
    # changed — better still, remove its stale known_hosts line).
    if os.getenv("CK_SSH_TRUST_ANY") != "1":
        try:
            client.load_system_host_keys()
        except Exception as e:
            # A malformed/unreadable known_hosts must not block a run; we simply fall
            # back to today's accept-anything behaviour rather than failing the connect.
            print(f"Warning: could not load known_hosts ({e}); host keys unpinned.")
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
        """Launch the run thread. `files` = {filename: code}. `on_update(run)` persists.

        THIS IS WHY NO TEST CASE HAD EVER EXECUTED (Phase 11.0, 2026-08-03).

        A new `threading.Thread` starts with a FRESH `contextvars.Context` — it inherits
        nothing. `llm.current_session_id` is a ContextVar, and `locks.current_holder()`
        reads it, so the run thread's holder was `''` while the browser tab that started
        the run held a live, heartbeated lock on the same case. The thread's very first
        `on_update` — `run["status"] = "connecting"`, before SSH is even attempted — was
        therefore rejected by `locks.require_can_write` with `LockConflictError`. Because
        that call sits inside the connect `try/except`, the user was told
        **"SSH connect failed: … the case is locked"**: a lock defect wearing a lab
        fault's clothing, which is why five sessions went looking at the bench.

        Reproduced against the real `locks` module:

            holder in main thread          : 'browser-tab-abc'   can write: YES
            holder inside RunManager thread: ''                  can write: NO

        `copy_context()` captures the request's values HERE, on the calling thread, where
        they are still live — `main.py` resets the ContextVar in a `finally` when the
        request ends, and a copy is unaffected by that reset. Copying the whole context
        rather than threading one `holder=` argument through fixes every ContextVar at
        once, including the one `llm_debug` uses to name its log file: background work was
        being written to `debug-log/no-session.jsonl` for the same reason.
        """
        with self._lock:
            if self.is_running(key):
                raise RuntimeError("a run is already active for this case")
            ctx = contextvars.copy_context()
            t = threading.Thread(
                target=ctx.run, name=f"pt-run-{key}",
                args=(self._run, run, profile, files, setup_remote, local_run_dir, on_update),
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
                        "finished_at": utc_now().isoformat()})
            on_update(run)
            return

        try:
            run["status"] = "uploading"
            on_update(run)
            # Guard: the run workdir must never be under the read-only framework dir.
            _assert_write_allowed(workdir, profile)
            client.exec_command(f"mkdir -p {shlex.quote(workdir)}")[1].channel.recv_exit_status()
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
            fw_path = profile.get("framework_path") or "/home/st-art/framework"
            # Every interpolated component is shell-quoted: test_name/case_key are already
            # regex-constrained upstream, but `setup_remote` can be a client-supplied
            # "explicit remote path" (pytest_create.py) — quoting it here is the primary
            # defense against command injection through the -s argument. PYTHONPATH must
            # stay OUTSIDE the quote (it's a VAR=val prefix to the command, not an argument).
            cmd = (f"cd {shlex.quote(workdir)} && "
                   f"ln -sfn {shlex.quote(fw_path)} framework && "
                   f"sudo -n PYTHONPATH={shlex.quote(fw_parent)} python3 "
                   f"./{shlex.quote(test_name)} -s {shlex.quote(setup_remote)} -v")
            _assert_command_allowed(cmd, profile)   # no mutation of the framework dir
            run["status"] = "running"
            run["command"] = cmd
            on_update(run)

            _, out, err = client.exec_command(cmd, timeout=timeout_s, get_pty=True)
            deadline = time.time() + timeout_s
            chunks = []
            # On timeout, KEEP what the run already produced (2026-07-28). Raising here
            # used to discard `chunks` entirely, so a suite that had completed 13 of 14
            # TestCases and then blocked reported nothing at all — no PASS/FAIL, no stdout.
            # The most likely cause of such a block is a script waiting on an operator with
            # nobody there, which is precisely when the completed results matter most.
            timed_out = False
            while not out.channel.exit_status_ready():
                if time.time() > deadline:
                    timed_out = True
                    break
                while out.channel.recv_ready():
                    chunks.append(out.channel.recv(65536).decode(errors="replace"))
                time.sleep(2)
            while out.channel.recv_ready():
                chunks.append(out.channel.recv(65536).decode(errors="replace"))
            if timed_out:
                stdout_text = "".join(chunks)
                local_run_dir.mkdir(parents=True, exist_ok=True)
                (local_run_dir / "stdout.txt").write_text(stdout_text, encoding="utf-8")
                try:
                    out.channel.close()
                except Exception:
                    pass
                raise TimeoutError(
                    f"run exceeded {timeout_s}s — partial output preserved "
                    f"({len(stdout_text)} chars in stdout.txt). A script blocked on an "
                    f"operator prompt with no operator present is the usual cause.")
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
            # Expected count comes from the script that was actually uploaded, so a "short"
            # verdict is measured against what this run meant to do (Phase 11.1).
            expected = expected_case_count(files.get(test_name, ""))
            run["parsed"] = parse_framework_log(log_text or stdout_text, expected_cases=expected)
            run["status"] = "done"
            run["finished_at"] = utc_now().isoformat()
            on_update(run)
        except Exception as e:
            run.update({"status": "error", "error": str(e),
                        "finished_at": utc_now().isoformat()})
            on_update(run)
        finally:
            client.close()


run_manager = RunManager()
